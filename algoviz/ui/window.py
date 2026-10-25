from PySide6.QtWidgets import QMainWindow, QStackedWidget

from ..registry import get_algorithm
from .home import HomePage
from .player import PlayerPage
from .export_dialog import ExportDialog
from .theme import STYLESHEET


class MainWindow(QMainWindow):
    """Navigation only. Algorithms and rendering live in their own modules."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Algo Lab")
        self.resize(960, 660)
        self.setMinimumSize(760, 560)
        self.setStyleSheet(STYLESHEET)
        self.closing = False
        self.pages = {}
        self.stack = QStackedWidget()
        self.home = HomePage()
        self.home.algorithm_selected.connect(self.open_algorithm)
        self.stack.addWidget(self.home)
        self.setCentralWidget(self.stack)
        self.export_dialog = ExportDialog(self)
        self.export_dialog.export_finished.connect(self.export_finished)

    def pause_current(self):
        page = self.stack.currentWidget()
        if isinstance(page, PlayerPage):
            page.pause()

    def open_algorithm(self, algorithm_id):
        self.pause_current()
        if algorithm_id not in self.pages:
            page = PlayerPage(get_algorithm(algorithm_id))
            page.go_home.connect(self.show_home)
            page.export_requested.connect(self.show_export)
            self.pages[algorithm_id] = page
            self.stack.addWidget(page)
        self.stack.setCurrentWidget(self.pages[algorithm_id])
        self.setWindowTitle(self.pages[algorithm_id].algorithm.title + " — Algo Lab")
        return self.pages[algorithm_id]

    def show_home(self):
        self.pause_current()
        self.stack.setCurrentWidget(self.home)
        self.setWindowTitle("Algo Lab")

    def show_export(self, execution):
        # While a job runs, reopening shows its progress without replacing it.
        self.export_dialog.capture(execution)
        self.export_dialog.show()
        self.export_dialog.raise_()
        self.export_dialog.activateWindow()

    def export_finished(self):
        if self.closing:
            self.close()

    def closeEvent(self, event):
        self.pause_current()
        if self.export_dialog.process is not None:
            self.closing = True
            self.export_dialog.closing = True
            self.export_dialog.cancel_render()
            event.ignore()
            return
        self.export_dialog.close()
        event.accept()
