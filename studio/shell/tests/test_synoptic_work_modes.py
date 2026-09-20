"""Studio's Synoptic toolbar carries the editor's work modes: a switch of
four mutually exclusive modes (Ctrl+1..4) and, beside it, only the tools of
the active mode - ticked and shown from Synoptic's state bridge."""
import os
import tempfile
from types import SimpleNamespace

from PySide6.QtCore import QSettings
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QToolBar

from studio.shell import menus
from studio.shell.main_window import StudioMainWindow


def _app():
    return QApplication.instance() or QApplication([])


class _FakePanel:
    def __init__(self):
        self.commands = []

    def trigger_command(self, command):
        self.commands.append(command)

    def trigger_menu_item(self, text, exact=False):
        self.commands.append(f"menu:{text}")

    def trigger_toolbar_button(self, title, exact=True):
        self.commands.append(f"title:{title}")


def _build():
    _app()
    window = StudioMainWindow(settings=QSettings(os.path.join(tempfile.mkdtemp(), "s.ini"), QSettings.IniFormat))
    toolbar = QToolBar()
    panel = _FakePanel()
    menus.build_synoptic_context_toolbar(toolbar, panel, window)
    return window, toolbar, panel


def _visible_labels(window, mode):
    return [a.text() for a in window.synoptic_mode_groups[mode] if a.isVisible() and not a.isSeparator()]


def test_four_exclusive_modes_with_ctrl_digit_shortcuts():
    window, _toolbar, _panel = _build()
    mode_actions = [window.synoptic_mode_actions[f"mode:{m}"] for m in menus.SYNOPTIC_WORK_MODES]
    assert [a.text() for a in mode_actions] == ["Symbols", "Rooms", "Connections", "Annotations"]
    assert [a.shortcut().toString() for a in mode_actions] == ["Ctrl+1", "Ctrl+2", "Ctrl+3", "Ctrl+4"]
    assert all(a.isCheckable() for a in mode_actions)
    group = mode_actions[0].actionGroup()
    assert group is not None and group.isExclusive()
    assert all(a.actionGroup() is group for a in mode_actions)


def test_clicking_a_mode_or_a_tool_sends_its_stable_command():
    window, _toolbar, panel = _build()
    window.synoptic_mode_actions["mode:ROOMS"].trigger()
    window.synoptic_mode_actions["wall"].trigger()
    window.synoptic_mode_actions["medium:WATER"].trigger()
    assert panel.commands == ["mode:ROOMS", "draw_wall", "medium:WATER"]


def test_only_the_active_modes_tools_are_shown_each_group_with_separators():
    window, _toolbar, _panel = _build()
    assert _visible_labels(window, "SYMBOLS")
    assert _visible_labels(window, "ROOMS") == []
    StudioMainWindow._apply_synoptic_mode_checks(window, {"workMode": "ROOMS"})
    assert _visible_labels(window, "SYMBOLS") == []
    # Rotation rides along with the room tools (owner, 2026-09-20):
    # a door or a luminaire is turned while the plan is drawn.
    assert _visible_labels(window, "ROOMS") == [
        "Draw wall", "Draw room (rectangle)", "Draw Frame", "Draw Building",
        "Rotate Left", "Rotate Right",
    ]
    assert sum(1 for a in window.synoptic_mode_groups["CONNECTIONS"] if a.isSeparator()) == 4
    StudioMainWindow._apply_synoptic_mode_checks(window, {"workMode": "CONNECTIONS"})
    assert "Draw Wire" in _visible_labels(window, "CONNECTIONS")
    assert _visible_labels(window, "ROOMS") == []


def test_the_active_mode_and_the_armed_tool_are_ticked():
    window, _toolbar, _panel = _build()
    StudioMainWindow._apply_synoptic_mode_checks(window, {
        "workMode": "ROOMS", "drawingWallTool": True, "drawingRoomTool": False,
        "drawingWire": False, "drawingFrame": None,
        "drawingMedium": "ELECTRICAL", "drawingStyle": "NORMAL", "wireRoutingMode": "AVOID",
    })
    ticked = sorted(k for k, a in window.synoptic_mode_actions.items() if a.isChecked())
    assert ticked == ["medium:ELECTRICAL", "mode:ROOMS", "routing:AVOID", "style:NORMAL", "wall"]


def test_an_action_from_a_rebuilt_toolbar_is_skipped_not_fatal():
    _app()
    dead = QAction("x")
    fake = SimpleNamespace(synoptic_mode_actions={"mode:ROOMS": dead}, synoptic_mode_groups={"ROOMS": [dead]})
    del dead
    StudioMainWindow._apply_synoptic_mode_checks(fake, {"workMode": "ROOMS"})
