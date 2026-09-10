"""EPW Studio: jedna szata graficzna, Stage 2 - regression test for the
window()-resolution bug found while building the shared toolbar.

MainWindow used to locate itself, from deep inside the canvas or a side
panel, via Qt's own `<some_widget>.window()` - which returns the nearest
ancestor for which isWindow() is True. That works fine standalone, but
studio/shell/logic_panel.py embeds MainWindow as a plain CHILD widget
(exactly what this test's _embed_like_the_shell_does() reproduces) -
once MainWindow has a real parent, Qt says it is no longer a window, so
`.window()` kept climbing past it to whatever real top-level window
happens to contain it. In the real shell that is EPW Studio's own
StudioMainWindow, which has none of `.project`/`.engine`/`.scene`/
`.view`/`.set_dirty()` - so every call site silently missed.

Fixed by logic_studio/ui/window_lookup.py's logic_main_window(widget):
walks widget.parentWidget() by hand (never touches Qt's own window()/
isWindow()) looking for the nearest real MainWindow ancestor - found
correctly regardless of whether MainWindow itself is a real top-level
window or an embedded child, because the search is by TYPE, not by
Qt's "window" bookkeeping.

This test would have failed before that fix (add_block_from_library()
would have silently produced an empty undo_stack and is_dirty=False,
exactly as this task's Stage 2 report's own probe script demonstrated
against the real shell) and must keep passing after it.
"""
from PySide6.QtWidgets import QStackedWidget, QWidget

from logic_studio.blocks import register_builtin_blocks
from logic_studio.blocks.registry import BlockRegistry
from logic_studio.ui.main_window import MainWindow
from logic_studio.ui.panels.library import TYPE_ID_ROLE

register_builtin_blocks()


def _embed_like_the_shell_does(main_window):
    """Reproduces studio/shell/logic_panel.py's own embedding exactly:
    MainWindow added to a QStackedWidget's page via addWidget() - the
    same mechanism that made MainWindow.isWindow() False in the real
    shell. No StudioMainWindow import here on purpose (studio/ and
    studio/logic/'s own test suite are separate deployable units - this
    reproduces the SHAPE of the embedding, an embedded MainWindow with
    no `.project`/`.engine`/etc. of its own, without depending on
    studio/shell/ at all)."""
    host = QWidget()
    stack = QStackedWidget(host)
    stack.addWidget(main_window)
    assert main_window.isWindow() is False, (
        "test setup didn't actually reproduce the embedding - MainWindow "
        "is still its own top-level window, so this test would prove "
        "nothing"
    )
    return host


def test_add_block_from_library_updates_undo_and_dirty_when_embedded(qsettings, qapp):
    mw = MainWindow(settings=qsettings)
    _host = _embed_like_the_shell_does(mw)  # noqa: F841 - keeps stack/host alive

    assert len(mw.project.undo_stack) == 0
    assert mw.is_dirty is False

    category = BlockRegistry.get_categories()[0]
    block_type = BlockRegistry.get_blocks_in_category(category)[0]
    mw.scene.add_block_from_library(block_type, 200, 200)

    assert len(mw.project.undo_stack) == 1, (
        "add_block_from_library() didn't push undo state - the scene "
        "resolved its owning window to something other than this "
        "MainWindow (see logic_studio/ui/window_lookup.py)"
    )
    assert mw.is_dirty is True


def test_property_commit_updates_undo_and_dirty_when_embedded(qsettings, qapp):
    """property_grid.py's _commit_property() is the single most common
    edit in the app (typing a new value into any block's property field)
    - it was one of the 32 real call sites relying on the broken
    self.window()."""
    mw = MainWindow(settings=qsettings)
    _host = _embed_like_the_shell_does(mw)  # noqa: F841

    category = BlockRegistry.get_categories()[0]
    block_type = BlockRegistry.get_blocks_in_category(category)[0]
    mw.scene.add_block_from_library(block_type, 200, 200)
    undo_len_after_add = len(mw.project.undo_stack)

    items = [i for i in mw.scene.items() if hasattr(i, "logic_block")]
    assert items, "the block just added isn't on the scene - test setup is wrong"
    logic_block = items[0].logic_block

    mw.property_panel.load_block_properties(logic_block, project=mw.project)
    prop_key = next(iter(logic_block.properties))
    old_value = logic_block.properties[prop_key]
    new_value = str(old_value) + "_changed"
    mw.property_panel._commit_property(prop_key, new_value)

    assert len(mw.project.undo_stack) == undo_len_after_add + 1, (
        "_commit_property() didn't push undo state when MainWindow is "
        "embedded"
    )
    assert mw.is_dirty is True


def test_library_double_click_insert_works_when_embedded(qsettings, qapp):
    """library.py's _on_item_double_clicked() used to return early
    (`view is None`) whenever `self.window()` missed - double-click-to-
    insert silently did nothing at all, not just an undo-tracking gap."""
    mw = MainWindow(settings=qsettings)
    _host = _embed_like_the_shell_does(mw)  # noqa: F841

    category = BlockRegistry.get_categories()[0]
    block_type = BlockRegistry.get_blocks_in_category(category)[0]
    item = None
    for i in range(mw.library_panel.tree.topLevelItemCount()):
        cat_item = mw.library_panel.tree.topLevelItem(i)
        for j in range(cat_item.childCount()):
            child = cat_item.child(j)
            if child.data(0, TYPE_ID_ROLE) == block_type:
                item = child
                break
        if item is not None:
            break
    assert item is not None, "couldn't find the test block in the library tree - test setup is wrong"

    before = len(mw.scene.items())
    mw.library_panel._on_item_double_clicked(item, 0)
    after = len(mw.scene.items())

    assert after > before, (
        "double-click insert added nothing to the scene - library.py's "
        "own window lookup missed (view resolved to None)"
    )
