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

Two failure/latency modes this file exists specifically to handle
visibly, both found only by actually looking at what a real run
produces, not assumed from reading the code (see this task's own
correction - the first version of this file's screenshot showed an
empty grey rectangle, silently, and was reported as working without
that being checked):

1. Page load takes a real, measurable amount of time (Stage 1 measured
   0.35-1.05s) - during which the view is blank grey. A loading label
   covers it until QWebEngineView.loadFinished fires.
2. A failed `npm run build` (missing npm, a real build error) used to
   call sys.exit(1) INSIDE build_frontend() - inherited unchanged from
   studio/synoptic/main.py, where that is correct (the whole point of
   that process IS building+launching, so failure = exit). Inside the
   shell it is not correct - it must not take the rest of Studio down
   with it, and it did. Caught here (SystemExit is an exception like
   any other - catching it simply prevents the exit from actually
   happening) and turned into a visible, readable error message in
   this panel's own area instead. LOGIC stays completely unaffected -
   the failure never leaves this widget's __init__.
"""
import importlib.util
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

from studio.shell.i18n import tr

SYNOPTIC_DIR = Path(__file__).resolve().parents[1] / "synoptic"
_SYNOPTIC_MAIN_PATH = SYNOPTIC_DIR / "main.py"

_PAGE_LOADING = 0
_PAGE_ERROR = 1
_PAGE_VIEW = 2


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
    editor never pays Chromium's startup/memory cost at all.

    Never raises out of __init__: a build failure is caught and shown
    as an error page in this widget instead - the rest of Studio (the
    tree, the status bar, LOGIC) is never touched by it."""

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

        self._pages = QStackedWidget()
        layout.addWidget(self._pages)

        self._loading_label = QLabel(tr("synoptic.loading"))
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pages.addWidget(self._loading_label)   # index _PAGE_LOADING

        self._error_label = QLabel()
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.setWordWrap(True)
        self._pages.addWidget(self._error_label)      # index _PAGE_ERROR

        self._view = QWebEngineView(self)
        self._pages.addWidget(self._view)              # index _PAGE_VIEW

        self._pages.setCurrentIndex(_PAGE_LOADING)

        try:
            launcher = _load_synoptic_launcher_module()
            if not (launcher.DIST_DIR / "index.html").exists():
                launcher.build_frontend()
        except SystemExit as e:
            # build_frontend()/_npm_command() call sys.exit(1) on a
            # failed build or missing npm - see this file's own module
            # docstring, point 2. Caught here so it stays a Studio-wide
            # non-event: the rest of the shell (LOGIC included) is
            # never touched by this. e is intentionally unused beyond
            # confirming we actually caught a SystemExit, not
            # something else masquerading as one.
            self._show_error(tr("synoptic.build_failed"))
            return

        port = launcher._free_port()
        launcher.serve_dist(port)
        self._view.loadFinished.connect(self._on_load_finished)
        self._view.load(QUrl(f"http://127.0.0.1:{port}/"))

    def _on_load_finished(self, ok: bool):
        if ok:
            self._pages.setCurrentIndex(_PAGE_VIEW)
        else:
            self._show_error(tr("synoptic.load_failed"))

    def _show_error(self, message: str):
        self._error_label.setText(message)
        self._pages.setCurrentIndex(_PAGE_ERROR)

    def web_view(self):
        """Exposes the QWebEngineView itself - e.g. for
        page().runJavaScript(...) calls a later shared-project-tree
        task will need (Stage 1 already proved this round-trip works)."""
        return self._view
