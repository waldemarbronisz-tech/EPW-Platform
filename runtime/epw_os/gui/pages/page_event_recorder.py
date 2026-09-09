from collections import deque

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
                             QLabel, QHBoxLayout, QComboBox, QLineEdit, QPushButton, QMenu,
                             QApplication, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt
import csv
from datetime import datetime
from epw_os.gui.logger import ui_logger
from epw_os.gui.widgets.event_item import EventTableItem
from epw_os.gui.table_helpers import set_resizable_columns
from epw_os.gui.theme_manager import get_theme_manager, current_colors
from epw_os.i18n import tr

# Acceptance-review finding (category: resources - "czy cos rosnie w
# nieskonczonosc"): on_log_event() below added a new row for EVERY event
# ui_logger ever emits, with no cap - on a long-running installation
# (this app's own deployment target, Orange Pi, runs unattended for
# weeks/months - see ORANGE_PI_DEPLOYMENT.md) self.table grows without
# bound for the life of the process, and apply_filter()/apply_sorting()
# both re-scan/re-sort the ENTIRE table on every single new event, so
# the cost of each new event grows with total uptime, not just its own
# processing (an O(n) coming to feel like an actual freeze once n is in
# the tens of thousands). Capped here at a fixed row count, evicting the
# oldest row once exceeded - see _row_ids and its use in on_log_event().
MAX_EVENT_ROWS = 5000

class PageEventRecorder(QWidget):
    def __init__(self, tag_manager, parent=None):
        super().__init__(parent)
        self.tag_manager = tag_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel(tr("pages.event_recorder.title"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PageHeader")
        layout.addWidget(title)

        # Event statistics bar
        stats_layout = QHBoxLayout()
        self.lbl_stats = QLabel(tr("pages.event_recorder.stats_template", events=0, displayed=0,
                                    filters=tr("pages.event_recorder.filters_none"), newest="N/A", oldest="N/A"))
        stats_layout.addWidget(self.lbl_stats)
        layout.addLayout(stats_layout)
        self._refresh_stats_bar_style()
        get_theme_manager().theme_changed.connect(self._refresh_stats_bar_style)

        # Filters
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel(tr("pages.event_recorder.lbl_search")))
        self.txt_search = QLineEdit()
        self.txt_search.textChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.txt_search)

        filter_layout.addWidget(QLabel(tr("pages.event_recorder.lbl_group")))
        self.cmb_cat = QComboBox()
        # Deliberately NOT translated - these values are matched
        # exact-string against the Group column (self.headers[2]) below
        # AND against the literal group strings ui_logger.log() calls use
        # app-wide ("OPERATION", "SYSTEM", ..., never translated - see
        # SESSION_REPORT.md). Translating this list would silently break
        # both the group filter and the "Filter by Group" context-menu
        # action.
        self.cmb_cat.addItems(["ALL", "PROTECTION", "OPERATION", "AUTOMATION", "ENVIRONMENT", "SYSTEM"])
        self.cmb_cat.currentTextChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.cmb_cat)

        btn_export = QPushButton(tr("pages.event_recorder.btn_export"))
        btn_export.clicked.connect(self.export_visible_to_csv)
        filter_layout.addWidget(btn_export)

        layout.addLayout(filter_layout)

        # Table (Norton Commander Style)
        self.table = QTableWidget(0, 8)
        # Deliberately NOT translated - self.headers doubles as (1) the
        # CSV export header row and (2) the EventTableItem col_type used
        # for custom Priority/Group sort ordering (event_item.py compares
        # col_type == "Priority"/"Group" by exact string) - translating
        # these would silently degrade sorting to plain alphabetical, an
        # unintended logic change. See SESSION_REPORT.md.
        self.headers = ["Timestamp", "Priority", "Group", "Object", "Event", "User", "Mode", "Result"]
        self.table.setHorizontalHeaderLabels(self.headers)
        # Timestamp, Priority, Group, Object, Event, User, Mode, Result
        set_resizable_columns(self.table.horizontalHeader(),
                              [150, 80, 110, 120, 320, 90, 110, 90])
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Disable automatic sorting to manage it manually with tri-state cycling
        self.table.setSortingEnabled(False)
        self.sort_col = 0
        self.sort_order = Qt.SortOrder.DescendingOrder
        self.table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        self.table.setObjectName("EventTable")
        layout.addWidget(self.table, stretch=1)

        ui_logger.log_event.connect(self.on_log_event)

        self.total_events = 0
        # Column-0 (Timestamp) item of every currently-retained row, in
        # insertion order - oldest first. QTableWidgetItem.row() always
        # reports the item's CURRENT physical row regardless of how many
        # times the table has been re-sorted since, so this stays correct
        # to evict the true oldest row even though apply_sorting() below
        # physically reorders rows on every single insert (see
        # MAX_EVENT_ROWS' own comment for why this cap exists at all).
        self._row_ids = deque()

    def on_log_event(self, timestamp, prio, group, obj, event, user, mode, result):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.total_events += 1

        items = [timestamp, prio, group, obj, event, user, mode, result]

        # Colors
        color = Qt.GlobalColor.white
        if prio.upper() == "WARNING": color = Qt.GlobalColor.yellow
        elif prio.upper() == "ALARM": color = Qt.GlobalColor.red
        elif prio.upper() == "FAULT": color = Qt.GlobalColor.magenta
        elif prio.upper() == "TRIP": color = Qt.GlobalColor.darkRed
        elif group.upper() == "SYSTEM": color = Qt.GlobalColor.cyan
        else: color = Qt.GlobalColor.green

        for i, val in enumerate(items):
            col_name = self.headers[i]
            item = EventTableItem(val, col_name)
            item.setForeground(color)
            self.table.setItem(row, i, item)
            if i == 0:
                self._row_ids.append(item)

        if len(self._row_ids) > MAX_EVENT_ROWS:
            oldest = self._row_ids.popleft()
            self.table.removeRow(oldest.row())

        self.apply_sorting(False)
        self.apply_filter()

    def on_header_clicked(self, logical_index):
        if self.sort_col == logical_index:
            # Cycle: Descending -> Ascending -> Default(Timestamp DESC)
            if self.sort_order == Qt.SortOrder.DescendingOrder:
                self.sort_order = Qt.SortOrder.AscendingOrder
            elif self.sort_order == Qt.SortOrder.AscendingOrder:
                # Reset to default
                self.sort_col = 0
                self.sort_order = Qt.SortOrder.DescendingOrder
        else:
            self.sort_col = logical_index
            self.sort_order = Qt.SortOrder.AscendingOrder
            
        self.apply_sorting(True)

    def apply_sorting(self, update_headers=True):
        self.table.sortItems(self.sort_col, self.sort_order)
        
        if update_headers:
            new_labels = []
            for i, h in enumerate(self.headers):
                if i == self.sort_col:
                    arrow = " ▲" if self.sort_order == Qt.SortOrder.AscendingOrder else " ▼"
                    new_labels.append(h + arrow)
                else:
                    new_labels.append(h)
            self.table.setHorizontalHeaderLabels(new_labels)

    def update_statistics(self):
        displayed = 0
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                displayed += 1
                
        filters = tr("pages.event_recorder.filters_active") if (self.txt_search.text() or self.cmb_cat.currentText() != "ALL") else tr("pages.event_recorder.filters_none")
        
        newest = "N/A"
        oldest = "N/A"
        if self.table.rowCount() > 0:
            # Re-find newest and oldest by just searching the Timestamp column since sorting might move them around
            timestamps = [self.table.item(i, 0).text() for i in range(self.table.rowCount()) if self.table.item(i, 0) is not None]
            if timestamps:
                timestamps.sort()
                oldest = timestamps[0]
                newest = timestamps[-1]
            
        self.lbl_stats.setText(tr("pages.event_recorder.stats_template", events=self.total_events,
                                   displayed=displayed, filters=filters, newest=newest, oldest=oldest))

    def _refresh_stats_bar_style(self, *_):
        c = current_colors()
        self.lbl_stats.setStyleSheet(
            "font-family: 'Consolas', 'Courier New'; font-weight: bold; font-size: 12px; "
            f"color: {c['console_header_text']}; background: {c['console_bg']}; padding: 2px;"
        )

    def apply_filter(self):
        search_txt = self.txt_search.text().lower()
        cat_txt = self.cmb_cat.currentText()

        for row in range(self.table.rowCount()):
            match = True
            if cat_txt != "ALL" and self.table.item(row, 2).text() != cat_txt:
                match = False

            if search_txt:
                row_match = False
                for col in range(self.table.columnCount()):
                    if search_txt in self.table.item(row, col).text().lower():
                        row_match = True
                        break
                if not row_match:
                    match = False

            self.table.setRowHidden(row, not match)
            
        self.update_statistics()

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
            
        row = item.row()
        menu = QMenu(self)
        c = current_colors()
        menu.setStyleSheet(f"""
            QMenu {{ background-color: {c['panel_bg']}; color: {c['text']}; border: 1px solid {c['dialog_border']}; }}
            QMenu::item:selected {{ background-color: {c['accent_bg']}; color: {c['accent_text']}; }}
        """)

        action_copy_row = menu.addAction(tr("pages.event_recorder.menu_copy_row"))
        action_copy_event = menu.addAction(tr("pages.event_recorder.menu_copy_event"))
        action_copy_obj = menu.addAction(tr("pages.event_recorder.menu_copy_obj"))
        menu.addSeparator()
        action_filter_obj = menu.addAction(tr("pages.event_recorder.menu_filter_obj"))
        action_filter_grp = menu.addAction(tr("pages.event_recorder.menu_filter_grp"))
        action_filter_prio = menu.addAction(tr("pages.event_recorder.menu_filter_prio"))
        action_show_only_obj = menu.addAction(tr("pages.event_recorder.menu_show_only_obj"))
        menu.addSeparator()
        action_goto = menu.addAction(tr("pages.event_recorder.menu_goto"))
        action_export_sel = menu.addAction(tr("pages.event_recorder.menu_export_sel"))

        action = menu.exec(self.table.mapToGlobal(pos))
        if not action:
            return

        obj_name = self.table.item(row, 3).text()
        event_name = self.table.item(row, 4).text()
        group_name = self.table.item(row, 2).text()
        prio_name = self.table.item(row, 1).text()

        cb = QApplication.clipboard()

        if action == action_copy_row:
            row_data = [self.table.item(row, c).text() for c in range(self.table.columnCount())]
            cb.setText(" | ".join(row_data))
        elif action == action_copy_event:
            cb.setText(event_name)
        elif action == action_copy_obj:
            cb.setText(obj_name)
        elif action == action_filter_obj or action == action_show_only_obj:
            self.txt_search.setText(obj_name)
        elif action == action_filter_grp:
            idx = self.cmb_cat.findText(group_name)
            if idx >= 0: self.cmb_cat.setCurrentIndex(idx)
        elif action == action_filter_prio:
            self.txt_search.setText(prio_name)
        elif action == action_goto:
            ui_logger.log("INFO", "OPERATION", "UI", f"Navigation to {obj_name} requested", "Operator", self.tag_manager.mode, "")
            # Implementation depends on main window navigation hooks
        elif action == action_export_sel:
            self.export_rows_to_csv([row], "selected_event")

    def export_visible_to_csv(self):
        """The 'Export CSV' toolbar button - was created and added to the
        layout but never connected to anything (a no-op button). Exports
        whatever the current search/group filter leaves visible, matching
        what the operator is actually looking at."""
        visible_rows = [r for r in range(self.table.rowCount()) if not self.table.isRowHidden(r)]
        self.export_rows_to_csv(visible_rows, "events")

    def export_rows_to_csv(self, rows, label):
        if not rows:
            QMessageBox.information(self, tr("pages.event_recorder.msgbox_export_title"),
                                     tr("pages.event_recorder.msg_no_events"))
            return

        default_name = f"epw_{label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path, _ = QFileDialog.getSaveFileName(self, tr("pages.event_recorder.msgbox_save_title"), default_name,
                                               tr("pages.historian_export.csv_filter"))
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # self.headers is the same untranslated list used for the
                # on-screen table (see above) - kept as the CSV column
                # names too, consistent either way.
                writer.writerow(self.headers)
                for row in rows:
                    writer.writerow([
                        self.table.item(row, c).text() if self.table.item(row, c) else ""
                        for c in range(self.table.columnCount())
                    ])
        except OSError as e:
            ui_logger.log("WARNING", "OPERATION", "Event Recorder", "CSV export failed", "Operator", self.tag_manager.mode, str(e))
            QMessageBox.warning(self, tr("pages.event_recorder.msgbox_export_title"),
                                 tr("pages.event_recorder.err_export_failed", error=e))
            return

        ui_logger.log("INFO", "OPERATION", "Event Recorder", f"Exported {len(rows)} event(s) to CSV", "Operator", self.tag_manager.mode, path)
        QMessageBox.information(self, tr("pages.event_recorder.msgbox_export_title"),
                                 tr("pages.event_recorder.msg_exported", n=len(rows), path=path))
