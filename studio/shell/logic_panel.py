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

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QWidget, QVBoxLayout

LOGIC_DIR = Path(__file__).resolve().parents[1] / "logic"

_blocks_registered = False

# Task "Studio: wyostrzenie stylu" Problem 4.3 - checked empirically
# before writing this (LogicScene.drawBackground()'s own comment):
# Logic Studio has no per-project or per-app canvas-background concept
# at all, unlike Synoptic's real canvasConfig.background project field.
# Reported as its own finding rather than guessed past - the proposal,
# implemented here: since there is nowhere in Logic Studio's OWN project
# format (.epwlogic, core/project.py) to put a per-project color yet,
# this lives in Studio's own QSettings instead - the same store
# StudioMainWindow itself already uses ("BroniszLabs"/"EPW Studio", not
# Logic Studio's separate "BroniszLabs"/"EPW Logic Studio" store), since
# it is a Studio-level UI preference until Logic Studio's project format
# grows a real field for it. Revisit once/if it does - the "per-project"
# vs "per-app" answer would change to match Synoptic's.
_SETTINGS_KEY = "logic/canvas_background"
_DEFAULT_BACKGROUND = "#FFFFFF"


def _load_saved_canvas_background() -> str:
    settings = QSettings("BroniszLabs", "EPW Studio")
    return str(settings.value(_SETTINGS_KEY, _DEFAULT_BACKGROUND))


def _save_canvas_background(hex_color: str) -> None:
    settings = QSettings("BroniszLabs", "EPW Studio")
    settings.setValue(_SETTINGS_KEY, hex_color)


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

    def __init__(self, parent=None, settings=None):
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
        # settings=None (the default) means "real usage" - MainWindow
        # itself then falls back to the real QSettings("BroniszLabs",
        # "EPW Logic Studio") store (tree-expand-state etc.), which
        # should carry over into the shell too. Injectable (unlike
        # before) so a test can pass a scratch QSettings instead, same
        # "settings=None defaults to the real store" pattern
        # StudioMainWindow itself already uses - see
        # [[logic-studio-tests-must-inject-qsettings]].
        self._main_window = MainWindow(settings=settings)

        # Task "EPW Studio: jedna szata graficzna" 2.1/2.2, extended by
        # "Studio: wyostrzenie stylu" Problem 1 - this embedded
        # MainWindow's own menu bar AND its own toolbar are both
        # replaced by Studio's chrome (menus.py's build_fixed_menu() +
        # build_logic_context_toolbar(), main_window.py's shared
        # toolbar) - showing Logic Studio's own copies at the same time
        # is the "pięć pasów, dwa programy sklejone" problem this task
        # exists to remove; every one of this toolbar's own actions
        # (Compile/Simulation/Zoom/Grid/Snap) is already mirrored into
        # build_logic_context_toolbar, so nothing is actually lost by
        # hiding the whole bar rather than pruning it action by action.
        # Only THIS embedded instance is affected: logic_studio/ui/
        # main_window.py itself is untouched, so studio/logic/main.py's
        # standalone MainWindow (its own, separate instance) still has
        # its own full menu bar and toolbar exactly as before.
        self._main_window.menuBar().setVisible(False)
        self._main_window.toolbar.setVisible(False)

        # Problem 4.2/4.3 - restores whatever canvas background color
        # was last picked (Studio's own QSettings, see module docstring
        # above) - a fresh embed looks the same as it did last session,
        # not reset to white every time Studio restarts.
        from PySide6.QtGui import QColor
        self._main_window.scene.background_color = QColor(_load_saved_canvas_background())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._main_window)

    def main_window(self):
        return self._main_window

    def sync_cards_from_studio(self, studio_project) -> None:
        """Task "jedno źródło listy kart": mirrors Studio's real Card list
        (studio/shell/project_format.py's Card - id/kind/channels) into
        the embedded Logic Studio project's `external_cards`, which
        logic_studio.core.device_model.DeviceModel then treats as the
        ONLY source for get_ela_devices()/get_ada_devices()/get_ela_
        addresses()/etc. - see that module's own docstring. Call after
        every Studio project change (main_window.py's own
        _on_project_changed(), cheap - just this list rebuild) AND every
        time the Logic tab is opened (in case it's the very first sync).

        Etap-4 concern (jank switching to Logika): rebuilding
        device_explorer's tree/simulation grid is the EXPENSIVE part, not
        this list comparison - only actually triggers that rebuild
        (MainWindow._refresh_project_dependent_panels()) when the
        computed card list is DIFFERENT from what was already set, not on
        every unrelated project edit (point renamed, metadata changed,
        ...) that leaves project.cards itself untouched."""
        new_cards = [
            {"id": c.id, "kind": c.kind, "channels": c.channels}
            for c in studio_project.cards
        ]
        project = self._main_window.project
        if project.external_cards == new_cards:
            return
        project.external_cards = new_cards
        self._main_window._refresh_project_dependent_panels()

    def canvas_background(self) -> str:
        """Current canvas background color, "#RRGGBB" - the picker's
        own starting color (Problem 4.1's "podgląd: obecny kolor obok
        nowego")."""
        return self._main_window.scene.background_color.name()

    def set_canvas_background(self, hex_color: str) -> None:
        """The write half - updates the real scene property, repaints,
        marks the document dirty (same as any other edit reaching
        LogicScene would), and persists to Studio's own QSettings."""
        from PySide6.QtGui import QColor
        self._main_window.scene.background_color = QColor(hex_color)
        self._main_window.scene.update()
        self._main_window.set_dirty()
        _save_canvas_background(hex_color)
