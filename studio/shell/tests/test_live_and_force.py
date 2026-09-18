"""SPEC "Studio - sterownik - połączenie na żywo" and "Wymuszanie
stanów": with "Na żywo" on, the point registry shows the controller's
values (forced ones red), the cards say whether the module answers, the
Synoptic editor receives the values; force mode is deliberate (a warning,
Engineer token), a force is set from a row and everything is dropped in
one move. Against a fake controller serving /api/v1/tags and /api/v1/forces."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

from studio.shell.main_window import StudioMainWindow
from studio.shell.project_format import Card, Location, new_project, save_project
from studio.shell.project_panels import sync_points_for_card
from studio.shell.tests.test_controller_project_sync import ENGINEER, _close

import pytest


def _app():
    return QApplication.instance() or QApplication([])


class FakeLiveController:
    """runtime's tags and forces, in memory; forces need the Engineer token."""

    def __init__(self):
        self.tags = {"ELA1.DI.1": {"value": True, "quality": "GOOD"}, "ELA1.DI.2": {"value": False, "quality": "COMM_FAILURE"},
                     "ELA1.AI.1": {"value": 21.5, "quality": "GOOD"}, "Safety.ELA1.Healthy": {"value": True, "quality": "GOOD"},
                     "Safety.ADA1.Healthy": {"value": False, "quality": "GOOD"}}
        self.forces = {}
        self.heartbeats = 0
        self.refuse = set()
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

            def _engineer(self):
                return self.headers.get("Authorization") == f"Bearer {ENGINEER}"

            def _forces_body(self):
                return {"forces": [{"tag": t, **e} for t, e in sorted(fake.forces.items())], "heartbeat_timeout_s": 15,
                        "seconds_since_heartbeat": 0}

            def do_GET(self):
                if self.path == "/api/v1/tags":
                    self._json(200, [{"name": n, "data_type": "BOOL", "timestamp": 0, **e} for n, e in fake.tags.items()])
                elif self.path == "/api/v1/forces":
                    self._json(200, self._forces_body())
                else:
                    self._json(404, {"detail": "no"})

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length)
                if not self._engineer():
                    self._json(401, {"detail": "Engineer token required"})
                    return
                if self.path == "/api/v1/forces/heartbeat":
                    fake.heartbeats += 1
                    self._json(200, self._forces_body())
                elif self.path == "/api/v1/forces":
                    data = json.loads(body)
                    if data["tag"] in fake.refuse:
                        self._json(403, {"detail": {"error": "force_refused", "reason": "on the protection path"}})
                        return
                    fake.forces[data["tag"]] = {"value": data["value"], "kind": "DI", "actor": "API:Engineer", "since": 0}
                    fake.tags.setdefault(data["tag"], {})["value"] = data["value"]
                    self._json(200, {"forced": True, **self._forces_body()})
                else:
                    self._json(404, {"detail": "no"})

            def do_DELETE(self):
                if not self._engineer():
                    self._json(401, {"detail": "Engineer token required"})
                    return
                if self.path == "/api/v1/forces":
                    count = len(fake.forces)
                    fake.forces.clear()
                    self._json(200, {"released": count, **self._forces_body()})
                elif self.path.startswith("/api/v1/forces/"):
                    tag = self.path[len("/api/v1/forces/"):]
                    if tag not in fake.forces:
                        self._json(404, {"detail": "not forced"})
                        return
                    del fake.forces[tag]
                    self._json(200, {"released": True, **self._forces_body()})
                else:
                    self._json(404, {"detail": "no"})

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def _project_path(tmp_path):
    project = new_project("Live", author="t")
    project.locations = [Location("KOT", "Kotlownia")]
    for card in (Card("ELA1", "ELA", channel_kinds={"DI": 2, "AI": 1}, location="KOT"),
                 Card("ADA1", "ADA", channel_kinds={"DO": 1}, location="KOT")):
        project.cards.append(card)
        sync_points_for_card(project, card)
    path = tmp_path / "projekt.epw"
    save_project(project, path)
    return path


def _window(tmp_path, url, token=ENGINEER):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    settings.setValue("controller/host", url)
    settings.setValue("controller/token", token)
    win = StudioMainWindow(settings=settings)
    win._load_project_from_path(str(_project_path(tmp_path)))
    return win


class FakeSynopticPanel:
    def __init__(self):
        self.pushed = []

    def is_page_ready(self):
        return True

    def push_live_values(self, values):
        self.pushed.append(values)


def test_live_fills_the_point_registry_the_cards_and_the_editor(tmp_path):
    _app()
    fake = FakeLiveController()
    win = _window(tmp_path, fake.url)
    try:
        win._open_point_registry()
        win._open_io_cards()
        win._synoptic_panel = FakeSynopticPanel()
        assert not win.live_enabled()
        win._toggle_live(True)
        assert win.live_enabled() and win.live_monitor().connected
        rows = dict((a, (text, forced)) for a, text, forced in win._point_registry_panel.live_rows())
        assert rows["ELA1.DI.1"] == ("1", False)
        assert rows["ELA1.DI.2"] == ("0 (COMM_FAILURE)", False)
        assert rows["ELA1.AI.1"] == ("21.5", False)
        assert rows["ADA1.DO.1"] == ("", False)                                  # the controller has no such tag
        assert dict(win._cards_panel.responds_rows()) == {"ELA1": "tak", "ADA1": "NIE"} or \
            dict(win._cards_panel.responds_rows()) == {"ELA1": "yes", "ADA1": "NO"}
        assert win._synoptic_panel.pushed[-1]["ELA1.DI.1"] is True

        win._toggle_live(False)
        assert not win.live_enabled()
        assert all(text == "" for _a, text, _f in win._point_registry_panel.live_rows())
        assert win._synoptic_panel.pushed[-1] is None
    finally:
        _close(win)
        fake.close()


def test_force_mode_is_deliberate_marks_forced_rows_and_drops_everything_in_one_move(tmp_path, monkeypatch):
    _app()
    fake = FakeLiveController()
    fake.refuse.add("ELA1.DI.2")
    win = _window(tmp_path, fake.url)
    warned = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warned.append(a[2]) or QMessageBox.StandardButton.Yes)
    try:
        win._open_point_registry()
        panel = win._point_registry_panel
        assert not win.force_mode_enabled()
        assert win.set_force_mode(True) and win.live_enabled()               # the warning was answered Yes
        assert warned and "Engineer" in warned[0]
        assert win.act_force_mode.isChecked()

        refused = panel.apply_forces([("ELA1.DI.1", False), ("ELA1.DI.2", True)])
        assert refused == [("ELA1.DI.2", "on the protection path")]
        rows = dict((a, (text, forced)) for a, text, forced in panel.live_rows())
        assert rows["ELA1.DI.1"][1] is True and rows["ELA1.DI.1"][0].startswith("F")
        assert fake.forces == {"ELA1.DI.1": {"value": False, "kind": "DI", "actor": "API:Engineer", "since": 0}}
        win.live_monitor().poll()
        assert fake.heartbeats >= 1                                            # kept alive while forces are held

        forced_row = next(r for r in range(panel.table.rowCount()) if panel.table.item(r, 0).text() == "ELA1.DI.1")
        panel.table.selectRow(forced_row)
        panel.release_selected_forces()
        assert fake.forces == {}
        panel.apply_forces([("ELA1.DI.1", True), ("ELA1.AI.1", 5.0)])
        assert len(fake.forces) == 2
        assert win.set_force_mode(False) is False
        assert fake.forces == {} and not win.act_force_mode.isChecked()
        assert all(not forced for _a, _t, forced in panel.live_rows())
    finally:
        _close(win)
        fake.close()


def test_declining_the_warning_keeps_force_mode_off_and_a_wrong_token_is_reported(tmp_path, monkeypatch):
    _app()
    fake = FakeLiveController()
    win = _window(tmp_path, fake.url, token="operator-token")
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.StandardButton.No)
    try:
        win._open_point_registry()
        assert win.set_force_mode(True) is False and not win.force_mode_enabled()
        monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.StandardButton.Yes)
        assert win.set_force_mode(True)
        refused = win._point_registry_panel.apply_forces([("ELA1.DI.1", True)])
        assert refused and "401" in str(refused[0][1])
        assert fake.forces == {}
    finally:
        win._force_mode = False
        _close(win)
        fake.close()
