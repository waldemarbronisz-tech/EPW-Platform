from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QFrame, QFormLayout, QCheckBox, QTabWidget, QWidget)
from PySide6.QtCore import Qt
from datetime import datetime
from epw_os.core.switching_counters import format_duration
from epw_os.gui.theme_manager import current_colors
from epw_os.gui.widgets.service_notes_widget import ServiceNotesWidget
from epw_os.i18n import tr


def _format_epoch(epoch_seconds):
    """Local date/time for a switching-counter timestamp (epoch seconds,
    or None if no transition has ever been recorded) - "N/A" untranslated,
    same "don't translate a placeholder value" policy as the rest of
    this file's device-properties fields."""
    if epoch_seconds is None:
        return "N/A"
    return datetime.fromtimestamp(epoch_seconds).strftime("%Y-%m-%d %H:%M:%S")


class DeviceControlPopup(QDialog):
    def __init__(self, device, parent=None, switching_counters=None, service_notes=None):
        super().__init__(parent)
        self.device = device
        # Qt-free (see epw_os/core/switching_counters.py) - may be None
        # (isolated widget tests, or a device with no counter_tag - not
        # every SynopticWidget represents a DI-tracked switching device).
        self.switching_counters = switching_counters
        # Qt-free too (see epw_os/core/service_notes.py) - forwarded to
        # Properties (show_properties() below), where the "Notatki" tab
        # actually lives (Task: "okno aparatu" - Properties is the
        # device's own detail window, reached from here).
        self.service_notes = service_notes
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("IndustrialDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        title = QLabel(self.device.tag_name)
        title.setObjectName("SectionHeader")
        layout.addWidget(title)

        desc = QLabel(getattr(self.device, "description", tr("pages.popups.default_device")))
        layout.addWidget(desc)

        state_str = tr("pages.common.state_closed") if self.device.state == 1 else tr("pages.common.state_open")
        layout.addWidget(QLabel(tr("pages.popups.current_state", state=state_str)))

        # Switching (mechanical wear) counter (Task: liczba przelaczen i
        # czas w stanie zamknietym per aparat) - "the device's window on
        # Main View". Full detail (first/last transition, threshold)
        # lives one level down in Properties (show_properties() below) -
        # this is just the at-a-glance summary.
        counter_tag = getattr(self.device, "counter_tag", None)
        if self.switching_counters is not None and counter_tag is not None:
            snap = self.switching_counters.get_snapshot(counter_tag)
            lbl_counter = QLabel(tr(
                "pages.popups.switching_summary",
                closes=snap["closes"], opens=snap["opens"],
                closed_time=format_duration(snap["closed_seconds"]),
            ))
            if self.switching_counters.is_over_threshold(counter_tag):
                lbl_counter.setStyleSheet(f"color: {current_colors()['state_alarm']}; font-weight: bold;")
                lbl_counter.setText(lbl_counter.text() + " " + tr("pages.popups.switching_threshold_warning"))
            layout.addWidget(lbl_counter)

        # Interlock Validation via Engine
        theme_colors = current_colors()
        interlock_msg = tr("pages.popups.interlock_ok")
        interlock_color = theme_colors["state_ok_text"]
        can_open = True
        can_close = True

        main_window = parent.window()
        if hasattr(main_window, 'command_manager'):
            # Only validate opposite state command
            cmd_to_check = "open" if self.device.state == 1 else "close"
            valid, reasons = main_window.command_manager.request_command(self.device.tag_name, cmd_to_check, validate_only=True)
            if not valid:
                interlock_msg = tr("pages.popups.interlock_blocked",
                                    reasons="\n".join([f"- {r}" for r in reasons]))
                interlock_color = theme_colors["state_alarm"]
                if cmd_to_check == "open": can_open = False
                if cmd_to_check == "close": can_close = False
            else:
                # Bug 2: logic_project == null is a normal, expected state,
                # not a fault - the command above was correctly permitted.
                # Still worth telling the operator plainly that no logic
                # interlock graph is active, rather than implying one was
                # evaluated and passed (a neutral message, not a failure -
                # see SESSION_REPORT.md). getattr/hasattr guards keep this
                # safe against test doubles that stand in for LogicEngine
                # without an is_configured() method (see test_core.py).
                logic_engine = getattr(main_window.command_manager, "logic_engine", None)
                if logic_engine is not None and hasattr(logic_engine, "is_configured") \
                        and not logic_engine.is_configured():
                    interlock_msg = tr("pages.popups.interlock_not_configured")
                    interlock_color = theme_colors["text_disabled"]

        self.lbl_interlock = QLabel(interlock_msg)
        self.lbl_interlock.setStyleSheet(f"color: {interlock_color};")
        layout.addWidget(self.lbl_interlock)

        # Actions
        btn_layout = QHBoxLayout()
        self.btn_open = QPushButton(tr("pages.popups.btn_open"))
        self.btn_close = QPushButton(tr("pages.popups.btn_close"))

        if self.device.state == 1:
            self.btn_close.setEnabled(False)
            if not can_open: self.btn_open.setEnabled(False)
        else:
            self.btn_open.setEnabled(False)
            if not can_close: self.btn_close.setEnabled(False)

        btn_layout.addWidget(self.btn_open)
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

        self.btn_props = QPushButton(tr("pages.popups.btn_properties"))
        self.btn_hist = QPushButton(tr("pages.popups.btn_history"))
        layout.addWidget(self.btn_props)
        layout.addWidget(self.btn_hist)

        self.btn_props.clicked.connect(self.show_properties)

        self.cmd_str = ""
        self.btn_open.clicked.connect(lambda: self.on_action("OPEN"))
        self.btn_close.clicked.connect(lambda: self.on_action("CLOSE"))

    def on_action(self, cmd):
        # Additional interlock to explicitly reject commands if already in the requested state
        requested_state = 1 if cmd == "CLOSE" else 0
        if self.device.state == requested_state:
            from epw_os.gui.logger import ui_logger
            ui_logger.log("WARNING", "OPERATION", self.device.tag_name, "Command rejected", "Operator", "Unknown", "Device already in requested state")
            self.reject()
            return
            
        self.cmd_str = cmd
        self.accept()

    def show_properties(self):
        self.accept()
        DevicePropertiesPopup(self.device, self.parent(), switching_counters=self.switching_counters,
                               service_notes=self.service_notes).exec()

class ConfirmationPopup(QDialog):
    def __init__(self, device_name, current_state, requested_cmd, user="Operator", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("IndustrialDialog")

        layout = QVBoxLayout(self)

        title = QLabel(tr("pages.popups.confirm_title"))
        title.setObjectName("SectionHeader")
        layout.addWidget(title)

        msg = QLabel(tr("pages.popups.confirm_message"))
        msg.setStyleSheet("font-weight: bold;")
        layout.addWidget(msg)

        form = QFormLayout()
        form.addRow(tr("pages.popups.lbl_object"), QLabel(device_name))
        form.addRow(tr("pages.popups.lbl_current_state"), QLabel(current_state))
        form.addRow(tr("pages.popups.lbl_requested"), QLabel(requested_cmd))
        form.addRow(tr("pages.popups.lbl_user"), QLabel(user))
        form.addRow(tr("pages.popups.lbl_time"), QLabel(datetime.now().strftime("%H:%M:%S")))
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.btn_confirm = QPushButton(tr("pages.popups.btn_confirm"))
        self.btn_cancel = QPushButton(tr("pages.popups.btn_cancel"))
        btn_layout.addWidget(self.btn_confirm)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_confirm.clicked.connect(self.accept)

class ForceOutputConfirmPopup(QDialog):
    """Deliberately more alarming than ConfirmationPopup - this gates the
    Engineer-only manual "Force" override on Control Outputs, a
    commissioning/testing tool that must never be reached by accident. Bold
    red header, explicit "this is not normal operation" copy, and a
    button labeled with the actual action rather than a generic OK."""
    def __init__(self, device_name, current_state, requested_cmd, user="Engineer", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("IndustrialDialog")

        layout = QVBoxLayout(self)

        theme_colors = current_colors()
        title = QLabel(tr("pages.popups.force_title"))
        title.setStyleSheet(
            f"font-weight: bold; background: {theme_colors['action_danger']}; "
            f"color: {theme_colors['state_warning']}; padding: 5px; font-size: 13px;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        msg = QLabel(tr("pages.popups.force_warning"))
        msg.setStyleSheet(f"font-weight: bold; color: {theme_colors['action_danger']};")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg)

        form = QFormLayout()
        form.addRow(tr("pages.popups.lbl_object"), QLabel(device_name))
        form.addRow(tr("pages.popups.lbl_current_state"), QLabel(current_state))
        form.addRow(tr("pages.popups.lbl_forcing_to"), QLabel(requested_cmd))
        form.addRow(tr("pages.popups.lbl_user"), QLabel(user))
        form.addRow(tr("pages.popups.lbl_time"), QLabel(datetime.now().strftime("%H:%M:%S")))
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.btn_confirm = QPushButton(tr("pages.popups.btn_force_confirm", cmd=requested_cmd))
        self.btn_confirm.setStyleSheet(f"color: {theme_colors['action_danger']}; font-weight: bold;")
        self.btn_cancel = QPushButton(tr("pages.popups.btn_cancel"))
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_confirm)
        layout.addLayout(btn_layout)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_confirm.clicked.connect(self.accept)
        self.btn_cancel.setFocus()

class SettingChangePopup(QDialog):
    def __init__(self, object_name, field, old_value, new_value, user="Engineer", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("IndustrialDialog")

        layout = QVBoxLayout(self)

        title = QLabel(tr("pages.popups.setting_change_title"))
        title.setObjectName("SectionHeader")
        layout.addWidget(title)

        msg = QLabel(tr("pages.popups.setting_change_message"))
        msg.setStyleSheet("font-weight: bold;")
        layout.addWidget(msg)

        form = QFormLayout()
        form.addRow(tr("pages.popups.lbl_object"), QLabel(object_name))
        form.addRow(tr("pages.popups.lbl_field"), QLabel(field))
        form.addRow(tr("pages.popups.lbl_current_value"), QLabel(str(old_value)))
        lbl_new = QLabel(str(new_value))
        lbl_new.setStyleSheet(f"font-weight: bold; color: {current_colors()['accent_bg']};")
        form.addRow(tr("pages.popups.lbl_new_value"), lbl_new)
        form.addRow(tr("pages.popups.lbl_user"), QLabel(user))
        form.addRow(tr("pages.popups.lbl_time"), QLabel(datetime.now().strftime("%H:%M:%S")))
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.btn_confirm = QPushButton(tr("pages.popups.btn_confirm"))
        self.btn_cancel = QPushButton(tr("pages.popups.btn_cancel"))
        btn_layout.addWidget(self.btn_confirm)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_confirm.clicked.connect(self.accept)
        self.btn_cancel.setFocus()

class InterlockFailurePopup(QDialog):
    def __init__(self, action, device_name, checks, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("IndustrialDialog")

        layout = QVBoxLayout(self)

        theme_colors = current_colors()
        title = QLabel(tr("pages.popups.interlock_failure_title"))
        title.setStyleSheet(
            f"font-weight: bold; background: {theme_colors['action_danger']}; "
            f"color: {theme_colors['accent_text']}; padding: 2px;"
        )
        layout.addWidget(title)

        layout.addWidget(QLabel(tr("pages.popups.command_rejected")))
        layout.addWidget(QLabel(tr("pages.popups.lbl_reasons")))

        for rule_name, ok in checks:
            cb = QCheckBox(rule_name)
            cb.setChecked(ok)
            cb.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            cb.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            layout.addWidget(cb)

        btn = QPushButton(tr("dialog.ok"))
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

class CommandFailedPopup(QDialog):
    def __init__(self, device_name, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("IndustrialDialog")

        layout = QVBoxLayout(self)

        theme_colors = current_colors()
        title = QLabel(tr("pages.popups.command_failed_title"))
        title.setStyleSheet(
            f"font-weight: bold; background: {theme_colors['action_danger']}; color: {theme_colors['accent_text']};"
        )
        layout.addWidget(title)

        layout.addWidget(QLabel(tr("pages.popups.command_failed_message", device=device_name)))

        btn = QPushButton(tr("dialog.ok"))
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

class DevicePropertiesPopup(QDialog):
    """The device's own detail window on Main View - Task's "okno
    aparatu" for the "Notatki" tab (reached via DeviceControlPopup's
    Properties button). Tab 1 is the properties form that already
    existed before this task, unchanged in content; Tab 2 is the new
    service-history log (epw_os/gui/widgets/service_notes_widget.py).
    A single Export CSV button below both tabs combines everything on
    Tab 1 with the full notes history (Task: "eksport notatek do CSV
    razem z reszta danych aparatu") - one file, not two."""

    def __init__(self, device, parent=None, switching_counters=None, service_notes=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog)
        self.setWindowTitle(tr("pages.popups.device_properties_title"))
        self.setStyleSheet(f"background: {current_colors()['panel_bg']};")
        self.setMinimumSize(380, 420)

        outer = QVBoxLayout(self)
        tabs = QTabWidget()
        outer.addWidget(tabs, stretch=1)

        # --- Tab 1: Properties (same fields/order as before this task) -
        props_page = QWidget()
        form = QFormLayout(props_page)

        # `self._properties` also backs the combined CSV export below -
        # built alongside the form instead of re-derived from it, so the
        # export can't silently drift from what's actually on screen.
        # Field labels/keys are translated for display; the values
        # themselves are device object attributes / fallback defaults
        # (N/A, None, Enabled, OK), left as-is - same "don't translate
        # data/placeholder values" policy applied to System Topology's
        # fabricated telemetry.
        self._properties = {}

        def _add_row(label_key, value):
            form.addRow(tr(label_key), QLabel(str(value)))
            self._properties[tr(label_key)] = str(value)

        _add_row("pages.popups.lbl_name", getattr(device, "name", device.tag_name))
        _add_row("pages.popups.lbl_description", getattr(device, "description", "N/A"))
        _add_row("pages.popups.lbl_position", f"{device.pos().x()}, {device.pos().y()}")
        _add_row("pages.popups.lbl_rotation", getattr(device, "rotation", 0))
        _add_row("pages.popups.lbl_visibility", device.isVisible())
        _add_row("pages.popups.lbl_tag", device.tag_name)
        _add_row("pages.popups.lbl_alarm", getattr(device, "alarm", "None"))
        _add_row("pages.popups.lbl_animation", getattr(device, "animation", "Enabled"))
        _add_row("pages.popups.lbl_communication", getattr(device, "communication", "OK"))

        # Switching (mechanical wear) counter - full detail (Task: liczba
        # przelaczen, czas w stanie zamknietym, pierwsze/ostatnie
        # przelaczenie). Omitted entirely for a device with no
        # counter_tag (not every SynopticWidget is a DI-tracked
        # switching device) or with switching_counters unavailable.
        counter_tag = getattr(device, "counter_tag", None)
        if switching_counters is not None and counter_tag is not None:
            snap = switching_counters.get_snapshot(counter_tag)
            _add_row("pages.popups.lbl_switching_closes", snap["closes"])
            _add_row("pages.popups.lbl_switching_opens", snap["opens"])
            _add_row("pages.popups.lbl_switching_closed_time", format_duration(snap["closed_seconds"]))
            _add_row("pages.popups.lbl_switching_first", _format_epoch(snap["first_transition"]))
            _add_row("pages.popups.lbl_switching_last", _format_epoch(snap["last_transition"]))
            threshold = snap.get("warning_threshold")
            if threshold is not None:
                lbl_threshold = QLabel(str(threshold))
                if switching_counters.is_over_threshold(counter_tag):
                    lbl_threshold.setStyleSheet(f"color: {current_colors()['state_alarm']}; font-weight: bold;")
                form.addRow(tr("pages.popups.lbl_switching_threshold"), lbl_threshold)
                self._properties[tr("pages.popups.lbl_switching_threshold")] = str(threshold)

        tabs.addTab(props_page, tr("pages.popups.tab_properties"))

        # --- Tab 2: Notatki (Task) --------------------------------------
        # Same tag identity as the counters above (counter_tag, the DI
        # feedback tag) rather than device.tag_name (the DO0N command
        # tag) - so a note added here is the exact same history as the
        # one shown for that DI row in the Digital Inputs table, not a
        # third, disconnected list.
        note_tag = counter_tag or device.tag_name
        self._note_tag = note_tag
        self._service_notes = service_notes
        main_window = parent.window() if parent is not None else None
        access_manager = getattr(main_window, "access_manager", None)
        self._notes_widget = ServiceNotesWidget(note_tag, service_notes, access_manager)
        tabs.addTab(self._notes_widget, tr("pages.popups.tab_notes"))

        btn_row = QHBoxLayout()
        btn_export = QPushButton(tr("pages.popups.btn_export_csv"))
        btn_export.clicked.connect(self._export_csv)
        btn_row.addWidget(btn_export)
        btn_row.addStretch()
        btn = QPushButton(tr("dialog.close"))
        btn.clicked.connect(self.accept)
        btn_row.addWidget(btn)
        outer.addLayout(btn_row)

    def _export_csv(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from epw_os.core.service_notes import build_device_report_csv
        default_name = f"{self._note_tag}_device_report.csv"
        path, _ = QFileDialog.getSaveFileName(self, tr("pages.popups.btn_export_csv"), default_name, "CSV (*.csv)")
        if not path:
            return
        notes = self._notes_widget.collect_notes_for_export()
        csv_text = build_device_report_csv(self._properties, notes)
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                f.write(csv_text)
        except OSError as e:
            QMessageBox.warning(self, tr("pages.popups.btn_export_csv"), str(e))

class TopologyDiagnosticsPopup(QDialog):
    def __init__(self, device_name, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog)
        self.setWindowTitle(tr("pages.popups.diagnostics_title", device=device_name))
        self.setStyleSheet(f"background: {current_colors()['panel_bg']}; font-family: Tahoma;")
        self.setMinimumWidth(250)

        layout = QFormLayout(self)

        # Property-name labels are translated (pure UI chrome, no logic
        # coupling); the values are fabricated placeholder telemetry (see
        # page_system_topology.py's identical situation) and are left as
        # literal data, same policy as elsewhere in this task.
        t = tr
        if "Orange Pi" in device_name:
            data = [(t("pages.popups.diag_hostname"), "ENTRY-GATE"), (t("pages.popups.diag_cpu_usage"), "12%"),
                    (t("pages.popups.diag_ram_usage"), "45%"), (t("pages.popups.diag_temperature"), "42°C"),
                    (t("pages.popups.diag_uptime"), "14d 2h"), (t("pages.popups.diag_os_version"), "Linux"),
                    (t("pages.popups.diag_epw_os_version"), "1.0"), (t("pages.popups.diag_ip_address"), "192.168.1.100")]
        elif "ADA" in device_name:
            data = [(t("pages.popups.diag_firmware"), "1.0.1"), (t("pages.popups.diag_address"), "3"),
                    (t("pages.popups.diag_supply_voltage"), "24.1 V"), (t("pages.popups.diag_output_count"), "8"),
                    (t("pages.popups.diag_relay_driver_status"), "OK"), (t("pages.popups.diag_communication"), "OK"),
                    (t("pages.popups.diag_temperature"), "35°C")]
        else:
            data = [(t("pages.popups.diag_address"), "2"), (t("pages.popups.diag_firmware"), "1.0.3"),
                    (t("pages.popups.diag_mcu"), "STM32G474"), (t("pages.popups.diag_supply"), "24.08 V"),
                    (t("pages.popups.diag_temperature"), "38°C"), (t("pages.popups.diag_digital_inputs"), "12"),
                    (t("pages.popups.diag_active_inputs"), "4"), (t("pages.popups.diag_last_communication"), "18 ms"),
                    (t("pages.popups.diag_watchdog"), "OK"), (t("pages.popups.diag_crc_errors"), "0"),
                    (t("pages.popups.diag_timeouts"), "0"), (t("pages.popups.diag_restart_counter"), "1")]

        for k, v in data:
            layout.addRow(k+":", QLabel(v))

        btn = QPushButton(tr("dialog.close"))
        btn.clicked.connect(self.accept)
        layout.addRow("", btn)

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
from epw_os.gui.table_helpers import set_resizable_columns

class ModbusRegisterBrowserPopup(QDialog):
    def __init__(self, device_name, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog)
        self.setWindowTitle(tr("pages.popups.modbus_title", device=device_name))
        theme_colors = current_colors()
        self.setStyleSheet(f"background: {theme_colors['panel_bg']}; font-family: Tahoma;")
        self.resize(500, 400)

        layout = QVBoxLayout(self)

        self.table = QTableWidget(10, 4)
        self.table.setHorizontalHeaderLabels([
            tr("pages.common.col_address"), tr("pages.popups.col_type"),
            tr("pages.common.col_value"), tr("pages.common.col_description"),
        ])
        set_resizable_columns(self.table.horizontalHeader(), [80, 80, 90, 220])
        self.table.setStyleSheet(f"background: {theme_colors['field_bg']}; color: {theme_colors['text']};")

        # Fabricated sample register list (a placeholder Modbus browser, not
        # a live read) - left untranslated, same "fabricated placeholder
        # data" policy as System Topology's sim_data and this dialog's own
        # diagnostics values above.
        regs = [
            ("40001", "Holding", "0x0001", "Device ID"),
            ("40002", "Holding", "0x0103", "Firmware Version"),
            ("40003", "Holding", "0x0000", "Control Word"),
            ("30001", "Input", "2408", "Supply Voltage (10mV)"),
            ("30002", "Input", "380", "Temperature (0.1C)"),
            ("30003", "Input", "18", "Uptime Hours"),
            ("00001", "Coil", "ON", "Relay 1 Command"),
            ("00002", "Coil", "OFF", "Relay 2 Command"),
            ("10001", "Discrete", "OFF", "Input 1 Status"),
            ("10002", "Discrete", "ON", "Input 2 Status")
        ]

        for i, (addr, typ, val, desc) in enumerate(regs):
            self.table.setItem(i, 0, QTableWidgetItem(addr))
            self.table.setItem(i, 1, QTableWidgetItem(typ))
            self.table.setItem(i, 2, QTableWidgetItem(val))
            self.table.setItem(i, 3, QTableWidgetItem(desc))

        layout.addWidget(self.table, stretch=1)

        btn = QPushButton(tr("dialog.close"))
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
