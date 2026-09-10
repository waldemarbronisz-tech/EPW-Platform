"""SPIKE probe (Stage 1): does QWebEngineView loading studio/synoptic's
real dist/ actually render, accept input, and let Python call into the
page and get a response back? Not part of the shell - throwaway,
answers the question empirically before building anything on top of it.
"""
import functools
import http.server
import socket
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView

REPO_ROOT = Path(__file__).resolve().parents[2]
DIST_DIR = REPO_ROOT / "studio" / "synoptic" / "dist"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def serve_dist(port: int):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST_DIR))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()


def main():
    t_start = time.time()
    app = QApplication(sys.argv)

    port = free_port()
    serve_dist(port)
    url = f"http://127.0.0.1:{port}/"

    window = QMainWindow()
    window.resize(1400, 900)
    view = QWebEngineView()
    window.setCentralWidget(view)
    window.show()

    results = {}

    def on_load_finished(ok):
        results["load_ok"] = ok
        results["load_time_s"] = time.time() - t_start
        print(f"[PROBE] load finished, ok={ok}, elapsed={results['load_time_s']:.2f}s")

        # Screenshot right after load (before any interaction) -
        # confirms the editor actually painted something, not a blank page.
        window.grab().save(str(Path(__file__).parent / "shot_1_loaded.png"))

        # Give React/Konva a moment to finish its own async init (store
        # hydration, canvas mount) before probing further.
        QTimer.singleShot(1500, after_settle)

    def after_settle():
        window.grab().save(str(Path(__file__).parent / "shot_2_settled.png"))

        # --- Python -> JS call, with a response read back in Python ---
        # This is the exact capability the shared-project-tree work will
        # need later: can Python ask the page something and get an
        # answer, not just fire-and-forget?
        script = "document.title + '|' + document.querySelectorAll('*').length"
        view.page().runJavaScript(script, on_js_result)

    def on_js_result(value):
        results["js_call_result"] = value
        print(f"[PROBE] runJavaScript result: {value!r}")
        QTimer.singleShot(300, try_input)

    def try_input():
        # A synthetic mouse click INTO the web view's own viewport -
        # proves input events actually reach the embedded page, not
        # just that pixels got painted. Clicking blank canvas space is
        # enough to prove event delivery without needing to know the
        # exact DOM/toolbox layout in advance.
        center = view.rect().center()
        press = QMouseEvent(QMouseEvent.Type.MouseButtonPress, center, Qt.MouseButton.LeftButton,
                             Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        release = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, center, Qt.MouseButton.LeftButton,
                               Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(view, press)
        QApplication.sendEvent(view, release)
        print("[PROBE] sent synthetic mouse click to the view")
        QTimer.singleShot(500, place_symbol)

    def place_symbol():
        # Real interaction test #2: drive the app's OWN drag-and-drop
        # code path (Canvas.tsx's handleDrop reads
        # dataTransfer.getData('application/reactflow')) by dispatching
        # a synthetic HTML5 DragEvent with a constructed DataTransfer -
        # this is the actual application logic a real drag from the
        # Object Library would trigger, not a shortcut through the
        # store. Proves this isn't just a static picture - the running
        # app's own event handlers fire and mutate its own state.
        script = """
        (function() {
            const el = document.querySelector('.canvas-container');
            if (!el) return 'NO_CANVAS_CONTAINER';
            const rect = el.getBoundingClientRect();
            const dt = new DataTransfer();
            dt.setData('application/reactflow', JSON.stringify({type: 'electrical.circuit_breaker', category: 'Electrical'}));
            const dropEvent = new DragEvent('drop', {
                bubbles: true, cancelable: true, dataTransfer: dt,
                clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2
            });
            el.dispatchEvent(dropEvent);
            return 'DISPATCHED';
        })();
        """
        view.page().runJavaScript(script, on_drop_dispatched)

    def on_drop_dispatched(result):
        print(f"[PROBE] synthetic drop dispatch result: {result!r}")
        # Arm a page-side listener BEFORE sending a real Qt key event -
        # proves a genuine QKeyEvent delivered to the view reaches the
        # page's own JS event loop, not just that runJavaScript works.
        view.page().runJavaScript(
            "window.__probeKeyLog = []; "
            "window.addEventListener('keydown', e => window.__probeKeyLog.push(e.key));",
            lambda _: send_real_key(),
        )

    def send_real_key():
        window.activateWindow()
        window.raise_()
        view.setFocus(Qt.FocusReason.OtherFocusReason)
        print(f"[PROBE] view.hasFocus()={view.hasFocus()} focusProxy={view.focusProxy()}")
        from PySide6.QtTest import QTest
        target = view.focusProxy() or view
        QTest.keyClick(target, Qt.Key.Key_A)
        QTimer.singleShot(500, check_key_received)

    def check_key_received():
        view.page().runJavaScript(
            "JSON.stringify({type: typeof window.__probeKeyLog, val: window.__probeKeyLog, active: document.activeElement && document.activeElement.tagName})",
            on_key_check_result,
        )

    def on_key_check_result(value):
        results["keydown_reached_page"] = value
        print(f"[PROBE] keydown log seen by the page: {value!r}")
        QTimer.singleShot(300, finish)

    def finish():
        window.grab().save(str(Path(__file__).parent / "shot_3_after_click.png"))
        print("[PROBE] RESULTS:", results)
        app.quit()

    view.loadFinished.connect(on_load_finished)
    view.load(QUrl(url))

    QTimer.singleShot(20000, app.quit)  # safety timeout
    app.exec()


if __name__ == "__main__":
    main()
