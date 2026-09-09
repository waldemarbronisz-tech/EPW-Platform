"""Historical trend data: fetch + downsample, for the Trends page
(epw_os/gui/pages/page_trends.py).

Headless (no PyQt import) on purpose, same rule as every other core/
module - this is the piece a background QThread worker calls into (see
TrendQueryWorker in page_trends.py), and keeping it importable/testable
without a QApplication is what makes an automated "large range doesn't
load everything into memory / doesn't block" check possible at all.

Read-only: this module only ever calls Historian.query_tag_history(),
never touches how Historian writes (GRANICE).
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from epw_os.core.historian import tag_history_value
from epw_os.core.analog_scaling import compute_display_value, normalize_config


# Any chart narrower than this still gets this many candidate samples per
# series - a floor, not a target, so a small/embedded window doesn't fall
# back to a handful of points that hide real excursions between them.
MIN_TARGET_POINTS = 200

# Roughly 2 raw samples surviving per horizontal pixel is already more
# resolution than a human eye (or the line width itself) can distinguish -
# comfortably below where painting cost or memory would become a concern,
# while still preserving fine detail when zoomed in on a narrow window.
POINTS_PER_PIXEL = 2


def target_point_count(width_px: int) -> int:
    return max(MIN_TARGET_POINTS, int(width_px) * POINTS_PER_PIXEL)


def downsample_min_max(points: List[Tuple[float, float]], target_points: int) -> List[Tuple[float, float]]:
    """Bucket `points` (already sorted by time) into `target_points // 2`
    time buckets and keep only the min- and max-valued sample in each
    bucket (both, in original time order) - a standard, dependency-free
    decimation strategy that (unlike naive "every Nth point") can't hide
    a real spike or a boolean's brief pulse that happens to land between
    the points a naive stride would have kept: if a bucket contains both
    a 0 and a 1, both survive, so the transition is never silently lost.

    A no-op (returns `points` unchanged) when there are already fewer
    points than the target - most live/short-range queries never reach
    this path at all."""
    n = len(points)
    if n <= target_points or n <= 2:
        return points

    bucket_count = max(1, target_points // 2)
    t_start = points[0][0]
    t_end = points[-1][0]
    span = t_end - t_start
    if span <= 0:
        # All samples share (rounding-identical) timestamps - nothing a
        # time-bucket split can meaningfully separate; first/last is the
        # best any decimation could do here anyway.
        return [points[0], points[-1]]

    buckets: List[List[Tuple[float, float]]] = [[] for _ in range(bucket_count)]
    for t, v in points:
        idx = int((t - t_start) / span * bucket_count)
        if idx >= bucket_count:
            idx = bucket_count - 1
        buckets[idx].append((t, v))

    out: List[Tuple[float, float]] = []
    for bucket in buckets:
        if not bucket:
            continue
        if len(bucket) == 1:
            out.append(bucket[0])
            continue
        lo = min(bucket, key=lambda p: p[1])
        hi = max(bucket, key=lambda p: p[1])
        # Keep min/max in their original time order, not always lo-then-hi -
        # a chart line jumping around should still trace time left-to-right.
        if lo[0] <= hi[0]:
            out.append(lo)
            out.append(hi)
        else:
            out.append(hi)
            out.append(lo)
    return out


class TrendSeriesData:
    """One tag's plottable data for a chart, already unit-scaled (if it's
    an analog point) and downsampled - the chart widget itself does no DB
    work and no scaling, only painting."""

    __slots__ = ("tag_name", "unit", "is_bool", "is_simulated", "points", "excluded_reason")

    def __init__(self, tag_name: str, unit: str = "", is_bool: bool = False,
                 is_simulated: bool = False, points: Optional[List[Tuple[float, float]]] = None,
                 excluded_reason: Optional[str] = None):
        self.tag_name = tag_name
        self.unit = unit
        self.is_bool = is_bool
        self.is_simulated = is_simulated
        self.points = points or []
        # None unless this tag couldn't be plotted at all (e.g. STRING
        # data) - the caller (page_trends.py) surfaces this to the
        # operator instead of just silently dropping the tag.
        self.excluded_reason = excluded_reason


def fetch_trend_series(historian, project_manager, tag_names: List[str],
                        start_dt: datetime, end_dt: datetime, width_px: int) -> Dict[str, TrendSeriesData]:
    """One bounded query per call (Historian.query_tag_history() is
    already filtered by time range + tag list, with its own hard safety
    cap on rows - see historian.py) - not "load the whole table". Safe to
    call from a background thread: Historian's read methods open their
    own short-lived SQLAlchemy session and return plain objects/values,
    nothing here touches Qt.

    Returns {tag_name: TrendSeriesData}, one entry per requested tag
    (even one with zero rows in range, or an excluded STRING tag) so the
    caller always has something to report for every tag it asked about.
    """
    unit_by_tag: Dict[str, dict] = {}
    if project_manager is not None:
        for point in project_manager.get_analog_points():
            unit_by_tag[point["tag"]] = point

    target = target_point_count(width_px)
    result: Dict[str, TrendSeriesData] = {}

    for tag_name in tag_names:
        rows = historian.query_tag_history(start_dt, end_dt, tag_names=[tag_name])
        if rows and rows[0].data_type == "STRING":
            result[tag_name] = TrendSeriesData(
                tag_name, excluded_reason="string_not_plottable",
            )
            continue

        is_bool = bool(rows) and rows[0].data_type == "BOOL"
        is_simulated = any(r.quality == "SIMULATED" for r in rows)
        analog_point = unit_by_tag.get(tag_name)
        unit = analog_point.get("unit", "") if analog_point else ""

        points: List[Tuple[float, float]] = []
        for row in rows:
            if row.timestamp is None:
                continue
            raw_value = tag_history_value(row)
            if raw_value is None:
                continue
            # row.timestamp is a NAIVE datetime that Historian stored as
            # UTC (datetime.utcnow(), see historian.py) - plain
            # .timestamp() on a naive datetime assumes it's *local* time
            # (Python's own documented behavior), which would silently
            # shift every point on the chart by the local UTC offset.
            # Attaching tzinfo=utc first (not .astimezone(), which would
            # also shift the clock numbers - here they must NOT move, only
            # get the correct label attached) makes .timestamp() compute
            # the correct epoch value instead.
            t = row.timestamp.replace(tzinfo=timezone.utc).timestamp()
            if is_bool:
                v = 1.0 if raw_value else 0.0
            elif analog_point is not None:
                v = float(compute_display_value(raw_value, analog_point))
            else:
                v = float(raw_value)
            points.append((t, v))

        points = downsample_min_max(points, target)
        result[tag_name] = TrendSeriesData(
            tag_name, unit=unit, is_bool=is_bool, is_simulated=is_simulated, points=points,
        )

    return result
