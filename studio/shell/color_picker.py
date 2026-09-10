"""Studio's own color picker - task "Studio: wyostrzenie stylu",
Problem 4.1: "Natywny próbnik koloru Windowsa nie pasuje do szaty
Studio [...] Ma wyglądać jak część Studio, nie jak okno systemowe."
Replaces QColorDialog everywhere Studio itself asks for a color (today:
canvas background, both editors - Problem 4.2).

Layout, literally per 4.1's own list:
  - a continuous hue/saturation FIELD (_HueSatWheel below) - a radial
    field (angle = hue, distance from center = saturation) rather than
    a square SV box, so hue and saturation are one gesture on one
    widget instead of two; brightness is the ONE dimension a 2D field
    can't also carry, so it gets its own control, per 4.1's own
    "suwak jasności OBOK" (a separate slider beside it, not folded in).
  - a vertical brightness QSlider beside the field.
  - an editable hex QLineEdit, kept in sync both directions.
  - current/new swatches side by side (4.1's own "podgląd").
  - a row of preset swatches underneath.
Styled via STUDIO_UI_STANDARD.md tokens directly (studio/shell/style.py
also styles QDialog#IndustrialDialog's own flat border, section 8).
"""
import math

from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSlider, QVBoxLayout, QWidget,
)

from studio.shell.i18n import tr

_PANEL_BG = "#D4D0C8"
_BEVEL_LIGHT = "#FFFFFF"
_BEVEL_SHADOW = "#808080"

# Problem 4.4 - "Neutralna, wg standardu — nie turkus": the standard's
# own field_bg (STUDIO_UI_STANDARD.md section 1) is the neutral default
# every NEW project/scene starts with - not Synoptic's own turquoise
# COLOR_CANVAS_BACKGROUND default, which stays reachable as a preset
# (below) for anyone who wants it back, per 4.4's own second sentence.
DEFAULT_CANVAS_BACKGROUND = "#FFFFFF"

# Presets row: the Studio chrome palette itself (so "match the app" is
# one click) plus a small set of neutral canvas tones, TURQUOISE
# included on purpose (4.4: "łącznie z turkusem, jeśli tak woli").
_PRESETS = [
    "#FFFFFF", "#D4D0C8", "#C0C0C0", "#F5F5F0",
    "#E8E4DC", "#00CFCF", "#EAF6F6", "#1E1E1E",
]


class _Swatch(QPushButton):
    """A flat color block with a sunken Win98 border - not a native
    push-button look (a color swatch is not a command), so its own QSS
    overrides the button chrome entirely, same technique
    main_window.py's _AspectContainer already uses for other flat
    chrome pieces."""

    clicked_with_color = Signal(QColor)

    def __init__(self, size=28, color="#FFFFFF", parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._color = QColor(color)
        self._apply_style()
        self.clicked.connect(lambda: self.clicked_with_color.emit(self._color))

    def set_color(self, color: QColor):
        self._color = QColor(color)
        self._apply_style()

    def color(self) -> QColor:
        return QColor(self._color)

    def _apply_style(self):
        self.setStyleSheet(
            f"QPushButton {{ background-color: {self._color.name()}; "
            f"border: 2px solid; border-top-color: {_BEVEL_SHADOW}; "
            f"border-left-color: {_BEVEL_SHADOW}; border-right-color: {_BEVEL_LIGHT}; "
            f"border-bottom-color: {_BEVEL_LIGHT}; }}"
        )


class _HueSatWheel(QWidget):
    """Continuous hue (angle) x saturation (radius) field - Problem
    4.1's own "płynne pole barwy (odcień + nasycenie), wybór ciągły,
    nie z listy". Brightness is a separate parameter (set_value()),
    supplied by the dialog's own vertical slider - this widget only
    ever draws at ONE fixed brightness at a time, matching what a real
    HSV color wheel looks like at that brightness.

    The wheel bitmap is cached and only rebuilt when brightness changes
    (set_value()) - a drag across the wheel itself (mouse move) only
    moves the marker and re-emits, no per-frame pixel regeneration."""

    hueSatChanged = Signal(int, int)  # hue 0-359, sat 0-255

    SIZE = 176

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self._hue = 0
        self._sat = 0
        self._value = 255
        self._cache = QPixmap()
        self._rebuild_cache()

    def set_value(self, value: int):
        if value != self._value:
            self._value = value
            self._rebuild_cache()
            self.update()

    def set_hue_sat(self, hue: int, sat: int, emit: bool = True):
        self._hue, self._sat = hue, sat
        self.update()
        if emit:
            self.hueSatChanged.emit(hue, sat)

    def _center_radius(self):
        c = self.SIZE / 2
        return c, c, c - 2

    def _rebuild_cache(self):
        img = QImage(self.SIZE, self.SIZE, QImage.Format.Format_RGB32)
        img.fill(QColor(_PANEL_BG))
        cx, cy, radius = self._center_radius()
        for y in range(self.SIZE):
            dy = y - cy
            for x in range(self.SIZE):
                dx = x - cx
                dist = math.hypot(dx, dy)
                if dist > radius:
                    continue
                angle = (math.degrees(math.atan2(dy, dx)) + 360.0) % 360.0
                sat = min(255, round(dist / radius * 255))
                img.setPixelColor(x, y, QColor.fromHsv(round(angle), sat, self._value))
        self._cache = QPixmap.fromImage(img)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawPixmap(0, 0, self._cache)

        cx, cy, radius = self._center_radius()
        angle_rad = math.radians(self._hue)
        r = self._sat / 255.0 * radius
        mx = cx + r * math.cos(angle_rad)
        my = cy + r * math.sin(angle_rad)
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPoint(round(mx), round(my)), 5, 5)
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawEllipse(QPoint(round(mx), round(my)), 6, 6)

    def mousePressEvent(self, event):
        self._handle(event.position().x(), event.position().y())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._handle(event.position().x(), event.position().y())

    def _handle(self, x, y):
        cx, cy, radius = self._center_radius()
        dx, dy = x - cx, y - cy
        dist = min(radius, math.hypot(dx, dy))
        angle = (math.degrees(math.atan2(dy, dx)) + 360.0) % 360.0
        sat = round(dist / radius * 255)
        self.set_hue_sat(round(angle), sat)


class StudioColorDialog(QDialog):
    """The dialog itself - see module docstring for the layout. Use the
    static get_color() below rather than constructing this directly."""

    def __init__(self, initial: QColor, parent=None):
        super().__init__(parent)
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("color_picker.title"))
        self.setStyleSheet(f"QDialog#IndustrialDialog {{ background: {_PANEL_BG}; border: 2px solid #000000; }}")
        self._result_color = QColor(initial)

        root = QVBoxLayout(self)
        top = QHBoxLayout()

        self._wheel = _HueSatWheel()
        self._wheel.hueSatChanged.connect(self._on_hue_sat_changed)
        top.addWidget(self._wheel)

        self._value_slider = QSlider(Qt.Orientation.Vertical)
        self._value_slider.setRange(0, 255)
        self._value_slider.valueChanged.connect(self._on_value_changed)
        top.addWidget(self._value_slider)

        right = QVBoxLayout()
        grid = QGridLayout()
        grid.addWidget(QLabel(tr("color_picker.current_label")), 0, 0)
        grid.addWidget(QLabel(tr("color_picker.new_label")), 0, 1)
        self._current_swatch = _Swatch(size=48, color=initial.name())
        self._new_swatch = _Swatch(size=48, color=initial.name())
        grid.addWidget(self._current_swatch, 1, 0)
        grid.addWidget(self._new_swatch, 1, 1)
        right.addLayout(grid)

        hex_row = QHBoxLayout()
        hex_row.addWidget(QLabel(tr("color_picker.hex_label")))
        self._hex_edit = QLineEdit()
        self._hex_edit.setMaximumWidth(90)
        self._hex_edit.editingFinished.connect(self._on_hex_edited)
        hex_row.addWidget(self._hex_edit)
        hex_row.addStretch(1)
        right.addLayout(hex_row)
        right.addStretch(1)
        top.addLayout(right)

        root.addLayout(top)

        root.addWidget(QLabel(tr("color_picker.presets_label")))
        preset_row = QHBoxLayout()
        for hex_value in _PRESETS:
            swatch = _Swatch(size=22, color=hex_value)
            swatch.clicked_with_color.connect(lambda c: self._set_color(c, update_wheel=True))
            preset_row.addWidget(swatch)
        preset_row.addStretch(1)
        root.addLayout(preset_row)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        ok_button = QPushButton(tr("color_picker.ok"))
        ok_button.setDefault(True)
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton(tr("color_picker.cancel"))
        cancel_button.clicked.connect(self.reject)
        button_row.addWidget(ok_button)
        button_row.addWidget(cancel_button)
        root.addLayout(button_row)

        self._set_color(initial, update_wheel=True)

    def _set_color(self, color: QColor, update_wheel: bool):
        self._result_color = QColor(color)
        self._new_swatch.set_color(self._result_color)
        self._hex_edit.setText(self._result_color.name().upper())
        if update_wheel:
            hue, sat, value, _ = self._result_color.getHsv()
            self._value_slider.blockSignals(True)
            self._value_slider.setValue(value)
            self._value_slider.blockSignals(False)
            self._wheel.set_value(value)
            self._wheel.set_hue_sat(max(hue, 0), sat, emit=False)

    def _on_hue_sat_changed(self, hue, sat):
        self._set_color(QColor.fromHsv(hue, sat, self._value_slider.value()), update_wheel=False)

    def _on_value_changed(self, value):
        self._wheel.set_value(value)
        hue = max(self._wheel._hue, 0)
        self._set_color(QColor.fromHsv(hue, self._wheel._sat, value), update_wheel=False)

    def _on_hex_edited(self):
        text = self._hex_edit.text().strip()
        if text and not text.startswith("#"):
            text = "#" + text
        color = QColor(text)
        if color.isValid():
            self._set_color(color, update_wheel=True)
        else:
            self._hex_edit.setText(self._result_color.name().upper())

    def selected_color(self) -> QColor:
        return QColor(self._result_color)

    @staticmethod
    def get_color(initial, parent=None):
        """initial: a QColor or "#RRGGBB" string. Returns a QColor, or
        None if the dialog was cancelled - same calling convention as
        QColorDialog.getColor() had, so call sites read the same way."""
        dialog = StudioColorDialog(QColor(initial), parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.selected_color()
        return None
