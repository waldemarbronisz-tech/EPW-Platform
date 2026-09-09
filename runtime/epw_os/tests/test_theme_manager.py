"""Tests for the ThemeManager's work-mode logic (epw_os/gui/theme_manager.py,
Task 4, page-split branch: MOTYW STALY vs AUTOMATYCZNY DZIEN/NOC). A
QObject with a Signal, same "needs a QApplication, no other Qt behavior
to speak of" situation test_core.py's own test_synoptic_loader() already
handles - same pattern followed here.

window_state's persistence path is redirected to a per-test tmp file
(monkeypatched _STATE_PATH) - this module intentionally never touches
the real machine-local window_state.local.json (memory: "verification
scripts must not touch real config files")."""
import datetime as dt
import sys

import pytest
from PySide6.QtWidgets import QApplication

if not QApplication.instance():
    QApplication(sys.argv)

from epw_os.gui import window_state
from epw_os.gui import theme_manager as theme_manager_module
from epw_os.gui.theme_manager import THEME_MODE_CONSTANT, THEME_MODE_AUTO

# Task (refactor/test-suite-split): every test in this module needs the
# module-level QApplication above - marked so `pytest epw_os/tests/
# -m "not slow"` can skip the whole file.
pytestmark = [pytest.mark.slow, pytest.mark.gui]


class FakeTagManager:
    """Minimal stand-in with a real tag_changed-shaped callback list -
    enough for ThemeManager.bind_tag_manager()/update_tag() without a
    real (Qt-dependent) TagManager."""
    def __init__(self):
        self._subs = []

    class _Signal:
        def __init__(self, subs):
            self._subs = subs

        def connect(self, cb):
            self._subs.append(cb)

    @property
    def tag_changed(self):
        return FakeTagManager._Signal(self._subs)

    def update_tag(self, name, value, quality=None):
        for cb in list(self._subs):
            cb(name, value, "GOOD")


@pytest.fixture
def mgr(tmp_path, monkeypatch):
    monkeypatch.setattr(window_state, "_STATE_PATH", str(tmp_path / "window_state.local.json"))
    theme_manager_module.reset_theme_manager_for_tests()
    m = theme_manager_module.get_theme_manager()
    yield m
    theme_manager_module.reset_theme_manager_for_tests()


def _window_covering_now(minutes_span=1):
    """Returns (start, end) HH:MM strings such that "now" falls inside
    [start, end)."""
    now = dt.datetime.now()
    end = (now + dt.timedelta(minutes=minutes_span)).strftime("%H:%M")
    return now.strftime("%H:%M"), end


def test_default_mode_is_constant_no_migration(mgr):
    """GRANICE: an old (or brand-new) persisted state with no
    "theme_mode" section behaves exactly like today - MOTYW STALY,
    index 0 (Industrial)."""
    assert mgr.get_mode() == THEME_MODE_CONSTANT
    assert mgr.current_index() == 0


def test_auto_mode_applies_the_night_theme_during_the_night_window(mgr):
    now_hhmm, later = _window_covering_now()
    mgr.set_mode(THEME_MODE_AUTO, day_index=0, night_index=1, day_start=later, night_start=now_hhmm)
    assert mgr.get_mode() == THEME_MODE_AUTO
    assert mgr.current_index() == 1


def test_auto_mode_applies_the_day_theme_during_the_day_window(mgr):
    now_hhmm, later = _window_covering_now()
    mgr.set_mode(THEME_MODE_AUTO, day_index=0, night_index=1, day_start=now_hhmm, night_start=later)
    assert mgr.current_index() == 0


def test_a_real_external_tag_write_sets_the_logic_override(mgr):
    ftm = FakeTagManager()
    mgr.bind_tag_manager(ftm)
    assert mgr.is_logic_override_active() is False
    ftm.update_tag("System.Theme", 2, "GOOD")
    assert mgr.current_index() == 2
    assert mgr.is_logic_override_active() is True


def test_menu_pick_via_apply_index_never_sets_the_override(mgr):
    """apply_index() is the plain "zmiana z menu: dowolny poziom" path -
    never counts as a logic-driven write, even though it also ends up
    pushing a (now-matching) value back through tag_changed once bound."""
    ftm = FakeTagManager()
    mgr.bind_tag_manager(ftm)
    mgr.apply_index(3)
    assert mgr.current_index() == 3
    assert mgr.is_logic_override_active() is False


def test_logic_override_suppresses_automatic_switching(mgr):
    now_hhmm, later = _window_covering_now()
    mgr.set_mode(THEME_MODE_AUTO, day_index=0, night_index=1, day_start=now_hhmm, night_start=later)
    assert mgr.current_index() == 0  # day theme, per the window above

    ftm = FakeTagManager()
    mgr.bind_tag_manager(ftm)
    ftm.update_tag("System.Theme", 4, "GOOD")
    assert mgr.current_index() == 4
    assert mgr.is_logic_override_active() is True

    mgr._check_auto_switch()  # would normally re-apply the day theme (0)
    assert mgr.current_index() == 4, "an active logic override must take priority over auto-switching"


def test_set_mode_clears_the_override_task_s_own_next_mode_change_rule(mgr):
    now_hhmm, later = _window_covering_now()
    ftm = FakeTagManager()
    mgr.bind_tag_manager(ftm)
    ftm.update_tag("System.Theme", 2, "GOOD")
    assert mgr.is_logic_override_active() is True

    mgr.set_mode(THEME_MODE_AUTO, day_index=0, night_index=1, day_start=now_hhmm, night_start=later)
    assert mgr.is_logic_override_active() is False
    assert mgr.current_index() == 0  # re-applies the correct auto theme immediately


def test_set_mode_back_to_constant_applies_the_chosen_theme(mgr):
    now_hhmm, later = _window_covering_now()
    mgr.set_mode(THEME_MODE_AUTO, day_index=0, night_index=1, day_start=now_hhmm, night_start=later)
    mgr.set_mode(THEME_MODE_CONSTANT, constant_index=3)
    assert mgr.get_mode() == THEME_MODE_CONSTANT
    assert mgr.current_index() == 3


def test_mode_and_schedule_persist_across_a_fresh_instance(tmp_path, monkeypatch):
    monkeypatch.setattr(window_state, "_STATE_PATH", str(tmp_path / "window_state.local.json"))
    theme_manager_module.reset_theme_manager_for_tests()
    m1 = theme_manager_module.get_theme_manager()
    now_hhmm, later = _window_covering_now()
    m1.set_mode(THEME_MODE_AUTO, day_index=3, night_index=4, day_start=now_hhmm, night_start=later)

    theme_manager_module.reset_theme_manager_for_tests()
    m2 = theme_manager_module.get_theme_manager()
    assert m2.get_mode() == THEME_MODE_AUTO
    assert m2.get_day_index() == 3
    assert m2.get_night_index() == 4
    assert m2.get_day_start() == now_hhmm
    assert m2.get_night_start() == later
    theme_manager_module.reset_theme_manager_for_tests()


def test_invalid_mode_is_ignored(mgr):
    mgr.set_mode("not_a_real_mode", constant_index=2)
    assert mgr.get_mode() == THEME_MODE_CONSTANT  # unchanged


def test_overnight_window_wrapping_midnight(mgr):
    """A day window that wraps past midnight (day_start > night_start,
    e.g. a night-shift-only site) still resolves correctly - "day" is
    whatever ISN'T inside [night_start, day_start)."""
    mgr.set_mode(THEME_MODE_AUTO, day_index=0, night_index=1, day_start="22:00", night_start="02:00")
    # "now" is real wall-clock time, so just check internal consistency:
    # exactly one of day/night should be considered active, and it must
    # match the currently-applied index.
    is_day = mgr._is_daytime()
    expected = mgr.get_day_index() if is_day else mgr.get_night_index()
    assert mgr.current_index() == expected
