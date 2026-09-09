"""Persist the main window's last size and maximized state between runs.

Stored in ``epw_os/config/window_state.local.json`` - a machine-local file
(gitignored), NOT the project file: window geometry is a per-workstation
preference, not part of the substation project. Path is anchored to this
file's location, not the process CWD, for the same reason AccessManager's
config path is (see its docstring).
"""

import json
import os

from epw_os.core.logging import log

_STATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "window_state.local.json",
)

# Sensible startup size = the original fixed panel resolution.
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 600
# Below this the nav panel + a data table stop fitting side by side.
MIN_WIDTH = 900
MIN_HEIGHT = 550


def _load_raw() -> dict:
    try:
        with open(_STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Routine, expected: no window state has ever been saved yet
        # (first run) - every load_*() below already has a sensible
        # default for this. Not logged - it's the normal first-launch
        # state, not a problem.
        return {}
    except (OSError, ValueError, TypeError) as e:
        # The file EXISTS but is unreadable/corrupt - unlike a missing
        # file above, this is an actual problem (disk error, a bad
        # hand-edit) silently reverting every window/keyboard/theme
        # preference to defaults with no other trace - same "polykane
        # wyjatki" pattern as System.Mode. _save_raw() below already logs
        # its own write failures; this is the matching read-side log.
        log.warning(f"Could not read window state from {_STATE_PATH} - using defaults: {e}")
        return {}


def _save_raw(data: dict):
    """Best-effort write; a failure here must never block app shutdown."""
    try:
        os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
        with open(_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        log.warning(f"Could not persist window state to {_STATE_PATH}: {e}")


def load() -> dict:
    """Return {"width", "height", "maximized"}. Any problem -> defaults.
    Every per-field type-coercion fallback in this module (here and in
    load_screen_sleep_minutes()/load_keyboard_enabled()/
    load_keyboard_geometry() below) is deliberately NOT individually
    logged - _load_raw()'s own logging above already covers the one
    meaningful root cause (a corrupt/unreadable file); a wrong-typed
    individual field within an otherwise-valid file is low-stakes
    (window size/keyboard visibility/position, never project data) and
    self-healing, so logging every such field separately would just add
    noise on top of that one useful signal."""
    data = _load_raw()
    try:
        width = int(data.get("width", DEFAULT_WIDTH))
        height = int(data.get("height", DEFAULT_HEIGHT))
        maximized = bool(data.get("maximized", False))
    except (ValueError, TypeError):
        return {"width": DEFAULT_WIDTH, "height": DEFAULT_HEIGHT, "maximized": False}

    # Guard against a corrupt/tiny persisted size making the window unusable.
    width = max(width, MIN_WIDTH)
    height = max(height, MIN_HEIGHT)
    return {"width": width, "height": height, "maximized": maximized}


def save(width: int, height: int, maximized: bool):
    # Merge onto whatever else is already in the file (e.g.
    # screen_sleep_minutes below) instead of clobbering it - both
    # load()/save() and load_screen_sleep_minutes()/save_screen_sleep_minutes()
    # share this one machine-local file.
    data = _load_raw()
    data.update({"width": int(width), "height": int(height), "maximized": bool(maximized)})
    _save_raw(data)


# Screen sleep (Task: blank the screen after idle time, distinct from the
# 5-minute access-level auto-logout - purely a display/kiosk behavior,
# same "machine-local, not project data" reasoning as window geometry
# above, not the operator's PIN/access session).
DEFAULT_SCREEN_SLEEP_MINUTES = 2
SCREEN_SLEEP_DISABLED = 0  # 0 minutes = never blank the screen


def load_screen_sleep_minutes() -> int:
    data = _load_raw()
    try:
        return max(0, int(data.get("screen_sleep_minutes", DEFAULT_SCREEN_SLEEP_MINUTES)))
    except (ValueError, TypeError):
        return DEFAULT_SCREEN_SLEEP_MINUTES


def save_screen_sleep_minutes(minutes: int):
    data = _load_raw()
    data["screen_sleep_minutes"] = max(0, int(minutes))
    _save_raw(data)


# On-screen keyboard (Task: touch input without a physical keyboard).
# Same "machine-local, not project data" reasoning as everything else in
# this file - whether a workstation has a physical keyboard is a trait
# of that workstation, not of the substation project.
def load_keyboard_enabled(kiosk_default: bool = False) -> bool:
    """Once the operator has explicitly picked anything in Settings, that
    choice is respected on every later launch - including a later launch
    with a different --kiosk value. Only when nothing has EVER been
    explicitly saved does `kiosk_default` apply (True when this launch
    passed --kiosk, False otherwise - see main.py): a dev machine with a
    physical keyboard should not have this in the way by default, but a
    freshly-imaged kiosk device should not need a Settings trip on day
    one either."""
    data = _load_raw()
    if "keyboard_enabled" in data:
        try:
            return bool(data["keyboard_enabled"])
        except (ValueError, TypeError):
            pass
    return bool(kiosk_default)


def save_keyboard_enabled(enabled: bool):
    data = _load_raw()
    data["keyboard_enabled"] = bool(enabled)
    _save_raw(data)


# On-screen keyboard window geometry (Task: rebuild the keyboard as a
# floating, draggable/resizable window - position/size remembered between
# runs, same "machine-local, not project data" pattern and the same
# load()/save() shape as the main window's own geometry above.  x/y are
# None until the operator has actually moved the window at least once -
# the caller picks a sensible default position for a first-ever run
# instead of this module inventing one (it doesn't know screen geometry).
DEFAULT_KEYBOARD_WIDTH = 420
DEFAULT_KEYBOARD_HEIGHT = 260
# Deliberately not tied to MIN_WIDTH/MIN_HEIGHT above (a different
# window) - small enough to tuck in a corner, large enough that
# on_screen_keyboard.py's own ~10mm-per-key floor still fits inside it.
MIN_KEYBOARD_WIDTH = 260
MIN_KEYBOARD_HEIGHT = 160


def load_keyboard_geometry() -> dict:
    """Return {"x", "y", "width", "height"} - x/y are None if the operator
    has never moved the keyboard (caller should pick a default position);
    width/height always have a usable value (defaults if never resized)."""
    data = _load_raw()
    geo = data.get("keyboard_geometry")
    if not isinstance(geo, dict):
        geo = {}
    try:
        width = max(int(geo.get("width", DEFAULT_KEYBOARD_WIDTH)), MIN_KEYBOARD_WIDTH)
        height = max(int(geo.get("height", DEFAULT_KEYBOARD_HEIGHT)), MIN_KEYBOARD_HEIGHT)
    except (ValueError, TypeError):
        width, height = DEFAULT_KEYBOARD_WIDTH, DEFAULT_KEYBOARD_HEIGHT
    x, y = geo.get("x"), geo.get("y")
    try:
        x = int(x) if x is not None else None
        y = int(y) if y is not None else None
    except (ValueError, TypeError):
        x = y = None
    return {"x": x, "y": y, "width": width, "height": height}


def save_keyboard_geometry(x: int, y: int, width: int, height: int):
    data = _load_raw()
    data["keyboard_geometry"] = {
        "x": int(x), "y": int(y),
        "width": max(int(width), MIN_KEYBOARD_WIDTH),
        "height": max(int(height), MIN_KEYBOARD_HEIGHT),
    }
    _save_raw(data)


# Recent projects (Task: Project menu > "Recently opened"). Same
# "machine-local, not project data" reasoning as everything else in this
# file - which project FILES someone has opened on THIS workstation is a
# trait of the workstation, not something that belongs inside any one of
# those project files.
MAX_RECENT_PROJECTS = 10


def load_recent_projects() -> list:
    """Up to MAX_RECENT_PROJECTS most-recently-opened project file paths,
    newest first. Any malformed entry (wrong type, or the whole key
    holding something other than a list) is dropped rather than raising -
    same defensive stance as every other load_*() in this file."""
    data = _load_raw()
    paths = data.get("recent_projects", [])
    if not isinstance(paths, list):
        return []
    return [p for p in paths if isinstance(p, str)][:MAX_RECENT_PROJECTS]


def add_recent_project(path: str):
    """Moves `path` to the front (most recent) if it's already in the
    list, otherwise inserts it there - then trims to
    MAX_RECENT_PROJECTS. Called after a successful Open/Save As/"Recently
    opened" click (see main_window.py) - never for a project that failed
    to load, and never just because the app started up with whatever was
    already the active project file."""
    data = _load_raw()
    paths = data.get("recent_projects", [])
    if not isinstance(paths, list):
        paths = []
    paths = [p for p in paths if isinstance(p, str) and p != path]
    paths.insert(0, path)
    data["recent_projects"] = paths[:MAX_RECENT_PROJECTS]
    _save_raw(data)


def clear_recent_projects():
    data = _load_raw()
    data["recent_projects"] = []
    _save_raw(data)


# Visual theme (Task: przelaczane motywy wizualne). Same "machine-local,
# not project data" reasoning as everything else in this file - which
# theme looks right on THIS screen (e.g. High Contrast for a cabinet in
# direct sunlight) is a trait of the workstation, not the substation
# project. Stored as the theme's stable numeric index (epw_os/core/
# themes.py) - the same value the "System.Theme" tag uses (see
# epw_os/gui/theme_manager.py), so a restart re-applies exactly what was
# active before, through the identical code path a menu change or a tag
# write already use (ThemeManager.apply_index()).
def load_theme_index() -> int:
    from epw_os.core.themes import DEFAULT_THEME_INDEX, clamp_index
    data = _load_raw()
    index = clamp_index(data.get("theme_index"))
    return DEFAULT_THEME_INDEX if index is None else index


def save_theme_index(index: int):
    data = _load_raw()
    data["theme_index"] = int(index)
    _save_raw(data)


# Theme work MODE (Task 4, page-split branch: "tryb pracy" - MOTYW STALY
# vs AUTOMATYCZNY DZIEN/NOC). Same "machine-local, not project data"
# reasoning as theme_index above - which schedule/pair of themes suits
# THIS screen's environment is a workstation trait, not a substation
# project setting. GRANICE: "Nie zmieniaj samych motywow... Nie usuwaj
# sterowania motywem przez tag" - this section is purely ADDITIVE to
# theme_index, which keeps meaning exactly what it always did (the
# currently-applied theme, however it got there - a menu pick, a tag
# write, or an automatic day/night switch).
THEME_MODE_CONSTANT = "constant"
THEME_MODE_AUTO = "auto"
DEFAULT_DAY_START = "06:00"
DEFAULT_NIGHT_START = "20:00"


def is_valid_hhmm(value) -> bool:
    if not isinstance(value, str) or len(value) != 5 or value[2] != ":":
        return False
    try:
        hh, mm = int(value[:2]), int(value[3:])
    except ValueError:
        return False
    return 0 <= hh <= 23 and 0 <= mm <= 59


def load_theme_mode_config() -> dict:
    """{"mode": "constant"|"auto", "day_index", "night_index" (theme
    indices - epw_os/core/themes.py), "day_start", "night_start"
    ("HH:MM")}. Missing/corrupt -> defaults that reproduce today's
    exact behavior (mode=constant, so day/night fields are simply
    unused) - GRANICE: "zachowanie jak dzis" for any project that
    predates this feature."""
    from epw_os.core.themes import DEFAULT_THEME_INDEX, clamp_index
    data = _load_raw()
    raw = data.get("theme_mode", {})
    if not isinstance(raw, dict):
        raw = {}
    mode = raw.get("mode")
    if mode not in (THEME_MODE_CONSTANT, THEME_MODE_AUTO):
        mode = THEME_MODE_CONSTANT
    day_index = clamp_index(raw.get("day_index"))
    night_index = clamp_index(raw.get("night_index"))
    day_start = raw.get("day_start")
    if not is_valid_hhmm(day_start):
        day_start = DEFAULT_DAY_START
    night_start = raw.get("night_start")
    if not is_valid_hhmm(night_start):
        night_start = DEFAULT_NIGHT_START
    return {
        "mode": mode,
        "day_index": day_index if day_index is not None else DEFAULT_THEME_INDEX,
        # Night theme's own sensible default is "night" (index 1) if
        # never configured - matching what the name literally says,
        # not just "whatever the constant default theme is".
        "night_index": night_index if night_index is not None else 1,
        "day_start": day_start,
        "night_start": night_start,
    }


def save_theme_mode_config(config: dict):
    data = _load_raw()
    data["theme_mode"] = dict(config)
    _save_raw(data)


# Navigation tree expand/collapse state (Task: "stan rozwiniecia
# zapamietywany miedzy uruchomieniami (wzorzec window_state.py)"). Same
# "machine-local, not project data" reasoning as everything else here -
# which groups an operator likes left open on THIS screen is a
# workstation preference, not part of the substation project. Keyed by
# group id (epw_os.core.nav_model's own group_id strings, e.g.
# "control_group") so a group's remembered state survives even if
# groups are reordered later (Task 5's own "kolejnosc... uczynic
# edytowalna" forward-looking note) - a numeric index would not.
def load_nav_tree_expanded() -> dict:
    """{group_id: bool}. A group id missing from the result (never
    saved before) is left for the caller to default (nav_tree.py
    defaults an unknown group to expanded, so a first-ever run - or a
    brand new group added by a later version - shows everything open,
    not mysteriously collapsed)."""
    data = _load_raw()
    raw = data.get("nav_tree_expanded", {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): bool(v) for k, v in raw.items()}


def save_nav_tree_expanded(expanded: dict):
    data = _load_raw()
    data["nav_tree_expanded"] = {str(k): bool(v) for k, v in expanded.items()}
    _save_raw(data)
