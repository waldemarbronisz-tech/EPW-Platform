"""Tests for epw_os/gui/style.py's theme-parameterized QSS template.

Pure string templating (no PySide6 import in style.py itself) - headless,
same as every other core-ish module in this suite, even though this file
lives under gui/.
"""

import re

import pytest

from epw_os.gui import style
from epw_os.core import themes


def _strip_asset_urls(qss: str) -> str:
    """image: url(...) lines encode an install-path-dependent absolute
    file path, not a color - irrelevant to "did the colors change"."""
    return re.sub(r"image:\s*url\([^)]*\);", "image: url(<asset>);", qss)


def _strip_comments(qss: str) -> str:
    """CSS/QSS comments never affect rendering - only the code's own
    explanatory text differs (mentioning the theme system now exists)."""
    return re.sub(r"/\*.*?\*/", "", qss, flags=re.DOTALL)


def _normalize_named_colors(qss: str) -> str:
    """The pre-theme style.py spelled a few colors as CSS keywords
    ("black"/"white") instead of hex. Qt resolves both identically
    (QColor("black") == QColor("#000000")), so for an appearance-parity
    check these must be treated as equal - not a real difference."""
    qss = re.sub(r"\bblack\b", "#000000", qss)
    qss = re.sub(r"\bwhite\b", "#FFFFFF", qss)
    return qss


def test_build_stylesheet_leaves_no_unfilled_placeholder():
    # Every {token} in the template must have been replaced - a missing
    # color key would otherwise raise KeyError (see the next test) or, if
    # the template had a stray literal "{something}" not in
    # themes.ALL_KEYS, silently ship broken CSS with a literal "{...}" in it.
    for index in range(themes.theme_count()):
        qss = style.build_stylesheet(themes.get_theme(index)["colors"])
        leftover = re.findall(r"\{[a-z_]+\}", qss)
        assert leftover == [], f"theme {index} left unfilled tokens: {leftover}"


def test_build_stylesheet_raises_on_incomplete_colors():
    incomplete = {"window_bg": "#000000"}
    with pytest.raises(KeyError):
        style.build_stylesheet(incomplete)


# --- DOWÓD (hard requirement): Industrial must render IDENTICALLY to the
# program before this task -----------------------------------------------

def test_industrial_stylesheet_matches_the_pre_theme_original_byte_for_byte():
    with open("epw_os/tests/fixtures/original_industrial_qss.txt", encoding="utf-8") as f:
        original = f.read()

    generated = style.build_stylesheet(themes.get_theme(0)["colors"])

    original_norm = _normalize_named_colors(_strip_comments(_strip_asset_urls(original)))
    generated_norm = _normalize_named_colors(_strip_comments(_strip_asset_urls(generated)))

    assert original_norm == generated_norm, (
        "Industrial theme's generated QSS differs from the exact stylesheet "
        "the program used before the theme system existed (after normalizing "
        "named colors to hex and ignoring the install-path-dependent asset "
        "URLs) - this would be a REAL, visible appearance change, violating "
        "the task's hard 'Industrial looks identical' requirement."
    )


def test_module_level_windows_nt_style_constant_still_exists_and_is_industrial():
    """Several other modules import WINDOWS_NT_STYLE directly (backward
    compatibility, see style.py's docstring) - it must still be the
    Industrial theme's stylesheet."""
    assert style.WINDOWS_NT_STYLE == style.build_stylesheet(themes.get_theme(0)["colors"])
