from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout, QGraphicsItem, QGraphicsObject
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPolygonF, QPainterPath
from PySide6.QtCore import Qt, QRect, QPointF, Signal, QTimer
from epw_os.gui.widgets.popups import DeviceControlPopup
from epw_os.i18n import tr


def _wrap_to_two_lines(text, metrics, max_width):
    """Word-wrap `text` into at most 2 lines that each fit within
    max_width (device pixels), eliding the 2nd line if there's a 3rd
    line's worth of content left over. Used for Breaker/Contactor's
    description label - Control Outputs' Description column has no
    length limit, so this has to stay robust for an arbitrarily long
    operator-entered string, not just today's default descriptions."""
    words = text.split()
    if not words:
        return [""]

    lines = []
    current = ""
    i = 0
    while i < len(words) and len(lines) < 2:
        candidate = f"{current} {words[i]}".strip()
        if not current or metrics.horizontalAdvance(candidate) <= max_width:
            current = candidate
            i += 1
        else:
            lines.append(current)
            current = ""
    if current:
        lines.append(current)
    if not lines:
        lines = [""]

    if i < len(words):
        # More text than fits in 2 lines - elide the last one instead of
        # silently dropping the remainder or growing a 3rd line.
        remainder = " ".join(words[i:])
        lines[-1] = metrics.elidedText(f"{lines[-1]} {remainder}", Qt.TextElideMode.ElideRight, max_width)
    return lines

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

class Wire(SynopticWidget):
    def __init__(self, orientation="H", length=100, tag_name="", parent=None):
        super().__init__(tag_name, parent)
        self.orientation = orientation
        self.length = length
        if orientation == "H":
            self.setFixedSize(length, 10)
        else:
            self.setFixedSize(10, length)

        self.animation_offset = 0
        self.current_flow = 0.0 # Proportional speed

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_power_flow)
        self.timer.start(50)

    def animate_power_flow(self):
        if self.voltage_present:
            speed = 2
            if self.current_flow > 50.0: speed = 4
            if self.current_flow > 100.0: speed = 6
            self.animation_offset = (self.animation_offset + speed) % 20
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.fault:
            color = QColor("red")
        elif self.voltage_present:
            color = QColor("green")
        else:
            color = QColor("black")

        pen = QPen(color, 4)
        painter.setPen(pen)

        if self.orientation == "H":
            painter.drawLine(0, 5, self.width(), 5)
            # Power flow dots
            if self.voltage_present:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(100, 255, 100))
                for i in range(self.animation_offset, self.width(), 20):
                    painter.drawEllipse(i-2, 3, 4, 4)
        else:
            painter.drawLine(5, 0, 5, self.height())
            if self.voltage_present:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(100, 255, 100))
                for i in range(self.animation_offset, self.height(), 20):
                    painter.drawEllipse(3, i-2, 4, 4)

class Busbar(SynopticWidget):
    def __init__(self, length=200, tag_name="", parent=None):
        super().__init__(tag_name, parent)
        self.length = length
        self.setFixedSize(length, 16)

    def paintEvent(self, event):
        painter = QPainter(self)
        color = QColor("green") if self.voltage_present else QColor("black")
        painter.fillRect(0, 0, self.width(), self.height(), color)

class Breaker(SynopticWidget):
    def __init__(self, tag_name="", parent=None):
        super().__init__(tag_name, parent)
        # Widened/heightened from the original 100x60 (Task: the
        # description label was getting cut off mid-word for anything
        # longer than a couple of short words, e.g. "Digital Output
        # Channel 1", which at the default 7pt Tahoma needs ~126px just
        # for "Digital Output" alone - measured with QFontMetrics, not
        # guessed) - the symbol itself (box/contacts/blade, all drawn at
        # x<=38) is untouched, this only grows the label area to its
        # right and gives the wrapped 2nd line room at the bottom.
        self.setFixedSize(190, 76)
        self.animation_step = 0
        self.target_state = self.state

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.animate_transition)

    def start_transition_animation(self, new_state):
        self.target_state = new_state
        self.anim_timer.start(20) # 20ms * 10 steps = 200ms

    def animate_transition(self):
        if self.state != self.target_state:
            # Simulate mechanical move
            self.animation_step += 1
            if self.animation_step >= 10:
                self.state = self.target_state
                self.animation_step = 0
                self.anim_timer.stop()
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw labels
        painter.setPen(QPen(QColor("black")))
        painter.setFont(QFont("Tahoma", 10, QFont.Weight.Bold))
        painter.drawText(40, 30, self.tag_name)
        painter.setFont(QFont("Tahoma", 7))
        # Word-wrapped to 2 lines instead of a single drawText() call
        # that silently ran off the widget's right edge for anything
        # longer than ~2 short words - see _wrap_to_two_lines() above.
        max_text_width = self.width() - 44
        for i, line in enumerate(_wrap_to_two_lines(self.description, painter.fontMetrics(), max_text_width)):
            painter.drawText(40, 45 + i * 10, line)

        # Connections
        pen = QPen(QColor("green") if self.voltage_present else QColor("black"), 4)
        painter.setPen(pen)
        painter.drawLine(20, 0, 20, 15)
        painter.drawLine(20, 45, 20, 60)

        # Contacts
        painter.setPen(QPen(QColor("black"), 2))
        painter.drawEllipse(17, 15, 6, 6)
        painter.drawEllipse(17, 39, 6, 6)

        # Blade
        # Command pending/feedback waiting indicators
        if self.command_pending or self.feedback_waiting:
            blade_pen = QPen(QColor("orange"), 3)
        else:
            blade_pen = QPen(QColor("black"), 3)

        painter.setPen(blade_pen)

        # Calculate angle for animation
        if self.state == 1 and self.animation_step == 0:
            painter.drawLine(20, 21, 20, 39)
        elif self.state == 0 and self.animation_step == 0:
            painter.drawLine(20, 39, 35, 15)
        else:
            if self.target_state == 1:
                x = 35 - (15 * (self.animation_step / 10.0))
                y = 15 + (6 * (self.animation_step / 10.0))
                painter.drawLine(20, 39, int(x), int(y))
            else:
                x = 20 + (15 * (self.animation_step / 10.0))
                y = 21 - (6 * (self.animation_step / 10.0))
                painter.drawLine(20, 39, int(x), int(y))

        # Box
        painter.setPen(QPen(QColor("gray"), 2, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(2, 5, 36, 50)

class Contactor(Breaker):
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setPen(QPen(QColor("blue"), 2))
        painter.drawRect(25, 25, 10, 10)
        painter.drawLine(25, 25, 35, 35)

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

class DigitalIndicator(SynopticWidget):
    def __init__(self, unit="", title="", tag_name="", parent=None):
        super().__init__(tag_name, parent)
        self.unit = unit
        self.title = title
        self.value = 0.0
        self.quality = "GOOD"
        # Task: podpowiedzi - "pelna nazwa wielkosci i jednostka". Set by
        # the caller via set_base_tooltip() (page_entry_gate.py's
        # MeasurementPanel knows what each tile actually measures; this
        # widget only knows a short abbreviation + unit). Preserved
        # across every update_value() call instead of being overwritten
        # by the quality-specific note below - see _apply_tooltip().
        self.base_tooltip = ""
        self.setFixedSize(80, 40)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)

        self.lbl_title = QLabel(self.title)
        self.lbl_title.setFont(QFont("Tahoma", 7, QFont.Weight.Normal))
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_value = QLabel(f"0.0 {self.unit}")
        self.lbl_value.setObjectName("LCD")
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_value)

    def set_base_tooltip(self, text: str):
        """Explains what this tile actually measures (full quantity name
        + unit) - the tile face itself only has room for a short
        abbreviation. Applied immediately and preserved across every
        future update_value() call - see _apply_tooltip()."""
        self.base_tooltip = text
        self._apply_tooltip("")

    def _apply_tooltip(self, quality_note: str):
        """base_tooltip (what this IS) is always shown; quality_note (why
        the value looks the way it does right now - simulated, no
        reading) is appended only when there's something to say, so a
        normal GOOD reading's tooltip is just the plain explanation."""
        if quality_note:
            self.setToolTip(f"{self.base_tooltip}\n{quality_note}" if self.base_tooltip else quality_note)
        else:
            self.setToolTip(self.base_tooltip)

    def update_value(self, value, quality="GOOD"):
        self.value = value
        self.quality = quality

        if quality == "BAD":
            self.lbl_value.setText(f"---.- {self.unit}")
            self.lbl_value.setStyleSheet("background-color: black; color: red; border: 2px inset #808080; font-weight: bold; font-size: 12px;")
            self._apply_tooltip("")
        elif quality == "SIMULATED":
            # Task: a value with no physical sensor/meter behind it (see
            # page_entry_gate.py's recalculate_electricity()) must not look
            # identical to a real measurement - amber, distinct from both
            # the real-data green and the fault-data red above, plus a
            # tooltip spelling out why.
            self.lbl_value.setText(f"{value:.1f} {self.unit}")
            self.lbl_value.setStyleSheet("background-color: black; color: #FFA500; border: 2px inset #808080; font-weight: bold; font-size: 12px;")
            self._apply_tooltip(tr("pages.common.simulated_value_tooltip"))
        else:
            self.lbl_value.setText(f"{value:.1f} {self.unit}")
            self.lbl_value.setStyleSheet("background-color: black; color: #00FF00; border: 2px inset #808080; font-weight: bold; font-size: 12px;")
            self._apply_tooltip("")

class Transformer(SynopticWidget):
    def __init__(self, tag_name="", parent=None):
        super().__init__(tag_name, parent)
        self.setFixedSize(40, 60)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(QColor("black"), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.drawEllipse(10, 10, 20, 20)
        painter.drawEllipse(10, 30, 20, 20)

        painter.drawLine(20, 0, 20, 10)
        painter.drawLine(20, 50, 20, 60)
