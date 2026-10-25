"""Small, immediate Qt renderer for the same execution that Manim exports."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..playback import Frame
from .array_layout import COLORS, array_geometry, visual_cells, visual_guides


class ArrayCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.frame = None
        self.cells = []
        self.guides = None
        self.show_indices = True
        self.setMinimumSize(400, 260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAccessibleName("Анимация массива")

    def show_frame(self, frame: Frame):
        self.frame = frame
        self.cells = visual_cells(frame)
        self.guides = visual_guides(frame)
        self.update()

    def set_show_indices(self, shown: bool):
        self.show_indices = bool(shown)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        if self.frame is None:
            painter.end()
            return

        count = len(self.cells)
        width, height = float(self.width()), float(self.height())
        geometry = array_geometry(width, height, count)
        cell_width, cell_height = geometry.cell_width, geometry.cell_height
        start_x, center_y = geometry.start_x, geometry.center_y

        font = QFont(self.font())
        font.setPixelSize(12)
        painter.setFont(font)
        painter.setPen(QColor("#9A9EA5"))
        if self.show_indices:
            for index in range(count):
                rect = QRectF(start_x + index * geometry.stride, geometry.index_y, cell_width, 16)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(index))

        if self.guides.active_range is not None:
            lo, hi = self.guides.active_range
            left = start_x + lo * geometry.stride
            right = start_x + (hi - 1) * geometry.stride + cell_width
            y = geometry.range_y
            painter.setPen(QPen(QColor(COLORS["pivot"]), 1.3))
            painter.drawLine(QPointF(left, y + 5), QPointF(left, y))
            painter.drawLine(QPointF(left, y), QPointF(right, y))
            painter.drawLine(QPointF(right, y), QPointF(right, y + 5))
            if self.guides.pivot_value is not None:
                painter.drawText(QRectF(start_x, y - 22, width - 2 * start_x, 18),
                                 Qt.AlignmentFlag.AlignCenter, f"Опора: {self.guides.pivot_value}")
        for index, names in self.guides.pointers:
            painter.setPen(QColor(COLORS["pivot"]))
            marker_font = QFont(font)
            marker_font.setPixelSize(11)
            painter.setFont(marker_font)
            painter.drawText(QRectF(start_x + index * geometry.stride - 3,
                                   geometry.pointer_y, cell_width + 6, 16),
                             Qt.AlignmentFlag.AlignCenter, names)

        if not count:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Пустой массив")

        font.setPixelSize(max(13, min(28, int(cell_width * 0.47))))
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        for cell in self.cells:
            rect = QRectF(start_x + cell.slot * geometry.stride,
                          center_y - cell_height / 2 + cell.lift * geometry.lift_height,
                          cell_width, cell_height)
            color = QColor(COLORS[cell.role])
            painter.setOpacity(cell.opacity)
            fill = QColor(color)
            fill.setAlpha(18 if cell.role == "normal" else 22)
            painter.setBrush(fill)
            painter.setPen(QPen(QColor(COLORS["pivot"]) if cell.pivot else color,
                                2.4 if cell.pivot else 1.3))
            painter.drawRoundedRect(rect, 10.0, 10.0)
            painter.setPen(QColor(COLORS["pivot"] if cell.pivot else "#24262B"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(cell.value))
        painter.end()
