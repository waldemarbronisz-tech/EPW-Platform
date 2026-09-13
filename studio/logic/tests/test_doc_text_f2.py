"""One way of editing text in all of EPW Studio: F2 on a single selected
documentation block starts the in-place editor, as it does on a selected
text box in the Synoptic editor."""
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication


def _window():
    QApplication.instance() or QApplication([])
    from logic_studio.ui.main_window import MainWindow
    mw = MainWindow()
    mw.resize(1200, 800)
    mw.show()
    QTest.qWaitForWindowExposed(mw)
    return mw


def _add(mw, type_id, x, y):
    """The block this call added - the difference of the scene's blocks
    before and after, not the last one of its type (items() is in stacking
    order, so two blocks of one type can come back in either order)."""
    from logic_studio.ui.canvas.block_item import BlockItem
    before = {id(i) for i in mw.scene.items() if isinstance(i, BlockItem)}
    mw.scene.add_block_from_library(type_id, x, y)
    added = [i for i in mw.scene.items() if isinstance(i, BlockItem) and id(i) not in before]
    assert len(added) == 1
    return added[0]


def test_f2_on_a_selected_note_edits_it_and_the_text_is_kept():
    mw = _window()
    view = mw.scene.views()[0]
    note = _add(mw, "doc.note", 200, 200)
    mw.scene.clearSelection()
    note.setSelected(True)
    view.setFocus()
    QTest.keyClick(view, Qt.Key_F2)
    assert getattr(note, "_doc_editor", None) is not None
    QTest.keyClicks(view, "Pompy")
    QTest.keyClick(view, Qt.Key_Return, Qt.ControlModifier)
    assert note.logic_block.properties["Text"] == "Pompy"
    mw.is_dirty = False
    mw.hide()


def test_f2_with_two_blocks_selected_does_nothing():
    mw = _window()
    view = mw.scene.views()[0]
    a = _add(mw, "doc.text", 100, 100)
    b = _add(mw, "doc.text", 100, 300)
    assert a is not b
    mw.scene.clearSelection()
    a.setSelected(True)
    b.setSelected(True)
    assert len(mw.scene.selectedItems()) == 2
    view.setFocus()
    QTest.keyClick(view, Qt.Key_F2)
    assert getattr(a, "_doc_editor", None) is None
    assert getattr(b, "_doc_editor", None) is None
    mw.is_dirty = False
    mw.hide()


def test_f2_on_a_selected_logic_gate_does_nothing():
    mw = _window()
    view = mw.scene.views()[0]
    gate = _add(mw, "logic.and", 200, 200)
    mw.scene.clearSelection()
    gate.setSelected(True)
    view.setFocus()
    QTest.keyClick(view, Qt.Key_F2)
    assert getattr(gate, "_doc_editor", None) is None
    assert gate.scene() is mw.scene
    mw.is_dirty = False
    mw.hide()
