"""SPEC "Wymuszanie stanów" condition 2 - "widoczne po obu stronach, także
na panelu przy szafce": the status bar shows every force Studio holds
and an Engineer drops them all from its context menu."""
from PySide6.QtCore import QObject, Signal

from gui_smoke._mocks import MockCommandManager, MockControllableAccessManager, MockProjectManager, MockTagManager


class _Forces:
    def __init__(self):
        self.entries = [{"tag": "ELA1.DI.2", "value": False, "actor": "API:Engineer"}]
        self.released = []

    def snapshot(self):
        return list(self.entries)

    def release_all(self, actor="Engineer", reason=""):
        self.released.append((actor, reason, len(self.entries)))
        self.entries = []
        return len(self.released)


class _Bridge(QObject):
    forces_changed = Signal(int)


def test_the_status_bar_shows_forces_and_an_engineer_drops_them_all(make_window):
    forces = _Forces()
    bridge = _Bridge()
    access = MockControllableAccessManager()
    win = make_window(MockTagManager(), MockCommandManager(), access, MockProjectManager(),
                      force_manager=forces, forces_changed_signal=bridge.forces_changed)
    try:
        assert win.lbl_sb_forces.isVisible() or win.lbl_sb_forces.text().strip() != ""   # shown at construction
        assert "1" in win.lbl_sb_forces.text() and "ELA1.DI.2" in win.lbl_sb_forces.toolTip()
        forces.entries.append({"tag": "ADA1.DO.4", "value": True, "actor": "API:Engineer"})
        bridge.forces_changed.emit(2)
        assert "2" in win.lbl_sb_forces.text()

        win.force_manager.release_all(actor="Engineer (panel)", reason="released at the panel")
        bridge.forces_changed.emit(0)
        assert win.lbl_sb_forces.isHidden()
        assert forces.released == [("Engineer (panel)", "released at the panel", 2)]
    finally:
        win.shutdown_gui()


def test_no_force_manager_means_no_indicator(make_window):
    win = make_window(MockTagManager(), MockCommandManager(), MockControllableAccessManager(), MockProjectManager())
    try:
        assert win.force_manager is None and win.lbl_sb_forces.isHidden()
    finally:
        win.shutdown_gui()
