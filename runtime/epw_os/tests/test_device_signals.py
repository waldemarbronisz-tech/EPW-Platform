"""Etap 3 of the signal register: PROT / PWR / DEV / DIAG exposed from
what the DEVICES report (core/device_signals.py) over the register maps
in drivers/device_blocks.py, with the same maps emulated on the virtual
bus (tools/device_emulation.py). Rule Z3 throughout: the controller
reads the card's status words, it decides nothing. Rule Z4: a silent
card gives the safe value and COMM says why. The last test is 3.6 -
the whole chain from an emulated ADA01 stage trip to a coil the LOGIC
closes, a lost phase on an emulated EPM, a silent ADA01, and a restart
after which the latch comes back from the device."""
import importlib.util
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

from epw_os.core import project_format as pf  # noqa: E402
from epw_os.core.access_manager import AccessLevel  # noqa: E402
from epw_os.core.alarm_manager import AlarmManager  # noqa: E402
from epw_os.core.device_manager import DeviceManager  # noqa: E402
from epw_os.core.device_signals import DeviceSignals  # noqa: E402
from epw_os.core.events import EventBus  # noqa: E402
from epw_os.core.logic_runtime import SystemSignalSource, TagIOProvider  # noqa: E402
from epw_os.core.tag_manager import TagManager  # noqa: E402
from epw_os.drivers import device_blocks as B  # noqa: E402
from epw_os.drivers.modbus_driver import ModbusDriver  # noqa: E402
from epw_os.tests import _logic_program  # noqa: E402
from shared.logic.protection_stages import STAGE_IDS, STAGE_INDEX, settings_checksum  # noqa: E402

_TOOLS = Path(__file__).resolve().parents[2] / "tools"


def _load_tool(name):
    spec = importlib.util.spec_from_file_location(f"{name}_for_tests", _TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sim = _load_tool("modbus_sim")
emu = _load_tool("device_emulation")


class _Audit:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))

    def types(self):
        return [e[0] for e in self.entries]


class _Driver:
    def __init__(self):
        self.writes = []
        self.fail = False

    def write_device_register(self, card_id, address, value):
        self.writes.append((card_id, address, value))
        return not self.fail

    def reset_comm_stats(self, device_id=None):
        self.writes.append(("reset_stats", device_id))

    def reconnect(self):
        self.writes.append(("reconnect",))
        return True


def _core(settings=None):
    bus = EventBus()
    manager = DeviceManager(bus)
    for card in ("ELA1", "ADA1", "EPM1"):
        manager.register_device(card, "MODBUS", timeout=5.0)
    core = SimpleNamespace(
        event_bus=bus, device_manager=manager, alarm_manager=AlarmManager(bus), audit_logger=_Audit(),
        modbus_driver=_Driver(), _modbus_card_ids={"ELA1", "ADA1", "EPM1"}, health_manager=None,
        tag_manager=TagManager(bus),
        project_manager=SimpleNamespace(
            config={"devices": [{"id": "ELA1", "model": "ELA01", "kind": "DI"}, {"id": "ADA1", "model": "ADA01", "kind": "DO"},
                                {"id": "EPM1", "model": "EPM", "kind": None}]},
            get_electrical_protection_stages=lambda: list(settings or [])),
    )
    return core


def _source(core):
    signals = DeviceSignals(core)
    system = SystemSignalSource(sources=[signals])
    return signals, system


def _prot_block(status=B.PROT_BIT_READY | B.PROT_BIT_ACTIVE, checksum=0, **stage_words):
    values = [0] * B.PROT_BLOCK[1]
    values[0] = status
    values[B.PROT_CHECKSUM_LO - B.PROT_BLOCK[0]] = checksum
    base = B.PROT_STAGE_BASE - B.PROT_BLOCK[0]
    for sid in STAGE_IDS:
        values[base + STAGE_INDEX[sid]] = stage_words.get(sid, B.STAGE_BIT_ENABLED)
    return values


def _online(core, *cards):
    for card in cards:
        core.device_manager.update_comm(card)


# --- PROT from ADA01's words ------------------------------------------------------

def test_a_stage_word_from_ada01_becomes_the_stage_bits_and_the_summaries():
    core = _core()
    signals, system = _source(core)
    _online(core, "ADA1")
    core.event_bus.emit("device_block_read", "ADA1", "PROT", _prot_block(
        status=B.PROT_BIT_READY | B.PROT_BIT_ACTIVE | B.PROT_BIT_ANY_TRIP | B.PROT_BIT_ANY_START,
        UV_STAGE1=B.STAGE_BIT_ENABLED | B.STAGE_BIT_TRIP | B.STAGE_BIT_LATCHED,
        OV_STAGE2=B.STAGE_BIT_ENABLED | B.STAGE_BIT_START,
        TOC_STAGE1=B.STAGE_BIT_ENABLED | B.STAGE_BIT_BLOCKED,
        PHSEQ_STAGE1=0))
    r = system.read
    assert r("PROT.READY") is True and r("PROT.ACTIVE") is True and r("PROT.FAIL") is False
    assert r("PROT.UV_STAGE1.TRIP") is True and r("PROT.UV_STAGE1.LATCHED") is True and r("PROT.UV_STAGE1.START") is False
    assert r("PROT.OV_STAGE2.START") is True and r("PROT.OV_STAGE2.TRIP") is False
    assert r("PROT.TOC_STAGE1.BLOCKED") is True and r("PROT.PHSEQ_STAGE1.ENABLED") is False
    assert r("PROT.UNDERVOLTAGE") is True and r("PROT.OVERVOLTAGE") is False and r("PROT.OVERCURRENT") is False
    assert r("PROT.ANY_TRIP") is True and r("PROT.ANY_START") is True and r("PROT.BLOCKED") is False
    # The same 47 stage feeds both register bits (the rozjazd named in the report).
    core.event_bus.emit("device_block_read", "ADA1", "PROT", _prot_block(PHSEQ_STAGE1=B.STAGE_BIT_ENABLED | B.STAGE_BIT_TRIP))
    assert r("PROT.PHASE_LOSS") is True and r("PROT.PHASE_SEQUENCE_FAULT") is True and r("PROT.UNDERVOLTAGE") is False


def test_a_silent_ada01_gives_the_safe_values_not_the_last_words():
    core = _core()
    signals, system = _source(core)
    _online(core, "ADA1")
    core.event_bus.emit("device_block_read", "ADA1", "PROT", _prot_block(UV_STAGE1=B.STAGE_BIT_ENABLED | B.STAGE_BIT_TRIP))
    assert system.read("PROT.UV_STAGE1.TRIP") is True and system.read("PROT.READY") is True
    core.device_manager.devices["ADA1"]["status"] = "COMM_FAILURE"
    assert system.read("PROT.UV_STAGE1.TRIP") is False and system.read("PROT.READY") is False
    assert system.read("PROT.FAIL") is True                                   # the safe value of FAIL is TRUE
    assert system.read("PROT.UV_STAGE1.ENABLED") is False
    no_ada = _core()
    no_ada.project_manager.config["devices"] = [{"id": "ELA1", "model": "ELA01", "kind": "DI"}]
    assert _source(no_ada)[1].read("PROT.FAIL") is True                       # no protection device at all


def test_the_card_wins_over_the_project_settings_and_the_difference_is_an_alarm():
    settings = [{"function_id": "27 Under Voltage", "stage_name": "Stage 1", "enabled": False, "setting": 200.0,
                 "hysteresis": 5.0, "delay_ms": 5000, "action": "Warning"}]
    core = _core(settings)
    signals, system = _source(core)
    _online(core, "ADA1")
    matching = settings_checksum(settings)
    core.event_bus.emit("device_block_read", "ADA1", "PROT", _prot_block(checksum=matching, UV_STAGE1=0))
    assert system.read("PROT.SETTINGS_MISMATCH") is False and not core.alarm_manager.get_active_alarms()
    # The card says ENABLED, the project says disabled: the card's word is what the logic sees.
    core.event_bus.emit("device_block_read", "ADA1", "PROT", _prot_block(checksum=0xBEEF, UV_STAGE1=B.STAGE_BIT_ENABLED))
    assert system.read("PROT.UV_STAGE1.ENABLED") is True
    assert system.read("PROT.SETTINGS_MISMATCH") is True
    alarms = core.alarm_manager.get_active_alarms()
    assert alarms and "PROT_SETTINGS_MISMATCH_ADA1" in [a.id for a in alarms] and "0xbeef" in alarms[0].message
    core.event_bus.emit("device_block_read", "ADA1", "PROT", _prot_block(checksum=matching))
    assert system.read("PROT.SETTINGS_MISMATCH") is False and not core.alarm_manager.get_active_alarms()


# --- PWR from EPM, DEV from the cards ---------------------------------------------

def _power_block(status):
    values = [0] * B.POWER_BLOCK[1]
    values[B.POWER_STATUS] = status
    return values


def _diag_block(status, temperature_c=35.0):
    values = [0] * B.DIAG_BLOCK[1]
    values[0] = status
    values[B.DIAG_TEMPERATURE - B.DIAG_STATUS] = int(temperature_c * 10) & 0xFFFF
    return values


def test_pwr_follows_the_epm_status_word_and_goes_safe_when_the_meter_is_silent():
    core = _core()
    signals, system = _source(core)
    r = system.read
    assert r("PWR.MAINS_LOST") is True and r("PWR.MAINS_OK") is False and r("PWR.POWER_24V_FAULT") is True   # never heard from
    _online(core, "EPM1")
    every = sum(bit for bit in (B.POWER_BIT_MAINS_OK, B.POWER_BIT_L1_OK, B.POWER_BIT_L2_OK, B.POWER_BIT_L3_OK,
                                B.POWER_BIT_NEUTRAL_OK, B.POWER_BIT_PHASE_SEQUENCE_OK, B.POWER_BIT_BACKUP_AVAILABLE,
                                B.POWER_BIT_DC_BUS_OK, B.POWER_BIT_AUX_POWER_OK, B.POWER_BIT_POWER_24V_OK))
    core.event_bus.emit("device_block_read", "EPM1", "POWER", _power_block(every))
    assert r("PWR.MAINS_OK") and r("PWR.L2_OK") and r("PWR.POWER_24V_OK") and not r("PWR.MAINS_LOST")
    assert r("PWR.BACKUP_AVAILABLE") is True and r("PWR.BACKUP_ACTIVE") is False
    core.event_bus.emit("device_block_read", "EPM1", "POWER", _power_block(every & ~B.POWER_BIT_L2_OK & ~B.POWER_BIT_MAINS_OK))
    assert r("PWR.L2_OK") is False and r("PWR.L1_OK") is True and r("PWR.MAINS_LOST") is True
    core.device_manager.devices["EPM1"]["status"] = "COMM_FAILURE"
    assert r("PWR.L1_OK") is False and r("PWR.MAINS_LOST") is True and r("PWR.POWER_24V_FAULT") is True


def test_dev_and_diag_follow_the_cards_diagnostic_words():
    core = _core()
    signals, system = _source(core)
    r = system.read
    assert r("DEV.ELA1.FAULT") is True and r("DEV.ELA1.WATCHDOG_FAULT") is True and r("DEV.ELA1.READY") is False
    _online(core, "ELA1", "ADA1", "EPM1")
    healthy = B.DIAG_BIT_READY | B.DIAG_BIT_RUNNING | B.DIAG_BIT_WATCHDOG_OK | B.DIAG_BIT_POWER_OK | B.DIAG_BIT_CONFIG_OK
    for card in ("ELA1", "ADA1", "EPM1"):
        core.event_bus.emit("device_block_read", card, "DIAG", _diag_block(healthy | B.DIAG_BIT_SIMULATION))
    assert r("DEV.ELA1.READY") and r("DEV.ELA1.RUNNING") and r("DEV.ELA1.SIMULATION") and not r("DEV.ELA1.FAULT")
    assert r("DEV.ELA1.WATCHDOG_FAULT") is False and r("DEV.ELA1.MAINTENANCE") is False
    assert r("DIAG.IO_FAULT") is False and r("DIAG.WATCHDOG_FAULT") is False and r("DIAG.HIGH_TEMP") is False
    core.event_bus.emit("device_block_read", "ADA1", "DIAG", _diag_block((healthy | B.DIAG_BIT_FAULT) & ~B.DIAG_BIT_WATCHDOG_OK, 81.5))
    assert r("DEV.ADA1.FAULT") is True and r("DEV.ADA1.WATCHDOG_FAULT") is True
    assert r("DIAG.IO_FAULT") is True and r("DIAG.WATCHDOG_FAULT") is True and r("DIAG.HIGH_TEMP") is True
    assert r("DIAG.ANY_FAULT") is True
    core.event_bus.emit("device_block_read", "EPM1", "DIAG", _diag_block(healthy & ~B.DIAG_BIT_CONFIG_OK))
    assert r("DIAG.CONFIG_FAULT") is True


# --- the requests -------------------------------------------------------------------

def test_requests_write_ada01s_command_registers_and_refusals_are_audited():
    core = _core()
    signals, system = _source(core)
    access = SimpleNamespace(level=AccessLevel.OPERATOR, has_access=lambda req: AccessLevel._ORDER.index(AccessLevel.OPERATOR) >= AccessLevel._ORDER.index(req))
    io = TagIOProvider(core.tag_manager, access_manager=access, audit_logger=core.audit_logger, system_signals=system)
    io.command_levels = {}
    # ADA1 silent: refused, audited, nothing written.
    io.write_system_signal("REQ.PROT.RESET_LATCH", True)
    assert core.modbus_driver.writes == [] and core.audit_logger.types()[-1] == "PROTECTION_REQUEST_REFUSED"
    assert "not answering" in core.audit_logger.entries[-1][2]
    _online(core, "ADA1", "ELA1")
    io.write_system_signal("REQ.PROT.RESET_LATCH", False)
    io.write_system_signal("REQ.PROT.RESET_LATCH", True)
    assert core.modbus_driver.writes[-1] == ("ADA1", B.PROT_CMD, B.PROT_CMD_RESET_LATCH)
    assert core.audit_logger.types()[-1] == "PROTECTION_REQUEST" and core.audit_logger.entries[-1][3] is True
    io.write_system_signal("REQ.PROT.TEST", True)
    assert core.modbus_driver.writes[-1] == ("ADA1", B.PROT_CMD, B.PROT_CMD_SELFTEST)
    # Blocking a stage is an engineer's act: refused at Operator, executed at Engineer.
    io.write_system_signal("REQ.PROT.UV_STAGE1.BLOCK", True)
    assert core.modbus_driver.writes[-1][1] != B.PROT_BLOCK_STAGE
    assert core.audit_logger.types()[-1] == "LOGIC_REQUEST_REFUSED" and "Engineer" in core.audit_logger.entries[-1][2]
    access.level = AccessLevel.ENGINEER
    access.has_access = lambda req: True
    io.write_system_signal("REQ.PROT.UV_STAGE1.BLOCK", False)
    io.write_system_signal("REQ.PROT.UV_STAGE1.BLOCK", True)
    assert core.modbus_driver.writes[-1] == ("ADA1", B.PROT_BLOCK_STAGE, STAGE_INDEX["UV_STAGE1"] + 1)
    io.write_system_signal("REQ.PROT.UV_STAGE1.UNBLOCK", True)
    assert core.modbus_driver.writes[-1] == ("ADA1", B.PROT_UNBLOCK_STAGE, STAGE_INDEX["UV_STAGE1"] + 1)
    io.write_system_signal("REQ.DEV.ELA1.RESET", True)
    assert core.modbus_driver.writes[-1] == ("ELA1", B.DIAG_CMD, B.DIAG_CMD_RESET)
    io.write_system_signal("REQ.DEV.ELA1.RECONNECT", True)
    assert core.modbus_driver.writes[-1] == ("reconnect",) and core.audit_logger.types()[-1] == "DEVICE_REQUEST"


# --- the driver and the emulation over the same map --------------------------------------

def test_the_driver_reads_the_emulated_blocks_and_writes_the_emulated_commands():
    bus = sim.VirtualBus({1: {"di": 8}, 2: {"do": 8}, 3: {}})
    dispatcher = emu.EmulationDispatcher(bus)
    ada = emu.Ada01Emulator(bus, 2)
    epm = emu.EpmEmulator(bus, 3)
    diag = emu.CardDiagEmulator(bus, 1, temperature_c=41.5)
    for e in (ada, epm, diag, emu.CardDiagEmulator(bus, 2), emu.CardDiagEmulator(bus, 3)):
        dispatcher.attach(e)
    events = []
    event_bus = EventBus()
    event_bus.subscribe("device_block_read", lambda card, block, values: events.append((card, block, list(values))))
    driver = ModbusDriver(event_bus)
    polled = driver.configure({"transport": "TCP", "host": bus.host, "tcp_port": bus.port},
                              [{"id": "ELA1", "kind": "DI", "channels": 8, "modbus_unit_id": 1, "model": "ELA01"},
                               {"id": "ADA1", "kind": "DO", "channels": 8, "modbus_unit_id": 2, "model": "ADA01"},
                               {"id": "EPM1", "kind": None, "channels": 0, "modbus_unit_id": 3, "model": "EPM"}],
                              {"poll_interval_ms": 50, "timeout_s": 0.5, "retries": 0})
    try:
        assert polled == ["ELA1", "ADA1", "EPM1"]
        ada.trip("UV_STAGE1")
        epm.set_phase(2, False)
        for card in ({"id": "ELA1", "unit": 1, "kinds": {"DI": 8}, "model": "ELA01"},
                     {"id": "ADA1", "unit": 2, "kinds": {"DO": 8}, "model": "ADA01"},
                     {"id": "EPM1", "unit": 3, "kinds": {}, "model": "EPM"}):
            assert driver.poll_card(card) is True
        blocks = {(card, block): values for card, block, values in events}
        assert set(blocks) == {("ELA1", "DIAG"), ("ADA1", "PROT"), ("ADA1", "DIAG"), ("EPM1", "POWER"), ("EPM1", "DIAG")}
        prot = blocks[("ADA1", "PROT")]
        assert prot[0] & B.PROT_BIT_ANY_TRIP and prot[0] & B.PROT_BIT_ANY_LATCHED
        assert prot[B.PROT_STAGE_BASE - B.PROT_STATUS + STAGE_INDEX["UV_STAGE1"]] & B.STAGE_BIT_TRIP
        assert not blocks[("EPM1", "POWER")][B.POWER_STATUS] & B.POWER_BIT_L2_OK
        assert blocks[("ELA1", "DIAG")][B.DIAG_TEMPERATURE - B.DIAG_STATUS] == 415
        assert blocks[("ELA1", "DIAG")][0] & B.DIAG_BIT_SIMULATION

        assert driver.write_device_register("ADA1", B.PROT_CMD, B.PROT_CMD_RESET_LATCH) is True
        assert ("CMD", B.PROT_CMD_RESET_LATCH) in ada.commands
        assert not ada.stage_word("UV_STAGE1") & B.STAGE_BIT_TRIP
        assert driver.write_device_register("ADA1", B.PROT_BLOCK_STAGE, STAGE_INDEX["OV_STAGE1"] + 1) is True
        assert ada.stage_word("OV_STAGE1") & B.STAGE_BIT_BLOCKED and ada.trip("OV_STAGE1") is False
        assert driver.write_device_register("ELA1", B.DIAG_CMD, B.DIAG_CMD_RESET) is True and diag.resets == 1
        assert driver.write_device_register("XYZ", B.DIAG_CMD, 1) is False
    finally:
        driver.stop()
        bus.close()


def test_the_checksum_is_one_number_the_card_and_the_project_agree_on():
    settings = [{"function_id": "27 Under Voltage", "stage_name": "Stage 1", "enabled": True, "setting": 200.0,
                 "hysteresis": 5.0, "delay_ms": 5000, "action": "Warning"}]
    assert settings_checksum(settings) == settings_checksum(list(settings))
    assert settings_checksum(settings) != settings_checksum([dict(settings[0], setting=190.0)])
    assert settings_checksum(settings) != settings_checksum([dict(settings[0], enabled=False)])
    assert settings_checksum([]) == settings_checksum([{"function_id": "nope", "stage_name": "x"}])   # unknown rows are ignored
    bus = sim.VirtualBus({2: {"do": 8}})
    ada = emu.Ada01Emulator(bus, 2, settings=settings)
    try:
        assert bus.units[2].input_registers[B.PROT_CHECKSUM_LO] == settings_checksum(settings)
        assert ada.stage_word("UV_STAGE1") & B.STAGE_BIT_ENABLED
        ada.apply_settings([dict(settings[0], enabled=False)])
        assert not ada.stage_word("UV_STAGE1") & B.STAGE_BIT_ENABLED
    finally:
        bus.close()


# --- 3.6: the whole chain on the virtual bus -----------------------------------------------

def _wait(predicate, timeout=8.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return predicate()


def _trip_to_coil_program():
    """The logic: PROT.UV_STAGE1.TRIP straight onto ADA1.DO.1."""
    source = _logic_program.make_block("virtual.input", Bit="PROT.UV_STAGE1.TRIP")
    sink = _logic_program.make_block("output.do", Address="ADA1.DO.1")
    _logic_program.connect(source, sink)
    return _logic_program.export([source, sink])


def _project(directory: Path, bus_port: int) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    project = pf.new_project("Etap 3")
    project.cards = [pf.Card(id="ELA1", model="ELA01", channel_kinds={"DI": 8}, modbus_unit_id=1),
                     pf.Card(id="ADA1", model="ADA01", channel_kinds={"DO": 8}, modbus_unit_id=2),
                     pf.Card(id="EPM1", model="EPM", channel_kinds={}, modbus_unit_id=3)]
    project.points = [pf.Point(address="ELA1.DI.1"), pf.Point(address="ADA1.DO.1")]
    project.electrical_protection_stages = [pf.ElectricalProtectionStage(
        function_id="27 Under Voltage", stage_name="Stage 1", enabled=True, setting=200.0, hysteresis=5.0,
        delay_ms=5000, action="Warning")]
    project.modbus_bus = pf.ModbusBusConfig(transport="TCP", host="127.0.0.1", tcp_port=bus_port)
    project.logic_runtime = _trip_to_coil_program()
    path = directory / "projekt.epw"
    pf.save_project(project, path)
    (directory / "controller.local.json").write_text(json.dumps({
        "format": "EPW_CONTROLLER_SETTINGS", "schema_version": 1,
        "io_driver": {"driver": "MODBUS", "poll_interval_ms": 40, "timeout_s": 0.3, "retries": 0}}), encoding="utf-8")
    return path


def test_3_6_from_an_emulated_trip_to_the_coil_the_logic_closes_and_back_from_a_restart(tmp_path, db):
    from epw_os.core.epw_core import EPWCore

    bus = sim.VirtualBus({1: {"di": 8}, 2: {"do": 8}, 3: {}})
    dispatcher = emu.EmulationDispatcher(bus)
    settings = [{"function_id": "27 Under Voltage", "stage_name": "Stage 1", "enabled": True, "setting": 200.0,
                 "hysteresis": 5.0, "delay_ms": 5000, "action": "Warning"}]
    ada = emu.Ada01Emulator(bus, 2, settings=settings)
    epm = emu.EpmEmulator(bus, 3)
    for e in (ada, epm, emu.CardDiagEmulator(bus, 1), emu.CardDiagEmulator(bus, 2), emu.CardDiagEmulator(bus, 3)):
        dispatcher.attach(e)
    project_path = _project(tmp_path / "controller", bus.port)

    def start():
        core = EPWCore()
        core.project_manager.project_file = str(project_path)
        core.startup()
        return core

    core = start()
    try:
        read = core.logic_engine._io.read_system_signal
        assert _wait(lambda: read("PROT.READY") and read("COMM.ADA1.ONLINE") and read("COMM.EPM1.ONLINE"))
        assert read("PROT.ANY_TRIP") is False and read("PROT.SETTINGS_MISMATCH") is False
        assert read("PWR.MAINS_OK") is True and read("DEV.EPM1.SIMULATION") is True
        assert core.logic_engine.is_running and bus.coil(2, 1) is False

        # (a) the emulated ADA01 declares UV stage 1 tripped -> the bits, and the LOGIC closes the coil
        ada.trip("UV_STAGE1")
        assert _wait(lambda: read("PROT.UV_STAGE1.TRIP") and read("PROT.ANY_TRIP") and read("PROT.UNDERVOLTAGE"))
        assert read("PROT.UV_STAGE1.LATCHED") is True
        assert _wait(lambda: bus.coil(2, 1)), "the logic did not drive ADA1.DO.1 from PROT.UV_STAGE1.TRIP"

        # (b) the emulated EPM loses L2
        epm.set_phase(2, False)
        assert _wait(lambda: read("PWR.L2_OK") is False)
        assert read("PWR.L1_OK") is True and read("PWR.MAINS_OK") is False and read("PWR.MAINS_LOST") is True

        # (c) the emulated ADA01 stops answering -> safe values AND COMM says why (rule Z4)
        bus.silence(2)
        assert _wait(lambda: read("COMM.ADA1.ONLINE") is False, timeout=12.0)
        assert read("PROT.UV_STAGE1.TRIP") is False and read("PROT.READY") is False and read("PROT.FAIL") is True
        assert read("COMM.ADA1.OFFLINE") is True and read("COMM.EPM1.ONLINE") is True
        bus.silence(2, False)
        assert _wait(lambda: read("COMM.ADA1.ONLINE") and read("PROT.UV_STAGE1.TRIP"))

        # the card's settings drift from the project: an alarm, not a silent choice
        ada.set_checksum(0x1234)
        assert _wait(lambda: read("PROT.SETTINGS_MISMATCH"))
        assert any(a.id == "PROT_SETTINGS_MISMATCH_ADA1" for a in core.alarm_manager.get_active_alarms())
        ada.apply_settings(settings)
        assert _wait(lambda: read("PROT.SETTINGS_MISMATCH") is False)
    finally:
        core.shutdown()

    # (d) a restart: the latch lives in the device, the bit comes back from it
    core = start()
    try:
        read = core.logic_engine._io.read_system_signal
        assert _wait(lambda: read("PROT.UV_STAGE1.LATCHED") and read("PROT.UV_STAGE1.TRIP"))
        # and the logic can clear it: REQ.PROT.RESET_LATCH at the operator's level
        core.access_manager.level = AccessLevel.OPERATOR
        io = core.logic_engine._io
        io.write_system_signal("REQ.PROT.RESET_LATCH", True)
        assert ("CMD", B.PROT_CMD_RESET_LATCH) in ada.commands
        assert _wait(lambda: read("PROT.UV_STAGE1.TRIP") is False and read("PROT.UV_STAGE1.LATCHED") is False)
        assert _wait(lambda: bus.coil(2, 1) is False)
    finally:
        core.shutdown()
        bus.close()
