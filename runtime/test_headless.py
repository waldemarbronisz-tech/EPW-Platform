import sys
import os
import tempfile

def check_no_qt():
    for mod in sys.modules:
        if mod.startswith("PyQt") or mod.startswith("PySide"):
            print(f"FAILED: Found Qt binding in {mod}")
            sys.exit(1)

# Task (fix/test-headless-scratch-path): EPWCore() takes no arguments -
# it always builds its own ProjectManager() with no path override,
# which then defaults to DEFAULT_PROJECT_FILE (the real, tracked
# runtime/project.json). core.startup() genuinely writes to it (e.g.
# switching-counter telemetry accumulated during the run) - so simply
# running this script, exactly as documented in this repo's own
# "before pushing" checklist, dirties the tracked project.json every
# time. Confirmed twice now (see MEMORY.md / SESSION_REPORT.md): once
# caught and reverted manually via git status/git diff, which is
# exactly the failure mode a checklist step should never depend on a
# human remembering.
#
# Fixed here, not in EPWCore or ProjectManager (GRANICE: "nie zmieniaj
# zachowania EPWCore", and what this script CHECKS - a full startup/
# shutdown cycle - must stay identical): redirect the MODULE-LEVEL
# name project_manager.py's __init__ actually reads from
# (`project_file or DEFAULT_PROJECT_FILE`) to a fresh temp file,
# before EPWCore (and therefore ProjectManager) is ever constructed.
# This must be the module attribute (`project_manager_module.
# DEFAULT_PROJECT_FILE`), not the class attribute
# (`ProjectManager.DEFAULT_PROJECT_FILE`) - a bare name inside a
# function body resolves against its own module's globals at call
# time, not via self/class lookup, so patching the class attribute
# would silently have no effect at all (confirmed the hard way in an
# earlier session - see MEMORY.md's own note on this exact distinction).
#
# See epw_os/tests/test_headless_script.py for the automated guard that
# fails loudly if this protection is ever removed or broken again.
import epw_os.core.project_manager as project_manager_module

_scratch_dir = tempfile.mkdtemp(prefix="epw_os_test_headless_")
project_manager_module.DEFAULT_PROJECT_FILE = os.path.join(_scratch_dir, "project.json")

from epw_os.core.epw_core import EPWCore
core = EPWCore()
core.startup()
print("Core started successfully.")
check_no_qt()
core.shutdown()
print("Core stopped successfully. Core is Qt-Free.")
