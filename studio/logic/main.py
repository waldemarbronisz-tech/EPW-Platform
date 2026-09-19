import sys
from pathlib import Path

# The block library and the execution engine live in shared/logic/ (they
# are the contract with runtime, which executes what this editor
# compiles), so the repository root has to be importable - this file's own
# directory is what Python puts on the path when it is run directly.
_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from logic_studio.app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
