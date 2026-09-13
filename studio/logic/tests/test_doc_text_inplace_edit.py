"""feat/text-formatting: editing a documentation block in place on the
canvas, with real key presses.

Pinned: double-click opens an editor on the block itself (no dialog), typed
text lands in the block as one undo step, Escape discards, Delete edits the
text instead of deleting the block, and clicking elsewhere keeps the text.
"""
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from logic_studio.blocks import register_builtin_blocks
from logic_studio.blocks.registry import BlockRegistry

register_builtin_blocks()


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _window_with(type_id, text):
    from logic_studio.ui.main_window import MainWindow
    from logic_studio.ui.canvas.block_item import BlockItem

    window = MainWindow()
    window.resize(1000, 700)
    window.show()
    block = BlockRegistry.create_block(type_id)
    block.properties["Text"] = text
    window.project.add_block(block)
    item = next((i for i in window.scene.items() if isinstance(i, BlockItem) and i.logic_block is block), None)
    if item is None:
        item = BlockItem(block)
        window.scene.addItem(item)
    QApplication.processEvents()
    return window, block, item


def _type(editor, text):
    view = editor.scene().views()[0]
    view.setFocus()
    for ch in text:
        QTest.keyClick(view.viewport(), ch)


def test_double_click_opens_an_in_place_editor_not_a_dialog():
    _app()
    window, block, item = _window_with("doc.text", "Pump")
    item._start_doc_edit()
    assert item._doc_editor is not None
    assert item._doc_editor.toPlainText() == "Pump"
    assert item._doc_editor.isVisible()
    assert item._doc_editor.textInteractionFlags() == Qt.TextEditorInteraction


def test_typed_text_is_kept_on_enter_as_one_undo_step():
    _app()
    window, block, item = _window_with("doc.text", "")
    depth = len(window.project.undo_stack)
    item._start_doc_edit()
    editor = item._doc_editor
    _type(editor, "Boiler")
    QTest.keyClick(editor.scene().views()[0].viewport(), Qt.Key_Return)
    QApplication.processEvents()
    assert block.properties["Text"] == "Boiler"
    assert item._doc_editor is None
    assert len(window.project.undo_stack) == depth + 1


def test_escape_discards_the_edit():
    _app()
    window, block, item = _window_with("doc.text", "Keep me")
    item._start_doc_edit()
    editor = item._doc_editor
    _type(editor, "XYZ")
    QTest.keyClick(editor.scene().views()[0].viewport(), Qt.Key_Escape)
    QApplication.processEvents()
    assert block.properties["Text"] == "Keep me"


def test_delete_edits_the_text_instead_of_deleting_the_block():
    _app()
    window, block, item = _window_with("doc.text", "AB")
    item.setSelected(True)
    item._start_doc_edit()
    editor = item._doc_editor
    viewport = editor.scene().views()[0].viewport()
    editor.scene().views()[0].setFocus()
    QTest.keyClick(viewport, Qt.Key_Home)
    QTest.keyClick(viewport, Qt.Key_Delete)
    QTest.keyClick(viewport, Qt.Key_Return)
    QApplication.processEvents()
    assert block in window.project.blocks
    assert block.properties["Text"] == "B"


def test_note_takes_enter_as_a_new_line_and_click_elsewhere_keeps_it():
    _app()
    window, block, item = _window_with("doc.note", "")
    item._start_doc_edit()
    editor = item._doc_editor
    viewport = editor.scene().views()[0].viewport()
    _type(editor, "one")
    QTest.keyClick(viewport, Qt.Key_Return)
    _type(editor, "two")
    assert item._doc_editor is not None  # Enter did not close a note
    editor.clearFocus()
    QApplication.processEvents()
    assert block.properties["Text"] == "one\ntwo"


def test_block_lets_go_of_the_mouse_so_the_next_edit_and_click_away_work():
    """User report "w Logic nie dziala edycja tekstu": after one in-place
    edit the block kept the mouse grab (the double-click's release landed on
    the editor), so the next click dragged that block along - a second edit
    never opened and clicking away never kept the text."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from logic_studio.ui.main_window import MainWindow
    from logic_studio.ui.canvas.block_item import BlockItem

    QApplication.instance() or QApplication([])
    mw = MainWindow()
    mw.resize(1200, 800)
    mw.show()
    QTest.qWaitForWindowExposed(mw)
    view = mw.scene.views()[0]
    viewport = view.viewport()

    def add(type_id, x, y):
        mw.scene.add_block_from_library(type_id, x, y)
        return [i for i in mw.scene.items() if isinstance(i, BlockItem) and i.logic_block.type_id == type_id][-1]

    def double_click(item):
        view.centerOn(item)
        point = view.mapFromScene(item.mapToScene(item.boundingRect().center()))
        QTest.mouseClick(viewport, Qt.LeftButton, Qt.NoModifier, point)
        QTest.mouseDClick(viewport, Qt.LeftButton, Qt.NoModifier, point)
        return getattr(item, "_doc_editor", None)

    text = add("doc.text", 200, 200)
    note = add("doc.note", 200, 400)
    text_pos = text.pos()

    assert double_click(text) is not None
    assert mw.scene.mouseGrabberItem() is None
    QTest.keyClicks(view, "Boiler room")  # replaces the selected sample text
    QTest.keyClick(view, Qt.Key_Return)
    assert text.logic_block.properties["Text"] == "Boiler room"

    editor = double_click(note)
    assert editor is not None
    assert text.pos() == text_pos
    QTest.keyClicks(view, "Pumps")
    QTest.mouseClick(viewport, Qt.LeftButton, Qt.NoModifier, viewport.rect().topLeft() + viewport.rect().center() * 0.1)
    assert note.logic_block.properties["Text"] == "Pumps"
    assert note._doc_editor is None
    mw.is_dirty = False
    mw.hide()
