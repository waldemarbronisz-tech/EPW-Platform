"""The status bar tells the person at the cabinet whether the logic is
running, and the Project menu lets an Engineer put a corrected program
into the scan without restarting the controller.

Real widgets, driven the way a person drives them - the indicator is
refreshed by the same method its own timer calls, and the menu action is
triggered rather than its handler called by hand.
"""
import pytest
from PySide6.QtWidgets import QMessageBox

from epw_os.core.access_manager import AccessLevel
from gui_smoke._mocks import (MockCommandManager, MockControllableAccessManager, MockProjectManager,
                              MockTagManager)


class FakeLogicEngine:
    """Stands in for LogicEngine with whatever status a test needs - the
    indicator only ever reads get_status()."""

    def __init__(self, **status):
        self.status = {"configured": True, "loaded": True, "running": True, "block_count": 3,
                       "cycle_time_ms": 100, "scan_count": 42, "last_scan_ms": 1.25, "max_scan_ms": 3.5,
                       "driven_outputs": ["ADA1.DO.1"], "last_error": ""}
        self.status.update(status)

    def get_status(self):
        return dict(self.status)


def _window(make_window, engine=None, reload_callback=None):
    """MockControllableAccessManager, not the always-deny one: the reload
    entry is Engineer-gated, so a test about it needs a real grant/deny
    distinction."""
    return make_window(MockTagManager(), MockCommandManager(), MockControllableAccessManager(),
                       MockProjectManager(), logic_engine=engine, logic_reload_callback=reload_callback)


# --- the indicator -----------------------------------------------------------

def test_a_running_scan_reads_run_and_says_how_fast_in_the_tooltip(make_window):
    win = _window(make_window, FakeLogicEngine())

    assert "RUN" in win.lbl_sb_logic.text()
    tooltip = win.lbl_sb_logic.toolTip()
    assert "100 ms" in tooltip and "42 scans" in tooltip and "3 block" in tooltip


def test_a_refused_program_reads_fault_and_carries_the_reason(make_window):
    win = _window(make_window, FakeLogicEngine(loaded=False, running=False,
                                               last_error="checksum does not match"))

    assert "FAULT" in win.lbl_sb_logic.text()
    assert "checksum does not match" in win.lbl_sb_logic.toolTip()


def test_a_loaded_but_stopped_program_is_not_shown_as_healthy(make_window):
    win = _window(make_window, FakeLogicEngine(running=False))

    assert "STOPPED" in win.lbl_sb_logic.text()
    assert "not being evaluated" in win.lbl_sb_logic.toolTip()


def test_a_controller_with_no_logic_says_so_rather_than_looking_broken(make_window):
    win = _window(make_window, FakeLogicEngine(configured=False, loaded=False, running=False))

    assert "none" in win.lbl_sb_logic.text()
    assert "FAULT" not in win.lbl_sb_logic.text()


def test_the_indicator_follows_the_engine_when_it_is_refreshed(make_window):
    engine = FakeLogicEngine()
    win = _window(make_window, engine)
    assert "RUN" in win.lbl_sb_logic.text()

    engine.status.update(running=False, loaded=False, last_error="unknown block type")
    win._refresh_logic_indicator()  # what its own timer calls

    assert "FAULT" in win.lbl_sb_logic.text()


# --- reloading from the Project menu -----------------------------------------

def _become_engineer(win):
    """The way the app itself raises the level: the access manager emits
    level_changed, and every Engineer-gated action re-checks. Setting the
    attribute alone would leave the menu entry disabled, and a disabled
    QAction ignores trigger() - which is exactly what the app does too."""
    win.access_manager.level = AccessLevel.ENGINEER
    win.access_manager.level_changed.emit(AccessLevel.ENGINEER)


def _project_menu_action(win, text_fragment):
    for action in win.menuBar().actions():
        menu = action.menu()
        if menu is None:
            continue
        for entry in menu.actions():
            if text_fragment in entry.text():
                return entry
    return None


def test_the_reload_entry_is_engineer_only(make_window):
    win = _window(make_window, FakeLogicEngine(), reload_callback=lambda **kw: {"success": True, "status": {}})
    entry = _project_menu_action(win, "Reload logic program")
    assert entry is not None

    win.access_manager.level = AccessLevel.OPERATOR
    win._refresh_reload_logic_action_visibility()
    assert entry.isVisible() is False and entry.isEnabled() is False

    win.access_manager.level = AccessLevel.ENGINEER
    win._refresh_reload_logic_action_visibility()
    assert entry.isVisible() is True and entry.isEnabled() is True


def test_confirming_the_reload_calls_the_controller_and_reports_back(make_window, monkeypatch):
    calls = []
    engine = FakeLogicEngine()

    def reload_callback(actor="", level=None):
        calls.append(actor)
        engine.status.update(block_count=7, cycle_time_ms=50)
        return {"success": True, "reason": "", "status": engine.get_status()}

    win = _window(make_window, engine, reload_callback=reload_callback)
    _become_engineer(win)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    shown = []
    monkeypatch.setattr(QMessageBox, "information", lambda parent, title, text, *a, **k: shown.append(text))

    _project_menu_action(win, "Reload logic program").trigger()

    assert len(calls) == 1 and "Engineer" in calls[0]
    assert "7 block" in shown[0] and "50 ms" in shown[0]


def test_declining_the_confirmation_changes_nothing(make_window, monkeypatch):
    calls = []
    win = _window(make_window, FakeLogicEngine(),
                  reload_callback=lambda **kw: calls.append(kw) or {"success": True, "status": {}})
    _become_engineer(win)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.No)

    _project_menu_action(win, "Reload logic program").trigger()

    assert calls == []


def test_a_failed_reload_is_reported_as_a_warning_with_its_reason(make_window, monkeypatch):
    win = _window(make_window, FakeLogicEngine(),
                  reload_callback=lambda **kw: {"success": False, "reason": "the checksum does not match",
                                                "status": {}})
    _become_engineer(win)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    warned = []
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text, *a, **k: warned.append(text))

    _project_menu_action(win, "Reload logic program").trigger()

    assert warned and "the checksum does not match" in warned[0]
