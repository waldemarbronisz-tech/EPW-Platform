"""Tests for SafetyKernel's health-DETECTION-and-SIGNALING layer (the
task adding check_system_health()/enforce_safe_state() - see
SESSION_REPORT.md). Everything here drives check_system_health()
directly and synchronously (never SafetyKernel.start()'s real
background thread) for fully deterministic control over exactly how
many "cycles" occur - the same approach the rest of this codebase
already uses for DeviceManager.check_watchdogs()/TagManager.check_watchdogs().

Built from small, real, headless core objects (EventBus/TagManager/
DeviceManager/AlarmManager - all cheap, no threads, no DB) plus two
lightweight fakes (a fake driver/driver_manager and a fake audit_logger)
so these tests stay fast, deterministic, and don't depend on the real
SQLite test database at all.
"""
import pytest

from epw_os.core.events import EventBus
from epw_os.core.tag_manager import TagManager, TagType
from epw_os.core.device_manager import DeviceManager, DeviceStatus
from epw_os.core.alarm_manager import AlarmManager, AlarmState
from epw_os.core.safety_kernel import SafetyKernel


class _FakeDriver:
    """Stands in for a real driver (SimulatorDriver et al.) - `alive` is
    directly settable so tests can simulate "the driver thread died"
    without needing a real thread at all. route_command()/write_tag()
    are recorded, never actually called by SafetyKernel itself - see
    test_safety_kernel_never_writes_to_outputs()."""
    def __init__(self):
        self.alive = True
        self.write_calls = []

    def is_alive(self):
        return self.alive

    def write_tag(self, tag_name, value):
        self.write_calls.append((tag_name, value))
        return True


class _FakeDriverManager:
    def __init__(self):
        self.drivers = {}
        self.route_calls = []

    def register_driver(self, driver_id, driver):
        self.drivers[driver_id] = driver

    def get_driver(self, driver_id):
        return self.drivers.get(driver_id)

    def route_command(self, driver_id, output_tag, value):
        self.route_calls.append((driver_id, output_tag, value))
        return True


class _FakeAuditLogger:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))


def _make_kernel(missed_cycles_threshold=3):
    """One device ("DEV1") on one fake driver ("DRV1"), fully wired -
    the minimal setup every test below builds on."""
    bus = EventBus()
    tag_manager = TagManager(bus)
    device_manager = DeviceManager(bus)
    alarm_manager = AlarmManager(bus)
    driver_manager = _FakeDriverManager()
    audit_logger = _FakeAuditLogger()
    driver = _FakeDriver()
    driver_manager.register_driver("DRV1", driver)
    device_manager.register_device("DEV1", "DRV1", timeout=9999)  # DeviceManager's own
    # watchdog timeout is deliberately huge and irrelevant here - this
    # task's "3 consecutive missed cycles" criterion is SafetyKernel's
    # own, independent of DeviceManager.check_watchdogs()'s separate,
    # single-elapsed-time mechanism.

    kernel = SafetyKernel(
        tag_manager, driver_manager=driver_manager, device_manager=device_manager,
        alarm_manager=alarm_manager, audit_logger=audit_logger,
        missed_cycles_threshold=missed_cycles_threshold,
    )
    return kernel, tag_manager, device_manager, alarm_manager, driver_manager, audit_logger, driver


def _advance_comm(device_manager, device_id="DEV1"):
    """Simulates one real, successful poll cycle for this device -
    exactly what DriverManager/SimulatorDriver's own comm-ok heartbeat
    does via DeviceManager.update_comm(), which is deliberately reused
    here unchanged (GRANICE: only read driver/comm-loop state)."""
    device_manager.update_comm(device_id)


# --- Criterion: N consecutive missed poll cycles -----------------------

def test_two_missed_cycles_do_not_raise_an_alarm():
    kernel, tag_manager, device_manager, alarm_manager, *_ = _make_kernel(missed_cycles_threshold=3)
    _advance_comm(device_manager)
    kernel.check_system_health()  # cycle 0: establishes the baseline, not a "miss"
    kernel.check_system_health()  # cycle 1: no new comm - miss #1
    kernel.check_system_health()  # cycle 2: no new comm - miss #2

    assert tag_manager.get_value("Safety.DEV1.Healthy") is True, \
        "one lost packet - or two - is normal, not a fault (task requirement)"
    assert tag_manager.get_value("Safety.DEV1.Fault") is False
    assert not alarm_manager.get_active_alarms(), "2 missed cycles must not raise any alarm"


def test_three_missed_cycles_do_raise_an_alarm():
    kernel, tag_manager, device_manager, alarm_manager, *_ = _make_kernel(missed_cycles_threshold=3)
    _advance_comm(device_manager)
    kernel.check_system_health()  # baseline
    kernel.check_system_health()  # miss #1
    kernel.check_system_health()  # miss #2
    kernel.check_system_health()  # miss #3 - threshold reached

    assert tag_manager.get_value("Safety.DEV1.Healthy") is False
    assert tag_manager.get_value("Safety.DEV1.Fault") is True
    active = alarm_manager.get_active_alarms()
    assert any(a.id == "DEVICE_HEALTH_DEV1" for a in active), active
    # System-wide aggregate must reflect it too.
    assert tag_manager.get_value("Safety.System.Healthy") is False
    assert tag_manager.get_value("Safety.System.Fault") is True
    assert any(a.id == SafetyKernel.SYSTEM_ALARM_ID for a in alarm_manager.get_active_alarms())


def test_threshold_is_configurable_not_hardcoded():
    """Same scenario as above, but with a threshold of 1 - proves the
    value actually comes from the constructor parameter, not a hardcoded
    "3" inside the method."""
    kernel, tag_manager, device_manager, alarm_manager, *_ = _make_kernel(missed_cycles_threshold=1)
    _advance_comm(device_manager)
    kernel.check_system_health()  # baseline
    kernel.check_system_health()  # miss #1 - already at threshold 1

    assert tag_manager.get_value("Safety.DEV1.Healthy") is False
    assert tag_manager.get_value("Safety.DEV1.Fault") is True


# --- Current state vs. latch --------------------------------------------

def test_recovered_comm_clears_current_state_but_not_the_latch():
    kernel, tag_manager, device_manager, alarm_manager, *_ = _make_kernel(missed_cycles_threshold=3)
    _advance_comm(device_manager)
    kernel.check_system_health()
    kernel.check_system_health()
    kernel.check_system_health()
    kernel.check_system_health()  # now unhealthy (3 misses reached)
    assert tag_manager.get_value("Safety.DEV1.Healthy") is False
    assert tag_manager.get_value("Safety.DEV1.Fault") is True

    _advance_comm(device_manager)  # comm resumes
    kernel.check_system_health()

    assert tag_manager.get_value("Safety.DEV1.Healthy") is True, \
        "current state must clear the instant comm actually resumes"
    assert tag_manager.get_value("Safety.DEV1.Fault") is True, \
        "the latch must NOT clear on its own - a fault that already happened stays visible"
    # AlarmManager's own state must reflect "condition gone, still needs
    # acknowledgement" (CLEARED_UNACK), not silently vanish (NORMAL).
    alarm = next(a for a in alarm_manager.get_all_alarms() if a.id == "DEVICE_HEALTH_DEV1")
    assert alarm.state == AlarmState.CLEARED_UNACK, alarm.state


def test_latch_clears_only_on_manual_acknowledgement():
    kernel, tag_manager, device_manager, alarm_manager, *_ = _make_kernel(missed_cycles_threshold=3)
    _advance_comm(device_manager)
    for _ in range(4):
        kernel.check_system_health()
    assert tag_manager.get_value("Safety.DEV1.Fault") is True

    # Recovers on its own - latch must still be set (already covered
    # above, re-asserted here as this test's own starting point).
    _advance_comm(device_manager)
    kernel.check_system_health()
    assert tag_manager.get_value("Safety.DEV1.Fault") is True

    # More health-check cycles passing, all healthy, must NOT clear the
    # latch by themselves - only acknowledging the alarm may.
    _advance_comm(device_manager)
    kernel.check_system_health()
    _advance_comm(device_manager)
    kernel.check_system_health()
    assert tag_manager.get_value("Safety.DEV1.Fault") is True, \
        "further healthy cycles alone must never clear the latch"

    # The existing Alarms page's acknowledge flow: AlarmManager.acknowledge_alarm()
    # (unchanged) -> 'alarm_acknowledged' event -> (in production,
    # EPWCore._on_alarm_acknowledged bridges this; called directly here,
    # exactly what that bridge does) -> SafetyKernel.on_alarm_acknowledged().
    alarm_manager.acknowledge_alarm("DEVICE_HEALTH_DEV1", user="Operator")
    kernel.on_alarm_acknowledged("DEVICE_HEALTH_DEV1", "Operator")

    assert tag_manager.get_value("Safety.DEV1.Fault") is False, \
        "the latch must clear once, and only once, the operator acknowledges it"
    ack_entries = [e for e in kernel.audit_logger.entries if e[0] == "DEVICE_HEALTH_FAULT_ACK"]
    assert ack_entries, "acknowledging the latch must be logged (task requirement)"


def test_acknowledging_an_unrelated_alarm_does_not_clear_the_latch():
    """on_alarm_acknowledged() must ignore alarm ids it didn't raise
    itself - a device COMM_FAILURE alarm or EMERGENCY_STOP being
    acknowledged must never accidentally clear a SafetyKernel latch."""
    kernel, tag_manager, device_manager, alarm_manager, *_ = _make_kernel(missed_cycles_threshold=3)
    _advance_comm(device_manager)
    for _ in range(4):
        kernel.check_system_health()
    assert tag_manager.get_value("Safety.DEV1.Fault") is True

    kernel.on_alarm_acknowledged("DEVICE_COMM_DEV1", "Operator")  # a different alarm id
    kernel.on_alarm_acknowledged("EMERGENCY_STOP", "Operator")

    assert tag_manager.get_value("Safety.DEV1.Fault") is True


# --- Occurrence and acknowledgement are logged --------------------------

def test_every_fault_occurrence_is_logged():
    kernel, tag_manager, device_manager, alarm_manager, *_ = _make_kernel(missed_cycles_threshold=3)
    _advance_comm(device_manager)
    for _ in range(4):
        kernel.check_system_health()

    occurrences = [e for e in kernel.audit_logger.entries if e[0] == "DEVICE_HEALTH_FAULT"]
    assert occurrences, "the fault occurrence must be recorded to the event journal"


# --- enforce_safe_state() blocks new commands, and only that -----------

def test_unhealthy_system_blocks_a_command_and_logs_it():
    kernel, tag_manager, device_manager, alarm_manager, *_ = _make_kernel(missed_cycles_threshold=3)
    _advance_comm(device_manager)
    for _ in range(4):
        kernel.check_system_health()
    assert tag_manager.get_value("Safety.System.Healthy") is False

    permitted, reason = kernel.validate_command_safety("DEV1.SomeOutput", "CLOSE")

    assert permitted is False
    assert "health" in reason.lower() or "system" in reason.lower(), reason
    blocked_entries = [e for e in kernel.audit_logger.entries if e[0] == "COMMAND_BLOCKED_UNHEALTHY_SYSTEM"]
    assert blocked_entries, "a command blocked by an unhealthy system must be logged"


def test_healthy_system_does_not_block_commands():
    kernel, tag_manager, device_manager, alarm_manager, *_ = _make_kernel(missed_cycles_threshold=3)
    _advance_comm(device_manager)
    kernel.check_system_health()
    # Task (device-communication-status gate): this bare test harness has
    # no EPWCore wired in, so nothing bridges DeviceManager's own
    # "DEV1 is online" status onto a Device.DEV1.Status tag the way
    # EPWCore._on_device_status_changed() does in the real app - set it
    # directly here, simulating that bridge, so this test isolates what
    # it actually means to test (enforce_safe_state() passing does not
    # block) from the separate per-device status gate (covered in its
    # own tests below).
    tag_manager.add_tag("Device.DEV1.Status", "ONLINE", TagType.STRING)

    permitted, reason = kernel.validate_command_safety("DEV1.SomeOutput", "CLOSE")
    assert permitted is True, reason


def test_enforce_safe_state_directly():
    kernel, tag_manager, device_manager, alarm_manager, *_ = _make_kernel(missed_cycles_threshold=3)
    ok, reason = kernel.enforce_safe_state()
    assert ok is True and reason == ""

    _advance_comm(device_manager)
    for _ in range(4):
        kernel.check_system_health()
    ok, reason = kernel.enforce_safe_state()
    assert ok is False
    assert reason


# --- Per-device communication-status gate (Task: "luka w blokadzie
# komend przy awarii komunikacji dla urzadzen skonfigurowanych w
# projekcie") - validate_command_safety()'s per-target check, previously
# based on a Device.<id>.Status tag that only ever existed for the four
# hardcoded default devices, now applies to ANY device DeviceManager
# tracks (device_manager.devices - populated for both default AND
# project-configured devices by EPWCore.startup()) and fails SAFE
# (blocks) when that status is anything other than affirmatively
# ONLINE - missing, OFFLINE, COMM_FAILURE, or unrecognized alike. -----

def test_default_device_online_command_passes():
    kernel, tag_manager, device_manager, alarm_manager, *_ = _make_kernel()
    tag_manager.add_tag("Device.DEV1.Status", "ONLINE", TagType.STRING)
    permitted, reason = kernel.validate_command_safety("DEV1.SomeOutput", "CLOSE")
    assert permitted is True, reason


def test_default_device_offline_command_blocked():
    kernel, tag_manager, device_manager, alarm_manager, *_ = _make_kernel()
    tag_manager.add_tag("Device.DEV1.Status", "OFFLINE", TagType.STRING)
    permitted, reason = kernel.validate_command_safety("DEV1.SomeOutput", "CLOSE")
    assert permitted is False
    assert "DEV1" in reason


def test_project_configured_device_online_command_passes():
    """SafetyKernel makes no distinction between a hardcoded default
    device and a project-configured one - both are simply whatever
    DeviceManager.devices happens to contain (see EPWCore.startup(),
    which registers both kinds through the exact same
    device_manager.register_device() call). "CUSTOM_PLC" here stands in
    for any device a project.json's own "devices" section defines."""
    kernel, tag_manager, device_manager, alarm_manager, *_ = _make_kernel()
    device_manager.register_device("CUSTOM_PLC", "DRV1", timeout=9999)
    tag_manager.add_tag("Device.CUSTOM_PLC.Status", "ONLINE", TagType.STRING)
    permitted, reason = kernel.validate_command_safety("CUSTOM_PLC.DO01", "CLOSE")
    assert permitted is True, reason


def test_project_configured_device_offline_command_blocked():
    """THE scenario that did not work before this fix: a
    project-configured device (anything other than the four hardcoded
    ones) never got a Device.<id>.Status tag registered anywhere, so
    this exact command always silently passed regardless of its real
    communication state."""
    kernel, tag_manager, device_manager, alarm_manager, *_ = _make_kernel()
    device_manager.register_device("CUSTOM_PLC", "DRV1", timeout=9999)
    tag_manager.add_tag("Device.CUSTOM_PLC.Status", "OFFLINE", TagType.STRING)
    permitted, reason = kernel.validate_command_safety("CUSTOM_PLC.DO01", "CLOSE")
    assert permitted is False
    assert "CUSTOM_PLC" in reason


def test_device_with_no_status_tag_at_all_is_blocked_not_passed():
    """The heart of the fix. Before: a missing Device.<id>.Status tag -
    exactly what every project-configured device had, always - made
    get_value() return None, and None == "COMM_FAILURE" was False, so
    the check silently never fired and the command passed. After: no
    information about a tracked device's communication status BLOCKS,
    the same "nie wiem, czy urzadzenie zyje - nie wysylam do niego
    rozkazu" principle as an explicit OFFLINE/COMM_FAILURE reading."""
    kernel, tag_manager, device_manager, alarm_manager, *_ = _make_kernel()
    device_manager.register_device("CUSTOM_PLC", "DRV1", timeout=9999)
    assert tag_manager.get_tag("Device.CUSTOM_PLC.Status") is None  # confirms the precondition being tested
    permitted, reason = kernel.validate_command_safety("CUSTOM_PLC.DO01", "CLOSE")
    assert permitted is False
    assert "CUSTOM_PLC" in reason
    assert "unknown" in reason.lower()


def test_command_blocked_by_device_status_is_logged_with_device_name_and_reason():
    kernel, tag_manager, device_manager, alarm_manager, driver_manager, audit_logger, driver = _make_kernel()
    device_manager.register_device("CUSTOM_PLC", "DRV1", timeout=9999)
    tag_manager.add_tag("Device.CUSTOM_PLC.Status", "OFFLINE", TagType.STRING)

    kernel.validate_command_safety("CUSTOM_PLC.DO01", "CLOSE")

    blocked = [e for e in audit_logger.entries if e[0] == "COMMAND_BLOCKED_DEVICE_STATUS"]
    assert blocked, audit_logger.entries
    event_type, actor, detail, success = blocked[0]
    assert "CUSTOM_PLC" in detail, detail  # names WHICH device
    assert "OFFLINE" in detail, detail     # says WHY
    assert success is False


def test_untracked_device_tag_is_unaffected_no_regression():
    """A command target whose device_id DeviceManager never registered
    at all - e.g. a standalone output channel with no separate
    communication module of its own ("DO05" in the real app) - must
    behave exactly as before this fix: unaffected, always passes this
    particular check (there is nothing tracked to know the status of)."""
    kernel, tag_manager, device_manager, alarm_manager, *_ = _make_kernel()
    permitted, reason = kernel.validate_command_safety("DO05", "CLOSE")
    assert permitted is True, reason


def test_untracked_device_unaffected_even_with_no_device_manager_wired():
    """Defense in depth: the exact same "nothing to check, so don't
    block" outcome when self.device_manager is None entirely (the
    construction-time state before EPWCore wires it in - see
    set_device_manager())."""
    from epw_os.core.tag_manager import TagManager
    tag_manager = TagManager(EventBus())
    kernel = SafetyKernel(tag_manager)  # no device_manager at all
    permitted, reason = kernel.validate_command_safety("DEV1.SomeOutput", "CLOSE")
    assert permitted is True, reason


# --- SafetyKernel never writes to any output ----------------------------

def test_safety_kernel_never_writes_to_outputs():
    """Detection and signaling only (task's central rule: "ekran
    informuje, sprzet chroni") - runs a full cycle through healthy,
    unhealthy (alarm raised), recovered-but-latched, acknowledged, and a
    blocked command, then asserts the fake driver/driver_manager never
    saw a single write/route call."""
    kernel, tag_manager, device_manager, alarm_manager, driver_manager, audit_logger, driver = _make_kernel(
        missed_cycles_threshold=3
    )
    _advance_comm(device_manager)
    kernel.check_system_health()
    for _ in range(4):
        kernel.check_system_health()  # go unhealthy
    _advance_comm(device_manager)
    kernel.check_system_health()  # recover (latch stays)
    alarm_manager.acknowledge_alarm("DEVICE_HEALTH_DEV1", user="Operator")
    kernel.on_alarm_acknowledged("DEVICE_HEALTH_DEV1", "Operator")
    kernel.validate_command_safety("DEV1.SomeOutput", "CLOSE")  # a command attempt, permitted or not

    driver.alive = False  # also exercise the driver-thread-dead path
    kernel.check_system_health()

    assert driver.write_calls == [], "SafetyKernel must never write to a driver's output"
    assert driver_manager.route_calls == [], "SafetyKernel must never route a command to a driver"


# --- Driver-thread-dead criterion ---------------------------------------

def test_driver_thread_dead_marks_device_unhealthy():
    kernel, tag_manager, device_manager, alarm_manager, driver_manager, audit_logger, driver = _make_kernel(
        missed_cycles_threshold=3
    )
    _advance_comm(device_manager)
    kernel.check_system_health()
    assert tag_manager.get_value("Safety.DEV1.Healthy") is True

    driver.alive = False
    kernel.check_system_health()

    assert tag_manager.get_value("Safety.DEV1.Healthy") is False
    assert tag_manager.get_value("Safety.DEV1.Fault") is True


# --- Tag staleness criterion ---------------------------------------------

def test_stale_device_tag_marks_device_unhealthy():
    kernel, tag_manager, device_manager, alarm_manager, *_ = _make_kernel(missed_cycles_threshold=3)
    # A tag genuinely belonging to this device (name-prefixed "DEV1."),
    # with a short, explicitly configured timeout - reuses TagManager's
    # own pre-existing Tag.timeout/check_watchdogs()/STALE mechanism
    # entirely as-is (see safety_kernel.py's _device_has_stale_tags()).
    tag_manager.add_tag("DEV1.DI01", False, TagType.BOOL, timeout=1.0)
    # Backdated well past its own 1-second timeout, so check_watchdogs()
    # (called by check_system_health() below) marks it STALE immediately -
    # no real sleep() needed for a deterministic test.
    import time
    tag_manager._tags["DEV1.DI01"].last_update = time.time() - 10.0

    _advance_comm(device_manager)
    kernel.check_system_health()

    assert tag_manager.get_value("Safety.DEV1.Healthy") is False
    assert tag_manager.get_value("Safety.DEV1.Fault") is True


# --- No wiring yet: must not crash --------------------------------------

def test_check_system_health_is_a_no_op_without_a_device_manager():
    tag_manager = TagManager(EventBus())
    kernel = SafetyKernel(tag_manager)  # exactly how EPWCore.__init__ constructs it
    kernel.check_system_health()  # must not raise
    assert tag_manager.get_tag("Safety.System.Healthy") is None
