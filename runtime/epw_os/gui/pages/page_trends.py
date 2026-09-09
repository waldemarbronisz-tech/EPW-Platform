"""Trends page (Task: "zbieramy dane, ktorych nikt nie widzi" - Historian
has recorded tag_history from day one, but CSV export was the only way to
ever see it). Two modes:

- HISTORY: a bounded range query against Historian.query_tag_history(),
  run on a background QThread (epw_os/core/trend_query.py does the
  actual fetch+downsample, headless - see that module's docstring).
- LIVE: a sliding window, points appended as tag_changed events arrive -
  no DB query at all, pure in-memory.

Both modes share one TrendChart widget (epw_os/gui/widgets/trend_chart.py)
- it has no opinion about where its data came from.

Access: every level (Task: "to podglad, nie sterowanie") - no
access_manager gating anywhere in this page.
"""
import time
from datetime import datetime, timezone

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
                             QListWidget, QListWidgetItem, QPushButton, QComboBox,
                             QDateTimeEdit, QSizePolicy, QRadioButton, QButtonGroup)
from PySide6.QtCore import Qt, QDateTime, QTimer, QObject, QThread, Signal

from epw_os.gui.widgets.trend_chart import TrendChart, MAX_AXES, axis_key_for
from epw_os.gui.theme_manager import get_theme_manager
from epw_os.core.themes import CORE_STATE_KEYS
from epw_os.core.tag_manager import TagType, TagQuality
from epw_os.i18n import tr

# Task: "sensowny limit jednoczesnych przebiegow - zaproponuj i uzasadnij".
# 5, tied directly to CORE_STATE_KEYS: those are the only theme colors
# themes.py's own state_colors_distinguishable() (enforced by
# test_themes.py, for EVERY one of the 5 visual themes already) guarantees
# are pairwise distinguishable AND distinguishable from the panel/window
# background. Any 6th trace would need a color with no such guarantee -
# checked empirically against all 5 themes while designing this feature,
# every other theme color collides with another in at least one theme
# (see SESSION_REPORT.md). An honest limit beats a 6th trace nobody can
# actually tell apart from one of the first 5.
MAX_TREND_TAGS = len(CORE_STATE_KEYS)

LIVE_WINDOW_OPTIONS = [
    ("1min", 60), ("5min", 300), ("15min", 900), ("1h", 3600),
]


class TrendQueryWorker(QObject):
    """Runs one fetch_trend_series() call on a background QThread - see
    page_trends.py's _start_history_load(). Qt-aware (Signals), so this
    lives in gui/, not core/; the actual query/downsample logic it calls
    into (trend_query.py) stays headless."""
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, historian, project_manager, tag_names, start_dt, end_dt, width_px):
        super().__init__()
        self.historian = historian
        self.project_manager = project_manager
        self.tag_names = tag_names
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.width_px = width_px

    def run(self):
        try:
            from epw_os.core.trend_query import fetch_trend_series
            result = fetch_trend_series(
                self.historian, self.project_manager, self.tag_names,
                self.start_dt, self.end_dt, self.width_px,
            )
            self.finished.emit(result)
        except Exception as e:  # noqa: BLE001 - report to the GUI, don't crash the worker thread silently
            self.failed.emit(str(e))


class PageTrends(QWidget):
    MODE_HISTORY = "history"
    MODE_LIVE = "live"

    def __init__(self, tag_manager, historian, project_manager=None, parent=None):
        super().__init__(parent)
        self.tag_manager = tag_manager
        self.historian = historian
        self.project_manager = project_manager
        self.theme_manager = get_theme_manager()

        self._mode = self.MODE_HISTORY
        self._selected_tags = []       # ordered - order also drives color assignment
        self._thread = None
        self._worker = None
        self._live_timer = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel(tr("nav.trends"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PageHeader")
        layout.addWidget(title)

        body = QHBoxLayout()
        layout.addLayout(body, stretch=1)

        # --- Left: tag picker + mode controls --------------------------
        side = QFrame()
        side.setObjectName("SunkenFrame")
        side.setFixedWidth(230)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(6, 6, 6, 6)

        mode_row = QHBoxLayout()
        self.rb_history = QRadioButton(tr("pages.trends.mode_history"))
        self.rb_history.setToolTip(tr("pages.trends.tooltip_mode_history"))
        self.rb_live = QRadioButton(tr("pages.trends.mode_live"))
        self.rb_live.setToolTip(tr("pages.trends.tooltip_mode_live"))
        self.rb_history.setChecked(True)
        mode_group = QButtonGroup(self)
        mode_group.addButton(self.rb_history)
        mode_group.addButton(self.rb_live)
        mode_row.addWidget(self.rb_history)
        mode_row.addWidget(self.rb_live)
        side_layout.addLayout(mode_row)
        self.rb_history.toggled.connect(self._on_mode_toggled)

        # History controls
        self.history_controls = QFrame()
        hc_layout = QVBoxLayout(self.history_controls)
        hc_layout.setContentsMargins(0, 0, 0, 0)
        hc_layout.addWidget(QLabel(tr("pages.trends.lbl_from")))
        self.dt_from = QDateTimeEdit(QDateTime.currentDateTime().addSecs(-3600))
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_from.setToolTip(tr("pages.trends.tooltip_range"))
        hc_layout.addWidget(self.dt_from)
        hc_layout.addWidget(QLabel(tr("pages.trends.lbl_to")))
        self.dt_to = QDateTimeEdit(QDateTime.currentDateTime())
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_to.setToolTip(tr("pages.trends.tooltip_range"))
        hc_layout.addWidget(self.dt_to)
        self.btn_load = QPushButton(tr("pages.trends.btn_load"))
        self.btn_load.setToolTip(tr("pages.trends.tooltip_btn_load"))
        self.btn_load.clicked.connect(self._start_history_load)
        hc_layout.addWidget(self.btn_load)
        side_layout.addWidget(self.history_controls)

        # Live controls
        self.live_controls = QFrame()
        lc_layout = QVBoxLayout(self.live_controls)
        lc_layout.setContentsMargins(0, 0, 0, 0)
        lc_layout.addWidget(QLabel(tr("pages.trends.lbl_window")))
        self.cmb_window = QComboBox()
        self.cmb_window.setToolTip(tr("pages.trends.tooltip_window"))
        for key, _seconds in LIVE_WINDOW_OPTIONS:
            self.cmb_window.addItem(tr(f"pages.trends.window_{key}"))
        self.cmb_window.currentIndexChanged.connect(self._on_live_window_changed)
        lc_layout.addWidget(self.cmb_window)
        side_layout.addWidget(self.live_controls)
        self.live_controls.setVisible(False)

        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        side_layout.addWidget(self.lbl_status)

        side_layout.addWidget(QLabel(tr("pages.trends.lbl_tags")))
        self.tag_list = QListWidget()
        self.tag_list.setToolTip(tr("pages.trends.tooltip_tag_list", max_tags=MAX_TREND_TAGS, max_axes=MAX_AXES))
        self.tag_list.itemChanged.connect(self._on_tag_checked)
        side_layout.addWidget(self.tag_list, stretch=1)

        body.addWidget(side)

        # --- Right: chart + toolbar -------------------------------------
        right = QVBoxLayout()
        toolbar = QHBoxLayout()
        self.btn_reset_view = QPushButton(tr("pages.trends.btn_reset_view"))
        self.btn_reset_view.setToolTip(tr("pages.trends.tooltip_btn_reset_view"))
        self.btn_reset_view.clicked.connect(self._on_reset_view)
        toolbar.addWidget(self.btn_reset_view)
        self.btn_export = QPushButton(tr("pages.trends.btn_export"))
        self.btn_export.setToolTip(tr("pages.trends.tooltip_btn_export"))
        self.btn_export.clicked.connect(self._on_export)
        toolbar.addWidget(self.btn_export)
        toolbar.addStretch()
        self.lbl_cursor = QLabel("")
        toolbar.addWidget(self.lbl_cursor)
        right.addLayout(toolbar)

        self.chart = TrendChart()
        self.chart.setToolTip(tr("pages.trends.tooltip_chart"))
        self.chart.unit_label = tr("pages.trends.no_unit")
        self.chart.simulated_label = tr("pages.trends.legend_simulated_suffix")
        self.chart.cursor_moved.connect(self._on_cursor_moved)
        right.addWidget(self.chart, stretch=1)

        body.addLayout(right, stretch=1)

        self._refresh_theme_colors()
        self.theme_manager.theme_changed.connect(self._refresh_theme_colors)

        self._populate_tag_list()
        self.tag_manager.tag_changed.connect(self._on_live_tag_changed)

    # --- setup -----------------------------------------------------

    def _refresh_theme_colors(self, *_):
        self.chart.set_theme_colors(self.theme_manager.current_colors())

    def _populate_tag_list(self):
        """Task: "lista wszystkich dostepnych tagow" - Historian's own
        get_distinct_tag_names() (every tag that ever actually recorded
        history), same source historian_export_dialog.py's own tag picker
        already uses - a tag that has never been written is not "available
        to trend" in any useful sense."""
        self.tag_list.blockSignals(True)
        self.tag_list.clear()
        names = self.historian.get_distinct_tag_names() if self.historian is not None else []
        for name in names:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.tag_list.addItem(item)
        self.tag_list.blockSignals(False)

    # --- tag selection / limits --------------------------------------

    def _tag_info(self, tag_name):
        """(unit, is_bool) - cheap, synchronous, from whatever's live
        right now (project_manager's analog point config for unit,
        tag_manager for BOOL-ness) - see trend_query.py's docstring for
        why the actual fetched data is the authoritative source at
        render time; this is only used to police the tag/axis limits
        *before* a query even runs."""
        unit = ""
        if self.project_manager is not None:
            for point in self.project_manager.get_analog_points():
                if point["tag"] == tag_name:
                    unit = point.get("unit", "")
                    break
        is_bool = False
        tag = self.tag_manager.get_tag(tag_name)
        if tag is not None:
            is_bool = tag.data_type == TagType.BOOL
        return unit, is_bool

    def _on_tag_checked(self, item):
        name = item.text()
        checked = item.checkState() == Qt.CheckState.Checked
        if checked:
            if len(self._selected_tags) >= MAX_TREND_TAGS:
                self._revert_check(item)
                self._show_status(tr("pages.trends.err_too_many_tags", n=MAX_TREND_TAGS), error=True)
                return
            candidate_axes = self._axis_keys_for(self._selected_tags + [name])
            if len(candidate_axes) > MAX_AXES:
                self._revert_check(item)
                self._show_status(tr("pages.trends.err_too_many_axes", n=MAX_AXES), error=True)
                return
            self._selected_tags.append(name)
        else:
            if name in self._selected_tags:
                self._selected_tags.remove(name)
        self._show_status("")
        if self._mode == self.MODE_LIVE:
            self._rebuild_live_series()
        # HISTORY mode: selection changes don't auto-query (Task doesn't
        # ask for that, and re-querying on every checkbox click would be
        # wasteful) - the operator clicks "Load" when ready, same as
        # historian_export_dialog.py's own "pick tags, then Export" flow.

    def _revert_check(self, item):
        self.tag_list.blockSignals(True)
        item.setCheckState(Qt.CheckState.Unchecked)
        self.tag_list.blockSignals(False)

    def _axis_keys_for(self, tag_names):
        keys = []
        for name in tag_names:
            unit, is_bool = self._tag_info(name)
            key = axis_key_for(unit, is_bool)
            if key not in keys:
                keys.append(key)
        return keys

    def _show_status(self, text, error=False):
        self.lbl_status.setText(text)
        if text and error:
            colors = self.theme_manager.current_colors()
            self.lbl_status.setStyleSheet(f"color: {colors['state_alarm']}; font-weight: bold;")
        else:
            self.lbl_status.setStyleSheet("")

    def _color_for(self, tag_name):
        idx = self._selected_tags.index(tag_name) if tag_name in self._selected_tags else 0
        key = CORE_STATE_KEYS[idx % len(CORE_STATE_KEYS)]
        return self.theme_manager.current_colors()[key]

    # --- mode switch -------------------------------------------------

    def _on_mode_toggled(self, history_checked):
        self._mode = self.MODE_HISTORY if history_checked else self.MODE_LIVE
        self.history_controls.setVisible(self._mode == self.MODE_HISTORY)
        self.live_controls.setVisible(self._mode == self.MODE_LIVE)
        self._show_status("")
        if self._mode == self.MODE_LIVE:
            self._start_live()
        else:
            self._stop_live()

    def _on_live_window_changed(self, *_):
        if self._mode == self.MODE_LIVE:
            self._rebuild_live_series()

    def _live_window_seconds(self):
        idx = max(0, self.cmb_window.currentIndex())
        return LIVE_WINDOW_OPTIONS[idx][1]

    def _start_live(self):
        self._rebuild_live_series()
        if self._live_timer is None:
            self._live_timer = QTimer(self)
            self._live_timer.timeout.connect(self.chart.tick_live_window)
        # A 1s repaint heartbeat, independent of tag_changed frequency -
        # keeps the sliding window's left edge (a pure function of "now",
        # not of the last received sample) visibly moving even for a tag
        # that hasn't changed value in a while, matching the task's
        # "przesuwajace sie okno czasowe" description exactly.
        self._live_timer.start(1000)

    def _stop_live(self):
        if self._live_timer is not None:
            self._live_timer.stop()

    def _rebuild_live_series(self):
        window = self._live_window_seconds()
        now = time.time()
        series = []
        for name in self._selected_tags:
            unit, is_bool = self._tag_info(name)
            tag = self.tag_manager.get_tag(name)
            is_simulated = tag is not None and tag.quality == TagQuality.SIMULATED
            points = []
            if tag is not None:
                v = self._numeric_value(tag.value, is_bool)
                if v is not None:
                    points.append((now, v))
            series.append({
                "tag_name": name, "unit": unit, "is_bool": is_bool,
                "is_simulated": is_simulated, "color": self._color_for(name),
                "points": points,
            })
        self.chart.set_series(series, reset_view=False)
        self.chart.set_live_window(now - window, now)

    @staticmethod
    def _numeric_value(value, is_bool):
        if is_bool:
            return 1.0 if value else 0.0
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        if isinstance(value, (int, float)):
            return float(value)
        return None

    def _on_live_tag_changed(self, tag_name, value, _quality):
        if self._mode != self.MODE_LIVE or tag_name not in self._selected_tags:
            return
        unit, is_bool = self._tag_info(tag_name)
        v = self._numeric_value(value, is_bool)
        if v is None:
            return
        self.chart.append_point(tag_name, time.time(), v, window_seconds=self._live_window_seconds())

    # --- history load (background thread) -----------------------------

    def _start_history_load(self):
        if self.historian is None:
            self._show_status(tr("pages.trends.err_no_historian"), error=True)
            return
        if not self._selected_tags:
            self._show_status(tr("pages.trends.err_no_tags_selected"), error=True)
            return
        if self._thread is not None:
            return  # a load is already running - Load button stays enabled but this is a harmless no-op

        # Same UTC<->local conversion historian_export_dialog.py already
        # uses (Task: "zerknij, jak tam rozwiazano konwersje, i zrob tak
        # samo") - QDateTime already knows the picker's local timezone;
        # toUTC() converts correctly (DST included), toPython() hands
        # back a naive UTC datetime matching how Historian stores rows.
        # (.toPython(), not .toPyDateTime() - see historian_export_dialog.py's
        # own comment on this same line: toPyDateTime() doesn't exist on
        # the installed PySide6, a bug found while writing this copy of
        # its pattern - see SESSION_REPORT.md.)
        start = self.dt_from.dateTime().toUTC().toPython()
        end = self.dt_to.dateTime().toUTC().toPython()
        if start >= end:
            self._show_status(tr("pages.trends.err_from_after_to"), error=True)
            return

        width_px = max(200, self.chart.width())
        self._worker = TrendQueryWorker(self.historian, self.project_manager,
                                          list(self._selected_tags), start, end, width_px)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_history_loaded)
        self._worker.failed.connect(self._on_history_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_finished)
        self.btn_load.setEnabled(False)
        self._show_status(tr("pages.trends.msg_loading"))
        self._thread.start()

    def _on_thread_finished(self):
        # Deferred cleanup, not deleteLater() from inside a slot connected
        # to this same thread's own finished signal timing edge case - a
        # plain None-out is enough since this page owns the only
        # reference and never reuses a QThread instance across loads.
        self._thread = None
        self._worker = None
        self.btn_load.setEnabled(True)

    def _on_history_loaded(self, result: dict):
        series = []
        excluded = []
        for name in self._selected_tags:
            data = result.get(name)
            if data is None:
                continue
            if data.excluded_reason:
                excluded.append(name)
                continue
            series.append({
                "tag_name": data.tag_name, "unit": data.unit, "is_bool": data.is_bool,
                "is_simulated": data.is_simulated, "color": self._color_for(data.tag_name),
                "points": data.points,
            })
        self.chart.set_series(series, reset_view=True)
        if excluded:
            self._show_status(tr("pages.trends.msg_excluded_string_tags", tags=", ".join(excluded)), error=True)
        else:
            total_points = sum(len(s["points"]) for s in series)
            self._show_status(tr("pages.trends.msg_loaded", n=total_points))

    def _on_history_failed(self, message: str):
        self._show_status(tr("pages.trends.err_load_failed", error=message), error=True)

    # --- toolbar -------------------------------------------------------

    def _on_reset_view(self):
        self.chart.reset_view()

    def _on_cursor_moved(self, info):
        if not info:
            self.lbl_cursor.setText("")
            return
        parts = [self.chart.format_time(info["time"])]
        for r in info["readings"]:
            shown = ("1" if r["value"] > 0.5 else "0") if r["is_bool"] else f"{r['value']:.3f}"
            parts.append(f"{r['tag_name']}={shown}{r['unit']}")
        self.lbl_cursor.setText("  ".join(parts))

    def _on_export(self):
        """Task: "Skorzystaj z istniejacego mechanizmu eksportu z
        Historiana, nie buduj drugiego" - opens the exact same
        HistorianExportDialog Tools > Export Historical Data... uses,
        pre-filled with the chart's current visible range and the
        currently selected tags, instead of a second CSV writer."""
        if self.historian is None:
            self._show_status(tr("pages.trends.err_no_historian"), error=True)
            return
        from epw_os.gui.widgets.historian_export_dialog import HistorianExportDialog
        view_start, view_end = self.chart.visible_range()
        initial_from = datetime.fromtimestamp(view_start, tz=timezone.utc)
        initial_to = datetime.fromtimestamp(view_end, tz=timezone.utc)
        dlg = HistorianExportDialog(
            self.historian, self.tag_manager, self,
            initial_from_utc=initial_from, initial_to_utc=initial_to,
            initial_tags=list(self._selected_tags) or None,
        )
        dlg.exec()

    # --- lifecycle -------------------------------------------------

    def shutdown(self):
        """Called from MainWindow.shutdown_gui() - a background QThread
        left running (or a live QTimer still ticking) when the process
        exits is the same class of dangling-callback risk documented on
        MainWindow.shutdown_gui() itself, just for this page's own
        thread/timer instead of an installEventFilter()."""
        self._stop_live()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
