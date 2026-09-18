"""SPEC "Wymuszanie stanów - Powiązanie" (the internal Omicron) on the
Studio side: Sterownik → Test zabezpieczeń lists what the controller
can test, starts a test with the Engineer token, follows it until the
controller reports the result, shows the reports and writes them out
as CSV. Against a fake controller serving /api/v1/protection-tests."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from studio.shell.main_window import StudioMainWindow, _TREE_ITEM_PROTECTION_TESTS, _MARKABLE_ASPECTS
from studio.shell.project_format import new_project, save_project
from studio.shell.tests.test_controller_project_sync import ENGINEER, _close


def _app():
    return QApplication.instance() or QApplication([])


REPORT = {"id": "abc123", "kind": "process", "subject": "PP1", "name": "Boiler", "actor": "API:Engineer",
          "started_at": "2026-09-18 10:00:00", "finished_at": None, "result": "RUNNING", "reason": "",
          "configured": {"analog_tag": "ELA1.AI.1", "upper_threshold": 80.0, "delay_seconds": 0.3},
          "measured": {}, "steps": ["10:00:00 force ELA1.AI.1 = 88.0 (above 80.0)"]}


class FakeTestController:
    """runtime's protection test endpoints, in memory: a started test
    reports RUNNING once, then PASS."""

    def __init__(self):
        self.reports = []
        self.running = None
        self.started = []
        self.polls = 0
        self.available = True
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
                if self.path == "/api/v1/protection-tests":
                    if not fake.available:
                        self._json(200, {"available": False, "reports": [], "running": None,
                                         "candidates": {"process": [], "apparatus": []}})
                        return
                    self._json(200, {"available": True, "reports": fake.reports, "running": fake.running,
                                     "candidates": {
                                         "process": [{"id": "PP1", "name": "Boiler", "analog_tag": "ELA1.AI.1",
                                                      "upper_threshold": 80.0, "lower_threshold": 0.0,
                                                      "delay_seconds": 0.3, "enabled": True, "exceeded": False},
                                                     {"id": "PP2", "name": "Off", "analog_tag": "ELA1.AI.2",
                                                      "upper_threshold": 10.0, "lower_threshold": 0.0,
                                                      "delay_seconds": 1.0, "enabled": False, "exceeded": False}],
                                         "apparatus": [{"id": "KOT_KM1", "kind": "contactor", "feedback": ["ELA1.DI.1"],
                                                        "command": ["ADA1.DO.1"], "command_style": "MAINTAINED"}]}})
                elif self.path.startswith("/api/v1/protection-tests/"):
                    test_id = self.path.rsplit("/", 1)[1]
                    fake.polls += 1
                    if fake.running and fake.running["id"] == test_id:
                        if fake.polls >= 2:
                            done = dict(fake.running, result="PASS", finished_at="2026-09-18 10:00:01",
                                        reason="trip 0.31 s (delay 0.30 s), reset 0.02 s",
                                        measured={"trip_seconds": 0.31, "reset_seconds": 0.02})
                            fake.reports.append(done)
                            fake.running = None
                            self._json(200, done)
                        else:
                            self._json(200, fake.running)
                    else:
                        found = [r for r in fake.reports if r["id"] == test_id]
                        self._json(200, found[0]) if found else self._json(404, {"detail": "no"})
                else:
                    self._json(404, {"detail": "no"})

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                if self.headers.get("Authorization") != f"Bearer {ENGINEER}":
                    self._json(401, {"detail": "Engineer token required"})
                    return
                fake.started.append(body)
                if body["id"] == "PP2":
                    blocked = dict(REPORT, id="blk", subject="PP2", result="BLOCKED", reason="the protection is disabled")
                    fake.reports.append(blocked)
                    self._json(409, {"detail": {"error": "test_blocked", "reason": "the protection is disabled",
                                                "report": blocked}})
                    return
                fake.running = dict(REPORT, subject=body["id"], kind=body["kind"])
                self._json(200, fake.running)

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def _window(tmp_path, url, token=ENGINEER):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    settings.setValue("controller/host", url)
    settings.setValue("controller/token", token)
    win = StudioMainWindow(settings=settings)
    path = tmp_path / "projekt.epw"
    save_project(new_project("Tests", author="t"), path)
    win._load_project_from_path(str(path))
    return win


def test_the_panel_lists_candidates_starts_a_test_follows_it_and_exports_the_reports(tmp_path):
    _app()
    fake = FakeTestController()
    win = _window(tmp_path, fake.url)
    try:
        win._open_protection_tests()
        panel = win._protection_tests_panel
        assert win._active == _TREE_ITEM_PROTECTION_TESTS and _TREE_ITEM_PROTECTION_TESTS not in _MARKABLE_ASPECTS
        assert panel.candidates_table.rowCount() == 3
        assert panel.candidates_table.item(0, 1).text() == "PP1" and "80" in panel.candidates_table.item(0, 3).text()
        assert panel.candidates_table.item(1, 4).text() != panel.candidates_table.item(0, 4).text()   # PP2 disabled
        assert panel.candidates_table.item(2, 1).text() == "KOT_KM1"
        assert panel.reports_table.rowCount() == 0

        assert panel.run_selected_test() is False            # nothing selected
        panel.candidates_table.selectRow(0)
        assert panel.run_selected_test() is True
        assert fake.started == [{"kind": "process", "id": "PP1"}]
        assert panel._poll_timer.isActive() and not panel.run_button.isEnabled()
        panel._poll()                                        # still RUNNING
        assert panel._poll_timer.isActive()
        panel._poll()                                        # PASS
        assert not panel._poll_timer.isActive() and panel.run_button.isEnabled()
        assert panel.reports_table.rowCount() == 1
        assert panel.reports_table.item(0, 3).text() == "PASS" and "0.31" in panel.reports_table.item(0, 5).text()
        assert "PASS" in panel.status_label.text()

        panel.candidates_table.selectRow(1)
        assert panel.run_selected_test() is False            # BLOCKED by the controller, reported anyway
        assert "disabled" in panel.status_label.text() and panel.reports_table.rowCount() == 2

        out = tmp_path / "reports.csv"
        assert panel.export_csv(str(out)) is True
        text = out.read_text(encoding="utf-8-sig")
        assert text.splitlines()[0].startswith("started_at;finished_at;kind;subject")
        assert "PP1;Boiler;API:Engineer;PASS" in text and "BLOCKED" in text and "trip_seconds=0.31" in text
    finally:
        _close(win)
        fake.close()


def test_without_the_engineer_token_a_start_is_refused_and_an_old_controller_is_named(tmp_path):
    _app()
    fake = FakeTestController()
    win = _window(tmp_path, fake.url, token="operator-token")
    try:
        win._open_protection_tests()
        panel = win._protection_tests_panel
        panel.candidates_table.selectRow(0)
        assert panel.run_selected_test() is False and fake.started == []
        assert "401" in panel.status_label.text()
        assert panel.export_csv(str(tmp_path / "none.csv")) is False   # nothing to save

        fake.available = False
        assert panel.refresh() is False
        assert panel.candidates_table.rowCount() == 0
        assert panel.status_label.text() != ""
    finally:
        _close(win)
        fake.close()
