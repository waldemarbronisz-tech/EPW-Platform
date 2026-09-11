#!/usr/bin/env python3
"""EPW Platform launcher - run from ANY directory, not just the repo
root. Anchored in this file's own location (Path(__file__)), never the
current working directory - the same rule this task's own CWD-relative
test-path fixes already established across the repo.

Usage:
    python epw.py studio     - launch EPW Studio
    python epw.py runtime    - launch EPW Runtime (EPW-OS)
    python epw.py test       - run every test suite, from the repo root
    python epw.py            - show this help
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def studio():
    return subprocess.call([sys.executable, str(REPO_ROOT / "studio" / "main.py")], cwd=str(REPO_ROOT))


def runtime():
    # runtime/main.py imports bare `epw_os...` - it needs to run WITH
    # runtime/ as the working directory, not the repo root.
    return subprocess.call([sys.executable, "main.py"], cwd=str(REPO_ROOT / "runtime"))


def test():
    is_windows = sys.platform == "win32"
    steps = [
        ("runtime", [sys.executable, "-m", "pytest", "-q", "epw_os/tests", "gui_smoke"], REPO_ROOT / "runtime"),
        ("studio-logic", [sys.executable, "-m", "pytest", "-q", "studio/logic/tests"], REPO_ROOT),
        ("studio-shell", [sys.executable, "-m", "pytest", "-q", "studio/shell/tests"], REPO_ROOT),
        ("cross-platform", [sys.executable, "-m", "pytest", "-q", "shared/tests"], REPO_ROOT),
        ("studio-synoptic", ["npm", "test"], REPO_ROOT / "studio" / "synoptic"),
    ]
    failed = []
    for name, cmd, cwd in steps:
        print(f"\n=== {name} ===")
        use_shell = is_windows and cmd[0] == "npm"
        rc = subprocess.call(cmd, cwd=str(cwd), shell=use_shell)
        if rc != 0:
            failed.append(name)
    print()
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    print("All suites green.")
    return 0


COMMANDS = {"studio": studio, "runtime": runtime, "test": test}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        return 0 if len(sys.argv) == 1 else 1
    return COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    sys.exit(main())
