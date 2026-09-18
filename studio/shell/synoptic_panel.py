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
import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtWidgets import QFileDialog, QLabel, QStackedWidget, QVBoxLayout, QWidget

from studio.shell.i18n import get_language, tr

SYNOPTIC_DIR = Path(__file__).resolve().parents[1] / "synoptic"
_SYNOPTIC_MAIN_PATH = SYNOPTIC_DIR / "main.py"

_PAGE_LOADING = 0
_PAGE_ERROR = 1
_PAGE_VIEW = 2

# Task "EPW Studio: jedna szata graficzna", 2.1 + 2.3 - applied on every
# load, not just as a Stage 1 probe. Stage 1 (test_style_overlay.py)
# proved both of these live-reflow cleanly with no reload:
#   - retint Synoptic's own chrome to shared/docs/STUDIO_UI_STANDARD.md
#     section 9's values, by overriding the --scada-*/--sys-* CSS custom
#     properties ScadaTheme.ts already reads everything from. Domain
#     colors (alarm/energized/water/...) are deliberately NOT in this
#     list - the standard never touches those, and neither does this.
#   - hide Synoptic's own File/Edit/View/Devices/Help bar AND its own
#     drawing/editing toolbar: both roles now belong to Studio's own
#     chrome (menus.py's build_fixed_menu() and, for the toolbar,
#     build_synoptic_context_toolbar() - reaching every one of these
#     same actions via trigger_menu_item()/trigger_toolbar_button()
#     below) - showing Synoptic's own copies at the same time is
#     exactly the "pięć pasów, dwa programy sklejone" problem task
#     "Studio: wyostrzenie stylu" 's Problem 1 exists to remove.
# No studio/synoptic/src/ change was needed for either - both are pure
# runtime CSS/DOM effects on the page Synoptic already serves.
_STUDIO_SKIN_JS = """
(function(){
    // Bug fix ("ten pasek nie działa" - Save/Open silently did
    // nothing): tells ProjectFileService.ts (src/types/file-system-
    // access.d.ts has the full story) that showOpenFilePicker/
    // showSaveFilePicker exist here but never actually resolve - so it
    // must use its own already-written browser-download/native-<input>
    // fallback instead, same as it would in a browser too old to have
    // the File System Access API at all.
    window.__EPW_STUDIO_EMBED__ = true;
    const root = document.documentElement;
    root.style.setProperty('--scada-panel', '#D4D0C8');
    root.style.setProperty('--scada-bevel-light', '#FFFFFF');
    root.style.setProperty('--scada-bevel-dark', '#808080');
    root.style.setProperty('--scada-outline', '#000000');
    root.style.setProperty('--scada-value-field', '#FFFFFF');
    root.style.setProperty('--scada-font-ui', 'Tahoma, "MS Sans Serif", sans-serif');
    root.style.setProperty('--scada-font-size-small', '11px');
    root.style.setProperty('--sys-highlight', '#000080');
    root.style.setProperty('--sys-highlight-text', '#FFFFFF');
    const bar = document.querySelector('.menu-bar');
    if (bar) bar.style.display = 'none';
    const toolbar = document.querySelector('.toolbar');
    if (toolbar) toolbar.style.display = 'none';
    return 'ok';
})();
"""


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


_SOURCE_ROOTS = ("src", "public")
_SOURCE_FILES = ("index.html", "package.json", "package-lock.json", "vite.config.ts", "vite.config.js",
                 "tsconfig.json", "tsconfig.app.json", "tsconfig.node.json")


def newest_source_mtime(root) -> float:
    """The newest modification time among the editor's sources - what a
    build depends on (src/ and public/ trees, the Vite/TS config files,
    the package manifest). 0.0 when nothing is there."""
    root = Path(root)
    newest = 0.0
    for name in _SOURCE_FILES:
        candidate = root / name
        if candidate.is_file():
            newest = max(newest, candidate.stat().st_mtime)
    for folder in _SOURCE_ROOTS:
        base = root / folder
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file():
                newest = max(newest, path.stat().st_mtime)
    return newest


def dist_is_stale(dist_dir, root) -> bool:
    """True when dist/index.html is missing or older than any source -
    then the frontend is built again before it is served."""
    index = Path(dist_dir) / "index.html"
    if not index.is_file():
        return True
    return newest_source_mtime(root) > index.stat().st_mtime


class SynopticPanel(QWidget):
    """One widget: builds/serves studio/synoptic/dist/ and shows it in
    a QWebEngineView.

    Construction USED to be deferred to the first EKRANY/SCREENS click,
    so a session that never opened the screen editor never paid
    Chromium's startup/memory cost. That is no longer the default:
    main_window.py's preload_editors() now builds this panel at startup,
    behind the splash, because paying the cost on first click is
    exactly what made arriving at this editor look like the whole
    application reloading (the loading page below is on screen for the
    0.35-1.05s the view needs). The cost did not disappear - it moved
    to a moment where it is covered. See preload_editors() for the
    trade-off in full; nothing about this class requires either choice,
    it is still perfectly safe to construct on demand.

    Never raises out of __init__: a build failure is caught and shown
    as an error page in this widget instead - the rest of Studio (the
    tree, the status bar, LOGIC) is never touched by it."""

    # Task "Studio: rejestr punktów" follow-up - fires once the page has
    # actually finished loading (query_device_registry()/
    # push_device_registry() are no-ops before that, same guard every
    # other bridge call already has). main_window.py uses this to run
    # the Cards/Locations sync at the one moment it can actually reach
    # the page, instead of guessing a delay.
    page_ready = Signal()

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

        # Bug fix ("ten pasek nie działa" - the shared Save/Save As
        # buttons produced no visible effect at all): QtWebEngine's
        # bundled Chromium has no File System Access API
        # (window.showSaveFilePicker/showOpenFilePicker are both
        # undefined), so ProjectFileService.saveFile()/saveFileAs()
        # (studio/synoptic/src/project/ProjectFileService.ts) always
        # falls through to their browser-download fallback: a Blob +
        # a hidden <a download> + .click(). Left unanswered, Qt's own
        # default for QWebEngineProfile.downloadRequested is to drop
        # the download silently - no dialog, no error, literally
        # nothing on screen, which is exactly what made the toolbar
        # look dead. Answering it with a real native Save dialog turns
        # that silent no-op into an actual .epwsyn file on disk.
        self._view.page().profile().downloadRequested.connect(self._on_download_requested)

        self._pages.setCurrentIndex(_PAGE_LOADING)

        try:
            launcher = _load_synoptic_launcher_module()
            # Rebuilt when MISSING or STALE: a dist/ older than the editor's
            # sources served the previous editor for days (user report
            # 2026-09-18: "nie działa kółko, rozciąganie pokoju rozjeżdża
            # się" - both already fixed in src/, never built).
            if dist_is_stale(launcher.DIST_DIR, launcher.ROOT_DIR):
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
        # The editor's interface follows Studio's own language.
        self._view.load(QUrl(f"http://127.0.0.1:{port}/?lang={get_language()}"))

    def _on_download_requested(self, download):
        """Answers QWebEngineProfile.downloadRequested - see the
        connect() call in __init__ for why this exists at all. `download`
        is a QWebEngineDownloadRequest; suggestedFileName() carries
        whatever name ProjectFileService.saveFileAs() proposed (the
        project's own file name, or "<project>.epwsyn" for a first
        save). Cancelling on a dismissed dialog is required, not just
        tidy - an accepted-then-abandoned QWebEngineDownloadRequest
        otherwise sits open."""
        suggested = download.suggestedFileName() or download.downloadFileName() or "project.epwsyn"
        path, _ = QFileDialog.getSaveFileName(
            self, tr("toolbar.save_as"), suggested, "EPW Synoptic Files (*.epwsyn)"
        )
        if not path:
            download.cancel()
            return
        target = Path(path)
        download.setDownloadDirectory(str(target.parent))
        download.setDownloadFileName(target.name)
        download.accept()

    def _on_load_finished(self, ok: bool):
        if ok:
            self._pages.setCurrentIndex(_PAGE_VIEW)
            self._view.page().runJavaScript(_STUDIO_SKIN_JS)
            self.page_ready.emit()
        else:
            self._show_error(tr("synoptic.load_failed"))

    def _show_error(self, message: str):
        self._error_label.setText(message)
        self._pages.setCurrentIndex(_PAGE_ERROR)

    def is_page_ready(self) -> bool:
        """True once the built page has actually finished loading - the
        same _PAGE_VIEW check every bridge method below already guards
        itself with, exposed so main_window.py can ask without reaching
        into this widget's privates."""
        return self._pages.currentIndex() == _PAGE_VIEW

    def is_page_pending(self) -> bool:
        """True while the page is still loading - neither ready NOR
        failed. Anything that WAITS for this panel must test this, not
        `not is_page_ready()`: a panel sitting on its build-failure page
        will never become ready, and waiting on that would burn the
        caller's entire timeout for nothing."""
        return self._pages.currentIndex() == _PAGE_LOADING

    def web_view(self):
        """Exposes the QWebEngineView itself - e.g. for
        page().runJavaScript(...) calls a later shared-project-tree
        task will need (Stage 1 already proved this round-trip works)."""
        return self._view

    def trigger_menu_item(self, text_fragment: str, exact: bool = False):
        """Fires one of Synoptic's own menu actions from Studio's shared
        menu (2.1) - Stage 1's test_menu_reachability.py proved a plain
        DOM .click() on the right `.dropdown-item` fires the real React
        onClick handler regardless of the item's CSS hover-visibility
        (now permanently display:none via _STUDIO_SKIN_JS above, not
        just hidden-on-hover). `exact` distinguishes e.g. "Save" from
        "Save As..." - matching by bare substring would hit whichever
        comes first in the DOM. Fire-and-forget: the caller (Studio's
        menu/toolbar action) doesn't need the result, only Synoptic's
        own on-screen effect."""
        if self._pages.currentIndex() != _PAGE_VIEW:
            return
        text_json = json.dumps(text_fragment)
        cmp_expr = f"t.textContent.trim() === {text_json}" if exact else f"t.textContent.includes({text_json})"
        js = (
            "(function(){"
            f"const t = Array.from(document.querySelectorAll('.dropdown-item')).find(t => {cmp_expr});"
            "if (t) { t.click(); return true; } return false;"
            "})();"
        )
        self._view.page().runJavaScript(js)

    def trigger_toolbar_button(self, title: str, exact: bool = True):
        """Fires one of Synoptic's own toolbar buttons (Toolbar.tsx) -
        now permanently display:none, same as the menu bar (see
        _STUDIO_SKIN_JS). Every button in that toolbar carries a real
        `title` attribute (used for its own native tooltip) - matched
        against that, not textContent, since these buttons render an
        icon, not text. `exact` defaults True here (unlike
        trigger_menu_item's default) because Toolbar.tsx's own titles
        are already short and specific enough that substring matching
        would be more likely to hit the wrong button (e.g. "Align
        Left"/"Align Center"/"Align Right" all share the substring
        "Align") than to help - callers pass exact=False only for a
        button whose title varies (none do, today)."""
        if self._pages.currentIndex() != _PAGE_VIEW:
            return
        title_json = json.dumps(title)
        cmp_expr = (
            f"b.getAttribute('title') === {title_json}"
            if exact
            else f"(b.getAttribute('title') || '').includes({title_json})"
        )
        js = (
            "(function(){"
            f"const b = Array.from(document.querySelectorAll('.toolbar button')).find(b => {cmp_expr});"
            "if (b) { b.click(); return true; } return false;"
            "})();"
        )
        self._view.page().runJavaScript(js)

    def trigger_command(self, command: str):
        """Clicks the Synoptic toolbar button whose stable data-cmd is
        `command` (Toolbar.tsx) - "mode:ROOMS", "draw_wall", "medium:WATER".
        Commands, unlike titles, do not change with the interface language.
        Fire-and-forget, like trigger_toolbar_button."""
        if self._pages.currentIndex() != _PAGE_VIEW:
            return
        selector = json.dumps(f'.toolbar [data-cmd="{command}"]')
        js = (
            "(function(){"
            f"const b = document.querySelector({selector});"
            "if (b) { b.click(); return true; } return false;"
            "})();"
        )
        self._view.page().runJavaScript(js)

    def query_state(self, callback):
        """Reads the read-only state bridge added to studio/synoptic/
        src/main.tsx (Blocker B of this task - approved for READ access
        only): whether there's anything to undo/redo, unsaved changes,
        and a selection. Used by Studio's shared toolbar (studio/shell/
        main_window.py) to decide whether Save/Undo/Redo may actually do
        anything right now - see this task's own "uściślenie 2.2": a
        button that's always clickable but sometimes a no-op is exactly
        what's being removed. `callback` receives a dict with keys
        canUndo/canRedo/isDirty/hasSelection, or None if the page hasn't
        loaded yet or (an old, un-rebuilt dist/) doesn't expose the
        bridge at all - the caller must treat None as "unknown", not as
        "everything false"."""
        if self._pages.currentIndex() != _PAGE_VIEW:
            callback(None)
            return
        js = (
            "typeof window.__synopticStudioState === 'function' "
            "? JSON.stringify(window.__synopticStudioState()) : ''"
        )

        def _handle(result):
            if not result:
                callback(None)
                return
            try:
                callback(json.loads(result))
            except ValueError:
                callback(None)

        self._view.page().runJavaScript(js, _handle)

    def query_canvas_background(self, callback):
        """Task "Studio: wyostrzenie stylu" Problem 4.3 - reads
        canvasConfig.background (a real project-file field,
        ProjectSchema.ts) through the read-only bridge main.tsx adds
        for exactly this. `callback` receives a "#RRGGBB" string, or
        None if the page hasn't loaded yet."""
        if self._pages.currentIndex() != _PAGE_VIEW:
            callback(None)
            return
        js = (
            "typeof window.__synopticCanvasBackground === 'function' "
            "? window.__synopticCanvasBackground() : ''"
        )

        def _handle(result):
            callback(result or None)

        self._view.page().runJavaScript(js, _handle)

    def set_canvas_background(self, hex_color: str):
        """The write half - calls the real store action (main.tsx's
        __synopticSetCanvasBackground bridge), so isDirty updates
        exactly as any other project edit would."""
        if self._pages.currentIndex() != _PAGE_VIEW:
            return
        js = (
            "typeof window.__synopticSetCanvasBackground === 'function' "
            f"&& window.__synopticSetCanvasBackground({json.dumps(hex_color)});"
        )
        self._view.page().runJavaScript(js)

    def query_device_registry(self, callback):
        """Task "Studio: rejestr punktów" follow-up ("most Cards/
        Locations do Synoptic") - reads Synoptic's OWN cards/locations
        (main.tsx's __synopticDeviceRegistry bridge) so Studio's Project
        can pick up cards/locations a user already defined inside
        Synoptic's own AddCardDialog/AddLocationDialog. `callback`
        receives {"cards": [...], "locations": [...], "devices": [...]}
        (Synoptic's own field names - channelKind/channelCount,
        code/description, DeviceSchema.ts's Device) or None if the page
        hasn't loaded / doesn't expose the bridge yet."""
        if self._pages.currentIndex() != _PAGE_VIEW:
            callback(None)
            return
        js = (
            "typeof window.__synopticDeviceRegistry === 'function' "
            "? JSON.stringify(window.__synopticDeviceRegistry()) : ''"
        )

        def _handle(result):
            if not result:
                callback(None)
                return
            try:
                callback(json.loads(result))
            except ValueError:
                callback(None)

        self._view.page().runJavaScript(js, _handle)

    def push_device_registry(self, cards, locations, devices=()):
        """The write half - ADDITIVE only (main.tsx's
        __synopticImportCardsAndLocations / __synopticImportDevices
        bridges skip any id/code they already have), never overwrites or
        removes an existing Synoptic card/location/device. `cards`/
        `locations`/`devices` are plain dicts already in Synoptic's OWN
        field-name shape (see main_window.py's
        _sync_device_registry_with_synoptic for the Card/Location/Device
        -> CardEntry/LocationEntry/Device field mapping)."""
        if self._pages.currentIndex() != _PAGE_VIEW:
            return
        js = (
            "typeof window.__synopticImportCardsAndLocations === 'function' "
            f"&& window.__synopticImportCardsAndLocations({json.dumps(cards)}, {json.dumps(locations)});"
        )
        if devices:
            js += (
                " typeof window.__synopticImportDevices === 'function' "
                f"&& window.__synopticImportDevices({json.dumps(list(devices))});"
            )
        self._view.page().runJavaScript(js)

    # -- the whole document in and out (task "Studio osadza ekrany i
    # logikę w projekt.epw") ---------------------------------------------
    # User report: "tworząc synoptykę w projekcie i zapisując projekt na
    # głównym pasku, synoptyka nie zapisuje się". The screens live INSIDE
    # projekt.epw now (shared/project_format.py's Project.screens) - Studio's
    # own Save reads this editor's document out through query_project_data(),
    # its Open/New hand one back through load_project_data(). main.tsx's
    # __synopticProjectData/__synopticLoadProjectData/__synopticMarkSaved -
    # see studio/synoptic/src/project/StudioBridge.ts.

    def query_project_data(self, callback):
        """`callback` receives the EPW_SYNOPTIC document as a dict, or
        None when the page isn't up, the bridge is missing (an old,
        un-rebuilt dist/) or the editor's own validation refused to
        produce a document (the same refusal its Save As shows)."""
        if self._pages.currentIndex() != _PAGE_VIEW:
            callback(None)
            return
        js = (
            "typeof window.__synopticProjectData === 'function' "
            "? (window.__synopticProjectData() || '') : ''"
        )

        def _handle(result):
            if not result:
                callback(None)
                return
            try:
                callback(json.loads(result))
            except ValueError:
                callback(None)

        self._view.page().runJavaScript(js, _handle)

    def load_project_data(self, document, name: str):
        """Replaces the editor's content with `document` (a dict - the
        project's `screens` section) or, when it is empty, with a fresh
        empty project named `name`. Clean afterwards - it is exactly what
        the project file holds."""
        if self._pages.currentIndex() != _PAGE_VIEW:
            return
        text = json.dumps(document) if document else None
        js = (
            "typeof window.__synopticLoadProjectData === 'function' "
            f"&& window.__synopticLoadProjectData({json.dumps(text)}, {json.dumps(name)});"
        )
        self._view.page().runJavaScript(js)

    def push_live_values(self, values):
        """{tag: value} from the controller (or None when live is off) -
        the editor shows device-bound symbols in their live state
        (src/store/liveSlice.ts)."""
        if self._pages.currentIndex() != _PAGE_VIEW:
            return
        payload = json.dumps(values) if values is not None else "null"
        js = (
            "typeof window.__synopticLiveValues === 'function' "
            f"&& window.__synopticLiveValues({json.dumps(payload)});"
        )
        self._view.page().runJavaScript(js)

    def mark_saved(self, name: str):
        """Studio just wrote projekt.epw with this editor's document inside."""
        if self._pages.currentIndex() != _PAGE_VIEW:
            return
        js = (
            "typeof window.__synopticMarkSaved === 'function' "
            f"&& window.__synopticMarkSaved({json.dumps(name)});"
        )
        self._view.page().runJavaScript(js)
