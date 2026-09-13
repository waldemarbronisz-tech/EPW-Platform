"""Studio's Synoptic toolbar shows the active drawing mode: the tool,
medium, wire style and routing buttons are ticked from Synoptic's state
bridge (user request: highlight electricity / water while drawing)."""
from types import SimpleNamespace

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication

from studio.shell.main_window import StudioMainWindow

KEYS = ["wire", "frame", "building", "medium:ELECTRICAL", "medium:WATER", "medium:VENTILATION",
        "style:NORMAL", "style:BUS", "routing:STRAIGHT", "routing:AVOID"]


def _actions():
    QApplication.instance() or QApplication([])
    actions = {}
    for key in KEYS:
        action = QAction(key)
        action.setCheckable(True)
        actions[key] = action
    return actions


def _ticked(actions):
    return sorted(k for k, a in actions.items() if a.isChecked())


def test_active_tool_medium_style_and_routing_are_ticked():
    actions = _actions()
    fake = SimpleNamespace(synoptic_mode_actions=actions)
    StudioMainWindow._apply_synoptic_mode_checks(fake, {
        "drawingWire": True, "drawingFrame": None, "drawingMedium": "WATER",
        "drawingStyle": "BUS", "wireRoutingMode": "AVOID",
    })
    assert _ticked(actions) == ["medium:WATER", "routing:AVOID", "style:BUS", "wire"]

    StudioMainWindow._apply_synoptic_mode_checks(fake, {
        "drawingWire": False, "drawingFrame": "BUILDING", "drawingMedium": "ELECTRICAL",
        "drawingStyle": "NORMAL", "wireRoutingMode": "STRAIGHT",
    })
    assert _ticked(actions) == ["building", "medium:ELECTRICAL", "routing:STRAIGHT", "style:NORMAL"]
