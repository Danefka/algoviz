from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMenu, QMessageBox,
    QPushButton, QSlider, QToolButton, QVBoxLayout, QWidget, QWidgetAction,
)
from ..playback import SPEED_PRESETS, Timeline
from ..inputs.registry import get_input
from ..renderers.registry import get_visualization
from .speed_slider import SpeedSlider, speed_label


class PlayerPage(QWidget):
    go_home = Signal()
    export_requested = Signal(dict)

    def __init__(self, algorithm, parent=None):
        super().__init__(parent)
        self.algorithm = algorithm
        self.input_spec = get_input(algorithm.input_type)
        self.visualization = get_visualization(algorithm.visualization)
        self.execution = None
        self.timeline = None
        self.input_valid = False
        self.playback_speed = 1.0
        self.last_tick = 0.0
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.tick)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)
        header = QHBoxLayout()
        self.home_button = QPushButton("← Алгоритмы")
        self.home_button.setObjectName("quiet")
        self.home_button.clicked.connect(lambda checked=False: self.go_home.emit())
        header.addWidget(self.home_button)
        header.addStretch()
        title = QLabel(algorithm.title)
        title.setObjectName("section")
        header.addWidget(title)
        header.addStretch()
        self.more = QToolButton()
        self.more.setText("⋯")
        self.more.setToolTip("Дополнительно")
        self.more.setAccessibleName("Дополнительно")
        self.more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.more.setMenu(self.make_menu())
        header.addWidget(self.more)
        layout.addLayout(header)

        self.input = QLineEdit(algorithm.example)
        self.input.setPlaceholderText(algorithm.example)
        self.input.setAccessibleName("Входные данные алгоритма")
        self.input.setToolTip(self.input_spec.input_hint)
        layout.addWidget(self.input)
        self.error = QLabel()
        self.error.setObjectName("error")
        self.error.setWordWrap(True)
        self.error.hide()
        layout.addWidget(self.error)
        self.canvas = self.visualization.create_canvas(self)
        self.indices_action.setEnabled(callable(getattr(self.canvas, "set_show_indices", None)))
        layout.addWidget(self.canvas, 1)
        self.caption = QLabel("Начальное состояние")
        self.caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption.setWordWrap(True)
        self.caption.setMinimumHeight(38)
        layout.addWidget(self.caption)
        self.stats = QLabel()
        self.stats.setObjectName("muted")
        self.stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stats.hide()
        layout.addWidget(self.stats)

        controls = QHBoxLayout()
        controls.addStretch()
        self.previous_button = QPushButton("←")
        self.previous_button.setToolTip("Предыдущий шаг")
        self.previous_button.setAccessibleName("Предыдущий шаг")
        self.previous_button.clicked.connect(self.step_back)
        self.play_button = QPushButton("Старт")
        self.play_button.setObjectName("primary")
        self.play_button.setFixedWidth(148)
        self.play_button.clicked.connect(self.toggle_playback)
        self.next_button = QPushButton("→")
        self.next_button.setToolTip("Следующий шаг")
        self.next_button.setAccessibleName("Следующий шаг")
        self.next_button.clicked.connect(self.step_forward)
        controls.addWidget(self.previous_button)
        controls.addWidget(self.play_button)
        controls.addWidget(self.next_button)
        controls.addStretch()
        layout.addLayout(controls)
        position = QHBoxLayout()
        self.seek = QSlider(Qt.Orientation.Horizontal)
        self.seek.setAccessibleName("Число завершённых шагов")
        self.seek.sliderPressed.connect(self.pause)
        self.seek.valueChanged.connect(self.seek_to)
        position.addWidget(self.seek, 1)
        self.counter = QLabel()
        self.counter.setObjectName("muted")
        self.counter.setMinimumWidth(74)
        self.counter.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        position.addWidget(self.counter)
        layout.addLayout(position)

        self.input.textChanged.connect(self.load_input)
        self.input.returnPressed.connect(self.toggle_playback)
        self.load_input()

    def make_menu(self):
        menu = QMenu(self)
        self.reset_action = menu.addAction("Сначала")
        self.reset_action.triggered.connect(lambda: self.seek_to(0))
        menu.addAction("Случайный пример", self.randomize)
        menu.addSeparator()
        speed_panel = QWidget(menu)
        speed_panel.setMinimumWidth(280)
        speed_layout = QVBoxLayout(speed_panel)
        speed_layout.setContentsMargins(20, 8, 20, 12)
        speed_layout.setSpacing(8)
        speed_heading = QHBoxLayout()
        speed_heading.addWidget(QLabel("Скорость"))
        speed_heading.addStretch()
        self.speed_value = QLabel("1×")
        self.speed_value.setObjectName("speedValue")
        self.speed_value.setMinimumWidth(48)
        self.speed_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        speed_heading.addWidget(self.speed_value)
        speed_layout.addLayout(speed_heading)
        self.speed_slider = SpeedSlider()
        self.speed_slider.valueChanged.connect(lambda index: self.change_speed(SPEED_PRESETS[index]))
        speed_layout.addWidget(self.speed_slider)
        self.speed_action = QWidgetAction(menu)
        self.speed_action.setDefaultWidget(speed_panel)
        menu.addAction(self.speed_action)
        menu.addSeparator()
        self.indices_action = menu.addAction("Показать индексы")
        self.indices_action.setCheckable(True)
        self.indices_action.setChecked(True)
        self.indices_action.toggled.connect(self.change_indices)
        self.comments_action = menu.addAction("Показать комментарии")
        self.comments_action.setCheckable(True)
        self.comments_action.setChecked(True)
        self.comments_action.toggled.connect(lambda shown: self.caption.setVisible(shown))
        self.stats_action = menu.addAction("Показать счётчики")
        self.stats_action.setCheckable(True)
        self.stats_action.toggled.connect(lambda shown: self.stats.setVisible(shown))
        menu.addSeparator()
        self.json_action = menu.addAction("Сохранить шаги JSON…")
        self.json_action.triggered.connect(self.export_json)
        self.export_action = menu.addAction("Экспорт видео…")
        self.export_action.triggered.connect(self.request_export)
        return menu

    def load_input(self):
        self.timer.stop()
        if self.timeline:
            self.timeline.pause()
        try:
            execution = self.algorithm.build(self.input_spec.parse(self.input.text()))
        except ValueError as exc:
            self.input_valid = False
            self.error.setText(str(exc))
            self.error.show()
            self.refresh()
            return
        self.input_valid = True
        self.execution = execution
        self.timeline = Timeline(execution)
        self.timeline.set_speed(self.playback_speed)
        self.error.hide()
        self.refresh()

    def randomize(self):
        self.input.setText(self.input_spec.random_input())

    def pause(self):
        if self.timeline:
            self.timeline.pause()
        self.timer.stop()
        self.refresh()

    def toggle_playback(self):
        if not self.input_valid:
            return
        if self.timeline.running:
            self.pause()
            return
        self.timeline.play()
        self.last_tick = perf_counter()
        if self.timeline.running:
            self.timer.start()
        self.refresh()

    def seek_to(self, position):
        if self.input_valid:
            self.timeline.seek(position)
            self.timer.stop()
            self.refresh()

    def step_back(self):
        if self.input_valid:
            self.timeline.backward()
            self.timer.stop()
            self.refresh()

    def step_forward(self):
        if self.input_valid:
            self.timeline.forward()
            self.timer.stop()
            self.refresh()

    def change_speed(self, speed):
        value = min(range(len(SPEED_PRESETS)), key=lambda index: abs(SPEED_PRESETS[index] - speed))
        speed = SPEED_PRESETS[value]
        blocked = self.speed_slider.blockSignals(True)
        self.speed_slider.setValue(value)
        self.speed_slider.blockSignals(blocked)
        self.speed_slider.describe_value(value)
        self.speed_value.setText(speed_label(speed))
        self.playback_speed = speed
        if self.timeline:
            self.timeline.set_speed(speed)

    def change_indices(self, shown):
        setter = getattr(self.canvas, "set_show_indices", None)
        if callable(setter):
            setter(shown)

    def tick(self):
        now = perf_counter()
        self.timeline.advance(min(0.1, max(0.0, now - self.last_tick)))
        self.last_tick = now
        if not self.timeline.running:
            self.timer.stop()
        self.refresh()

    def refresh(self):
        valid = self.input_valid and self.timeline is not None
        for widget in (self.play_button, self.seek, self.reset_action, self.json_action, self.export_action):
            widget.setEnabled(valid)
        self.previous_button.setEnabled(valid and (self.timeline.position > 0 or self.timeline.in_transition))
        self.next_button.setEnabled(valid and self.timeline.position < self.timeline.total)
        if self.timeline is None:
            return
        frame = self.timeline.frame()
        self.canvas.show_frame(frame)
        self.caption.setText(frame.step["description"] if frame.step else "Начальное состояние")
        self.stats.setText(self.visualization.statistics(frame.after))
        self.counter.setText(f"{frame.number} / {self.timeline.total}")
        self.seek.blockSignals(True)
        self.seek.setRange(0, self.timeline.total)
        self.seek.setValue(self.timeline.position)
        self.seek.blockSignals(False)
        if not valid:
            text = "Старт"
        elif self.timeline.running:
            text = "Пауза"
        elif self.timeline.position == self.timeline.total:
            text = "Повторить"
        elif self.timeline.position or self.timeline.in_transition:
            text = "Продолжить"
        else:
            text = "Старт"
        self.play_button.setText(text)

    def request_export(self):
        if self.input_valid:
            self.export_requested.emit(self.execution)

    def export_json(self):
        if not self.input_valid:
            return
        dialog = QFileDialog(self, "Сохранить шаги")
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setNameFilter("JSON (*.json)")
        dialog.setDefaultSuffix("json")
        dialog.selectFile(self.algorithm.id + ".json")
        if dialog.exec():
            try:
                Path(dialog.selectedFiles()[0]).write_text(
                    json.dumps(self.execution, ensure_ascii=False, indent=2), encoding="utf-8")
            except OSError as exc:
                QMessageBox.warning(self, "Не удалось сохранить шаги", str(exc))
