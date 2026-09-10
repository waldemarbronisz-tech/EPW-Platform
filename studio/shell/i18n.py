"""Minimal UI translation layer for the EPW Studio shell.

Deliberately its own small module, not a shared import from runtime/
(runtime/epw_os/i18n has an equivalent lightweight pattern, but studio/
and runtime/ are separate deployable units with separate venvs and
GRANICE for this task is explicit: don't touch runtime/ at all, and
don't add a dependency between the two).

Same shape as every other lightweight i18n layer in this codebase:
one flat JSON file per language in locales/<code>.json, dotted-path
keys, English fallback, never raises. This module is Qt-free (only the
shell's own new chrome uses it - Synoptic and Logic Studio keep
whatever text they already have, untouched, per GRANICE "nie
przepisuj").
"""
import json
import os

_LOCALES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locales")

DEFAULT_LANGUAGE = "pl"

_cache = {}
_active = DEFAULT_LANGUAGE


def _load(code):
    if code in _cache:
        return _cache[code]
    path = os.path.join(_LOCALES_DIR, code + ".json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except OSError:
        data = {}
    except ValueError:
        data = {}
    _cache[code] = data
    return data


def set_language(code):
    global _active
    _active = code if code in ("en", "pl") else DEFAULT_LANGUAGE
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
