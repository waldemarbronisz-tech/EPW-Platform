"""Regression guard for test_headless.py's own scratch-path fix (Task:
fix/test-headless-scratch-path - "checklista nie moze brudzic projektu").

test_headless.py is a bare top-level script, not a pytest file and not
importable as a callable (it runs EPWCore() at module scope on import) -
so the only real way to verify it never touches the real, tracked
runtime/project.json is to actually RUN it as a subprocess and compare
that file's content before and after, exactly the way this exact
regression was originally caught by hand (git status/git diff). A
comment in test_headless.py saying "this won't touch project.json" is
not proof - this test is.

Marked slow: constructs a real EPWCore() (in a subprocess) same as
every other `db`-using test in this file's sibling test_core.py.
"""
import hashlib
import os
import subprocess
import sys

import pytest

# runtime/epw_os/tests/test_headless_script.py -> runtime/
RUNTIME_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HEADLESS_SCRIPT = os.path.join(RUNTIME_ROOT, "test_headless.py")
REAL_PROJECT_JSON = os.path.join(RUNTIME_ROOT, "project.json")


def _hash_if_exists(path):
    """None for "file does not exist" - kept distinct from any real
    hash value, so a script that CREATES the file where none existed
    before is caught too, not just one that edits an existing one."""
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


@pytest.mark.slow
def test_headless_script_does_not_modify_the_real_project_json():
    before = _hash_if_exists(REAL_PROJECT_JSON)

    result = subprocess.run(
        [sys.executable, HEADLESS_SCRIPT],
        cwd=RUNTIME_ROOT, capture_output=True, text=True, timeout=60,
    )

    after = _hash_if_exists(REAL_PROJECT_JSON)

    assert result.returncode == 0, (
        f"test_headless.py exited {result.returncode}:\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    assert before == after, (
        "test_headless.py modified the real, tracked runtime/project.json. "
        "Its scratch-path guard (redirecting epw_os.core.project_manager."
        "DEFAULT_PROJECT_FILE to a temp file before constructing EPWCore()) "
        "is broken, missing, or was reverted - see that script's own comment "
        "for why this must never touch the real file."
    )


@pytest.mark.slow
def test_headless_script_still_prints_its_success_markers():
    """A narrower companion to the guard above - proves the fix didn't
    also silently break what the script is FOR (GRANICE: "nie zmieniaj
    tego, co skrypt sprawdza"). Startup/shutdown/Qt-free must still all
    genuinely run, not just "not touch project.json"."""
    result = subprocess.run(
        [sys.executable, HEADLESS_SCRIPT],
        cwd=RUNTIME_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "Core started successfully." in result.stdout
    assert "Core stopped successfully. Core is Qt-Free." in result.stdout
