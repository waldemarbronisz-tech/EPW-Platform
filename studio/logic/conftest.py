"""Puts the repository root on sys.path so `shared.logic` (the block
library and the execution engine, shared with runtime) is importable
when this suite is started from the repository root or from
studio/logic. The suite's own package directory only ever put
studio/logic there, which is enough for `logic_studio` and nothing
else.
"""
import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
