"""Tests for the central visual-theme module (epw_os/core/themes.py) -
headless, no Qt needed at all."""

import pytest

from epw_os.core import themes


def test_five_themes_exist_in_stable_order():
    assert themes.theme_count() == 5
    assert [t["id"] for t in themes.THEMES] == [
        "industrial", "night", "high_contrast", "cyberpunk", "simcity2000",
    ]


def test_industrial_is_the_default_and_is_index_zero():
    assert themes.DEFAULT_THEME_INDEX == 0
    assert themes.THEMES[0]["id"] == "industrial"
    assert themes.get_theme(themes.DEFAULT_THEME_INDEX)["id"] == "industrial"


@pytest.mark.parametrize("index", range(5))
def test_every_theme_defines_every_required_color_key(index):
    colors = themes.get_theme(index)["colors"]
    missing = [k for k in themes.ALL_KEYS if k not in colors]
    assert missing == [], f"theme {index} is missing: {missing}"
    # And nothing is an empty/placeholder value.
    for key, value in colors.items():
        assert isinstance(value, str) and value.startswith("#") and len(value) == 7, (key, value)


# --- DOWÓD: state colors are distinguishable from each other and from
# the background, in EVERY theme --------------------------------------

@pytest.mark.parametrize("index", range(5))
def test_state_colors_are_distinguishable_in_every_theme(index):
    colors = themes.get_theme(index)["colors"]
    ok, problems = themes.state_color_report(colors)
    assert ok, f"theme {index} ({themes.get_theme(index)['id']}): {problems}"


def test_distinguishability_check_actually_catches_a_bad_theme():
    # Negative control: prove the test above isn't vacuously true by
    # feeding it a deliberately broken palette (alarm color == background).
    colors = dict(themes.get_theme(0)["colors"])
    colors["state_alarm"] = colors["window_bg"]
    ok, problems = themes.state_color_report(colors)
    assert not ok
    assert any("state_alarm" in p for p in problems)


# --- Industrial must be pixel-identical to the app's pre-theme look ----

INDUSTRIAL_EXPECTED = {
    "window_bg": "#C0C0C0", "panel_bg": "#D4D0C8", "field_bg": "#FFFFFF",
    "text": "#000000", "text_disabled": "#808080",
    "bevel_light": "#FFFFFF", "bevel_shadow": "#808080", "button_shadow": "#404040",
    "grid_line": "#808080", "accent_bg": "#000080", "accent_text": "#FFFFFF",
    "dialog_border": "#000000", "spin_pressed_bg": "#A0A0A0",
    "lcd_bg": "#000000", "lcd_fg": "#00FF00",
    "console_bg": "#000080", "console_text": "#00FFFF", "console_border": "#00FFFF",
    "console_header_bg": "#000080", "console_header_text": "#FFFF00",
    "state_ok": "#00FF00", "state_warning": "#FFFF00", "state_alarm": "#FF0000",
    "state_info": "#0000FF", "state_neutral": "#808080",
    "action_danger": "#800000",
}


def test_industrial_matches_every_hardcoded_value_from_before_this_task():
    """Task's hard requirement: Industrial must look IDENTICAL to the
    program before this task. These are the literal hex values that were
    hardcoded across style.py and the GUI files before the theme system
    existed (see SESSION_REPORT.md's "moved from" list) - if any of
    these drift, Industrial's actual on-screen appearance would change."""
    colors = themes.get_theme(0)["colors"]
    for key, expected in INDUSTRIAL_EXPECTED.items():
        assert colors[key] == expected, f"{key}: expected {expected}, got {colors[key]}"


# --- clamp_index(): never lets a bad tag write through ------------------

@pytest.mark.parametrize("value,expected", [
    (0, 0), (4, 4), (2, 2),
    ("3", 3),  # TagManager casts INT tag values through int(), so a
               # numeric string is a legitimate value to defend against too
    (3.0, 3),
])
def test_clamp_index_accepts_valid_values(value, expected):
    assert themes.clamp_index(value) == expected


@pytest.mark.parametrize("value", [-1, 5, 99, -99, "not a number", None, [], {}, True, False])
def test_clamp_index_rejects_invalid_values(value):
    assert themes.clamp_index(value) is None


def test_clamp_index_truncates_a_float_like_int_does():
    # Consistent with TagManager itself: a REAL-valued write to an
    # INT-typed tag is already truncated by TagManager's own int(value)
    # cast before ThemeManager ever sees it (_apply_update) - clamp_index()
    # matches that same leniency rather than being stricter than the tag
    # system it's guarding.
    assert themes.clamp_index(2.7) == 2


def test_get_theme_by_id():
    assert themes.get_theme_by_id("night")["colors"]["window_bg"] == "#2B2B2B"
    assert themes.get_theme_by_id("nonexistent_theme") is None
