"""Decided 2026-09-18 (ZADANIA p. 6): MQTT and the service notes are
settings of the project; Studio reads everything else the controller
holds (its local settings) and zeroes switching counters over REST. The
MQTT panel edits project.mqtt, the notes panel lists project.
service_notes, the controller panel fetches /api/v1/controller/settings
and /api/v1/counters and posts the Engineer-token reset. Same fake
controller technique as the project-sync tests."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

from studio.shell.main_window import StudioMainWindow
from studio.shell.project_format import MqttConfig, load_project, new_project, save_project, settings_hash, \
    settings_snapshot
from studio.shell.tests.test_controller_project_sync import ENGINEER, FakeController, _close, _quiet_boxes

NOTE = {"text": "contact set replaced", "timestamp": 1758000000.0, "author_level": "Engineer"}


def _app():
    return QApplication.instance() or QApplication([])


def _project_path(tmp_path, with_notes=True):
    project = new_project("Site", author="t")
    project.mqtt = MqttConfig(enabled=True, host="haos.local", topic_prefix="epw/site",
                              link_in=[{"topic": "home/pump", "tag": "Link.HA.In1", "type": "BOOL", "stale_after_s": 30}],
                              deadband_per_tag={"ELA1.AI.1": 0.5})
    if with_notes:
        project.service_notes = {"ELA1.DI.1": [NOTE]}
    path = tmp_path / "studio" / "projekt.epw"
    save_project(project, path)
    return path


def _window(tmp_path, path, url="http://127.0.0.1:1", token=ENGINEER):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    settings.setValue("controller/host", url)
    settings.setValue("controller/token", token)
    win = StudioMainWindow(settings=settings)
    win._load_project_from_path(str(path))
    return win


# --- the MQTT panel edits the project -----------------------------------------------------

def test_the_mqtt_panel_shows_and_edits_the_projects_mqtt_settings(tmp_path):
    _app()
    path = _project_path(tmp_path)
    win = _window(tmp_path, path)
    try:
        win._open_mqtt()
        panel = win._mqtt_panel
        assert panel.enabled_check.isChecked() and panel.host_edit.text() == "haos.local"
        assert panel.links_table.rowCount() == 1 and panel.links_table.item(0, 1).text() == "Link.HA.In1"
        assert panel.deadband_table.rowCount() == 1 and panel.deadband_table.item(0, 1).text() == "0.5"
        assert not win._project.is_dirty

        panel.host_edit.setText("broker.lan")
        panel.host_edit.editingFinished.emit()
        panel.port_spin.setValue(8883)
        panel.tls_check.setChecked(True)
        assert win._project.mqtt.host == "broker.lan" and win._project.mqtt.port == 8883 and win._project.mqtt.tls
        assert win._project.is_dirty

        panel.add_link()
        panel.links_table.item(1, 0).setText("home/valve")
        panel.links_table.item(1, 1).setText("Link.HA.In2")
        panel.links_table.item(1, 2).setText("real")          # normalised to a known type
        panel.links_table.item(1, 3).setText("x")             # not a number: the default
        assert win._project.mqtt.link_in[1] == {"topic": "home/valve", "tag": "Link.HA.In2", "type": "REAL",
                                                "stale_after_s": 30}
        panel.links_table.setCurrentCell(0, 0)
        panel.remove_selected_link()
        assert [l["topic"] for l in win._project.mqtt.link_in] == ["home/valve"]

        panel.add_deadband()
        panel.deadband_table.item(1, 0).setText("ELA1.AI.2")
        panel.deadband_table.item(1, 1).setText("1.25")
        assert win._project.mqtt.deadband_per_tag == {"ELA1.AI.1": 0.5, "ELA1.AI.2": 1.25}

        win._save_project()
        saved = load_project(path)
        assert saved.mqtt.host == "broker.lan" and saved.mqtt.deadband_per_tag["ELA1.AI.2"] == 1.25
        assert settings_snapshot(saved)["mqtt/broker/host"] == "broker.lan"
    finally:
        _close(win)


def test_the_notes_panel_lists_the_logbook_read_only(tmp_path):
    _app()
    path = _project_path(tmp_path)
    win = _window(tmp_path, path)
    try:
        win._open_service_notes()
        panel = win._service_notes_panel
        assert panel.rows() == [("ELA1.DI.1", "", 1758000000.0, "Engineer", "contact set replaced")]
        assert panel.table.rowCount() == 1 and panel.table.item(0, 4).text() == "contact set replaced"
        assert panel.table.item(0, 2).text().startswith("2025-09-16")
        assert "1" in panel.count_label.text()
        assert not (panel.table.item(0, 4).flags() & panel.table.item(0, 4).flags().ItemIsEditable)
    finally:
        _close(win)


def test_notes_and_mqtt_differences_show_in_the_live_settings_and_can_be_taken(tmp_path, monkeypatch):
    _app()
    path = _project_path(tmp_path, with_notes=False)
    on_controller = load_project(path)
    on_controller.mqtt.host = "changed-on-panel"
    on_controller.service_notes = {"ELA1.DI.1": [NOTE]}
    controller = FakeController(path.read_bytes(), revision=5, settings=settings_snapshot(on_controller),
                                stored_hash=settings_hash(on_controller))
    win = _window(tmp_path, path, controller.url)
    _quiet_boxes(monkeypatch, answer=QMessageBox.StandardButton.Yes)
    try:
        win._open_controller()
        panel = win._controller_panel
        panel._fetch_settings()
        differing = {r[0]: (r[1], r[2]) for r in panel.settings_rows() if r[3]}
        assert differing == {"mqtt/broker/host": ("haos.local", "changed-on-panel"),
                             "service_notes/ELA1.DI.1/notes": (None, [NOTE])}
        panel._take_controller_settings()
        assert win._project.mqtt.host == "changed-on-panel"
        assert win._project.service_notes == {"ELA1.DI.1": [NOTE]}
        assert [r for r in panel.settings_rows() if r[3]] == []
    finally:
        _close(win)
        controller.close()


# --- the controller's local settings and counters over REST --------------------------------

class FakeCounters:
    """runtime's /api/v1/controller/settings and /api/v1/counters[/reset]."""

    def __init__(self, counters, local=None, available=True):
        self.counters = counters
        self.local = local if local is not None else {"language": "pl", "api_port": 8010,
                                                      "historian_retention": {"max_days": 30}}
        self.available = available
        self.resets = []
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

            def do_GET(self):
                if self.path == "/api/v1/controller/settings":
                    self._json(200, {"source": "controller.local.json", "path": "/x/controller.local.json",
                                     "language": fake.local.get("language"), "settings": fake.local})
                elif self.path == "/api/v1/counters":
                    self._json(200, {"available": fake.available, "counters": fake.counters if fake.available else {}})
                else:
                    self._json(404, {"detail": "no"})

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                self.rfile.read(length)
                if not (self.path.startswith("/api/v1/counters/") and self.path.endswith("/reset")):
                    self._json(404, {"detail": "no"})
                    return
                if self.headers.get("Authorization") != f"Bearer {ENGINEER}":
                    self._json(401, {"detail": "Engineer token required"})
                    return
                tag = self.path[len("/api/v1/counters/"):-len("/reset")]
                if tag not in fake.counters:
                    self._json(404, {"detail": f"No switching counter for {tag}."})
                    return
                fake.resets.append(tag)
                previous = dict(fake.counters[tag])
                fake.counters[tag] = {**previous, "closes": 0, "opens": 0, "closed_seconds": 0.0}
                self._json(200, {"reset": True, "tag": tag, "previous": previous, "actor": "API:Engineer"})

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def _counters():
    return {"ELA1.DI.1": {"closes": 12, "opens": 11, "closed_seconds": 90061.0, "closed_since": None,
                          "warning_threshold": 5000},
            "ELA1.DI.2": {"closes": 3, "opens": 3, "closed_seconds": 5.0, "closed_since": None,
                          "warning_threshold": None}}


def test_the_controller_panel_shows_the_local_settings_and_the_counters(tmp_path, monkeypatch):
    _app()
    path = _project_path(tmp_path)
    fake = FakeCounters(_counters())
    win = _window(tmp_path, path, fake.url)
    _quiet_boxes(monkeypatch)
    try:
        win._open_controller()
        panel = win._controller_panel
        panel._fetch_local_settings()
        assert panel.local_settings_rows() == [("api_port", "8010"), ("historian_retention/max_days", "30"),
                                               ("language", "pl")]
        assert panel.local_table.rowCount() == 3 and "controller.local.json" in panel.local_status_label.text()

        panel._fetch_counters()
        assert panel.counter_rows() == [("ELA1.DI.1", 12, 11, 90061.0, 5000), ("ELA1.DI.2", 3, 3, 5.0, None)]
        assert panel.counters_table.item(0, 3).text() == "1d 01:01:01"
        assert panel.counters_table.item(0, 4).text() == "5000" and panel.counters_table.item(1, 4).text() == ""
        assert panel.reset_counter_button.isEnabled() and panel.reset_all_counters_button.isEnabled()
    finally:
        _close(win)
        fake.close()


def test_resetting_a_counter_posts_with_the_engineer_token_and_refreshes(tmp_path, monkeypatch):
    _app()
    path = _project_path(tmp_path)
    fake = FakeCounters(_counters())
    win = _window(tmp_path, path, fake.url)
    shown = _quiet_boxes(monkeypatch, answer=QMessageBox.StandardButton.Yes)
    try:
        win._open_controller()
        panel = win._controller_panel
        panel._fetch_counters()
        panel._reset_selected_counter()                       # nothing selected: told so, nothing posted
        assert shown["info"] and fake.resets == []
        panel.counters_table.selectRow(0)
        panel.counters_table.setCurrentCell(0, 0)
        panel._reset_selected_counter()
        assert fake.resets == ["ELA1.DI.1"] and shown["question"]
        assert panel.counter_rows()[0][1:3] == (0, 0)          # refreshed from the controller
        assert "1" in panel.counters_status_label.text()

        panel._reset_all_counters()
        assert fake.resets == ["ELA1.DI.1", "ELA1.DI.1", "ELA1.DI.2"]
        assert all(row[1] == 0 for row in panel.counter_rows())
    finally:
        _close(win)
        fake.close()


def test_a_wrong_token_is_reported_and_a_controller_without_the_module_says_so(tmp_path, monkeypatch):
    _app()
    path = _project_path(tmp_path)
    fake = FakeCounters(_counters())
    win = _window(tmp_path, path, fake.url, token="operator-token")
    shown = _quiet_boxes(monkeypatch, answer=QMessageBox.StandardButton.Yes)
    try:
        win._open_controller()
        panel = win._controller_panel
        panel._fetch_counters()
        panel.counters_table.setCurrentCell(1, 0)
        panel._reset_selected_counter()
        assert fake.resets == [] and shown["warn"] and "401" in shown["warn"][0]

        fake.available = False
        panel._fetch_counters()
        assert panel.counters_table.rowCount() == 0 and not panel.reset_counter_button.isEnabled()
    finally:
        _close(win)
        fake.close()
