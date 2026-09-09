"""Lightweight UI translation layer for EPW OS.

Design goals (deliberately minimal - no Qt Linguist / .ts / .qm toolchain):

* One flat JSON file per language in ``epw_os/i18n/locales/<code>.json``.
* Keys are dotted paths (``"menu.file"``, ``"nav.main_view"``) resolved
  against the nested JSON. Grouping by area/page keeps the files readable
  and lets a whole page be added as one new block.
* ``tr(key)`` never raises: it falls back active-language -> English ->
  the caller's ``default`` -> the key string itself. A half-translated
  locale therefore just shows English for the missing keys.
* ``set_language()`` flips the active language immediately, but this
  module has no idea any GUI exists and never re-triggers already-built
  widgets on its own - every ``tr("...")`` call site stays a plain,
  unwired string lookup, resolved once, at whatever moment the widget
  that owns it happens to run that line.
* Applying a language *change* to an already-running GUI (Task: switch
  language on a kiosk without restarting the process) is therefore the
  GUI layer's job, not this module's: main.py rebuilds the whole
  MainWindow - calling ``set_language()`` again first, then constructing
  a fresh window, so every widget re-reads ``tr()`` at its own
  construction time exactly like on a real restart - rather than this
  module trying to reach into arbitrary already-built widgets itself.
  See ``MainWindow._open_language_dialog()``/``main.py``'s
  ``rebuild_window_for_language_change()``.

This module is intentionally free of any PyQt import so the headless core
can load a language without pulling in Qt (see ``test_headless.py``).

Adding translations for a new page later:

1. Add a block to ``locales/en.json`` and ``locales/pl.json`` (and,
   ideally, the other locales - otherwise they inherit English).
2. In the page, ``from epw_os.i18n import tr`` and wrap each user-facing
   string: ``QLabel(tr("pages.my_page.title"))``.

That's the whole procedure - no architecture change.
"""

import json
import os

# Qt-free (see this module's own docstring: "intentionally free of any
# PyQt import") - epw_os.core.logging is a plain stdlib logging wrapper,
# imported by every other core/ module already.
from epw_os.core.logging import log

_LOCALES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locales")

# code -> native display name, in the order the Settings dropdown lists them.
LANGUAGES = {
    "en": "English",
    "pl": "Polski",
    "de": "Deutsch",
    "es": "Español",
    "uk": "Українська",
    "fr": "Français",
    "it": "Italiano",
}

DEFAULT_LANGUAGE = "en"

_cache = {}          # code -> parsed dict
_active = DEFAULT_LANGUAGE


def _load(code):
    """Parsed locale dict for ``code`` (cached). Missing/broken file -> {}."""
    if code in _cache:
        return _cache[code]
    path = os.path.join(_LOCALES_DIR, code + ".json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except OSError:
        # Missing file - not logged: LANGUAGES only lists codes this
        # module expects to have a real file, so this should be rare,
        # but is still routine/recoverable (tr() falls back to English,
        # then the key itself).
        data = {}
    except ValueError as e:
        # The file EXISTS but isn't valid JSON - a real, actionable
        # problem (a bad hand-edit, disk corruption), not the routine
        # "missing" case above. Silently falling back to {} here would
        # make the ENTIRE UI quietly render raw translation keys/English
        # for that whole language, with nobody able to tell why - the
        # same "polykane wyjatki" pattern System.Mode had.
        log.warning(f"Malformed JSON in locale file {path}: {e}")
        data = {}
    _cache[code] = data
    return data


def available_languages():
    """``[(code, native_name), ...]`` in dropdown display order."""
    return list(LANGUAGES.items())


def is_supported(code):
    return code in LANGUAGES


def set_language(code):
    """Select the active UI language. An unknown code falls back to English.
    Returns the code that ended up active."""
    global _active
    _active = code if code in LANGUAGES else DEFAULT_LANGUAGE
    _load(_active)
    _load(DEFAULT_LANGUAGE)
    return _active


def get_language():
    return _active


def _lookup(data, key):
    node = data
    for part in key.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node if isinstance(node, str) else None


def tr(key, default=None, **params):
    """Translate ``key`` (a dotted path) in the active language.

    Fallback order: active language -> English -> ``default`` -> ``key``.
    ``params`` are applied with ``str.format`` when present, so a locale
    string may contain ``{name}`` placeholders. Never raises.
    """
    value = _lookup(_load(_active), key)
    if value is None:
        value = _lookup(_load(DEFAULT_LANGUAGE), key)
    if value is None:
        value = default if default is not None else key
    if params:
        try:
            value = value.format(**params)
        except (KeyError, IndexError, ValueError) as e:
            # A locale string referencing a {placeholder} the caller
            # didn't pass (or a format-spec mismatch) - shown unformatted
            # (literal "{...}" text and all) rather than crashing the
            # widget that called tr() (kept unchanged - this function
            # must never raise). Silently doing so means a translation/
            # call-site typo just sits there in the UI forever with
            # nobody able to tell why - the same "polykane wyjatki"
            # pattern System.Mode had.
            log.warning(f"tr({key!r}, **{params!r}) - format() failed on {value!r}: {e}")
    return value


def reload():
    """Drop the parse cache - only needed by tests that edit locale files."""
    _cache.clear()
    _load(_active)
    _load(DEFAULT_LANGUAGE)
