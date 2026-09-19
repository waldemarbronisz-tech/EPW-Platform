"""Task "runtime wykonuje logikę użytkownika": the controller scans the
program Logic Studio compiled, instead of merely holding the file.

Everything below is about what the CONTROLLER does with a program: that
a scan really reaches the driver layer, that it fails safe, that it never
gets a private path to the hardware an operator command does not have
(Training Mode, forces), and that it refuses a program it cannot execute
faithfully. The other half of the contract - that a program compiled in
Logic Studio produces the same results here as it did on the canvas -
lives in shared/tests/test_logic_execution_contract.py.
"""
import sys
import time
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core import project_format as pf
from epw_os.core.analog_scaling import SIGNAL_TYPE_READY
from epw_os.core.epw_core import EPWCore
from epw_os.core.logic_engine import LogicEngine
from epw_os.core.logic_runtime import SystemSignalSource, TagIOProvider
from epw_os.tests import _logic_program

DI = "ELA1.DI.1"
DO = "ADA1.DO.1"
AI = "ELA1.AI.1"
AO = "ADA1.AO.1"


def _project(directory: Path, logic_runtime) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    project = pf.new_project("Logic execution")
    project.modules = ["analog_inputs"]
    project.cards = [pf.Card(id="ELA1", model="ELA", channel_kinds={"DI": 2, "AI": 2}, modbus_unit_id=1),
                     pf.Card(id="ADA1", model="ADA", channel_kinds={"DO": 2, "AO": 2}, modbus_unit_id=2)]
    project.points = [pf.Point(address=DI), pf.Point(address="ELA1.DI.2"),
                      pf.Point(address=AI, signal_type=SIGNAL_TYPE_READY, eng_min=0.0, eng_max=100.0, unit="%"),
                      pf.Point(address="ELA1.AI.2"),
                      pf.Point(address=DO), pf.Point(address="ADA1.DO.2"),
                      pf.Point(address=AO, signal_type="4-20mA", raw_min=4.0, raw_max=20.0,
                               eng_min=0.0, eng_max=100.0, unit="%", decimals=0),
                      pf.Point(address="ADA1.AO.2")]
    project.logic_runtime = logic_runtime
    path = directory / "projekt.epw"
    pf.save_project(project, path)
    return path


@pytest.fixture
def start_core(tmp_path, db):
    cores = []

    def _start(logic_runtime, subdir="site"):
        instance = EPWCore()
        instance.project_manager.project_file = str(_project(tmp_path / subdir, logic_runtime))
        instance.startup()
        cores.append(instance)
        return instance

    yield _start
    for instance in cores:
        if instance.is_running:
            instance.shutdown()


@pytest.fixture(autouse=True)
def driver_writes(monkeypatch):
    """Everything that actually crossed the driver boundary."""
    from epw_os.drivers.simulator_driver import SimulatorDriver
    original = SimulatorDriver.write_tag
    recorded = []

    def recording(self, tag_name, value):
        recorded.append((tag_name, value))
        return original(self, tag_name, value)

    monkeypatch.setattr(SimulatorDriver, "write_tag", recording, raising=True)
    return recorded


def _wait_for(predicate, timeout: float = 3.0) -> bool:
    """Waits for the real scan thread rather than stepping the engine by
    hand - the thread and its cycle time are part of what is under test."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


# --- the scan itself ---------------------------------------------------------

def test_the_controller_scans_the_program_and_drives_the_output(start_core, driver_writes):
    core = start_core(_logic_program.di_to_do(DI, DO))
    assert core.logic_engine.is_running is True
    assert core.health_manager.get_health()["LOGIC_RUNTIME"] == "RUNNING"

    core.tag_manager.publish_from_driver(DI, True)
    assert _wait_for(lambda: (DO, True) in driver_writes), driver_writes

    core.tag_manager.publish_from_driver(DI, False)
    assert _wait_for(lambda: (DO, False) in driver_writes[driver_writes.index((DO, True)):]), driver_writes

    status = core.logic_engine.get_status()
    assert status["running"] is True
    assert status["scan_count"] > 0
    assert status["driven_outputs"] == [DO]


def test_an_analog_output_written_by_logic_is_scaled_like_an_operator_write(start_core, driver_writes):
    core = start_core(_logic_program.ai_to_ao(AI, AO))
    core.tag_manager.publish_from_driver(AI, 50.0)
    # 50 % of a 4-20 mA point is 12 mA - the same raw value
    # EPWCore.write_analog_output() computes for an operator, because both
    # go through the one _route_analog_output().
    assert _wait_for(lambda: any(tag == AO and abs(value - 12.0) < 0.001 for tag, value in driver_writes)), \
        driver_writes


def test_stopping_the_scan_drives_the_outputs_safe(start_core, driver_writes):
    core = start_core(_logic_program.di_to_do(DI, DO))
    core.tag_manager.publish_from_driver(DI, True)
    assert _wait_for(lambda: (DO, True) in driver_writes), driver_writes

    core.shutdown()
    # Not latched at its last value: stopping drives every output the
    # program ever touched to its safe state.
    assert driver_writes[-1] == (DO, False)
    assert core.logic_engine.is_running is False


# --- the program is never given a private path to the hardware ---------------

def test_training_mode_cuts_a_logic_driven_output_at_the_driver_boundary(start_core, driver_writes):
    core = start_core(_logic_program.di_to_do(DI, DO))
    core.training_mode.set_active(True)
    driver_writes.clear()

    core.tag_manager.publish_from_driver(DI, True)
    # The scan keeps running and the interface still follows along (the
    # driver_update event is emitted), but nothing reaches a driver.
    assert _wait_for(lambda: core.logic_engine.get_status()["scan_count"] > 0)
    time.sleep(0.15)
    assert [w for w in driver_writes if w[0] == DO] == []


def test_a_forced_output_is_not_written_by_the_program(start_core, driver_writes):
    core = start_core(_logic_program.di_to_do(DI, DO))
    assert core.force_manager.force(DO, False, actor="Engineer")[0] is True
    driver_writes.clear()

    core.tag_manager.publish_from_driver(DI, True)
    assert _wait_for(lambda: core.logic_engine.get_status()["scan_count"] > 0)
    time.sleep(0.15)
    assert [w for w in driver_writes if w[0] == DO] == []


def test_a_manual_command_to_a_logic_driven_output_is_blocked(start_core):
    core = start_core(_logic_program.di_to_do(DI, DO))
    permitted, reasons = core.logic_engine.validate_command(DO, "CLOSE")
    assert permitted is False
    assert "driven by the logic program" in reasons[0]
    # An output the program does NOT drive stays under manual control.
    assert core.logic_engine.validate_command("ADA1.DO.2", "CLOSE") == (True, [])


# --- refusals ----------------------------------------------------------------

def test_a_tampered_program_is_refused_reported_and_blocks_commands(start_core):
    tampered = _logic_program.di_to_do(DI, DO)
    tampered["cycle_time_ms"] = 999  # covered by the checksum
    core = start_core(tampered)

    assert core.logic_engine.is_running is False
    assert core.health_manager.get_health()["LOGIC_RUNTIME"] == "FAULT"
    assert [i["id"] for i in core.startup_issues if i["id"] == "LOGIC_PROGRAM_REJECTED"] == \
        ["LOGIC_PROGRAM_REJECTED"]
    # Fail safe: a program that was configured but is not running blocks
    # commands, exactly as before this feature existed.
    permitted, reasons = core.logic_engine.validate_command("ADA1.DO.2", "CLOSE")
    assert permitted is False
    assert "Logic Runtime Unavailable" in reasons[0]


def test_a_block_type_this_controller_does_not_know_is_refused():
    program = _logic_program.di_to_do(DI, DO)
    uuid = program["execution_order"][0]
    program["blocks"][uuid]["type_id"] = "input.from_the_future"
    program["checksum"] = _logic_program.compute_checksum(program)

    engine = LogicEngine(tag_manager=None)
    assert engine.load_program_data(program) is False
    assert "block library does not know" in engine.last_error


def test_a_program_with_no_io_provider_never_starts_a_scan():
    engine = LogicEngine(tag_manager=None)
    assert engine.load_program_data(_logic_program.di_to_do(DI, DO)) is True
    assert engine.start() is False
    assert engine.is_running is False
    assert "IOProvider" in engine.last_error


# --- the system signals the controller serves --------------------------------

def test_system_signals_report_this_controller_not_a_simulation(start_core):
    core = start_core(_logic_program.di_to_do(DI, DO))
    io = core.logic_engine._io

    assert io.read_system_signal("SYS.READY") is True
    assert io.read_system_signal("SYS.TRAINING_MODE") is False
    core.training_mode.set_active(True)
    assert io.read_system_signal("SYS.TRAINING_MODE") is True

    assert io.read_system_signal("SYS.ACCESS_LEVEL") == 0.0  # every start is User
    assert io.read_system_signal("SYS.ACCESS_ENGINEER") is False
    # The generators come from the shared table, so they blink at the same
    # rate as they did in the engineer's simulation.
    assert io.read_system_signal("SYS.PULSE_1S", 100) is True
    assert io.read_system_signal("SYS.PULSE_1S", 600) is False
    # Anything this controller does not serve yet is defined and falsy,
    # never None.
    assert io.read_system_signal("SSWIN.ARMED") is False


def test_an_unserved_system_signal_write_is_reported_once():
    """A command the controller cannot execute must not vanish quietly -
    but it also must not fill the log with one line per scan."""
    import logging

    from epw_os.core.logging import log as epw_log

    records = []

    class _Collect(logging.Handler):
        def emit(self, record):
            records.append(record.getMessage())

    handler = _Collect()
    epw_log.addHandler(handler)
    # Whichever earlier test in this suite ran uvicorn's own
    # logging.config.dictConfig() left every existing logger disabled
    # (disable_existing_loggers defaults to True) - re-enabled here for
    # the duration, and put back exactly as found, so this test measures
    # the code under test and not the log configuration a neighbour left
    # behind.
    was_disabled = epw_log.disabled
    epw_log.disabled = False
    try:
        io = TagIOProvider(tag_manager=None, system_signals=SystemSignalSource())
        io.write_system_signal("SSWIN.CMD_ARM", True)
        io.write_system_signal("SSWIN.CMD_ARM", True)
    finally:
        epw_log.disabled = was_disabled
        epw_log.removeHandler(handler)

    assert len([m for m in records if "SSWIN.CMD_ARM" in m]) == 1

