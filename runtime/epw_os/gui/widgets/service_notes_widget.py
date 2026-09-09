"""Per-device service history UI (Task: historia serwisowa przypisana do
aparatu) - the "Notatki" tab in Main View's device window, and the
standalone dialog reachable from the Digital Inputs/Control Outputs
tables.

All the actual rules (immutability, the Operator-or-above gate, "zero
wymyslania" about what's recorded) live in
epw_os/core/service_notes.py - this module is purely the Qt
presentation layer on top of it, same "headless core + thin GUI
wrapper" split as switching_counters.py/page_digital_inputs.py.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QPlainTextEdit, QDialog, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt

from epw_os.core.access_manager import AccessLevel
from epw_os.core.service_notes import format_timestamp, build_device_report_csv
from epw_os.gui.table_helpers import set_resizable_columns
from epw_os.gui.theme_manager import current_colors, neutral_text_style
from epw_os.i18n import tr


def _level_name(level):
    return tr(f"access.{str(level).lower()}", default=str(level))


class ServiceNotesWidget(QWidget):
    """Task requirements, each mapped to a specific piece of this widget:

    - "Wpis zawiera: tresc, date i czas, poziom dostepu autora" -> the
      3-column table below.
    - "Dodawanie wpisu: poziom Operator lub wyzszy" -> the entry box +
      Add button are enabled only at Operator+, and _add_note() re-checks
      access at click time (not just the button's enabled state) - same
      defense-in-depth every other gated action in this app uses. The
      manager itself (add_note()) refuses a below-Operator author_level
      too, as a second, independent line of defense.
    - "Wpisy sa NIEUSUWALNE i NIEEDYTOWALNE" -> the table has
      NoEditTriggers (no in-place editor at all) and there is
      deliberately no delete button, context menu, or any other control
      that could remove/change a row - matching
      ServiceNoteManager's own API, which has no such method either.
    - "Podglad: dla kazdego, bez ograniczen" -> refresh()/the table
      itself have no access check at all.
    - Note TEXT is never passed through tr() anywhere in this file
      (GRANICE) - only the column headers/button labels/gate message are.
    """

    def __init__(self, tag_name, service_notes, access_manager=None, parent=None):
        super().__init__(parent)
        self.tag_name = tag_name
        self.service_notes = service_notes
        self.access_manager = access_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([
            tr("pages.popups.notes_col_timestamp"), tr("pages.popups.notes_col_level"),
            tr("pages.popups.notes_col_text"),
        ])
        set_resizable_columns(self.table.horizontalHeader(), [140, 80, 320])
        self.table.setWordWrap(True)
        self.table.verticalHeader().setVisible(False)
        # Task: entries are permanently read-only - no in-place editor of
        # any kind, for any level (not access-gated like Description
        # elsewhere in this app - genuinely never editable, period).
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, stretch=1)

        entry_row = QHBoxLayout()
        self.edit_text = QPlainTextEdit()
        self.edit_text.setPlaceholderText(tr("pages.popups.notes_placeholder"))
        self.edit_text.setFixedHeight(50)
        entry_row.addWidget(self.edit_text, stretch=1)
        self.btn_add = QPushButton(tr("pages.popups.btn_add_note"))
        self.btn_add.clicked.connect(self._add_note)
        entry_row.addWidget(self.btn_add)
        layout.addLayout(entry_row)

        self.lbl_gate = QLabel("")
        self.lbl_gate.setStyleSheet(neutral_text_style("font-style: italic;"))
        layout.addWidget(self.lbl_gate)

        self.refresh()
        self._refresh_add_permission()
        if self.access_manager is not None and hasattr(self.access_manager, "level_changed"):
            self.access_manager.level_changed.connect(self._refresh_add_permission)

    def refresh(self):
        """Task: "podglad: dla kazdego, bez ograniczen" - no access check
        here. Newest first (an at-a-glance monitoring view, same
        reasoning as Recently Opened Projects) - build_device_report_csv()
        deliberately uses the opposite (oldest-first) order for the
        exported report instead."""
        notes = self.service_notes.get_notes(self.tag_name) if self.service_notes is not None else []
        notes = sorted(notes, key=lambda n: n["timestamp"], reverse=True)
        self.table.setRowCount(len(notes))
        for row, note in enumerate(notes):
            ts_item = QTableWidgetItem(format_timestamp(note["timestamp"]))
            level_item = QTableWidgetItem(_level_name(note["author_level"]))
            # Note text is NEVER translated (GRANICE) - it's the
            # operator's own words, stored and shown completely verbatim.
            text_item = QTableWidgetItem(note["text"])
            for item in (ts_item, level_item, text_item):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, ts_item)
            self.table.setItem(row, 1, level_item)
            self.table.setItem(row, 2, text_item)
        self.table.resizeRowsToContents()

    def _refresh_add_permission(self, *_):
        can_add = self.access_manager is not None and self.access_manager.has_access(AccessLevel.OPERATOR)
        self.edit_text.setEnabled(can_add)
        self.btn_add.setEnabled(can_add)
        self.lbl_gate.setText("" if can_add else tr("pages.popups.notes_gate_message"))

    def _add_note(self):
        # Re-checked here, not just via the button's enabled state -
        # access could have lapsed (5-minute auto-logout) since this
        # widget was opened, same pattern as every other Operator/
        # Engineer-gated action in this app.
        if self.access_manager is None or not self.access_manager.has_access(AccessLevel.OPERATOR):
            main_window = self.window()
            if hasattr(main_window, "deny_access"):
                main_window.deny_access(AccessLevel.OPERATOR, "Add service note")
            self._refresh_add_permission()
            return
        text = self.edit_text.toPlainText().strip()
        if not text or self.service_notes is None:
            return
        self.service_notes.add_note(self.tag_name, text, self.access_manager.level)
        self.edit_text.clear()
        self.refresh()

    def collect_notes_for_export(self):
        """For build_device_report_csv() - the raw, un-sorted list
        straight from the manager (that function does its own oldest-
        first ordering)."""
        return self.service_notes.get_notes(self.tag_name) if self.service_notes is not None else []


class ServiceNotesDialog(QDialog):
    """Standalone window for the Digital Inputs/Control Outputs tables'
    "dostep z tabel DI/DO" requirement - a plain wrapper around
    ServiceNotesWidget plus the combined CSV export (Task: "razem z
    reszta danych aparatu") using whatever `properties` the caller
    already has on screen for that row (tag/description/counters)."""

    def __init__(self, tag_name, service_notes, access_manager=None, properties=None, parent=None):
        super().__init__(parent)
        self.tag_name = tag_name
        self.properties = properties or {}
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("pages.popups.notes_dialog_title", tag=tag_name))
        self.setMinimumSize(480, 360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        header = QLabel(tr("pages.popups.notes_dialog_title", tag=tag_name))
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        self.notes_widget = ServiceNotesWidget(tag_name, service_notes, access_manager, self)
        layout.addWidget(self.notes_widget, stretch=1)

        btn_row = QHBoxLayout()
        btn_export = QPushButton(tr("pages.popups.btn_export_csv"))
        btn_export.clicked.connect(self._export_csv)
        btn_row.addWidget(btn_export)
        btn_row.addStretch()
        btn_close = QPushButton(tr("dialog.close"))
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _export_csv(self):
        default_name = f"{self.tag_name}_service_history.csv"
        path, _ = QFileDialog.getSaveFileName(self, tr("pages.popups.btn_export_csv"), default_name, "CSV (*.csv)")
        if not path:
            return
        csv_text = build_device_report_csv(self.properties, self.notes_widget.collect_notes_for_export())
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                f.write(csv_text)
        except OSError as e:
            QMessageBox.warning(self, tr("pages.popups.btn_export_csv"), str(e))
