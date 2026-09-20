"""Logic Studio's own UI translation layer.

Owner's instruction: "jeżeli polski to wszędzie ma być polski zarówno w
logice synoptyce itp". Logic Studio had no translation layer at all -
its whole interface was hardcoded English, which is why picking Polish
in Studio left this department in English while every other one
switched.

Same shape as every other lightweight i18n layer here (the Studio
shell's `studio/shell/i18n.py`, the runtime's `epw_os/i18n`, the
Synoptic editor's `src/i18n/tr.ts`): one flat JSON file per language in
`locales/<code>.json`, dotted-path keys, English as the fallback, never
raises.

**Its own module, not an import from the shell**: Logic Studio is a
dependency of the shell, not the other way round, and it still runs
standalone (`studio/logic/main.py`). The shell calls `set_language()`
here when its own language changes - see StudioMainWindow._set_language.

**The block library is translated separately**, by
`shared.logic.i18n`, because its English source is the block classes
themselves rather than a locale file. `block_language()` below is what
ties the two together so a caller needs one answer, not two.
"""
import json
import os

_LOCALES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locales")

DEFAULT_LANGUAGE = "en"
LANGUAGES = ("en", "pl")

_cache = {}
_active = DEFAULT_LANGUAGE


def _load(code):
    if code in _cache:
        return _cache[code]
    path = os.path.join(_LOCALES_DIR, code + ".json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    _cache[code] = data
    return data


def set_language(code):
    """Called by the Studio shell on every language change, and once by
    Logic Studio's own startup when it runs standalone."""
    global _active
    _active = code if code in LANGUAGES else DEFAULT_LANGUAGE
    return _active


def get_language():
    return _active


def block_language():
    """The language to pass to `shared.logic.i18n` for block names,
    categories and descriptions - the same one, kept here so no caller
    has to know there are two catalogues behind one setting."""
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
    value = _lookup(_load(_active), key)
    if value is None:
        value = _lookup(_load("en"), key)
    if value is None:
        value = default if default is not None else key
    if params:
        try:
            value = value.format(**params)
        except (KeyError, IndexError, ValueError):
            pass
    return value
