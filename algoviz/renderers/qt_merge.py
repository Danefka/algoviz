"""One canvas paints the persistent recursion tree and its travelling copies."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from .merge_layout import (
    CELL_HEIGHT, CELL_WIDTH, VIEW_TOP, visual_merge,
)


class MergeCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.frame = None
        self.picture = None
        self.show_indices = True
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAccessibleName("Дерево разбиений и сборки массива")

    def show_frame(self, frame):
        self.frame = frame
        self.picture = visual_merge(frame)
        self.update()

    def set_show_indices(self, shown):
        self.show_indices = bool(shown)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        if self.picture is None:
            painter.end()
            return
        scale = min((self.width() - 24) / self.picture.width, (self.height() - 12) / self.picture.height)
        origin_x = self.width() / 2
        origin_y = (self.height() - self.picture.height * scale) / 2 - VIEW_TOP * scale
        for edge in self.picture.edges:
            painter.setOpacity(edge.opacity)
            painter.setPen(QPen(QColor("#DFE4EB"), 1.2))
            painter.drawLine(QPointF(origin_x + edge.x1 * scale, origin_y + edge.y1 * scale),
                             QPointF(origin_x + edge.x2 * scale, origin_y + edge.y2 * scale))
        font = QFont(self.font())
        font.setPixelSize(max(11, min(24, int(scale * 0.36))))
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        for cell in self.picture.cells:
            painter.setOpacity(cell.opacity)
            color = QColor(cell.color)
            fill = QColor(color)
            fill.setAlpha(18 if cell.role in ("normal", "empty") else 25)
            painter.setBrush(fill)
            painter.setPen(QPen(color, 1.3))
            rect = QRectF(origin_x + (cell.x - CELL_WIDTH / 2) * scale,
                          origin_y + (cell.y - CELL_HEIGHT / 2) * scale,
                          CELL_WIDTH * scale, CELL_HEIGHT * scale)
            painter.drawRoundedRect(rect, 6, 6)
            if cell.value is not None:
                painter.setOpacity(cell.opacity * cell.text_opacity)
                painter.setPen(QColor("#24262B"))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(cell.value))
        painter.setOpacity(1)
        font.setWeight(QFont.Weight.Normal)
        for label in self.picture.labels:
            if label.kind == "index" and not self.show_indices:
                continue
            painter.setOpacity(label.opacity)
            font.setPixelSize(max(9, min(11, int(scale * 0.22))) if label.kind == "index" else 12)
            painter.setFont(font)
            painter.setPen(QColor("#878C96" if label.kind == "index" else "#6D737D"))
            rect = QRectF(origin_x + label.x * scale - 80,
                          origin_y + label.y * scale - 9, 160, 18)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label.text)
        painter.end()
