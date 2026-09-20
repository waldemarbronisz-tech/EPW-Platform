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
