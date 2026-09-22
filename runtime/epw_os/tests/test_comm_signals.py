"""Etap 2 of the signal register: COMM.* counted by the controller as
the Modbus master (core/comm_signals.py) - per device and over the bus,
from DeviceManager's watchdog and the driver's own diagnostics. The last
test runs the real thing: a virtual bus, a card that falls silent, the
bit that flips after the watchdog time, the card that comes back."""
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ["EPW_TESTING"] = "1"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core.comm_diagnostics import ERROR_CRC, ERROR_TIMEOUT, CommDiagnostics  # noqa: E402
from epw_os.core.comm_signals import CommSignals  # noqa: E402
from epw_os.core.device_manager import DeviceManager, DeviceStatus  # noqa: E402
from epw_os.core.events import EventBus  # noqa: E402
from epw_os.core.logic_runtime import SystemSignalSource  # noqa: E402
from epw_os.core.tag_manager import TagManager, TagType  # noqa: E402


class _Driver:
    def __init__(self, is_running=True, alive=True, transport="TCP", unavailable=None):
        self.is_running = is_running
        self._alive = alive
        self._bus = {"transport": transport}
        self.unavailable_reason = unavailable
        self.diagnostics = CommDiagnostics()

    def is_alive(self):
        return self._alive

    def get_comm_stats(self):
        return self.diagnostics.get_all_stats()


def _core(devices=("ELA1", "ADA1"), modbus=("ELA1", "ADA1"), driver=None):
    bus = EventBus()
    manager = DeviceManager(bus)
    for dev in devices:
        manager.register_device(dev, "MODBUS" if dev in modbus else "SIM_DRIVER", timeout=0.2)
    manager.register_device("OrangePi", "SIM_DRIVER", timeout=5.0)      # the panel's own, not the project's
    driver = driver or _Driver()
    tags = TagManager(bus)
    return SimpleNamespace(
        device_manager=manager, driver_manager=SimpleNamespace(is_running=True, drivers={"MODBUS": driver}),
        modbus_driver=driver, _modbus_card_ids=set(modbus), tag_manager=tags,
        project_manager=SimpleNamespace(config={"devices": [{"id": d} for d in devices]}),
    )


def _read(core, signal_id):
    signals = CommSignals(core)
    signals._last_watchdog_check = 0.0
    return SystemSignalSource(sources=[signals]).read(signal_id)


def test_a_device_never_heard_from_is_offline_not_faulted_and_nothing_is_ok():
    core = _core()
    assert _read(core, "COMM.ELA1.ONLINE") is False and _read(core, "COMM.ELA1.OFFLINE") is True
    assert _read(core, "COMM.ELA1.FAULT") is False and _read(core, "COMM.ELA1.TIMEOUT") is False
    assert _read(core, "COMM.ALL_OK") is False and _read(core, "COMM.ANY_DEVICE_OFFLINE") is True
    assert _read(core, "COMM.ANY_DEVICE_FAULT") is False
    # Every card on the bus silent at once is the bus.
    assert _read(core, "COMM.BUS_FAULT") is True and _read(core, "COMM.ETHERNET_FAULT") is True
    assert _read(core, "COMM.RS485_FAULT") is False


def test_a_good_poll_puts_the_device_online_and_the_watchdog_takes_it_away_again():
    core = _core()
    core.device_manager.update_comm("ELA1")
    core.device_manager.update_comm("ADA1")
    assert _read(core, "COMM.ELA1.ONLINE") is True and _read(core, "COMM.ALL_OK") is True
    assert _read(core, "COMM.ANY_DEVICE_OFFLINE") is False and _read(core, "COMM.BUS_FAULT") is False
    core.device_manager.devices["ADA1"]["last_comm"] -= 1.0          # silent for longer than its 0.2 s watchdog
    # The read runs the watchdog check itself - nobody else would, with the card silent.
    assert _read(core, "COMM.ADA1.ONLINE") is False and _read(core, "COMM.ADA1.FAULT") is True
    assert _read(core, "COMM.ADA1.OFFLINE") is True and _read(core, "COMM.ELA1.ONLINE") is True
    assert _read(core, "COMM.ANY_DEVICE_FAULT") is True and _read(core, "COMM.ALL_OK") is False
    assert _read(core, "COMM.BUS_FAULT") is False                       # one card, not the bus
    core.device_manager.update_comm("ADA1")
    assert _read(core, "COMM.ADA1.ONLINE") is True and _read(core, "COMM.ADA1.FAULT") is False


def test_timeout_and_degraded_come_from_the_drivers_own_error_accounting():
    core = _core()
    diag = core.modbus_driver.diagnostics
    core.device_manager.update_comm("ELA1")
    core.device_manager.update_comm("ADA1")
    diag.record_frame_sent("ADA1")
    diag.record_error("ADA1", ERROR_TIMEOUT, "no reply")
    assert _read(core, "COMM.ADA1.TIMEOUT") is True and _read(core, "COMM.ADA1.DEGRADED") is True
    assert _read(core, "COMM.LINK_DEGRADED") is True and _read(core, "COMM.ALL_OK") is False
    assert _read(core, "COMM.ELA1.DEGRADED") is False
    diag.record_frame_sent("ADA1")
    diag.record_success("ADA1", 3.0)
    assert _read(core, "COMM.ADA1.TIMEOUT") is False                    # something succeeded since
    assert _read(core, "COMM.ADA1.DEGRADED") is True                    # but the error is still recent
    diag.record_error("ADA1", ERROR_CRC, "bad crc")
    assert _read(core, "COMM.ADA1.TIMEOUT") is False                    # a CRC error is not a timeout
    # Errors older than the window no longer degrade the link.
    old = [type(e)(timestamp=e.timestamp - 3600, error_type=e.error_type, description=e.description)
           for e in diag._devices["ADA1"].recent_errors]
    diag._devices["ADA1"].recent_errors.clear()
    diag._devices["ADA1"].recent_errors.extend(old)
    assert _read(core, "COMM.ADA1.DEGRADED") is False and _read(core, "COMM.LINK_DEGRADED") is False


def test_the_bus_fault_names_its_transport_and_a_dead_driver():
    serial = _core(driver=_Driver(transport="RTU", unavailable="COM3 not found"))
    assert _read(serial, "COMM.BUS_FAULT") is True and _read(serial, "COMM.RS485_FAULT") is True
    assert _read(serial, "COMM.ETHERNET_FAULT") is False
    dead = _core(driver=_Driver(transport="TCP", alive=False))
    dead.device_manager.update_comm("ELA1")
    dead.device_manager.update_comm("ADA1")
    assert _read(dead, "COMM.BUS_FAULT") is True and _read(dead, "COMM.ETHERNET_FAULT") is True
    no_bus = _core(modbus=())
    no_bus.modbus_driver = None
    assert _read(no_bus, "COMM.BUS_FAULT") is False


def test_the_older_per_device_diagnostics_are_answered_from_the_same_facts():
    core = _core()
    signals = CommSignals(core)
    assert signals.serves("ELA1.ONLINE") and signals.serves("ADA1.SAFE_PATH_OK") and not signals.serves("XYZ.ONLINE")
    assert _read(core, "ELA1.ONLINE") is False
    core.device_manager.update_comm("ELA1")
    assert _read(core, "ELA1.ONLINE") is True and _read(core, "ELA1.FAULT") is False
    core.tag_manager.add_tag("Safety.ADA1.Healthy", True, TagType.BOOL)
    assert _read(core, "ADA1.SAFE_PATH_OK") is True
    core.tag_manager.update_tag("Safety.ADA1.Healthy", False)
    assert _read(core, "ADA1.SAFE_PATH_OK") is False


def test_the_catalogue_expands_comm_patterns_once_per_card_and_classifies_them_served():
    from shared.docs import generate_signal_register_status as gen
    from shared.logic import system_signals

    class _Project:
        settings = {}
        external_cards = [{"id": "ELA1", "kind": "DI", "channels": 16}, {"id": "ELA1", "kind": "AI", "channels": 8},
                          {"id": "ADA1", "kind": "DO", "channels": 16}]

    ids = [s["id"] for s in system_signals.get_all_signals(_Project()) if s["id"].startswith("COMM.")]
    assert ids.count("COMM.ELA1.ONLINE") == 1 and "COMM.ADA1.DEGRADED" in ids and "COMM.ALL_OK" in ids
    catalog = {gen._normalise(s["id"]): s for s in system_signals.raw_signals()}
    for row in ("COMM.ALL_OK", "COMM.BUS_FAULT", "COMM.<device_id>.ONLINE", "COMM.<device_id>.TIMEOUT"):
        assert gen.classify({"ID / Wzorzec": row, "Grupa": "COMM"}, catalog, {})[0] == "w katalogu i obsłużony", row


# --- the real thing: a virtual bus and a card that falls silent ------------------

def _wait(predicate, timeout=8.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return predicate()


def test_on_the_virtual_bus_a_silent_card_goes_offline_after_its_watchdog_and_comes_back(tmp_path, db):
    from epw_os.core.epw_core import EPWCore
    from epw_os.tests.test_software_commissioning import _studio_project, sim
    from studio.shell.project_format import load_project, save_project

    bus = sim.VirtualBus({1: {"di": 8}, 2: {"do": 8}})
    controller_dir = tmp_path / "controller"
    project_path = _studio_project(controller_dir, bus.port)
    project = load_project(project_path)
    for card in project.cards:                    # one unit per card, so one can fall silent alone
        card.modbus_unit_id = 1 if card.id == "ELA1" else 2
    save_project(project, project_path)
    (controller_dir / "controller.local.json").write_text(json.dumps({
        "format": "EPW_CONTROLLER_SETTINGS", "schema_version": 1,
        "io_driver": {"driver": "MODBUS", "poll_interval_ms": 40, "timeout_s": 0.3, "retries": 0}}), encoding="utf-8")
    core = EPWCore()
    core.project_manager.project_file = str(project_path)
    core.startup()
    try:
        read = core.logic_engine._io.read_system_signal
        assert _wait(lambda: read("COMM.ELA1.ONLINE") and read("COMM.ADA1.ONLINE"))
        assert read("COMM.ALL_OK") is True and read("COMM.BUS_FAULT") is False and read("COMM.ETHERNET_FAULT") is False

        bus.silence(2)
        assert _wait(lambda: read("COMM.ADA1.TIMEOUT"))
        assert _wait(lambda: read("COMM.ADA1.ONLINE") is False, timeout=12.0), "ADA1 stayed online past its watchdog"
        assert read("COMM.ADA1.FAULT") is True and read("COMM.ADA1.OFFLINE") is True
        assert read("COMM.ANY_DEVICE_OFFLINE") is True and read("COMM.ANY_DEVICE_FAULT") is True
        assert read("COMM.ELA1.ONLINE") is True and read("COMM.BUS_FAULT") is False
        assert read("COMM.ALL_OK") is False

        bus.silence(2, False)
        assert _wait(lambda: read("COMM.ADA1.ONLINE"))
        assert read("COMM.ADA1.FAULT") is False and read("COMM.ADA1.TIMEOUT") is False
        assert read("COMM.ADA1.DEGRADED") is True and read("COMM.LINK_DEGRADED") is True   # the errors are still recent
    finally:
        core.shutdown()
        bus.close()
