import csv
from datetime import datetime, timezone

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDateTimeEdit,
                             QListWidget, QListWidgetItem, QCheckBox, QPushButton,
                             QDialogButtonBox, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QDateTime

from epw_os.core.historian import tag_history_value
from epw_os.gui.logger import ui_logger
from epw_os.gui.theme_manager import error_text_style, success_text_style, neutral_text_style
from epw_os.i18n import tr


class HistorianExportDialog(QDialog):
    """Tools > Export Historical Data... - general historical tag-trend
    export from Historian's tag_history table (every tag_changed event
    ever recorded, not just DI/DO). Deliberately separate from Event
    Recorder's own "Export CSV" button (page_event_recorder.py), which
    exports the operational *event log* table - a different table with a
    different meaning (alarms/operator actions vs. raw value-over-time
    trend data). See SESSION_REPORT.md for why this lives under Tools
    rather than as a page of its own: it's a one-shot action with no
    ongoing state to browse, not a place an operator monitors - the same
    reasoning Settings' popups already use, and Tools was an empty
    placeholder menu with nothing in it yet.
    """

    def __init__(self, historian, tag_manager, parent=None,
                 initial_from_utc=None, initial_to_utc=None, initial_tags=None):
        """`initial_from_utc`/`initial_to_utc` (naive-or-aware UTC
        datetime) and `initial_tags` (list of tag names) pre-fill the
        pickers/selection instead of the usual "last 24h, all tags"
        defaults - used by page_trends.py's "Export visible range"
        button (Task: "skorzystaj z istniejacego mechanizmu eksportu z
        Historiana, nie buduj drugiego") to open this exact same dialog
        already set to the chart's current view, rather than a second
        CSV-writing code path. None (the default) for any of the three
        keeps this dialog's original Tools-menu behavior unchanged."""
        super().__init__(parent)
        self.historian = historian
        self.tag_manager = tag_manager
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("pages.historian_export.title"))
        self.setModal(True)
        self.setMinimumSize(420, 440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        header = QLabel(tr("pages.historian_export.header"))
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        hint = QLabel(tr("pages.historian_export.hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # QDateTime.fromSecsSinceEpoch()'s result is already local time
        # (Qt does the UTC->local conversion for us) - the pickers always
        # show/accept local time, whether pre-filled from a UTC datetime
        # here or left at the plain "now"-based default below.
        default_from = QDateTime.currentDateTime().addDays(-1)
        default_to = QDateTime.currentDateTime()
        if initial_from_utc is not None:
            default_from = QDateTime.fromSecsSinceEpoch(int(initial_from_utc.replace(tzinfo=timezone.utc).timestamp()))
        if initial_to_utc is not None:
            default_to = QDateTime.fromSecsSinceEpoch(int(initial_to_utc.replace(tzinfo=timezone.utc).timestamp()))

        range_row1 = QHBoxLayout()
        range_row1.addWidget(QLabel(tr("pages.historian_export.lbl_from")))
        self.dt_from = QDateTimeEdit(default_from)
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        range_row1.addWidget(self.dt_from, 1)
        layout.addLayout(range_row1)

        range_row2 = QHBoxLayout()
        range_row2.addWidget(QLabel(tr("pages.historian_export.lbl_to")))
        self.dt_to = QDateTimeEdit(default_to)
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        range_row2.addWidget(self.dt_to, 1)
        layout.addLayout(range_row2)

        self.chk_all_tags = QCheckBox(tr("pages.historian_export.chk_all_tags"))
        self.chk_all_tags.setChecked(initial_tags is None)
        self.chk_all_tags.toggled.connect(self._on_all_tags_toggled)
        layout.addWidget(self.chk_all_tags)

        self.tag_list = QListWidget()
        self.tag_list.setEnabled(initial_tags is not None)
        initial_tags_set = set(initial_tags or [])
        for name in self.historian.get_distinct_tag_names():
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if name in initial_tags_set else Qt.CheckState.Unchecked)
            self.tag_list.addItem(item)
        layout.addWidget(self.tag_list, 1)

        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.btn_export = QPushButton(tr("pages.historian_export.btn_export"))
        self.btn_export.clicked.connect(self._export)
        buttons.addButton(self.btn_export, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_all_tags_toggled(self, checked):
        self.tag_list.setEnabled(not checked)

    def _selected_tags(self):
        """None means "every tag" (query_tag_history's own convention) -
        distinct from an empty list, which means the operator unchecked
        "All tags" but picked nothing, a real input error."""
        if self.chk_all_tags.isChecked():
            return None
        selected = []
        for i in range(self.tag_list.count()):
            item = self.tag_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.text())
        return selected

    def _export(self):
        # The date/time pickers show and accept *local* wall-clock time,
        # but Historian stores TagHistory.timestamp as naive UTC
        # (datetime.utcnow(), see historian.py) - comparing a local-time
        # value against that directly would silently miss rows (or
        # return the wrong ones) by exactly the local UTC offset. QDateTime
        # already knows its own local timezone; toUTC() does the
        # conversion correctly (handles DST too), toPython() then hands
        # back a naive datetime in UTC, matching how it's stored.
        #
        # Premise correction (found while implementing page_trends.py's
        # copy of this exact pattern - see SESSION_REPORT.md): this used
        # to call .toPyDateTime(), which does not exist on the installed
        # PySide6 6.11.2's QDateTime (AttributeError) - the equivalent
        # method here is .toPython(). Nothing had ever caught this: no
        # test exercises this dialog's real _export() path (test_gui_smoke.py
        # only constructs the dialog, never clicks Export), so every
        # actual CSV export attempt through this dialog has been broken
        # since whatever PySide6 upgrade renamed/removed toPyDateTime().
        # (test_gui_smoke.py mentioned above is now gui_smoke/ - see
        # gui_smoke/test_i18n.py, which still only constructs this dialog.)
        start = self.dt_from.dateTime().toUTC().toPython()
        end = self.dt_to.dateTime().toUTC().toPython()
        if start >= end:
            self.lbl_status.setText(tr("pages.historian_export.err_from_after_to"))
            self.lbl_status.setStyleSheet(error_text_style())
            return

        tags = self._selected_tags()
        if tags is not None and not tags:
            self.lbl_status.setText(tr("pages.historian_export.err_no_tags_selected"))
            self.lbl_status.setStyleSheet(error_text_style())
            return

        rows = self.historian.query_tag_history(start, end, tag_names=tags)
        if not rows:
            self.lbl_status.setText(tr("pages.historian_export.msg_no_history"))
            self.lbl_status.setStyleSheet(neutral_text_style())
            return

        # Task (Part 1.3): "Eksport... ma jasno informowac, jesli zakres
        # zawiera dane symulowane". quality is already exported as its own
        # CSV column below (unchanged - it always was), so a SIMULATED row
        # is filterable there regardless; this additionally surfaces it
        # up front, in the dialog itself and the completion popup, so an
        # operator doesn't have to know to go looking in that column.
        simulated_count = sum(1 for r in rows if r.quality == "SIMULATED")

        default_name = f"epw_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, tr("pages.historian_export.title"), default_name, tr("pages.historian_export.csv_filter")
        )
        if not path:
            return

        mode = getattr(self.tag_manager, "mode", "") or ""
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # CSV column headers are deliberately NOT translated - this
                # is an exported data file (possibly re-opened by another
                # tool/analysis script expecting stable column names), not
                # an on-screen UI element. See SESSION_REPORT.md.
                writer.writerow(["Timestamp", "Tag", "Value", "Quality"])
                for row in rows:
                    # Convert the stored naive-UTC timestamp back to local
                    # time for the CSV, so it lines up with the local
                    # From/To range the operator picked instead of
                    # appearing shifted by the UTC offset.
                    if row.timestamp:
                        local_ts = row.timestamp.replace(tzinfo=timezone.utc).astimezone()
                        ts = local_ts.strftime("%Y-%m-%d %H:%M:%S.%f")
                    else:
                        ts = ""
                    writer.writerow([ts, row.tag_name, tag_history_value(row), row.quality or ""])
        except OSError as e:
            ui_logger.log("WARNING", "OPERATION", "Historian Export", "CSV export failed", "Operator", mode, str(e))
            QMessageBox.warning(self, tr("pages.historian_export.title"),
                                 tr("pages.historian_export.err_export_failed", error=e))
            return

        ui_logger.log("INFO", "OPERATION", "Historian Export", f"Exported {len(rows)} row(s) to CSV", "Operator", mode, path)
        sim_note = ""
        if simulated_count:
            sim_note = tr("pages.historian_export.warn_contains_simulated", n=simulated_count)
            ui_logger.log("WARNING", "OPERATION", "Historian Export",
                          f"Exported range includes {simulated_count} simulated value(s)", "Operator", mode, path)
        self.lbl_status.setText(tr("pages.historian_export.msg_exported", n=len(rows)) + sim_note)
        self.lbl_status.setStyleSheet(error_text_style() if simulated_count else success_text_style())
        QMessageBox.information(self, tr("pages.historian_export.title"),
                                 tr("pages.historian_export.msg_exported_to", n=len(rows), path=path) + sim_note)
