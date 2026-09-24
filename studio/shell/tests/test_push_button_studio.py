"""Studio's side of the synoptic push button (owner 2026-09-24): a LIVE
panel preview relays a button's bit write to the controller's own bits
endpoint (a PULSE's clearing write after its delay), and "Sprawdź
projekt" checks that every button on every screen writes a real IN bit
the panel may write."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication

from studio.shell import i18n as shell_i18n
from studio.shell.main_window import StudioMainWindow, _TREE_ITEM_SCREENS
from studio.shell.project_format import new_project, save_project
from studio.shell.project_panels import push_button_bit, screen_push_buttons, validate_project
from studio.shell.tests.test_panel_preview import FakeSynopticPanel

ENGINEER = "engineer-token-for-tests"


class FakeBitsController:
    """runtime's POST /api/v1/bits/<bit>: M.START obeys, M.ZLY is refused."""

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
                if not self.path.startswith("/api/v1/bits/"):
                    self._json(404, {"detail": "no"})
                    return
                bit = self.path[len("/api/v1/bits/"):]
                fake.received.append((bit, body))
                if bit == "M.ZLY":
                    self._json(403, {"detail": {"error": "bit_write_refused",
                                                "reason": "M.ZLY: remote writes are not enabled for this bit"}})
                    return
                self._json(200, {"written": True, "bit": bit, "value": body["value"]})

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def _app():
    return QApplication.instance() or QApplication([])


def _close(win):
    for timer in win.findChildren(QTimer):
        timer.stop()
    win.hide()


def _window(tmp_path, url):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    settings.setValue("controller/host", url)
    settings.setValue("controller/token", ENGINEER)
    win = StudioMainWindow(settings=settings)
    path = tmp_path / "projekt.epw"
    save_project(new_project("Przycisk", author="t"), path)
    win._load_project_from_path(str(path))
    win._synoptic_panel = FakeSynopticPanel()
    win._active = _TREE_ITEM_SCREENS
    return win


def _button(id_, bit, text="", mode="TOGGLE"):
    obj = {"id": id_, "type": "scada.push_button", "text": text, "editor": {"button_mode": mode}}
    if bit is not None:
        obj["bindings"] = {"command": {"tag": bit}}
    return obj


def _screens_document():
    return {
        "format": "EPW_SYNOPTIC", "schema_version": 2, "project": {"name": "Obiekt"},
        "screens": [{"id": "s1", "name": "Główny"}, {"id": "s2", "name": "Pompownia"}],
        "activeScreenId": "s1",
        "objects": [_button("b1", "M.START", "START"), {"id": "q1", "type": "electrical.circuit_breaker"}],
        "screenContents": {"s2": {"objects": [_button("b2", "M.NIE_MA", "RESET"), _button("b3", None),
                                              _button("b4", "M.KMG1_ZEZW", "ZEZW"), _button("b5", "M.CICHY", "CICHY")]}},
    }


def test_a_live_preview_relays_a_buttons_write_to_the_bits_endpoint_and_names_a_refusal(tmp_path):
    _app()
    shell_i18n.set_language("pl")
    fake = FakeBitsController()
    win = _window(tmp_path, fake.url)
    try:
        panel = win._synoptic_panel
        assert win.enter_panel_preview("s1") is True
        panel.commands = [{"bit": "M.START", "value": True}, {"bit": "M.ZLY", "value": True}]
        win._panel_preview_tick()
        assert fake.received == [("M.START", {"value": True}), ("M.ZLY", {"value": True})]
        assert "M.ZLY" in win.statusBar().currentMessage() and "remote writes" in win.statusBar().currentMessage()
        assert panel.commands == []
        assert win.relay_commands([{"bit": "M.START", "value": False}]) == 1
        assert win.statusBar().currentMessage() == "Przycisk: zapisano M.START = FALSE na sterowniku."
        # a PULSE: TRUE now, FALSE after its delay - from a timer, not a sleep in the tick
        fake.received.clear()
        assert win.relay_commands([{"bit": "M.START", "value": True}, {"bit": "M.START", "value": False, "delay_ms": 40}]) == 1
        assert fake.received == [("M.START", {"value": True})]
        app = _app()
        deadline = QTimer()
        for _ in range(60):
            app.processEvents()
            if len(fake.received) == 2:
                break
            QTimer.singleShot(0, lambda: None)
            import time
            time.sleep(0.01)
        assert fake.received == [("M.START", {"value": True}), ("M.START", {"value": False})]
        assert deadline is not None
    finally:
        win.exit_panel_preview()
        _close(win)
        fake.close()


def test_the_panel_bridge_keeps_bit_writes_and_drops_what_is_neither_command_nor_write():
    from studio.shell.synoptic_panel import SynopticPanel
    seen = []
    fake = type("P", (), {})()
    fake._pages = type("Pages", (), {"currentIndex": lambda self: 0})()
    fake._view = type("V", (), {})()
    fake._view.page = lambda: type("Pg", (), {"runJavaScript": lambda self, js, cb=None: cb(json.dumps([
        {"deviceId": "KOT_KM1", "action": "CLOSE"}, {"bit": "M.START", "value": True, "delay_ms": 0},
        {"bit": "", "value": True}, {"deviceId": "", "action": "OPEN"}, {"other": 1}, "junk"]))})()
    from studio.shell import synoptic_panel as module
    fake_page_view = module._PAGE_VIEW
    fake._pages = type("Pages", (), {"currentIndex": lambda self: fake_page_view})()
    SynopticPanel.take_pending_commands(fake, seen.append)
    assert seen == [[{"deviceId": "KOT_KM1", "action": "CLOSE"}, {"bit": "M.START", "value": True, "delay_ms": 0}]]


def test_screen_push_buttons_walks_every_screen_and_names_them():
    project = new_project("Test")
    project.screens = _screens_document()
    found = screen_push_buttons(project)
    assert [(name, obj["id"]) for name, obj in found] == [("Główny", "b1"), ("Pompownia", "b2"), ("Pompownia", "b3"),
                                                          ("Pompownia", "b4"), ("Pompownia", "b5")]
    assert push_button_bit(found[0][1]) == "M.START" and push_button_bit(found[2][1]) == ""
    assert screen_push_buttons(new_project("Empty")) == []
    single = new_project("Single")
    single.screens = {"format": "EPW_SYNOPTIC", "project": {"name": "Jeden"}, "objects": [_button("b9", "M.X")]}
    assert [(name, obj["id"]) for name, obj in screen_push_buttons(single)] == [("Jeden", "b9")]


def test_check_project_reports_a_button_without_a_bit_an_unknown_bit_an_out_bit_and_a_bit_the_panel_may_not_write():
    shell_i18n.set_language("pl")
    project = new_project("Test")
    project.screens = _screens_document()
    project.logic = {"settings": {"internal_bits": [
        {"name": "START", "type": "BOOL", "direction": "IN", "panel_level": "Operator", "remote_write": False},
        {"name": "KMG1_ZEZW", "type": "BOOL", "direction": "OUT"},
        {"name": "CICHY", "type": "BOOL", "direction": "IN", "panel_level": "", "remote_write": True},
    ]}}
    issues = [i for i in validate_project(project) if "przycisk" in i.message.lower()]
    assert [(i.severity, i.message) for i in issues] == [
        ("error", "Ekran Pompownia: przycisk 'RESET' pisze bit 'M.NIE_MA', którego nie ma w rejestrze bitów wewnętrznych logiki."),
        ("warning", "Ekran Pompownia: przycisk 'b3' nie ma bitu — nic nie zrobi na panelu (Właściwości → Przycisk → Bit)."),
        ("error", "Ekran Pompownia: przycisk 'ZEZW' pisze 'M.KMG1_ZEZW', a przycisk może pisać tylko bit BOOL o kierunku WE."),
        ("error", "Ekran Pompownia: przycisk 'CICHY' pisze 'M.CICHY', ale rejestr nie pozwala panelowi pisać tego bitu (kolumna Panel w dziale Sygnały)."),
    ]
    assert all(i.target == "screens" for i in issues)
    # the correct button on the main screen is silent
    assert not [i for i in issues if "START" in i.message]
    shell_i18n.set_language("en")
    english = [i.message for i in validate_project(project) if "push button" in i.message.lower()]
    assert len(english) == 4 and english[0].startswith("Screen Pompownia: push button 'RESET' writes bit 'M.NIE_MA'")


def test_the_screens_target_opens_the_synoptic_editor(tmp_path):
    assert StudioMainWindow._VALIDATION_TARGETS["screens"] == ("_synoptic_panel", "_open_screens")
