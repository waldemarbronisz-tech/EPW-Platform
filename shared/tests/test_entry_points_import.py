"""The commands a person actually types must at least import.

This exists because of a real one: moving a helper out of
`studio/shell/logic_panel.py` into its own module updated every caller
the test suite reaches - and missed `studio/main.py`, which is the
command that starts Studio. 2552 tests passed and the program did not
open.

Nothing here runs a GUI. Importing an entry point is enough to catch
the whole class of failure it missed: a moved name, a renamed module, a
typo in an import, a circular import introduced by a new dependency
between packages.

`main()` is deliberately NOT called - these modules create a
QApplication and a window, and a test that did that would be a GUI
test, which is what the gui_smoke and studio suites are for. Which is
exactly why importing the module is not enough on its own: the import
that broke Studio sat INSIDE a function, where a plain import of the
file never reaches it. So every import statement in the file is
resolved, wherever it sits.
"""
import ast
import importlib
import importlib.util
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# (label, path, extra sys.path entry the command itself sets up)
ENTRY_POINTS = [
    ("EPW Studio", _REPO_ROOT / "studio" / "main.py", None),
    ("EPW OS", _REPO_ROOT / "runtime" / "main.py", _REPO_ROOT / "runtime"),
    ("Logic Studio (standalone)", _REPO_ROOT / "studio" / "logic" / "main.py",
     _REPO_ROOT / "studio" / "logic"),
    ("Synoptic editor (standalone)", _REPO_ROOT / "studio" / "synoptic" / "main.py", None),
]


def _import_isolated(label, path, extra_path):
    """Imports the file under a private module name so importing one
    entry point cannot satisfy the next one's imports by accident."""
    added = None
    if extra_path is not None and str(extra_path) not in sys.path:
        sys.path.insert(0, str(extra_path))
        added = str(extra_path)
    module_name = "_entry_point_" + label.split()[0].lower()
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous
        if added:
            sys.path.remove(added)
    return module


@pytest.mark.parametrize("label,path,extra", ENTRY_POINTS, ids=[e[0] for e in ENTRY_POINTS])
def test_the_entry_point_exists(label, path, extra):
    assert path.exists(), f"{label}: {path} is gone - this list is out of date"


@pytest.mark.parametrize("label,path,extra", ENTRY_POINTS, ids=[e[0] for e in ENTRY_POINTS])
def test_the_entry_point_imports(label, path, extra):
    """Everything the file does at module scope, actually done."""
    module = _import_isolated(label, path, extra)
    assert hasattr(module, "main") or hasattr(module, "__file__")


def _deferred_imports(path):
    """Every `from x import y` and `import x` that is NOT at module
    scope - the ones a plain import of the file never executes."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    top_level = {id(node) for node in tree.body}
    found = []
    for node in ast.walk(tree):
        if id(node) in top_level:
            continue
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for alias in node.names:
                found.append((node.lineno, node.module, alias.name))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                found.append((node.lineno, alias.name, None))
    return found


@pytest.mark.parametrize("label,path,extra", ENTRY_POINTS, ids=[e[0] for e in ENTRY_POINTS])
def test_every_import_inside_a_function_resolves_too(label, path, extra):
    """THE test. Studio's entry point imported a helper inside
    `_apply_studio_skin()`; the helper had moved to another module, and
    nothing noticed until somebody ran the program.

    An import written inside a function is still an import the command
    performs - it just performs it a second later.
    """
    added = None
    if extra is not None and str(extra) not in sys.path:
        sys.path.insert(0, str(extra))
        added = str(extra)
    try:
        broken = []
        for lineno, module_name, symbol in _deferred_imports(path):
            try:
                module = importlib.import_module(module_name)
            except ImportError as e:
                broken.append(f"line {lineno}: import {module_name} - {e}")
                continue
            if symbol and not hasattr(module, symbol):
                # A submodule is a legitimate "attribute" that only
                # appears once it has been imported in its own right.
                try:
                    importlib.import_module(f"{module_name}.{symbol}")
                except ImportError:
                    broken.append(f"line {lineno}: {module_name} has no {symbol!r}")
        assert not broken, f"{label}: imports that do not resolve: " + "; ".join(broken)
    finally:
        if added:
            sys.path.remove(added)


@pytest.mark.parametrize("label,path,extra", ENTRY_POINTS, ids=[e[0] for e in ENTRY_POINTS])
def test_the_entry_point_has_something_to_run(label, path, extra):
    """A `python main.py` that defines no main() and has no
    `if __name__ == "__main__"` block starts nothing."""
    source = path.read_text(encoding="utf-8")
    assert "def main(" in source or '__name__ == "__main__"' in source, \
        f"{label}: nothing here runs when the file is executed"
