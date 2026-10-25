from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QFrame, QLabel, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from ..registry import list_algorithms


class HomePage(QWidget):
    algorithm_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(36, 32, 36, 32)
        outer.addStretch(1)
        content = QWidget()
        content.setMaximumWidth(580)
        content.setMinimumWidth(400)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.back_button = QPushButton("← Алгоритмы")
        self.back_button.setObjectName("quiet")
        self.back_button.clicked.connect(self.show_categories)
        layout.addWidget(self.back_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.title = QLabel("Алгоритмы")
        self.title.setObjectName("title")
        layout.addWidget(self.title)
        layout.addSpacing(22)
        self.category_stack = QStackedWidget()
        self.root_page, root_rows = self.make_listing()
        self.category_stack.addWidget(self.root_page)
        layout.addWidget(self.category_stack)
        self.buttons = {}
        self.category_buttons = {}
        self.category_pages = {}
        categories = {}
        for algorithm in list_algorithms():
            categories.setdefault(algorithm.category, []).append(algorithm)
        for category, algorithms in categories.items():
            folder = QPushButton(category)
            folder.setObjectName("algorithm")
            folder.clicked.connect(lambda checked=False, name=category: self.show_category(name))
            root_rows.addWidget(folder)
            self.category_buttons[category] = folder
            page, rows = self.make_listing()
            self.category_pages[category] = page
            self.category_stack.addWidget(page)
            for algorithm in algorithms:
                button = QPushButton(algorithm.title)
                button.setObjectName("algorithm")
                button.setToolTip(algorithm.description)
                button.setAccessibleName(algorithm.title)
                button.clicked.connect(lambda checked=False, key=algorithm.id: self.algorithm_selected.emit(key))
                rows.addWidget(button)
                self.buttons[algorithm.id] = button
            rows.addStretch()
        root_rows.addStretch()
        outer.addWidget(content, 2, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(1)
        self.show_categories()

    @staticmethod
    def make_listing():
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumHeight(230)
        listing = QWidget()
        rows = QVBoxLayout(listing)
        rows.setContentsMargins(0, 0, 0, 0)
        rows.setSpacing(10)
        scroll.setWidget(listing)
        return scroll, rows

    def show_category(self, category):
        self.category_stack.setCurrentWidget(self.category_pages[category])
        self.title.setText(category)
        self.back_button.show()

    def show_categories(self):
        self.category_stack.setCurrentWidget(self.root_page)
        self.title.setText("Алгоритмы")
        self.back_button.hide()
