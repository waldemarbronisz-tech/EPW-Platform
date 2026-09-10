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


def main():
    app = QApplication(sys.argv)
    window = StudioMainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
