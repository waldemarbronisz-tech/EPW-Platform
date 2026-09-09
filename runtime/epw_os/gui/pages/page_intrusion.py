import csv
from datetime import datetime, timedelta

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
                             QTableWidget, QTableWidgetItem, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
                             QDialog, QDialogButtonBox, QPushButton, QMessageBox,
                             QDateEdit, QFileDialog, QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt, QTimer, QDate
from PySide6.QtGui import QColor

from epw_os.gui.table_helpers import (
    set_resizable_columns, set_header_tooltips,
    apply_table_button_style, style_transparent_cell_container,
    ItemBackgroundDelegate,
)
from epw_os.gui.widgets.crud_dialog import run_crud_dialog
from epw_os.core.access_manager import AccessLevel
from epw_os.core.intrusion_manager import (
    LineType, ZoneState, NORMAL_STATE_NC, NORMAL_STATE_NO,
    DEFAULT_MIN_VIOLATION_SECONDS, DEFAULT_MULTIPLICITY_COUNT, DEFAULT_MULTIPLICITY_WINDOW_SECONDS,
    DEFAULT_LOCKOUT_AFTER_COUNT, DEFAULT_ALARM_HOLD_SECONDS, DEFAULT_SILENCE_THRESHOLD_SECONDS,
    LineInputMode, DEFAULT_LINE_INPUT_MODE, LineParametrization, DEFAULT_PARAMETRIZATION,
    LineState, default_value_windows, is_line_fault_state,
    DEFAULT_WALK_TEST_DURATION_SECONDS,
)
from epw_os.gui.theme_manager import get_theme_manager, neutral_text_style, error_text_style
from epw_os.i18n import tr


def _zone_state_name(state: str) -> str:
    return {
        ZoneState.DISARMED: tr("pages.intrusion.state_disarmed"),
        ZoneState.EXIT_DELAY: tr("pages.intrusion.state_exit_delay"),
        ZoneState.ARMED: tr("pages.intrusion.state_armed"),
        ZoneState.ENTRY_DELAY: tr("pages.intrusion.state_entry_delay"),
        ZoneState.ALARM: tr("pages.intrusion.state_alarm"),
    }.get(state, state or "")


_LINE_TYPE_KEYS = {
    LineType.INSTANT: "pages.intrusion.line_type_instant",
    LineType.DELAYED: "pages.intrusion.line_type_delayed",
    LineType.TWENTY_FOUR_HOUR: "pages.intrusion.line_type_24h",
    LineType.SUPERVISORY: "pages.intrusion.line_type_supervisory",
}


def _line_type_name(line_type: str) -> str:
    return tr(_LINE_TYPE_KEYS.get(line_type, "pages.intrusion.line_type_instant"))


_LINE_STATE_KEYS = {
    LineState.SECURE: "pages.intrusion.line_state_secure",
    LineState.VIOLATED: "pages.intrusion.line_state_violated",
    LineState.TAMPER: "pages.intrusion.line_state_tamper",
    LineState.SHORT: "pages.intrusion.line_state_short",
    LineState.FAULT_OPEN: "pages.intrusion.line_state_fault_open",
    LineState.UNDETERMINED: "pages.intrusion.line_state_undetermined",
}

# Same order used both by the config dialog's value-windows editor (Task:
# "okno wartosci... od-do" per state) and _line_state_name() below - EOL
# shows 3 rows, DEOL shows 5, in this fixed, deterministic order.
_EOL_STATE_ORDER = (LineState.VIOLATED, LineState.SECURE, LineState.FAULT_OPEN)
_DEOL_STATE_ORDER = (LineState.SHORT, LineState.VIOLATED, LineState.SECURE, LineState.TAMPER, LineState.FAULT_OPEN)


def _line_state_name(state: str) -> str:
    return tr(_LINE_STATE_KEYS.get(state, "pages.intrusion.line_state_secure"))


class ZoneConfigDialog(QDialog):
    """Add (zone=None) or edit an existing zone - name + exit/entry
    delay seconds. Engineer-only (see PageIntrusionConfiguration._configure_zones())."""

    def __init__(self, zone=None, parent=None):
        super().__init__(parent)
        self.is_new = zone is None
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("pages.intrusion.dialog_zone_add_title") if self.is_new
                             else tr("pages.intrusion.dialog_zone_edit_title", name=zone["name"]))
        self.setModal(True)
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        form = QFormLayout()
        layout.addLayout(form)

        self.edit_name = QLineEdit(zone["name"] if zone else "")
        form.addRow(tr("pages.intrusion.lbl_zone_name"), self.edit_name)

        self.spin_exit_delay = QSpinBox()
        self.spin_exit_delay.setRange(0, 600)
        self.spin_exit_delay.setSuffix(" s")
        self.spin_exit_delay.setValue(int(zone["exit_delay_seconds"]) if zone else 30)
        form.addRow(tr("pages.intrusion.lbl_exit_delay"), self.spin_exit_delay)

        self.spin_entry_delay = QSpinBox()
        self.spin_entry_delay.setRange(0, 600)
        self.spin_entry_delay.setSuffix(" s")
        self.spin_entry_delay.setValue(int(zone["entry_delay_seconds"]) if zone else 30)
        form.addRow(tr("pages.intrusion.lbl_entry_delay"), self.spin_entry_delay)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet(error_text_style())
        self.lbl_error.setWordWrap(True)
        layout.addWidget(self.lbl_error)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._try_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _try_accept(self):
        if not self.edit_name.text().strip():
            self.lbl_error.setText(tr("pages.intrusion.err_name_required"))
            return
        self.accept()

    def result_name(self) -> str:
        return self.edit_name.text().strip()

    def result_exit_delay(self) -> float:
        return float(self.spin_exit_delay.value())

    def result_entry_delay(self) -> float:
        return float(self.spin_entry_delay.value())


class LineConfigDialog(QDialog):
    """Add (line=None) or edit an existing supervision line. `zones` is
    the current list of zone dicts (get_zones()) to populate the zone
    dropdown - Task: "przypisanie do strefy". `digital_candidates`/
    `analog_candidates` (IntrusionManager.get_digital_input_candidates()/
    get_analog_input_candidates()) populate the CONTACT/PARAMETRIZED
    input pickers - Task part 1: "lista wejsc... WYLACZNIE wejscia
    wlasciwego typu... NIEMOZLIWE przypisanie wejscia niewlasciwego
    typu" - a combo box populated only from the right list, replacing
    the free-text tag field this dialog used to have (GRANICE for the
    predecessor task's own line dialog no longer applies here - THIS
    task explicitly tightens that to a type-restricted picker)."""

    def __init__(self, zones, digital_candidates, analog_candidates, line=None, parent=None):
        super().__init__(parent)
        self.is_new = line is None
        self.zones = zones
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("pages.intrusion.dialog_line_add_title") if self.is_new
                             else tr("pages.intrusion.dialog_line_edit_title", name=line["name"]))
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        form = QFormLayout()
        layout.addLayout(form)

        self.edit_name = QLineEdit(line["name"] if line else "")
        form.addRow(tr("pages.intrusion.lbl_line_name"), self.edit_name)

        self.combo_zone = QComboBox()
        for zone in zones:
            self.combo_zone.addItem(zone["name"], zone["id"])
        if line:
            idx = self.combo_zone.findData(line["zone_id"])
            if idx >= 0:
                self.combo_zone.setCurrentIndex(idx)
        form.addRow(tr("pages.intrusion.lbl_line_zone"), self.combo_zone)

        # Task part 1: "tryb pracy" (input mode) drives what the rest of
        # this form shows - see _update_mode_visibility() below.
        self._last_mode = line.get("input_mode", DEFAULT_LINE_INPUT_MODE) if line else DEFAULT_LINE_INPUT_MODE
        self.combo_input_mode = QComboBox()
        self.combo_input_mode.addItem(tr("pages.intrusion.input_mode_contact"), LineInputMode.CONTACT)
        self.combo_input_mode.addItem(tr("pages.intrusion.input_mode_parametrized"), LineInputMode.PARAMETRIZED)
        idx = self.combo_input_mode.findData(self._last_mode)
        if idx >= 0:
            self.combo_input_mode.setCurrentIndex(idx)
        form.addRow(tr("pages.intrusion.lbl_input_mode"), self.combo_input_mode)

        # --- CONTACT-mode fields ---------------------------------------
        self.combo_tag_contact = QComboBox()
        self.combo_tag_contact.addItem("", "")
        for t in digital_candidates:
            self.combo_tag_contact.addItem(t, t)
        self.lbl_tag_contact = QLabel(tr("pages.intrusion.lbl_line_tag"))
        form.addRow(self.lbl_tag_contact, self.combo_tag_contact)

        self.combo_normal_state = QComboBox()
        self.combo_normal_state.addItem(tr("pages.intrusion.normal_state_nc"), NORMAL_STATE_NC)
        self.combo_normal_state.addItem(tr("pages.intrusion.normal_state_no"), NORMAL_STATE_NO)
        self.lbl_normal_state = QLabel(tr("pages.intrusion.lbl_line_normal_state"))
        form.addRow(self.lbl_normal_state, self.combo_normal_state)

        # --- PARAMETRIZED-mode fields ------------------------------------
        self.combo_tag_analog = QComboBox()
        self.combo_tag_analog.addItem("", "")
        for t in analog_candidates:
            self.combo_tag_analog.addItem(t, t)
        self.lbl_tag_analog = QLabel(tr("pages.intrusion.lbl_line_analog_point"))
        form.addRow(self.lbl_tag_analog, self.combo_tag_analog)

        self.combo_parametrization = QComboBox()
        self.combo_parametrization.addItem(tr("pages.intrusion.parametrization_eol"), LineParametrization.EOL)
        self.combo_parametrization.addItem(tr("pages.intrusion.parametrization_deol"), LineParametrization.DEOL)
        self.lbl_parametrization = QLabel(tr("pages.intrusion.lbl_parametrization"))
        form.addRow(self.lbl_parametrization, self.combo_parametrization)

        self.lbl_windows_header = QLabel(tr("pages.intrusion.lbl_value_windows"))
        form.addRow(self.lbl_windows_header)
        self.windows_widget = QWidget()
        self.windows_layout = QFormLayout(self.windows_widget)
        self.windows_layout.setContentsMargins(0, 0, 0, 0)
        form.addRow(self.windows_widget)
        self._window_spinboxes = {}  # LineState.* -> (spin_min, spin_max)

        # Pre-select whichever fields apply, BEFORE wiring the
        # mode/parametrization change handlers below - otherwise loading
        # an existing line would immediately look like a user-driven
        # mode change and trigger the "input cleared, re-select it"
        # warning on a dialog that just opened.
        if line:
            if self._last_mode == LineInputMode.PARAMETRIZED:
                idx = self.combo_tag_analog.findData(line["tag"])
                if idx >= 0:
                    self.combo_tag_analog.setCurrentIndex(idx)
                idx = self.combo_parametrization.findData(line.get("parametrization", DEFAULT_PARAMETRIZATION))
                if idx >= 0:
                    self.combo_parametrization.setCurrentIndex(idx)
            else:
                idx = self.combo_tag_contact.findData(line["tag"])
                if idx >= 0:
                    self.combo_tag_contact.setCurrentIndex(idx)
                idx = self.combo_normal_state.findData(line["normal_state"])
                if idx >= 0:
                    self.combo_normal_state.setCurrentIndex(idx)
        self._rebuild_value_windows(line.get("value_windows") if line else None)
        self._update_mode_visibility()

        self.combo_input_mode.currentIndexChanged.connect(self._on_mode_changed)
        self.combo_parametrization.currentIndexChanged.connect(lambda _i: self._rebuild_value_windows(None))

        self.combo_type = QComboBox()
        for lt in LineType._ALL:
            self.combo_type.addItem(_line_type_name(lt), lt)
        if line:
            idx = self.combo_type.findData(line["line_type"])
            if idx >= 0:
                self.combo_type.setCurrentIndex(idx)
        form.addRow(tr("pages.intrusion.lbl_line_type"), self.combo_type)

        # Task part 2: false-alarm filtering, per line - each field
        # defaults to the "filter off, behaves as before" value
        # (DEFAULT_* in intrusion_manager.py, the single source of
        # truth this dialog reads rather than repeating the numbers).
        self.spin_min_violation = QDoubleSpinBox()
        self.spin_min_violation.setRange(0.0, 3600.0)
        self.spin_min_violation.setDecimals(1)
        self.spin_min_violation.setSuffix(" s")
        self.spin_min_violation.setToolTip(tr("pages.intrusion.tooltip_min_violation"))
        self.spin_min_violation.setValue(
            float(line["min_violation_seconds"]) if line else DEFAULT_MIN_VIOLATION_SECONDS)
        form.addRow(tr("pages.intrusion.lbl_min_violation"), self.spin_min_violation)

        mult_row = QHBoxLayout()
        self.spin_multiplicity_count = QSpinBox()
        self.spin_multiplicity_count.setRange(1, 100)
        self.spin_multiplicity_count.setToolTip(tr("pages.intrusion.tooltip_multiplicity_count"))
        self.spin_multiplicity_count.setValue(
            int(line["multiplicity_count"]) if line else DEFAULT_MULTIPLICITY_COUNT)
        mult_row.addWidget(self.spin_multiplicity_count)
        mult_row.addWidget(QLabel(tr("pages.intrusion.lbl_multiplicity_window")))
        self.spin_multiplicity_window = QDoubleSpinBox()
        self.spin_multiplicity_window.setRange(0.1, 3600.0)
        self.spin_multiplicity_window.setDecimals(1)
        self.spin_multiplicity_window.setSuffix(" s")
        self.spin_multiplicity_window.setToolTip(tr("pages.intrusion.tooltip_multiplicity_window"))
        self.spin_multiplicity_window.setValue(
            float(line["multiplicity_window_seconds"]) if line else DEFAULT_MULTIPLICITY_WINDOW_SECONDS)
        mult_row.addWidget(self.spin_multiplicity_window)
        form.addRow(tr("pages.intrusion.lbl_multiplicity_count"), mult_row)

        self.spin_lockout_after = QSpinBox()
        self.spin_lockout_after.setRange(0, 100)
        self.spin_lockout_after.setToolTip(tr("pages.intrusion.tooltip_lockout_after"))
        self.spin_lockout_after.setValue(
            int(line["lockout_after_count"]) if line else DEFAULT_LOCKOUT_AFTER_COUNT)
        form.addRow(tr("pages.intrusion.lbl_lockout_after"), self.spin_lockout_after)

        self.spin_alarm_hold = QDoubleSpinBox()
        self.spin_alarm_hold.setRange(0.0, 3600.0)
        self.spin_alarm_hold.setDecimals(1)
        self.spin_alarm_hold.setSuffix(" s")
        self.spin_alarm_hold.setToolTip(tr("pages.intrusion.tooltip_alarm_hold"))
        self.spin_alarm_hold.setValue(
            float(line["alarm_hold_seconds"]) if line else DEFAULT_ALARM_HOLD_SECONDS)
        form.addRow(tr("pages.intrusion.lbl_alarm_hold"), self.spin_alarm_hold)

        # Task part 3 (life/silence supervision): "konfigurowalny per
        # linia MAKSYMALNY CZAS BEZ NARUSZENIA".
        self.spin_silence_threshold = QDoubleSpinBox()
        self.spin_silence_threshold.setRange(0.0, 100_000_000.0)
        self.spin_silence_threshold.setDecimals(0)
        self.spin_silence_threshold.setSuffix(" s")
        self.spin_silence_threshold.setToolTip(tr("pages.intrusion.tooltip_silence_threshold"))
        self.spin_silence_threshold.setValue(
            float(line["silence_threshold_seconds"]) if line else DEFAULT_SILENCE_THRESHOLD_SECONDS)
        form.addRow(tr("pages.intrusion.lbl_silence_threshold"), self.spin_silence_threshold)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet(error_text_style())
        self.lbl_error.setWordWrap(True)
        layout.addWidget(self.lbl_error)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._try_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # --- mode switching (Task part 1) ---------------------------------

    def _on_mode_changed(self, _index):
        new_mode = self.combo_input_mode.currentData()
        if new_mode != self._last_mode:
            # Task: "zmiana trybu... ma wymagac ponownego wskazania
            # wejscia - stare przypisanie przestaje byc wazne. Ostrzez o
            # tym uzytkownika zamiast po cichu czyscic konfiguracje" -
            # the warning comes FIRST, then the (now-invalid) input
            # selection is cleared, every time the mode actually changes.
            QMessageBox.warning(self, self.windowTitle(), tr("pages.intrusion.warn_mode_change_clears_input"))
            self.combo_tag_contact.setCurrentIndex(0)
            self.combo_tag_analog.setCurrentIndex(0)
            self._last_mode = new_mode
        self._update_mode_visibility()

    def _update_mode_visibility(self):
        is_param = self.combo_input_mode.currentData() == LineInputMode.PARAMETRIZED
        for w in (self.lbl_tag_contact, self.combo_tag_contact, self.lbl_normal_state, self.combo_normal_state):
            w.setVisible(not is_param)
        for w in (self.lbl_tag_analog, self.combo_tag_analog, self.lbl_parametrization, self.combo_parametrization,
                  self.lbl_windows_header, self.windows_widget):
            w.setVisible(is_param)

    def _rebuild_value_windows(self, initial_windows):
        while self.windows_layout.rowCount():
            self.windows_layout.removeRow(0)
        self._window_spinboxes = {}
        parametrization = self.combo_parametrization.currentData() or DEFAULT_PARAMETRIZATION
        defaults = default_value_windows(parametrization)
        windows = initial_windows or defaults
        state_order = _DEOL_STATE_ORDER if parametrization == LineParametrization.DEOL else _EOL_STATE_ORDER
        for state in state_order:
            lo, hi = windows.get(state, defaults.get(state, [0.0, 0.0]))
            row = QHBoxLayout()
            spin_lo = QDoubleSpinBox()
            spin_lo.setRange(-1_000_000.0, 1_000_000.0)
            spin_lo.setDecimals(2)
            spin_lo.setValue(float(lo))
            spin_hi = QDoubleSpinBox()
            spin_hi.setRange(-1_000_000.0, 1_000_000.0)
            spin_hi.setDecimals(2)
            spin_hi.setValue(float(hi))
            row.addWidget(spin_lo)
            row.addWidget(QLabel(tr("pages.intrusion.lbl_window_range_sep")))
            row.addWidget(spin_hi)
            self.windows_layout.addRow(_line_state_name(state), row)
            self._window_spinboxes[state] = (spin_lo, spin_hi)

    def _try_accept(self):
        if not self.edit_name.text().strip():
            self.lbl_error.setText(tr("pages.intrusion.err_name_required"))
            return
        if not self.result_tag():
            self.lbl_error.setText(tr("pages.intrusion.err_input_required"))
            return
        if self.combo_zone.count() == 0:
            self.lbl_error.setText(tr("pages.intrusion.err_zone_required"))
            return
        self.accept()

    def result_name(self) -> str:
        return self.edit_name.text().strip()

    def result_zone_id(self) -> str:
        return self.combo_zone.currentData()

    def result_input_mode(self) -> str:
        return self.combo_input_mode.currentData()

    def result_tag(self) -> str:
        # Task part 1: whichever picker is active for the current mode
        # is authoritative - the other one is hidden and irrelevant.
        if self.result_input_mode() == LineInputMode.PARAMETRIZED:
            return (self.combo_tag_analog.currentData() or "").strip()
        return (self.combo_tag_contact.currentData() or "").strip()

    def result_normal_state(self) -> str:
        return self.combo_normal_state.currentData()

    def result_parametrization(self) -> str:
        return self.combo_parametrization.currentData()

    def result_value_windows(self) -> dict:
        return {
            state: [spin_lo.value(), spin_hi.value()]
            for state, (spin_lo, spin_hi) in self._window_spinboxes.items()
        }

    def result_line_type(self) -> str:
        return self.combo_type.currentData()

    def result_min_violation_seconds(self) -> float:
        return self.spin_min_violation.value()

    def result_multiplicity_count(self) -> int:
        return self.spin_multiplicity_count.value()

    def result_multiplicity_window_seconds(self) -> float:
        return self.spin_multiplicity_window.value()

    def result_lockout_after_count(self) -> int:
        return self.spin_lockout_after.value()

    def result_alarm_hold_seconds(self) -> float:
        return self.spin_alarm_hold.value()

    def result_silence_threshold_seconds(self) -> float:
        return self.spin_silence_threshold.value()


class ArmConfirmPopup(QDialog):
    """Task 4: arming a zone with a violated line must require EXPLICIT
    confirmation, naming which line(s) - shown only when
    IntrusionManager.arm_zone() comes back with needs_confirmation=True."""

    def __init__(self, zone_name: str, violated_line_names: list, fault_line_names: list = None, parent=None):
        super().__init__(parent)
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("pages.intrusion.confirm_arm_title"))
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        msg = QLabel(tr("pages.intrusion.confirm_arm_message", zone=zone_name))
        msg.setWordWrap(True)
        msg.setStyleSheet("font-weight: bold;")
        layout.addWidget(msg)

        if violated_line_names:
            violated_header = QLabel(tr("pages.intrusion.confirm_arm_violated_header"))
            violated_header.setStyleSheet(error_text_style())
            layout.addWidget(violated_header)
            lines_label = QLabel("\n".join(f"- {name}" for name in violated_line_names))
            lines_label.setStyleSheet(error_text_style())
            lines_label.setWordWrap(True)
            layout.addWidget(lines_label)

        if fault_line_names:
            # Task part 4: fault lines are shown distinctly ("z jakiego
            # powodu" the confirmation is needed) from plain violations.
            fault_header = QLabel(tr("pages.intrusion.confirm_arm_fault_header"))
            fault_header.setStyleSheet(error_text_style())
            layout.addWidget(fault_header)
            fault_label = QLabel("\n".join(f"- {name}" for name in fault_line_names))
            fault_label.setStyleSheet(error_text_style())
            fault_label.setWordWrap(True)
            layout.addWidget(fault_label)

        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton(tr("pages.intrusion.btn_cancel"))
        self.btn_confirm = QPushButton(tr("pages.intrusion.btn_confirm_arm_anyway"))
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_confirm)
        layout.addLayout(btn_layout)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_confirm.clicked.connect(self.accept)


class PowerSupervisionDialog(QDialog):
    """Task part 2: a single, page-level (not per-line, not per-zone)
    optional config - "brak konfiguracji = brak nadzoru, bez bledow", so
    both inputs default to blank/unselected and the dialog can always be
    saved as-is with nothing configured."""

    def __init__(self, digital_candidates, current: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("pages.intrusion.power_supervision_title"))
        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        form = QFormLayout()
        layout.addLayout(form)

        self.combo_mains_tag = QComboBox()
        self.combo_mains_tag.addItem("", "")
        for t in digital_candidates:
            self.combo_mains_tag.addItem(t, t)
        form.addRow(tr("pages.intrusion.lbl_mains_tag"), self.combo_mains_tag)

        self.combo_mains_ok_state = QComboBox()
        self.combo_mains_ok_state.addItem(tr("pages.intrusion.power_ok_when_true"), True)
        self.combo_mains_ok_state.addItem(tr("pages.intrusion.power_ok_when_false"), False)
        form.addRow(tr("pages.intrusion.lbl_mains_ok_state"), self.combo_mains_ok_state)

        self.combo_battery_tag = QComboBox()
        self.combo_battery_tag.addItem("", "")
        for t in digital_candidates:
            self.combo_battery_tag.addItem(t, t)
        form.addRow(tr("pages.intrusion.lbl_battery_tag"), self.combo_battery_tag)

        self.combo_battery_ok_state = QComboBox()
        self.combo_battery_ok_state.addItem(tr("pages.intrusion.power_ok_when_true"), True)
        self.combo_battery_ok_state.addItem(tr("pages.intrusion.power_ok_when_false"), False)
        form.addRow(tr("pages.intrusion.lbl_battery_ok_state"), self.combo_battery_ok_state)

        mains_tag = current.get("mains_tag") or ""
        idx = self.combo_mains_tag.findData(mains_tag)
        if idx >= 0:
            self.combo_mains_tag.setCurrentIndex(idx)
        idx = self.combo_mains_ok_state.findData(bool(current.get("mains_ok_state", True)))
        if idx >= 0:
            self.combo_mains_ok_state.setCurrentIndex(idx)
        battery_tag = current.get("battery_tag") or ""
        idx = self.combo_battery_tag.findData(battery_tag)
        if idx >= 0:
            self.combo_battery_tag.setCurrentIndex(idx)
        idx = self.combo_battery_ok_state.findData(bool(current.get("battery_ok_state", True)))
        if idx >= 0:
            self.combo_battery_ok_state.setCurrentIndex(idx)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result_mains_tag(self) -> str:
        return (self.combo_mains_tag.currentData() or "").strip()

    def result_mains_ok_state(self) -> bool:
        return bool(self.combo_mains_ok_state.currentData())

    def result_battery_tag(self) -> str:
        return (self.combo_battery_tag.currentData() or "").strip()

    def result_battery_ok_state(self) -> bool:
        return bool(self.combo_battery_ok_state.currentData())


def _format_epoch(ts) -> str:
    """Same "%Y-%m-%d %H:%M:%S" convention page_alarms.py/popups.py
    already use elsewhere in this app - None (nothing recorded yet)
    renders as "-", never a crash or "None" on screen."""
    if not ts:
        return "-"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


class AlarmMemoryDialog(QDialog):
    """Task 3 ("pamiec alarmu"): shows one zone's alarm-memory record -
    whether it's active, the first cause (line + time), and every
    subsequent alarm event in the same latch, clearly separated from
    the first cause (Task 2: "WYRAZNIE ODDZIELONE") - and lets someone
    with clear access (Operator+, already checked by the caller before
    even offering the button - see PageIntrusionOverview._clear_alarm_memory())
    clear it. Stays open after a clear (re-renders in place) rather than
    closing, so the "now inactive" result is visible immediately."""

    def __init__(self, intrusion_manager, zones, on_clear_requested, initial_zone_id=None, parent=None):
        super().__init__(parent)
        self.intrusion_manager = intrusion_manager
        self.on_clear_requested = on_clear_requested
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("pages.intrusion.alarm_memory_title"))
        self.setModal(True)
        self.setMinimumSize(440, 380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        zone_row = QHBoxLayout()
        zone_row.addWidget(QLabel(tr("pages.intrusion.lbl_line_zone")))
        self.combo_zone = QComboBox()
        for zone in zones:
            self.combo_zone.addItem(zone["name"], zone["id"])
        if initial_zone_id is not None:
            idx = self.combo_zone.findData(initial_zone_id)
            if idx >= 0:
                self.combo_zone.setCurrentIndex(idx)
        zone_row.addWidget(self.combo_zone)
        layout.addLayout(zone_row)

        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.lbl_status)

        self.lbl_first_cause_header = QLabel(tr("pages.intrusion.alarm_memory_first_cause_header"))
        self.lbl_first_cause_header.setStyleSheet(error_text_style("font-weight: bold;"))
        layout.addWidget(self.lbl_first_cause_header)
        self.lbl_first_cause = QLabel("")
        self.lbl_first_cause.setWordWrap(True)
        self.lbl_first_cause.setStyleSheet(error_text_style())
        layout.addWidget(self.lbl_first_cause)

        self.lbl_subsequent_header = QLabel(tr("pages.intrusion.alarm_memory_subsequent_header"))
        layout.addWidget(self.lbl_subsequent_header)
        self.list_subsequent = QListWidget()
        layout.addWidget(self.list_subsequent)

        self.btn_clear = QPushButton(tr("pages.intrusion.btn_clear_alarm_memory"))
        self.btn_clear.clicked.connect(self._clear)
        layout.addWidget(self.btn_clear)

        btn_close = QPushButton(tr("pages.intrusion.btn_close"))
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        self.combo_zone.currentIndexChanged.connect(self._refresh)
        self._refresh()

    def _current_zone_id(self):
        return self.combo_zone.currentData()

    def _refresh(self, *_):
        zone_id = self._current_zone_id()
        if zone_id is None:
            self.lbl_status.setText(tr("pages.intrusion.err_zone_required"))
            self.btn_clear.setEnabled(False)
            return
        memory = self.intrusion_manager.get_alarm_memory(zone_id)
        active = memory["active"]
        self.lbl_status.setText(tr("pages.intrusion.alarm_memory_active") if active
                                 else tr("pages.intrusion.alarm_memory_inactive"))
        self.lbl_first_cause_header.setVisible(active)
        self.lbl_first_cause.setVisible(active)
        if active:
            self.lbl_first_cause.setText(tr(
                "pages.intrusion.alarm_memory_first_cause_line_time",
                line=memory["first_cause_line_name"] or memory["first_cause_line_id"] or "?",
                time=_format_epoch(memory["first_cause_at"]),
            ))
        self.list_subsequent.clear()
        for entry in memory["subsequent"]:
            self.list_subsequent.addItem(
                f"{entry.get('line_name') or entry.get('line_id') or '?'} - {_format_epoch(entry.get('at'))}")
        self.lbl_subsequent_header.setVisible(active and bool(memory["subsequent"]))
        self.list_subsequent.setVisible(active and bool(memory["subsequent"]))
        self.btn_clear.setEnabled(active)

    def _clear(self):
        zone_id = self._current_zone_id()
        if zone_id is None or self.on_clear_requested is None:
            return
        if self.on_clear_requested(zone_id):
            self._refresh()


class WalkTestDialog(QDialog):
    """Task 4 ("tryb chodzenia"): start/stop walk-test mode on one zone
    and watch, live, which of its lines have already reacted - a QTimer
    ticks while this dialog is open (Task: "odliczanie widoczne na
    ekranie" + "widoczna lista linii... ktore juz zareagowaly, a ktore
    jeszcze nie"), same 1s cadence PageIntrusion's own countdown timer
    already uses elsewhere on this page. Stopping (by hand, from here)
    shows the confirmed/silent summary in place (Task: "po wyjsciu z
    trybu - podsumowanie") - closing the dialog does NOT stop the test,
    the same way closing the Manage Zones/Lines dialog doesn't undo
    anything either; use the Stop button for that."""

    def __init__(self, intrusion_manager, zones, on_start, on_stop, initial_zone_id=None, parent=None):
        super().__init__(parent)
        self.intrusion_manager = intrusion_manager
        self.on_start = on_start
        self.on_stop = on_stop
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("pages.intrusion.walk_test_title"))
        self.setModal(True)
        self.setMinimumSize(440, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        zone_row = QHBoxLayout()
        zone_row.addWidget(QLabel(tr("pages.intrusion.lbl_line_zone")))
        self.combo_zone = QComboBox()
        for zone in zones:
            self.combo_zone.addItem(zone["name"], zone["id"])
        if initial_zone_id is not None:
            idx = self.combo_zone.findData(initial_zone_id)
            if idx >= 0:
                self.combo_zone.setCurrentIndex(idx)
        zone_row.addWidget(self.combo_zone)
        layout.addLayout(zone_row)

        duration_row = QHBoxLayout()
        duration_row.addWidget(QLabel(tr("pages.intrusion.lbl_walk_test_duration")))
        self.spin_duration = QSpinBox()
        self.spin_duration.setRange(10, 24 * 3600)
        self.spin_duration.setSuffix(" s")
        self.spin_duration.setValue(int(DEFAULT_WALK_TEST_DURATION_SECONDS))
        duration_row.addWidget(self.spin_duration)
        layout.addLayout(duration_row)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.lbl_status)

        layout.addWidget(QLabel(tr("pages.intrusion.walk_test_lines_header")))
        self.list_lines = QListWidget()
        layout.addWidget(self.list_lines)

        btn_row = QHBoxLayout()
        self.btn_start = QPushButton(tr("pages.intrusion.btn_walk_test_start"))
        self.btn_start.clicked.connect(self._start)
        btn_row.addWidget(self.btn_start)
        self.btn_stop = QPushButton(tr("pages.intrusion.btn_walk_test_stop"))
        self.btn_stop.clicked.connect(self._stop)
        btn_row.addWidget(self.btn_stop)
        layout.addLayout(btn_row)

        btn_close = QPushButton(tr("pages.intrusion.btn_close"))
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        self.combo_zone.currentIndexChanged.connect(self._refresh)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(1000)
        self._refresh()

    def _current_zone_id(self):
        return self.combo_zone.currentData()

    def _refresh(self, *_):
        zone_id = self._current_zone_id()
        if zone_id is None:
            return
        status = self.intrusion_manager.get_walk_test_status(zone_id)
        active = status["active"]
        self.combo_zone.setEnabled(not active)  # switching zones mid-test would be confusing - stop first
        self.spin_duration.setEnabled(not active)
        self.btn_start.setEnabled(not active)
        self.btn_stop.setEnabled(active)
        self.lbl_status.setText(
            tr("pages.intrusion.walk_test_active_remaining", seconds=status["remaining"]) if active
            else tr("pages.intrusion.walk_test_inactive"))

        self.list_lines.clear()
        for line in status["lines"]:
            marker = tr("pages.intrusion.walk_test_confirmed") if line["confirmed"] \
                else tr("pages.intrusion.walk_test_silent")
            suffix = f" - {_format_epoch(line['last_at'])}" if line["confirmed"] else ""
            self.list_lines.addItem(f"{line['name']}: {marker}{suffix}")

    def _start(self):
        zone_id = self._current_zone_id()
        if zone_id is None or self.on_start is None:
            return
        self.on_start(zone_id, self.spin_duration.value())
        self._refresh()

    def _stop(self):
        zone_id = self._current_zone_id()
        if zone_id is None or self.on_stop is None:
            return
        summary = self.on_stop(zone_id)
        self._refresh()
        if summary is not None:
            confirmed = ", ".join(c["line_name"] or c["line_id"] for c in summary["confirmed"]) or "-"
            silent = ", ".join(s["line_name"] or s["line_id"] for s in summary["silent"]) or "-"
            QMessageBox.information(
                self, tr("pages.intrusion.walk_test_title"),
                tr("pages.intrusion.walk_test_summary", confirmed=confirmed, silent=silent),
            )


class HistoryRetentionDialog(QDialog):
    """Task 5 ("retencja: konfigurowalna liczba zdarzen albo dni") -
    Engineer-only (see PageIntrusionConfiguration._configure_history_retention()).
    Either field at 0 means that axis is unlimited - both can be 0 at
    once (unbounded history), though that defeats the SD-card concern
    the Task itself raises, so it's allowed but not the default."""

    def __init__(self, current: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("pages.intrusion.history_retention_title"))
        self.setModal(True)
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        form = QFormLayout()
        layout.addLayout(form)

        self.spin_max_events = QSpinBox()
        self.spin_max_events.setRange(0, 1_000_000)
        self.spin_max_events.setSpecialValueText(tr("pages.intrusion.retention_unlimited"))
        self.spin_max_events.setToolTip(tr("pages.intrusion.tooltip_retention_max_events"))
        self.spin_max_events.setValue(int(current.get("max_events", 0) or 0))
        form.addRow(tr("pages.intrusion.lbl_retention_max_events"), self.spin_max_events)

        self.spin_max_days = QSpinBox()
        self.spin_max_days.setRange(0, 3650)
        self.spin_max_days.setSpecialValueText(tr("pages.intrusion.retention_unlimited"))
        self.spin_max_days.setToolTip(tr("pages.intrusion.tooltip_retention_max_days"))
        self.spin_max_days.setValue(int(current.get("max_days", 0) or 0))
        form.addRow(tr("pages.intrusion.lbl_retention_max_days"), self.spin_max_days)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result_max_events(self) -> int:
        return self.spin_max_events.value()

    def result_max_days(self) -> int:
        return self.spin_max_days.value()


_ZONE_COL_NAME, _ZONE_COL_STATE, _ZONE_COL_COUNTDOWN, _ZONE_COL_ACTION = range(4)
_LINE_COL_NAME, _LINE_COL_ZONE, _LINE_COL_TYPE, _LINE_COL_TAG, _LINE_COL_VIOLATED, _LINE_COL_BYPASS = range(6)

_ZONE_COL_NAME, _ZONE_COL_STATE, _ZONE_COL_COUNTDOWN, _ZONE_COL_ACTION = range(4)
_LINE_COL_NAME, _LINE_COL_ZONE, _LINE_COL_TYPE, _LINE_COL_TAG, _LINE_COL_VIOLATED, _LINE_COL_BYPASS = range(6)


class PageIntrusionOverview(QWidget):
    """Task (page-split): SYSTEM ALARMOWY > Podglad - live operational
    work ONLY, "ZADNYCH pol konfiguracyjnych": zones with state + arm/
    disarm, lines with state/bypass/suspect/awaria, alarm memory (first
    cause), walk-test mode. Viewing is open to everyone (like every
    other status page in this app); arming/disarming needs Operator+;
    bypass and walk-test stay Engineer-only, unchanged from before the
    split (GRANICE: "co dzis wymaga Engineera, ma dalej wymagac").
    Zone/line CONFIGURATION (add/edit/remove, input modes, filters,
    power supervision, history retention) moved to
    PageIntrusionConfiguration - this page never opens any of those
    dialogs. Reads the SAME live IntrusionManager instance as the other
    two System Alarmowy pages (constructed once in main_window.py, not
    per-page)."""

    def __init__(self, intrusion_manager, access_manager, audit_logger=None, parent=None):
        super().__init__(parent)
        self.intrusion_manager = intrusion_manager
        self.access_manager = access_manager
        self.audit_logger = audit_logger

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel(tr("nav.intrusion_overview"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PageHeader")
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        self.lbl_gate = QLabel("")
        self.lbl_gate.setStyleSheet(neutral_text_style("font-style: italic;"))
        toolbar.addWidget(self.lbl_gate)
        toolbar.addStretch()
        self.btn_alarm_memory = QPushButton(tr("pages.intrusion.btn_alarm_memory"))
        self.btn_alarm_memory.clicked.connect(self._show_alarm_memory)
        toolbar.addWidget(self.btn_alarm_memory)
        self.btn_walk_test = QPushButton(tr("pages.intrusion.btn_walk_test"))
        self.btn_walk_test.clicked.connect(self._show_walk_test)
        toolbar.addWidget(self.btn_walk_test)
        layout.addLayout(toolbar)

        layout.addWidget(QLabel(tr("pages.intrusion.list_zones_header")))
        self.zone_table = QTableWidget(0, 4)
        self.zone_table.setHorizontalHeaderLabels([
            tr("pages.intrusion.col_zone_name"), tr("pages.common.col_state"),
            tr("pages.intrusion.col_zone_countdown"), tr("pages.intrusion.col_zone_action"),
        ])
        set_resizable_columns(self.zone_table.horizontalHeader(), [200, 190, 110, 110])
        self.zone_table.verticalHeader().setVisible(False)
        self.zone_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # Bug fix: item.setBackground()/setForeground() render wrong
        # under this app's stylesheet without this - see
        # ItemBackgroundDelegate's own docstring (table_helpers.py).
        self.zone_table.setItemDelegate(ItemBackgroundDelegate(self.zone_table))
        layout.addWidget(self.zone_table)

        layout.addWidget(QLabel(tr("pages.intrusion.list_lines_header")))
        self.line_table = QTableWidget(0, 6)
        self.line_table.setHorizontalHeaderLabels([
            tr("pages.intrusion.col_line_name"), tr("pages.intrusion.col_line_zone"),
            tr("pages.intrusion.col_line_type"), tr("pages.common.col_tag"),
            tr("pages.intrusion.col_line_violated"), tr("pages.intrusion.col_line_bypass"),
        ])
        set_header_tooltips(self.line_table, [
            "", "", "", "", tr("pages.intrusion.tooltip_col_violated"), tr("pages.intrusion.tooltip_col_bypass"),
        ])
        set_resizable_columns(self.line_table.horizontalHeader(), [160, 140, 120, 100, 100, 110])
        self.line_table.verticalHeader().setVisible(False)
        self.line_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.line_table.setItemDelegate(ItemBackgroundDelegate(self.line_table))
        layout.addWidget(self.line_table)

        self.access_manager.level_changed.connect(self.refresh)
        get_theme_manager().theme_changed.connect(self.refresh)

        # Bug fix: see _build_action_container()'s docstring below - a
        # cell widget (the Uzbroj/Rozbroj, Bypass buttons) never joins
        # the table's own row-selection painting, so selecting a row
        # left that one cell looking like a rendering glitch ("jasna
        # obwodka") without this.
        self.zone_table.itemSelectionChanged.connect(self._resync_action_containers)
        self.line_table.itemSelectionChanged.connect(self._resync_action_containers)

        # A zone counting down (or walk-testing) needs a ticking display
        # (Task: "wskazanie ktora linia jest naruszona" + a usable
        # countdown; Task 4: "odliczanie widoczne na ekranie") -
        # CountdownRemaining's own tag only changes at each state
        # transition, not once a second, so this page polls
        # get_countdown_remaining()/get_walk_test_remaining() directly on
        # a short timer instead of asking intrusion_manager.py to run a
        # background thread just for cosmetic ticking (see that module's
        # own docstring: it is otherwise purely event-driven, no polling
        # loop of its own).
        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._tick)
        self._countdown_timer.start(1000)

        self.refresh()

    # --- refreshing ----------------------------------------------------
    #
    # Two update paths share the text/color-building helpers just below
    # (Task 6: "aktualizuj tylko to, co sie zmienilo, nie przebudowuj
    # calej tabeli przy kazdym zdarzeniu"):
    # - refresh(): the FULL rebuild - setRowCount() + brand new
    #   QTableWidgetItem/cell-widget objects for every row. Used for
    #   anything that can change which ROWS exist or their per-row
    #   static fields (access-level change, theme change, first
    #   construction, or right after a zone/line CRUD action on
    #   PageIntrusionConfiguration - see that class's own refresh
    #   wiring for how this page learns about it).
    # - refresh_live(): the lightweight counterpart MainWindow's
    #   tag_changed bridge calls instead, on every Security.* tag change
    #   (the actual hot path - a violation, a state transition, a
    #   Suspect/Locked/Fault flip can all fire many times a second) -
    #   updates EXISTING items/cell widgets in place, never calls
    #   setRowCount() or constructs a new QTableWidgetItem for a cell
    #   whose text didn't actually change.
    # A third, independent 1Hz QTimer (_tick()) handles the two numbers
    # that change on their own even with no tag event at all (an exit/
    # entry countdown, a walk-test's remaining seconds) - same reasoning
    # this page's countdown timer already had before this task.

    def _zone_state_text(self, zone_id: str, state: str) -> str:
        text = _zone_state_name(state)
        if self.intrusion_manager.is_walk_test_active(zone_id):
            remaining = self.intrusion_manager.get_walk_test_remaining(zone_id)
            text += f" ({tr('pages.intrusion.walk_test_suffix', seconds=remaining)})"
        if self.intrusion_manager.get_alarm_memory(zone_id)["active"]:
            text += f" ({tr('pages.intrusion.alarm_memory_suffix')})"
        return text

    def _zone_row_colors(self, state: str, colors: dict):
        if state == ZoneState.ALARM:
            return QColor(colors["state_alarm_dark"]), QColor(colors["accent_text"])
        elif state in (ZoneState.EXIT_DELAY, ZoneState.ENTRY_DELAY):
            return QColor(colors["state_warning_dark"]), QColor(colors["accent_text"])
        return QColor(colors["field_bg"]), QColor(colors["text"])

    def _line_row_display(self, line_id: str, colors: dict):
        """Returns (violated_text, bypassed, bg, fg) - everything
        refresh()/refresh_live() need to paint one line row, built in
        exactly one place so the two update paths can never drift apart."""
        violated = self.intrusion_manager.is_line_violated_now(line_id)
        bypassed = self.intrusion_manager.is_line_bypassed(line_id)
        locked = self.intrusion_manager.is_line_locked(line_id)
        fault = self.intrusion_manager.is_line_fault(line_id)
        suspect = self.intrusion_manager.is_line_suspect(line_id)
        if fault:
            text = _line_state_name(self.intrusion_manager.get_line_state(line_id))
        else:
            text = tr("pages.intrusion.violated_yes") if violated else tr("pages.intrusion.violated_no")
        if bypassed:
            text += f" ({tr('pages.intrusion.bypassed_suffix')})"
        if locked:
            text += f" ({tr('pages.intrusion.locked_suffix')})"
        if suspect:
            text += f" ({tr('pages.intrusion.suspect_suffix')})"
        if (violated or fault) and not bypassed:
            bg, fg = QColor(colors["state_alarm_dark"]), QColor(colors["accent_text"])
        elif suspect and not bypassed:
            bg, fg = QColor(colors["state_warning_dark"]), QColor(colors["accent_text"])
        else:
            bg, fg = QColor(colors["field_bg"]), QColor(colors["text"])
        return text, bypassed, bg, fg

    def refresh(self, *_):
        can_arm = self.access_manager.has_access(AccessLevel.OPERATOR)
        can_configure = self.access_manager.has_access(AccessLevel.ENGINEER)
        self.btn_walk_test.setEnabled(can_configure)
        self.btn_alarm_memory.setEnabled(can_arm)  # viewing needs no level; clearing (inside) checks Operator itself
        if not can_arm:
            self.lbl_gate.setText(tr("pages.intrusion.gate_arm_message"))
        else:
            self.lbl_gate.setText("")

        # intrusion_manager is None in isolated widget tests / mocks that
        # don't wire up a real IntrusionManager - same guard every other
        # optional core manager gets in this app (switching_counters,
        # alarm_manager, ...): the page simply shows empty tables.
        zones = self.intrusion_manager.get_zones() if self.intrusion_manager is not None else []
        lines = self.intrusion_manager.get_lines() if self.intrusion_manager is not None else []
        zone_names = {z["id"]: z["name"] for z in zones}
        colors = get_theme_manager().current_colors()

        # Read BEFORE rebuilding (rowCount()/items are about to be
        # replaced) so a refresh() triggered by something else (theme
        # change, access-level change, an arm/disarm/bypass action) can
        # preserve which row was selected - see _build_action_container()
        # below for why this has to be baked in at construction time
        # rather than patched onto an already-shown widget afterward.
        zone_selected_rows = {index.row() for index in self.zone_table.selectedIndexes()}
        line_selected_rows = {index.row() for index in self.line_table.selectedIndexes()}

        self.zone_table.setRowCount(len(zones))
        for row, zone in enumerate(zones):
            zone_id = zone["id"]
            state = self.intrusion_manager.get_zone_state(zone_id)
            name_item = QTableWidgetItem(zone["name"])
            # Stashed here (not matched back by displayed name text later)
            # so _tick()/refresh_live() find the right row even if two
            # zones happen to share a name - nothing here enforces
            # uniqueness of zone names.
            name_item.setData(Qt.ItemDataRole.UserRole, zone_id)
            self.zone_table.setItem(row, _ZONE_COL_NAME, name_item)
            state_item = QTableWidgetItem(self._zone_state_text(zone_id, state))
            self.zone_table.setItem(row, _ZONE_COL_STATE, state_item)
            remaining = self.intrusion_manager.get_countdown_remaining(zone_id)
            countdown_text = f"{remaining}s" if state in (ZoneState.EXIT_DELAY, ZoneState.ENTRY_DELAY) else "-"
            self.zone_table.setItem(row, _ZONE_COL_COUNTDOWN, QTableWidgetItem(countdown_text))

            # ARMED/DISARMED are both calm, plain-background states - no
            # theme defines a distinct "ok_dark" tone (state_ok/
            # state_ok_text are foreground-only, meant for small
            # ON/OFF-style text, not a full row highlight), so only the
            # two states that actually need attention (a countdown
            # running, or ALARM) get one, same highlight-only-when-
            # -it-matters approach as page_alarms.py.
            bg, fg = self._zone_row_colors(state, colors)
            for col in (_ZONE_COL_NAME, _ZONE_COL_STATE, _ZONE_COL_COUNTDOWN):
                item = self.zone_table.item(row, col)
                item.setBackground(bg)
                item.setForeground(fg)

            container = self._build_zone_action_container(zone_id, state, can_arm, row in zone_selected_rows)
            self.zone_table.setCellWidget(row, _ZONE_COL_ACTION, container)

        self.line_table.setRowCount(len(lines))
        for row, line in enumerate(lines):
            line_id = line["id"]
            self.line_table.setItem(row, _LINE_COL_NAME, QTableWidgetItem(line["name"]))
            self.line_table.setItem(row, _LINE_COL_ZONE, QTableWidgetItem(zone_names.get(line["zone_id"], "?")))
            self.line_table.setItem(row, _LINE_COL_TYPE, QTableWidgetItem(_line_type_name(line["line_type"])))
            self.line_table.setItem(row, _LINE_COL_TAG, QTableWidgetItem(line["tag"]))
            violated_text, bypassed, bg, fg = self._line_row_display(line_id, colors)
            self.line_table.setItem(row, _LINE_COL_VIOLATED, QTableWidgetItem(violated_text))
            for col in (_LINE_COL_NAME, _LINE_COL_ZONE, _LINE_COL_TYPE, _LINE_COL_TAG, _LINE_COL_VIOLATED):
                item = self.line_table.item(row, col)
                item.setBackground(bg)
                item.setForeground(fg)

            container = self._build_line_bypass_container(line_id, bypassed, can_configure, row in line_selected_rows)
            self.line_table.setCellWidget(row, _LINE_COL_BYPASS, container)

    def refresh_live(self):
        """Task 6's own lightweight, tag-driven counterpart to
        refresh() - MainWindow's _on_intrusion_tag_changed() calls THIS,
        not refresh(), on every Security.* tag change. Updates existing
        items/cell widgets in place; never calls setRowCount() or builds
        a new QTableWidgetItem for a cell whose text didn't actually
        change. Falls back to a full refresh() if the row COUNT no
        longer matches what's on screen (a zone/line was added/removed
        from PageIntrusionConfiguration without this page having
        already been told to refresh() - defensive, not expected in
        normal operation since that page always calls back into this
        one - see its own on_zones_or_lines_changed callback)."""
        if self.intrusion_manager is None:
            return
        zones = self.intrusion_manager.get_zones()
        lines = self.intrusion_manager.get_lines()
        if len(zones) != self.zone_table.rowCount() or len(lines) != self.line_table.rowCount():
            self.refresh()
            return
        can_arm = self.access_manager.has_access(AccessLevel.OPERATOR)
        colors = get_theme_manager().current_colors()

        for row in range(self.zone_table.rowCount()):
            name_item = self.zone_table.item(row, _ZONE_COL_NAME)
            if name_item is None:
                continue
            zone_id = name_item.data(Qt.ItemDataRole.UserRole)
            if zone_id is None:
                continue
            state = self.intrusion_manager.get_zone_state(zone_id)
            state_item = self.zone_table.item(row, _ZONE_COL_STATE)
            new_state_text = self._zone_state_text(zone_id, state)
            state_changed = state_item.text() != new_state_text
            if state_changed:
                state_item.setText(new_state_text)
            remaining = self.intrusion_manager.get_countdown_remaining(zone_id)
            countdown_text = f"{remaining}s" if state in (ZoneState.EXIT_DELAY, ZoneState.ENTRY_DELAY) else "-"
            countdown_item = self.zone_table.item(row, _ZONE_COL_COUNTDOWN)
            if countdown_item.text() != countdown_text:
                countdown_item.setText(countdown_text)
            bg, fg = self._zone_row_colors(state, colors)
            for col in (_ZONE_COL_NAME, _ZONE_COL_STATE, _ZONE_COL_COUNTDOWN):
                item = self.zone_table.item(row, col)
                if item.background().color() != bg:
                    item.setBackground(bg)
                if item.foreground().color() != fg:
                    item.setForeground(fg)
            if state_changed:
                # The Arm/Disarm button's LABEL (and the walk-test/
                # alarm-memory suffix baked into new_state_text) only
                # need a fresh container when something about the
                # zone's displayed state actually changed - not every
                # single tick.
                selected = row in {i.row() for i in self.zone_table.selectedIndexes()}
                container = self._build_zone_action_container(zone_id, state, can_arm, selected)
                self.zone_table.setCellWidget(row, _ZONE_COL_ACTION, container)

        for row in range(self.line_table.rowCount()):
            name_item = self.line_table.item(row, _LINE_COL_NAME)
            if name_item is None or row >= len(lines):
                continue
            line_id = lines[row]["id"]
            violated_item = self.line_table.item(row, _LINE_COL_VIOLATED)
            new_text, bypassed, bg, fg = self._line_row_display(line_id, colors)
            text_changed = violated_item.text() != new_text
            if text_changed:
                violated_item.setText(new_text)
            for col in (_LINE_COL_NAME, _LINE_COL_ZONE, _LINE_COL_TYPE, _LINE_COL_TAG, _LINE_COL_VIOLATED):
                item = self.line_table.item(row, col)
                if item.background().color() != bg:
                    item.setBackground(bg)
                if item.foreground().color() != fg:
                    item.setForeground(fg)

    def _build_action_container(self, selected: bool) -> QWidget:
        """A cell holding a setCellWidget() button (Uzbroj/Rozbroj,
        Bypass) never joins the table's own row-selection painting -
        that's an item-view concept, and a cell widget isn't an item -
        so selecting a row would otherwise leave that ONE cell's plain
        background sitting inside an otherwise-highlighted row, looking
        exactly like a rendering glitch ("jasna obwodka"). Fix: bake the
        right background in at construction time, matching `selected` -
        style_transparent_cell_container() the rest of the time, the
        theme's own selection color when this cell's row is selected.
        _resync_action_containers() below (the only caller of this
        outside refresh() - a plain selection click has no other reason
        to touch the tables) always builds a FRESH widget rather than
        restyling the existing one in place, the same way refresh()
        already does for every other reason a container gets rebuilt."""
        container = QWidget()
        if selected:
            colors = get_theme_manager().current_colors()
            container.setStyleSheet(f"background: {colors['accent_bg']}; border: none;")
        else:
            style_transparent_cell_container(container)
        return container

    def _build_zone_action_container(self, zone_id, state, can_arm: bool, selected: bool) -> QWidget:
        container = self._build_action_container(selected)
        btn_layout = QHBoxLayout(container)
        btn_layout.setContentsMargins(2, 2, 2, 2)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if state == ZoneState.DISARMED:
            btn = QPushButton(tr("pages.intrusion.btn_arm"))
            btn.clicked.connect(lambda checked=False, zid=zone_id: self._arm(zid))
        else:
            btn = QPushButton(tr("pages.intrusion.btn_disarm"))
            btn.clicked.connect(lambda checked=False, zid=zone_id: self._disarm(zid))
        btn.setEnabled(can_arm)
        apply_table_button_style(btn)
        btn_layout.addWidget(btn)
        return container

    def _build_line_bypass_container(self, line_id, bypassed: bool, can_configure: bool, selected: bool) -> QWidget:
        container = self._build_action_container(selected)
        btn_layout = QHBoxLayout(container)
        btn_layout.setContentsMargins(2, 2, 2, 2)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn = QPushButton(tr("pages.intrusion.btn_bypass_off") if bypassed
                           else tr("pages.intrusion.btn_bypass_on"))
        btn.setEnabled(can_configure)
        btn.clicked.connect(lambda checked=False, lid=line_id, b=not bypassed: self._bypass(lid, b))
        apply_table_button_style(btn)
        btn_layout.addWidget(btn)
        return container

    def _resync_action_containers(self, *_):
        """Connected to both tables' itemSelectionChanged - a plain
        click doesn't call refresh() (nothing about zone/line state
        actually changed), so this is the only place a selection change
        by itself needs to rebuild the two action-column containers to
        match (see _build_action_container()'s docstring for why a
        rebuild, not a live restyle)."""
        if self.intrusion_manager is None:
            return
        can_arm = self.access_manager.has_access(AccessLevel.OPERATOR)
        can_configure = self.access_manager.has_access(AccessLevel.ENGINEER)
        zone_selected_rows = {index.row() for index in self.zone_table.selectedIndexes()}
        for row in range(self.zone_table.rowCount()):
            name_item = self.zone_table.item(row, _ZONE_COL_NAME)
            if name_item is None:
                continue
            zone_id = name_item.data(Qt.ItemDataRole.UserRole)
            state = self.intrusion_manager.get_zone_state(zone_id)
            container = self._build_zone_action_container(zone_id, state, can_arm, row in zone_selected_rows)
            self.zone_table.setCellWidget(row, _ZONE_COL_ACTION, container)

        lines = self.intrusion_manager.get_lines()
        line_selected_rows = {index.row() for index in self.line_table.selectedIndexes()}
        for row, line in enumerate(lines):
            line_id = line["id"]
            bypassed = self.intrusion_manager.is_line_bypassed(line_id)
            container = self._build_line_bypass_container(line_id, bypassed, can_configure, row in line_selected_rows)
            self.line_table.setCellWidget(row, _LINE_COL_BYPASS, container)

    def _tick(self):
        """Lighter than a full refresh() - just the two things that
        change on their own, once a second, with no Security.* tag
        event to drive them: an exit/entry countdown's remaining
        seconds, and a walk-test's remaining seconds (baked into the
        STATE cell's own text via _zone_state_text()) - avoids
        rebuilding every row (and every button) once a second for
        something that's otherwise static most of the time."""
        for row in range(self.zone_table.rowCount()):
            name_item = self.zone_table.item(row, _ZONE_COL_NAME)
            if name_item is None:
                continue
            zone_id = name_item.data(Qt.ItemDataRole.UserRole)
            if zone_id is None:
                continue
            state = self.intrusion_manager.get_zone_state(zone_id)
            if state in (ZoneState.EXIT_DELAY, ZoneState.ENTRY_DELAY):
                remaining = self.intrusion_manager.get_countdown_remaining(zone_id)
                self.zone_table.item(row, _ZONE_COL_COUNTDOWN).setText(f"{remaining}s")
            if self.intrusion_manager.is_walk_test_active(zone_id):
                self.zone_table.item(row, _ZONE_COL_STATE).setText(self._zone_state_text(zone_id, state))
        # A zone actually finishing its countdown (EXIT_DELAY -> ARMED,
        # ENTRY_DELAY -> ALARM) or a walk-test auto-expiring both write a
        # Security.* tag from IntrusionManager's own background timer
        # thread - which reaches this page through the normal tag_changed
        # bridge -> on_tag_changed() -> refresh_live() path (see
        # MainWindow's tag_changed wiring), same as every other tag-
        # driven page in this app. This timer's only job is the cosmetic
        # once-a-second tick while something is counting down; it does
        # not need to detect either transition itself.

    # --- actions ---------------------------------------------------------

    def _arm(self, zone_id):
        if self.intrusion_manager is None:  # can't actually happen - no rows/buttons without one
            return
        if not self.window().request_access(AccessLevel.OPERATOR):
            return
        result = self.intrusion_manager.arm_zone(zone_id, actor=self.access_manager.level,
                                                  level=self.access_manager.level)
        if result.needs_confirmation:
            zone = next((z for z in self.intrusion_manager.get_zones() if z["id"] == zone_id), None)
            lines_by_id = {l["id"]: l for l in self.intrusion_manager.get_lines()}
            violated_names = [lines_by_id[lid]["name"] for lid in result.violated_line_ids if lid in lines_by_id]
            fault_names = [lines_by_id[lid]["name"] for lid in result.fault_line_ids if lid in lines_by_id]
            popup = ArmConfirmPopup(zone["name"] if zone else zone_id, violated_names, fault_names, self)
            if popup.exec():
                self.intrusion_manager.arm_zone(zone_id, actor=self.access_manager.level,
                                                 level=self.access_manager.level, force=True)
        self.refresh()

    def _disarm(self, zone_id):
        if self.intrusion_manager is None:  # can't actually happen - no rows/buttons without one
            return
        if not self.window().request_access(AccessLevel.OPERATOR):
            return
        self.intrusion_manager.disarm_zone(zone_id, actor=self.access_manager.level, level=self.access_manager.level)
        self.refresh()

    def _bypass(self, line_id, bypassed):
        if self.intrusion_manager is None:  # can't actually happen - no rows/buttons without one
            return
        if not self.window().request_access(AccessLevel.ENGINEER):
            return
        self.intrusion_manager.bypass_line(line_id, bypassed, actor=self.access_manager.level,
                                            level=self.access_manager.level)
        self.refresh()

    # --- alarm memory (Task 3) ---------------------------------------------

    def _show_alarm_memory(self):
        if self.intrusion_manager is None:  # isolated widget test / mock - nothing to show
            return
        zones = self.intrusion_manager.get_zones()
        if not zones:
            QMessageBox.information(self, tr("pages.intrusion.alarm_memory_title"),
                                     tr("pages.intrusion.err_no_zones_yet"))
            return
        dialog = AlarmMemoryDialog(self.intrusion_manager, zones, self._clear_alarm_memory, parent=self)
        dialog.exec()
        self.refresh()

    def _clear_alarm_memory(self, zone_id) -> bool:
        """Passed into AlarmMemoryDialog as its on_clear_requested
        callback - PIN-gates the SAME way every other action on this
        page does (self.window().request_access()), THEN calls the
        manager, which re-checks the level itself regardless (defense
        in depth, same pattern _arm()/_disarm()/_bypass() already use)."""
        if not self.window().request_access(AccessLevel.OPERATOR):
            return False
        return self.intrusion_manager.clear_alarm_memory(zone_id, actor=self.access_manager.level,
                                                           level=self.access_manager.level)

    # --- walk-test mode (Task 4) --------------------------------------------

    def _show_walk_test(self):
        if self.intrusion_manager is None:  # isolated widget test / mock - nothing to show
            return
        if not self.window().request_access(AccessLevel.ENGINEER):
            return
        zones = self.intrusion_manager.get_zones()
        if not zones:
            QMessageBox.information(self, tr("pages.intrusion.walk_test_title"),
                                     tr("pages.intrusion.err_no_zones_yet"))
            return
        dialog = WalkTestDialog(self.intrusion_manager, zones, self._start_walk_test_for,
                                 self._stop_walk_test_for, parent=self)
        dialog.exec()
        self.refresh()

    def _start_walk_test_for(self, zone_id, duration_seconds) -> bool:
        # Engineer level already confirmed once, opening the dialog
        # itself (_show_walk_test() above) - not re-prompted per click
        # inside it, same "one PIN per dialog session" stance the
        # Manage Zones/Lines CRUD dialog already has.
        return self.intrusion_manager.start_walk_test(zone_id, actor=self.access_manager.level,
                                                        level=self.access_manager.level,
                                                        duration_seconds=duration_seconds)

    def _stop_walk_test_for(self, zone_id):
        return self.intrusion_manager.stop_walk_test(zone_id, actor=self.access_manager.level,
                                                       level=self.access_manager.level)


class PageIntrusionHistory(QWidget):
    """Task (page-split): SYSTEM ALARMOWY > Historia zdarzen - promoted
    from a tab inside the old single intrusion page to its own nav
    entry; functionally unchanged (filter by zone/event type/date range,
    export CSV) except "Configure Retention" moved to
    PageIntrusionConfiguration (a KONFIGURACJA concern, not something to
    view alongside day-to-day history browsing). No access gate of its
    own to VIEW - matches today's behavior exactly (only Configure
    Retention ever required Engineer, and that button is gone from this
    page now)."""

    def __init__(self, intrusion_manager, access_manager, parent=None):
        super().__init__(parent)
        self.intrusion_manager = intrusion_manager
        self.access_manager = access_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel(tr("nav.intrusion_history"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PageHeader")
        layout.addWidget(title)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel(tr("pages.intrusion.lbl_history_zone")))
        self.combo_history_zone = QComboBox()
        self.combo_history_zone.addItem(tr("pages.intrusion.history_all_zones"), None)
        filter_row.addWidget(self.combo_history_zone)

        filter_row.addWidget(QLabel(tr("pages.intrusion.lbl_history_event_type")))
        self.combo_history_event_type = QComboBox()
        self.combo_history_event_type.addItem(tr("pages.intrusion.history_all_event_types"), None)
        filter_row.addWidget(self.combo_history_event_type)

        filter_row.addWidget(QLabel(tr("pages.intrusion.lbl_history_from")))
        self.date_history_from = QDateEdit()
        self.date_history_from.setCalendarPopup(True)
        self.date_history_from.setDate(QDate.currentDate().addDays(-7))
        filter_row.addWidget(self.date_history_from)

        filter_row.addWidget(QLabel(tr("pages.intrusion.lbl_history_to")))
        self.date_history_to = QDateEdit()
        self.date_history_to.setCalendarPopup(True)
        self.date_history_to.setDate(QDate.currentDate())
        filter_row.addWidget(self.date_history_to)

        self.btn_history_apply = QPushButton(tr("pages.intrusion.btn_apply_filters"))
        self.btn_history_apply.clicked.connect(self._refresh_history_tab)
        filter_row.addWidget(self.btn_history_apply)
        layout.addLayout(filter_row)

        action_row = QHBoxLayout()
        action_row.addStretch()
        self.btn_history_export = QPushButton(tr("pages.intrusion.btn_export_csv"))
        self.btn_history_export.clicked.connect(self._export_history_to_csv)
        action_row.addWidget(self.btn_history_export)
        layout.addLayout(action_row)

        self.history_table = QTableWidget(0, 6)
        self.history_headers = [
            tr("pages.intrusion.col_history_time"), tr("pages.intrusion.col_history_event_type"),
            tr("pages.intrusion.col_history_zone"), tr("pages.intrusion.col_history_line"),
            tr("pages.intrusion.col_history_actor"), tr("pages.intrusion.col_history_detail"),
        ]
        self.history_table.setHorizontalHeaderLabels(self.history_headers)
        set_resizable_columns(self.history_table.horizontalHeader(), [150, 210, 120, 120, 90, 0], stretch_last=True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.history_table)

        self._refresh_history_zone_filter()

    def showEvent(self, event):
        """Zones can be added/edited/removed from PageIntrusionConfiguration
        (a different page/class now) - refresh the zone-filter combo
        every time this page becomes visible, rather than needing that
        page to know this one exists at all (kept as two independent
        pages, loosely coupled through IntrusionManager itself, not
        through each other)."""
        super().showEvent(event)
        self._refresh_history_zone_filter()

    # --- alarm event history (Task 5) ---------------------------------------

    def _refresh_history_zone_filter(self):
        if self.intrusion_manager is None:  # isolated widget test / mock
            return
        zones = self.intrusion_manager.get_zones()
        current = self.combo_history_zone.currentData()
        self.combo_history_zone.blockSignals(True)
        self.combo_history_zone.clear()
        self.combo_history_zone.addItem(tr("pages.intrusion.history_all_zones"), None)
        for zone in zones:
            self.combo_history_zone.addItem(zone["name"], zone["id"])
        idx = self.combo_history_zone.findData(current)
        self.combo_history_zone.setCurrentIndex(idx if idx >= 0 else 0)
        self.combo_history_zone.blockSignals(False)

    def _refresh_history_tab(self):
        if self.intrusion_manager is None:  # isolated widget test / mock - nothing to query
            return
        self._refresh_history_zone_filter()
        # Event-type choices are populated HERE (on "Apply filters"),
        # not eagerly - they only ever grow as new kinds of events
        # actually get recorded, so re-reading them every keystroke/tick
        # would be pure waste for something that changes this rarely.
        current_type = self.combo_history_event_type.currentData()
        self.combo_history_event_type.blockSignals(True)
        self.combo_history_event_type.clear()
        self.combo_history_event_type.addItem(tr("pages.intrusion.history_all_event_types"), None)
        for event_type in self.intrusion_manager.get_history_event_types():
            self.combo_history_event_type.addItem(event_type, event_type)
        idx = self.combo_history_event_type.findData(current_type)
        self.combo_history_event_type.setCurrentIndex(idx if idx >= 0 else 0)
        self.combo_history_event_type.blockSignals(False)

        zone_id = self.combo_history_zone.currentData()
        event_type = self.combo_history_event_type.currentData()
        start = datetime.combine(self.date_history_from.date().toPython(), datetime.min.time())
        end = datetime.combine(self.date_history_to.date().toPython(), datetime.min.time()) + timedelta(days=1)
        rows = self.intrusion_manager.query_alarm_history(limit=2000, zone_id=zone_id, event_type=event_type,
                                                            start=start, end=end)
        self.history_table.setRowCount(len(rows))
        for row, entry in enumerate(rows):
            values = [
                entry.timestamp.strftime("%Y-%m-%d %H:%M:%S") if entry.timestamp else "-",
                entry.event_type or "", entry.zone_name or entry.zone_id or "",
                entry.line_name or entry.line_id or "", entry.actor or "", entry.detail or "",
            ]
            for col, value in enumerate(values):
                self.history_table.setItem(row, col, QTableWidgetItem(value))

    def _export_history_to_csv(self):
        """Same recipe every other page's own CSV export already uses
        (page_event_recorder.py's export_rows_to_csv(), service_notes.py's
        build_device_report_csv()) - Task: "wykorzystaj ISTNIEJACY
        mechanizm eksportu, nie buduj drugiego" - exports exactly what's
        currently in the (already filtered) history table, not a fresh
        unfiltered DB query."""
        rows = self.history_table.rowCount()
        if rows == 0:
            QMessageBox.information(self, tr("nav.intrusion_history"), tr("pages.intrusion.msg_no_history"))
            return
        default_name = f"epw_intrusion_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path, _ = QFileDialog.getSaveFileName(self, tr("pages.intrusion.btn_export_csv"), default_name,
                                               tr("pages.historian_export.csv_filter"))
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.history_headers)
                for row in range(rows):
                    writer.writerow([
                        self.history_table.item(row, c).text() if self.history_table.item(row, c) else ""
                        for c in range(self.history_table.columnCount())
                    ])
        except OSError as e:
            QMessageBox.warning(self, tr("pages.intrusion.btn_export_csv"),
                                 tr("pages.event_recorder.err_export_failed", error=e))
            return
        QMessageBox.information(self, tr("pages.intrusion.btn_export_csv"),
                                 tr("pages.event_recorder.msg_exported", n=rows, path=path))


class PageIntrusionConfiguration(QWidget):
    """Task (page-split): SYSTEM ALARMOWY > Konfiguracja - installer-only
    setup, split out of the old single intrusion page: zones/lines
    (add/edit/remove, input modes, EOL/DEOL windows, false-alarm
    filters), power supervision, and history retention. "Dostep:
    wylacznie Engineer" - the WHOLE PAGE, not just individual buttons,
    same "gate the page itself, don't just disable one button" pattern
    page_audit_log.py already established for its own Engineer-only
    view. `on_zones_or_lines_changed`, if given, is called after any
    zone/line add/edit/remove so PageIntrusionOverview (a separate page/
    class now) can refresh its own tables - the one place these two
    pages are wired together at all, kept to exactly this one callback
    rather than either page reaching into the other's internals."""

    def __init__(self, intrusion_manager, access_manager, audit_logger=None,
                 on_zones_or_lines_changed=None, parent=None):
        super().__init__(parent)
        self.intrusion_manager = intrusion_manager
        self.access_manager = access_manager
        self.audit_logger = audit_logger
        self.on_zones_or_lines_changed = on_zones_or_lines_changed

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel(tr("nav.intrusion_config"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PageHeader")
        layout.addWidget(title)

        self.lbl_gate = QLabel("")
        self.lbl_gate.setStyleSheet(neutral_text_style("font-style: italic;"))
        layout.addWidget(self.lbl_gate)

        self.btn_configure_zones = QPushButton(tr("pages.intrusion.btn_configure_zones"))
        self.btn_configure_zones.clicked.connect(self._configure_zones)
        layout.addWidget(self.btn_configure_zones)
        self.btn_configure_lines = QPushButton(tr("pages.intrusion.btn_configure_lines"))
        self.btn_configure_lines.clicked.connect(self._configure_lines)
        layout.addWidget(self.btn_configure_lines)
        self.btn_power_supervision = QPushButton(tr("pages.intrusion.btn_power_supervision"))
        self.btn_power_supervision.clicked.connect(self._configure_power_supervision)
        layout.addWidget(self.btn_power_supervision)
        self.btn_history_retention = QPushButton(tr("pages.intrusion.btn_configure_retention"))
        self.btn_history_retention.clicked.connect(self._configure_history_retention)
        layout.addWidget(self.btn_history_retention)
        layout.addStretch()

        self.access_manager.level_changed.connect(self.refresh)
        self.refresh()

    def refresh(self, *_):
        can_configure = self.access_manager.has_access(AccessLevel.ENGINEER)
        for btn in (self.btn_configure_zones, self.btn_configure_lines,
                    self.btn_power_supervision, self.btn_history_retention):
            btn.setEnabled(can_configure)
        self.lbl_gate.setText("" if can_configure else tr("pages.intrusion.gate_configure_message"))

    def _notify_zones_or_lines_changed(self):
        if self.on_zones_or_lines_changed is not None:
            self.on_zones_or_lines_changed()

    # --- configuration (Engineer-only) ------------------------------------

    def _configure_zones(self):
        if self.intrusion_manager is None:  # isolated widget test / mock - nothing to configure
            return
        if not self.window().request_access(AccessLevel.ENGINEER):
            return
        # A lightweight in-page dialog listing zones with Add/Edit/Remove -
        # built inline rather than as a separate module-level class since
        # it's a thin CRUD wrapper around IntrusionManager's own
        # add_zone()/update_zone()/remove_zone(), same pragmatic choice
        # this codebase's other one-off "manage a list" dialogs make.
        run_crud_dialog(
            self,
            title=tr("pages.intrusion.manage_zones_title"),
            get_items=self.intrusion_manager.get_zones,
            item_label=lambda z: z["name"],
            open_add_dialog=lambda: ZoneConfigDialog(None, self),
            open_edit_dialog=lambda item: ZoneConfigDialog(item, self),
            on_add=lambda dlg: self.intrusion_manager.add_zone(
                dlg.result_name(), dlg.result_exit_delay(), dlg.result_entry_delay(),
                level=self.access_manager.level),
            on_edit=lambda item, dlg: self.intrusion_manager.update_zone(
                item["id"], dlg.result_name(), dlg.result_exit_delay(), dlg.result_entry_delay(),
                level=self.access_manager.level),
            on_remove=lambda item: self.intrusion_manager.remove_zone(item["id"], level=self.access_manager.level),
            remove_refused_message=tr("pages.intrusion.err_zone_has_lines"),
        )
        self._notify_zones_or_lines_changed()

    def _configure_lines(self):
        if self.intrusion_manager is None:  # isolated widget test / mock - nothing to configure
            return
        if not self.window().request_access(AccessLevel.ENGINEER):
            return
        zones = self.intrusion_manager.get_zones()
        if not zones:
            QMessageBox.information(self, tr("pages.intrusion.manage_lines_title"),
                                     tr("pages.intrusion.err_no_zones_yet"))
            return
        digital_candidates = self.intrusion_manager.get_digital_input_candidates()
        analog_candidates = self.intrusion_manager.get_analog_input_candidates()
        run_crud_dialog(
            self,
            title=tr("pages.intrusion.manage_lines_title"),
            get_items=self.intrusion_manager.get_lines,
            item_label=lambda l: l["name"],
            open_add_dialog=lambda: LineConfigDialog(zones, digital_candidates, analog_candidates, None, self),
            open_edit_dialog=lambda item: LineConfigDialog(zones, digital_candidates, analog_candidates, item, self),
            on_add=lambda dlg: self.intrusion_manager.add_line(
                dlg.result_name(), dlg.result_zone_id(), dlg.result_tag(),
                dlg.result_normal_state(), dlg.result_line_type(), level=self.access_manager.level,
                min_violation_seconds=dlg.result_min_violation_seconds(),
                multiplicity_count=dlg.result_multiplicity_count(),
                multiplicity_window_seconds=dlg.result_multiplicity_window_seconds(),
                lockout_after_count=dlg.result_lockout_after_count(),
                alarm_hold_seconds=dlg.result_alarm_hold_seconds(),
                silence_threshold_seconds=dlg.result_silence_threshold_seconds(),
                input_mode=dlg.result_input_mode(), parametrization=dlg.result_parametrization(),
                value_windows=dlg.result_value_windows()),
            on_edit=lambda item, dlg: self.intrusion_manager.update_line(
                item["id"], dlg.result_name(), dlg.result_zone_id(), dlg.result_tag(),
                dlg.result_normal_state(), dlg.result_line_type(), level=self.access_manager.level,
                min_violation_seconds=dlg.result_min_violation_seconds(),
                multiplicity_count=dlg.result_multiplicity_count(),
                multiplicity_window_seconds=dlg.result_multiplicity_window_seconds(),
                lockout_after_count=dlg.result_lockout_after_count(),
                alarm_hold_seconds=dlg.result_alarm_hold_seconds(),
                silence_threshold_seconds=dlg.result_silence_threshold_seconds(),
                input_mode=dlg.result_input_mode(), parametrization=dlg.result_parametrization(),
                value_windows=dlg.result_value_windows()),
            on_remove=lambda item: self.intrusion_manager.remove_line(item["id"], level=self.access_manager.level),
            remove_refused_message=None,
        )
        self._notify_zones_or_lines_changed()

    def _configure_power_supervision(self):
        if self.intrusion_manager is None:  # isolated widget test / mock - nothing to configure
            return
        if not self.window().request_access(AccessLevel.ENGINEER):
            return
        digital_candidates = self.intrusion_manager.get_digital_input_candidates()
        current = self.intrusion_manager.get_power_supervision_config()
        dialog = PowerSupervisionDialog(digital_candidates, current, self)
        if dialog.exec():
            self.intrusion_manager.configure_power_supervision(
                mains_tag=dialog.result_mains_tag() or None, mains_ok_state=dialog.result_mains_ok_state(),
                battery_tag=dialog.result_battery_tag() or None, battery_ok_state=dialog.result_battery_ok_state(),
                level=self.access_manager.level)

    def _configure_history_retention(self):
        if self.intrusion_manager is None:  # isolated widget test / mock - nothing to configure
            return
        if not self.window().request_access(AccessLevel.ENGINEER):
            return
        current = self.intrusion_manager.get_history_retention_config()
        dialog = HistoryRetentionDialog(current, self)
        if dialog.exec():
            self.intrusion_manager.configure_history_retention(
                max_events=dialog.result_max_events(), max_days=dialog.result_max_days(),
                level=self.access_manager.level)
