"""Software commissioning - the whole loop with no hardware, every piece
real: a project built with Studio's own code (cards with Modbus unit
ids, apparatuses, the screen embedded), a virtual Modbus TCP bus
(tools/modbus_sim.py), the runtime core on that bus (io_driver MODBUS in
controller.local.json), the Synoptic page following the inputs, a click
that sends a command out to a coil the bus mirrors back as feedback,
and Studio sending the project to the running controller over its real
REST API (a uvicorn server on a free port) up to the restart request.
"""
import importlib.util
import json
import os
import socket
import sys
import threading
import time
from pathlib import Path

import pytest

os.environ["EPW_TESTING"] = "1"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core import project_format as pf  # noqa: E402
from epw_os.core.api_auth import ApiAuth  # noqa: E402
from epw_os.core.epw_core import EPWCore  # noqa: E402
from epw_os.drivers.modbus_driver import DRIVER_ID  # noqa: E402

_SIM = Path(__file__).resolve().parents[2] / "tools" / "modbus_sim.py"
_spec = importlib.util.spec_from_file_location("modbus_sim_e2e", _SIM)
sim = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sim)


def _wait(predicate, timeout=6.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.03)
    return predicate()


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _studio_project(directory: Path, bus_port: int) -> Path:
    from studio.shell.project_format import Card, Device, Location, ModbusBusConfig, new_project, save_project
    from studio.shell.project_panels import device_to_synoptic_dict, sync_points_for_card
    directory.mkdir(parents=True, exist_ok=True)
    project = new_project("Software commissioning", author="Test")
    project.modules = []
    project.locations = [Location("KOT", "Kotlownia")]
    for card in (Card("ELA1", "ELA01", channel_kinds={"DI": 8}, modbus_unit_id=1, location="KOT"),
                 Card("ADA1", "ADA01", channel_kinds={"DO": 8}, modbus_unit_id=1, location="KOT")):
        project.cards.append(card)
        sync_points_for_card(project, card)
    project.devices = [
        Device(id="KOT_Q1", behavior="SWITCHED", kind="breaker", feedback=["ELA1.DI.1"], command=["ADA1.DO.1"]),
        Device(id="KOT_KM1", behavior="SWITCHED", kind="contactor", feedback=["ELA1.DI.2"],
               command=["ADA1.DO.2", "ADA1.DO.3"], command_style="PULSE_TOGGLE", pulse_ms=60),
    ]
    project.modbus_bus = ModbusBusConfig(transport="TCP", host="127.0.0.1", tcp_port=bus_port)

    def obj(id_, type_, x, y, device):
        return {"id": id_, "type": type_, "category": "Electrical", "x": x, "y": y, "rotation": 0, "scaleX": 1,
                "scaleY": 1, "visible": True, "locked": False, "layer": 1, "tag": "", "description": "", "color": "",
                "fill": "", "border": "", "text": "", "font": "", "fontSize": 13, "tooltip": "", "width": 64,
                "height": 64, "customProperties": {}, "deviceId": device, "designation": "-" + device.split("_")[1]}
    project.screens = {
        "format": "EPW_SYNOPTIC", "schema_version": 2, "project": {"name": "Kotlownia"},
        "canvas": {"width": 800, "height": 600},
        "objects": [obj("q1", "electrical.circuit_breaker", 100, 100, "KOT_Q1"),
                    obj("km1", "electrical.contactor", 300, 100, "KOT_KM1")],
        "devices": [device_to_synoptic_dict(d) for d in project.devices],
        "connections": [{"id": "w", "points": [{"x": 132, "y": 164}, {"x": 132, "y": 300}], "medium": "ELECTRICAL",
                         "style": "NORMAL"}],
    }
    path = directory / "projekt.epw"
    save_project(project, path)
    return path


class _Access:
    def has_access(self, level):
        return True


@pytest.fixture
def stack(tmp_path, db):
    """Virtual bus + a running core on it + a real REST server."""
    bus = sim.VirtualBus({1: {"di": 8, "do": 8}}, mirror_coils_to_inputs=True, mirror_delay_s=0.02)
    controller_dir = tmp_path / "controller"
    project_path = _studio_project(controller_dir, bus.port)
    (controller_dir / "controller.local.json").write_text(json.dumps({
        "format": "EPW_CONTROLLER_SETTINGS", "schema_version": 1,
        "io_driver": {"driver": "MODBUS", "poll_interval_ms": 40, "timeout_s": 0.5, "retries": 0}}), encoding="utf-8")
    core = EPWCore()
    core.project_manager.project_file = str(project_path)
    core.api_auth = ApiAuth(config_path=str(tmp_path / "api_tokens.local.json"))
    import hashlib
    import secrets
    tokens = {"Operator": secrets.token_hex(16), "Engineer": secrets.token_hex(16)}
    (tmp_path / "api_tokens.local.json").write_text(json.dumps({"token_hashes": {
        level: hashlib.sha256(t.encode("utf-8")).hexdigest() for level, t in tokens.items()}}))
    core.api_auth = ApiAuth(config_path=str(tmp_path / "api_tokens.local.json"))
    core.startup()

    import uvicorn
    from epw_os.backend.api import app
    app.state.core = core
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    assert _wait(lambda: server.started, timeout=10)
    try:
        yield bus, core, project_path, f"http://127.0.0.1:{port}", tokens
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        if core.is_running:
            core.shutdown()
        bus.close()


def test_the_screen_follows_the_bus_a_click_drives_a_coil_and_studio_sends_the_project(stack, tmp_path, monkeypatch):
    bus, core, project_path, url, tokens = stack
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from epw_os.gui.synoptic.page_synoptic import PageSynoptic

    # --- the core runs the project on the virtual bus ---
    assert core.modbus_driver is not None and core.modbus_driver.is_alive()
    assert core.device_manager.devices["ELA1"]["driver_id"] == DRIVER_ID
    assert core.command_manager._definitions["KOT_KM1.CLOSE"].driver_id == DRIVER_ID
    assert core.startup_issues == []

    page = PageSynoptic(core.tag_manager, project_manager=core.project_manager,
                        apparatus_registry=core.apparatus_registry, access_manager=_Access(),
                        command_manager=core.command_manager)
    page.resize(800, 600)
    objects = {o["id"]: o for o in page.screen.document.project.objects}
    state = lambda oid: page.screen.presentation_for(objects[oid]).state  # noqa: E731

    # --- an input closes on the bus: the breaker symbol closes on the screen ---
    assert _wait(lambda: core.tag_manager.get_tag("ELA1.DI.1").quality.value == "GOOD")
    assert state("q1") == "OPEN"
    bus.set_input(1, 1, True)
    assert _wait(lambda: state("q1") == "CLOSED")
    page.screen.grab()
    assert page.screen.connection_state("w") == "ACTIVE"          # the wire from Q1's OUT terminal is live

    # --- a click on the closed breaker sends OPEN: coil 1 goes False, the mirrored input follows ---
    page.confirm_command = lambda apparatus, action, pos=None: True
    page._on_object_clicked(objects["q1"], page.screen.presentation_for(objects["q1"]), None)
    assert _wait(lambda: (1, "coil", 1, False) in bus.writes)
    assert _wait(lambda: state("q1") == "OPEN")

    # --- the contactor: one PULSE_TOGGLE pulse on the CLOSE coil, released after pulse_ms ---
    assert state("km1") == "OFF"
    page._on_object_clicked(objects["km1"], page.screen.presentation_for(objects["km1"]), None)
    assert _wait(lambda: (1, "coil", 2, True) in bus.writes)
    assert _wait(lambda: (1, "coil", 2, False) in bus.writes)     # the pulse ends on its own
    assert _wait(lambda: state("km1") == "ON")
    page.shutdown()

    # --- Studio sends a changed project to the running controller over the real API ---
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QMessageBox
    from studio.shell.main_window import StudioMainWindow
    laptop = tmp_path / "laptop" / "projekt.epw"
    laptop.parent.mkdir()
    laptop.write_bytes(project_path.read_bytes())
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    settings.setValue("controller/host", url)
    settings.setValue("controller/token", tokens["Engineer"])
    win = StudioMainWindow(settings=settings)
    win._load_project_from_path(str(laptop))
    win._project.metadata.description = "changed on the laptop"
    win._project.touch()
    win._open_controller()
    shown = {"info": [], "warn": []}
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: shown["info"].append(a[2]) or QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: shown["warn"].append(a[2]) or QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    panel = win._controller_panel
    panel._confirm_overwrite = lambda header, local, diff: True
    try:
        panel._send_to_device()
        assert shown["warn"] == [], shown["warn"]
        assert shown["info"] and "2" in shown["info"][0]
        installed = pf.read_project(project_path).project
        assert installed.metadata.description == "changed on the laptop" and installed.revision == 2
        assert pf.read_project(str(project_path) + ".bak").project.revision == 1
        assert _wait(lambda: core.restart_requested is not None, timeout=6)
        assert "revision 2" in core.restart_requested
    finally:
        from PySide6.QtCore import QTimer
        for timer in win.findChildren(QTimer):
            timer.stop()
        win.hide()
