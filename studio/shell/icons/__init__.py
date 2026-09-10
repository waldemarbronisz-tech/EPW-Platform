"""Studio's own Win98-manner icon set - loads the PNGs this package's
generate_icons.py drew (see that file for the drawing rules/palette).
Studio does not draw icons at runtime; it only reads the committed
PNGs. Re-run generate_icons.py and re-commit the PNGs to change one.
"""
import os

from PySide6.QtGui import QIcon

_DIR = os.path.dirname(os.path.abspath(__file__))
_cache: dict[tuple[str, int], QIcon] = {}


def icon(name: str, size: int = 16) -> QIcon:
    """Returns the QIcon for `name`, loaded from
    studio/shell/icons/<name>.png and cached. `size` only affects how
    the icon is asked to scale when a caller requests a larger pixmap
    (e.g. the contact sheet); the source art is always drawn at 16x16."""
    key = (name, size)
    cached = _cache.get(key)
    if cached is not None:
        return cached
    path = os.path.join(_DIR, f"{name}.png")
    result = QIcon(path) if os.path.isfile(path) else QIcon()
    _cache[key] = result
    return result


def has_icon(name: str) -> bool:
    return os.path.isfile(os.path.join(_DIR, f"{name}.png"))
