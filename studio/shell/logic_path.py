"""Where Logic Studio lives, and how the shell reaches it.

`logic_studio` is a real package (it has `__init__.py`) but the
directory containing it - `studio/logic/` - is not on `sys.path` by
default: the shell lives in `studio/shell/`, a sibling, not a parent.

This used to be a private helper inside `logic_panel.py`, which was
fine while that module was the only thing that imported Logic Studio.
It no longer is - the shell also needs Logic Studio's translation layer,
at import time, before any panel exists (see
StudioMainWindow._set_language) - so the one fact "here is where Logic
Studio is" lives in one place rather than being repeated wherever
somebody needs it next.

Qt-free on purpose: importing this must not drag a GUI toolkit into a
module that only wants a path.
"""
import sys
from pathlib import Path

# studio/shell/logic_path.py -> studio/logic
LOGIC_DIR = Path(__file__).resolve().parent.parent / "logic"


def ensure_importable() -> str:
    """Puts `studio/logic` on sys.path if it is not there already, and
    returns it. Idempotent - safe to call from every entry point that
    might be the first one."""
    path_str = str(LOGIC_DIR)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
    return path_str
