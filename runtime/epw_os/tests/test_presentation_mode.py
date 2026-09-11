"""Presentation Mode (Task: "przygotowany scenariusz demonstracyjny
uruchamiany jednym poleceniem").

Covers every DOWOD UKONCZENIA item explicitly: starting without
Training Mode is rejected (the GRANICE hard requirement); a scenario
loaded from a file executes step by step (both via real wall-clock
timing and via step_forward()); stopping - whether by request or on
natural completion - restores the pre-start state; the audit log gets
start/stop entries; and a scenario step goes through the same
validation a real command would (never a shortcut around it).
"""
import json
import os
import tempfile
import time

import pytest

from epw_os.core.events import EventBus
from epw_os.core.tag_manager import TagManager, TagType, TagQuality
from epw_os.core.alarm_manager import AlarmManager
from epw_os.core.training_mode import TrainingModeManager
from epw_os.core.presentation_mode import (
    PresentationMode, PresentationModeError, PresentationScenario, PresentationStep,
    load_scenario, list_scenarios, DEFAULT_SCENARIOS_DIR,
)
from epw_os.core.device_manager import DeviceManager
from epw_os.core.driver_manager import DriverManager
from epw_os.core.logic_engine import LogicEngine
from epw_os.core.safety_kernel import SafetyKernel
from epw_os.core.command_manager import CommandManager
from epw_os.core.project_manager import ProjectManager
from epw_os.core.switching_counters import SwitchingCounterManager
from epw_os.drivers.simulator_driver import SimulatorDriver


class _RecordingCommandManager:
    """Real CommandState semantics (BLOCKED/SUCCESS), not a real
    CommandManager - used to prove a scenario "command" step goes
    through request_command_ex() and reacts correctly to a rejection,
    without needing a full safety_kernel/logic_engine wiring for every
    test."""
    def __init__(self, known_targets=None):
        self.calls = []
        self.known_targets = known_targets if known_targets is not None else {"ADA01.DO.2"}

    def request_command_ex(self, target, action, user="Operator", source="GUI"):
        self.calls.append((target, action, user, source))

        class _Record:
            pass
        rec = _Record()
        if target not in self.known_targets:
            rec.state = "BLOCKED"
            rec.reason = "Unknown command definition"
        else:
            rec.state = "SUCCESS"
            rec.reason = ""
        return rec


class _RecordingAuditLogger:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))


def _make_env(with_command_target=True):
    bus = EventBus()
    tm = TagManager(bus)
    tm.add_tag("Meas.L1", 230.1, TagType.REAL, quality=TagQuality.SIMULATED)
    tm.add_tag("ELA01.DI.2", False, TagType.BOOL)
    am = AlarmManager(bus)
    training = TrainingModeManager(bus)
    cmd = _RecordingCommandManager(known_targets={"ADA01.DO.2"} if with_command_target else set())
    audit = _RecordingAuditLogger()
    pm = PresentationMode(bus, tm, cmd, am, training, audit_logger=audit)
    return bus, tm, am, training, cmd, audit, pm


def _write_scenario(tmp_path, steps):
    path = os.path.join(tmp_path, "scenario.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"name": "Test Scenario", "description": "", "steps": steps}, f)
    return path


class _FullEnv:
    """Every real component PresentationMode's new step types (Task: 4/5
    more scenarios) actually talk to - not mocks. Deliberately NEVER
    starts SimulatorDriver's or SafetyKernel's own background threads:
    driver_manager.route_command() takes the Training Mode cutoff branch
    unconditionally whenever training_mode.active is True (which it
    always is here, the same hard requirement Presentation Mode itself
    enforces), so command dispatch/feedback works synchronously with no
    thread needed at all; SafetyKernel's health check is called directly
    (check_system_health()) instead of waiting on its 1s-cadence thread,
    for determinism - the exact same pattern test_safety_kernel.py's own
    suite already uses."""
    def __init__(self, tmp_path):
        self.bus = EventBus()
        self.tm = TagManager(self.bus)
        # Task "migracja adresacji": init_default_tags()'s own flat
        # DI1..DI64/DO05..DO64 scheme is gone - this test only ever
        # needed a handful of real DI/DO tags to drive its own scenario
        # fixtures against (ELA01.DI.1-4/ADA01.DO.1-4 below, matching the
        # shipped presentation_scenarios/*.json fixtures' own device ids,
        # not a made-up test-only name), so configure() with the same two
        # devices this env already tracks for comm-status is the direct
        # replacement, not a workaround.
        self.tm.configure([
            {"id": "ELA01", "type": "ELA", "channels": 4},
            {"id": "ADA01", "type": "ADA", "channels": 4},
        ])
        # Shipped scenario JSON fixtures (DEFAULT_SCENARIOS_DIR below)
        # reference Meas.L1/Sim.Voltage/etc, same as a real EPWCore.
        # startup() would provide - configure() only ever creates DI/DO
        # channel tags, not these (unconditional, unrelated to devices -
        # see tag_manager.py's own docstring for why they're a separate
        # method now).
        self.tm.init_simulation_and_cabinet_tags()
        self.training = TrainingModeManager(self.bus)
        self.training.set_active(True)
        self.device_manager = DeviceManager(self.bus)
        for dev_id in ("OrangePi", "ELA01", "ADA01", "Modbus"):
            self.device_manager.register_device(dev_id, "SIM_DRIVER", timeout=5.0)
        self.driver_manager = DriverManager(self.bus, training_mode=self.training)
        self.sim_driver = SimulatorDriver(self.bus)
        self.sim_driver.set_devices(["OrangePi", "ELA01", "ADA01", "Modbus"])
        self.driver_manager.register_driver("SIM_DRIVER", self.sim_driver)
        # The same "driver_to_tag" -> tag_manager.update_tag() bridge
        # EPWCore._bridge_driver_to_tag() wires in a real app - without
        # it, DriverManager's Training Mode cutoff still emits
        # driver_update/driver_to_tag correctly, but nothing ever turns
        # that into an actual tag write, so no command's feedback would
        # ever be observable here.
        def _bridge_driver_to_tag(tag_name, value, quality):
            from epw_os.core.tag_manager import TagQuality as _TQ
            q = _TQ(quality) if isinstance(quality, str) else quality
            self.tm.update_tag(tag_name, value, q)
        self.bus.subscribe("driver_to_tag", _bridge_driver_to_tag)
        # The same "driver_comm_ok" -> device_manager.update_comm() bridge
        # EPWCore._on_driver_comm_ok() wires in a real app - without it,
        # SimulatorDriver's own real per-second heartbeat never actually
        # reaches DeviceManager, so last_comm would never advance and
        # SafetyKernel could never see a device recover.
        def _bridge_driver_comm_ok(device_id):
            self.device_manager.update_comm(device_id)
            self.device_manager.check_watchdogs()
        self.bus.subscribe("driver_comm_ok", _bridge_driver_comm_ok)
        self.logic_engine = LogicEngine(self.tm)
        self.alarm_manager = AlarmManager(self.bus)
        self.safety_kernel = SafetyKernel(
            self.tm, driver_manager=self.driver_manager, logic_engine=self.logic_engine,
            device_manager=self.device_manager, alarm_manager=self.alarm_manager,
            missed_cycles_threshold=3, poll_interval=1.0,
        )
        self.command_manager = CommandManager(self.tm, self.logic_engine, self.safety_kernel, self.bus)
        self.command_manager.set_driver_manager(self.driver_manager)
        # Task "migracja adresacji": now self-contained (own tag is both
        # the command output and its own feedback), matching
        # epw_core.py's own default command definitions exactly. This
        # fixture used to route each DO's command to a SEPARATE DI
        # feedback tag (mirroring the old flat scheme's own DO01-04
        # special case), which has no equivalent to mirror anymore once
        # every real DO channel is self-contained - see epw_core.py's
        # own docstring on why that special case had no natural
        # multi-device generalization.
        defs = {}
        for tag in ("ADA01.DO.1", "ADA01.DO.2", "ADA01.DO.3", "ADA01.DO.4"):
            defs[f"{tag}.CLOSE"] = {"driver_id": "SIM_DRIVER", "output_tag": tag, "output_value": True,
                                     "feedback_tag": tag, "feedback_value": True, "timeout_ms": 1500}
            defs[f"{tag}.OPEN"] = {"driver_id": "SIM_DRIVER", "output_tag": tag, "output_value": False,
                                    "feedback_tag": tag, "feedback_value": False, "timeout_ms": 1500}
        self.command_manager.load_definitions(defs)
        self.project_manager = ProjectManager(project_file=os.path.join(str(tmp_path), "scratch_project.json"))
        self.switching_counters = SwitchingCounterManager(self.bus, self.project_manager)
        self.audit = _RecordingAuditLogger()
        self.pm = PresentationMode(
            self.bus, self.tm, self.command_manager, self.alarm_manager, self.training, self.audit,
            driver_manager=self.driver_manager, device_manager=self.device_manager,
            switching_counter_manager=self.switching_counters,
        )


# --- DOWOD: starting without Training Mode is rejected -------------------

def test_can_start_is_false_without_training_mode():
    _, _, _, training, _, _, pm = _make_env()
    assert training.active is False
    assert pm.can_start() is False


def test_start_raises_without_training_mode():
    _, _, _, training, _, _, pm = _make_env()
    scenario = PresentationScenario(name="X", steps=[PresentationStep(time_s=0, type="tag", tag="Meas.L1", value=1.0)])
    with pytest.raises(PresentationModeError):
        pm.start(scenario)
    assert pm.active is False


def test_start_succeeds_once_training_mode_active():
    _, _, _, training, _, _, pm = _make_env()
    training.set_active(True)
    scenario = PresentationScenario(name="X", steps=[PresentationStep(time_s=100, type="tag", tag="Meas.L1", value=1.0)])
    pm.start(scenario)
    assert pm.active is True
    pm.stop()


# --- DOWOD: a scenario loaded from a file executes step by step ----------

def test_shipped_sample_scenario_loads_with_expected_narrative():
    path = os.path.join(DEFAULT_SCENARIOS_DIR, "voltage_sag_trip.json")
    assert os.path.isfile(path), "the sample scenario must ship in the repo"
    scenario = load_scenario(path)
    assert len(scenario.steps) >= 5
    types = [s.type for s in scenario.steps]
    assert "command" in types and "tag" in types and "alarm" in types and "alarm_clear" in types
    # sorted by time_s regardless of file order
    assert [s.time_s for s in scenario.steps] == sorted(s.time_s for s in scenario.steps)


def test_list_scenarios_finds_the_shipped_sample():
    found = list_scenarios(DEFAULT_SCENARIOS_DIR)
    assert any(os.path.basename(p) == "voltage_sag_trip.json" for p in found)


def test_malformed_step_is_skipped_not_fatal(tmp_path):
    path = _write_scenario(str(tmp_path), [
        {"time_s": 0, "type": "tag", "tag": "Meas.L1", "value": 1.0},
        {"type": "tag"},  # missing time_s - malformed
        {"time_s": 1, "type": "tag", "tag": "Meas.L1", "value": 2.0},
    ])
    scenario = load_scenario(path)
    assert len(scenario.steps) == 2  # the malformed one was dropped, not fatal


def test_scenario_executes_step_by_step_via_real_timing():
    """Actual wall-clock scheduling, not step_forward() - proves the
    file-driven scenario really runs on its own over time."""
    bus, tm, am, training, cmd, audit, pm = _make_env()
    training.set_active(True)
    scenario = PresentationScenario(name="Timed", steps=[
        PresentationStep(time_s=0.0, type="tag", tag="Meas.L1", value=100.0, description="step0"),
        PresentationStep(time_s=0.15, type="tag", tag="Meas.L1", value=200.0, description="step1"),
        PresentationStep(time_s=0.30, type="tag", tag="Meas.L1", value=300.0, description="step2"),
    ])
    seen = []
    bus.subscribe("presentation_step", lambda i, n, d: seen.append(d))

    pm.start(scenario)
    deadline = time.time() + 5.0
    while pm.active and time.time() < deadline:
        time.sleep(0.02)

    assert seen == ["step0", "step1", "step2"]
    assert pm.active is False  # finished on its own


def test_step_forward_executes_immediately_regardless_of_schedule():
    bus, tm, am, training, cmd, audit, pm = _make_env()
    training.set_active(True)
    # A 3rd, far-future step keeps the scenario "still running" after the
    # 2nd step executes - otherwise the 2nd step being the LAST one would
    # immediately finish (and restore!) the scenario, making "the value
    # is 2.0 right after step_forward()" a check of a value that's
    # already been reset back to original by the time it runs.
    scenario = PresentationScenario(name="Slow", steps=[
        PresentationStep(time_s=0, type="tag", tag="Meas.L1", value=1.0),
        PresentationStep(time_s=999, type="tag", tag="Meas.L1", value=2.0),  # would never fire naturally in this test
        PresentationStep(time_s=1998, type="tag", tag="Meas.L1", value=3.0),
    ])
    pm.start(scenario)
    time.sleep(0.05)
    assert tm.get_value("Meas.L1") == 1.0
    pm.step_forward()
    time.sleep(0.05)
    assert tm.get_value("Meas.L1") == 2.0
    assert pm.active is True  # still waiting on the 3rd step
    pm.stop()


def test_pause_prevents_advancement_and_resume_continues():
    bus, tm, am, training, cmd, audit, pm = _make_env()
    training.set_active(True)
    # A 3rd, far-future step keeps the scenario running after step 1
    # fires - see the identical note in
    # test_step_forward_executes_immediately_regardless_of_schedule().
    scenario = PresentationScenario(name="PauseTest", steps=[
        PresentationStep(time_s=0, type="tag", tag="Meas.L1", value=1.0),
        PresentationStep(time_s=0.1, type="tag", tag="Meas.L1", value=2.0),
        PresentationStep(time_s=999, type="tag", tag="Meas.L1", value=3.0),
    ])
    pm.start(scenario)
    time.sleep(0.02)
    pm.pause()
    assert pm.paused is True
    # Wait well past when step 1 would have fired if not paused.
    time.sleep(0.3)
    assert tm.get_value("Meas.L1") == 1.0, "a paused presentation must not advance on its own"

    pm.resume()
    time.sleep(0.3)
    assert tm.get_value("Meas.L1") == 2.0
    assert pm.active is True  # still waiting on the 3rd (never-firing-in-this-test) step
    pm.stop()


# --- DOWOD: stopping restores the pre-start state -------------------------

def test_stop_restores_tag_state_mid_scenario():
    bus, tm, am, training, cmd, audit, pm = _make_env()
    training.set_active(True)
    original = tm.get_value("Meas.L1")
    scenario = PresentationScenario(name="Restore", steps=[
        PresentationStep(time_s=100, type="tag", tag="Meas.L1", value=999.0),
        PresentationStep(time_s=200, type="tag", tag="Meas.L1", value=888.0),
    ])
    pm.start(scenario)
    pm.step_forward()  # only the first step - value now changed
    assert tm.get_value("Meas.L1") == 999.0

    pm.stop(actor="TestEngineer")
    assert tm.get_value("Meas.L1") == original
    assert pm.active is False


def test_stop_clears_alarms_the_scenario_itself_triggered():
    bus, tm, am, training, cmd, audit, pm = _make_env()
    training.set_active(True)
    # A 2nd, far-future step keeps the scenario running after the alarm
    # fires - otherwise the alarm step being the LAST one would
    # immediately finish (and restore/clear!) the scenario on its own,
    # making the mid-scenario "is the alarm active" check moot.
    scenario = PresentationScenario(name="AlarmRestore", steps=[
        PresentationStep(time_s=0, type="alarm", alarm_id="DEMO_TEST", message="msg", priority=3),
        PresentationStep(time_s=999, type="tag", tag="Meas.L1", value=1.0),
    ])
    pm.start(scenario)
    time.sleep(0.05)
    assert any(a.id == "DEMO_TEST" for a in am.get_active_alarms())
    assert pm.active is True  # still waiting on the 2nd step - not auto-finished

    pm.stop()
    assert not any(a.id == "DEMO_TEST" for a in am.get_active_alarms())


def test_natural_completion_also_restores_state():
    """A scenario whose OWN last step deliberately does NOT return to
    the original value - proves the restore-on-finish path genuinely
    runs, not that the scenario's own ending happened to already match."""
    bus, tm, am, training, cmd, audit, pm = _make_env()
    training.set_active(True)
    original = tm.get_value("Meas.L1")
    scenario = PresentationScenario(name="Finish", steps=[
        PresentationStep(time_s=0, type="tag", tag="Meas.L1", value=555.0, description="only step"),
    ])
    pm.start(scenario)
    deadline = time.time() + 5.0
    while pm.active and time.time() < deadline:
        time.sleep(0.02)

    assert pm.active is False
    assert tm.get_value("Meas.L1") == original, "finishing on its own must restore state too, not just an explicit stop()"


def test_command_step_does_not_bypass_rejection():
    """GRANICE: a scenario must not bypass permissions/interlocks - a
    command targeting something request_command_ex() itself rejects
    (BLOCKED) must stay rejected; the scenario continues to its next
    step instead of crashing or forcing the command through."""
    bus, tm, am, training, cmd, audit, pm = _make_env(with_command_target=False)  # DO02 unknown -> BLOCKED
    training.set_active(True)
    # A 3rd, far-future step keeps the scenario running after the tag
    # step - see the identical note on the other tests that add one.
    scenario = PresentationScenario(name="Blocked", steps=[
        PresentationStep(time_s=0, type="command", target="ADA01.DO.2", action="OPEN"),
        PresentationStep(time_s=100, type="tag", tag="Meas.L1", value=42.0),
        PresentationStep(time_s=999, type="tag", tag="Meas.L1", value=43.0),
    ])
    pm.start(scenario)
    time.sleep(0.05)  # let the t=0 command step auto-fire
    assert cmd.calls == [("ADA01.DO.2", "OPEN", "Engineer", "Presentation")]
    assert pm.active is True  # rejection did not crash/abort the scenario
    pm.step_forward()  # advance past the 100s wait to the tag step
    assert tm.get_value("Meas.L1") == 42.0  # scenario continued past the rejection
    assert pm.active is True  # still waiting on the 3rd step
    pm.stop()


def test_command_step_uses_the_real_command_manager_path():
    bus, tm, am, training, cmd, audit, pm = _make_env()
    training.set_active(True)
    scenario = PresentationScenario(name="Cmd", steps=[
        PresentationStep(time_s=0, type="command", target="ADA01.DO.2", action="CLOSE"),
    ])
    pm.start(scenario)
    pm.step_forward()
    assert cmd.calls == [("ADA01.DO.2", "CLOSE", "Engineer", "Presentation")]
    pm.stop()


# --- DOWOD/GRANICE: start/stop reach the audit log ------------------------

def test_start_and_stop_are_audited():
    bus, tm, am, training, cmd, audit, pm = _make_env()
    training.set_active(True)
    scenario = PresentationScenario(name="AuditMe", steps=[
        PresentationStep(time_s=100, type="tag", tag="Meas.L1", value=1.0),
    ])
    pm.start(scenario, actor="Engineer")
    pm.stop(actor="Engineer")

    event_types = [e[0] for e in audit.entries]
    assert "PRESENTATION_START" in event_types
    assert "PRESENTATION_STOP" in event_types
    for entry in audit.entries:
        if entry[0] in ("PRESENTATION_START", "PRESENTATION_STOP"):
            assert entry[3] is True  # success=True


def test_stop_when_nothing_running_is_a_harmless_noop():
    bus, tm, am, training, cmd, audit, pm = _make_env()
    pm.stop()  # never started
    assert pm.active is False
    assert audit.entries == []  # no spurious audit entry for a no-op


# ===========================================================================
# Task: cztery/piec nowych scenariuszy demonstracyjnych - real components
# (_FullEnv above), covering every DOWOD item for this task: each of the
# five shipped scenarios runs start to finish; none starts without Training
# Mode; stopping each restores initial state, including switching counters;
# scenario 2's fault latch does not self-clear.
# ===========================================================================

def test_all_five_scenarios_are_shipped_and_load_correctly():
    paths = list_scenarios()
    names = {os.path.basename(p) for p in paths}
    expected = {
        "voltage_sag_trip.json",
        "normal_operation_manual_control.json",
        "communication_loss_and_latch.json",
        "overload_ramp_trip.json",
        "command_not_confirmed.json",
        "mechanical_wear_and_service_history.json",
    }
    assert expected.issubset(names)

    known_types = {"tag", "command", "alarm", "alarm_clear", "device_comm", "counter_threshold"}
    for path in paths:
        if os.path.basename(path) not in expected:
            continue  # a locally-dropped-in scenario, not one this task ships
        scenario = load_scenario(path)
        assert scenario.steps, f"{path} has no steps"
        assert [s.time_s for s in scenario.steps] == sorted(s.time_s for s in scenario.steps)
        for step in scenario.steps:
            assert step.type in known_types

    jammed = load_scenario(os.path.join(DEFAULT_SCENARIOS_DIR, "command_not_confirmed.json"))
    assert "DEMO_JAMMED.CLOSE" in jammed.command_definitions


def test_none_of_the_five_scenarios_start_without_training_mode(tmp_path):
    env = _FullEnv(str(tmp_path))
    env.training.set_active(False)
    for path in list_scenarios():
        scenario = load_scenario(path)
        with pytest.raises(PresentationModeError):
            env.pm.start(scenario)
        assert env.pm.active is False


# --- scenario 1: normal operation and manual control ----------------------

def test_scenario1_shipped_file_runs_with_real_feedback_and_restores(tmp_path):
    # Task "migracja adresacji": normal_operation_manual_control.json's
    # own CLOSE command targets "ADA01.DO.1" - self-contained (own tag
    # is both the command output and its own feedback, see
    # epw_core.py's own default command definitions), not a separate
    # DI feedback tag the way the old flat DO01-04 special case used to
    # provide. The real feedback this test observes is therefore the DO
    # tag itself now.
    env = _FullEnv(str(tmp_path))
    # Task "migracja adresacji": "ADA01.DO.1" (unlike the old flat "DO01")
    # names a channel ON a DeviceManager-tracked device (ADA01) - a real,
    # intended consequence of card-based addressing (safety_kernel.py's
    # own comm-status gate now correctly applies to it, reading
    # Device.ADA01.Status directly, where the old flat name accidentally
    # bypassed that gate entirely - see safety_kernel.py's own comment on
    # standalone output channels). In a real app, EPWCore's own
    # device_status_changed -> Device.<id>.Status bridge (epw_core.py's
    # _on_device_status_changed()) keeps that tag current automatically;
    # this env is deliberately NOT a full EPWCore (see its own docstring)
    # and never wires that bridge, so the tag is set directly here,
    # exactly what the gate actually reads.
    env.tm.update_tag("Device.ADA01.Status", "ONLINE")
    path = os.path.join(DEFAULT_SCENARIOS_DIR, "normal_operation_manual_control.json")
    scenario = load_scenario(path)
    original_do1 = env.tm.get_value("ADA01.DO.1")

    env.pm.start(scenario)
    deadline = time.time() + 6.0
    while env.tm.get_value("ADA01.DO.1") == original_do1 and time.time() < deadline:
        time.sleep(0.02)
    assert env.tm.get_value("ADA01.DO.1") is True, "the CLOSE command's real feedback should confirm the state change"

    deadline = time.time() + 8.0
    while env.pm.active and time.time() < deadline:
        time.sleep(0.05)
    assert env.pm.active is False, "the scenario should finish on its own"
    assert env.tm.get_value("ADA01.DO.1") == original_do1, "finishing restores the pre-start state"


# --- scenario 2: communication loss and the fault latch --------------------

def test_scenario2_fault_latch_survives_recovery_and_stop_only_manual_ack_clears_it(tmp_path):
    env = _FullEnv(str(tmp_path))
    env.sim_driver.start()
    env.safety_kernel.start()
    try:
        # time_s=100/200, not 0 - a first step at time_s=0 auto-fires
        # essentially synchronously inside start() itself (a real
        # threading.Timer(0, ...) - see the identical, already-
        # established idiom on test_stop_restores_tag_state_mid_scenario()
        # above), which would make this test's own explicit
        # step_forward() calls land one step further ahead than
        # intended. Large, clearly-separated delays plus explicit
        # step_forward() calls keep this fully deterministic.
        scenario = PresentationScenario(name="Comm", steps=[
            PresentationStep(time_s=100, type="device_comm", target="Modbus", action="SUSPEND"),
            PresentationStep(time_s=200, type="device_comm", target="Modbus", action="RESUME"),
        ])
        env.pm.start(scenario)
        env.pm.step_forward()  # SUSPEND
        assert env.sim_driver.is_comm_suspended("Modbus") is True

        # Real detection: SafetyKernel checks health once a second and
        # needs 3 consecutive misses (missed_cycles_threshold=3) - give
        # it comfortably more than that in real elapsed time.
        deadline = time.time() + 6.0
        while env.tm.get_value("Safety.Modbus.Fault") is not True and time.time() < deadline:
            time.sleep(0.1)
        assert env.tm.get_value("Safety.Modbus.Healthy") is False
        assert env.tm.get_value("Safety.Modbus.Fault") is True
        assert any(a.id == "DEVICE_HEALTH_Modbus" for a in env.alarm_manager.get_active_alarms())

        env.pm.step_forward()  # RESUME
        assert env.sim_driver.is_comm_suspended("Modbus") is False
        deadline = time.time() + 3.0
        while env.tm.get_value("Safety.Modbus.Healthy") is not True and time.time() < deadline:
            time.sleep(0.1)
        assert env.tm.get_value("Safety.Modbus.Healthy") is True, "the underlying condition should clear once comm resumes"
        assert env.tm.get_value("Safety.Modbus.Fault") is True, "DOWOD: the latch must NOT self-clear"

        env.pm.stop()
        assert env.tm.get_value("Safety.Modbus.Fault") is True, "stopping the presentation must not silently un-latch a real fault"

        env.safety_kernel.on_alarm_acknowledged("DEVICE_HEALTH_Modbus", user="TestEngineer")
        assert env.tm.get_value("Safety.Modbus.Fault") is False, "only a real, manual acknowledgement clears it"
    finally:
        env.sim_driver.stop()
        env.safety_kernel.stop()


# --- scenario 3: overload and rising current --------------------------------

def test_scenario3_overcurrent_ramp_alarms_trips_and_restores(tmp_path):
    env = _FullEnv(str(tmp_path))
    original_i1 = env.tm.get_value("Meas.I1")
    scenario = PresentationScenario(name="Overload", steps=[
        PresentationStep(time_s=0, type="tag", tag="Meas.I1", value=15.0, quality="SIMULATED"),
        PresentationStep(time_s=0.05, type="tag", tag="Meas.I1", value=50.0, quality="SIMULATED"),
        PresentationStep(time_s=0.10, type="alarm", alarm_id="DEMO_I1_WARN", message="warn", priority=2, source_tag="Meas.I1"),
        PresentationStep(time_s=0.15, type="tag", tag="Meas.I1", value=61.0, quality="SIMULATED"),
        PresentationStep(time_s=0.20, type="alarm", alarm_id="DEMO_I1_TRIP", message="trip", priority=3, source_tag="Meas.I1"),
        PresentationStep(time_s=0.25, type="command", target="ADA01.DO.3", action="OPEN"),
        PresentationStep(time_s=0.30, type="tag", tag="Meas.I1", value=0.0, quality="SIMULATED"),
        PresentationStep(time_s=999, type="tag", tag="Meas.I1", value=0.0, quality="SIMULATED"),
    ])
    env.pm.start(scenario)
    deadline = time.time() + 3.0
    while env.pm.step_index < 7 and time.time() < deadline:
        time.sleep(0.02)

    assert env.tm.get_tag("Meas.I1").quality == TagQuality.SIMULATED, "GRANICE: must never look like a real measurement"
    assert any(a.id == "DEMO_I1_WARN" for a in env.alarm_manager.get_active_alarms())
    assert any(a.id == "DEMO_I1_TRIP" for a in env.alarm_manager.get_active_alarms())
    assert env.pm.active is True  # still waiting on the far-future step

    env.pm.stop()
    assert env.tm.get_value("Meas.I1") == original_i1
    assert not any(a.id == "DEMO_I1_WARN" for a in env.alarm_manager.get_active_alarms())
    assert not any(a.id == "DEMO_I1_TRIP" for a in env.alarm_manager.get_active_alarms())


# --- scenario 4: command sent, never confirmed ------------------------------

def test_scenario4_command_never_confirmed_times_out_and_restores(tmp_path):
    env = _FullEnv(str(tmp_path))
    scenario = PresentationScenario(
        name="Jammed",
        # time_s=100, not 0 - see the identical note in the scenario 2
        # test above. A 2nd, far-future step keeps the scenario "still
        # running" after the command fires - otherwise it being the
        # LAST (only) step would immediately finish (and restore!) the
        # scenario, making every assertion below observe already-
        # reverted state - the same "trailing far-future step" idiom
        # used throughout this file (see e.g.
        # test_step_forward_executes_immediately_regardless_of_schedule()).
        steps=[
            PresentationStep(time_s=100, type="command", target="DEMO_JAMMED", action="CLOSE"),
            PresentationStep(time_s=999, type="command", target="DEMO_JAMMED", action="CLOSE"),
        ],
        command_definitions={
            "DEMO_JAMMED.CLOSE": {
                "driver_id": "SIM_DRIVER", "output_tag": "Demo.JammedBreaker.CmdSent", "output_value": True,
                "feedback_tag": "Demo.JammedBreaker.Feedback", "feedback_value": True, "timeout_ms": 150,
            },
        },
    )
    statuses = []
    env.bus.subscribe("command_status", lambda cid, state, reason: statuses.append(state))

    env.pm.start(scenario)
    env.pm.step_forward()
    assert env.tm.get_value("Demo.JammedBreaker.CmdSent") is True, "the command's own output write still happens"
    assert env.tm.get_value("Demo.JammedBreaker.Feedback") is False, "but feedback never arrives"

    time.sleep(0.3)  # past the 150ms real supervision timeout
    assert "TIMEOUT" in statuses, "CommandManager's own real supervision timeout must genuinely fire"
    assert env.pm.active is True  # still waiting on the far-future 2nd step

    env.pm.stop()
    assert env.tm.get_value("Demo.JammedBreaker.CmdSent") is False, "the scratch output tag is restored like any other"


# --- scenario 5: mechanical wear and switching counters ---------------------

def test_scenario5_counters_and_threshold_restore_after_stop(tmp_path):
    env = _FullEnv(str(tmp_path))
    # Task "migracja adresacji": this scenario used to drive the DI
    # counter via DO commands (the old flat DO01-04 special case wrote
    # straight to a separate DI feedback tag) - no longer possible now
    # that every DO channel is self-contained (see _FullEnv's own defs
    # comment). Drives "ELA01.DI.1" directly via "tag" steps instead -
    # the presentation_scenarios/mechanical_wear_and_service_history.json
    # shipped fixture was fixed the identical way, for the identical
    # reason.
    #
    # SwitchingCounterManager never counts a tag's FIRST-ever observed
    # transition (see its own _on_tag_changed() docstring: nothing to
    # call it a transition FROM yet) - a real installation always has
    # this history already; a brand-new scratch environment doesn't, so
    # seed it with one warm-up cycle first, exactly like a real device
    # would already have before any demo ever runs. Ends back at DI1's
    # natural default (open/False), so this doesn't shift the baseline
    # `original` captures below.
    env.tm.update_tag("ELA01.DI.1", True)
    env.tm.update_tag("ELA01.DI.1", False)

    original = env.switching_counters.get_snapshot("ELA01.DI.1")
    scenario = PresentationScenario(name="Wear", steps=[
        PresentationStep(time_s=0, type="counter_threshold", target="ELA01.DI.1", value=3),
        PresentationStep(time_s=0.05, type="tag", tag="ELA01.DI.1", value=True, quality="GOOD"),
        PresentationStep(time_s=0.10, type="tag", tag="ELA01.DI.1", value=False, quality="GOOD"),
        PresentationStep(time_s=0.15, type="tag", tag="ELA01.DI.1", value=True, quality="GOOD"),
        PresentationStep(time_s=0.20, type="tag", tag="ELA01.DI.1", value=False, quality="GOOD"),
        PresentationStep(time_s=0.25, type="tag", tag="ELA01.DI.1", value=True, quality="GOOD"),
        PresentationStep(time_s=999, type="tag", tag="ELA01.DI.1", value=False, quality="GOOD"),
    ])
    env.pm.start(scenario)
    deadline = time.time() + 3.0
    while env.pm.step_index < 6 and time.time() < deadline:
        time.sleep(0.02)

    during = env.switching_counters.get_snapshot("ELA01.DI.1")
    assert during["closes"] == 3
    assert env.switching_counters.is_over_threshold("ELA01.DI.1") is True
    assert env.pm.active is True  # still waiting on the far-future step

    env.pm.stop()
    restored = env.switching_counters.get_snapshot("ELA01.DI.1")
    assert restored["closes"] == original["closes"]
    assert restored["opens"] == original["opens"]
    assert restored["warning_threshold"] == original["warning_threshold"]
    assert env.switching_counters.is_over_threshold("ELA01.DI.1") is False
