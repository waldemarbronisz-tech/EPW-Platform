from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QTableWidget, QTableWidgetItem, QPushButton)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from datetime import datetime

from epw_os.gui.table_helpers import (
    set_resizable_columns, set_header_tooltips,
    apply_table_button_style, style_transparent_cell_container,
)
from epw_os.core.access_manager import AccessLevel
from epw_os.core.alarm_manager import AlarmState
from epw_os.gui.theme_manager import get_theme_manager, neutral_text_style
from epw_os.i18n import tr


# Display-only translation maps - AlarmState.value / the raw priority int
# keep meaning exactly what they did before (compared elsewhere in this
# file, e.g. `alarm.state == AlarmState.ACTIVE_UNACK`, and by the core
# AlarmManager); only the rendered text changes with the UI language.
def _priority_name(priority):
    return {1: tr("pages.alarms.priority_low"), 2: tr("pages.alarms.priority_medium"),
            3: tr("pages.alarms.priority_high"), 4: tr("pages.alarms.priority_critical")}.get(priority, str(priority))


def _state_name(state):
    return {
        AlarmState.NORMAL: tr("pages.alarms.state_normal"),
        AlarmState.ACTIVE_UNACK: tr("pages.alarms.state_active_unack"),
        AlarmState.ACTIVE_ACK: tr("pages.alarms.state_active_ack"),
        AlarmState.CLEARED_UNACK: tr("pages.alarms.state_cleared_unack"),
    }.get(state, state.value)


class PageAlarms(QWidget):
    """Alarm summary, built on the existing (previously GUI-unconnected)
    AlarmManager - see SESSION_REPORT.md for what actually raises real
    alarms today (device comm failure, EMERGENCY_STOP) and why those two.

    Acknowledging requires Operator-or-above access, consistent with the
    rest of the app's "User = view only" rule - a plain User can see the
    alarm list but not silence it."""

    def __init__(self, alarm_manager, access_manager, parent=None):
        super().__init__(parent)
        self.alarm_manager = alarm_manager
        self.access_manager = access_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel(tr("nav.alarms"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PageHeader")
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        self.lbl_gate = QLabel("")
        self.lbl_gate.setStyleSheet(neutral_text_style("font-style: italic;"))
        toolbar.addWidget(self.lbl_gate)
        toolbar.addStretch()
        self.btn_refresh = QPushButton(tr("pages.common.btn_refresh"))
        self.btn_refresh.clicked.connect(self.refresh)
        toolbar.addWidget(self.btn_refresh)
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 7)
        self.headers = [
            tr("pages.alarms.col_priority"), tr("pages.alarms.col_message"), tr("pages.alarms.col_source"),
            tr("pages.alarms.col_activated"), tr("pages.alarms.col_state"), tr("pages.alarms.col_ack"),
            tr("pages.alarms.col_action"),
        ]
        self.table.setHorizontalHeaderLabels(self.headers)
        set_header_tooltips(self.table, [
            "", "", "",
            tr("pages.alarms.tooltip_col_activated"), "", tr("pages.alarms.tooltip_col_ack"),
            "",
        ])
        set_resizable_columns(self.table.horizontalHeader(), [75, 260, 130, 140, 100, 150, 90])
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.access_manager.level_changed.connect(self.refresh)
        get_theme_manager().theme_changed.connect(self.refresh)
        self.refresh()

    def refresh(self, *_):
        can_ack = self.access_manager.has_access(AccessLevel.OPERATOR)
        self.lbl_gate.setText("" if can_ack else tr("pages.alarms.gate_message"))

        # alarm_manager is None in isolated widget tests / mocks that
        # don't wire up a real AlarmManager.
        alarms = self.alarm_manager.get_all_alarms() if self.alarm_manager is not None else []
        self.table.setRowCount(len(alarms))
        for row, alarm in enumerate(alarms):
            self.table.setItem(row, 0, QTableWidgetItem(_priority_name(alarm.priority)))
            # alarm.message/source_tag are data raised by AlarmManager
            # (device comm failure, EMERGENCY_STOP, ...) - left
            # untranslated, same policy as ui_logger event text.
            self.table.setItem(row, 1, QTableWidgetItem(alarm.message))
            self.table.setItem(row, 2, QTableWidgetItem(alarm.source_tag))
            self.table.setItem(row, 3, QTableWidgetItem(self._fmt(alarm.activation_time)))

            state_item = QTableWidgetItem(_state_name(alarm.state))
            self.table.setItem(row, 4, state_item)

            if alarm.ack_time:
                ack_item = QTableWidgetItem(f"{alarm.ack_user or '?'} @ {self._fmt(alarm.ack_time)}")
            else:
                ack_item = QTableWidgetItem("-")
            self.table.setItem(row, 5, ack_item)

            # Visual distinction: unacknowledged active alarms stand out
            # (red background, bold state text); acknowledged/normal ones
            # are calm/default - this is the "different color/style"
            # requirement, applied consistently across every column of
            # the row, not just the state cell.
            theme_colors = get_theme_manager().current_colors()
            if alarm.state == AlarmState.ACTIVE_UNACK:
                bg = QColor(theme_colors["state_alarm_dark"])  # dark red
                fg = QColor(theme_colors["accent_text"])
            elif alarm.state == AlarmState.ACTIVE_ACK:
                bg = QColor(theme_colors["state_warning_dark"])  # dark amber - active but silenced
                fg = QColor(theme_colors["accent_text"])
            elif alarm.state == AlarmState.CLEARED_UNACK:
                bg = QColor(theme_colors["state_neutral_dark"])  # cleared but still needs ack
                fg = QColor(theme_colors["accent_text"])
            else:  # NORMAL
                bg = QColor(theme_colors["field_bg"])
                fg = QColor(theme_colors["text"])
            for col in range(6):
                item = self.table.item(row, col)
                item.setBackground(bg)
                item.setForeground(fg)

            # Action column: an Acknowledge button only for alarms that
            # actually need one, only when the operator can use it.
            if alarm.state in (AlarmState.ACTIVE_UNACK, AlarmState.CLEARED_UNACK) and can_ack:
                # Task (button-look fix): wrapped in a small centering
                # container, like every other table-cell button - set
                # directly as the cell widget it used to fill the entire
                # cell (touching every edge) instead of sitting centered
                # with a small margin like the rest of the row.
                ack_container = QWidget()
                style_transparent_cell_container(ack_container)
                ack_layout = QHBoxLayout(ack_container)
                ack_layout.setContentsMargins(2, 2, 2, 2)
                ack_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                btn = QPushButton(tr("pages.alarms.btn_acknowledge"))
                btn.setToolTip(tr("pages.alarms.tooltip_btn_acknowledge"))
                apply_table_button_style(btn)
                btn.clicked.connect(lambda checked=False, aid=alarm.id: self._acknowledge(aid))
                ack_layout.addWidget(btn)
                self.table.setCellWidget(row, 6, ack_container)
            else:
                self.table.setCellWidget(row, 6, None)
                placeholder = QTableWidgetItem("")
                placeholder.setBackground(bg)
                self.table.setItem(row, 6, placeholder)

    def _acknowledge(self, alarm_id):
        if not self.access_manager.has_access(AccessLevel.OPERATOR):
            # Re-checked here too, not just via button visibility - access
            # could have timed out in the seconds since the table was
            # last refreshed.
            self.window().deny_access(AccessLevel.OPERATOR, "Acknowledge alarm")
            self.refresh()
            return
        self.alarm_manager.acknowledge_alarm(alarm_id, user=self.access_manager.level)
        self.refresh()

    @staticmethod
    def _fmt(ts):
        if not ts:
            return "-"
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
