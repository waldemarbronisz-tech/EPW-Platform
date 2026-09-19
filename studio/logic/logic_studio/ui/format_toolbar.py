"""feat/text-formatting: the Word-style formatting bar for documentation
blocks (doc.text, doc.note, doc.section).

One toolbar, grouped the way a word processor groups it:
    Style | Font | Size | B I U | left  centre  right  justify
It acts on every selected documentation block at once and shows what they
have in common - an empty box means the selection is mixed. With no text
block selected the controls are greyed out rather than hidden, so the bar
never jumps around.

It is a toolbar of MainWindow's own, separate from the main one. Studio
hides only MainWindow's main toolbar and menu bar (studio/shell/
logic_panel.py), so this bar shows in Studio exactly as it does in the
standalone editor, with no mirroring code.

Formatting is stored as ordinary block properties (blocks/documentation.py),
so it saves, loads, undoes and copies like every other property.
"""
from PySide6.QtCore import Qt, QSignalBlocker
from PySide6.QtGui import QAction, QActionGroup, QFont
from PySide6.QtWidgets import QComboBox, QFontComboBox, QToolBar

from logic_studio.ui.icons import action_icon
from shared.logic.blocks.documentation import (
    ALIGN_KEY, ALIGNMENTS, BOLD_KEY, FONT_KEY, ITALIC_KEY, TEXT_SIZE_KEY, UNDERLINE_KEY,
)

DOC_TYPE_IDS = ("doc.text", "doc.note", "doc.section")

# Paragraph styles: what choosing one writes, as a word processor applies it.
TEXT_STYLES = (
    ("Normal", {TEXT_SIZE_KEY: 9, BOLD_KEY: False, ITALIC_KEY: False}),
    ("Title", {TEXT_SIZE_KEY: 20, BOLD_KEY: True, ITALIC_KEY: False}),
    ("Heading 1", {TEXT_SIZE_KEY: 14, BOLD_KEY: True, ITALIC_KEY: False}),
    ("Heading 2", {TEXT_SIZE_KEY: 12, BOLD_KEY: True, ITALIC_KEY: False}),
    ("Caption", {TEXT_SIZE_KEY: 8, BOLD_KEY: False, ITALIC_KEY: True}),
)

FONT_SIZES = (6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48)

_ALIGN_TITLES = {
    "Left": "Align text left",
    "Center": "Center text",
    "Right": "Align text right",
    "Justify": "Justify text",
}


def common_value(blocks, key):
    """The value every block shares for `key`, or None when they differ (or
    there are no blocks)."""
    if not blocks:
        return None
    first = blocks[0].properties.get(key)
    return first if all(b.properties.get(key) == first for b in blocks) else None


class FormatToolbar(QToolBar):
    def __init__(self, main_window):
        super().__init__("Format", main_window)
        self.setObjectName("format_toolbar")
        self.setMovable(True)
        self._mw = main_window

        self.style_combo = QComboBox(self)
        self.style_combo.setToolTip("Paragraph style")
        self.style_combo.setMinimumContentsLength(9)
        self.style_combo.addItem("")
        for name, _ in TEXT_STYLES:
            self.style_combo.addItem(name)
        self.style_combo.activated.connect(self._on_style)
        self.addWidget(self.style_combo)

        self.font_combo = QFontComboBox(self)
        self.font_combo.setToolTip("Font")
        self.font_combo.setMaximumWidth(170)
        self.font_combo.currentFontChanged.connect(self._on_font)
        self.addWidget(self.font_combo)

        self.size_combo = QComboBox(self)
        self.size_combo.setToolTip("Font size")
        self.size_combo.setEditable(True)
        self.size_combo.setMinimumContentsLength(3)
        for size in FONT_SIZES:
            self.size_combo.addItem(str(size))
        self.size_combo.activated.connect(lambda _i: self._on_size(self.size_combo.currentText()))
        self.size_combo.lineEdit().editingFinished.connect(lambda: self._on_size(self.size_combo.currentText()))
        self.addWidget(self.size_combo)

        self.addSeparator()

        self.act_bold = self._toggle_action("B", "Bold", QFont.Bold, BOLD_KEY, "Ctrl+B")
        self.act_italic = self._toggle_action("I", "Italic", None, ITALIC_KEY, "Ctrl+I")
        self.act_underline = self._toggle_action("U", "Underline", None, UNDERLINE_KEY, "Ctrl+U")
        italic_font = self.act_italic.font()
        italic_font.setItalic(True)
        self.act_italic.setFont(italic_font)
        underline_font = self.act_underline.font()
        underline_font.setUnderline(True)
        self.act_underline.setFont(underline_font)
        self.act_bold.setIcon(action_icon("text_bold", 16))
        self.act_italic.setIcon(action_icon("text_italic", 16))
        self.act_underline.setIcon(action_icon("text_underline", 16))

        self.addSeparator()

        self._align_group = QActionGroup(self)
        self._align_group.setExclusive(True)
        self.align_actions = {}
        for align in ALIGNMENTS:
            action = QAction(align[0] if align != "Justify" else "J", self)
            action.setToolTip(_ALIGN_TITLES[align])
            action.setIcon(action_icon(f"text_align_{align.lower()}", 16))
            action.setCheckable(True)
            action.triggered.connect(lambda _checked=False, a=align: self._apply({ALIGN_KEY: a}))
            self._align_group.addAction(action)
            self.addAction(action)
            self.align_actions[align] = action

        self.refresh()

    # ---- helpers ---------------------------------------------------------

    def _toggle_action(self, text, tooltip, weight, key, shortcut):
        action = QAction(text, self)
        action.setToolTip(f"{tooltip} ({shortcut})")
        action.setCheckable(True)
        if weight is not None:
            font = action.font()
            font.setWeight(weight)
            action.setFont(font)
        # Mixed or off becomes on; on becomes off - as in a word processor.
        action.triggered.connect(lambda _checked=False, k=key: self._apply({k: common_value(self.selected_doc_blocks(), k) is not True}))
        self.addAction(action)
        return action

    def selected_doc_blocks(self):
        """The logic blocks behind every selected documentation block item."""
        from logic_studio.ui.canvas.block_item import BlockItem
        scene = getattr(self._mw, "scene", None)
        if scene is None:
            return []
        return [
            item.logic_block for item in scene.selectedItems()
            if isinstance(item, BlockItem) and item.logic_block.type_id in DOC_TYPE_IDS
        ]

    # ---- reading the selection -------------------------------------------

    def refresh(self):
        blocks = self.selected_doc_blocks()
        enabled = bool(blocks)
        for widget in (self.style_combo, self.font_combo, self.size_combo):
            widget.setEnabled(enabled)
        for action in (self.act_bold, self.act_italic, self.act_underline, *self.align_actions.values()):
            action.setEnabled(enabled)

        blockers = [QSignalBlocker(w) for w in (self.style_combo, self.font_combo, self.size_combo)]
        try:
            self.style_combo.setCurrentIndex(0)
            font = common_value(blocks, FONT_KEY)
            if font:
                self.font_combo.setCurrentFont(QFont(font))
            size = common_value(blocks, TEXT_SIZE_KEY)
            self.size_combo.setEditText("" if size is None else str(size))
        finally:
            del blockers

        self.act_bold.setChecked(common_value(blocks, BOLD_KEY) is True)
        self.act_italic.setChecked(common_value(blocks, ITALIC_KEY) is True)
        self.act_underline.setChecked(common_value(blocks, UNDERLINE_KEY) is True)
        align = common_value(blocks, ALIGN_KEY)
        self._align_group.setExclusive(False)
        for name, action in self.align_actions.items():
            action.setChecked(name == align)
        self._align_group.setExclusive(True)

    # ---- writing ---------------------------------------------------------

    def _on_style(self, index):
        if index <= 0:
            return
        _name, updates = TEXT_STYLES[index - 1]
        self._apply(dict(updates))
        self.style_combo.setCurrentIndex(0)

    def _on_font(self, qfont):
        self._apply({FONT_KEY: qfont.family()})

    def _on_size(self, text):
        try:
            size = int(float(str(text).strip()))
        except ValueError:
            return
        self._apply({TEXT_SIZE_KEY: max(6, min(48, size))})

    def _apply(self, updates):
        """Writes `updates` to every selected documentation block as ONE undo
        step, then refits and repaints them and reloads the property grid."""
        blocks = self.selected_doc_blocks()
        changes = [
            (b, k, v) for b in blocks for k, v in updates.items()
            if b.properties.get(k) != v
        ]
        if not changes:
            self.refresh()
            return
        project = getattr(self._mw, "project", None)
        if project is not None:
            project.push_state()
        if hasattr(self._mw, "set_dirty"):
            self._mw.set_dirty()
        for block, key, value in changes:
            block.update_property(key, str(value))
        self._refit(blocks)
        panel = getattr(self._mw, "property_panel", None)
        if panel is not None and getattr(panel, "current_block", None) in blocks:
            panel.load_block_properties(panel.current_block, project, getattr(self._mw, "current_macro_def_id", None))
        self.refresh()

    def _refit(self, blocks):
        from logic_studio.ui.canvas.block_item import BlockItem
        scene = getattr(self._mw, "scene", None)
        if scene is None:
            return
        wanted = set(id(b) for b in blocks)
        for item in scene.items():
            if isinstance(item, BlockItem) and id(item.logic_block) in wanted:
                item.prepareGeometryChange()
                item._determine_shape_style()
                item.update()
        scene.update()
