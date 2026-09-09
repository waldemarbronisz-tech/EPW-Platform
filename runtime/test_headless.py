import sys
import os

def check_no_qt():
    for mod in sys.modules:
        if mod.startswith("PyQt") or mod.startswith("PySide"):
            print(f"FAILED: Found Qt binding in {mod}")
            sys.exit(1)
            
from epw_os.core.epw_core import EPWCore
core = EPWCore()
core.startup()
print("Core started successfully.")
check_no_qt()
core.shutdown()
print("Core stopped successfully. Core is Qt-Free.")
