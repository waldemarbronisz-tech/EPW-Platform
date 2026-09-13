"""One icon look everywhere in EPW Studio.

Logic Studio's action icons come from the Studio shell's icon set when it is
present, pixel for pixel, so the three parts of Studio show the same
pictures; the Format toolbar uses the same text-formatting pictograms.
"""
import os

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

SHELL_ICONS = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "shell", "icons"))


def _app():
    return QApplication.instance() or QApplication([])


def _same(image_a, image_b):
    a = image_a.convertToFormat(QImage.Format_ARGB32)
    b = image_b.convertToFormat(QImage.Format_ARGB32)
    return all(a.pixelColor(x, y).rgba() == b.pixelColor(x, y).rgba() for x in range(16) for y in range(16))


def test_logic_action_icons_are_the_studio_icons():
    _app()
    from logic_studio.ui.icons import action_icon

    for name, png in (("new", "new"), ("save", "save"), ("undo", "undo"), ("compile", "compile"),
                      ("start", "sim_start"), ("pause", "sim_pause"), ("stop", "sim_stop")):
        path = os.path.join(SHELL_ICONS, png + ".png")
        assert os.path.isfile(path), path
        rendered = action_icon(name, 16).pixmap(16, 16).toImage()
        assert _same(rendered, QImage(path)), name


def test_format_toolbar_uses_the_text_formatting_pictograms():
    _app()
    from logic_studio.ui.main_window import MainWindow

    toolbar = MainWindow().format_toolbar
    for action in (toolbar.act_bold, toolbar.act_italic, toolbar.act_underline, *toolbar.align_actions.values()):
        assert not action.icon().isNull(), action.toolTip()
    for name in ("text_bold", "text_italic", "text_underline", "text_align_left",
                 "text_align_center", "text_align_right", "text_align_justify"):
        assert os.path.isfile(os.path.join(SHELL_ICONS, name + ".png")), name
