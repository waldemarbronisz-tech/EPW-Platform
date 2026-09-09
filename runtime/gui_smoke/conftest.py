"""Shared fixtures for the gui_smoke/ package (refactor/test-suite-split
task).

Root-cause of the old test_gui_smoke.py's progressive slowdown (task
section 2), found directly in that file's own comments/code rather than
guessed at:

  1. The whole ~2676-line script ran as ONE Python process against ONE
     shared QApplication, top to bottom, inside a single `try:` block -
     there was no function boundary where a fixture could tear anything
     down between logical sections (only comment dividers).
  2. Every MainWindow built along the way WAS mostly paired with an
     explicit `.shutdown_gui()` call somewhere later in the script (good
     discipline) and PageEntryGate's own 250ms sim_timer was stopped
     immediately via `_stop_sim_timer()` right after construction (also
     already done almost everywhere) - so the sim_timer/window-leak
     hypothesis, while a real and worth-fixing hazard, was not the
     dominant cost.
  3. The dominant, self-documented cost: dozens of modal dialogs/popups
     across the script (ProjectPropertiesDialog, ThemeDialog,
     PinPromptPopup, ChangePinDialog, ConfirmationPopup,
     ForceOutputConfirmPopup, AboutDialog, HistorianExportDialog,
     PresentationDialog, and ~15 individual page objects built directly
     in the old Polish-translation sweep) were only ever `.deleteLater()`'d
     - which just SCHEDULES destruction on the next Qt event-loop pump,
     and does nothing at all if nothing pumps the event loop again before
     the next one is constructed. `app.processEvents()` was only called a
     handful of times in the whole script, so Qt's live object graph
     (every QApplication.topLevelWidgets() entry, every installed event
     filter) grew monotonically for the ENTIRE run and was never pruned
     until interpreter exit. The PIN-dialog test block even has to work
     around this directly in its own comment: "QApplication.topLevelWidgets()
     also returns every never-shown PinPromptPopup instance still alive
     from earlier in this script" - i.e. this was already observed,
     in-code, as a real accumulation, just never connected to the
     run-to-run timing variance.

Splitting into separate pytest functions fixes this structurally: every
test function here gets this module's own autouse `_pump_qt_events_after_test`
fixture, which flushes the Qt event loop (actually reclaiming every
`deleteLater()`'d object the test just constructed) before the next test
starts, and the `make_window` fixture guarantees `shutdown_gui()` +
`_stop_sim_timer()` for every MainWindow a test builds, even ones a test
forgets to shut down itself - so nothing accumulates across a whole file
the way it used to accumulate across the whole old script.

Deliberately NOT placed under epw_os/tests/: that directory's own
conftest.py used to have an autouse fixture that ran a full Alembic
migration pass before EVERY test collected anywhere under it,
regardless of whether that test touched the database - see
refactor/test-db-fixture's own SESSION_REPORT.md; it's since been
replaced with an explicit, opt-in `db` fixture there. Nearly everything
in gui_smoke/ still needs no database at all (this package still isn't
placed under epw_os/tests/, so it stays outside that directory's own
migrate-once-per-session bookkeeping) - the only exception is the
handful of tests in test_retention.py that pass a REAL Historian/
AuditLogger into MainWindow, which use the `real_db` fixture below.
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("EPW_TESTING", "1")

import pytest
from PySide6.QtWidgets import QApplication

from epw_os.gui import window_state as _ws_module


def pytest_collection_modifyitems(config, items):
    # Every test in this package constructs at least a QApplication-backed
    # mock and usually a full MainWindow - "slow" and "gui" in the sense
    # Task 4 asks for (no test here is a candidate for the fast, dozen-
    # seconds, no-interface-construction slice of the suite).
    for item in items:
        item.add_marker(pytest.mark.slow)
        item.add_marker(pytest.mark.gui)


@pytest.fixture
def real_db():
    """Opt-in, for the handful of tests (test_retention.py) that pass a
    REAL, headless Historian/AuditLogger into MainWindow - unlike every
    other gui_smoke test, those actually touch the database (both
    directly, and pre-existing production code does too: PageTrends
    unconditionally calls historian.get_distinct_tag_names() at
    construction whenever historian is not None).

    Task (feature/retention-and-test-fix, Part A): epw_os/tests/ installs
    a GLOBAL guard on the real, process-wide SQLAlchemy engine that
    raises for any unrequested DB connection - global because it's a
    `sqlalchemy.event.listens_for(engine.pool, "checkout")` listener, not
    scoped to that directory. When gui_smoke/ is collected together with
    epw_os/tests/ in the same pytest session (as CI, and this file's own
    DOWÓD verification, both do), that guard is active for THIS
    package's tests too. This fixture participates in that SAME shared
    mechanism (epw_os/tests/_db_guard.py - imported here by its own real
    dotted name, NOT via `epw_os.tests.conftest`, which has no
    guaranteed dotted name of its own and would silently create a
    second, independent copy of the guard instead of sharing the real
    one - see that module's own docstring for exactly how this was
    found: a real combined-run failure, not anticipated in advance)."""
    from epw_os.tests import _db_guard
    _db_guard.activate()
    try:
        _db_guard.ensure_migrated_and_clean()
        yield
    finally:
        _db_guard.deactivate()


@pytest.fixture(scope="session")
def qapp():
    """One QApplication for the whole gui_smoke/ session - matching the
    old script's own reasoning (a real QApplication is a genuine
    process-wide singleton; constructing more than one is not what's
    being fixed here) while every actual GUI OBJECT still gets its own
    per-test construction and teardown below."""
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture(autouse=True)
def _isolated_window_state(tmp_path, qapp):
    """Redirect ALL window_state.local.json reads/writes to a fresh
    per-TEST temp file - every MainWindow construction touches this file
    (window geometry, on-screen keyboard enabled/geometry, screen sleep
    minutes), and this project's own established convention is that
    verification scripts must never touch real config/project files (see
    MEMORY.md). This is a per-test redirect (stronger than the old
    script's single whole-run redirect - it also means one test's saved
    state, e.g. the theme-persistence tests, can never leak into a
    DIFFERENT test that happens to run after it)."""
    orig = _ws_module._STATE_PATH
    _ws_module._STATE_PATH = str(tmp_path / "window_state.local.json")
    try:
        yield
    finally:
        _ws_module._STATE_PATH = orig


@pytest.fixture(autouse=True)
def _pump_qt_events_after_test(qapp):
    """The actual fix for the progressive-slowdown root cause described
    at the top of this file: flush the Qt event loop after every single
    test, so every `.deleteLater()` a test issued (dialogs, popups, pages)
    is actually reclaimed before the next test starts, instead of piling
    up for the rest of the run the way it did in the old single-process
    script.

    Task (feature/retention-and-test-fix, Part A): this used to ALSO
    force a `gc.collect()` here, every single test. Two independent
    findings say that call - not `processEvents()` - was the real
    problem, not the fix:
      1. It is the exact frame two different native crashes captured
         when running gui_smoke/ combined with epw_os/tests/ at full
         scale (`gc.collect()` walks the ENTIRE Python heap, not just
         Qt objects - a forced full collection is where a PySide6/
         shiboken C++ object whose Python wrapper is momentarily in an
         inconsistent state, mid-teardown, actually gets touched).
      2. `gc.collect()`'s own cost scales with total LIVE OBJECT COUNT
         in the whole process, not just this package's own churn -
         once combined with epw_os/tests/'s own 500+ tests in the same
         process, every one of these calls got measurably slower as the
         run went on, which is the exact "progressive slowdown"
         symptom this fixture was written to fix in the first place,
         just from a different mechanism (whole-process heap size,
         not Qt windows/timers left running).
    `processEvents()` alone is what actually reclaims a
    `.deleteLater()`'d Qt object (Qt's own deferred-deletion queue, a
    completely different mechanism from Python's cyclic garbage
    collector) - it was always the operative half of this fixture; see
    SESSION_REPORT.md for the timing comparison with and without
    `gc.collect()`."""
    yield
    qapp.processEvents()
    qapp.processEvents()


def _stop_sim_timer(win):
    """PageEntryGate's 250ms sim_timer has no parent-triggered cleanup
    path - left running, it fires (and throws a mock tag manager's
    known-harmless missing-update_tag AttributeError) for as long as the
    window object stays alive. Purely a test-speed/noise fix - nothing
    under test depends on the simulation actually running."""
    try:
        win.page_entry_gate.sim_timer.stop()
    except AttributeError:
        pass


@pytest.fixture
def make_window(qapp):
    """Returns a factory that constructs a MainWindow, stops its
    simulation timer, and guarantees shutdown_gui() runs at the end of
    the test even if the test itself never calls it - the direct fix for
    Task 2's "MainWindow instances never stopped" suspect. A test may
    still call win.shutdown_gui() itself early (several original checks
    depend on shutting one down mid-test to build another); shutdown_gui()
    is explicitly documented as idempotent, so the fixture's own call
    after a test-initiated one is a safe no-op."""
    from epw_os.gui.main_window import MainWindow

    built = []

    def _make(*args, **kwargs):
        win = MainWindow(*args, **kwargs)
        _stop_sim_timer(win)
        built.append(win)
        return win

    yield _make

    for win in built:
        win.shutdown_gui()
    qapp.processEvents()


@pytest.fixture
def stop_sim_timer():
    """Exposes the helper above directly, for the handful of tests that
    construct a MainWindow through some path other than `make_window`
    (e.g. one built and reassigned mid-test to a new instance)."""
    return _stop_sim_timer
