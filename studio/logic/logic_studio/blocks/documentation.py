from logic_studio.blocks.base import BaseLogicBlock
from logic_studio.blocks.registry import BlockRegistry

# Shared search aliases for every documentation block type (§9.6).
DOC_ALIASES = ["opis", "komentarz", "tekst", "tytuł"]

# feat/wire-detour-and-text-size §B1: the "Rozmiar tekstu" property key —
# " (pkt)" suffix so ui/panels/property_grid.py's own unit-suffix
# convention (_split_unit()) shows it as a "pkt"-suffixed spinbox
# automatically, the same way every other unit-bearing property already
# does, no per-property UI code needed here. Range (§B1: 6-48) is
# enforced in property_grid.py's own editor construction, not here —
# this module has no UI dependency and shouldn't gain one just for a
# min/max pair.
TEXT_SIZE_KEY = "Rozmiar tekstu (pkt)"
_TEXT_SIZE_DESCRIPTION = "Font size of the text on the diagram, in points (6-48)."

# feat/text-formatting: character and paragraph formatting, written by the
# Word-style Format toolbar (ui/format_toolbar.py) and editable in the
# property grid like any other property. New, English keys: nothing older
# ever stored them, and BaseLogicBlock.deserialize() merges a saved
# block onto a freshly-constructed one, so a project saved before these
# existed simply gets the defaults below.
FONT_KEY = "Font"
BOLD_KEY = "Bold"
ITALIC_KEY = "Italic"
UNDERLINE_KEY = "Underline"
ALIGN_KEY = "Align"
ALIGNMENTS = ("Left", "Center", "Right", "Justify")
DEFAULT_DOC_FONT = "Arial"  # ui/canvas/style.py FONT_FAMILY, not imported (no Qt here)

_FORMAT_DESCRIPTIONS = {
    FONT_KEY: "Font family of the text on the diagram.",
    BOLD_KEY: "Bold text.",
    ITALIC_KEY: "Italic text.",
    UNDERLINE_KEY: "Underlined text.",
    ALIGN_KEY: "Paragraph alignment: Left, Center, Right or Justify.",
}


def _add_format_properties(block, bold=False, align="Left"):
    block.properties[FONT_KEY] = DEFAULT_DOC_FONT
    block.properties[BOLD_KEY] = bold
    block.properties[ITALIC_KEY] = False
    block.properties[UNDERLINE_KEY] = False
    block.properties[ALIGN_KEY] = align

@BlockRegistry.register
class TextBlock(BaseLogicBlock):
    PROPERTY_DESCRIPTIONS = {
        "Text": "Free text shown on the diagram.",
        TEXT_SIZE_KEY: _TEXT_SIZE_DESCRIPTION,
        **_FORMAT_DESCRIPTIONS,
    }

    def __init__(self, type_id="doc.text", default_name="Text", category="Documentation", description="Free text on the diagram, no effect on the logic."):
        super().__init__(type_id, default_name, category, description)
        self.aliases = list(DOC_ALIASES)
        self.width = 150
        self.height = 40
        self.properties["Text"] = "Enter text here"
        # feat/wire-detour-and-text-size §B1: 9 matches the font size this
        # block type has always painted at -- ui/canvas/style.py's own
        # FONT_SIZE_DOC_TEXT, read directly from that module's current
        # value rather than guessed. NOT imported from there: this module
        # (like every logic_studio/blocks/*.py file) must stay importable,
        # and its blocks constructible, with zero PySide6/logic_studio.ui
        # dependency -- a headless engine/compiler process reconstructs
        # every block type on project load, doc blocks included, and must
        # never pull in Qt just to do that (tests/test_acceptance.py::
        # test_headless_engine_no_qt).
        self.properties[TEXT_SIZE_KEY] = 9
        _add_format_properties(self)

        # Doc blocks don't execute logic and have no pins
        self.inputs = []
        self.outputs = []

    def evaluate(self, engine=None):
        pass

@BlockRegistry.register
class NoteBlock(BaseLogicBlock):
    PROPERTY_DESCRIPTIONS = {
        "Text": "Multi-line note shown on the diagram.",
        TEXT_SIZE_KEY: _TEXT_SIZE_DESCRIPTION,
        **_FORMAT_DESCRIPTIONS,
    }

    def __init__(self, type_id="doc.note", default_name="Note", category="Documentation", description="Multi-line note on the diagram, no effect on the logic."):
        super().__init__(type_id, default_name, category, description)
        self.aliases = list(DOC_ALIASES)
        self.width = 200
        self.height = 80
        # Was "Multiline\\nnote here" (a literal backslash-n, not a newline)
        # before this PR — fixed (§6.7).
        self.properties["Text"] = "Multiline\nnote here"
        # §B1: matches ui/canvas/style.py's own FONT_SIZE_DOC_NOTE — see
        # TextBlock's own comment above for why this isn't imported.
        self.properties[TEXT_SIZE_KEY] = 8
        _add_format_properties(self)

        self.inputs = []
        self.outputs = []

    def evaluate(self, engine=None):
        pass

@BlockRegistry.register
class SectionTitleBlock(BaseLogicBlock):
    PROPERTY_DESCRIPTIONS = {
        "Text": "Section heading text.",
        TEXT_SIZE_KEY: _TEXT_SIZE_DESCRIPTION,
        **_FORMAT_DESCRIPTIONS,
    }

    def __init__(self, type_id="doc.section", default_name="Section Title", category="Documentation", description="Large diagram section heading, no effect on the logic."):
        super().__init__(type_id, default_name, category, description)
        self.aliases = list(DOC_ALIASES)
        self.width = 300
        self.height = 50
        self.properties["Text"] = "SECTION TITLE"
        # §B1: matches ui/canvas/style.py's own FONT_SIZE_DOC_SECTION —
        # see TextBlock's own comment above for why this isn't imported.
        self.properties[TEXT_SIZE_KEY] = 14
        _add_format_properties(self, bold=True)

        self.inputs = []
        self.outputs = []

    def evaluate(self, engine=None):
        pass
