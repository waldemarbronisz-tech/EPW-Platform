"""Custom-painted multi-series trend chart - built entirely on QPainter,
no charting library (GRANICE: no new dependencies; if a library felt
unavoidable the instruction was to stop and say so in the report instead
of adding one - see SESSION_REPORT.md for why it wasn't needed here).

Used by page_trends.py for both HISTORY (a fetched, already-downsampled
batch - see epw_os/core/trend_query.py) and LIVE (a sliding window,
points appended incrementally) modes - this widget itself has no opinion
about where its data came from, only how to draw it.
"""
import time
from bisect import bisect_left

from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QFont

# Task: "sensowny limit osi - zaproponuj i uzasadnij". 4: beyond that,
# each additional fixed-width axis strip eats into the plot area badly
# enough on a typical panel-PC width (1024px - see window_state.py's
# DEFAULT_WIDTH) that the chart itself gets cramped; with a 5-trace cap
# (see page_trends.py's MAX_TREND_TAGS), 4 axes already covers the
# realistic worst case of "4 different units + one repeat" without ever
# forcing two genuinely different units to share a scale.
MAX_AXES = 4

AXIS_STRIP_WIDTH = 58
BOTTOM_MARGIN = 34
TOP_MARGIN = 10
RIGHT_MARGIN = 16
LEGEND_HEIGHT = 22

# A boolean series is always drawn on its own kind of axis (0/1, fixed
# range) - grouping it by "unit" (typically "", same as every other
# unitless REAL tag like Meas.L1) would let a real value's own axis
# auto-fit swallow a 0/1 step trace into a flat line at the bottom -
# exactly the "current and voltage on one axis" problem this whole
# feature exists to avoid, just for a different pair of series.
def axis_key_for(unit: str, is_bool: bool) -> str:
    return "__BOOL__" if is_bool else (unit or "")


class TrendChart(QWidget):
    """series: list of dicts, each:
        {"tag_name": str, "unit": str, "is_bool": bool, "is_simulated": bool,
         "color": "#RRGGBB", "points": [(epoch_seconds, value), ...]}
    Points must be sorted by time (trend_query.py already returns them
    that way). Simulated series are drawn dashed - the same distinction
    the previous session's SIMULATED tag quality introduced elsewhere in
    the UI, not a new convention invented here.
    """

    #: emitted after the visible time window changes (pan/zoom/reset), so
    #: page_trends.py can update its own "visible range" labels/export
    #: pre-fill - purely informational, this widget never re-queries data
    #: itself.
    view_changed = Signal(float, float)
    #: emitted on mouse hover with the nearest sample time/values, so
    #: page_trends.py can show a readout beside the chart too (in
    #: addition to the in-chart crosshair box this widget already draws).
    cursor_moved = Signal(object)  # dict or None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(420, 260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self._series = []
        self._data_start = 0.0
        self._data_end = 1.0
        self._view_start = 0.0
        self._view_end = 1.0
        self._axes = []  # ordered list of axis keys actually present
        self._drag_anchor_px = None
        self._drag_anchor_view = None
        self._cursor_px = None
        self.theme_colors = {}
        self.unit_label = ""       # tr("pages.trends.no_unit") - set by caller
        self.simulated_label = ""  # tr("pages.trends.legend_simulated_suffix")
        self._live_window_seconds = None  # set by set_live_window(); None = HISTORY mode

    # --- public API ----------------------------------------------------

    def set_theme_colors(self, colors: dict):
        self.theme_colors = colors or {}
        self.update()

    def set_series(self, series_list, reset_view: bool = True):
        # Cleared here, re-armed by set_live_window() right after in LIVE
        # mode (see page_trends.py's _rebuild_live_series()) - keeps a
        # stale live-window setting from a previous mode/tag switch from
        # ever affecting a HISTORY-mode chart.
        self._live_window_seconds = None
        self._series = series_list
        seen = []
        for s in series_list:
            key = axis_key_for(s["unit"], s["is_bool"])
            if key not in seen:
                seen.append(key)
        self._axes = seen[:MAX_AXES]

        all_t = [t for s in series_list for t, _v in s["points"]]
        if all_t:
            self._data_start = min(all_t)
            self._data_end = max(all_t)
            if self._data_end <= self._data_start:
                self._data_end = self._data_start + 1.0
        else:
            now = time.time()
            self._data_start, self._data_end = now - 60.0, now
        if reset_view:
            self.reset_view()
        else:
            self.update()

    def append_point(self, tag_name: str, t: float, v: float, window_seconds: float = None):
        """LIVE mode: append one sample to an existing series in place,
        drop anything older than `window_seconds` (a sliding window), and
        keep the view pinned to "now" - the live chart auto-scrolls."""
        for s in self._series:
            if s["tag_name"] != tag_name:
                continue
            s["points"].append((t, v))
            if window_seconds is not None:
                cutoff = t - window_seconds
                while s["points"] and s["points"][0][0] < cutoff:
                    s["points"].pop(0)
            break
        self._data_end = t
        if window_seconds is not None:
            self._data_start = t - window_seconds
        self._view_start, self._view_end = self._data_start, self._data_end
        self.update()

    def reset_view(self):
        self._view_start = self._data_start
        self._view_end = self._data_end
        self.view_changed.emit(self._view_start, self._view_end)
        self.update()

    def set_live_window(self, start: float, end: float):
        """LIVE mode only: pins the data/view range to an explicit
        [start, end] window instead of deriving it from set_series()'s
        (possibly single-point, possibly empty) data - a freshly selected
        live tag has at most one seed sample, which set_series()'s normal
        "span = data min..max" logic would otherwise collapse to a
        degenerate zero-width view."""
        self._live_window_seconds = end - start
        self._data_start, self._data_end = start, end
        self._view_start, self._view_end = start, end
        self.update()

    def tick_live_window(self, now: float = None):
        """Advances the sliding window to "now" even when no new sample
        has arrived since the last tick (Task: "przesuwajace sie okno
        czasowe" - the window moves with wall-clock time, not just with
        incoming data) - called by page_trends.py's 1s heartbeat timer
        while in LIVE mode. A no-op before set_live_window() has ever
        been called (HISTORY mode, or LIVE mode with nothing selected
        yet)."""
        if self._live_window_seconds is None:
            return
        now = now if now is not None else time.time()
        self._data_end = now
        self._data_start = now - self._live_window_seconds
        self._view_start, self._view_end = self._data_start, self._data_end
        for s in self._series:
            pts = s["points"]
            while pts and pts[0][0] < self._data_start:
                pts.pop(0)
        self.update()

    # --- geometry --------------------------------------------------

    def _plot_rect(self) -> QRectF:
        left = AXIS_STRIP_WIDTH * max(1, len(self._axes))
        top = TOP_MARGIN + LEGEND_HEIGHT
        w = max(10, self.width() - left - RIGHT_MARGIN)
        h = max(10, self.height() - top - BOTTOM_MARGIN)
        return QRectF(left, top, w, h)

    def _x_for(self, t: float, plot: QRectF) -> float:
        span = self._view_end - self._view_start
        if span <= 0:
            return plot.left()
        return plot.left() + (t - self._view_start) / span * plot.width()

    def _visible_range_for_axis(self, axis_key: str):
        """(y_min, y_max) computed only from points inside the current
        view window (Task: "automatyczne dopasowanie skali pionowej do
        widocznego zakresu") - recomputed on every paint, so pan/zoom
        always rescales instead of showing the full-range scale."""
        if axis_key == "__BOOL__":
            return -0.15, 1.15
        vmin, vmax = None, None
        for s in self._series:
            if axis_key_for(s["unit"], s["is_bool"]) != axis_key:
                continue
            pts = s["points"]
            if not pts:
                continue
            times = [p[0] for p in pts]
            lo = bisect_left(times, self._view_start)
            hi = bisect_left(times, self._view_end)
            lo = max(0, lo - 1)  # one point before the window, so a line entering it isn't clipped flat
            hi = min(len(pts), hi + 1)
            for _t, v in pts[lo:hi]:
                if vmin is None or v < vmin:
                    vmin = v
                if vmax is None or v > vmax:
                    vmax = v
        if vmin is None:
            return 0.0, 1.0
        if vmax == vmin:
            pad = abs(vmax) * 0.1 or 1.0
            return vmin - pad, vmax + pad
        pad = (vmax - vmin) * 0.08
        return vmin - pad, vmax + pad

    def _y_for(self, v: float, y_min: float, y_max: float, plot: QRectF) -> float:
        span = y_max - y_min
        if span <= 0:
            return plot.center().y()
        ratio = (v - y_min) / span
        return plot.bottom() - ratio * plot.height()

    # --- painting --------------------------------------------------

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        tc = self.theme_colors
        bg = QColor(tc.get("field_bg", "#000000"))
        grid = QColor(tc.get("grid_line", "#444444"))
        text_color = QColor(tc.get("text", "#FFFFFF"))
        p.fillRect(self.rect(), bg)

        plot = self._plot_rect()
        p.fillRect(plot, QColor(tc.get("lcd_bg", "#000000")))

        axis_ranges = {key: self._visible_range_for_axis(key) for key in self._axes}

        self._draw_grid_and_x_axis(p, plot, grid, text_color)
        for i, key in enumerate(self._axes):
            self._draw_y_axis(p, plot, i, key, axis_ranges[key], text_color, grid)

        for s in self._series:
            key = axis_key_for(s["unit"], s["is_bool"])
            y_min, y_max = axis_ranges.get(key, (0.0, 1.0))
            self._draw_series(p, plot, s, y_min, y_max)

        self._draw_legend(p, text_color)
        if self._cursor_px is not None and plot.left() <= self._cursor_px <= plot.right():
            self._draw_crosshair(p, plot, text_color, tc)

        p.end()

    def _draw_grid_and_x_axis(self, p, plot, grid_color, text_color):
        p.setPen(QPen(grid_color, 1))
        p.drawRect(plot)
        # 5 vertical gridlines + time labels, evenly spaced across the view.
        p.setFont(QFont("Tahoma", 7))
        fm = p.fontMetrics()
        n = 5
        for i in range(n + 1):
            x = plot.left() + plot.width() * i / n
            p.setPen(QPen(grid_color, 1, Qt.PenStyle.DotLine))
            p.drawLine(int(x), int(plot.top()), int(x), int(plot.bottom()))
            t = self._view_start + (self._view_end - self._view_start) * i / n
            label = self.format_time(t)
            p.setPen(QPen(text_color))
            tw = fm.horizontalAdvance(label)
            lx = min(max(x - tw / 2, 0), self.width() - tw)
            p.drawText(int(lx), int(plot.bottom() + 16), label)

    def format_time(self, epoch: float) -> str:
        span = self._view_end - self._view_start
        dt = time.localtime(epoch)
        if span > 3600 * 20:
            return time.strftime("%Y-%m-%d", dt)
        if span > 3600 * 2:
            return time.strftime("%m-%d %H:%M", dt)
        return time.strftime("%H:%M:%S", dt)

    def _draw_y_axis(self, p, plot, index, axis_key, y_range, text_color, grid_color):
        y_min, y_max = y_range
        strip_left = AXIS_STRIP_WIDTH * index
        strip_right = strip_left + AXIS_STRIP_WIDTH
        p.setPen(QPen(text_color))
        p.setFont(QFont("Tahoma", 7, QFont.Weight.Bold))
        unit_text = "BOOL" if axis_key == "__BOOL__" else (axis_key or self.unit_label)
        p.drawText(int(strip_left + 4), int(TOP_MARGIN + LEGEND_HEIGHT - 2), unit_text)

        p.setFont(QFont("Tahoma", 7))
        ticks = 4
        for i in range(ticks + 1):
            frac = i / ticks
            y = plot.bottom() - plot.height() * frac
            value = y_min + (y_max - y_min) * frac
            label = "1" if (axis_key == "__BOOL__" and value > 0.5) else \
                    "0" if (axis_key == "__BOOL__" and value <= 0.5) else f"{value:.2f}".rstrip("0").rstrip(".")
            p.setPen(QPen(grid_color, 1, Qt.PenStyle.DotLine))
            p.drawLine(int(plot.left()), int(y), int(plot.right()), int(y))
            p.setPen(QPen(text_color))
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(label)
            p.drawText(int(strip_right - tw - 4), int(y + 4), label)

    def _draw_series(self, p, plot, s, y_min, y_max):
        points = s["points"]
        if not points:
            return
        color = QColor(s["color"])
        pen = QPen(color, 2)
        if s["is_simulated"]:
            pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setClipRect(plot)

        prev_px = None
        for t, v in points:
            x = self._x_for(t, plot)
            y = self._y_for(v, y_min, y_max, plot)
            if prev_px is not None:
                if s["is_bool"]:
                    # Step, not interpolated (Task: "stan zmienia sie
                    # skokowo, nie plynnie") - horizontal at the old
                    # value up to the new sample's time, then a vertical
                    # jump, exactly matching a digital signal's real shape.
                    p.drawLine(QPointF(prev_px[0], prev_px[1]), QPointF(x, prev_px[1]))
                    p.drawLine(QPointF(x, prev_px[1]), QPointF(x, y))
                else:
                    p.drawLine(QPointF(prev_px[0], prev_px[1]), QPointF(x, y))
            prev_px = (x, y)
        p.setClipping(False)

    def _draw_legend(self, p, text_color):
        x = AXIS_STRIP_WIDTH * max(1, len(self._axes))
        y = TOP_MARGIN + 4
        p.setFont(QFont("Tahoma", 8))
        fm = p.fontMetrics()
        for s in self._series:
            color = QColor(s["color"])
            p.setPen(QPen(color, 3))
            p.drawLine(int(x), int(y + 6), int(x) + 14, int(y + 6))
            label = s["tag_name"]
            if s["unit"]:
                label += f" [{s['unit']}]"
            if s["is_simulated"]:
                label += f" {self.simulated_label}"
            p.setPen(QPen(text_color))
            p.drawText(int(x) + 18, int(y + 10), label)
            x += 18 + fm.horizontalAdvance(label) + 16
            if x > self.width() - RIGHT_MARGIN - 40:
                break  # Task doesn't require legend wrapping; truncating
                       # gracefully beats overdrawing off the widget edge.

    def _draw_crosshair(self, p, plot, text_color, tc):
        x = self._cursor_px
        p.setPen(QPen(QColor(tc.get("text_disabled", "#888888")), 1, Qt.PenStyle.DashLine))
        p.drawLine(int(x), int(plot.top()), int(x), int(plot.bottom()))

        t_at_cursor = self._view_start + (x - plot.left()) / max(1.0, plot.width()) * (self._view_end - self._view_start)
        lines = [self.format_time(t_at_cursor) + " " + time.strftime("%Y", time.localtime(t_at_cursor))]
        for s in self._series:
            v = self._nearest_value(s["points"], t_at_cursor)
            if v is None:
                continue
            shown = "1" if (s["is_bool"] and v > 0.5) else "0" if s["is_bool"] else f"{v:.3f}"
            lines.append(f"{s['tag_name']}: {shown}{(' ' + s['unit']) if s['unit'] else ''}")

        p.setFont(QFont("Tahoma", 8))
        fm = p.fontMetrics()
        box_w = max(fm.horizontalAdvance(line) for line in lines) + 12
        box_h = fm.height() * len(lines) + 8
        box_x = x + 8 if x + 8 + box_w < self.width() else x - 8 - box_w
        box_y = plot.top() + 4
        p.fillRect(QRectF(box_x, box_y, box_w, box_h), QColor(tc.get("console_bg", "#000000")))
        p.setPen(QPen(QColor(tc.get("console_border", "#888888"))))
        p.drawRect(QRectF(box_x, box_y, box_w, box_h))
        p.setPen(QPen(QColor(tc.get("console_text", text_color.name()))))
        for i, line in enumerate(lines):
            p.drawText(int(box_x + 6), int(box_y + fm.height() * (i + 1)), line)

    @staticmethod
    def _nearest_value(points, t):
        if not points:
            return None
        times = [pt[0] for pt in points]
        idx = bisect_left(times, t)
        if idx <= 0:
            return points[0][1]
        if idx >= len(points):
            return points[-1][1]
        before, after = points[idx - 1], points[idx]
        return before[1] if (t - before[0]) <= (after[0] - t) else after[1]

    # --- interaction (zoom / pan / crosshair) ---------------------

    def wheelEvent(self, event):
        plot = self._plot_rect()
        x = event.position().x()
        if not (plot.left() <= x <= plot.right()):
            return
        factor = 0.85 if event.angleDelta().y() > 0 else (1 / 0.85)
        anchor_t = self._view_start + (x - plot.left()) / max(1.0, plot.width()) * (self._view_end - self._view_start)
        new_span = (self._view_end - self._view_start) * factor
        # Never zoom in tighter than 1 second, or out past the full
        # fetched/live data range - there's nothing more to show either way.
        full_span = max(1.0, self._data_end - self._data_start)
        new_span = max(1.0, min(new_span, full_span))
        left_frac = (anchor_t - self._view_start) / max(1e-9, self._view_end - self._view_start)
        self._view_start = anchor_t - new_span * left_frac
        self._view_end = self._view_start + new_span
        self._clamp_view()
        self.view_changed.emit(self._view_start, self._view_end)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_anchor_px = event.position().x()
            self._drag_anchor_view = (self._view_start, self._view_end)

    def mouseMoveEvent(self, event):
        x = event.position().x()
        self._cursor_px = x
        if self._drag_anchor_px is not None:
            plot = self._plot_rect()
            dx = x - self._drag_anchor_px
            span = self._drag_anchor_view[1] - self._drag_anchor_view[0]
            dt = -dx / max(1.0, plot.width()) * span
            self._view_start = self._drag_anchor_view[0] + dt
            self._view_end = self._drag_anchor_view[1] + dt
            self._clamp_view()
            self.view_changed.emit(self._view_start, self._view_end)
        self._emit_cursor_info(x)
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_anchor_px = None
            self._drag_anchor_view = None

    def leaveEvent(self, event):
        self._cursor_px = None
        self.cursor_moved.emit(None)
        self.update()

    def _clamp_view(self):
        span = self._view_end - self._view_start
        if self._view_start < self._data_start:
            self._view_start = self._data_start
            self._view_end = self._view_start + span
        if self._view_end > self._data_end:
            self._view_end = self._data_end
            self._view_start = self._view_end - span

    def _emit_cursor_info(self, x):
        plot = self._plot_rect()
        if not (plot.left() <= x <= plot.right()):
            self.cursor_moved.emit(None)
            return
        t = self._view_start + (x - plot.left()) / max(1.0, plot.width()) * (self._view_end - self._view_start)
        readings = []
        for s in self._series:
            v = self._nearest_value(s["points"], t)
            if v is not None:
                readings.append({"tag_name": s["tag_name"], "value": v, "unit": s["unit"], "is_bool": s["is_bool"]})
        self.cursor_moved.emit({"time": t, "readings": readings})

    def visible_range(self):
        return self._view_start, self._view_end
