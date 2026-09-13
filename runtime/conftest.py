"""Lets the runtime suites start from the repository root
(`python -m pytest runtime/epw_os/tests`), not only from runtime/.

epw_os/tests/ has no __init__.py, so pytest's default import mode puts
that test directory - not runtime/ - on sys.path, and the suite's own
conftest.py then fails on `from epw_os.tests import _db_guard` with
"No module named 'epw_os'". Being a conftest in runtime/ itself, this
file is loaded first for every test below it and puts runtime/ on the
path explicitly.
"""
import sys
from pathlib import Path

_RUNTIME_ROOT = str(Path(__file__).resolve().parent)
if _RUNTIME_ROOT not in sys.path:
    sys.path.insert(0, _RUNTIME_ROOT)
