"""Tests for the lightweight i18n layer (epw_os/i18n)."""

import json
import os

import pytest

from epw_os import i18n

LOCALES_DIR = os.path.join(os.path.dirname(i18n.__file__), "locales")
EXPECTED_CODES = ["en", "pl", "de", "es", "uk", "fr", "it"]


@pytest.fixture(autouse=True)
def _restore_language():
    original = i18n.get_language()
    yield
    i18n.set_language(original)


def test_all_seven_locale_files_exist_and_parse():
    for code in EXPECTED_CODES:
        path = os.path.join(LOCALES_DIR, f"{code}.json")
        assert os.path.exists(path), f"missing locale file: {code}.json"
        with open(path, encoding="utf-8") as f:
            json.load(f)  # must be valid JSON


def test_available_languages_matches_files():
    codes = [code for code, _name in i18n.available_languages()]
    assert codes == EXPECTED_CODES


def test_english_is_fully_populated_for_shipped_areas():
    i18n.set_language("en")
    # A representative key from every area translated this session.
    for key in [
        "app.title",
        "menu.file", "menu.file_new", "menu.file_exit",
        "menu.settings", "menu.settings_language", "menu.settings_change_pin",
        "nav.main_view", "nav.engineer_mode",
        "statusbar.user", "statusbar.simulation_mode",
        "topbar.project", "topbar.comm_ok",
        "settings.pin_change_title", "settings.language_label",
        "pin_prompt.unlock", "timeout_popup.title",
    ]:
        assert i18n.tr(key) != key, f"English missing translation for {key}"


def test_polish_translates_menu_nav_statusbar():
    i18n.set_language("pl")
    assert i18n.tr("menu.file") == "Plik"
    assert i18n.tr("nav.digital_inputs") == "WEJŚCIA CYFROWE"
    assert i18n.tr("statusbar.simulation_mode") == "TRYB SYMULACJI"


def test_missing_key_falls_back_to_key_then_default():
    i18n.set_language("pl")
    assert i18n.tr("nope.not.here") == "nope.not.here"
    assert i18n.tr("nope.not.here", default="X") == "X"


def test_placeholder_locale_falls_back_to_english():
    # de/es/uk/fr/it ship as English copies for now - a lookup must yield
    # the English string, never an empty value or the raw key.
    i18n.set_language("de")
    assert i18n.tr("menu.file") == "File"
    assert i18n.tr("nav.main_view") == i18n._lookup(i18n._load("en"), "nav.main_view")


def test_unknown_language_code_falls_back_to_english():
    assert i18n.set_language("zz") == "en"


def test_format_params_are_substituted():
    i18n.set_language("en")
    assert i18n.tr("topbar.comm_offline", n=3) == "COMM: 3 OFFLINE"


def _flatten_keys(data, prefix=""):
    """Dotted-path key set for a nested locale dict, e.g. {"a": {"b": "x"}}
    -> {"a.b"}. Mirrors i18n._lookup()'s own dotted-path walk."""
    keys = set()
    for k, v in data.items():
        path = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            keys |= _flatten_keys(v, path)
        else:
            keys.add(path)
    return keys


def test_every_english_key_exists_in_polish():
    # Catches forgotten translations: pl.json is meant to be fully
    # translated (unlike the de/es/uk/fr/it placeholders), so every key
    # that exists in en.json must also exist in pl.json - even if a
    # future English-only addition is temporarily missed, this test
    # should fail loudly rather than silently falling back to English
    # for a Polish-selected user. _meta is excluded - it's per-file
    # identification (language name/code/status), not a translatable key.
    en_data = i18n._load("en")
    pl_data = i18n._load("pl")
    en_keys = _flatten_keys({k: v for k, v in en_data.items() if k != "_meta"})
    pl_keys = _flatten_keys({k: v for k, v in pl_data.items() if k != "_meta"})
    missing = en_keys - pl_keys
    assert not missing, f"pl.json is missing {len(missing)} key(s) present in en.json: {sorted(missing)}"


def test_module_has_no_qt_dependency():
    # Importing and using i18n must not drag in a GUI toolkit - the
    # headless core loads a language at startup (see test_headless.py).
    import subprocess
    import sys

    code = (
        "import sys; from epw_os import i18n; i18n.set_language('pl'); "
        "i18n.tr('menu.file'); "
        "bad=[m for m in sys.modules if m.startswith(('PyQt6','PySide6'))]; "
        "print(bad); sys.exit(1 if bad else 0)"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, f"i18n pulled in Qt: {result.stdout.strip()}"
