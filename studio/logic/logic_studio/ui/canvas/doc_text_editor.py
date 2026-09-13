"""feat/text-formatting: typing straight into a documentation block on the
canvas, instead of into a modal dialog.

A QGraphicsTextItem laid over the block's own text, in the block's own
font, weight, style, decoration and alignment, so editing looks like the
text itself became editable - the way a text box works in a word processor:

  - doc.note: Enter makes a new line; Ctrl+Enter keeps the text.
  - doc.text / doc.section: Enter keeps the text (they are single-line).
  - Clicking anywhere else keeps the text (focus-out).
  - Escape throws the edit away.

While it is open, every key goes to the text - including the ones the
main window uses as shortcuts (Delete, Ctrl+C, Ctrl+V, Ctrl+A...). Without
that, pressing Delete to remove a character deleted the whole block.

Committing goes through BlockItem.apply_doc_text(), so it is one undo step
and the block refits to the new text exactly as before.
"""
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QTextCursor, QTextOption
from PySide6.QtWidgets import QGraphicsTextItem

from logic_studio.ui.canvas import style
from logic_studio.ui.qt_lifetime import create_owned_timer


class DocTextEditor(QGraphicsTextItem):
    def __init__(self, block_item):
        super().__init__(block_item)
        self._item = block_item
        self._done = False
        block = block_item.logic_block
        self._multiline = block.type_id == "doc.note"

        self.document().setDocumentMargin(0)
        self.setPlainText(block.properties.get("Text", ""))
        self.setFont(block_item.doc_text_font())
        self.setDefaultTextColor(style.COLOR_DOC_TEXT)

        option = QTextOption(block_item.doc_text_alignment())
        option.setWrapMode(QTextOption.WordWrap if self._multiline else QTextOption.NoWrap)
        self.document().setDefaultTextOption(option)

        if self._multiline:
            self.setTextWidth(max(block_item.width - 12, 20))
            self.setPos(6, 6)
        else:
            self.setTextWidth(max(block_item.width, self.document().idealWidth() + 4, 40))
            self.setPos(0, max(0.0, (block_item.height - self.boundingRect().height()) / 2))

        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setZValue(1000)
        self.document().contentsChanged.connect(self._fit_width)

    def start(self):
        self.setFocus(Qt.MouseFocusReason)
        cursor = self.textCursor()
        if self.toPlainText() == self._placeholder_text():
            # A fresh block still shows its sample text ("Enter text here"):
            # select it, so typing replaces it as in a word processor.
            cursor.select(QTextCursor.Document)
        else:
            cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)

    def _placeholder_text(self):
        from logic_studio.blocks.registry import BlockRegistry
        fresh = BlockRegistry.create_block(self._item.logic_block.type_id)
        return fresh.properties.get("Text") if fresh is not None else None

    def _fit_width(self):
        """A single-line block's editor widens as you type instead of
        wrapping; a note wraps within its width (and grows downward)."""
        if not self._multiline:
            needed = self.document().idealWidth() + 4
            if needed > self.textWidth():
                self.setTextWidth(needed)

    # ---- keys ------------------------------------------------------------

    def sceneEvent(self, event):
        # Claim every shortcut while editing, so the key reaches the text
        # rather than a main-window action (Delete, Ctrl+C/V/A, ...).
        if event.type() == QEvent.ShortcutOverride:
            event.accept()
            return True
        return super().sceneEvent(event)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            self.finish(commit=False)
            event.accept()
            return
        if key in (Qt.Key_Return, Qt.Key_Enter):
            if not self._multiline or event.modifiers() & Qt.ControlModifier:
                self.finish(commit=True)
                event.accept()
                return
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.finish(commit=True)

    # ---- finishing -------------------------------------------------------

    def finish(self, commit: bool):
        if self._done:
            return
        self._done = True
        text = self.toPlainText()
        item = self._item
        item._doc_editor = None
        scene = self.scene()
        if scene is not None and scene.mouseGrabberItem() in (self, item):
            scene.mouseGrabberItem().ungrabMouse()
        self.setVisible(False)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        if commit:
            item.apply_doc_text(text)
        item.update()
        # Removed on the next event-loop turn: removing an item from inside
        # its own focus-out/key event is not safe.
        self._remove_timer = create_owned_timer(self, self._remove, single_shot=True)
        self._remove_timer.start(0)

    def _remove(self):
        scene = self.scene()
        if scene is not None:
            scene.removeItem(self)
