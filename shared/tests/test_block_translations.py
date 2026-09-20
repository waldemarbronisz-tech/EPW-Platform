"""The logic library in Polish - complete, and provably so.

Owner's instruction: "jeżeli polski to wszędzie ma być polski (...) poki
co jezyk jest polski a np biblioteki po angielsku". A translation
catalogue is worth nothing if a block added next month ships with an
English description and nobody notices - the library still opens, the
tree still fills, and the one untranslated line sits there for a year.

So this test walks the REGISTRY, not the catalogue: every string the
library actually exposes must have a Polish entry, and an entry for a
string the library no longer exposes is an error too (it means somebody
edited an English description and left the Polish describing the old
behaviour, which is worse than no translation at all).
"""
import importlib
import pkgutil
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from shared.logic import i18n
import shared.logic.blocks as _blocks_pkg
from shared.logic.blocks.registry import BlockRegistry

for _module in pkgutil.iter_modules(_blocks_pkg.__path__):
    importlib.import_module("shared.logic.blocks." + _module.name)

LANGUAGES = [code for code in i18n.available_languages() if code != "en"]


def _all_blocks():
    for category in BlockRegistry.get_categories():
        for type_id in BlockRegistry.get_blocks_in_category(category):
            block = BlockRegistry.create_block(type_id)
            if block is not None:
                yield type_id, block


def _exposed_strings():
    """Every English string the library puts in front of a person, with
    where it came from, so a failure names the block rather than just
    the sentence."""
    categories, names, texts, properties = {}, {}, {}, {}
    for type_id, block in _all_blocks():
        categories.setdefault(block.category, type_id)
        names.setdefault(block.display_name, type_id)
        texts.setdefault(block.description, f"{type_id} (description)")
        pins = (block.merged_pin_descriptions() if hasattr(block, "merged_pin_descriptions")
                else dict(getattr(block, "PIN_DESCRIPTIONS", {})))
        for pin, description in pins.items():
            texts.setdefault(description, f"{type_id} (pin {pin})")
        for key, description in (getattr(block, "PROPERTY_DESCRIPTIONS", {}) or {}).items():
            texts.setdefault(description, f"{type_id} (property {key})")
        for key in (block.properties or {}):
            properties.setdefault(key, type_id)
    return categories, names, texts, properties


CATEGORIES, NAMES, TEXTS, PROPERTIES = _exposed_strings()


def test_the_registry_is_actually_loaded():
    """Every other test here would pass vacuously against an empty
    registry - the block modules are imported for their side effect."""
    assert len(list(_all_blocks())) >= 60
    assert len(CATEGORIES) >= 10


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_category_is_translated(language):
    for category in CATEGORIES:
        assert i18n.has_entry("categories", category, language), \
            f"{language}: category {category!r} has no entry"


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_description_is_translated(language):
    missing = {text: where for text, where in TEXTS.items()
               if not i18n.has_entry("text", text, language)}
    assert not missing, ("untranslated in " + language + ":\n" +
                         "\n".join(f"  {where}: {text}" for text, where in sorted(missing.items())))


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_catalogue_has_nothing_the_library_no_longer_says(language):
    """The direction that catches a stale translation: an English
    description edited in the block class leaves its old Polish behind,
    still describing the old behaviour."""
    catalogue = i18n._catalog(language)
    for section, live in (("categories", set(CATEGORIES)), ("text", set(TEXTS)),
                          ("properties", set(PROPERTIES)), ("names", set(NAMES))):
        stale = set(catalogue.get(section, {})) - live
        assert not stale, f"{language}/{section}: entries for strings the library no longer has: {sorted(stale)}"


# Property keys written in Polish years before the interface was
# unified on English, and kept because renaming them would break every
# .epwlogic file and every export already deployed. They are data, and
# the PL interface shows them as they are; it is the EN interface that
# needs a label for them (logic_studio/ui/display_names.py).
_ALREADY_POLISH_KEYS = {"Sygnał", "Minimalny poziom dostępu", "Rozmiar tekstu (pkt)"}


@pytest.mark.parametrize("language", LANGUAGES)
def test_property_keys_that_are_words_are_translated(language):
    for key in PROPERTIES:
        if key in _ALREADY_POLISH_KEYS:
            continue
        assert i18n.has_entry("properties", key, language), \
            f"{language}: property key {key!r} has no label"


def test_the_legacy_polish_keys_are_the_only_ones_left():
    """If a new property key is ever written in Polish, this fails -
    which is the moment to decide, rather than two years later when the
    export is in the field."""
    polish_letters = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")
    suspicious = {key for key in PROPERTIES
                  if key not in _ALREADY_POLISH_KEYS and (set(key) & polish_letters)}
    assert not suspicious, f"new property keys written in Polish: {sorted(suspicious)}"
    assert _ALREADY_POLISH_KEYS <= set(PROPERTIES), \
        "a legacy key is gone - remove it from _ALREADY_POLISH_KEYS too"


def test_iec_identifiers_are_left_alone():
    """Deliberate, and worth pinning: a schematic whose pins are renamed
    stops being readable to anybody who knows IEC 61131, and to every
    tool that reads an export."""
    for mnemonic in ("AND", "OR", "TON", "TOF", "CTU", "SR", "RS", "R_TRIG"):
        assert i18n.block_label(mnemonic, "pl") == mnemonic
    for pin in ("In1", "Out", "Q", "CV", "PT", "ET", "IN", "R", "S"):
        assert i18n.property_label(pin, "pl") == pin or pin in PROPERTIES


def test_english_is_returned_unchanged_and_needs_no_catalogue():
    assert i18n.text("Analog output.", "en") == "Analog output."
    assert i18n.category_label("Analog", "en") == "Analog"


def test_an_unknown_language_falls_back_instead_of_failing():
    assert i18n.text("Analog output.", "de") == "Analog output."
    assert i18n.category_label("Analog", "zz") == "Analog"


def test_no_english_source_string_is_actually_polish(language="en"):
    """This is how the drift was found in the first place: four strings
    in the "English" source were Polish, so the English UI showed Polish
    and the Polish catalogue had nothing to translate."""
    polish_letters = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")
    for text, where in TEXTS.items():
        assert not (set(text) & polish_letters), f"{where}: English source is Polish: {text!r}"
