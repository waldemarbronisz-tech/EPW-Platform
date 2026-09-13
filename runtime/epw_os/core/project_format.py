"""Runtime's handle on shared/project_format.py - the one implementation
of the `projekt.epw` format, the same file Studio writes with (task
"runtime czyta projekt.epw", point 1.1: shared, not a second copy).

Loaded BY PATH, the way epw_os/core/addressing.py loads
shared/addressing.py - runtime never needs the repository root on
sys.path. The module is registered in sys.modules under a private name
so dataclasses and pickling can resolve it; if this process already
imported the same file as `shared.project_format` (the cross-program
tests do), that module object is reused, so a Studio `Card` and a
runtime `Card` are the same class in one process.
"""
import importlib.util
import sys
from pathlib import Path

SHARED_SOURCE_PATH = Path(__file__).resolve().parents[3] / "shared" / "project_format.py"
_MODULE_NAME = "_epw_shared_project_format"


def _load():
    for name in ("shared.project_format", _MODULE_NAME):
        module = sys.modules.get(name)
        if module is not None and Path(module.__file__).resolve() == SHARED_SOURCE_PATH:
            return module
    spec = importlib.util.spec_from_file_location(_MODULE_NAME, SHARED_SOURCE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


_shared = _load()
globals().update({name: value for name, value in vars(_shared).items() if not name.startswith("__")})
