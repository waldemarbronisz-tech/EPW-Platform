from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QTableWidget, QTableWidgetItem, QPushButton)
from PySide6.QtCore import Qt
from epw_os.gui.table_helpers import set_resizable_columns
from epw_os.core.access_manager import AccessLevel
from epw_os.gui.theme_manager import get_theme_manager, neutral_text_style
from epw_os.i18n import tr


class PageAuditLog(QWidget):
    """Independent security/configuration audit trail viewer - reads
    epw_os.core.audit_logger.AuditLogger, a *separate* DB table
    (audit_log) from the operational Event Recorder (page_event_recorder
    .py, which is about alarms/device state, not security events). See
    audit_logger.py's module docstring for the full reasoning, and
    SESSION_REPORT.md for why this is its own page rather than a tab
    inside Events.

    Gated to Engineer access to view (same pattern as Protection Settings/
    Engineer Mode) - login attempts and PIN-change records are sensitive
    enough that a plain User shouldn't be able to browse them. The task
    brief didn't specify a view-access policy for this page - flagged as
    WYMAGA DECYZJI in SESSION_REPORT.md; this is the most consistent
    default given how every other sensitive page in the app already
    gates on Engineer access.
    """

    def __init__(self, audit_logger, access_manager, parent=None):
        super().__init__(parent)
        self.audit_logger = audit_logger
        self.access_manager = access_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel(tr("nav.audit_log"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PageHeader")
        layout.addWidget(title)

        info = QLabel(tr("pages.audit_log.info"))
        info.setWordWrap(True)
        layout.addWidget(info)

        toolbar = QHBoxLayout()
        self.lbl_gate = QLabel("")
        self._refresh_gate_style()
        get_theme_manager().theme_changed.connect(self._refresh_gate_style)
        toolbar.addWidget(self.lbl_gate)
        toolbar.addStretch()
        self.btn_refresh = QPushButton(tr("pages.common.btn_refresh"))
        self.btn_refresh.clicked.connect(self.refresh)
        toolbar.addWidget(self.btn_refresh)
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 5)
        self.headers = [
            tr("pages.common.col_timestamp"), tr("pages.audit_log.col_event_type"),
            tr("pages.audit_log.col_actor"), tr("pages.audit_log.col_detail"),
            tr("pages.audit_log.col_result"),
        ]
        self.table.setHorizontalHeaderLabels(self.headers)
        set_resizable_columns(self.table.horizontalHeader(), [150, 110, 90, 380, 70])
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.access_manager.level_changed.connect(self.refresh)
        self.refresh()

    def _refresh_gate_style(self, *_):
        self.lbl_gate.setStyleSheet(neutral_text_style("font-style: italic;"))

    def refresh(self, *_):
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            self.table.setRowCount(0)
            self.lbl_gate.setText(tr("pages.audit_log.gate_message"))
            self.btn_refresh.setEnabled(False)
            return
        self.lbl_gate.setText("")
        self.btn_refresh.setEnabled(True)

        # audit_logger is None in isolated widget tests / mocks that don't
        # wire up a real AuditLogger.
        entries = self.audit_logger.query(limit=500) if self.audit_logger is not None else []
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S") if entry.timestamp else "-"
            self.table.setItem(row, 0, QTableWidgetItem(ts))
            self.table.setItem(row, 1, QTableWidgetItem(entry.event_type or ""))
            self.table.setItem(row, 2, QTableWidgetItem(entry.actor or ""))
            self.table.setItem(row, 3, QTableWidgetItem(entry.detail or ""))
            result_item = QTableWidgetItem(
                tr("pages.audit_log.result_ok") if entry.success else tr("pages.audit_log.result_failed"))
            if not entry.success:
                result_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 4, result_item)
