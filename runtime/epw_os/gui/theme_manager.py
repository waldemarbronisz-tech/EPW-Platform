"""The GUI-side visual-theme singleton (Task: przelaczane motywy
wizualne, sterowanie motywem z logiki).

Palette DATA and the state-color distinguishability check live in
epw_os/core/themes.py (headless, pytest-testable without a QApplication -
same "headless core + thin GUI wrapper" split as help_content.py/
help_window.py). This module is the thin Qt wrapper: a single
process-wide instance (get_theme_manager()) that

  - holds the currently active theme index,
  - emits theme_changed(index) so any widget anywhere can repaint live
    without MainWindow having to know about it individually,
  - persists the choice (epw_os/gui/window_state.py) so it survives a
    restart,
  - keeps the Settings-menu choice and the "System.Theme" TagManager tag
    in sync in both directions (Task 4 - "sterowanie motywem z logiki"):
    a menu pick writes the tag, and a tag write (from logic, or from
    anywhere else) applies the theme exactly like a menu pick would.

Any widget that wants to react to a theme change does:

    from epw_os.gui.theme_manager import get_theme_manager
    get_theme_manager().theme_changed.connect(self._on_theme_changed)

and reads epw_os.core.themes.get_theme(get_theme_manager().current_index())
(or the convenience current_colors() below) whenever it (re)paints.
"""

from datetime import datetime, time as dt_time

from PySide6.QtCore import QObject, QTimer, Signal

from epw_os.core import themes
from epw_os.core.logging import log
from epw_os.gui import window_state
from epw_os.gui.window_state import THEME_MODE_CONSTANT, THEME_MODE_AUTO

# The tag's name and shape are a Task-4 design decision, justified in
# SESSION_REPORT.md: ONE writable INT tag holding the theme's numeric
# index (0=Industrial..4=SimCity 2000) - not a bit-per-theme set. A
# single value has no "which bit wins if two are set" ambiguity to
# invent and document, and remains trivial to drive even from
# bit-oriented logic (setting one register to a literal is a single,
# universal instruction - no less "simple bit logic" than flipping a
# coil). See epw_os.core.themes.clamp_index() for how an invalid write
# is handled: ignored, never applied, never crashes.
THEME_TAG_NAME = "System.Theme"


class ThemeManager(QObject):
    theme_changed = Signal(int)

    def __init__(self):
        super().__init__()
        self._index = window_state.load_theme_index()
        self._tag_manager = None

        # --- work mode (Task 4, page-split branch): MOTYW STALY (today's
        # exact behavior, unchanged) vs AUTOMATYCZNY DZIEN/NOC ----------
        mode_cfg = window_state.load_theme_mode_config()
        self._mode = mode_cfg["mode"]
        self._day_index = mode_cfg["day_index"]
        self._night_index = mode_cfg["night_index"]
        self._day_start = mode_cfg["day_start"]
        self._night_start = mode_cfg["night_start"]
        # Task: "zapis do tagu System.Theme z logiki MA MIEC PIERWSZENSTWO
        # nad trybem automatycznym... az do nastepnej zmiany trybu przez
        # uzytkownika w Ustawieniach" - set the instant a genuine EXTERNAL
        # tag write actually changes the applied theme (see
        # _on_tag_changed() below), cleared only by set_mode() (the
        # Settings dialog's own Save path - see its own docstring for why
        # that, and only that, counts as "the next mode change").
        self._logic_override_active = False

        # Checked periodically rather than with a precise "sleep until
        # the next boundary" timer - simpler, and being off by up to 30s
        # at a day/night transition is irrelevant for a visual theme.
        self._auto_timer = QTimer(self)
        self._auto_timer.timeout.connect(self._check_auto_switch)
        self._auto_timer.start(30_000)
        # Apply immediately at startup if already in auto mode - don't
        # wait for the first 30s tick to show the theme actually correct
        # for right now (the persisted theme_index could be stale from
        # whenever the program last ran).
        self._check_auto_switch()

    # --- reading the active theme ---------------------------------

    def current_index(self) -> int:
        return self._index

    def current_colors(self) -> dict:
        return themes.get_theme(self._index)["colors"]

    def current_theme(self) -> dict:
        return themes.get_theme(self._index)

    # --- TagManager binding (Task 4) --------------------------------

    def bind_tag_manager(self, tag_manager):
        """Called once by MainWindow right after it has a live
        tag_manager. Registers this manager as the tag's writer/reader
        and pushes the persisted (or default) theme onto the tag so it
        reflects the truth from the very first read - the exact same
        code path apply_index() uses for a menu pick or a later logic
        write, so "restore on startup" needs no special-cased logic of
        its own."""
        self._tag_manager = tag_manager
        tag_manager.tag_changed.connect(self._on_tag_changed)
        self._push_to_tag()

    def _on_tag_changed(self, name, value, quality):
        if name != THEME_TAG_NAME:
            return
        index = themes.clamp_index(value)
        if index is None:
            log.warning(
                f"Ignoring invalid {THEME_TAG_NAME} write ({value!r}) - "
                f"keeping theme {self._index} ({themes.get_theme(self._index)['id']})."
            )
            return
        # Task 4: a write that actually CHANGES the applied theme, seen
        # here (i.e. NOT our own _push_to_tag() echoing back whatever
        # self._index already is - that path never reaches this branch,
        # since by the time its own echo arrives self._index has already
        # been updated to match) is, by construction, a genuine EXTERNAL
        # write - from logic, or any other tool driving this tag - and
        # takes priority over automatic day/night switching from this
        # point on. apply_index()/set_mode()'s own internal changes
        # (a menu pick, or the auto-switch itself) never take this path.
        if index != self._index:
            self._logic_override_active = True
        self._apply(index, push_to_tag=False)

    # --- applying a theme --------------------------------------------

    def apply_index(self, index: int):
        """The menu-driven path (Settings > Theme...) - also the one a
        test or another caller uses directly. Not access-gated (GRANICE:
        "zmiana z menu: dowolny poziom") - callers decide their own UI,
        this method itself never checks access_manager."""
        clamped = themes.clamp_index(index)
        if clamped is None:
            log.warning(f"Ignoring invalid theme index {index!r} from apply_index().")
            return
        self._apply(clamped, push_to_tag=True)

    def _apply(self, index: int, push_to_tag: bool):
        if index == self._index:
            # Still push once even when unchanged, so a fresh bind (or a
            # redundant menu click) leaves the tag correctly seeded
            # without ever re-emitting theme_changed for a no-op change.
            if push_to_tag:
                self._push_to_tag()
            return
        self._index = index
        window_state.save_theme_index(index)
        if push_to_tag:
            self._push_to_tag()
        self.theme_changed.emit(index)

    def _push_to_tag(self):
        if self._tag_manager is None:
            return
        # Defensive, not just tidy: a test/tool may hand this a
        # tag_manager stand-in with no update_tag() at all, or a real one
        # where "System.Theme" hasn't been registered (add_tag() raises
        # ValueError via TagManager._apply_update()'s "Unknown tag" path)
        # - the theme itself must keep working (and the app must keep
        # constructing) either way. Task's own "never require this to
        # work for the visual feature to work" spirit, same as
        # HelpContentStore/AboutDialog's missing-file handling elsewhere
        # in this codebase.
        try:
            self._tag_manager.update_tag(THEME_TAG_NAME, self._index)
        except (AttributeError, ValueError) as e:
            log.warning(f"Could not sync {THEME_TAG_NAME} tag: {e}")

    # --- work mode: MOTYW STALY vs AUTOMATYCZNY DZIEN/NOC (Task 4) -----

    def get_mode(self) -> str:
        return self._mode

    def get_day_index(self) -> int:
        return self._day_index

    def get_night_index(self) -> int:
        return self._night_index

    def get_day_start(self) -> str:
        return self._day_start

    def get_night_start(self) -> str:
        return self._night_start

    def is_logic_override_active(self) -> bool:
        """Task 4: "Pokaz w Ustawieniach, gdy motyw jest aktualnie
        narzucony przez logike" - the Settings dialog reads this to show
        that note, so the operator isn't left wondering why AUTOMATYCZNY
        appears configured but isn't actually switching."""
        return self._logic_override_active

    def set_mode(self, mode: str, constant_index: int = None, day_index: int = None,
                 night_index: int = None, day_start: str = None, night_start: str = None):
        """The Settings-dialog "Save" path whenever the work MODE itself
        is involved - entering/adjusting/leaving AUTOMATYCZNY, or
        switching mode back to STALY with a newly chosen theme (Task 4:
        "Zmiana trybu: poziom Engineer, zapis do dziennika audytowego" -
        the CALLER, ThemeDialog, enforces that gate + the audit write,
        same convention apply_index() itself already follows for the
        plain constant-theme pick, which stays "zmiana z menu: dowolny
        poziom" and does NOT go through this method at all - see
        ThemeDialog._apply()). Always counts as "the next mode change"
        (Task: "az do nastepnej zmiany trybu przez uzytkownika w
        Ustawieniach") - clears any active logic override unconditionally,
        even if `mode` ends up equal to what it already was."""
        if mode not in (THEME_MODE_CONSTANT, THEME_MODE_AUTO):
            log.warning(f"Ignoring invalid theme mode {mode!r} from set_mode().")
            return
        if day_index is not None:
            clamped = themes.clamp_index(day_index)
            if clamped is not None:
                self._day_index = clamped
        if night_index is not None:
            clamped = themes.clamp_index(night_index)
            if clamped is not None:
                self._night_index = clamped
        if day_start is not None and window_state.is_valid_hhmm(day_start):
            self._day_start = day_start
        if night_start is not None and window_state.is_valid_hhmm(night_start):
            self._night_start = night_start
        self._mode = mode
        self._logic_override_active = False
        window_state.save_theme_mode_config({
            "mode": self._mode, "day_index": self._day_index, "night_index": self._night_index,
            "day_start": self._day_start, "night_start": self._night_start,
        })
        if mode == THEME_MODE_CONSTANT and constant_index is not None:
            self.apply_index(constant_index)
        elif mode == THEME_MODE_AUTO:
            self._check_auto_switch()
        # mode == CONSTANT with no constant_index given (shouldn't happen
        # from the dialog, which always supplies one): leave whatever
        # theme is currently showing exactly as it is.

    def _is_daytime(self) -> bool:
        now = datetime.now().time()
        day_start = _parse_hhmm(self._day_start)
        night_start = _parse_hhmm(self._night_start)
        if day_start <= night_start:
            return day_start <= now < night_start
        # Day window wraps past midnight (an unusual, but not invalid,
        # configuration - e.g. a night-shift-only site) - "day" is then
        # everything NOT in the [night_start, day_start) night window.
        return not (night_start <= now < day_start)

    def _check_auto_switch(self):
        """Runs on the 30s _auto_timer tick, and once at construction/
        set_mode() so the correct theme applies immediately rather than
        waiting for the next tick. A no-op whenever not in AUTO mode, or
        while a logic override is active (Task 4's own priority rule -
        see _on_tag_changed())."""
        if self._mode != THEME_MODE_AUTO or self._logic_override_active:
            return
        desired = self._day_index if self._is_daytime() else self._night_index
        if desired != self._index:
            self._apply(desired, push_to_tag=True)


def _parse_hhmm(value: str) -> "dt_time":
    hh, mm = int(value[:2]), int(value[3:])
    return dt_time(hh, mm)


_instance = None


def get_theme_manager() -> ThemeManager:
    global _instance
    if _instance is None:
        _instance = ThemeManager()
    return _instance


def current_colors() -> dict:
    """Convenience module-level shortcut for the many small, one-shot
    dialogs that just need "the current theme's colors", without each
    one importing the singleton getter and calling .current_colors()
    itself."""
    return get_theme_manager().current_colors()


def error_text_style(extra: str = "") -> str:
    """Ready-made QSS for a form's inline "that was wrong" message label
    - used across several one-shot dialogs (PIN change, Historian export,
    Project Properties, ...) that used to hardcode "color: red;" (Task 5:
    "zbierz rozproszone ... ustawienia kolorow"). These dialogs are
    rebuilt fresh every time they're opened, so simply reading the
    CURRENT theme here is enough to stay in sync - no theme_changed
    subscription needed for a one-shot dialog."""
    return f"color: {current_colors()['state_alarm']}; {extra}"


def success_text_style(extra: str = "font-weight: bold;") -> str:
    """Same as error_text_style() but for a "that worked" message -
    used to hardcode "color: darkgreen;"."""
    return f"color: {current_colors()['state_ok_text']}; {extra}"


def neutral_text_style(extra: str = "") -> str:
    """Same idea for a plain informational/gated message (neither an
    error nor a success) - used to hardcode "color: gray;"."""
    return f"color: {current_colors()['text_disabled']}; {extra}"


def reset_theme_manager_for_tests():
    """Test-only: drop the singleton so the next get_theme_manager() call
    re-reads window_state (which a test may have just pointed at an
    isolated tmp file) instead of returning a stale instance left over
    from an earlier test."""
    global _instance
    _instance = None
