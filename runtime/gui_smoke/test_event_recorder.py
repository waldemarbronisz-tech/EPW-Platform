"""Event Recorder's row cap: an acceptance-review finding fixed in an
earlier task - the table used to grow one row per event forever (no
cap), which on this app's own deployment target (Orange Pi, unattended
for weeks/months - see ORANGE_PI_DEPLOYMENT.md) is unbounded memory
growth, and every new row also re-sorted/re-filtered the ENTIRE table.
Fixed with a fixed-size cap, oldest row evicted first.

Split out on its own (refactor/test-suite-split task) rather than folded
into test_i18n.py, where it happened to sit textually in the old script
only because it reused that section's _PageMockTM - it isn't a
translation check.
"""
from gui_smoke._mocks import PageMockTagManager


def test_event_recorder_caps_rows_oldest_evicted_first():
    import epw_os.gui.pages.page_event_recorder as per_module
    from epw_os.gui.logger import ui_logger

    # Exercises the SAME code path as production (on_log_event() reads
    # MAX_EVENT_ROWS from this module's own globals at call time, not a
    # value captured at import time), just with a small cap instead of
    # the real 5000 - proving eviction with ~30 events instead of
    # ~5000+ avoids flooding every OTHER PageEventRecorder connected to
    # the same ui_logger singleton (which, in the old single-process
    # script, made a full-scale run of this check alone take several
    # minutes - moot here, since this file's own PageEventRecorder is
    # the only one alive in this test's process).
    real_max = per_module.MAX_EVENT_ROWS
    per_module.MAX_EVENT_ROWS = 20
    try:
        per = per_module.PageEventRecorder(PageMockTagManager())
        extra = 5
        for i in range(per_module.MAX_EVENT_ROWS + extra):
            ui_logger.log("INFO", "SYSTEM", "SmokeTest", f"probe-{i}", "SYSTEM", "SIMULATION MODE", "")
        assert per.table.rowCount() == 20, per.table.rowCount()
        assert per.total_events == 20 + extra, per.total_events  # lifetime counter stays uncapped

        all_events_shown = {per.table.item(r, 4).text() for r in range(per.table.rowCount())}
        for i in range(extra):
            assert f"probe-{i}" not in all_events_shown, f"probe-{i} should have been evicted (oldest)"
        assert f"probe-{20 + extra - 1}" in all_events_shown, "the newest probe must never be evicted"
    finally:
        per_module.MAX_EVENT_ROWS = real_max
