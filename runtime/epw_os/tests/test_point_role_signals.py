"""Signal register etap 4: PWR / UPS / PROT bits carried by a contact on
a digital input (core/point_role_signals.py). The bit reads under the
same name an EPM or an ADA01 would give it (4.3), the contact type gives
it the platform's sense (4.2: TRUE = healthy), a silent card gives the
safe value (Z4), and a role assigned in the project wins over the device
block for that one bit (4.4). The last test runs on the virtual bus."""
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

os.environ["EPW_TESTING"] = "1"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core import project_format as pf  # noqa: E402
from epw_os.core.device_manager import DeviceManager  # noqa: E402
from epw_os.core.device_signals import DeviceSignals  # noqa: E402
from epw_os.core.events import EventBus  # noqa: E402
from epw_os.core.logic_runtime import SystemSignalSource  # noqa: E402
from epw_os.core.point_role_signals import PointRoleSignals  # noqa: E402
from epw_os.core.tag_manager import TagManager, TagQuality, TagType  # noqa: E402
from epw_os.drivers import device_blocks as B  # noqa: E402

_TOOLS = Path(__file__).resolve().parents[2] / "tools"


def _load_tool(name):
    spec = importlib.util.spec_from_file_location(f"{name}_for_role_tests", _TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _core(registry, devices=None):
    bus = EventBus()
    tags = TagManager(bus)
    for point in registry:
        tags.add_tag(point["address"], False, TagType.BOOL, quality=TagQuality.NOT_INITIALIZED, source="HARDWARE")
    manager = DeviceManager(bus)
    for dev in devices or [{"id": "ELA1", "model": "ELA01"}]:
        manager.register_device(dev["id"], "MODBUS", timeout=5.0)
        manager.update_comm(dev["id"])           # the cards answer, unless a test says otherwise
    return SimpleNamespace(
        event_bus=bus, tag_manager=tags, device_manager=manager, alarm_manager=None, audit_logger=None,
        modbus_driver=None, _modbus_card_ids=set(), health_manager=None,
        project_manager=SimpleNamespace(
            config={"devices": devices or [{"id": "ELA1", "model": "ELA01", "kind": "DI"}], "point_registry": registry},
            get_electrical_protection_stages=lambda: []),
    )


def _point(address, role=None, contact="NO", kind="DI"):
    return {"address": address, "kind": kind, "description": "", "location": "", "technical_note": "",
            "role": role, "contact": contact}


def _system(core):
    return SystemSignalSource(sources=[PointRoleSignals(core), DeviceSignals(core)])


def test_an_nc_mains_relay_contact_reads_mains_ok_true_while_the_input_is_open():
    core = _core([_point("ELA1.DI.1", "PWR.MAINS_OK", "NC")])
    system = _system(core)
    read = system.read
    core.tag_manager.publish_from_driver("ELA1.DI.1", False)             # relay energised: NC open
    assert read("PWR.MAINS_OK") is True and read("PWR.MAINS_LOST") is False
    core.tag_manager.publish_from_driver("ELA1.DI.1", True)              # relay dropped: NC closed
    assert read("PWR.MAINS_OK") is False and read("PWR.MAINS_LOST") is True
    # the same relay's NO contact, the opposite wiring, the same meaning
    core.project_manager.config["point_registry"] = [_point("ELA1.DI.1", "PWR.MAINS_OK", "NO")]
    core.tag_manager.publish_from_driver("ELA1.DI.1", True)
    assert read("PWR.MAINS_OK") is True and read("PWR.MAINS_LOST") is False


def test_ups_contacts_read_under_the_registers_names_and_an_unwired_ups_reads_safe():
    core = _core([_point("ELA1.DI.1", "UPS.ON_BATTERY", "NO"), _point("ELA1.DI.2", "UPS.ONLINE", "NC"),
                  _point("ELA1.DI.3", "UPS.FAULT", "NO")])
    system = _system(core)
    read = system.read
    for address, value in (("ELA1.DI.1", False), ("ELA1.DI.2", False), ("ELA1.DI.3", False)):
        core.tag_manager.publish_from_driver(address, value)
    assert read("UPS.ON_BATTERY") is False and read("UPS.ONLINE") is True and read("UPS.FAULT") is False
    core.tag_manager.publish_from_driver("ELA1.DI.1", True)
    core.tag_manager.publish_from_driver("ELA1.DI.2", True)
    assert read("UPS.ON_BATTERY") is True and read("UPS.ONLINE") is False
    # nobody wired UPS.LOW_BATTERY: the safe value, not an error, and it is still served
    assert read("UPS.LOW_BATTERY") is False and system.sources[0].serves("UPS.LOW_BATTERY")
    unwired = _system(_core([]))
    assert unwired.read("UPS.FAULT") is True and unwired.read("UPS.ONLINE") is False


def test_no_data_is_the_safe_value_never_the_last_value():
    core = _core([_point("ELA1.DI.1", "PWR.POWER_24V_OK", "NO"), _point("ELA1.DI.2", "UPS.FAULT", "NC")])
    system = _system(core)
    read = system.read
    # never read yet (NOT_INITIALIZED): safe
    assert read("PWR.POWER_24V_OK") is False and read("PWR.POWER_24V_FAULT") is True and read("UPS.FAULT") is True
    core.tag_manager.publish_from_driver("ELA1.DI.1", True)
    core.tag_manager.publish_from_driver("ELA1.DI.2", True)
    assert read("PWR.POWER_24V_OK") is True and read("PWR.POWER_24V_FAULT") is False and read("UPS.FAULT") is False
    # the card falls silent: the driver marks the tags, the bits go safe although the last values were healthy
    core.tag_manager.publish_from_driver("ELA1.DI.1", True, TagQuality.COMM_FAILURE)
    core.tag_manager.publish_from_driver("ELA1.DI.2", True, TagQuality.STALE)
    assert read("PWR.POWER_24V_OK") is False and read("PWR.POWER_24V_FAULT") is True and read("UPS.FAULT") is True
    core.tag_manager.publish_from_driver("ELA1.DI.1", True, TagQuality.GOOD)
    assert read("PWR.POWER_24V_OK") is True
    # the card's watchdog says offline before the tag's own staleness timer: safe at once (Z4)
    core.device_manager.devices["ELA1"]["status"] = "COMM_FAILURE"
    assert read("PWR.POWER_24V_OK") is False and read("PWR.POWER_24V_FAULT") is True
    core.device_manager.update_comm("ELA1")
    assert read("PWR.POWER_24V_OK") is True


def test_a_role_wins_over_the_device_block_for_that_bit_only_and_says_so():
    devices = [{"id": "ELA1", "model": "ELA01", "kind": "DI"}, {"id": "EPM1", "model": "EPM", "kind": None}]
    core = _core([_point("ELA1.DI.1", "PWR.L2_OK", "NO")], devices)
    system = _system(core)
    notices = system.sources[0].notices
    assert len(notices) == 1 and "PWR.L2_OK" in notices[0] and "EPM" in notices[0] and "ELA1.DI.1" in notices[0]
    assert _system(_core([_point("ELA1.DI.1", "UPS.ONLINE", "NO")], devices)).sources[0].notices == []
    read = system.read
    core.device_manager.update_comm("EPM1")
    every = (B.POWER_BIT_MAINS_OK | B.POWER_BIT_L1_OK | B.POWER_BIT_L2_OK | B.POWER_BIT_L3_OK
             | B.POWER_BIT_NEUTRAL_OK | B.POWER_BIT_POWER_24V_OK)
    values = [0] * B.POWER_BLOCK[1]
    values[B.POWER_STATUS] = every
    core.event_bus.emit("device_block_read", "EPM1", "POWER", values)
    core.tag_manager.publish_from_driver("ELA1.DI.1", False)             # the contact says L2 is gone
    assert read("PWR.L2_OK") is False, "the point's role must win for this bit"
    assert read("PWR.L1_OK") is True and read("PWR.MAINS_OK") is True, "every other PWR bit is still the EPM's"
    core.tag_manager.publish_from_driver("ELA1.DI.1", True)
    assert read("PWR.L2_OK") is True


def test_two_contacts_on_one_role_and_a_role_on_the_wrong_kind_of_point():
    core = _core([_point("ELA1.DI.1", "PWR.MAINS_OK", "NO"), _point("ELA1.DI.2", "PWR.MAINS_OK", "NO"),
                  _point("ELA1.DI.3", "UPS.OVERLOAD", "NO"), _point("ELA1.DI.4", "UPS.OVERLOAD", "NO"),
                  _point("ELA1.AI.1", "PROT.ANY_TRIP", "NO", kind="AI")])
    system = _system(core)
    read = system.read
    for n in (1, 2, 3, 4):
        core.tag_manager.publish_from_driver(f"ELA1.DI.{n}", False)
    core.tag_manager.publish_from_driver("ELA1.DI.1", True)
    assert read("PWR.MAINS_OK") is False, "healthy needs every contact"
    core.tag_manager.publish_from_driver("ELA1.DI.2", True)
    assert read("PWR.MAINS_OK") is True
    core.tag_manager.publish_from_driver("ELA1.DI.4", True)
    assert read("UPS.OVERLOAD") is True, "an event needs any contact"
    assert not system.sources[0].serves("PROT.ANY_TRIP"), "an AI point cannot carry a role"
    assert "PROT.ANY_TRIP" not in system.sources[0].assignments()


# --- on the virtual bus ------------------------------------------------------------------------

def _wait(predicate, timeout=8.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return predicate()


def test_on_the_virtual_bus_a_ups_contact_becomes_the_bit_and_a_silent_card_reads_safe_and_offline(tmp_path, db):
    from epw_os.core.epw_core import EPWCore
    sim = _load_tool("modbus_sim")
    bus = sim.VirtualBus({1: {"di": 8}})
    directory = tmp_path / "controller"
    directory.mkdir(parents=True)
    project = pf.new_project("Role")
    project.cards = [pf.Card(id="ELA1", model="ELA01", channel_kinds={"DI": 8}, modbus_unit_id=1)]
    project.points = [pf.Point(address="ELA1.DI.1", role="PWR.MAINS_OK", contact="NC"),
                      pf.Point(address="ELA1.DI.2", role="UPS.ON_BATTERY", contact="NO"),
                      pf.Point(address="ELA1.DI.3", role="UPS.FAULT", contact="NC")]
    project.modbus_bus = pf.ModbusBusConfig(transport="TCP", host="127.0.0.1", tcp_port=bus.port)
    path = directory / "projekt.epw"
    pf.save_project(project, path)
    (directory / "controller.local.json").write_text(json.dumps({
        "format": "EPW_CONTROLLER_SETTINGS", "schema_version": 1,
        "io_driver": {"driver": "MODBUS", "poll_interval_ms": 40, "timeout_s": 0.3, "retries": 0}}), encoding="utf-8")
    core = EPWCore()
    core.project_manager.project_file = str(path)
    core.startup()
    try:
        read = core.logic_engine._io.read_system_signal
        assert _wait(lambda: read("COMM.ELA1.ONLINE"))
        # inputs open: NC "mains OK" relay energised, NO "on battery" open, NC "fault" open = fault
        assert _wait(lambda: read("PWR.MAINS_OK") is True)
        assert read("PWR.MAINS_LOST") is False and read("UPS.ON_BATTERY") is False and read("UPS.FAULT") is True
        bus.set_input(1, 1, True)      # mains relay dropped
        bus.set_input(1, 2, True)      # UPS on battery
        bus.set_input(1, 3, True)      # fault contact closed = no fault
        assert _wait(lambda: read("PWR.MAINS_LOST") is True and read("UPS.ON_BATTERY") is True)
        assert read("PWR.MAINS_OK") is False and read("UPS.FAULT") is False
        # the card stops answering: safe values AND COMM says why (Z4)
        bus.silence(1)
        assert _wait(lambda: read("COMM.ELA1.ONLINE") is False, timeout=12.0)
        assert read("PWR.MAINS_OK") is False and read("PWR.MAINS_LOST") is True
        assert read("UPS.ON_BATTERY") is False and read("UPS.FAULT") is True
        bus.silence(1, False)
        assert _wait(lambda: read("COMM.ELA1.ONLINE") and read("UPS.ON_BATTERY") is True)
        assert read("UPS.FAULT") is False
    finally:
        core.shutdown()
        bus.close()
