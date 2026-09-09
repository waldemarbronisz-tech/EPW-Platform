import pytest
from epw_os.core.epw_core import EPWCore
from epw_os.core.tag_manager import TagType, TagQuality, TagManager
from epw_os.core.alarm_manager import AlarmState
from epw_os.core.events import EventBus

# Task (refactor/test-db-fixture): the `db` fixture (epw_os/tests/conftest.py)
# is requested individually per test below, not file-wide - EPWCore().startup()
# genuinely touches the database (runs its own real migration as part of
# normal production startup, see epw_os/core/epw_core.py), but several
# tests in this file construct EPWCore() and never call .startup(), so
# they never touch it - those are left without `db` on purpose.

def test_headless_boot(db):
    core = EPWCore()
    core.startup()
    assert core.is_running is True
    assert "DATABASE" in core.health_manager.get_health()
    core.shutdown()
    assert core.is_running is False


# --- Task (device-communication-status gate): DOWOD - "program startuje
# i dziala normalnie, zadna dotychczas dzialajaca funkcja nie zostala
# zablokowana" - one explicit, end-to-end anchor test covering both
# halves: a command whose target was never checked against a device's
# communication status before this fix (an untracked standalone output
# channel) and one that was (a default device, once actually online). --

def test_normal_startup_does_not_block_any_existing_command_path(db):
    core = EPWCore()
    core.startup()

    class AllowAllLogicRuntime:
        ready = True
        is_running = True
        def validate_command(self, target, action):
            return True, []
        def scan(self): pass
        def load_program(self, filepath): return True
    core.logic_engine = AllowAllLogicRuntime()
    core.command_manager.logic_engine = core.logic_engine

    # A standalone output channel (DO01-64) has no DeviceManager-tracked
    # device of its own behind it (see safety_kernel.py's own comment on
    # validate_command_safety()) - never checked against a communication
    # status before this fix, and still isn't. Zero setup needed.
    permitted, reasons = core.command_manager.request_command("DO10", "CLOSE", validate_only=True)
    assert permitted is True, reasons

    # A real, DeviceManager-tracked device (one of the four hardcoded
    # defaults) - WAS already checked before this fix, and still passes
    # once it's actually known to be online (the normal, steady-state
    # case a real running system reaches within about one poll cycle of
    # startup - see SimulatorDriver._run_loop()).
    core.device_manager.update_comm("ADA01")
    permitted, reasons = core.command_manager.request_command("ADA01.DO01", "CLOSE", validate_only=True)
    assert permitted is True, reasons

    core.shutdown()
    assert core.is_running is False

def test_tag_manager_typing():
    core = EPWCore()
    core.tag_manager.add_tag("Test.Tag1", 0, TagType.INT)
    assert core.tag_manager.get_value("Test.Tag1") == 0
    core.tag_manager.update_tag("Test.Tag1", "42")
    assert core.tag_manager.get_value("Test.Tag1") == 42
    assert core.tag_manager.get_tag("Test.Tag1").quality == TagQuality.GOOD


# --- Bug fix (Task: "System.Mode nie jest zarejestrowany") --------------
# DOWOD: set_mode() actually changes the System.Mode tag with no
# exception, and reading it works immediately after start, before any
# mode change - see tag_manager.py's own comment on why this is
# registered in __init__(), not init_default_tags()/configure() (both
# of which run CONDITIONALLY - see EPWCore.startup() - so registering it
# in either one only would have reproduced the exact same "sometimes
# missing" bug class this task exists to fix).

def test_system_mode_tag_readable_immediately_after_construction():
    """Before the very first mode change - proves this isn't just
    "registered lazily on first set_mode() call"."""
    tm = TagManager(EventBus())
    assert tm.get_tag("System.Mode") is not None
    assert tm.get_value("System.Mode") == "SIMULATION MODE" == tm.mode


def test_set_mode_updates_the_tag_without_raising():
    tm = TagManager(EventBus())
    tm.set_mode("LIVE MODE")  # must not raise - this is the bug itself
    assert tm.get_value("System.Mode") == "LIVE MODE"
    assert tm.mode == "LIVE MODE"
    tm.set_mode("SIMULATION MODE")
    assert tm.get_value("System.Mode") == "SIMULATION MODE"


def test_set_mode_emits_a_real_tag_changed_event():
    """Before the fix, update_tag("System.Mode", ...) raised BEFORE ever
    reaching event_bus.emit("tag_changed", ...) - so no subscriber
    (GUI, MQTT, REST API) ever received this event for this tag, in the
    program's entire history. Verified directly against the event bus,
    not just the tag's own stored value."""
    tm = TagManager(EventBus())
    received = []
    tm.event_bus.subscribe("tag_changed", lambda n, v, q: received.append((n, v, q)))
    tm.set_mode("LIVE MODE")
    assert ("System.Mode", "LIVE MODE", "GOOD") in received


def test_system_mode_registered_via_epw_core_startup_too(db):
    """End-to-end through the real composition root, not just a bare
    TagManager - toggle_mode()'s own event_bus round trip
    (mode_change_request -> EPWCore._handle_mode_request -> set_mode())
    must also work without the exception this bug used to raise (and
    EventBus.emit() used to silently swallow)."""
    core = EPWCore()
    core.startup()
    assert core.tag_manager.get_value("System.Mode") == "SIMULATION MODE"
    core.tag_manager.toggle_mode()  # emits mode_change_request, handled synchronously
    assert core.tag_manager.get_value("System.Mode") == "LIVE MODE"
    core.shutdown()


# --- Tag.read_only removed (Task: "martwe pole") -------------------------

def test_tag_dataclass_has_no_read_only_field():
    from epw_os.core.tag_manager import Tag
    import dataclasses
    field_names = {f.name for f in dataclasses.fields(Tag)}
    assert "read_only" not in field_names


def test_add_tag_no_longer_accepts_a_read_only_argument():
    core = EPWCore()
    with pytest.raises(TypeError):
        core.tag_manager.add_tag("Test.ReadOnlyGone", 0, TagType.INT, read_only=True)

def test_event_bus():
    core = EPWCore()
    flag = []
    def on_event(tag, val, qual):
        flag.append((tag, val))
    core.event_bus.subscribe("tag_changed", on_event)
    core.tag_manager.add_tag("Evt.Tag", False, TagType.BOOL)
    core.tag_manager.update_tag("Evt.Tag", True)
    assert len(flag) > 0
    assert flag[0] == ("Evt.Tag", True)

def test_alarm_lifecycle():
    core = EPWCore()
    core.alarm_manager.trigger_alarm("ALM1", "Test Alarm")
    alarms = core.alarm_manager.get_active_alarms()
    assert len(alarms) == 1
    assert alarms[0].state == AlarmState.ACTIVE_UNACK
    core.alarm_manager.acknowledge_alarm("ALM1")
    assert core.alarm_manager.get_active_alarms()[0].state == AlarmState.ACTIVE_ACK
    core.alarm_manager.clear_alarm("ALM1")
    assert len(core.alarm_manager.get_active_alarms()) == 0

def test_driver_manager_lifecycle(db):
    core = EPWCore()
    core.startup()
    assert core.driver_manager.is_running is True
    driver = core.driver_manager.get_driver("SIM_DRIVER")
    assert driver is not None
    assert driver.is_running is True
    core.shutdown()
    assert driver.is_running is False

def test_watchdog_and_health(db):
    core = EPWCore()
    core.startup()
    core.device_manager.register_device("ELA01", "SIM_DRIVER", timeout=0.1)
    core.device_manager.update_comm("ELA01")
    assert core.device_manager.devices["ELA01"]["status"] == "ONLINE"
    import time
    time.sleep(0.2)
    core.device_manager.check_watchdogs()
    assert core.device_manager.devices["ELA01"]["status"] == "COMM_FAILURE"
    assert core.health_manager.get_health()["DRIVERS"] == "DEGRADED"
    core.shutdown()

def test_canonical_tags(db):
    core = EPWCore()
    core.tag_manager.configure([
        {"id": "ELA01", "type": "ELA"},
        {"id": "ADA01", "type": "ADA"},
        {"id": "EPM01", "type": "EPM"}
    ])
    core.startup()
    assert core.tag_manager.get_value("ELA01.DI01") is False
    assert core.tag_manager.get_value("ADA01.DO01") is False
    assert core.tag_manager.get_value("EPM01.UL1.RMS") == 0.0
    core.shutdown()

def test_logic_engine_fail_safe(db):
    # Bug 2 fix: the default project (logic_project == null - nothing
    # ever handed to load_program()) is a normal, expected state, not a
    # fault - manual commands must be PERMITTED here. This assertion used
    # to be the opposite (permitted is False) - that was the reported
    # bug: "no logic project configured" and "a project was configured
    # but failed to load" both left LogicEngine._project as None and were
    # therefore indistinguishable, so this normal case was fail-safe
    # blocked exactly like a real fault. See SESSION_REPORT.md.
    core = EPWCore()
    core.startup()
    # Task (device-communication-status gate): ADA01 is a real,
    # DeviceManager-tracked device (one of the four hardcoded defaults),
    # and validate_command_safety() now requires it to be affirmatively
    # ONLINE before permitting a command - true almost immediately after
    # a real startup() (SimulatorDriver's background thread reports its
    # first heartbeat within ~1 poll cycle), but NOT deterministically at
    # this exact line (a race against that background thread). Advancing
    # comm directly, synchronously, is the same deterministic pattern
    # test_safety_kernel.py's own _advance_comm() already uses - this
    # test is about the LOGIC engine gate, not device communication, so
    # isolate it from that unrelated race.
    core.device_manager.update_comm("ADA01")
    assert core.logic_engine.is_configured() is False
    permitted, reasons = core.command_manager.request_command("ADA01.DO01", "CLOSE", validate_only=True)
    assert permitted is True
    assert reasons == []
    core.shutdown()

def test_logic_engine_fail_safe_when_configured_but_not_loaded(db):
    # The other half of Bug 2's required distinction: a project WAS
    # configured (load_program() was actually called) but never loaded
    # successfully - this IS a genuine fault and must stay blocked,
    # unchanged from before this task.
    core = EPWCore()
    core.startup()
    # Task (device-communication-status gate) - see
    # test_logic_engine_fail_safe()'s own comment just above: ADA01 must
    # be deterministically ONLINE so the block asserted below is
    # provably the LOGIC engine's own (the thing this test is actually
    # about), not an unrelated race against the device-status gate.
    core.device_manager.update_comm("ADA01")
    ok = core.logic_engine.load_program("nonexistent_logic_project_for_test.json")
    assert ok is False
    assert core.logic_engine.is_configured() is True
    permitted, reasons = core.command_manager.request_command("ADA01.DO01", "CLOSE", validate_only=True)
    assert permitted is False
    assert "Logic Runtime Unavailable" in reasons[0]
    core.shutdown()

def test_logic_engine_allow_all_stub_still_works(db):
    core = EPWCore()
    core.startup()

    class AllowAllLogicRuntime:
        ready = True
        is_running = True
        def validate_command(self, target, action):
            return True, []
        def scan(self): pass
        def load_program(self, filepath): return True
    core.logic_engine = AllowAllLogicRuntime()
    core.command_manager.logic_engine = core.logic_engine

    # Task (device-communication-status gate) - same reasoning as
    # test_logic_engine_fail_safe() above.
    core.device_manager.update_comm("ADA01")
    permitted, reasons = core.command_manager.request_command("ADA01.DO01", "CLOSE", validate_only=True)
    assert permitted is True
    core.shutdown()

def test_safety_kernel(db):
    core = EPWCore()
    core.startup()
    class AllowAllLogicRuntime:
        ready = True
        is_running = True
        def validate_command(self, target, action):
            return True, []
        def scan(self): pass
        def load_program(self, filepath): return True
    core.logic_engine = AllowAllLogicRuntime()
    core.command_manager.logic_engine = core.logic_engine
    # Task (device-communication-status gate): the "permitted is True"
    # assertion just below the EMERGENCY_STOP checks now also depends on
    # ADA01 being deterministically ONLINE (the same race - see
    # test_logic_engine_fail_safe()'s own comment - the explicit
    # add_tag(..., "ONLINE", ...) a few lines down was already here for
    # the COMM_FAILURE transition that follows it, but ran too late to
    # cover the "permitted is True" check before it).
    core.device_manager.update_comm("ADA01")
    core.tag_manager.update_tag("EMERGENCY_STOP", True)
    permitted, reasons = core.command_manager.request_command("ADA01.DO01", "CLOSE")
    assert permitted is False
    assert "Emergency Stop" in reasons[0]
    core.tag_manager.update_tag("EMERGENCY_STOP", False)
    permitted, reasons = core.command_manager.request_command("ADA01.DO01", "CLOSE")
    assert permitted is True
    core.tag_manager.add_tag("Device.ADA01.Status", "ONLINE", TagType.STRING)
    core.tag_manager.update_tag("Device.ADA01.Status", "COMM_FAILURE")
    permitted, reasons = core.command_manager.request_command("ADA01.DO01", "CLOSE")
    assert permitted is False
    assert "COMM_FAILURE" in reasons[0]
    core.shutdown()

def test_project_activation():
    core = EPWCore()
    import json
    with open("bad_project.json", "w") as f:
        json.dump({"format": "INVALID_FORMAT"}, f)
    core.project_manager.project_file = "bad_project.json"
    success = core.project_manager.load_project()
    assert success is False
    assert core.project_manager.config == {}
    with open("good_project.json", "w") as f:
        json.dump({"format": "EPW_OS_PROJECT", "schema_version": 1, "project_id": "TEST_PRJ_1"}, f)
    core.project_manager.project_file = "good_project.json"
    success = core.project_manager.load_project()
    assert success is True
    assert core.project_manager.config["project_id"] == "TEST_PRJ_1"
    import os
    os.remove("bad_project.json")
    os.remove("good_project.json")

def test_mode_service(db):
    core = EPWCore()
    core.startup()
    assert core.tag_manager.mode == "SIMULATION MODE"
    core.event_bus.emit("mode_change_request", "LIVE MODE")
    assert core.tag_manager.mode == "LIVE MODE"
    core.shutdown()

def test_command_chain(db):
    core = EPWCore()
    core.startup()
    
    class AllowAllLogicRuntime:
        ready = True
        is_running = True
        def validate_command(self, target, action):
            return True, []
        def scan(self): pass
        def load_program(self, filepath): return True
    core.logic_engine = AllowAllLogicRuntime()
    core.command_manager.logic_engine = core.logic_engine
    # Task (device-communication-status gate) - same reasoning as
    # test_logic_engine_fail_safe() above: this test's own target
    # ("ADA01") is a real, DeviceManager-tracked device.
    core.device_manager.update_comm("ADA01")
    core.command_manager.load_definitions({
        "ADA01.CLOSE": {
            "driver_id": "SIM_DRIVER",
            "output_tag": "ADA01.DO01",
            "output_value": True,
            "timeout_ms": 1500
        }
    })
    
    status_log = []
    def on_status(cmd_id, state, msg):
        status_log.append(state)
        
    core.event_bus.subscribe("command_status", on_status)
    
    rec = core.command_manager.request_command_ex("ADA01", "CLOSE")
    permitted = rec.state not in ["FAILED", "BLOCKED"]
    
    assert "REQUESTED" in status_log
    assert "VALIDATED" in status_log
    assert "DISPATCHED" in status_log or "SUCCESS" in status_log
    core.shutdown()

def test_driver_chain(db):
    core = EPWCore()
    core.startup()
    
    import time
    core.event_bus.emit("driver_update", "Sim.Voltage", 235.0, "GOOD")
    time.sleep(0.1)
    
    val = core.tag_manager.get_value("Sim.Voltage")
    assert val == 235.0
    core.shutdown()

def test_fat_command_action_mapping(db):
    core = EPWCore()
    core.startup()
    class AllowAllLogicRuntime:
        ready = True
        is_running = True
        def validate_command(self, target, action):
            return True, []
        def scan(self): pass
        def load_program(self, filepath): return True
    core.logic_engine = AllowAllLogicRuntime()
    core.command_manager.logic_engine = core.logic_engine
    
    # Load configuration
    core.command_manager.load_definitions({
        "TEST_DEVICE.CLOSE": {
            "driver_id": "SIM_DRIVER",
            "output_tag": "ADA01.DO01",
            "output_value": True,
            "feedback_tag": "ELA01.DI03",
            "feedback_value": True,
            "timeout_ms": 1500
        }
    })
    
    # Capture state
    states = []
    def on_status(cid, st, msg):
        states.append(st)
        if st == "FEEDBACK_PENDING":
            # Test hooks feedback bypass in plant
            core.event_bus.emit("tag_changed", "ELA01.DI03", True, "GOOD")
            
    core.event_bus.subscribe("command_status", on_status)
    
    # We hook a naive feedback processor for the test
    def process_feedback(name, val, qual):
        if name == "ELA01.DI03" and val == True:
            for cid, rec in core.command_manager._pending_commands.items():
                if rec.definition.feedback_tag == name:
                    core.event_bus.emit("command_status", cid, "SUCCESS", "Feedback received")
                    
    core.event_bus.subscribe("tag_changed", process_feedback)
    
    rec = core.command_manager.request_command_ex("TEST_DEVICE", "CLOSE")
    
    # The SimulatedPlant will trigger the output delay and emit driver_update -> TagManager which hits our feedback check
    import time
    time.sleep(0.2) 
    
    assert "REQUESTED" in states
    assert "VALIDATED" in states
    assert "FEEDBACK_PENDING" in states or "SUCCESS" in states
    assert "SUCCESS" in states
    
    core.shutdown()

def test_driver_single_start(db):
    from epw_os.drivers.simulator_driver import SimulatorDriver
    class CountingSimulatorDriver(SimulatorDriver):
        def __init__(self, event_bus):
            super().__init__(event_bus)
            self.start_count = 0
            self.stop_count = 0

        def start(self):
            self.start_count += 1
            super().start()

        def stop(self):
            self.stop_count += 1
            super().stop()
            
    core = EPWCore()
    counting_driver = CountingSimulatorDriver(core.event_bus)
    core.sim_driver = counting_driver
    core.driver_manager.drivers["SIM_DRIVER"] = counting_driver
    
    core.startup()
    assert counting_driver.start_count == 1
    
    core.shutdown()
    assert counting_driver.stop_count == 1

@pytest.mark.slow
@pytest.mark.gui
def test_synoptic_loader():
    # Task (refactor/test-suite-split): the one test in this otherwise
    # headless file that needs a real QApplication (SynopticRuntimeAdapter
    # constructs real Qt graphics items) - marked so `pytest epw_os/tests/
    # -m "not slow"` can skip just this one, not the whole file.
    import sys
    from PySide6.QtWidgets import QApplication
    if not QApplication.instance():
        app = QApplication(sys.argv)
    from epw_os.gui.widgets.synoptic_runtime import SynopticRuntimeAdapter
    adapter = SynopticRuntimeAdapter()
    
    import json
    with open("test_synoptic.epwsyn", "w") as f:
        json.dump({
            "format": "EPW_SYNOPTIC",
            "schema_version": 1,
            "objects": [
                {
                    "id": "lamp1",
                    "type": "indicator",
                    "bindings": {
                        "value": "ELA01.DI01",
                        "command": "ADA01.CLOSE"
                    }
                }
            ]
        }, f)
        
    assert adapter.load_synoptic_definition("test_synoptic.epwsyn") is True
    assert adapter.ready is True
    assert len(adapter.objects) == 1
    
    import os
    os.remove("test_synoptic.epwsyn")

def test_true_timeout_fat(db):
    core = EPWCore()
    core.startup()
    class AllowAllLogicRuntime:
        ready = True
        is_running = True
        def validate_command(self, target, action):
            return True, []
        def scan(self): pass
        def load_program(self, filepath): return True
    core.logic_engine = AllowAllLogicRuntime()
    core.command_manager.logic_engine = core.logic_engine
    
    # Load configuration with 100ms timeout
    core.command_manager.load_definitions({
        "TEST_DEVICE.CLOSE": {
            "driver_id": "SIM_DRIVER",
            "output_tag": "ADA01.DO01",
            "output_value": True,
            "feedback_tag": "ELA01.DI03",
            "feedback_value": True,
            "timeout_ms": 50
        }
    })
    
    states = []
    def on_status(cid, st, msg):
        states.append(st)
            
    core.event_bus.subscribe("command_status", on_status)
    
    # Intentionally disable plant simulation hook to force a timeout
    core.simulated_plant.mappings = {}
    
    rec = core.command_manager.request_command_ex("TEST_DEVICE", "CLOSE")
    
    import time
    time.sleep(0.1) # Wait beyond 50ms timeout
    
    assert "REQUESTED" in states
    assert "VALIDATED" in states
    assert "DISPATCHED" in states
    assert "FEEDBACK_PENDING" in states or "TIMEOUT" in states
    assert "TIMEOUT" in states
    assert rec.id not in core.command_manager._pending_commands
    
    core.shutdown()
