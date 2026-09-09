"""Single source of truth for the application name/version string.

Both the status bar (main_window.py) and the Help > About dialog read
from here instead of each hardcoding their own literal - previously only
the status bar had one ("v1.0.0", not referenced anywhere else), so there
was nothing yet to drift *from*, but a second hardcoded copy would have
started that drift immediately.
"""

APP_NAME = "EPW OS"
__version__ = "1.0.0"
