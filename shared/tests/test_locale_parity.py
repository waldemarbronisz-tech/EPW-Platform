"""The four translation catalogues, held level with each other.

Owner's instruction: "jeżeli polski to wszędzie ma być polski zarówno w
logice synoptyce itp". "Wszędzie" is four separate programs, each with
its own catalogue for its own good reasons:

  runtime/epw_os/i18n/locales      the controller's panel
  studio/shell/locales             the Studio shell
  studio/logic/logic_studio/locales  Logic Studio
  studio/synoptic/src/i18n/locales   the Synoptic editor (TypeScript)

Four catalogues means four chances to add a string to one language and
forget the other. Nothing breaks when that happens - the lookup falls
back to English and the interface is silently bilingual on one screen.
This test is the only thing that notices.

The block library is checked separately, by
test_block_translations.py: its English lives in the block classes
rather than in a locale file, so it needs a different kind of test, not
a different standard.
"""
import json
import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]

CATALOGUES = {
    "runtime": _REPO_ROOT / "runtime" / "epw_os" / "i18n" / "locales",
    "studio-shell": _REPO_ROOT / "studio" / "shell" / "locales",
    "logic-studio": _REPO_ROOT / "studio" / "logic" / "logic_studio" / "locales",
    "synoptic": _REPO_ROOT / "studio" / "synoptic" / "src" / "i18n" / "locales",
}
NAMES = sorted(CATALOGUES)
_PLACEHOLDERS = re.compile(r"\{(\w+)\}")
_POLISH_LETTERS = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")


def _flatten(data, prefix=""):
    out = {}
    for key, value in data.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(_flatten(value, full))
        else:
            out[full] = value
    return out


def _load(name, language):
    path = CATALOGUES[name] / f"{language}.json"
    return _flatten(json.loads(path.read_text(encoding="utf-8")))


def test_every_catalogue_is_where_this_test_thinks_it_is():
    """A catalogue moved without updating this file would make every
    test below pass by finding nothing."""
    for name, directory in CATALOGUES.items():
        for language in ("en", "pl"):
            assert (directory / f"{language}.json").exists(), f"{name}/{language}.json is missing"


@pytest.mark.parametrize("name", NAMES)
def test_both_languages_carry_the_same_keys(name):
    english, polish = _load(name, "en"), _load(name, "pl")
    only_en = sorted(set(english) - set(polish))
    only_pl = sorted(set(polish) - set(english))
    assert not only_en, f"{name}: in en.json but not pl.json: {only_en}"
    assert not only_pl, f"{name}: in pl.json but not en.json: {only_pl}"


@pytest.mark.parametrize("name", NAMES)
def test_a_translation_never_drops_a_placeholder(name):
    """A translation missing a {name} shows a literal brace to the
    operator, or throws where the code formats it - and only on the
    screen nobody opened during testing."""
    english, polish = _load(name, "en"), _load(name, "pl")
    for key in sorted(set(english) & set(polish)):
        if not (isinstance(english[key], str) and isinstance(polish[key], str)):
            continue
        assert set(_PLACEHOLDERS.findall(english[key])) == set(_PLACEHOLDERS.findall(polish[key])), \
            f"{name}/{key}: the two languages use different placeholders"


@pytest.mark.parametrize("name", NAMES)
def test_nothing_in_the_english_catalogue_is_actually_polish(name):
    """How the whole problem was found: strings sitting in the English
    catalogue written in Polish, so the interface was wrong in
    whichever language you picked."""
    offending = {key: value for key, value in _load(name, "en").items()
                 if isinstance(value, str) and (set(value) & _POLISH_LETTERS)}
    assert not offending, f"{name}: Polish in en.json: {offending}"


@pytest.mark.parametrize("name", NAMES)
def test_no_translation_is_empty(name):
    """An empty string is not a translation - it is a control with no
    label, which looks like a rendering bug rather than a missing
    string."""
    for language in ("en", "pl"):
        empty = [key for key, value in _load(name, language).items()
                 if isinstance(value, str) and not value.strip()]
        assert not empty, f"{name}/{language}: empty strings at {empty}"


def test_the_catalogues_are_substantial():
    """Guards against a catalogue that has been emptied or replaced by
    a stub, which would make the parity tests above pass trivially."""
    total = sum(len(_load(name, "en")) for name in NAMES)
    assert total > 1500, f"only {total} translated strings in total - something is missing"
