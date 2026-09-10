"""Embeds EPW Logic Studio's own main view inside the EPW Studio
shell's editor area.

Logic Studio is, today, a standalone app whose entry point
(studio/logic/main.py -> logic_studio.app.main()) constructs its own
QApplication (LogicStudioApp) and shows its own MainWindow as a
top-level window. Only one QApplication may exist per process, so the
shell cannot go through main()/LogicStudioApp - instead this reuses the
two pieces that ARE separable without rewriting anything (Task 2.3:
"zrob to minimalnie, bez przebudowy Logic Studio"):

  - logic_studio.app.apply_classic_style(app) - the classic Win98/NT
    style+palette+QSS LogicStudioApp.__init__ used to apply to itself
    inline. Extracted into its own function (studio/logic/logic_studio/
    app.py) so the shell's own QApplication can look identical without
    a second QApplication - the ONE change made to Logic Studio's own
    code for this task, behavior-preserving (its own test suite passes
    unchanged after the extraction - see the commit).
  - logic_studio.ui.main_window.MainWindow - already a plain QMainWindow
    class, constructible on its own and embeddable as a child widget
    exactly as-is. No change needed here at all.

studio/logic/main.py itself is untouched and still launches Logic
Studio standalone exactly as before.
"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout

LOGIC_DIR = Path(__file__).resolve().parents[1] / "logic"

_blocks_registered = False


def _ensure_logic_studio_importable():
    """logic_studio is a real package (has __init__.py) but studio/logic/
    - the directory containing it - is not on sys.path by default, since
    nothing put it there (the shell lives in studio/, a sibling
    directory, not a parent of studio/logic/)."""
    path_str = str(LOGIC_DIR)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


class LogicPanel(QWidget):
    """One widget: Logic Studio's real MainWindow, embedded. Construction
    is lazy (only happens the first time LOGIKA/LOGIC is actually
    clicked - see main_window.py), same reasoning as SynopticPanel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        _ensure_logic_studio_importable()

        global _blocks_registered
        from logic_studio.blocks import register_builtin_blocks
        if not _blocks_registered:
            register_builtin_blocks()
            _blocks_registered = True

        from logic_studio.app import apply_classic_style
        from PySide6.QtWidgets import QApplication
        apply_classic_style(QApplication.instance())

        from logic_studio.ui.main_window import MainWindow
        # settings=None (the default) intentionally NOT overridden here:
        # this is real usage, not a test - the same QSettings("BroniszLabs",
        # "EPW Logic Studio") the standalone app already reads/writes
        # (tree-expand-state etc.) should carry over into the shell too.
        self._main_window = MainWindow()

        # Task "EPW Studio: jedna szata graficzna" 2.1/2.2 - this
        # embedded MainWindow's own menu bar and its New/Open/Save/Undo/
        # Redo toolbar buttons are replaced by Studio's shared ones
        # (studio/shell/menus.py, main_window.py's shared toolbar) -
        # showing both would mean two menus and two Save buttons, which
        # is the exact problem this task exists to remove. Only THIS
        # embedded instance is affected: logic_studio/ui/main_window.py
        # itself is untouched, so studio/logic/main.py's standalone
        # MainWindow (its own, separate instance) still has its own full
        # menu bar and toolbar exactly as before.
        self._main_window.menuBar().setVisible(False)
        for action in (
            self._main_window.act_new,
            self._main_window.act_open,
            self._main_window.act_save,
            self._main_window.act_undo,
            self._main_window.act_redo,
        ):
            self._main_window.toolbar.removeAction(action)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._main_window)

    def main_window(self):
        return self._main_window
