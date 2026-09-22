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

from studio.shell.logic_path import LOGIC_DIR, ensure_importable

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


def _point_kind(address: str):
    """"ELA1.AI.3" -> "AI"; None for anything that is not a well-formed
    point address. Goes through the platform's one address grammar
    (shared/addressing.py) rather than splitting the string here."""
    from shared.addressing import try_parse_address
    parsed = try_parse_address(address)
    return parsed[1] if parsed else None


class LogicPanel(QWidget):
    """One widget: Logic Studio's real MainWindow, embedded. Construction
    is lazy (only happens the first time LOGIKA/LOGIC is actually
    clicked - see main_window.py), same reasoning as SynopticPanel."""

    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        ensure_importable()

        global _blocks_registered
        from shared.logic.blocks import register_builtin_blocks
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
        (studio/shell/project_format.py's Card - id/model/channel_kinds)
        into the embedded Logic Studio project's `external_cards`, which
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
        # A Studio Card can now have more than one channel kind (task
        # follow-up, user report: "karta ELA1 ma DI oraz AI") - flattened
        # to one {"id","kind","channels"} entry per kind here, since
        # DeviceModel's own get_ela_device_channels()/get_ada_device_
        # channels() (and the "ELA"/"ADA" split beneath them) already
        # expect exactly that flat, one-kind-per-entry shape.
        new_cards = [
            {"id": c.id, "kind": kind, "channels": channels}
            for c in studio_project.cards
            for kind, channels in c.channel_kinds.items()
        ]
        # The analog half of the same mirror. A card's AI/AO channels are
        # already in new_cards above, but a DI/DO channel is fully
        # described by its address while an ANALOG one also needs its
        # engineering range and unit - which live on Studio's own points,
        # not on the card. Without this, an embedded Logic Studio had no
        # analog addresses at all (every AI/AO block's Address dropdown
        # was empty in Studio, whatever the cards said), and the compiler
        # had no range to resolve for an AI block's quality check.
        new_analog_points = [
            {
                "address": point.address,
                "name": point.description or "",
                "unit": point.unit or "",
                "min": point.eng_min,
                "max": point.eng_max,
                "direction": "input" if _point_kind(point.address) == "AI" else "output",
            }
            for point in studio_project.points
            if _point_kind(point.address) in ("AI", "AO")
        ]

        # feat/signal-register §3.3: the alarm system's zones and lines,
        # for the same reason and by the same route as the cards above.
        # The catalog holds SEC.ZONE.<zone_id>.ARMED as a PATTERN; it can
        # only become SEC.ZONE.PARTER.ARMED if the logic project knows
        # this installation's zones. Only the stable id and the display
        # name travel - the id is what a schematic binds to, the name is
        # what an engineer recognises in the picker.
        new_zones = [{"id": z.id, "name": z.name} for z in studio_project.zones if z.id]
        new_lines = [{"id": l.id, "name": l.name} for l in studio_project.lines if l.id]
        # Signal register etap 5: the process protections, for the
        # catalog's ALM.<alarm_id>.* patterns (one alarm per protection
        # the controller computes) - the same route as the zones.
        new_protections = [{"id": pp.id, "name": pp.name}
                           for pp in getattr(studio_project, "process_protections", []) if pp.id]

        project = self._main_window.project
        if (project.external_cards == new_cards
                and project.external_analog_points == new_analog_points
                and getattr(project, "external_zones", None) == new_zones
                and getattr(project, "external_lines", None) == new_lines
                and getattr(project, "external_process_protections", None) == new_protections):
            return
        project.external_cards = new_cards
        project.external_analog_points = new_analog_points
        project.external_zones = new_zones
        project.external_lines = new_lines
        project.external_process_protections = new_protections
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

    # -- the whole document in and out (task "Studio osadza ekrany i
    # logikę w projekt.epw") ---------------------------------------------
    # User report: "podejrzewam że to samo jest z logiką - dalej to
    # traktowane jest jako osobne programy". The logic lives INSIDE
    # projekt.epw now (shared/project_format.py's Project.logic /
    # logic_runtime); Studio's own Save/Open go through these.

    def document(self) -> dict:
        """The EPW_LOGIC document (blocks, wires, settings) as saved."""
        return self._main_window.project.serialize()

    def runtime_document(self):
        """The compiled EPW_RUNTIME_LOGIC document, or None when the
        project does not compile - Studio keeps the previous compiled
        document in that case and says so."""
        return self._main_window.export_runtime_data()

    def load_document(self, data: dict) -> None:
        """Opens `data` (the project's `logic` section; {} = fresh
        project). Raises what Project.deserialize() raises."""
        self._main_window.load_project_data(data)

    def is_dirty(self) -> bool:
        return bool(self._main_window.is_dirty)

    def mark_saved(self) -> None:
        self._main_window.is_dirty = False
        self._main_window.update_title()
