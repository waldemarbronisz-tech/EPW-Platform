from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QSlider, QFrame, QSizePolicy
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath
import math
from epw_os.i18n import tr
from epw_os.core.tag_manager import TagQuality
from epw_os.gui.theme_manager import get_theme_manager, current_colors

class WaveformWidget(QWidget):
    def __init__(self, title, colors, parent=None):
        super().__init__(parent)
        self.title = title
        self.colors = colors
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.phase_offset = 0
        self.amplitude = 100.0
        self.frequency = 50.0
        self.noise = 0.0
        self.harmonics = 0.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(50)

    def animate(self):
        self.phase_offset += (self.frequency / 50.0) * 10
        if self.phase_offset > 360:
            self.phase_offset -= 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), Qt.GlobalColor.black)

        # Grid
        painter.setPen(QPen(QColor(50, 50, 50), 1))
        for i in range(1, 10):
            y = int(self.height() * i / 10)
            painter.drawLine(0, y, self.width(), y)

        # Title
        painter.setPen(Qt.GlobalColor.white)
        painter.drawText(5, 15, self.title)

        center_y = self.height() / 2

        import random

        for idx, color in enumerate(self.colors):
            path = QPainterPath()
            painter.setPen(QPen(QColor(color), 2))

            phase_shift = idx * 120

            for x in range(self.width()):
                # Calculate basic sine
                angle = math.radians((x * 2) + self.phase_offset + phase_shift)
                y_val = math.sin(angle) * (self.amplitude * 0.4)

                # Add harmonics
                if self.harmonics > 0:
                    y_val += math.sin(angle * 3) * (self.amplitude * 0.4 * (self.harmonics/100.0))

                # Add noise
                if self.noise > 0:
                    y_val += random.uniform(-self.noise, self.noise) * 0.5

                if x == 0:
                    path.moveTo(x, center_y - y_val)
                else:
                    path.lineTo(x, center_y - y_val)

            painter.drawPath(path)

class PagePowerQuality(QWidget):
    def __init__(self, tag_manager, parent=None):
        super().__init__(parent)
        self.tag_manager = tag_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel(tr("nav.power_quality"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PageHeader")
        layout.addWidget(title)

        # Task (Part 3a): this whole page is a synthetic-waveform sandbox
        # with sliders - zero connection to any real measurement, sitting
        # in the nav right next to pages that show real data (Digital/
        # Analog Inputs, Main View). Nothing about the waveforms or dials
        # themselves said so. A persistent, impossible-to-miss banner
        # (not just a tooltip or a line in Help) fixes that - same
        # "impossible to overlook" bar Training Mode's own status-bar
        # indicator uses (see main_window.py's _refresh_training_mode_indicator()),
        # themed so it reads clearly in every visual theme, not just
        # Industrial's default colors.
        self.lbl_sim_banner = QLabel(tr("pages.power_quality.sim_banner"))
        self.lbl_sim_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_sim_banner.setWordWrap(True)
        layout.addWidget(self.lbl_sim_banner)
        self._refresh_sim_banner_style()
        get_theme_manager().theme_changed.connect(self._refresh_sim_banner_style)

        split_layout = QHBoxLayout()
        layout.addLayout(split_layout, stretch=1)

        # Waveforms
        wave_layout = QVBoxLayout()
        self.voltage_wave = WaveformWidget(tr("pages.power_quality.wave_voltage_title"), ["red", "yellow", "blue"])
        self.current_wave = WaveformWidget(tr("pages.power_quality.wave_current_title"), ["red", "yellow", "blue"])
        wave_layout.addWidget(self.voltage_wave, stretch=1)
        wave_layout.addWidget(self.current_wave, stretch=1)
        split_layout.addLayout(wave_layout, stretch=2)

        # Controls
        ctrl_frame = QFrame()
        ctrl_frame.setObjectName("SunkenFrame")
        

        ctrl_layout = QGridLayout(ctrl_frame)
        ctrl_layout.setContentsMargins(5, 5, 5, 5)

        def create_slider(name, row, min_val, max_val, default_val, update_cb, tooltip=""):
            ctrl_layout.addWidget(QLabel(name), row, 0)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setValue(default_val)
            if tooltip:
                slider.setToolTip(tooltip)
            slider.valueChanged.connect(update_cb)
            ctrl_layout.addWidget(slider, row, 1)

            val_lbl = QLabel(str(default_val))
            ctrl_layout.addWidget(val_lbl, row, 2)

            def on_change(v):
                val_lbl.setText(str(v))
                update_cb(v)

            slider.valueChanged.connect(on_change)
            return slider

        # Task: podpowiedzi - Voltage/Current Ampl./Frequency are
        # self-explanatory sliders (Task: "nie dodawaj tam, gdzie
        # etykieta mowi wszystko"); Noise/Harmonics are not obvious
        # without EE background, so those two get one.
        create_slider(tr("pages.power_quality.lbl_voltage_ampl"), 0, 0, 150, 100, lambda v: self.set_wave_param('amplitude', v, 'v'))
        create_slider(tr("pages.power_quality.lbl_current_ampl"), 1, 0, 150, 100, lambda v: self.set_wave_param('amplitude', v, 'i'))
        create_slider(tr("pages.power_quality.lbl_frequency"), 2, 40, 60, 50, lambda v: self.set_wave_param('frequency', v, 'both'))
        create_slider(tr("pages.power_quality.lbl_noise"), 3, 0, 100, 0, lambda v: self.set_wave_param('noise', v, 'both'),
                      tooltip=tr("pages.power_quality.tooltip_noise"))
        create_slider(tr("pages.power_quality.lbl_harmonics"), 4, 0, 50, 0, lambda v: self.set_wave_param('harmonics', v, 'both'),
                      tooltip=tr("pages.power_quality.tooltip_harmonics"))

        ctrl_layout.setRowStretch(5, 1)
        split_layout.addWidget(ctrl_frame, stretch=1)

    def _refresh_sim_banner_style(self, *_):
        theme_colors = current_colors()
        self.lbl_sim_banner.setStyleSheet(
            f"color: {theme_colors['window_bg']}; background-color: {theme_colors['state_caution']}; "
            "font-weight: bold; padding: 3px 6px;"
        )

    def set_wave_param(self, param, value, target):
        if target in ('v', 'both'):
            setattr(self.voltage_wave, param, float(value))
        if target in ('i', 'both'):
            setattr(self.current_wave, param, float(value))

        # Update simulation tags based on slider changes. Positional
        # quality (not quality=...): self.tag_manager may be main.py's
        # GUITagManagerAdapter, whose update_tag() names this parameter
        # `q`, not `quality` - see page_entry_gate.py for the same note.
        if param == 'amplitude' and target == 'v':
            self.tag_manager.update_tag("Sim.Voltage", value * 2.3, TagQuality.SIMULATED)
        elif param == 'frequency':
            self.tag_manager.update_tag("Sim.Frequency", float(value), TagQuality.SIMULATED)
