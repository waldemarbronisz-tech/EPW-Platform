"""Tests for Training Mode (Task: tryb, w ktorym caly interfejs dziala
normalnie, ale zaden rozkaz nie wychodzi na sprzet).

Three layers, tested separately:
1. epw_os/core/training_mode.py's TrainingModeManager - headless, no Qt,
   no driver/CommandManager involvement at all (just the on/off flag and
   the audit trail).
2. epw_os/core/driver_manager.py's route_command() - the actual cutoff
   point at the driver layer's own boundary.
3. Full end-to-end through a real EPWCore (TagManager, AccessManager's
   own level gate is exercised at the GUI layer, not here - CommandManager,
   SafetyKernel, LogicEngine, DriverManager all real) - proving the
   command still travels the entire normal decision path, is still
   recorded via the normal command_status/event pipeline, and simply
   never reaches a driver.

Layer 3 tests take `db` (epw_os/tests/conftest.py) - they build a real
EPWCore via _make_core_with_allow_all_logic() below, whose .startup()
genuinely touches the database (Task: refactor/test-db-fixture). Layers
1-2 never construct an EPWCore at all, so they're left without `db`.
"""
import pytest

from epw_os.core.events import EventBus
from epw_os.core.training_mode import TrainingModeManager
from epw_os.core.driver_manager import DriverManager
from epw_os.core.epw_core import EPWCore
from epw_os.core.tag_manager import TagType


class FakeAuditLogger:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))


class FakeDriver:
    """Minimal BaseDriver stand-in - just enough for route_command() to
    have something to (not) call."""
    def __init__(self, running=True):
        self.is_running = running
        self.write_calls = []

    def write_tag(self, tag_name, value):
        self.write_calls.append((tag_name, value))
        return True


# --- Layer 1: TrainingModeManager itself --------------------------------

def test_starts_inactive():
    mgr = TrainingModeManager(EventBus(), FakeAuditLogger())
    assert mgr.active is False


def test_enable_sets_active_and_records_audit():
    audit = FakeAuditLogger()
    mgr = TrainingModeManager(EventBus(), audit)
    changed = mgr.set_active(True, actor="Engineer")
    assert changed is True
    assert mgr.active is True
    assert len(audit.entries) == 1
    event_type, actor, detail, success = audit.entries[0]
    assert event_type == "TRAINING_MODE_ON"
    assert actor == "Engineer"
    assert success is True


def test_disable_sets_inactive_and_records_audit():
    audit = FakeAuditLogger()
    mgr = TrainingModeManager(EventBus(), audit)
    mgr.set_active(True, actor="Engineer")
    changed = mgr.set_active(False, actor="Engineer")
    assert changed is True
    assert mgr.active is False
    assert audit.entries[-1][0] == "TRAINING_MODE_OFF"


def test_enabling_twice_does_not_double_record():
    audit = FakeAuditLogger()
    mgr = TrainingModeManager(EventBus(), audit)
    assert mgr.set_active(True, actor="Engineer") is True
    assert mgr.set_active(True, actor="Engineer") is False
    assert len(audit.entries) == 1


def test_disabling_when_already_inactive_does_not_record():
    audit = FakeAuditLogger()
    mgr = TrainingModeManager(EventBus(), audit)
    assert mgr.set_active(False, actor="Engineer") is False
    assert audit.entries == []


def test_event_bus_emits_training_mode_changed():
    bus = EventBus()
    seen = []
    bus.subscribe("training_mode_changed", lambda active: seen.append(active))
    mgr = TrainingModeManager(bus, FakeAuditLogger())
    mgr.set_active(True)
    mgr.set_active(False)
    assert seen == [True, False]


def test_no_audit_logger_does_not_crash():
    mgr = TrainingModeManager(EventBus(), audit_logger=None)
    mgr.set_active(True)  # must not raise
    assert mgr.active is True


def test_no_event_bus_does_not_crash():
    mgr = TrainingModeManager(event_bus=None, audit_logger=FakeAuditLogger())
    mgr.set_active(True)  # must not raise
    assert mgr.active is True


def test_never_persisted_no_project_manager_hook_at_all():
    """Task: "Tryb NIE jest zapamietywany miedzy uruchomieniami" - the
    constructor takes no project_manager at all, so there is no
    persisted-data path that could bring it back."""
    import inspect
    params = inspect.signature(TrainingModeManager.__init__).parameters
    assert "project_manager" not in params


# --- Layer 2: DriverManager.route_command() cutoff ----------------------

def test_route_command_reaches_the_real_driver_when_inactive():
    bus = EventBus()
    dm = DriverManager(bus)  # training_mode=None -> unaffected, exactly as before this feature
    driver = FakeDriver()
    dm.register_driver("SIM_DRIVER", driver)
    ok = dm.route_command("SIM_DRIVER", "DO01", True)
    assert ok is True
    assert driver.write_calls == [("DO01", True)]


def test_route_command_never_touches_the_driver_when_training_mode_active():
    bus = EventBus()
    training_mode = TrainingModeManager(bus)
    dm = DriverManager(bus, training_mode=training_mode)
    driver = FakeDriver()
    dm.register_driver("SIM_DRIVER", driver)

    training_mode.set_active(True)
    ok = dm.route_command("SIM_DRIVER", "DO01", True)

    assert ok is True, "the caller must see the same success it would see from a real dispatch"
    assert driver.write_calls == [], "the command must never reach the driver instance at all"


def test_route_command_simulates_feedback_via_driver_update_event():
    """Task: "sprzezenie zwrotne symulowane, zeby interfejs zachowywal sie
    realistycznie" - even with no real driver touched, the normal
    driver_update -> driver_to_tag pipeline still fires."""
    bus = EventBus()
    training_mode = TrainingModeManager(bus)
    training_mode.set_active(True)
    dm = DriverManager(bus, training_mode=training_mode)

    seen = []
    bus.subscribe("driver_to_tag", lambda tag, val, q: seen.append((tag, val, q)))

    dm.route_command("SIM_DRIVER", "DI1", True)
    assert seen == [("DI1", True, "GOOD")]


def test_route_command_works_even_with_no_driver_registered_at_all_when_training_mode_active():
    """The whole point is independence from whatever driver is (or isn't)
    configured - this must succeed even for a driver_id nothing ever
    registered."""
    bus = EventBus()
    training_mode = TrainingModeManager(bus)
    training_mode.set_active(True)
    dm = DriverManager(bus, training_mode=training_mode)
    assert dm.route_command("SOME_UNCONFIGURED_DRIVER", "DO99", True) is True


def test_route_command_reverts_to_normal_once_training_mode_disabled():
    bus = EventBus()
    training_mode = TrainingModeManager(bus)
    dm = DriverManager(bus, training_mode=training_mode)
    driver = FakeDriver()
    dm.register_driver("SIM_DRIVER", driver)

    training_mode.set_active(True)
    dm.route_command("SIM_DRIVER", "DO01", True)
    assert driver.write_calls == []

    training_mode.set_active(False)
    dm.route_command("SIM_DRIVER", "DO01", True)
    assert driver.write_calls == [("DO01", True)]


def test_route_command_still_fails_normally_for_a_dead_driver_when_inactive():
    """Unaffected pre-existing behavior - GRANICE requires the normal path
    stay identical."""
    bus = EventBus()
    dm = DriverManager(bus)
    driver = FakeDriver(running=False)
    dm.register_driver("SIM_DRIVER", driver)
    assert dm.route_command("SIM_DRIVER", "DO01", True) is False


# --- Layer 3: end-to-end through a real EPWCore -------------------------

class _AllowAllLogicRuntime:
    ready = True
    is_running = True
    def validate_command(self, target, action):
        return True, []
    def scan(self): pass
    def load_program(self, filepath): return True


def _make_core_with_allow_all_logic():
    core = EPWCore()
    core.startup()
    core.logic_engine = _AllowAllLogicRuntime()
    core.command_manager.logic_engine = core.logic_engine
    return core


def test_command_passes_through_command_manager_but_never_reaches_the_driver(db):
    """DOWOD: "w trybie cwiczebnym komenda przechodzi przez CommandManager,
    jest zapisywana, ale nie dociera do sterownika"."""
    core = _make_core_with_allow_all_logic()
    core.command_manager.load_definitions({
        "TEST_DEVICE.CLOSE": {
            "driver_id": "SIM_DRIVER", "output_tag": "ADA01.DO01", "output_value": True,
            "timeout_ms": 1500,
        }
    })

    # Spy on the real SimulatorDriver instance's write_tag - it must never
    # be called while Training Mode is active.
    write_calls = []
    real_write_tag = core.sim_driver.write_tag
    def spying_write_tag(tag_name, value):
        write_calls.append((tag_name, value))
        return real_write_tag(tag_name, value)
    core.sim_driver.write_tag = spying_write_tag

    core.training_mode.set_active(True, actor="Engineer")

    status_log = []
    core.event_bus.subscribe("command_status", lambda cid, state, msg: status_log.append(state))

    rec = core.command_manager.request_command_ex("TEST_DEVICE", "CLOSE")

    # It's "recorded" - travelled the normal, visible pipeline exactly as
    # it would with Training Mode off.
    assert "REQUESTED" in status_log
    assert "VALIDATED" in status_log
    assert "DISPATCHED" in status_log or "SUCCESS" in status_log
    assert rec.state not in ("BLOCKED", "FAILED")

    # ...but it never reached the driver.
    assert write_calls == [], f"command reached the real driver while Training Mode was active: {write_calls}"

    core.shutdown()


def test_feedback_is_simulated_realistically_in_training_mode(db):
    """Task 3: the device still "changes state" on screen - the output
    tag itself updates through the exact same driver_update ->
    driver_to_tag bridge a real driver write would use, even though no
    real driver was ever touched."""
    core = _make_core_with_allow_all_logic()
    core.command_manager.load_definitions({
        "TEST_DEVICE.CLOSE": {
            "driver_id": "SIM_DRIVER", "output_tag": "DO50", "output_value": True,
            "timeout_ms": 1500,
        }
    })
    core.tag_manager.add_tag("DO50", False, TagType.BOOL)

    core.training_mode.set_active(True, actor="Engineer")

    status_log = []
    core.event_bus.subscribe("command_status", lambda cid, state, msg: status_log.append(state))

    core.command_manager.request_command_ex("TEST_DEVICE", "CLOSE")

    assert "SUCCESS" in status_log
    assert core.tag_manager.get_value("DO50") is True, "the tag must visibly change state on screen"

    core.shutdown()


def test_self_referential_command_reaches_the_same_command_manager_state_either_way(db):
    """Parity check (GRANICE: "sciezka decyzyjna ma byc identyczna jak w
    trybie normalnym"): every default DO command definition configure()
    produces is self-referential (output_tag == feedback_tag - see
    epw_core.py's startup(), task "migracja adresacji" - the old flat
    scheme's own DO01-04/DO05-64 split is gone, but DO05-64's already-
    self-contained pattern is now the ONLY pattern, for every real DO
    channel), so both a same-process SimulatorDriver.write_tag() and
    Training Mode's own driver-boundary cutoff (driver_manager.py)
    resolve a command's feedback SYNCHRONOUSLY, inside route_command()
    itself, either way - command_manager.py's request_command_ex() now
    registers the command as pending BEFORE calling route_command()
    specifically so that synchronous, same-call-stack feedback is never
    missed (a real bug this task's own Presentation Mode scenarios
    found: it used to always land at FEEDBACK_PENDING, resolving only
    via an unnecessary timeout, never via genuine feedback - see
    command_manager.py's own comment on this for the full story). Only
    the immediate states (checked right after request_command_ex()
    returns, before the 1500ms timeout timer could ever matter) are
    compared here - a real wall-clock timeout is a separate, unrelated
    concern from what this test is about."""
    def run(training_active):
        import dataclasses
        import json
        import os
        import tempfile
        core = EPWCore()
        # Task "migracja adresacji": a project with zero configured
        # devices now gets zero default DO command definitions (no flat
        # DO01-64 fallback left to fall back to) - a real ADA card is
        # needed for this test's own "a default command definition
        # exists out of the box" premise to hold at all. Mutating
        # project_manager.config directly BEFORE startup() would be
        # thrown away - startup() calls load_project() first, which
        # REPLACES self.config wholesale (from a real file, or a fresh
        # default if project_file doesn't exist) - so the devices list
        # has to actually be on disk, at a scratch path, for
        # load_project() to pick it up.
        project_file = os.path.join(tempfile.mkdtemp(), "project.json")
        with open(project_file, "w", encoding="utf-8") as f:
            json.dump({
                "format": "EPW_OS_PROJECT", "schema_version": 1, "project_id": "TEST",
                "devices": [{"id": "ADA1", "type": "ADA", "channels": 4}],
            }, f)
        core.project_manager.project_file = project_file
        core.startup()
        core.device_manager.update_comm("ADA1")  # tracked now (unlike the old flat "DO01") - bring it online
        class AllowAll:
            ready = True
            is_running = True
            def validate_command(self, t, a): return True, []
            def scan(self): pass
            def load_program(self, f): return True
        core.logic_engine = AllowAll()
        core.command_manager.logic_engine = core.logic_engine
        if training_active:
            core.training_mode.set_active(True, actor="Engineer")
        # Push the pending-command timeout well past anything this test
        # could plausibly take, so there is no real-world timing window
        # in which the background threading.Timer could fire mid-test
        # and race the immediate-state read below (CommandDefinition is
        # a frozen dataclass - replace() swaps in a copy, not a mutation).
        key = "ADA1.DO.1.CLOSE"
        core.command_manager._definitions[key] = dataclasses.replace(
            core.command_manager._definitions[key], timeout_ms=3_600_000
        )
        # The tag route_command() actually writes to - "ADA1.DO.1" itself
        # (self-referential definition: output_tag == feedback_tag, see
        # the comment above and epw_core.py's startup()). Read it
        # straight from the definition rather than hardcoding it, so
        # this stays correct if that mapping ever changes.
        output_tag = core.command_manager._definitions[key].output_tag
        write_calls = []
        real_write_tag = core.sim_driver.write_tag
        core.sim_driver.write_tag = lambda t, v: (write_calls.append((t, v)), real_write_tag(t, v))[1]
        rec = core.command_manager.request_command_ex("ADA1.DO.1", "CLOSE")
        immediate_state = rec.state
        value = core.tag_manager.get_value(output_tag)
        core.command_manager._pending_commands.pop(rec.id, None)  # already resolved to SUCCESS by now; harmless if so
        core.shutdown()
        return immediate_state, value, write_calls, output_tag

    state_off, value_off, writes_off, output_tag_off = run(False)
    state_on, value_on, writes_on, output_tag_on = run(True)
    assert output_tag_off == output_tag_on  # sanity: same definition both runs

    # write_calls captures every write_tag() call on the shared
    # SimulatorDriver instance, not just this test's own DO01 command -
    # including SimulatorDriver._run_loop()'s own unrelated 1-second
    # analog-simulation heartbeat (AI1/AI2/...), which keeps ticking
    # regardless of Training Mode (deliberately: "SimulatorDriver.write_tag()
    # itself is untouched by this feature, per GRANICE" - driver_manager.py).
    # That heartbeat is real and harmless, but under a slow/loaded test
    # run (core.startup()..shutdown() taking >=1s) it can fire inside this
    # test's own window and land in write_calls, failing the assertion
    # below over a write this test was never about - confirmed by
    # reproducing under load vs. in isolation. Scope the check to the
    # actual command's own output tag so only a real DO01 write counts.
    do01_writes_off = [c for c in writes_off if c[0] == output_tag_off]
    do01_writes_on = [c for c in writes_on if c[0] == output_tag_on]

    assert state_off == state_on == "SUCCESS"
    assert value_off == value_on is True, "the tag must visibly change state on screen either way"
    assert do01_writes_off != [], "control: the normal run really did reach the driver"
    assert do01_writes_on == [], "the driver must never be touched while Training Mode is active"


def test_permissions_and_interlocks_work_the_same_in_training_mode(db):
    """DOWOD: "uprawnienia i blokady dzialaja w trybie cwiczebnym tak
    samo" - EMERGENCY_STOP blocks a command in Training Mode exactly as
    it does normally (SafetyKernel is untouched and never even asked
    whether Training Mode exists)."""
    core = EPWCore()
    core.startup()
    core.logic_engine = _AllowAllLogicRuntime()
    core.command_manager.logic_engine = core.logic_engine

    # Task (device-communication-status gate, a separate fix in this
    # same session): ADA01 is a real, DeviceManager-tracked device, and
    # SafetyKernel.validate_command_safety() now requires it to be
    # affirmatively ONLINE before permitting a command - true almost
    # immediately after a real startup() (SimulatorDriver's background
    # thread reports its first heartbeat within ~1 poll cycle), but not
    # deterministically at this exact line (a race against that
    # background thread). Advancing comm directly, synchronously, avoids
    # that race - this test is about Training Mode/EMERGENCY_STOP, not
    # device communication.
    core.device_manager.update_comm("ADA01")

    core.training_mode.set_active(True, actor="Engineer")

    core.tag_manager.update_tag("EMERGENCY_STOP", True)
    permitted, reasons = core.command_manager.request_command("ADA01.DO01", "CLOSE")
    assert permitted is False
    assert "Emergency Stop" in reasons[0]

    core.tag_manager.update_tag("EMERGENCY_STOP", False)
    permitted, reasons = core.command_manager.request_command("ADA01.DO01", "CLOSE")
    assert permitted is True

    core.shutdown()


def test_unknown_command_still_blocked_in_training_mode(db):
    core = EPWCore()
    core.startup()
    core.training_mode.set_active(True, actor="Engineer")
    rec = core.command_manager.request_command_ex("NoSuchDevice", "CLOSE")
    assert rec.state == "BLOCKED"
    core.shutdown()


def test_command_reaches_driver_normally_when_training_mode_off(db):
    """Control: with Training Mode left off, the exact same command DOES
    reach the real driver - proves the spy/assertions above are actually
    meaningful, not just always-false."""
    core = _make_core_with_allow_all_logic()
    core.command_manager.load_definitions({
        "TEST_DEVICE.CLOSE": {
            "driver_id": "SIM_DRIVER", "output_tag": "ADA01.DO01", "output_value": True,
            "timeout_ms": 1500,
        }
    })
    write_calls = []
    real_write_tag = core.sim_driver.write_tag
    def spying_write_tag(tag_name, value):
        write_calls.append((tag_name, value))
        return real_write_tag(tag_name, value)
    core.sim_driver.write_tag = spying_write_tag

    assert core.training_mode.active is False
    core.command_manager.request_command_ex("TEST_DEVICE", "CLOSE")
    assert write_calls == [("ADA01.DO01", True)]

    core.shutdown()


def test_training_mode_on_and_off_reach_the_audit_log(db):
    """DOWOD (Task 5): "wlaczenie i wylaczenie trybu zapisywane do
    dziennika audytowego" - through the REAL AuditLogger/DB, not a fake."""
    core = EPWCore()
    core.startup()
    core.training_mode.set_active(True, actor="Engineer")
    core.training_mode.set_active(False, actor="Engineer")

    entries = core.audit_logger.query(limit=10)
    event_types = [e.event_type for e in entries]
    assert "TRAINING_MODE_ON" in event_types
    assert "TRAINING_MODE_OFF" in event_types

    core.shutdown()


def test_training_mode_does_not_survive_a_restart(db):
    """DOWOD: "tryb nie przezywa restartu"."""
    core1 = EPWCore()
    core1.startup()
    core1.training_mode.set_active(True, actor="Engineer")
    assert core1.training_mode.active is True
    core1.shutdown()

    # A fresh process-equivalent instance (a real restart constructs a
    # brand new EPWCore the exact same way) - must always come back up
    # inactive, regardless of what the previous instance did.
    core2 = EPWCore()
    core2.startup()
    assert core2.training_mode.active is False
    core2.shutdown()


def test_project_config_never_gains_a_training_mode_key(db):
    """Belt-and-suspenders proof of "never persisted anywhere": even
    after enabling/disabling it repeatedly and saving the project for an
    unrelated reason, project_manager.config never grows a training-mode
    section the way switching_counters/service_notes deliberately do."""
    core = EPWCore()
    core.startup()
    core.training_mode.set_active(True, actor="Engineer")
    core.training_mode.set_active(False, actor="Engineer")
    core.project_manager.save_project()
    assert not any("training" in str(k).lower() for k in core.project_manager.config.keys())
    core.shutdown()
