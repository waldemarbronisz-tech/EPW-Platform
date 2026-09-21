"""SPEC "Widok główny": F11 in Studio shows the main view screen full
screen as the panel shows it - Studio's own chrome hidden, the editor's
PanelPreview asked for - and while it is on, the commands clicked in a
live preview go to the controller (POST /api/v1/commands) and Esc in the
editor brings Studio's window back. Against a fake editor panel and a
fake controller."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from studio.shell.main_window import StudioMainWindow, _TREE_ITEM_SCREENS
from studio.shell.project_format import new_project, save_project
from studio.shell.tests.test_controller_project_sync import ENGINEER, _close


def _app():
    return QApplication.instance() or QApplication([])


class FakeCommandController:
    """runtime's POST /api/v1/commands: KOT_KM1 obeys, KOT_Q1 is blocked."""

    def __init__(self):
        self.received = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _json(self, code, body):
                data = json.dumps(body).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                if self.headers.get("Authorization") != f"Bearer {ENGINEER}":
                    self._json(401, {"detail": "token required"})
                    return
                if self.path != "/api/v1/commands":
                    self._json(404, {"detail": "no"})
                    return
                fake.received.append(body)
                if body["device_tag"] == "KOT_Q1":
                    self._json(403, {"detail": {"error": "Command Blocked", "reasons": ["Interlock: door open"]}})
                    return
                self._json(200, {"command_id": "c1", "state": "FEEDBACK_PENDING", "reason": "", "actor": "API:Engineer"})

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class FakeSynopticPanel:
    """The editor as Studio sees it through synoptic_panel.py's bridges."""

    def __init__(self):
        self.entered = []
        self.exited = 0
        self.state = {"canUndo": False, "canRedo": False, "isDirty": False, "hasSelection": False, "panelPreview": False}
        self.commands = []
        self.focused = 0

    def is_page_ready(self):
        return True

    def enter_panel_preview(self, screen_id=None):
        self.entered.append(screen_id)
        self.state["panelPreview"] = True

    def exit_panel_preview(self):
        self.exited += 1
        self.state["panelPreview"] = False

    def query_state(self, callback):
        callback(dict(self.state))

    def take_pending_commands(self, callback):
        commands, self.commands = self.commands, []
        callback(commands)

    def web_view(self):
        panel = self

        class _View:
            def setFocus(self):
                panel.focused += 1
        return _View()

    def push_live_values(self, values):
        pass


def _window(tmp_path, url):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    settings.setValue("controller/host", url)
    settings.setValue("controller/token", ENGINEER)
    win = StudioMainWindow(settings=settings)
    path = tmp_path / "projekt.epw"
    save_project(new_project("Preview", author="t"), path)
    win._load_project_from_path(str(path))
    win._synoptic_panel = FakeSynopticPanel()
    win._active = _TREE_ITEM_SCREENS
    return win


def test_f11_hides_studios_chrome_and_asks_the_editor_for_the_panel_preview_until_it_ends(tmp_path):
    _app()
    fake = FakeCommandController()
    win = _window(tmp_path, fake.url)
    win.show()
    try:
        panel = win._synoptic_panel
        assert win.menuBar().isVisible() and win._left_splitter.isVisible()
        assert win.enter_panel_preview() is True
        assert win.panel_preview_active() and panel.entered == [None] and panel.focused == 1
        assert not win.menuBar().isVisible() and not win._left_splitter.isVisible()
        assert not win._shared_toolbar.isVisible() and not win.statusBar().isVisible()
        assert win._panel_preview_timer.isActive()
        # F11 again toggles back.
        win.toggle_panel_preview()
        assert not win.panel_preview_active() and panel.exited == 1
        assert win.menuBar().isVisible() and win._left_splitter.isVisible() and win.statusBar().isVisible()

        # Esc pressed in the editor: its state drops panelPreview, the next tick brings Studio back.
        win.toggle_panel_preview()
        assert win.panel_preview_active() and panel.entered == [None, None]
        panel.state["panelPreview"] = False
        win._panel_preview_tick()
        assert not win.panel_preview_active() and win.menuBar().isVisible()
    finally:
        _close(win)
        fake.close()


def test_commands_clicked_in_a_live_preview_reach_the_controller_and_refusals_are_named(tmp_path):
    _app()
    fake = FakeCommandController()
    win = _window(tmp_path, fake.url)
    try:
        panel = win._synoptic_panel
        assert win.enter_panel_preview("s2") is True and panel.entered == ["s2"]
        panel.commands = [{"deviceId": "KOT_KM1", "action": "CLOSE"}, {"deviceId": "KOT_Q1", "action": "OPEN"}]
        win._panel_preview_tick()
        assert fake.received == [{"device_tag": "KOT_KM1", "command": "CLOSE"}, {"device_tag": "KOT_Q1", "command": "OPEN"}]
        assert "Interlock: door open" in win.statusBar().currentMessage()
        assert panel.commands == []          # drained
        assert win.relay_commands([{"deviceId": "KOT_KM1", "action": "OPEN"}]) == 1
        assert win.relay_commands([{"deviceId": "KOT_Q1", "action": "OPEN"}]) == 0
    finally:
        win.exit_panel_preview()
        _close(win)
        fake.close()
