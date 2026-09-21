"""Owner: "zmień od razu przy okazji aby zawijało tekst w obrębie symbolu."

The screenshot was a system-signal block reading "SYS.ACCESS_..." - the
name shrunk to the smallest font the renderer allows and then cut off,
so the half that says WHICH signal was the half thrown away. Every name
worth reading is one of the long ones: SYS.ACCESS_ENGINEER,
SSWIN.CMD_ARM_PARTIAL, SEC.ZONE.PARTER.ARMED.

These test the wrap itself against real QFontMetricsF - a fake metric
object would let a wrap that is wrong on screen pass here. What they
pin is the property that matters and the one that is easy to lose:
every produced line FITS, and nothing is dropped.

The second half checks the block still honours its own outline. The
renderer's long-standing rule - never hand Qt one multi-line string,
never draw past the bottom edge - is exactly what a naive "just turn on
TextWordWrap" would have broken.
"""
import pytest
from PySide6.QtGui import QFont, QFontMetricsF
from PySide6.QtWidgets import QApplication

from logic_studio.ui.canvas.block_item import _wrap_io_text


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def fm(app):
    return QFontMetricsF(QFont("Tahoma", 9))


def _fits(lines, fm, width):
    return all(fm.horizontalAdvance(line) <= width for line in lines)


# --- the wrap itself ---------------------------------------------------------

def test_text_that_already_fits_is_left_alone(fm):
    width = fm.horizontalAdvance("SYS.READY") + 10

    assert _wrap_io_text("SYS.READY", fm, width) == ["SYS.READY"]


def test_a_long_identifier_is_wrapped_rather_than_cut(fm):
    """The reported case. Before this it came back as one line the
    renderer then ellipsis'd."""
    text = "SYS.ACCESS_ENGINEER"
    width = fm.horizontalAdvance("SYS.ACCESS")

    lines = _wrap_io_text(text, fm, width)

    assert len(lines) > 1, lines
    assert "".join(lines) == text, "characters were lost in the wrap"
    assert _fits(lines, fm, width), lines


def test_no_character_is_ever_lost(fm):
    """Joining the lines back must give the original exactly - a wrap
    that drops a separator produces a name that is not the signal's."""
    for text in ("SEC.ZONE.PARTER.ARMED", "SSWIN.CMD_ARM_PARTIAL",
                 "ELA01.DI.10", "MWR.BARDZO_DLUGA_NAZWA_REJESTRU"):
        lines = _wrap_io_text(text, fm, fm.horizontalAdvance("ABCDEFGH"))
        assert "".join(lines) == text, (text, lines)


def test_the_break_keeps_the_separator_on_the_line_it_ends(fm):
    """"SYS." over "ACCESS_ENGINEER" reads as one name; a line starting
    with "." reads as a typo."""
    lines = _wrap_io_text("SYS.ACCESS_ENGINEER", fm, fm.horizontalAdvance("SYS.AC"))

    assert not any(line.startswith((".", "_")) for line in lines), lines


def test_a_segment_with_no_separator_is_broken_by_characters(fm):
    """A custom Tag can be one long word. Ugly beats invisible."""
    text = "BARDZODLUGANAZWABEZSEPARATOROW"
    width = fm.horizontalAdvance("ABCDE")

    lines = _wrap_io_text(text, fm, width)

    assert len(lines) > 1
    assert "".join(lines) == text
    assert _fits(lines, fm, width), lines


def test_empty_text_produces_no_lines(fm):
    assert _wrap_io_text("", fm, 100.0) == []


def test_an_impossibly_narrow_box_still_returns_something(fm):
    """Zero lines would draw nothing at all, which is worse than one
    over-wide line the bottom-edge guard already handles."""
    assert _wrap_io_text("SYS.READY", fm, 1.0)


# --- the block keeps its own outline -----------------------------------------

def test_the_renderer_keeps_every_line_inside_the_block(app):
    """The rule the old docstring protects: nothing drawn past the
    block's bottom edge, however long the text is."""
    from PySide6.QtGui import QPainter, QPixmap

    from shared.logic.blocks import register_builtin_blocks
    from shared.logic.blocks.registry import BlockRegistry
    from logic_studio.ui.canvas.block_item import BlockItem

    register_builtin_blocks()
    block = BlockRegistry.create_block("virtual.input")
    block.properties["Bit"] = "SYS.ACCESS_ENGINEER"
    item = BlockItem(block)

    drawn = []
    pixmap = QPixmap(400, 400)
    painter = QPainter(pixmap)
    original = painter.drawText

    def _spy(rect, flags, text):
        drawn.append((rect.y() + rect.height(), text))
        return original(rect, flags, text)

    painter.drawText = _spy
    try:
        item._draw_io_text_lines(painter, [("SYS.ACCESS_ENGINEER", True)], "input")
    finally:
        painter.end()

    assert drawn, "nothing was drawn at all"
    for bottom, text in drawn:
        assert bottom <= item.height, f"{text!r} drawn past the block's bottom edge"


def test_a_long_name_now_reaches_the_block_in_more_than_one_piece(app):
    """The user-visible half of the change: the name arrives wrapped
    instead of as a single ellipsis'd line."""
    from PySide6.QtGui import QPainter, QPixmap

    from shared.logic.blocks import register_builtin_blocks
    from shared.logic.blocks.registry import BlockRegistry
    from logic_studio.ui.canvas.block_item import BlockItem

    register_builtin_blocks()
    block = BlockRegistry.create_block("virtual.input")
    item = BlockItem(block)

    pieces = []
    pixmap = QPixmap(400, 400)
    painter = QPainter(pixmap)
    original = painter.drawText

    def _spy(rect, flags, text):
        pieces.append(text)
        return original(rect, flags, text)

    painter.drawText = _spy
    try:
        item._draw_io_text_lines(painter, [("SYS.ACCESS_ENGINEER", True)], "input")
    finally:
        painter.end()

    assert len(pieces) > 1, pieces
    assert "ENGINEER" in "".join(pieces), (
        "the part that says which signal it is was still lost")
