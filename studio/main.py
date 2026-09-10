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

from PySide6.QtWidgets import QApplication

from studio.shell.main_window import StudioMainWindow


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


def main():
    app = QApplication(sys.argv)
    _apply_studio_skin(app)
    window = StudioMainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
