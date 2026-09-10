"""EPW Studio - one window, one project tree, one editor area.

Task ("EPW Studio, powloka"): Synoptic and Logic Studio stop being two
separate programs launched by two separate commands. This is the
common entry point; studio/synoptic/main.py and studio/logic/main.py
still work exactly as before (GRANICE: "stare punkty wejscia zostaja") -
this is an addition, not a replacement.

Usage:
    python studio/main.py          (from the repo root)
    python main.py                 (from inside studio/)
Both work - the sys.path setup below is based on this file's own
location, not the current working directory.
"""
import sys
from pathlib import Path

STUDIO_DIR = Path(__file__).resolve().parent
REPO_ROOT = STUDIO_DIR.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from studio.shell.main_window import StudioMainWindow
from studio.shell.version import STUDIO_VERSION

# Task "fix/project-format-integrity" point 4.2 - "Dziś Studio nie
# ustawia żadnej ikony - ma domyślną Qt." Derived from runtime/epw_os/
# resources/about_logo.png - see studio/shell/identity/generate_
# identity.py's own module docstring for how and why (a crop of the
# logo's own "EPW" plaque, not a redrawn/invented graphic). Set on both
# the QApplication (taskbar grouping/defaults on some platforms) and
# the window itself (title bar/alt-tab) - belt and suspenders, the same
# reasoning logic_studio.app.apply_classic_style() being called from
# multiple entry points already established for a skin.
APP_ICON_PATH = STUDIO_DIR / "shell" / "identity" / "app_icon.ico"


def _apply_studio_skin(app: QApplication) -> None:
    """Task "EPW Studio: jedna szata graficzna" 2.3 - the WHOLE shell
    (tree, splitter, shared toolbar, menu, status bar) must already be
    in the Win98 skin the moment the window appears, not just once the
    user happens to open LOGIC first. logic_studio.app.apply_classic_style
    is the one already-existing, already-tested implementation of that
    skin (STUDIO_UI_STANDARD.md's palette matches it almost exactly -
    see the standard's own reconciliation notes) - reused here rather
    than duplicated, same reasoning as logic_panel.py reusing it for the
    embedded MainWindow. Calling it again from LogicPanel.__init__ later
    is a harmless no-op re-apply, kept there defensively for any code
    path that constructs a LogicPanel without going through this file."""
    from studio.shell.logic_panel import _ensure_logic_studio_importable
    _ensure_logic_studio_importable()
    from logic_studio.app import apply_classic_style
    apply_classic_style(app)


def _show_splash(app: QApplication):
    """Task point 4.4 (optional, "jeśli starczy czasu") - logo + name +
    version, visible only for however long StudioMainWindow itself
    takes to construct (Logic/Synoptic panels are lazy - see
    main_window.py - so this is normally under a second; it's not
    covering up a slow load, just naming what's on screen for the
    instant before the real window replaces it)."""
    logo_path = STUDIO_DIR / "shell" / "identity" / "app_icon_256.png"
    if not logo_path.exists():
        return None
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QPainter

    logo_size, logo_top = 160, 16
    title_height, version_height, bottom_pad = 28, 22, 14
    canvas_width = 320
    canvas_height = logo_top + logo_size + title_height + version_height + bottom_pad

    pixmap = QPixmap(str(logo_path)).scaled(
        logo_size, logo_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
    )
    canvas = QPixmap(canvas_width, canvas_height)
    canvas.fill(QColor("#D4D0C8"))  # STUDIO_UI_STANDARD.md's own panel_bg
    painter = QPainter(canvas)
    painter.drawPixmap((canvas_width - pixmap.width()) // 2, logo_top, pixmap)

    title_rect = QRect(0, logo_top + logo_size, canvas_width, title_height)
    version_rect = QRect(0, title_rect.bottom(), canvas_width, version_height)

    painter.setPen(QColor("#000000"))
    font = painter.font()
    font.setBold(True)
    font.setPointSize(12)
    painter.setFont(font)
    painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, "EPW Studio")
    font.setBold(False)
    font.setPointSize(9)
    painter.setFont(font)
    painter.drawText(version_rect, Qt.AlignmentFlag.AlignCenter, f"wersja {STUDIO_VERSION} — BroniszLabs")
    painter.end()

    splash = QSplashScreen(canvas)
    splash.show()
    app.processEvents()
    return splash


def main():
    app = QApplication(sys.argv)
    _apply_studio_skin(app)
    if APP_ICON_PATH.exists():
        app_icon = QIcon(str(APP_ICON_PATH))
        app.setWindowIcon(app_icon)
    splash = _show_splash(app)
    window = StudioMainWindow()
    if APP_ICON_PATH.exists():
        window.setWindowIcon(app_icon)
    window.show()
    if splash is not None:
        splash.finish(window)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
