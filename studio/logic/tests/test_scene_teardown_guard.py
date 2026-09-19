"""A scene being destroyed emits selectionChanged one last time.

Destroying a QGraphicsScene clears its items, and clearing items changes
the selection - so every slot connected to selectionChanged runs once
more AFTER shiboken has invalidated the Python wrapper. Each handler that
touched the scene then raised "Internal C++ object (LogicScene) already
deleted": one stack trace per handler, on every teardown, for work that
could not possibly matter any more. Qt's auto-disconnect does not help,
because the emission happens before it.

HOW TO SEE THIS FAIL: remove the `is_alive(self.scene)` guard from
MainWindow._on_selection_changed() and run this file - the first test
below fails with that exact RuntimeError.
"""
import gc

import pytest
import shiboken6
from PySide6.QtWidgets import QApplication

from shared.logic.blocks import register_builtin_blocks
from logic_studio.ui.qt_lifetime import is_alive

register_builtin_blocks()


def _app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(qsettings):
    from logic_studio.ui.main_window import MainWindow
    _app()
    return MainWindow(settings=qsettings)


def test_is_alive_reports_a_destroyed_object(window):
    from PySide6.QtWidgets import QGraphicsScene
    scene = QGraphicsScene()
    assert is_alive(scene) is True
    shiboken6.delete(scene)
    assert is_alive(scene) is False
    # Several objects: any one gone is enough.
    assert is_alive(window, scene) is False


@pytest.mark.parametrize("handler", [
    "_on_selection_changed",
    "_update_clipboard_actions",
    "_update_block_toggle_actions",
    "_highlight_selection_in_signals_panel",
])
def test_every_selection_handler_survives_a_destroyed_scene(window, handler):
    shiboken6.delete(window.scene)
    getattr(window, handler)()          # must not raise


def test_the_format_toolbar_survives_it_too(window):
    shiboken6.delete(window.scene)
    assert window.format_toolbar.selected_doc_blocks() == []
    window.format_toolbar.refresh()     # must not raise


def test_a_live_scene_is_still_read_normally(window):
    """The guard must not turn every handler into a no-op: with a real
    scene and a real block selected, the panel still follows it."""
    from logic_studio.ui.canvas.block_item import BlockItem
    window.scene.add_block_from_library("logic.and", 0, 0)
    block_item = next(i for i in window.scene.items() if isinstance(i, BlockItem))
    block_item.setSelected(True)

    window._on_selection_changed()

    assert "Selected:" in window.lbl_selected.text()
    assert window.lbl_selected.text() != "Selected: None"
    assert window.act_copy.isEnabled() is True


def test_dropping_a_window_leaves_no_complaint_behind(qsettings, capsys):
    """The whole point, end to end: build a window, let it go, and pump
    Qt's own deletion queue - nothing may be written to stderr."""
    from logic_studio.ui.main_window import MainWindow
    app = _app()
    doomed = MainWindow(settings=qsettings)
    doomed.scene.add_block_from_library("logic.and", 0, 0)
    from logic_studio.ui.canvas.block_item import BlockItem
    next(i for i in doomed.scene.items() if isinstance(i, BlockItem)).setSelected(True)
    # Deliberately NOT close(): a dirty project makes closeEvent() put up
    # the save prompt, and a modal in a test hangs forever. What is under
    # test is Qt DESTROYING the scene, which deleteLater() below does.
    doomed.deleteLater()
    del doomed
    gc.collect()
    app.processEvents()

    assert "already deleted" not in capsys.readouterr().err
