"""Embeds the Synoptic Editor (React + TypeScript + Konva, built by
`npm run build`) inside the EPW Studio shell's editor area.

# --- QtWebEngine: studio/ ONLY, never runtime/ ---------------------------
# This is the ONE and ONLY place in this whole platform that may import
# PySide6.QtWebEngineWidgets. Stage 1 of the "EPW Studio, powloka" task
# measured three embedding options for exactly this editor and found
# QWebEngineView the clear, working choice (rendering/mouse/keyboard/
# drag-and-drop/Python<->JS calls all verified against the real running
# app - see spike/studio_shell_probe/). That result does NOT extend to
# runtime/: EPW-OS runs on an Orange Pi, not a workstation, and the
# reasons QtWebEngine was already ruled out there in an earlier task
# (SYMBOL_RENDERING_PATHS.md's Path B costing) still hold exactly as
# they did before this file existed -
#   - Qt WebEngine is a full embedded Chromium build: ~150-300+ MB
#     resident just for an idle, content-empty view, before drawing
#     anything - a large fraction of an Orange Pi's total RAM.
#   - "praca miesiacami bez restartu" (the runtime's own deployment
#     requirement) is in tension with Chromium's well-documented
#     long-uptime memory growth - mitigated in real browsers by
#     periodically recycling tabs/processes, a pattern the runtime's
#     single always-on kiosk screen has no equivalent of.
#   - Kiosk Mode today is a single-process PySide6 window; Qt
#     WebEngine's multi-process Chromium sandbox is a materially
#     different crash/restart story runtime/ has never needed before.
#   - Whether a working PySide6-Addons wheel with Qt WebEngine even
#     installs on the actual target aarch64/Orange Pi image was
#     EXPLICITLY left unverified in that earlier task - "works great on
#     a Windows/Linux workstation" (confirmed again here) says nothing
#     about whether it is even available on the deployment target.
# Studio runs on a developer's PC (Windows/Linux), never the
# controller - none of the above applies here, which is exactly why
# this file may use QtWebEngine and nothing under runtime/ may.
# ---------------------------------------------------------------------

Reuses studio/synoptic/main.py's own build/serve helpers (loaded by
file path below, not a package import - that script has no __init__.py
package structure of its own to import from) rather than duplicating
"build dist/ if missing, serve it over a loopback HTTP server" logic a
second time. studio/synoptic/main.py itself is untouched (GRANICE:
"nie przepisuj Synoptica") - this only reads functions off it.
"""
import importlib.util
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QVBoxLayout, QWidget

from studio.shell.i18n import tr

SYNOPTIC_DIR = Path(__file__).resolve().parents[1] / "synoptic"
_SYNOPTIC_MAIN_PATH = SYNOPTIC_DIR / "main.py"


def _load_synoptic_launcher_module():
    """Loads studio/synoptic/main.py as a plain module by file path -
    NOT via `import`, since that script sits outside any Python package
    and has no __init__.py of its own (it's a standalone launcher, not
    a library). This is the standard, safe way to reuse a sibling
    script's functions without restructuring it into a package - see
    importlib's own docs for "importing a source file directly"."""
    spec = importlib.util.spec_from_file_location("epw_synoptic_launcher", _SYNOPTIC_MAIN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SynopticPanel(QWidget):
    """One widget: builds/serves studio/synoptic/dist/ and shows it in
    a QWebEngineView. Construction is intentionally lazy (only happens
    the first time EKRANY/SCREENS is actually clicked - see
    main_window.py) so a shell session that never opens the screen
    editor never pays Chromium's startup/memory cost at all."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Imported here, not at module level: the module-level docstring
        # above is the one place allowed to explain WHY, but the actual
        # import should still only happen when a SynopticPanel is truly
        # being constructed (belt-and-suspenders against ever importing
        # QtWebEngine from a code path runtime/ could somehow reach).
        from PySide6.QtWebEngineWidgets import QWebEngineView

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._view = QWebEngineView(self)
        layout.addWidget(self._view)

        launcher = _load_synoptic_launcher_module()
        if not (launcher.DIST_DIR / "index.html").exists():
            launcher.build_frontend()
        port = launcher._free_port()
        launcher.serve_dist(port)
        self._view.load(QUrl(f"http://127.0.0.1:{port}/"))

    def web_view(self):
        """Exposes the QWebEngineView itself - e.g. for
        page().runJavaScript(...) calls a later shared-project-tree
        task will need (Stage 1 already proved this round-trip works)."""
        return self._view
