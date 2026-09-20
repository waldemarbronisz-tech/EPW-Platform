"""The two synoptic widgets the panel still draws with: SynopticWidget
(the tag-bound base) and Lamp (the LED in the Digital Inputs and
Control Outputs tables).

This module used to hold a whole one-line-diagram kit as well - wire,
busbar, breaker, contactor, transformer, digital indicator - drawn
only by the hand-built Main View page. That page is gone (the Main
View is the embedded Synoptic screen now, where symbols come from the
editor's own library), and so is the kit: nothing else ever used it.
"""
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout, QGraphicsItem, QGraphicsObject
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPolygonF, QPainterPath
from PySide6.QtCore import Qt, QRect, QPointF, Signal, QTimer
from epw_os.i18n import tr


class SynopticWidget(QWidget):
    request_control = Signal(object)

    def __init__(self, tag_name="", parent=None):
        super().__init__(parent)
        self.tag_name = tag_name
        self.name = tag_name
        self.description = f"Device {tag_name}"
        self.state = 0
        self.voltage_present = False
        self.fault = False
        self.remote_enabled = True
        self.alarm = "None"
        self.animation = "Enabled"
        self.communication = "OK"
        self.op_counter = 0
        self.last_op_time = "N/A"

        # New states for commands
        self.command_pending = False
        self.feedback_waiting = False

    def update_state(self, value):
        self.state = value
        self.update()

    def update_voltage(self, present):
        self.voltage_present = present
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.request_control.emit((self, event.globalPosition().toPoint()))

class Lamp(SynopticWidget):
    def __init__(self, color_on="green", tag_name="", parent=None):
        super().__init__(tag_name, parent)
        self.color_on = QColor(color_on)
        self.setFixedSize(30, 30)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = self.color_on if self.state == 1 else QColor("darkgray")

        # Geometry derived from the widget's actual size (not hardcoded for
        # the 30x30 default) so the lamp stays a true circle - never clipped
        # into a flat-edged blob - at whatever size a page sets it to
        # (e.g. the 20x20 DI table LEDs or the 16x16 pulse indicators).
        pen_width = 2
        margin = pen_width  # keep the pen stroke fully inside the widget
        diameter = max(min(self.width(), self.height()) - margin * 2, 1)
        cx = (self.width() - diameter) // 2
        cy = (self.height() - diameter) // 2

        painter.setBrush(color)
        painter.setPen(QPen(Qt.GlobalColor.black, pen_width))
        painter.drawEllipse(cx, cy, diameter, diameter)

        if self.state == 1:
            hl_d = max(int(diameter * 0.3), 2)
            hl_off = int(diameter * 0.2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 150))
            painter.drawEllipse(cx + hl_off, cy + hl_off, hl_d, hl_d)

