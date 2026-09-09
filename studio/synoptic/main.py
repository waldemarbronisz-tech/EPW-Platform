"""EPW Synoptic Editor - native desktop launcher.

Runs the existing editor (React + TypeScript + Konva, built by
`npm run build`) inside a native OS window via pywebview, instead of a
browser tab - no address bar, no tabs, no browser chrome. The frontend
itself is completely unchanged: this only serves the already-built
`dist/` folder over a local, loopback-only HTTP server and points a
pywebview window at that URL. On Windows, pywebview renders through the
WebView2 (Edge/Chromium) runtime that ships with the OS - same engine
the app already ran on in a browser tab, just without the browser's own
UI around it.

Usage:
    python main.py             Build dist/ if missing, then launch.
    python main.py --rebuild   Force a fresh `npm run build` first.
    python main.py --dev       Point the window at the Vite dev server
                                (run `npm run dev` yourself first) -
                                for iterating on the UI with hot reload
                                while still seeing it in the native shell.

Note on unsaved-changes-on-close: the app's own File > Exit menu item
asks for confirmation via the page's own window.confirm() dialog, same
as it always has. Closing the native window directly via its OS-level
close button used to skip that entirely - pywebview does not honor the
page's beforeunload handler the way a real browser tab does, so an
unsaved project could be lost with no warning at all. Fixed: the
window's own `closing` event (fired for EVERY close, OS button
included) is handled below - if there are unsaved changes, it shows a
native confirmation dialog before allowing the window to actually
close; declining it cancels the close, exactly as if the user had
clicked Cancel on the in-page File > Exit dialog.

The unsaved-changes state itself is PUSHED from the frontend into a
plain Python variable (main.tsx calls the exposed set_dirty() below
every time the store's own isDirty flag changes), not pulled via
window.evaluate_js() from the closing handler - a live test against
this exact pywebview version found that evaluate_js deadlocks every
single close when called from there: window.events.closing always
fires on the UI thread (WinForms raises FormClosing there regardless
of what triggered the close), and this version's WebView2 backend
resolves evaluate_js's result via a continuation scheduled onto that
same thread's synchronization context - which can never run while
that same thread is sitting there blocked, waiting for it. Reading a
plain Python attribute has no such dependency, so there is nothing to
deadlock on.
"""

import functools
import http.server
import shutil
import socket
import subprocess
import sys
import threading
from pathlib import Path

import webview

APP_TITLE = "EPW Synoptic Editor"
ROOT_DIR = Path(__file__).resolve().parent
DIST_DIR = ROOT_DIR / "dist"
DEV_SERVER_URL = "http://localhost:5173/"


def _npm_command() -> list[str]:
    # npm ships as npm.cmd on Windows - shutil.which resolves whichever
    # actual executable belongs to the platform this happens to run on.
    npm = shutil.which("npm")
    if not npm:
        print("[ERROR] npm was not found on PATH - install Node.js first (see README.md).")
        sys.exit(1)
    return [npm]


def build_frontend() -> None:
    print("[INFO] Building frontend (npm run build)...")
    result = subprocess.run(_npm_command() + ["run", "build"], cwd=ROOT_DIR)
    if result.returncode != 0:
        print("[ERROR] npm run build failed - see output above.")
        sys.exit(1)


def _free_port() -> int:
    # Bind to port 0 so the OS hands back an unused ephemeral port, then
    # release it immediately. The tiny window between this and the real
    # server binding the same port is the same race every "find a free
    # port" helper accepts - harmless here (loopback-only, one process).
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def serve_dist(port: int) -> None:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST_DIR))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    # Daemon thread: dies with the main process the instant the pywebview
    # window closes, with nothing else to shut down explicitly.
    threading.Thread(target=server.serve_forever, daemon=True).start()


# fix/audit-findings commit 2: the frontend's own current isDirty
# value, pushed here from main.tsx (via set_dirty below, exposed to JS
# as window.pywebview.api.set_dirty) every time it changes in the
# store - never pulled from Python via evaluate_js. See this file's
# own module docstring for exactly why: evaluate_js deadlocks when
# called from window.events.closing's handler in this pywebview
# version, confirmed with a live test before choosing this design
# (see raport.md). A plain module-level variable, read directly - no
# call across the JS/Python bridge happens at close time at all.
_is_dirty = False


def set_dirty(value: bool) -> None:
    """Exposed to the frontend (window.expose in main(), below) as
    window.pywebview.api.set_dirty - called from main.tsx whenever the
    store's own isDirty flag changes. Never called directly by this
    file; only by the frontend, across the pywebview JS bridge.
    """
    global _is_dirty
    _is_dirty = bool(value)


def _confirm_close(window: webview.Window) -> bool | None:
    """Handler for window.events.closing - fires for every close, the
    OS-level close button included (unlike the page's own beforeunload,
    which pywebview does not reliably honor). Returning False here
    cancels the close (webview.window.Window.events.closing is a
    cancelable event - see webview/event.py's own Event.set(): if any
    handler returns False, the platform backend sets args.Cancel=True
    and the window stays open). Returning None/True lets it proceed.
    """
    if not _is_dirty:
        return None

    return window.create_confirmation_dialog(
        APP_TITLE,
        "Masz niezapisane zmiany. Jesli zamkniesz teraz, zostana utracone. Zamknac mimo to?",
    )


def main() -> int:
    args = sys.argv[1:]
    dev_mode = "--dev" in args
    force_rebuild = "--rebuild" in args

    if dev_mode:
        url = DEV_SERVER_URL
        print(f"[INFO] Dev mode - pointing the window at {url} (run 'npm run dev' yourself first).")
    else:
        if force_rebuild or not (DIST_DIR / "index.html").exists():
            build_frontend()
        port = _free_port()
        serve_dist(port)
        url = f"http://127.0.0.1:{port}/"
        print(f"[INFO] Serving {DIST_DIR} at {url}")

    window = webview.create_window(APP_TITLE, url, width=1600, height=900, min_size=(1024, 700))
    window.expose(set_dirty)
    window.events.closing += _confirm_close
    webview.start()
    return 0


if __name__ == "__main__":
    sys.exit(main())
