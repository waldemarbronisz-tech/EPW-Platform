"""The commands a person actually types must reach the code they name.

This exists because of a real one: moving a helper out of
`studio/shell/logic_panel.py` into its own module updated every caller
the test suite reaches - and missed `studio/main.py`, which is the
command that starts Studio. 2552 tests passed and the program did not
open.

## Two things this deliberately does not do

**It does not run the entry points.** Importing `runtime/main.py`
executes its module scope; `studio/synoptic/main.py` pulls in pywebview,
a launcher-only dependency that most environments have no reason to
install. A test that needs a GUI, a browser runtime or a database is a
different kind of test, and this one would then fail for reasons that
have nothing to do with what it is checking.

**It does not judge third-party imports.** `import pywebview` failing
is a fact about an environment. `from studio.shell.logic_panel import
_ensure_logic_studio_importable` failing is a broken reference inside
this repository, and that is the whole target.

So: every import statement in each entry point is read out of the source
with `ast` - including the ones inside functions, which is where the
bug that prompted this actually sat, and which importing the file would
never reach - and every one that names one of OUR packages is resolved.
"""
import ast
import importlib
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# (label, path, the sys.path entry that command sets up for itself,
#  whether it reaches into this repository at all)
ENTRY_POINTS = [
    ("EPW Studio", _REPO_ROOT / "studio" / "main.py", None, True),
    ("EPW OS", _REPO_ROOT / "runtime" / "main.py", _REPO_ROOT / "runtime", True),
    ("Logic Studio (standalone)", _REPO_ROOT / "studio" / "logic" / "main.py",
     _REPO_ROOT / "studio" / "logic", True),
    # The Synoptic launcher imports nothing of ours on purpose: it
    # starts a loopback HTTP server over the already-built dist/ and
    # points a pywebview window at it. The editor is TypeScript; this
    # file is a window around it.
    ("Synoptic editor (standalone)", _REPO_ROOT / "studio" / "synoptic" / "main.py", None, False),
]
IDS = [entry[0] for entry in ENTRY_POINTS]

# The top-level packages this repository owns. An import of anything
# else is somebody's dependency, and whether it is installed says
# nothing about whether this code is correct.
OUR_PACKAGES = {"studio", "shared", "epw_os", "logic_studio", "synoptic_editor"}


def _imports(path):
    """[(line, module, symbol_or_None)] for every import in the file -
    module scope and inside functions alike."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:  # a relative import resolves against a package we are not in
                continue
            for alias in node.names:
                found.append((node.lineno, node.module, alias.name))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                found.append((node.lineno, alias.name, None))
    return found


def _ours(module_name):
    return bool(module_name) and module_name.split(".")[0] in OUR_PACKAGES


@pytest.mark.parametrize("label,path,extra,ours", ENTRY_POINTS, ids=IDS)
def test_the_entry_point_exists(label, path, extra, ours):
    assert path.exists(), f"{label}: {path} is gone - this list is out of date"


@pytest.mark.parametrize("label,path,extra,ours", ENTRY_POINTS, ids=IDS)
def test_the_entry_point_has_something_to_run(label, path, extra, ours):
    """A `python main.py` that defines no main() and has no
    `if __name__ == "__main__"` block starts nothing."""
    source = path.read_text(encoding="utf-8")
    assert "def main(" in source or '__name__ == "__main__"' in source, \
        f"{label}: nothing here runs when the file is executed"


@pytest.mark.parametrize("label,path,extra,ours", ENTRY_POINTS, ids=IDS)
def test_every_reference_into_this_repository_resolves(label, path, extra, ours):
    """THE test. Studio's entry point imported a helper inside
    `_apply_studio_skin()`; the helper had moved to another module, and
    nothing noticed until somebody tried to start the program.

    An import written inside a function is still an import the command
    performs - it just performs it a second later.
    """
    added = None
    if extra is not None and str(extra) not in sys.path:
        sys.path.insert(0, str(extra))
        added = str(extra)
    try:
        broken = []
        for lineno, module_name, symbol in _imports(path):
            if not _ours(module_name):
                continue
            try:
                module = importlib.import_module(module_name)
            except ImportError as e:
                broken.append(f"line {lineno}: {module_name} - {e}")
                continue
            if symbol and not hasattr(module, symbol):
                # A submodule is a legitimate "attribute" that only
                # appears once it has been imported in its own right.
                try:
                    importlib.import_module(f"{module_name}.{symbol}")
                except ImportError:
                    broken.append(f"line {lineno}: {module_name} has no {symbol!r}")
        assert not broken, f"{label}: references that do not resolve: " + "; ".join(broken)
    finally:
        if added:
            sys.path.remove(added)


def test_the_entry_points_really_do_reference_this_repository():
    """The test above would pass against a file that imports nothing of
    ours - which is what a typo in a package name looks like. So the
    table says which entry points reach into the repository, and this
    holds them to it. The Synoptic launcher is marked as not doing so,
    and is checked for that too: if it ever starts importing our code,
    the table is what should say so."""
    for label, path, _extra, reaches_in in ENTRY_POINTS:
        found = [name for _line, name, _symbol in _imports(path) if _ours(name)]
        if reaches_in:
            assert found, f"{label}: imports nothing from this repository - is the path right?"
        else:
            assert not found, f"{label}: now imports {found} - update the table"
