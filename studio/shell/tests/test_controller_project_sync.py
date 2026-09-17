"""Task "wysyłanie projektu na sterownik przez REST" - Studio's side.
"Wyślij do urządzenia" / "Zgraj z urządzenia" on the controller panel,
driven against a small HTTP server that answers exactly like runtime's
project endpoints (revision + settings_hash header, settings for the
diff, Engineer-token upload with the expected_revision guard, download).
Real StudioMainWindow, real saved projekt.epw; only the modal boxes are
stubbed (a modal blocks forever offscreen).
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from studio.shell.main_window import StudioMainWindow
from studio.shell.project_format import (ElectricalProtectionStage, load_project, new_project, save_project,
                                         settings_hash, settings_snapshot)

ENGINEER = "engineer-token"


class FakeController:
    """runtime's /api/v1/project* endpoints, in memory."""

    def __init__(self, project_bytes, revision, modified_by="panel", settings=None, stored_hash=None):
        self.project_bytes = project_bytes
        self.revision = revision
        self.modified_by = modified_by
        self.settings = settings or {}
        self.settings_hash = stored_hash
        self.installed = []          # (bytes, expected_revision, restart)
        self.requests = []
        controller = self

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

            def _engineer(self):
                return self.headers.get("Authorization") == f"Bearer {ENGINEER}"

            def do_GET(self):
                controller.requests.append(("GET", self.path))
                if self.path == "/api/v1/project":
                    self._json(200, {"loaded": True, "revision": controller.revision,
                                     "modified_by": controller.modified_by, "settings_hash": controller.settings_hash})
                elif self.path == "/api/v1/project/settings":
                    self._json(200, {"loaded": True, "revision": controller.revision,
                                     "settings_hash": controller.settings_hash, "settings": controller.settings})
                elif self.path == "/api/v1/project/file":
                    if not self._engineer():
                        self._json(401, {"detail": "Engineer token required"})
                        return
                    self.send_response(200)
                    self.send_header("Content-Type", "application/gzip")
                    self.send_header("Content-Length", str(len(controller.project_bytes)))
                    self.end_headers()
                    self.wfile.write(controller.project_bytes)
                else:
                    self._json(404, {"detail": "no"})

            def do_POST(self):
                path, _, query = self.path.partition("?")
                controller.requests.append(("POST", self.path))
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length)
                if path != "/api/v1/project/install":
                    self._json(404, {"detail": "no"})
                    return
                if not self._engineer():
                    self._json(401, {"detail": "Engineer token required"})
                    return
                params = dict(p.split("=") for p in query.split("&") if p)
                expected = int(params["expected_revision"]) if "expected_revision" in params else None
                if expected is not None and expected != controller.revision:
                    self._json(409, {"detail": {"error": "revision_mismatch", "expected_revision": expected,
                                                "controller": {"revision": controller.revision,
                                                               "modified_by": controller.modified_by}}})
                    return
                if not body.startswith(b"\x1f\x8b"):
                    self._json(400, {"detail": {"error": "project_refused",
                                                "reason": {"key": "x", "params": {}, "text": "not a project"}}})
                    return
                controller.installed.append((body, expected, params.get("restart", "true")))
                controller.project_bytes = body
                controller.revision += 1
                self._json(200, {"installed": True, "revision": controller.revision, "restart_scheduled": True})

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def _app():
    return QApplication.instance() or QApplication([])


def _stage(setting):
    return ElectricalProtectionStage(function_id="50 Instantaneous Overcurrent", stage_name="Stage 1", enabled=True,
                                     setting=setting, hysteresis=3.0, delay_ms=150, action="Trip")


def _saved_project(tmp_path, name="Site", setting=25.0):
    project = new_project(name, author="t")
    project.electrical_protection_stages = [_stage(setting)]
    path = tmp_path / "studio" / "projekt.epw"
    save_project(project, path)
    return path


def _window(tmp_path, project_path, controller_url, token=ENGINEER):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    settings.setValue("controller/host", controller_url)
    settings.setValue("controller/token", token)
    win = StudioMainWindow(settings=settings)
    win._load_project_from_path(str(project_path))
    win._open_controller()
    return win


def _quiet_boxes(monkeypatch, answer=QMessageBox.StandardButton.Yes):
    shown = {"info": [], "warn": [], "question": []}
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: shown["info"].append(a[2]) or QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: shown["warn"].append(a[2]) or QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: shown["question"].append(a[2]) or answer)
    return shown


def _close(win):
    """A window left alive keeps polling its panels on timers during later
    tests - stop them and detach the fake panel. No deleteLater(): the
    other window-building tests leave their windows alive too, and a
    window deleted under a running suite surfaces as "already deleted"
    QActions in whatever test pumps the event loop next."""
    from PySide6.QtCore import QTimer
    for timer in win.findChildren(QTimer):
        timer.stop()
    win._synoptic_panel = None
    win.hide()


def test_send_uploads_the_saved_file_with_the_controllers_revision_as_the_guard(tmp_path, monkeypatch):
    _app()
    path = _saved_project(tmp_path)
    local = load_project(path)
    controller = FakeController(path.read_bytes(), revision=4, stored_hash=settings_hash(local))
    win = _window(tmp_path, path, controller.url)
    shown = _quiet_boxes(monkeypatch)
    try:
        panel = win._controller_panel
        panel._confirm_overwrite = lambda *a: (_ for _ in ()).throw(AssertionError("no diff expected"))
        panel._send_to_device()
        assert shown["question"] == []                       # saved and clean: no save prompt
        assert len(controller.installed) == 1
        body, expected, _restart = controller.installed[0]
        assert body == path.read_bytes() and expected == 4
        assert shown["warn"] == [] and shown["info"] and "5" in shown["info"][0]   # the new revision
        assert "5" in panel.status_label.text()
    finally:
        _close(win)
        controller.close()


def test_send_saves_first_when_the_project_is_dirty(tmp_path, monkeypatch):
    _app()
    path = _saved_project(tmp_path)
    controller = FakeController(path.read_bytes(), revision=1, stored_hash=settings_hash(load_project(path)))
    win = _window(tmp_path, path, controller.url)
    shown = _quiet_boxes(monkeypatch)
    try:
        win._project.electrical_protection_stages[0].setting = 30.0
        win._project.touch()
        before = path.read_bytes()
        panel = win._controller_panel
        panel._confirm_overwrite = lambda header, local, diff: True
        panel._send_to_device()
        assert shown["question"]                              # asked to save
        assert path.read_bytes() != before                    # saved
        assert controller.installed and controller.installed[0][0] == path.read_bytes()
        assert load_project(path).electrical_protection_stages[0].setting == 30.0
    finally:
        _close(win)
        controller.close()


def test_send_shows_the_settings_that_differ_and_stops_when_the_operator_says_so(tmp_path, monkeypatch):
    _app()
    path = _saved_project(tmp_path, setting=25.0)
    on_controller = new_project("Site", author="t")
    on_controller.electrical_protection_stages = [_stage(40.0)]          # the panel changed it to 40 A
    controller = FakeController(path.read_bytes(), revision=9, settings=settings_snapshot(on_controller),
                                stored_hash=settings_hash(on_controller))
    win = _window(tmp_path, path, controller.url)
    shown = _quiet_boxes(monkeypatch)
    try:
        panel = win._controller_panel
        seen = []

        def confirm(header, local, diff):
            seen.append((header["revision"], local.revision, diff))
            return False
        panel._confirm_overwrite = confirm
        panel._send_to_device()
        assert seen == [(9, 1, [("electrical_protection_stages/50 Instantaneous Overcurrent / Stage 1/setting",
                                  25.0, 40.0)])]
        assert controller.installed == [] and shown["info"] == []

        panel._confirm_overwrite = lambda header, local, diff: True
        panel._send_to_device()
        assert len(controller.installed) == 1 and controller.installed[0][1] == 9
    finally:
        _close(win)
        controller.close()


def test_the_diff_dialog_lists_every_difference(tmp_path):
    _app()
    from studio.shell.project_panels import SettingsDiffDialog
    local = load_project(_saved_project(tmp_path))
    dialog = SettingsDiffDialog({"revision": 3, "modified_by": "panel"}, local,
                                [("zones/Z1/exit_delay_seconds", 10.0, 20.0), ("lines/L1/alarm_hold_seconds", None, 5)])
    assert dialog.table.rowCount() == 2
    assert dialog.table.item(0, 1).text() == "10.0" and dialog.table.item(0, 2).text() == "20.0"
    assert dialog.table.item(1, 1).text() == "" and dialog.table.item(1, 2).text() == "5"
    dialog.deleteLater()


def test_send_reports_a_controller_that_moved_on_and_a_missing_token(tmp_path, monkeypatch):
    _app()
    path = _saved_project(tmp_path)
    controller = FakeController(path.read_bytes(), revision=2, stored_hash=settings_hash(load_project(path)))
    win = _window(tmp_path, path, controller.url)
    shown = _quiet_boxes(monkeypatch)
    try:
        panel = win._controller_panel
        # The controller's revision changes between the header read and the post.
        original = panel._request

        def racing(path_, **kw):
            if path_ == "/api/v1/project":
                ok, header = original(path_, **kw)
                controller.revision += 1
                return ok, header
            return original(path_, **kw)
        panel._request = racing
        panel._send_to_device()
        assert controller.installed == []
        assert shown["warn"] and "3" in shown["warn"][-1]     # names the controller's current revision
        panel._request = original

        panel.token_edit.setText("")
        panel._send_to_device()
        assert controller.installed == []
        assert "401" in shown["warn"][-1]
    finally:
        _close(win)
        controller.close()


def test_receive_downloads_the_controllers_file_and_opens_it(tmp_path, monkeypatch):
    _app()
    path = _saved_project(tmp_path, name="Laptop copy")
    remote = new_project("Controller copy", author="panel")
    remote.electrical_protection_stages = [_stage(40.0)]
    remote_path = tmp_path / "remote" / "projekt.epw"
    save_project(remote, remote_path)
    save_project(remote, remote_path)                                     # revision 2
    controller = FakeController(remote_path.read_bytes(), revision=2)
    win = _window(tmp_path, path, controller.url)
    shown = _quiet_boxes(monkeypatch)
    target = tmp_path / "received" / "projekt.epw"
    target.parent.mkdir()
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(target), "")))
    try:
        panel = win._controller_panel
        panel._receive_from_device()
        assert target.read_bytes() == remote_path.read_bytes()
        assert win._project.metadata.name == "Controller copy" and win._project.revision == 2
        assert win._project_path == str(target)
        assert shown["warn"] == [] and "2" in panel.status_label.text()

        panel.token_edit.setText("")
        panel._receive_from_device()
        assert "401" in shown["warn"][-1]
    finally:
        _close(win)
        controller.close()
