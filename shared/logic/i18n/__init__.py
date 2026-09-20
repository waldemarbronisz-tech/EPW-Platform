"""Polish for the logic block library.

Owner's instruction: "jeżeli polski to wszędzie ma być polski zarówno w
logice synoptyce itp, poki co jezyk jest polski a np biblioteki po
angielsku". The Synoptic editor already had this (98 symbols, both
languages); the logic library did not have it at all.

**English is the source and it lives in the block classes themselves** -
`display_name`, `category`, `description`, `PIN_DESCRIPTIONS`,
`PROPERTY_DESCRIPTIONS`. Nothing is copied here, so the English text
cannot drift from a second copy of itself. `pl.json` maps the English
string to its Polish, and `test_block_translations.py` fails both ways:
a string the registry exposes with no entry here, and an entry here for
a string the registry no longer has.

**What is deliberately NOT translated**: pin names (`In1`, `Q`, `CV`,
`PT`, `ET`, `R`, `S`) and block mnemonics (`AND`, `TON`, `CTU`, `SR`).
Those are IEC 61131 identifiers. A schematic that renames them stops
being readable to anybody who knows the standard, and to every other
tool that reads an export. Their DESCRIPTIONS are translated, which is
where the explaining happens anyway.

**Property keys are data**: the grid stores what the block defines
("Preset (ms)", and the handful that were written in Polish years ago,
"Sygnał", "Minimalny poziom dostępu"). This module only says what to
SHOW. Callers display with the helpers below and always store the
original key - the same rule logic_studio/ui/display_names.py already
states for the English direction.
"""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_cache = {}


def _catalog(language):
    """The catalogue for `language`, or an empty one for a language that
    has none - English needs no catalogue (it is the source), and an
    unknown language must fall back to it rather than fail."""
    if language in _cache:
        return _cache[language]
    path = os.path.join(_HERE, f"{language}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    _cache[language] = data
    return data


def _lookup(language, section, value):
    if not value or language == "en":
        return value
    table = _catalog(language).get(section) or {}
    return table.get(value, value)


def has_entry(section, value, language):
    """Whether somebody has actually looked at this string for this
    language. Not the same as "the translation differs" - "LED" and
    "Bit" are the same word in both, and a coverage test that demanded a
    difference would push somebody into inventing one."""
    if language == "en":
        return True
    return value in (_catalog(language).get(section) or {})


def category_label(category, language="en"):
    """A block category as it should appear in the library tree."""
    return _lookup(language, "categories", category)


def block_label(display_name, language="en"):
    """A block's name in the library and on the canvas. Mnemonics have no
    entry and come back unchanged, which is the intended behaviour."""
    return _lookup(language, "names", display_name)


def property_label(key, language="en"):
    """What to show for a stored property key. The key itself never
    changes - see this module's own docstring."""
    return _lookup(language, "properties", key)


def enum_label(value, language="en"):
    """What to show for a stored enum value whose stored form is English
    (alignment, mainly). Values already stored in Polish are handled in
    the other direction, by logic_studio/ui/display_names.py."""
    return _lookup(language, "enums", value)


def text(english, language="en"):
    """A description - of a block, a pin or a property. Keyed by the
    English text itself, so a description edited in the block class
    fails the coverage test instead of silently showing the old Polish."""
    return _lookup(language, "text", english)


def available_languages():
    """Languages with a catalogue on disk, English always included as the
    source language."""
    found = {"en"}
    for name in os.listdir(_HERE):
        if name.endswith(".json"):
            found.add(name[:-5])
    return sorted(found)
