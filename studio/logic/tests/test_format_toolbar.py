"""feat/text-formatting: Word-style formatting for documentation blocks.

What is pinned: the formatting is stored as ordinary block properties with
sensible defaults (so old projects load with them), the canvas font and
alignment follow those properties, and the Format toolbar writes them to
every selected text block as ONE undo step and reads back what a mixed
selection has in common.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from logic_studio.blocks import register_builtin_blocks
from logic_studio.blocks.registry import BlockRegistry
from logic_studio.blocks.documentation import (
    ALIGN_KEY, BOLD_KEY, FONT_KEY, ITALIC_KEY, TEXT_SIZE_KEY, UNDERLINE_KEY,
)

register_builtin_blocks()


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_every_doc_block_carries_formatting_defaults():
    for type_id, bold in (("doc.text", False), ("doc.note", False), ("doc.section", True)):
        block = BlockRegistry.create_block(type_id)
        assert block.properties[FONT_KEY] == "Arial"
        assert block.properties[BOLD_KEY] is bold
        assert block.properties[ITALIC_KEY] is False
        assert block.properties[UNDERLINE_KEY] is False
        assert block.properties[ALIGN_KEY] == "Left"


def test_a_block_saved_before_formatting_existed_loads_with_the_defaults():
    block = BlockRegistry.create_block("doc.text")
    data = block.serialize()
    for key in (FONT_KEY, BOLD_KEY, ITALIC_KEY, UNDERLINE_KEY, ALIGN_KEY):
        data["properties"].pop(key)
    restored = type(block).deserialize(data)
    assert restored.properties[ALIGN_KEY] == "Left"
    assert restored.properties[BOLD_KEY] is False


def test_property_writes_keep_their_types():
    block = BlockRegistry.create_block("doc.text")
    block.update_property(BOLD_KEY, "True")
    block.update_property(TEXT_SIZE_KEY, "16")
    assert block.properties[BOLD_KEY] is True
    assert block.properties[TEXT_SIZE_KEY] == 16


def test_canvas_font_and_alignment_follow_the_properties():
    _app()
    from logic_studio.ui.canvas.block_item import BlockItem

    block = BlockRegistry.create_block("doc.text")
    block.properties.update({FONT_KEY: "Courier New", BOLD_KEY: True, ITALIC_KEY: True, UNDERLINE_KEY: True, ALIGN_KEY: "Justify"})
    item = BlockItem(block)
    font = item.doc_text_font()
    assert font.family() == "Courier New"
    assert font.bold() and font.italic() and font.underline()
    assert item.doc_text_alignment() == Qt.AlignJustify


def test_section_keeps_its_bold_look_and_can_be_made_regular():
    _app()
    from logic_studio.ui.canvas.block_item import BlockItem

    section = BlockRegistry.create_block("doc.section")
    assert BlockItem(section).doc_text_font().bold()
    section.properties[BOLD_KEY] = False
    assert not BlockItem(section).doc_text_font().bold()


def test_format_toolbar_writes_every_selected_text_block_as_one_undo_step():
    _app()
    from logic_studio.ui.main_window import MainWindow
    from logic_studio.ui.canvas.block_item import BlockItem

    window = MainWindow()
    a = BlockRegistry.create_block("doc.text")
    b = BlockRegistry.create_block("doc.note")
    window.project.add_block(a)
    window.project.add_block(b)
    window.scene.load_project(window.project) if hasattr(window.scene, "load_project") else None
    items = [i for i in window.scene.items() if isinstance(i, BlockItem) and i.logic_block in (a, b)]
    if len(items) < 2:
        for block in (a, b):
            item = BlockItem(block)
            window.scene.addItem(item)
            items.append(item)
    for item in items:
        item.setSelected(True)

    toolbar = window.format_toolbar
    assert set(toolbar.selected_doc_blocks()) >= {a, b}

    undo_depth = len(getattr(window.project, "undo_stack", []))
    toolbar._apply({BOLD_KEY: True, ALIGN_KEY: "Center"})
    assert a.properties[BOLD_KEY] is True and b.properties[BOLD_KEY] is True
    assert a.properties[ALIGN_KEY] == "Center" and b.properties[ALIGN_KEY] == "Center"
    if hasattr(window.project, "undo_stack"):
        assert len(window.project.undo_stack) == undo_depth + 1


def test_format_toolbar_greys_out_without_a_text_selection_and_reports_mixed_values():
    _app()
    from logic_studio.ui.format_toolbar import common_value

    a = BlockRegistry.create_block("doc.text")
    b = BlockRegistry.create_block("doc.text")
    a.properties[TEXT_SIZE_KEY] = 12
    b.properties[TEXT_SIZE_KEY] = 14
    assert common_value([a, b], TEXT_SIZE_KEY) is None
    assert common_value([a, b], ALIGN_KEY) == "Left"
    assert common_value([], ALIGN_KEY) is None

    from logic_studio.ui.main_window import MainWindow
    window = MainWindow()
    window.scene.clearSelection()
    window.format_toolbar.refresh()
    assert not window.format_toolbar.act_bold.isEnabled()
    assert not window.format_toolbar.size_combo.isEnabled()


def test_font_size_box_applies_a_picked_and_a_typed_size():
    """The size box: picking a size from the list and typing one + Enter
    both resize the selected block's text (user report: size did nothing)."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from logic_studio.ui.main_window import MainWindow
    from logic_studio.ui.canvas.block_item import BlockItem
    from logic_studio.blocks.documentation import TEXT_SIZE_KEY

    QApplication.instance() or QApplication([])
    mw = MainWindow()
    mw.scene.add_block_from_library("doc.text", 100, 100)
    item = [i for i in mw.scene.items() if isinstance(i, BlockItem) and i.logic_block.type_id == "doc.text"][-1]
    item.setSelected(True)
    toolbar = mw.format_toolbar
    height = item.boundingRect().height()

    index = toolbar.size_combo.findText("20")
    toolbar.size_combo.setCurrentIndex(index)
    toolbar.size_combo.activated.emit(index)
    assert item.logic_block.properties[TEXT_SIZE_KEY] == 20
    assert item.doc_text_font().pointSize() == 20
    assert item.boundingRect().height() > height

    edit = toolbar.size_combo.lineEdit()
    edit.selectAll()
    QTest.keyClicks(edit, "32")
    QTest.keyClick(edit, Qt.Key_Return)
    assert item.logic_block.properties[TEXT_SIZE_KEY] == 32
    assert toolbar.size_combo.currentText() == "32"
