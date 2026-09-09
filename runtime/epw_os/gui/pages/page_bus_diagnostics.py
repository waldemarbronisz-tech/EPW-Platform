"""Bus Diagnostics (Task: "ekran diagnostyczny komunikacji szeregowej -
ramki, bledy, czasy odpowiedzi per urzadzenie"). Built now, against
SimulatorDriver - the only driver that exists today - specifically so
it's ready the day a real ModbusDriver exists: this page only ever
calls BaseDriver.get_comm_stats()/reset_comm_stats() (see
base_driver.py's neutral interface, and epw_os/core/comm_diagnostics.py
for the counting engine SimulatorDriver composes to implement it) - it
has no SimulatorDriver-specific code anywhere, and needs none changed
when a second/different driver starts serving some of these devices.

Engineer-only to view (Task: "dostep: Engineer") - same nav-level gate
pattern as Audit Log/Engineer Mode (main_window.py's _navigate_to()),
with this page's own refresh()-time re-check as the second layer, same
as page_audit_log.py.
"""
import time

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QTableWidget, QTableWidgetItem)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from epw_os.gui.table_helpers import set_resizable_columns, set_header_tooltips
from epw_os.core.access_manager import AccessLevel
from epw_os.core.switching_counters import format_duration
from epw_os.gui.theme_manager import get_theme_manager, current_colors, neutral_text_style
from epw_os.i18n import tr

# Friendlier labels for the built-in default device ids (see
# tag_manager.py's init_default_tags()/epw_core.py's default_devices) -
# purely cosmetic, same "Device" column convention page_entry_gate.py's
# DeviceStatusPanel already uses for these same four ids. Any other
# device_id (a project-configured one) falls back to showing the id
# itself - never a fabricated name.
_DEVICE_DISPLAY_NAMES = {
    "OrangePi": "Orange Pi",
    "ELA01": "ELA-01",
    "ADA01": "ADA-01",
    "Modbus": "Modbus RTU",
}

# Recent-errors panel: how many rows to show, merged across every
# device - each device's own ring buffer (comm_diagnostics.py's
# MAX_RECENT_ERRORS) already bounds memory; this just bounds the table.
MAX_DISPLAYED_ERRORS = 100

_COL_ID = 0
_COL_NAME = 1
_COL_SENT = 2
_COL_RECEIVED = 3
_COL_TIMEOUT = 4
_COL_CRC = 5
_COL_INVALID = 6
_COL_LAST_MS = 7
_COL_AVG_MS = 8
_COL_WORST_MS = 9
_COL_SINCE_SUCCESS = 10
_COL_SUCCESS_PCT = 11

REFRESH_INTERVAL_MS = 1000  # matches SimulatorDriver's own ~1s poll cadence - no point polling faster


class PageBusDiagnostics(QWidget):
    def __init__(self, device_manager, driver_manager, access_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self.driver_manager = driver_manager
        self.access_manager = access_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel(tr("pages.bus_diagnostics.title"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PageHeader")
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        self.lbl_gate = QLabel("")
        self._refresh_gate_style()
        get_theme_manager().theme_changed.connect(self._refresh_gate_style)
        toolbar.addWidget(self.lbl_gate)
        toolbar.addStretch()
        self.btn_reset = QPushButton(tr("pages.bus_diagnostics.btn_reset"))
        self.btn_reset.setToolTip(tr("pages.bus_diagnostics.tooltip_btn_reset"))
        self.btn_reset.clicked.connect(self._reset_all)
        toolbar.addWidget(self.btn_reset)
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 12)
        self.table.setHorizontalHeaderLabels([
            tr("pages.bus_diagnostics.col_id"), tr("pages.bus_diagnostics.col_name"),
            tr("pages.bus_diagnostics.col_sent"), tr("pages.bus_diagnostics.col_received"),
            tr("pages.bus_diagnostics.col_timeout"), tr("pages.bus_diagnostics.col_crc"),
            tr("pages.bus_diagnostics.col_invalid"), tr("pages.bus_diagnostics.col_last_ms"),
            tr("pages.bus_diagnostics.col_avg_ms"), tr("pages.bus_diagnostics.col_worst_ms"),
            tr("pages.bus_diagnostics.col_since_success"), tr("pages.bus_diagnostics.col_success_pct"),
        ])
        set_header_tooltips(self.table, [
            tr("pages.bus_diagnostics.tooltip_col_id"), "",
            tr("pages.bus_diagnostics.tooltip_col_sent"), tr("pages.bus_diagnostics.tooltip_col_received"),
            tr("pages.bus_diagnostics.tooltip_col_timeout"), tr("pages.bus_diagnostics.tooltip_col_crc"),
            tr("pages.bus_diagnostics.tooltip_col_invalid"), tr("pages.bus_diagnostics.tooltip_col_last_ms"),
            tr("pages.bus_diagnostics.tooltip_col_avg_ms"), tr("pages.bus_diagnostics.tooltip_col_worst_ms"),
            tr("pages.bus_diagnostics.tooltip_col_since_success"), tr("pages.bus_diagnostics.tooltip_col_success_pct"),
        ])
        set_resizable_columns(self.table.horizontalHeader(), [80, 90, 65, 75, 70, 60, 65, 70, 70, 75, 90, 75])
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, stretch=2)

        errors_title = QLabel(tr("pages.bus_diagnostics.errors_title"))
        errors_title.setObjectName("SectionHeader")
        layout.addWidget(errors_title)

        self.errors_table = QTableWidget(0, 4)
        self.errors_table.setHorizontalHeaderLabels([
            tr("pages.common.col_timestamp"), tr("pages.bus_diagnostics.col_id"),
            tr("pages.bus_diagnostics.col_error_type"), tr("pages.common.col_description"),
        ])
        set_resizable_columns(self.errors_table.horizontalHeader(), [150, 90, 130, 400])
        self.errors_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.errors_table.verticalHeader().setVisible(False)
        self.errors_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.errors_table, stretch=1)

        self.access_manager.level_changed.connect(self.refresh)

        # Task: podpowiedzi-style dynamic refresh, but here it's the
        # page's core content, not just a tooltip - a plain QTimer
        # poll of get_comm_stats() (a few cheap in-memory dict/deque
        # reads, no I/O), same cadence as the driver's own poll cycle.
        # Not event-driven off tag_changed: comm stats aren't tags, and
        # polling once/second is already as fresh as the underlying
        # data ever changes.
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start(REFRESH_INTERVAL_MS)
        self.refresh()

    def _refresh_gate_style(self, *_):
        self.lbl_gate.setStyleSheet(neutral_text_style("font-style: italic;"))

    def _device_ids(self):
        if self.device_manager is None:
            return []
        return list(self.device_manager.devices.keys())

    def _stats_for(self, device_id):
        """Looks up which driver actually serves this device (via
        DeviceManager's own driver_id record) and asks THAT driver for
        its stats - the neutral interface means this page never assumes
        it's talking to SimulatorDriver specifically, and works
        unchanged once a device's driver_id points at a real
        ModbusDriver instead."""
        if self.device_manager is None or self.driver_manager is None:
            return None
        info = self.device_manager.devices.get(device_id)
        if info is None:
            return None
        driver = self.driver_manager.get_driver(info.get("driver_id"))
        if driver is None:
            return None
        return driver.get_comm_stats().get(device_id)

    def refresh(self, *_):
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.table.setRowCount(0)
            self.errors_table.setRowCount(0)
            self.lbl_gate.setText(tr("pages.bus_diagnostics.gate_message"))
            self.btn_reset.setEnabled(False)
            return
        self.lbl_gate.setText("")
        self.btn_reset.setEnabled(True)

        device_ids = self._device_ids()
        self.table.setRowCount(len(device_ids))
        all_errors = []
        colors = current_colors()

        for row, device_id in enumerate(device_ids):
            stats = self._stats_for(device_id)
            name = _DEVICE_DISPLAY_NAMES.get(device_id, device_id)
            self.table.setItem(row, _COL_ID, QTableWidgetItem(device_id))
            self.table.setItem(row, _COL_NAME, QTableWidgetItem(name))

            if stats is None:
                # A registered device with no driver reporting stats for
                # it yet (Task: base interface default is "nothing to
                # report", not an error) - "no data" markers, not zeros
                # that would look like a real 0-frame reading.
                for col in (_COL_SENT, _COL_RECEIVED, _COL_TIMEOUT, _COL_CRC, _COL_INVALID,
                            _COL_LAST_MS, _COL_AVG_MS, _COL_WORST_MS, _COL_SINCE_SUCCESS, _COL_SUCCESS_PCT):
                    self.table.setItem(row, col, QTableWidgetItem(tr("pages.bus_diagnostics.no_data")))
                continue

            self.table.setItem(row, _COL_SENT, QTableWidgetItem(str(stats.frames_sent)))
            self.table.setItem(row, _COL_RECEIVED, QTableWidgetItem(str(stats.frames_received)))
            self.table.setItem(row, _COL_TIMEOUT, QTableWidgetItem(str(stats.errors_timeout)))
            self.table.setItem(row, _COL_CRC, QTableWidgetItem(str(stats.errors_crc)))
            self.table.setItem(row, _COL_INVALID, QTableWidgetItem(str(stats.errors_invalid_response)))
            self.table.setItem(row, _COL_LAST_MS, QTableWidgetItem(self._fmt_ms(stats.last_response_ms)))
            self.table.setItem(row, _COL_AVG_MS, QTableWidgetItem(self._fmt_ms(stats.avg_response_ms)))
            self.table.setItem(row, _COL_WORST_MS, QTableWidgetItem(self._fmt_ms(stats.worst_response_ms)))

            since = stats.seconds_since_success()
            since_item = QTableWidgetItem(
                format_duration(since) if since is not None else tr("pages.bus_diagnostics.no_data")
            )
            self.table.setItem(row, _COL_SINCE_SUCCESS, since_item)

            pct = stats.success_rate_pct
            pct_item = QTableWidgetItem(f"{pct:.1f} %" if pct is not None else tr("pages.bus_diagnostics.no_data"))
            if pct is not None and pct < 100.0:
                pct_item.setForeground(QColor(colors["state_alarm"] if pct < 90.0 else colors["state_warning_dark"]))
            self.table.setItem(row, _COL_SUCCESS_PCT, pct_item)

            for err in stats.recent_errors:
                all_errors.append((err, device_id))

        all_errors.sort(key=lambda pair: pair[0].timestamp, reverse=True)
        all_errors = all_errors[:MAX_DISPLAYED_ERRORS]
        self.errors_table.setRowCount(len(all_errors))
        for row, (err, device_id) in enumerate(all_errors):
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(err.timestamp))
            self.errors_table.setItem(row, 0, QTableWidgetItem(ts))
            self.errors_table.setItem(row, 1, QTableWidgetItem(device_id))
            self.errors_table.setItem(row, 2, QTableWidgetItem(err.error_type))
            self.errors_table.setItem(row, 3, QTableWidgetItem(err.description))

    @staticmethod
    def _fmt_ms(value):
        if value is None:
            return tr("pages.bus_diagnostics.no_data")
        return f"{value:.3f}"

    def _reset_all(self):
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.window().deny_access(AccessLevel.ENGINEER, "Reset Bus Diagnostics counters")
            return
        if self.driver_manager is None:
            return
        # Every driver currently registered, not just the ones this
        # page happens to be showing devices for right now - "reset
        # counters" means the whole board, matching the single, global
        # button the task describes (not a per-row reset).
        for driver in self.driver_manager.drivers.values():
            driver.reset_comm_stats()
        self.refresh()

    def shutdown(self):
        """Called from MainWindow.shutdown_gui() - same "stop a timer
        this page owns before the process exits" pattern as
        page_trends.py's own shutdown()."""
        self._refresh_timer.stop()
