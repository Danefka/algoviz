"""Generic Qt painter for composed structure views."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget


class CompositeCanvas(QWidget):
    def __init__(self, layout, parent=None):
        super().__init__(parent)
        self.layout_fn = layout
        self.picture = self.frame = None
        self.show_indices = True
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAccessibleName("Совместная визуализация структур данных")

    def show_frame(self, frame):
        self.frame = frame
        self.picture = self.layout_fn(frame)
        self.update()

    def set_show_indices(self, shown):
        self.show_indices = bool(shown)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        picture = self.picture
        if picture is None:
            painter.end()
            return
        scale = min((self.width() - 24) / picture.width, (self.height() - 12) / picture.height)
        origin_x = self.width() / 2
        origin_y = (self.height() - picture.height * scale) / 2 - picture.top * scale
        for line in picture.lines:
            painter.setPen(QPen(QColor("#DDE2E9"), 1.5))
            painter.drawLine(QPointF(origin_x + line.x1 * scale, origin_y + line.y1 * scale),
                             QPointF(origin_x + line.x2 * scale, origin_y + line.y2 * scale))
        font = QFont(self.font())
        font.setPixelSize(max(11, min(27, int(scale * 0.37))))
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        for cell in picture.cells:
            painter.setOpacity(cell.opacity)
            color = QColor(cell.color)
            fill = QColor(color)
            fill.setAlpha(23)
            painter.setPen(QPen(color, 1.4))
            painter.setBrush(fill)
            rect = QRectF(origin_x + (cell.x - cell.width / 2) * scale,
                          origin_y + (cell.y - cell.height / 2) * scale,
                          cell.width * scale, cell.height * scale)
            painter.drawRoundedRect(rect, 5, 5)
            painter.setPen(QColor("#24262B"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(cell.value))
        font.setWeight(QFont.Weight.Normal)
        for label in picture.labels:
            if label.kind == "index" and not self.show_indices:
                continue
            painter.setOpacity(label.opacity)
            font.setPixelSize(10 if label.kind == "index" else 12)
            painter.setFont(font)
            painter.setPen(QColor("#878C96"))
            rect = QRectF(origin_x + label.x * scale - 75, origin_y + label.y * scale - 9, 150, 18)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label.text)
        painter.end()
