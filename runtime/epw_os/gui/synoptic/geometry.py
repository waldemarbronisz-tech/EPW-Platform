"""shared/symbols/geometry.json - the Synoptic Editor's symbol library as
drawing primitives (exported by studio/synoptic/tools/geometry_export/
export.mjs; see that script's header for the format).

Loaded by path from the repository's shared/ directory, the same way
runtime loads shared/project_format.py and shared/addressing.py - the
file is data the two programs share, not runtime's own. A missing or
unreadable file is reported (load_problem) and every symbol then draws
as the generic box - the screen still shows, honestly degraded.

Templates: a prop exported as {"$template": "...{{field}}...",
"$default": v} is resolved per object with resolve_template(): the
object's own field values go in, and a template whose every field is
empty falls back to the symbol's own default for an empty field.
"""
import json
import os
import re
from functools import lru_cache
from pathlib import Path

from epw_os.core.logging import log

GEOMETRY_FORMAT = "EPW_SYMBOL_GEOMETRY"
DEFAULT_GEOMETRY_PATH = Path(__file__).resolve().parents[4] / "shared" / "symbols" / "geometry.json"
_FIELD = re.compile(r"\{\{([a-zA-Z]+)\}\}")


class SymbolGeometry:
    def __init__(self, data: dict, path: str):
        self.path = path
        self.symbols = data.get("symbols") or {}
        self.generated_at = data.get("generated_at")

    def __contains__(self, symbol_type):
        return symbol_type in self.symbols

    def types(self):
        return sorted(self.symbols)

    def symbol(self, symbol_type):
        return self.symbols.get(symbol_type)

    def reference_size(self, symbol_type, default=(64.0, 64.0)):
        rec = self.symbols.get(symbol_type)
        if not rec:
            return default
        return float(rec.get("reference_width") or default[0]), float(rec.get("reference_height") or default[1])

    def default_state(self, symbol_type):
        rec = self.symbols.get(symbol_type)
        return (rec or {}).get("default_state") or "NORMAL"

    def allowed_states(self, symbol_type):
        rec = self.symbols.get(symbol_type)
        return list((rec or {}).get("allowed_states") or [])

    def state_tree(self, symbol_type, state):
        """The primitive tree for (type, state), falling back to the
        symbol's default state, then to any exported state; None when the
        type is unknown or generic (drawn by the renderer's own box)."""
        rec = self.symbols.get(symbol_type)
        if not rec or rec.get("generic"):
            return None
        states = rec.get("states") or {}
        for candidate in (state, rec.get("default_state"), "NORMAL"):
            tree = states.get(candidate) if candidate else None
            if tree:
                return tree
        for tree in states.values():
            if tree:
                return tree
        return None

    def animation(self, symbol_type):
        rec = self.symbols.get(symbol_type)
        return (rec or {}).get("animation")


class GeometryLoadResult:
    def __init__(self, geometry, problem=None):
        self.geometry = geometry
        self.problem = problem

    @property
    def ok(self):
        return self.problem is None


def load_geometry(path=None) -> GeometryLoadResult:
    path = str(path or os.environ.get("EPW_SYMBOL_GEOMETRY") or DEFAULT_GEOMETRY_PATH)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        problem = f"Symbol geometry file not found: {path}"
    except (OSError, ValueError) as e:
        problem = f"Symbol geometry file unreadable: {path} ({e})"
    else:
        if not isinstance(data, dict) or data.get("format") != GEOMETRY_FORMAT:
            problem = f"{path} is not an {GEOMETRY_FORMAT} file."
        else:
            return GeometryLoadResult(SymbolGeometry(data, path))
    log.error(problem)
    return GeometryLoadResult(SymbolGeometry({"symbols": {}}, path), problem)


@lru_cache(maxsize=4)
def shared_geometry(path=None) -> GeometryLoadResult:
    """One parsed copy per process (the file is ~1 MB)."""
    return load_geometry(path)


def is_template(value) -> bool:
    return isinstance(value, dict) and "$template" in value


def resolve_template(value, fields: dict):
    """A prop value from the geometry file -> the value to draw for an
    object whose per-instance fields are `fields` (text, fill, border,
    color, designation, name, tag, value, unit, fontSize...). Plain values
    pass through."""
    if not is_template(value):
        return value
    template = value["$template"]
    default = value.get("$default")
    if template == "{{fontSize}}":
        size = fields.get("fontSize")
        try:
            size = float(size) if size not in (None, "", 0) else 0.0
        except (TypeError, ValueError):
            size = 0.0
        if size <= 0:
            return default
        return size * float(value.get("$scale", 1.0))
    names = _FIELD.findall(template)
    present = {n: fields.get(n) for n in names}
    if all(v in (None, "") for v in present.values()):
        return default
    return _FIELD.sub(lambda m: "" if present.get(m.group(1)) in (None,) else str(present.get(m.group(1), "")), template)
