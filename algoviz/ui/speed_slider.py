"""Five labelled stops with native slider keyboard and accessibility support."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSlider

from ..playback import SPEED_PRESETS


def speed_label(speed):
    return f"{speed:g}×".replace(".", ",")


class SpeedSlider(QSlider):
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setRange(0, len(SPEED_PRESETS) - 1)
        self.setSingleStep(1)
        self.setPageStep(1)
        self.setValue(SPEED_PRESETS.index(1.0))
        self.setMinimumWidth(236)
        self.setFixedHeight(58)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Скорость воспроизведения")
        self.setToolTip("Выбери одну из пяти скоростей")
        self.valueChanged.connect(self.describe_value)
        self.describe_value(self.value())

    def describe_value(self, index):
        self.setAccessibleDescription("Скорость: " + speed_label(SPEED_PRESETS[index]))

    def stop_x(self, index):
        return 24.0 + (self.width() - 48.0) * index / self.maximum()

    def select_at(self, x):
        fraction = (x - 24.0) / max(1.0, self.width() - 48.0)
        index = int(max(0.0, min(1.0, fraction)) * self.maximum() + 0.5)
        self.setSliderPosition(index)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self.setSliderDown(True)
            self.select_at(event.position().x())
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.isSliderDown():
            self.select_at(event.position().x())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isSliderDown():
            self.select_at(event.position().x())
            self.setSliderDown(False)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        y = 16.0
        active, inactive = QColor("#292D35"), QColor("#E2E5EA")
        painter.setPen(QPen(inactive, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(self.stop_x(0), y), QPointF(self.stop_x(self.maximum()), y))
        painter.setPen(QPen(active, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(self.stop_x(0), y), QPointF(self.stop_x(self.value()), y))
        font = QFont(self.font())
        font.setPixelSize(11)
        for index, speed in enumerate(SPEED_PRESETS):
            x = self.stop_x(index)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(active if index <= self.value() else inactive)
            painter.drawEllipse(QPointF(x, y), 3, 3)
            font.setWeight(QFont.Weight.DemiBold if index == self.value() else QFont.Weight.Normal)
            painter.setFont(font)
            painter.setPen(active if index == self.value() else QColor("#878C96"))
            painter.drawText(QRectF(x - 24, 33, 48, 18), Qt.AlignmentFlag.AlignCenter, speed_label(speed))
        x = self.stop_x(self.value())
        if self.hasFocus():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#DFE3E9"))
            painter.drawEllipse(QPointF(x, y), 11, 11)
        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.setBrush(active)
        painter.drawEllipse(QPointF(x, y), 8, 8)
        painter.end()
