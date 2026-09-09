"""Central visual-theme definitions (Task: przelaczane motywy wizualne) -
headless (no PyQt import), same rule as every other core/ module, so the
palettes and the state-color distinguishability check are testable
without a QApplication.

A theme is ONLY a set of colors (GRANICE: "Motyw zmienia WYLACZNIE
kolory"). Nothing here changes shapes, border widths, or sizes - that
stays in epw_os/gui/style.py's QSS structure, unchanged across themes.

THEMES is ordered - a theme's position in this list IS its stable
numeric identity (the "System.Theme" tag's value, see
epw_os/gui/theme_manager.py), so entries must never be reordered or
removed, only appended.
"""

# --- the token set --------------------------------------------------
#
# "Chrome" tokens are consumed by epw_os/gui/style.py's QSS template.
# "State" tokens are consumed directly by Python code that paints a
# discrete status (ONLINE/alarm/warning/...) outside the QSS (Task:
# "kolory oznaczajace stan maja pozostac rozroznialne w KAZDYM motywie").
#
# Every theme below must define every one of these keys - enforced by
# test_themes.py, not just left to convention.

CHROME_KEYS = [
    "window_bg", "panel_bg", "field_bg", "text", "text_disabled",
    "bevel_light", "bevel_shadow", "button_shadow", "grid_line",
    "accent_bg", "accent_text", "dialog_border", "spin_pressed_bg",
    "lcd_bg", "lcd_fg",
    "console_bg", "console_text", "console_border",
    "console_header_bg", "console_header_text",
    "tree_group_bg", "tree_item_bg",
]

# The subset of STATE_KEYS that must be mutually distinguishable from
# each other AND from the theme's backgrounds in every theme (Task's
# explicit test requirement) - the ones an operator actually reads as
# "what state is this?" at a glance. state_*_dark/badge/text variants
# and action_danger are still real, used tokens, just not part of this
# specific hard guarantee (they're saturation/contrast variants of the
# same handful of hues, not a 6th/7th independent state).
CORE_STATE_KEYS = ["state_ok", "state_warning", "state_alarm", "state_info", "state_neutral"]

STATE_KEYS = CORE_STATE_KEYS + [
    "state_ok_text", "state_warning_badge", "state_warning_dark",
    "state_caution", "state_alarm_dark", "state_neutral_dark",
    "state_indeterminate", "state_unknown", "action_danger",
]

ALL_KEYS = CHROME_KEYS + STATE_KEYS

DEFAULT_THEME_INDEX = 0


def _theme(theme_id, name_key, colors):
    missing = [k for k in ALL_KEYS if k not in colors]
    if missing:
        raise ValueError(f"theme {theme_id!r} is missing color keys: {missing}")
    return {"id": theme_id, "name_key": name_key, "colors": dict(colors)}


THEMES = [
    # 0 - Industrial: TODAY'S actual look (epw_os/gui/style.py's literal
    # hex values, unchanged) plus every Python-side hardcoded color this
    # task centralized - see SESSION_REPORT.md for the full "moved from"
    # list. HARD REQUIREMENT: must render pixel-identical to the program
    # before this task - verified in test_themes.py by reconstructing the
    # exact pre-task QSS text from this theme's colors.
    _theme("industrial", "theme.industrial", {
        "window_bg": "#C0C0C0", "panel_bg": "#D4D0C8", "field_bg": "#FFFFFF",
        "text": "#000000", "text_disabled": "#808080",
        "bevel_light": "#FFFFFF", "bevel_shadow": "#808080", "button_shadow": "#404040",
        "grid_line": "#808080", "accent_bg": "#000080", "accent_text": "#FFFFFF",
        "dialog_border": "#000000", "spin_pressed_bg": "#A0A0A0",
        "lcd_bg": "#000000", "lcd_fg": "#00FF00",
        "console_bg": "#000080", "console_text": "#00FFFF", "console_border": "#00FFFF",
        "console_header_bg": "#000080", "console_header_text": "#FFFF00",
        "tree_group_bg": "#969696", "tree_item_bg": "#C8C8C8",
        "state_ok": "#00FF00", "state_ok_text": "#008000",
        "state_warning": "#FFFF00", "state_warning_badge": "#FFD700", "state_warning_dark": "#4B4B00",
        "state_caution": "#FFA500",
        "state_alarm": "#FF0000", "state_alarm_dark": "#8B0000",
        "state_info": "#0000FF",
        "state_neutral": "#808080", "state_neutral_dark": "#555555",
        "state_indeterminate": "#808000", "state_unknown": "#FF00FF",
        "action_danger": "#800000",
    }),

    # 1 - Night: dark background, light text, stonowane (muted) accents.
    _theme("night", "theme.night", {
        "window_bg": "#2B2B2B", "panel_bg": "#3C3C3C", "field_bg": "#1E1E1E",
        "text": "#E0E0E0", "text_disabled": "#808080",
        "bevel_light": "#5A5A5A", "bevel_shadow": "#1A1A1A", "button_shadow": "#0D0D0D",
        "grid_line": "#4A4A4A", "accent_bg": "#375A7F", "accent_text": "#FFFFFF",
        "dialog_border": "#000000", "spin_pressed_bg": "#555555",
        "lcd_bg": "#000000", "lcd_fg": "#33FF33",
        "console_bg": "#0D1B2A", "console_text": "#4DD9E8", "console_border": "#4DD9E8",
        "console_header_bg": "#0D1B2A", "console_header_text": "#E8D44D",
        "tree_group_bg": "#4A4A4A", "tree_item_bg": "#383838",
        "state_ok": "#33CC33", "state_ok_text": "#4CAF50",
        "state_warning": "#E0C700", "state_warning_badge": "#D4AF37", "state_warning_dark": "#6B5B00",
        "state_caution": "#CC7A00",
        "state_alarm": "#E63946", "state_alarm_dark": "#7A1F1F",
        "state_info": "#4A90D9",
        "state_neutral": "#888888", "state_neutral_dark": "#4A4A4A",
        "state_indeterminate": "#A69B00", "state_unknown": "#C77DD9",
        "action_danger": "#7A1F1F",
    }),

    # 2 - High Contrast: black background, jaskrawe (vivid) colors - for
    # readability in full sunlight (an outdoor cabinet).
    _theme("high_contrast", "theme.high_contrast", {
        "window_bg": "#000000", "panel_bg": "#1A1A1A", "field_bg": "#000000",
        "text": "#FFFFFF", "text_disabled": "#AAAAAA",
        "bevel_light": "#666666", "bevel_shadow": "#000000", "button_shadow": "#000000",
        "grid_line": "#444444", "accent_bg": "#FFFF00", "accent_text": "#000000",
        "dialog_border": "#FFFFFF", "spin_pressed_bg": "#333333",
        "lcd_bg": "#000000", "lcd_fg": "#00FF00",
        "console_bg": "#000000", "console_text": "#00FFFF", "console_border": "#00FFFF",
        "console_header_bg": "#000000", "console_header_text": "#FFFF00",
        "tree_group_bg": "#333333", "tree_item_bg": "#222222",
        "state_ok": "#00FF00", "state_ok_text": "#00FF00",
        "state_warning": "#FFFF00", "state_warning_badge": "#FFD700", "state_warning_dark": "#806600",
        "state_caution": "#FF9900",
        "state_alarm": "#FF0000", "state_alarm_dark": "#CC0000",
        "state_info": "#00CCFF",
        "state_neutral": "#999999", "state_neutral_dark": "#666666",
        "state_indeterminate": "#CCAA00", "state_unknown": "#FF00FF",
        "action_danger": "#FF3300",
    }),

    # 3 - Cyberpunk: dark background, neon accents (cyan/magenta), glowing
    # measurement values.
    _theme("cyberpunk", "theme.cyberpunk", {
        "window_bg": "#0D0221", "panel_bg": "#1A0B2E", "field_bg": "#10041F",
        "text": "#E0E0FF", "text_disabled": "#6B5B95",
        "bevel_light": "#FF2EC4", "bevel_shadow": "#0FF0FC", "button_shadow": "#00B8C4",
        "grid_line": "#3D1F5C", "accent_bg": "#FF2EC4", "accent_text": "#0D0221",
        "dialog_border": "#0FF0FC", "spin_pressed_bg": "#3D1F5C",
        "lcd_bg": "#0D0221", "lcd_fg": "#0FF0FC",
        "console_bg": "#1A0B2E", "console_text": "#0FF0FC", "console_border": "#FF2EC4",
        "console_header_bg": "#1A0B2E", "console_header_text": "#FF2EC4",
        "tree_group_bg": "#2A1445", "tree_item_bg": "#1F0E38",
        "state_ok": "#39FF14", "state_ok_text": "#39FF14",
        "state_warning": "#FFE600", "state_warning_badge": "#FFB800", "state_warning_dark": "#806B00",
        "state_caution": "#FF8C00",
        "state_alarm": "#FF0055", "state_alarm_dark": "#99002E",
        "state_info": "#0FF0FC",
        "state_neutral": "#6B5B95", "state_neutral_dark": "#3D1F5C",
        "state_indeterminate": "#B8A600", "state_unknown": "#FF2EC4",
        "action_danger": "#FF0055",
    }),

    # 4 - SimCity 2000: warm 90s-game palette (browns/beiges, muted
    # green/blue) - same era as the Win98 shape language, different hues.
    _theme("simcity2000", "theme.simcity2000", {
        "window_bg": "#C9B79C", "panel_bg": "#B89968", "field_bg": "#F0E6D2",
        "text": "#3E2C1C", "text_disabled": "#8C7A5E",
        "bevel_light": "#E8D9BC", "bevel_shadow": "#6B4F2E", "button_shadow": "#4A3620",
        "grid_line": "#8C7A5E", "accent_bg": "#5C7A5C", "accent_text": "#F0E6D2",
        "dialog_border": "#3E2C1C", "spin_pressed_bg": "#A08558",
        "lcd_bg": "#3E2C1C", "lcd_fg": "#8FBF7F",
        "console_bg": "#3E5C6B", "console_text": "#C9E0E6", "console_border": "#8FBF7F",
        "console_header_bg": "#3E5C6B", "console_header_text": "#E8D9BC",
        "tree_group_bg": "#A08558", "tree_item_bg": "#C4AC7D",
        "state_ok": "#2E8B3D", "state_ok_text": "#2E8B3D",
        "state_warning": "#C77D1E", "state_warning_badge": "#C68A2E", "state_warning_dark": "#7A5A20",
        "state_caution": "#A1481E",
        "state_alarm": "#A63D2E", "state_alarm_dark": "#7A2B1F",
        "state_info": "#3E5C8C",
        "state_neutral": "#736A62", "state_neutral_dark": "#4A4030",
        "state_indeterminate": "#8C7A2E", "state_unknown": "#8C5E8C",
        "action_danger": "#7A2B1F",
    }),
]


def theme_count() -> int:
    return len(THEMES)


def get_theme(index: int) -> dict:
    """Raises IndexError for an out-of-range index - callers that accept
    untrusted input (a tag write) must go through clamp_index() first."""
    return THEMES[index]


def get_theme_by_id(theme_id: str):
    for theme in THEMES:
        if theme["id"] == theme_id:
            return theme
    return None


def clamp_index(value) -> "int | None":
    """None means "not a usable theme index" - the caller's job is to
    ignore it and keep whatever theme is already active (Task: a bad
    write from logic must never crash or blank the screen)."""
    try:
        # bool is an int subclass; True/False are never a sane theme
        # index, so reject them explicitly before the int() cast (which
        # would otherwise happily accept them as 0/1).
        if isinstance(value, bool):
            return None
        index = int(value)
    except (TypeError, ValueError):
        return None
    if 0 <= index < len(THEMES):
        return index
    return None


def _hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _color_distance(hex_a: str, hex_b: str) -> float:
    """Simple Euclidean RGB distance - good enough to catch "these two
    colors are basically the same" without needing a new dependency for
    a perceptual color-difference formula."""
    ra, ga, ba = _hex_to_rgb(hex_a)
    rb, gb, bb = _hex_to_rgb(hex_b)
    return ((ra - rb) ** 2 + (ga - gb) ** 2 + (ba - bb) ** 2) ** 0.5


MIN_DISTINGUISHABLE_DISTANCE = 60.0


def state_color_report(colors: dict, min_distance: float = MIN_DISTINGUISHABLE_DISTANCE):
    """Checks that every CORE_STATE_KEYS color is distinguishable from
    every other one, and from the theme's two main backgrounds
    (window_bg, panel_bg) - Task: "w kazdym motywie kolory stanow musza
    roznic sie od siebie i od tla". Returns (ok: bool, problems: list[str])
    - problems is empty iff ok is True, and always human-readable (used
    directly in a test assertion message)."""
    problems = []
    backgrounds = {"window_bg": colors["window_bg"], "panel_bg": colors["panel_bg"]}

    keys = list(CORE_STATE_KEYS)
    for i, key_a in enumerate(keys):
        for key_b in keys[i + 1:]:
            dist = _color_distance(colors[key_a], colors[key_b])
            if dist < min_distance:
                problems.append(
                    f"{key_a} ({colors[key_a]}) too close to {key_b} ({colors[key_b]}): distance={dist:.1f}"
                )
        for bg_name, bg_hex in backgrounds.items():
            dist = _color_distance(colors[key_a], bg_hex)
            if dist < min_distance:
                problems.append(
                    f"{key_a} ({colors[key_a]}) too close to {bg_name} ({bg_hex}): distance={dist:.1f}"
                )
    return (len(problems) == 0), problems


def state_colors_distinguishable(colors: dict, min_distance: float = MIN_DISTINGUISHABLE_DISTANCE) -> bool:
    ok, _problems = state_color_report(colors, min_distance)
    return ok
