"""Optional video export, kept out of the player screen."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import uuid

from PySide6.QtCore import QProcess, QStandardPaths, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QMessageBox,
    QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout,
)
from ..registry import get_algorithm
from ..worker import EVENT_PREFIX

APP_ROOT = Path(__file__).resolve().parents[2]


class ExportDialog(QDialog):
    export_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Экспорт видео")
        self.resize(560, 300)
        self.process = None
        self.execution = None
        self.input_valid = False
        self.video_path = None
        self.video_cache = {}
        self.job_dir = None
        self.export_target = None
        self.export_key = None
        self.pending_video = None
        self.stdout_buffer = ""
        self.last_worker_error = ""
        self.cancelled = False
        self.closing = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        self.heading = QLabel()
        self.heading.setObjectName("section")
        self.heading.setWordWrap(True)
        layout.addWidget(self.heading)
        self.quality = QComboBox()
        self.quality.addItem("480p · 15 кадров/с", "preview")
        self.quality.addItem("720p · 30 кадров/с", "hd")
        layout.addWidget(self.quality)
        options_row = QHBoxLayout()
        self.option_checks = {}
        for key, label in (("show_title", "Название"),
                           ("show_indices", "Индексы"),
                           ("show_counters", "Счётчики"),
                           ("show_comments", "Комментарии")):
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)
            self.option_checks[key] = checkbox
            options_row.addWidget(checkbox)
        self.option_checks["show_counters"].setToolTip(
            "Счётчики выбранного алгоритма и номер шага")
        self.option_checks["show_comments"].setToolTip("Текстовые пояснения к шагам под анимацией")
        options_row.addStretch()
        layout.addLayout(options_row)
        row = QHBoxLayout()
        self.export_video_button = QPushButton("Сохранить MP4…")
        self.export_video_button.setObjectName("primary")
        self.export_video_button.clicked.connect(self.export_video)
        row.addWidget(self.export_video_button)
        self.cancel_button = QPushButton("Отменить")
        self.cancel_button.clicked.connect(self.cancel_render)
        self.cancel_button.hide()
        row.addWidget(self.cancel_button)
        layout.addLayout(row)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.status = QLabel("Будет сохранена вся сортировка.")
        self.status.setWordWrap(True)
        self.status.setObjectName("muted")
        layout.addWidget(self.status)
        self.external_button = QPushButton("Открыть последний MP4")
        self.external_button.setEnabled(False)
        self.external_button.clicked.connect(self.open_external)
        layout.addWidget(self.external_button)
        self.log_button = QPushButton("Подробнее")
        self.log_button.setObjectName("quiet")
        self.log_button.setCheckable(True)
        self.log_button.toggled.connect(self.toggle_log)
        layout.addWidget(self.log_button)
        self.log = QPlainTextEdit()
        self.log.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(400)
        self.log.setMaximumHeight(150)
        self.log.hide()
        layout.addWidget(self.log)

    def capture(self, execution):
        if self.process is not None:
            return False
        self.execution = deepcopy(execution)
        self.input_valid = True
        self.heading.setText(get_algorithm(execution["algorithm"]).title)
        self.status.setText("Будет сохранена вся сортировка. Просмотр можно продолжать.")
        self.progress.hide()
        self.log.clear()
        self.log_button.setChecked(False)
        self.export_video_button.setEnabled(True)
        self.external_button.setEnabled(False)
        self.video_path = None
        return True

    def toggle_log(self, visible):
        self.log.setVisible(visible)
        self.log_button.setText("Скрыть подробности" if visible else "Подробнее")

    def set_busy(self, busy):
        self.cancel_button.setVisible(busy)
        self.cancel_button.setEnabled(busy and not self.cancelled)
        self.quality.setEnabled(not busy)
        for checkbox in self.option_checks.values():
            checkbox.setEnabled(not busy)
        self.export_video_button.setEnabled(self.input_valid and not busy)
        self.progress.show()

    def export_video(self):
        if not self.input_valid or self.process is not None:
            return
        # Capture this execution. Editing and playback can continue while
        # the worker exports this exact snapshot in its own process.
        job = {
            "execution": self.execution,
            "quality": self.quality.currentData(),
            "options": {key: checkbox.isChecked() for key, checkbox in self.option_checks.items()},
        }
        content = json.dumps(job, ensure_ascii=False, sort_keys=True)
        key = hashlib.sha256(content.encode("utf-8")).hexdigest()
        cached = self.video_cache.get(key)
        if not (cached and cached.is_file()) and importlib.util.find_spec("manim") is None:
            QMessageBox.information(
                self, "Manim нужен только для экспорта",
                "Просмотр уже работает без Manim. Для MP4 закрой приложение и запусти в папке проекта:\n\n"
                "uv run --extra export python main.py\n\n"
                "Системные зависимости для твоей ОС описаны в README.md.")
            return
        target = self.save_target("Экспорт видео", self.execution["algorithm"] + ".mp4", "MP4 (*.mp4)", "mp4")
        if not target:
            return
        self.export_target = Path(target)
        if cached and cached.is_file():
            self.save_rendered_video(cached)
            return
        try:
            cache = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)
            if not cache:
                raise OSError("Не найден каталог для временных файлов.")
            self.job_dir = Path(cache) / "renders" / uuid.uuid4().hex
            self.job_dir.mkdir(parents=True, exist_ok=False)
            job_file = self.job_dir / "job.json"
            job_file.write_text(content, encoding="utf-8")
        except OSError as exc:
            self.status.setText(str(exc))
            return
        self.export_key = key
        self.pending_video = None
        self.stdout_buffer = ""
        self.last_worker_error = ""
        self.cancelled = False
        self.log.clear()
        self.progress.setValue(0)
        self.status.setText("Подготовка MP4. Просмотр можно продолжать.")
        process = QProcess(self)
        self.process = process
        self.set_busy(True)
        process.setWorkingDirectory(str(APP_ROOT))
        process.setProgram(sys.executable)
        process.setArguments(["-u", "-X", "utf8", str(APP_ROOT / "main.py"), "--render", str(job_file)])
        process.readyReadStandardOutput.connect(lambda: self.read_stdout(process))
        process.readyReadStandardError.connect(lambda: self.read_stderr(process))
        process.finished.connect(lambda code, state: self.render_finished(process, code, state))
        process.errorOccurred.connect(lambda error: self.process_error(process, error))
        process.start()

    def read_stdout(self, process):
        if process is not self.process:
            return
        self.stdout_buffer += bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
        while "\n" in self.stdout_buffer:
            line, self.stdout_buffer = self.stdout_buffer.split("\n", 1)
            self.handle_worker_line(line.rstrip("\r"))

    def read_stderr(self, process):
        if process is self.process:
            text = bytes(process.readAllStandardError()).decode("utf-8", errors="replace")
            if text.strip():
                self.log.appendPlainText(text.rstrip())

    def handle_worker_line(self, line):
        if not line.startswith(EVENT_PREFIX):
            if line.strip():
                self.log.appendPlainText(line)
            return
        try:
            event = json.loads(line[len(EVENT_PREFIX):])
        except json.JSONDecodeError:
            self.log.appendPlainText(line)
            return
        kind = event.get("kind")
        if self.cancelled and kind in {"progress", "status"}:
            return
        if kind == "progress":
            current, total = event["current"], event["total"]
            self.progress.setValue(int(95 * current / max(total, 1)))
            self.status.setText(f"Экспорт MP4: шаг {current} из {total}")
        elif kind == "status":
            self.status.setText(event["message"])
            self.log.appendPlainText(event["message"])
        elif kind == "error":
            self.last_worker_error = event["message"]
            self.log.appendPlainText(event["message"])
        elif kind == "complete":
            self.pending_video = Path(event["path"])

    def process_error(self, process, error):
        if process is not self.process:
            return
        if error == QProcess.ProcessError.FailedToStart:
            self.last_worker_error = f"Процесс не запустился: {process.errorString()}"
            self.render_finished(process, -1, QProcess.ExitStatus.CrashExit)

    def render_finished(self, process, code, exit_status):
        if process is not self.process:
            return
        self.read_stdout(process)
        self.read_stderr(process)
        if self.stdout_buffer.strip():
            self.handle_worker_line(self.stdout_buffer.strip())
        self.stdout_buffer = ""
        self.process = None
        process.deleteLater()
        self.set_busy(False)
        if self.cancelled:
            self.status.setText("Экспорт отменён. Просмотр по шагам доступен.")
            self.progress.setValue(0)
        elif (code == 0 and exit_status == QProcess.ExitStatus.NormalExit
              and self.pending_video is not None and self.pending_video.is_file()
              and self.pending_video.stat().st_size > 0):
            self.video_cache[self.export_key] = self.pending_video
            self.save_rendered_video(self.pending_video)
        else:
            self.status.setText(self.last_worker_error or "Не удалось экспортировать MP4. Открой журнал ниже.")
            self.log_button.setChecked(True)
            self.progress.setValue(0)
        if self.job_dir is not None:
            try:
                (self.job_dir / "render.log").write_text(self.log.toPlainText(), encoding="utf-8")
            except OSError:
                pass
        self.export_finished.emit()

    def save_rendered_video(self, source):
        self.video_path = source
        self.external_button.setEnabled(True)
        self.progress.show()
        self.progress.setValue(100)
        try:
            if self.export_target.resolve() != source.resolve():
                shutil.copy2(source, self.export_target)
            self.status.setText(f"MP4 сохранён: {self.export_target.name}")
        except OSError as exc:
            self.status.setText("Видео готово, но файл не удалось сохранить. Повтори экспорт в другую папку.")
            if not self.closing:
                QMessageBox.warning(self, "Не удалось сохранить MP4", str(exc))

    def cancel_render(self):
        process = self.process
        if process is None:
            return
        self.cancelled = True
        self.cancel_button.setEnabled(False)
        self.status.setText("Останавливаем экспорт…")
        process.terminate()
        QTimer.singleShot(2000, lambda: self.kill_if_running(process))

    def kill_if_running(self, process):
        if process is self.process and process.state() != QProcess.ProcessState.NotRunning:
            process.kill()

    def save_target(self, title, filename, name_filter, suffix):
        dialog = QFileDialog(self, title)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setNameFilter(name_filter)
        dialog.setDefaultSuffix(suffix)
        dialog.selectFile(filename)
        return dialog.selectedFiles()[0] if dialog.exec() else ""

    def open_external(self):
        if self.video_path and not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.video_path))):
            QMessageBox.information(self, "Видео готово", f"Открой файл в своём видеоплеере:\n{self.video_path}")
