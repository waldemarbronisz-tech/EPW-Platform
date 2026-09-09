"""Tests for the intrusion (burglar) alarm system
(epw_os/core/intrusion_manager.py) - headless, no Qt needed at all.

Organized by the Task's own "DOWOD UKONCZENIA" checklist:
1. Each line type behaves per its definition (including 24H alarming
   while disarmed).
2. A DOZOROWA (SUPERVISORY) line signals a plain VIOLATION but never
   alarms on it - a FAULT (sabotage/short/break/undetermined) on that
   same line alarms exactly like any other type, always (see the
   "SUPERVISORY fault alarming" section further down).
3. Entry/exit countdowns count down correctly.
4. Arming with a violated line requires explicit confirmation.
5. A line bypass reaches the audit log.
6. The module never writes to any tag but its own "Security.*" ones.
Plus: access-level gating, persistence (and bypass's deliberate
non-persistence), the system-wide aggregate state, and zone/line CRUD
guards.
"""
import time

import pytest

from epw_os.core.access_manager import AccessLevel
from epw_os.core.events import EventBus
from epw_os.core.intrusion_manager import (
    IntrusionManager, LineType, ZoneState, NORMAL_STATE_NC, NORMAL_STATE_NO, is_line_violated,
    LineInputMode, LineParametrization, LineState, default_value_windows, classify_parametrized_value,
    is_line_fault_state,
)
from epw_os.core.tag_manager import TagManager, TagType


class FakeProjectManager:
    """Minimal stand-in matching only the ProjectManager methods this
    module actually calls - same "no real project.json needed" pattern
    as test_switching_counters.py's own FakeProjectManager."""
    def __init__(self, zones=None, lines=None, analog_points=None):
        self._zones = zones or []
        self._lines = lines or []
        self._line_supervision = {}
        self._power_supervision = {}
        self._analog_points = analog_points or []
        self._alarm_memory = {}
        self._history_retention = {}
        self.save_count = 0

    def get_intrusion_zones(self):
        return self._zones

    def set_intrusion_zones(self, zones):
        self._zones = list(zones)

    def get_intrusion_lines(self):
        return self._lines

    def set_intrusion_lines(self, lines):
        self._lines = list(lines)

    def get_intrusion_line_supervision(self):
        return self._line_supervision

    def set_intrusion_line_supervision(self, data):
        self._line_supervision = dict(data)

    def get_intrusion_power_supervision(self):
        return self._power_supervision

    def set_intrusion_power_supervision(self, data):
        self._power_supervision = dict(data)

    def get_analog_points(self):
        return self._analog_points

    def get_intrusion_alarm_memory(self):
        return self._alarm_memory

    def set_intrusion_alarm_memory(self, data):
        self._alarm_memory = dict(data)

    def get_intrusion_history_retention(self):
        return self._history_retention

    def set_intrusion_history_retention(self, data):
        self._history_retention = dict(data)

    def save_project(self):
        self.save_count += 1


class FakeAuditLogger:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))


class FakeAlarmHistoryLogger:
    """Minimal in-memory stand-in matching only the
    IntrusionAlarmHistoryLogger methods IntrusionManager actually calls -
    same pattern FakeProjectManager/FakeAuditLogger already use."""
    def __init__(self):
        self.entries = []  # list of dicts, in record() order (oldest first)

    def record(self, event_type, actor, detail="", zone_id=None, zone_name=None, line_id=None, line_name=None):
        self.entries.append({
            "event_type": event_type, "actor": actor, "detail": detail,
            "zone_id": zone_id, "zone_name": zone_name, "line_id": line_id, "line_name": line_name,
        })

    def get_retention_config(self):
        return {"max_events": 0, "max_days": 0}

    def configure_retention(self, max_events=None, max_days=None):
        pass


@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def tags(bus):
    tm = TagManager(bus)
    # Seeded True (secure/closed) - the default line normal_state used by
    # every test here is NC, where True is the SECURE reading and False
    # is tripped (see is_line_violated()). Starting these at the
    # TagManager-wide default of False would mean every line is already
    # "violated" the instant it's added, before any test explicitly
    # trips anything.
    for i in range(1, 9):
        tm.add_tag(f"DI{i}", True, TagType.BOOL, source="HARDWARE")
    return tm


@pytest.fixture
def pm():
    return FakeProjectManager()


@pytest.fixture
def audit():
    return FakeAuditLogger()


@pytest.fixture
def history():
    return FakeAlarmHistoryLogger()


@pytest.fixture
def im(bus, tags, pm, audit, history):
    return IntrusionManager(bus, tags, pm, audit, history)


def _add_zone(im, name="Zone1", exit_delay=0.0, entry_delay=0.0):
    return im.add_zone(name, exit_delay, entry_delay)


def _add_line(im, zone_id, tag="DI1", normal_state=NORMAL_STATE_NC, line_type=LineType.INSTANT, name="Line1"):
    return im.add_line(name, zone_id, tag, normal_state, line_type)


# --- is_line_violated() - pure helper --------------------------------------

def test_is_line_violated_nc():
    assert is_line_violated(True, NORMAL_STATE_NC) is False   # closed loop = secure
    assert is_line_violated(False, NORMAL_STATE_NC) is True   # broken loop = violated


def test_is_line_violated_no():
    assert is_line_violated(False, NORMAL_STATE_NO) is False  # open = secure
    assert is_line_violated(True, NORMAL_STATE_NO) is True    # closed = violated


# --- 1 & 2: per-line-type behavior -----------------------------------------

def test_instant_line_alarms_immediately_when_armed(im, tags, audit):
    zone_id = _add_zone(im)
    _add_line(im, zone_id, tag="DI1", line_type=LineType.INSTANT)
    assert im.arm_zone(zone_id, actor="Operator").success is True
    assert im.get_zone_state(zone_id) == ZoneState.ARMED

    tags.update_tag("DI1", False)  # NC line trips

    assert im.get_zone_state(zone_id) == ZoneState.ALARM
    assert tags.get_value("Security.System.Alarm") is True
    assert any(e[0] == "INTRUSION_ALARM" for e in audit.entries)


def test_instant_line_has_no_effect_while_disarmed(im, tags):
    zone_id = _add_zone(im)
    _add_line(im, zone_id, tag="DI1", line_type=LineType.INSTANT)
    tags.update_tag("DI1", False)  # trips while disarmed
    assert im.get_zone_state(zone_id) == ZoneState.DISARMED
    assert tags.get_value("Security.Line.L1.Violated") is True  # still visible as violated...
    assert tags.get_value("Security.System.Alarm") is False     # ...but never an alarm


def test_delayed_line_starts_entry_countdown_when_armed(im, tags):
    zone_id = _add_zone(im, entry_delay=60.0)
    _add_line(im, zone_id, tag="DI1", line_type=LineType.DELAYED)
    im.arm_zone(zone_id, actor="Operator")
    tags.update_tag("DI1", False)
    assert im.get_zone_state(zone_id) == ZoneState.ENTRY_DELAY
    assert tags.get_value("Security.System.EntryCountdownActive") is True
    im._cancel_timer(zone_id)  # don't let a real 60s timer outlive the test


def test_delayed_line_has_no_effect_while_disarmed(im, tags):
    zone_id = _add_zone(im)
    _add_line(im, zone_id, tag="DI1", line_type=LineType.DELAYED)
    tags.update_tag("DI1", False)
    assert im.get_zone_state(zone_id) == ZoneState.DISARMED


def test_24h_line_alarms_even_when_disarmed(im, tags, audit):
    """Task's own explicit proof requirement: "test: linia CALODOBOWA
    alarmujaca przy rozbrojonym systemie"."""
    zone_id = _add_zone(im)
    _add_line(im, zone_id, tag="DI1", line_type=LineType.TWENTY_FOUR_HOUR)
    assert im.get_zone_state(zone_id) == ZoneState.DISARMED

    tags.update_tag("DI1", False)

    assert im.get_zone_state(zone_id) == ZoneState.ALARM
    assert tags.get_value("Security.System.Alarm") is True
    assert any(e[0] == "INTRUSION_ALARM" and "24H" in e[2] for e in audit.entries)


def test_24h_line_alarms_while_armed_too(im, tags):
    zone_id = _add_zone(im)
    _add_line(im, zone_id, tag="DI1", line_type=LineType.TWENTY_FOUR_HOUR)
    im.arm_zone(zone_id, actor="Operator")
    tags.update_tag("DI1", False)
    assert im.get_zone_state(zone_id) == ZoneState.ALARM


def test_supervisory_line_signals_violation_but_never_alarms(im, tags):
    """Task's own explicit proof requirement: "test: linia DOZOROWA
    sygnalizuje naruszenie, ale NIE wywoluje alarmu" - checked in both
    disarmed and armed zone states."""
    zone_id = _add_zone(im)
    line_id = _add_line(im, zone_id, tag="DI1", line_type=LineType.SUPERVISORY)

    tags.update_tag("DI1", False)
    assert tags.get_value(f"Security.Line.{line_id}.Violated") is True
    assert im.get_zone_state(zone_id) == ZoneState.DISARMED  # unaffected
    assert tags.get_value("Security.Supervisory.Violated") is True

    tags.update_tag("DI1", True)  # clear it, then arm and try again
    im.arm_zone(zone_id, actor="Operator")
    tags.update_tag("DI1", False)
    assert im.get_zone_state(zone_id) == ZoneState.ARMED  # still unaffected, even armed
    assert tags.get_value("Security.System.Alarm") is False


@pytest.mark.parametrize("fault_value,expected_state", [
    (75.0, LineState.TAMPER),
    (5.0, LineState.SHORT),
    (95.0, LineState.FAULT_OPEN),
    (200.0, LineState.UNDETERMINED),
])
def test_supervisory_line_alarms_on_any_fault_state(im, tags, audit, fault_value, expected_state):
    """RESOLVED design decision (see _dispatch_line_fault()'s own
    docstring): a SUPERVISORY line's "never alarms" rule is about a
    plain VIOLATION (motion), not a FAULT (sabotage/short/break/
    undetermined) - a fault alarms exactly like every other line type,
    regardless of zone state, for every one of the 4 fault states."""
    tags.add_tag("AI9", 50.0, TagType.REAL, source="HARDWARE")
    zone_id = _add_zone(im)
    line_id = im.add_line("Perimeter", zone_id, "AI9", NORMAL_STATE_NC, LineType.SUPERVISORY,
                           input_mode=LineInputMode.PARAMETRIZED, parametrization=LineParametrization.DEOL)
    assert im.get_zone_state(zone_id) == ZoneState.DISARMED  # not armed - a fault must alarm anyway

    tags.update_tag("AI9", fault_value)
    assert im.get_line_state(line_id) == expected_state
    assert tags.get_value(f"Security.Line.{line_id}.Fault") is True
    assert im.get_zone_state(zone_id) == ZoneState.ALARM
    assert any(e[0] == "INTRUSION_ALARM" and "fault" in e[2].lower() for e in audit.entries)


# --- 3: entry/exit countdown timing ----------------------------------------

def test_exit_delay_counts_down_then_arms(im, tags):
    zone_id = _add_zone(im, exit_delay=0.1)
    result = im.arm_zone(zone_id, actor="Operator")
    assert result.success is True
    assert im.get_zone_state(zone_id) == ZoneState.EXIT_DELAY
    assert tags.get_value("Security.System.ExitCountdownActive") is True
    assert 0 < im.get_countdown_remaining(zone_id) <= 1

    time.sleep(0.3)

    assert im.get_zone_state(zone_id) == ZoneState.ARMED
    assert tags.get_value("Security.System.ExitCountdownActive") is False
    assert im.get_countdown_remaining(zone_id) == 0


def test_entry_delay_counts_down_then_alarms_if_not_disarmed(im, tags, audit):
    zone_id = _add_zone(im, entry_delay=0.1)
    _add_line(im, zone_id, tag="DI1", line_type=LineType.DELAYED, name="Front Door")
    im.arm_zone(zone_id, actor="Operator")

    tags.update_tag("DI1", False)
    assert im.get_zone_state(zone_id) == ZoneState.ENTRY_DELAY

    time.sleep(0.3)

    assert im.get_zone_state(zone_id) == ZoneState.ALARM
    assert any(e[0] == "INTRUSION_ALARM" and "Front Door" in e[2] for e in audit.entries)


def test_disarm_during_entry_delay_cancels_the_pending_alarm(im, tags):
    zone_id = _add_zone(im, entry_delay=0.15)
    _add_line(im, zone_id, tag="DI1", line_type=LineType.DELAYED)
    im.arm_zone(zone_id, actor="Operator")
    tags.update_tag("DI1", False)
    assert im.get_zone_state(zone_id) == ZoneState.ENTRY_DELAY

    im.disarm_zone(zone_id, actor="Operator")
    assert im.get_zone_state(zone_id) == ZoneState.DISARMED

    time.sleep(0.3)  # let the original timer's deadline pass

    assert im.get_zone_state(zone_id) == ZoneState.DISARMED  # never alarmed


def test_countdown_remaining_reflects_real_time_left(im):
    zone_id = _add_zone(im, exit_delay=1.0)
    assert im.get_countdown_remaining(zone_id) == 0  # disarmed: nothing counting down
    im.arm_zone(zone_id, actor="Operator")
    remaining = im.get_countdown_remaining(zone_id)
    assert 0 < remaining <= 1
    im._cancel_timer(zone_id)


# --- 4: arming with a violated line requires confirmation ------------------

def test_arm_with_violated_line_requires_confirmation(im, tags, audit):
    zone_id = _add_zone(im)
    line_id = _add_line(im, zone_id, tag="DI1", name="Window")
    tags.update_tag("DI1", False)  # violated before arming is even attempted

    result = im.arm_zone(zone_id, actor="Operator")

    assert result.success is False
    assert result.needs_confirmation is True
    assert result.violated_line_ids == [line_id]
    assert im.get_zone_state(zone_id) == ZoneState.DISARMED  # nothing armed yet
    assert not any(e[0] == "INTRUSION_ZONE_ARMED" for e in audit.entries)  # nothing authorized yet either


def test_arm_forced_despite_violation_succeeds_and_audits_it(im, tags, audit):
    zone_id = _add_zone(im)
    _add_line(im, zone_id, tag="DI1", name="Window")
    tags.update_tag("DI1", False)

    result = im.arm_zone(zone_id, actor="Operator", force=True)

    assert result.success is True
    assert im.get_zone_state(zone_id) == ZoneState.ARMED
    entries = [e for e in audit.entries if e[0] == "INTRUSION_ZONE_ARMED"]
    assert len(entries) == 1
    assert "Window" in entries[0][2] and "DESPITE" in entries[0][2]


def test_arm_ignores_a_bypassed_violated_line(im, tags):
    zone_id = _add_zone(im)
    line_id = _add_line(im, zone_id, tag="DI1", name="Known-faulty sensor")
    tags.update_tag("DI1", False)
    im.bypass_line(line_id, True, actor="Engineer")

    result = im.arm_zone(zone_id, actor="Operator")

    assert result.success is True
    assert result.needs_confirmation is False


# --- 5: bypass reaches the audit log ----------------------------------------

def test_bypass_on_and_off_both_reach_the_audit_log(im, tags, audit):
    zone_id = _add_zone(im)
    line_id = _add_line(im, zone_id, tag="DI1", name="Garage Sensor")

    assert im.bypass_line(line_id, True, actor="Engineer") is True
    on_entries = [e for e in audit.entries if e[0] == "INTRUSION_LINE_BYPASS_ON"]
    assert len(on_entries) == 1
    assert "Garage Sensor" in on_entries[0][2] and on_entries[0][1] == "Engineer"

    assert im.bypass_line(line_id, False, actor="Engineer") is True
    off_entries = [e for e in audit.entries if e[0] == "INTRUSION_LINE_BYPASS_OFF"]
    assert len(off_entries) == 1


def test_bypass_suppresses_the_violated_tag(im, tags):
    zone_id = _add_zone(im)
    line_id = _add_line(im, zone_id, tag="DI1")
    tags.update_tag("DI1", False)
    assert tags.get_value(f"Security.Line.{line_id}.Violated") is True

    im.bypass_line(line_id, True, actor="Engineer")
    assert tags.get_value(f"Security.Line.{line_id}.Violated") is False
    assert im.is_line_violated_now(line_id) is True  # the real sensor state is still queryable

    im.bypass_line(line_id, False, actor="Engineer")
    assert tags.get_value(f"Security.Line.{line_id}.Violated") is True


def test_bypass_is_idempotent_no_duplicate_audit_entry(im, audit):
    zone_id = _add_zone(im)
    line_id = _add_line(im, zone_id, tag="DI1")
    im.bypass_line(line_id, True, actor="Engineer")
    im.bypass_line(line_id, True, actor="Engineer")  # already bypassed - no-op
    assert len([e for e in audit.entries if e[0] == "INTRUSION_LINE_BYPASS_ON"]) == 1


# --- 6: the module never writes to any output/driver tag -------------------

def test_never_writes_to_any_non_security_tag(im, tags, audit):
    """Task's own explicit proof requirement: "test: modul NIE zapisuje
    na zadne wyjscie". Monkeypatches TagManager.update_tag to record
    every write made through the whole public surface (add/remove zone
    and line, arm with a violation needing force, an alarm, a bypass,
    disarm) and asserts every single one is a "Security."-prefixed tag -
    never a DI/DO/Cabinet/output tag."""
    written = []
    real_update_tag = tags.update_tag
    tags.update_tag = lambda name, value, quality=None: (
        written.append(name), real_update_tag(name, value) if quality is None else real_update_tag(name, value, quality)
    )[1]

    zone_id = _add_zone(im)
    line_id = _add_line(im, zone_id, tag="DI1", line_type=LineType.INSTANT)
    tags.update_tag("DI1", False)  # violate before arming (a real DI write, done by the TEST, not the module)
    im.arm_zone(zone_id, actor="Operator", force=True)  # arms straight to ALARM (INSTANT, already violated)
    im.bypass_line(line_id, True, actor="Engineer")
    im.disarm_zone(zone_id, actor="Operator")
    im.remove_line(line_id, level=AccessLevel.ENGINEER)
    im.remove_zone(zone_id, level=AccessLevel.ENGINEER)

    module_writes = [n for n in written if n != "DI1"]  # exclude the test's own DI1 write above
    assert module_writes, "the scenario above should have produced at least one tag write to check"
    assert all(n.startswith("Security.") for n in module_writes), module_writes


# --- access-level gating -----------------------------------------------------

def test_arm_disarm_require_operator_level(im, tags):
    zone_id = _add_zone(im)
    result = im.arm_zone(zone_id, actor="User", level=AccessLevel.USER)
    assert result.success is False
    assert im.get_zone_state(zone_id) == ZoneState.DISARMED

    im.arm_zone(zone_id, actor="Operator", level=AccessLevel.OPERATOR)
    assert im.disarm_zone(zone_id, actor="User", level=AccessLevel.USER) is False
    assert im.get_zone_state(zone_id) == ZoneState.ARMED


def test_zone_line_config_and_bypass_require_engineer_level(bus, tags, pm, audit):
    im = IntrusionManager(bus, tags, pm, audit)
    assert im.add_zone("Z", 0, 0, level=AccessLevel.OPERATOR) is None
    zone_id = im.add_zone("Z", 0, 0, level=AccessLevel.ENGINEER)
    assert zone_id is not None

    assert im.add_line("L", zone_id, "DI1", NORMAL_STATE_NC, LineType.INSTANT, level=AccessLevel.OPERATOR) is None
    line_id = im.add_line("L", zone_id, "DI1", NORMAL_STATE_NC, LineType.INSTANT, level=AccessLevel.ENGINEER)
    assert line_id is not None

    assert im.bypass_line(line_id, True, actor="Operator", level=AccessLevel.OPERATOR) is False
    assert im.bypass_line(line_id, True, actor="Engineer", level=AccessLevel.ENGINEER) is True


# --- persistence -------------------------------------------------------------

def test_zones_and_lines_persist_and_reload(bus, tags, pm, audit):
    im1 = IntrusionManager(bus, tags, pm, audit)
    zone_id = im1.add_zone("Perimeter", 30.0, 45.0)
    im1.add_line("Front Door", zone_id, "DI1", NORMAL_STATE_NC, LineType.DELAYED)

    bus2 = EventBus()
    tags2 = TagManager(bus2)
    for i in range(1, 9):
        tags2.add_tag(f"DI{i}", True, TagType.BOOL, source="HARDWARE")
    im2 = IntrusionManager(bus2, tags2, pm, audit)  # "restart": same project data, fresh instance

    zones = im2.get_zones()
    assert len(zones) == 1
    assert zones[0]["name"] == "Perimeter"
    assert zones[0]["exit_delay_seconds"] == 30.0
    lines = im2.get_lines()
    assert len(lines) == 1
    assert lines[0]["name"] == "Front Door"
    assert lines[0]["line_type"] == LineType.DELAYED


def test_bypass_does_not_survive_a_restart(bus, tags, pm, audit):
    """Deliberate design choice (see module docstring) - same reasoning
    as Training Mode's own non-persistence."""
    im1 = IntrusionManager(bus, tags, pm, audit)
    zone_id = im1.add_zone("Z", 0, 0)
    line_id = im1.add_line("L", zone_id, "DI1", NORMAL_STATE_NC, LineType.INSTANT)
    im1.bypass_line(line_id, True, actor="Engineer")
    assert im1.is_line_bypassed(line_id) is True

    bus2 = EventBus()
    tags2 = TagManager(bus2)
    for i in range(1, 9):
        tags2.add_tag(f"DI{i}", True, TagType.BOOL, source="HARDWARE")
    im2 = IntrusionManager(bus2, tags2, pm, audit)

    assert im2.is_line_bypassed(line_id) is False


# --- system-wide aggregate state ---------------------------------------------

def test_system_state_priority_alarm_beats_everything(im, tags):
    z1 = _add_zone(im, name="Z1")
    z2 = _add_zone(im, name="Z2", exit_delay=5.0)
    _add_line(im, z1, tag="DI1", line_type=LineType.INSTANT)
    im.arm_zone(z1, actor="Operator")
    im.arm_zone(z2, actor="Operator")  # -> EXIT_DELAY
    assert im.get_system_state() == ZoneState.EXIT_DELAY  # no alarm yet, EXIT_DELAY is the most urgent present

    tags.update_tag("DI1", False)  # z1 -> ALARM

    assert im.get_system_state() == ZoneState.ALARM
    assert tags.get_value("Security.System.State") == ZoneState.ALARM
    im._cancel_timer(z2)


def test_system_state_disarmed_with_no_zones(im):
    assert im.get_system_state() == ZoneState.DISARMED


# --- zone/line CRUD guards ---------------------------------------------------

def test_remove_zone_refused_while_lines_assigned(im):
    zone_id = _add_zone(im)
    _add_line(im, zone_id, tag="DI1")
    assert im.remove_zone(zone_id, level=AccessLevel.ENGINEER) is False
    assert zone_id in {z["id"] for z in im.get_zones()}


def test_remove_zone_succeeds_once_empty(im):
    zone_id = _add_zone(im)
    assert im.remove_zone(zone_id, level=AccessLevel.ENGINEER) is True
    assert zone_id not in {z["id"] for z in im.get_zones()}


def test_disarm_is_idempotent_no_duplicate_audit_entry(im, audit):
    zone_id = _add_zone(im)
    assert im.disarm_zone(zone_id, actor="Operator") is False  # already disarmed
    assert not any(e[0] == "INTRUSION_ZONE_DISARMED" for e in audit.entries)


def test_disarm_from_alarm_returns_to_disarmed(im, tags):
    zone_id = _add_zone(im)
    _add_line(im, zone_id, tag="DI1", line_type=LineType.TWENTY_FOUR_HOUR)
    tags.update_tag("DI1", False)
    assert im.get_zone_state(zone_id) == ZoneState.ALARM

    assert im.disarm_zone(zone_id, actor="Operator") is True
    assert im.get_zone_state(zone_id) == ZoneState.DISARMED
    assert tags.get_value("Security.System.Alarm") is False


# --- arm/disarm requested from logic, via the ArmRequest tag -----------------

def test_arm_request_tag_from_logic_arms_the_zone(im, tags):
    zone_id = _add_zone(im)
    tags.update_tag(f"Security.Zone.{zone_id}.ArmRequest", True)
    assert im.get_zone_state(zone_id) == ZoneState.ARMED


def test_arm_request_tag_false_disarms_the_zone(im, tags):
    zone_id = _add_zone(im)
    im.arm_zone(zone_id, actor="Operator")
    tags.update_tag(f"Security.Zone.{zone_id}.ArmRequest", False)
    assert im.get_zone_state(zone_id) == ZoneState.DISARMED


# --- Task part 2: false-alarm filtering per line ----------------------------
# DOWOD's own checklist: min_violation_seconds, multiplicity, lockout, an old
# (pre-this-task) config still working identically, and the new signals for
# logic (Locked, MultiplicityCounting).

def test_old_config_without_any_new_filter_field_behaves_exactly_as_before(bus, tags, audit):
    """A project.json line dict that predates Part 2 entirely - no
    min_violation_seconds/multiplicity_*/lockout_after_count/
    alarm_hold_seconds keys at all - loaded through the real
    _load_from_project() path, not add_line() (which would seed the
    defaults itself either way - this proves the LOADING path also
    backfills them)."""
    from epw_os.core.intrusion_manager import IntrusionManager

    class OldFakeProjectManager:
        def __init__(self):
            self._zones = [{"id": "Z1", "name": "Zone1", "exit_delay_seconds": 0.0, "entry_delay_seconds": 0.0}]
            self._lines = [{"id": "L1", "name": "Front Door", "zone_id": "Z1", "tag": "DI1",
                             "normal_state": NORMAL_STATE_NC, "line_type": LineType.INSTANT}]
        def get_intrusion_zones(self): return self._zones
        def set_intrusion_zones(self, zones): self._zones = list(zones)
        def get_intrusion_lines(self): return self._lines
        def set_intrusion_lines(self, lines): self._lines = list(lines)
        # This "old" project.json shape ALSO predates line supervision
        # and power supervision (this task's own additions) - no such
        # keys/methods exist here at all, exactly like a real pre-this-
        # task project.json wouldn't. IntrusionManager must not crash
        # calling these - it should just treat them as "nothing to load".
        def get_intrusion_line_supervision(self): return {}
        def set_intrusion_line_supervision(self, data): pass
        def get_intrusion_power_supervision(self): return {}
        def set_intrusion_power_supervision(self, data): pass
        def get_analog_points(self): return []
        # Same reasoning, one task later: alarm memory (Task 2/3) also
        # postdates this "old" shape - no such section/methods exist.
        def get_intrusion_alarm_memory(self): return {}
        def set_intrusion_alarm_memory(self, data): pass
        def save_project(self): pass

    old_im = IntrusionManager(bus, tags, OldFakeProjectManager(), audit)
    assert old_im.arm_zone("Z1", actor="Operator").success is True
    assert old_im.get_zone_state("Z1") == ZoneState.ARMED

    tags.update_tag("DI1", False)  # NC line trips - INSTANT alarms immediately, exactly as before

    assert old_im.get_zone_state("Z1") == ZoneState.ALARM
    assert tags.get_value("Security.System.Alarm") is True
    assert any(e[0] == "INTRUSION_ALARM" for e in audit.entries)
    old_im.shutdown()


def test_violation_shorter_than_min_violation_seconds_does_not_alarm(im, tags, audit):
    zone_id = _add_zone(im)
    line_id = im.add_line("Front Door", zone_id, "DI1", NORMAL_STATE_NC, LineType.INSTANT,
                           min_violation_seconds=0.3)
    im.arm_zone(zone_id, actor="Operator")

    tags.update_tag("DI1", False)  # trips...
    time.sleep(0.05)
    tags.update_tag("DI1", True)  # ...but clears well before the 0.3s threshold - a bounce

    time.sleep(0.4)  # let the (cancelled) debounce deadline pass either way

    assert im.get_zone_state(zone_id) == ZoneState.ARMED  # never alarmed
    assert tags.get_value("Security.System.Alarm") is False
    assert tags.get_value(f"Security.Line.{line_id}.Violated") is False
    assert not any(e[0] == "INTRUSION_ALARM" for e in audit.entries)


def test_violation_longer_than_min_violation_seconds_does_alarm(im, tags):
    zone_id = _add_zone(im)
    line_id = im.add_line("Front Door", zone_id, "DI1", NORMAL_STATE_NC, LineType.INSTANT,
                           min_violation_seconds=0.1)
    im.arm_zone(zone_id, actor="Operator")

    tags.update_tag("DI1", False)  # trips and STAYS tripped past the threshold
    assert im.get_zone_state(zone_id) == ZoneState.ARMED  # not yet - still debouncing
    assert tags.get_value(f"Security.Line.{line_id}.Violated") is False

    time.sleep(0.25)

    assert im.get_zone_state(zone_id) == ZoneState.ALARM
    assert tags.get_value(f"Security.Line.{line_id}.Violated") is True


def test_multiplicity_two_first_violation_alone_does_not_alarm_second_does(im, tags):
    zone_id = _add_zone(im)
    im.add_line("Front Door", zone_id, "DI1", NORMAL_STATE_NC, LineType.INSTANT,
                multiplicity_count=2, multiplicity_window_seconds=1.0)
    im.arm_zone(zone_id, actor="Operator")

    tags.update_tag("DI1", False)  # 1st violation
    assert im.get_zone_state(zone_id) == ZoneState.ARMED  # not enough yet

    tags.update_tag("DI1", True)   # clears
    tags.update_tag("DI1", False)  # 2nd violation, well within the 1s window

    assert im.get_zone_state(zone_id) == ZoneState.ALARM


def test_multiplicity_counter_resets_after_window_elapses_without_another_violation(im, tags):
    zone_id = _add_zone(im)
    line_id = im.add_line("Front Door", zone_id, "DI1", NORMAL_STATE_NC, LineType.INSTANT,
                           multiplicity_count=2, multiplicity_window_seconds=0.15)
    im.arm_zone(zone_id, actor="Operator")

    tags.update_tag("DI1", False)  # 1st violation - starts the window
    assert tags.get_value(f"Security.Line.{line_id}.MultiplicityCounting") is True
    tags.update_tag("DI1", True)

    time.sleep(0.3)  # let the window elapse with no 2nd violation

    assert tags.get_value(f"Security.Line.{line_id}.MultiplicityCounting") is False
    assert im.get_zone_state(zone_id) == ZoneState.ARMED  # never reached 2 - no alarm

    # counter genuinely reset to 0, not just "still at 1" - a fresh single
    # violation now must NOT alarm either (needs 2 more, not 1 more)
    tags.update_tag("DI1", False)
    assert im.get_zone_state(zone_id) == ZoneState.ARMED


def test_lockout_after_repeated_alarms_locks_the_line_and_reaches_audit_log(im, tags, audit):
    """24H (not INSTANT/DELAYED) so each violation alarms independently of
    the zone's own state - INSTANT would stop reaching _handle_violation()
    at all once the zone is already ALARM, making a 2nd same-cycle alarm
    from the SAME line impossible to reach without also invoking
    alarm_hold_seconds; 24H's "alarms regardless of zone state" rule (see
    the module docstring) isolates lockout_after_count on its own."""
    zone_id = _add_zone(im)
    line_id = im.add_line("Tamper", zone_id, "DI1", NORMAL_STATE_NC, LineType.TWENTY_FOUR_HOUR,
                           lockout_after_count=2)

    tags.update_tag("DI1", False)  # alarm #1
    assert im.get_zone_state(zone_id) == ZoneState.ALARM
    assert im.is_line_locked(line_id) is False
    tags.update_tag("DI1", True)

    tags.update_tag("DI1", False)  # alarm #2 - reaches the lockout threshold
    assert im.is_line_locked(line_id) is True
    assert tags.get_value(f"Security.Line.{line_id}.Locked") is True
    assert any(e[0] == "INTRUSION_LINE_LOCKED" and e[3] is False for e in audit.entries)
    alarm_count_before = sum(1 for e in audit.entries if e[0] == "INTRUSION_ALARM")
    tags.update_tag("DI1", True)

    tags.update_tag("DI1", False)  # alarm #3 attempt - suppressed, line is locked
    alarm_count_after = sum(1 for e in audit.entries if e[0] == "INTRUSION_ALARM")
    assert alarm_count_after == alarm_count_before  # no new alarm reached the log

    # "do rozbrojenia" - disarming the zone unlocks it again
    im.disarm_zone(zone_id, actor="Operator")
    assert im.is_line_locked(line_id) is False
    assert tags.get_value(f"Security.Line.{line_id}.Locked") is False


def test_alarm_hold_seconds_returns_to_armed_once_elapsed_and_line_clear(im, tags):
    zone_id = _add_zone(im)
    im.add_line("Front Door", zone_id, "DI1", NORMAL_STATE_NC, LineType.INSTANT,
                alarm_hold_seconds=0.15)
    im.arm_zone(zone_id, actor="Operator")

    tags.update_tag("DI1", False)  # trips -> alarm
    assert im.get_zone_state(zone_id) == ZoneState.ALARM
    tags.update_tag("DI1", True)  # clears well before the hold elapses

    assert im.get_zone_state(zone_id) == ZoneState.ALARM  # still held

    time.sleep(0.3)

    assert im.get_zone_state(zone_id) == ZoneState.ARMED  # auto-returned, line was clear


def test_alarm_hold_seconds_stays_in_alarm_while_line_still_violated(im, tags):
    zone_id = _add_zone(im)
    im.add_line("Front Door", zone_id, "DI1", NORMAL_STATE_NC, LineType.INSTANT,
                alarm_hold_seconds=0.1)
    im.arm_zone(zone_id, actor="Operator")

    tags.update_tag("DI1", False)  # trips -> alarm, stays tripped
    assert im.get_zone_state(zone_id) == ZoneState.ALARM

    time.sleep(0.3)  # hold time elapses, but the line never cleared

    assert im.get_zone_state(zone_id) == ZoneState.ALARM  # requires manual disarm


def test_alarm_hold_seconds_zero_never_auto_returns_manual_disarm_only(im, tags):
    zone_id = _add_zone(im)
    im.add_line("Front Door", zone_id, "DI1", NORMAL_STATE_NC, LineType.INSTANT)  # default: 0.0
    im.arm_zone(zone_id, actor="Operator")

    tags.update_tag("DI1", False)
    assert im.get_zone_state(zone_id) == ZoneState.ALARM
    tags.update_tag("DI1", True)

    time.sleep(0.2)

    assert im.get_zone_state(zone_id) == ZoneState.ALARM  # today's behavior - unchanged


# --- this task: line supervision (input mode, EOL/DEOL, power, life/silence) -

def test_line_with_no_supervision_configured_behaves_exactly_as_before(im, tags, audit):
    """add_line() called with none of this task's new kwargs at all -
    input_mode defaults to CONTACT, and a CONTACT-mode line's own
    existing behavior (an INSTANT line alarming immediately while
    armed) is completely unaffected - Task: "linia bez nadzoru dziala
    identycznie jak przed zmiana"."""
    zone_id = _add_zone(im)
    line_id = im.add_line("Front Door", zone_id, "DI1", NORMAL_STATE_NC, LineType.INSTANT)
    line = next(l for l in im.get_lines() if l["id"] == line_id)
    assert line["input_mode"] == LineInputMode.CONTACT

    im.arm_zone(zone_id, actor="Operator")
    tags.update_tag("DI1", False)

    assert im.get_zone_state(zone_id) == ZoneState.ALARM
    assert tags.get_value(f"Security.Line.{line_id}.State") == LineState.VIOLATED
    assert im.is_line_fault(line_id) is False


def test_eol_recognizes_secure_violated_and_fault_open(im, tags):
    tags.add_tag("AI1", 50.0, TagType.REAL, source="HARDWARE")
    zone_id = _add_zone(im)
    line_id = im.add_line("Fence", zone_id, "AI1", NORMAL_STATE_NC, LineType.INSTANT,
                           input_mode=LineInputMode.PARAMETRIZED, parametrization=LineParametrization.EOL)
    windows = im.get_lines()[0]["value_windows"]
    assert set(windows.keys()) == {LineState.VIOLATED, LineState.SECURE, LineState.FAULT_OPEN}

    tags.update_tag("AI1", 50.0)  # inside the default SECURE window [45,55]
    assert im.get_line_state(line_id) == LineState.SECURE

    tags.update_tag("AI1", 5.0)  # inside VIOLATED [0,20]
    assert im.get_line_state(line_id) == LineState.VIOLATED

    tags.update_tag("AI1", 95.0)  # inside FAULT_OPEN [90,100]
    assert im.get_line_state(line_id) == LineState.FAULT_OPEN
    assert im.is_line_fault(line_id) is True


def test_deol_recognizes_all_five_states(im, tags):
    tags.add_tag("AI2", 50.0, TagType.REAL, source="HARDWARE")
    zone_id = _add_zone(im)
    line_id = im.add_line("Perimeter", zone_id, "AI2", NORMAL_STATE_NC, LineType.INSTANT,
                           input_mode=LineInputMode.PARAMETRIZED, parametrization=LineParametrization.DEOL)
    windows = im.get_lines()[0]["value_windows"]
    assert set(windows.keys()) == {LineState.SHORT, LineState.VIOLATED, LineState.SECURE,
                                    LineState.TAMPER, LineState.FAULT_OPEN}

    for value, expected in (
        (5.0, LineState.SHORT), (25.0, LineState.VIOLATED), (50.0, LineState.SECURE),
        (75.0, LineState.TAMPER), (95.0, LineState.FAULT_OPEN),
    ):
        tags.update_tag("AI2", value)
        assert im.get_line_state(line_id) == expected, f"value {value} -> expected {expected}"


def test_value_outside_every_window_is_undetermined_and_is_a_fault():
    windows = default_value_windows(LineParametrization.DEOL)
    assert classify_parametrized_value(37.5, windows) == LineState.UNDETERMINED  # squarely in a gap
    assert is_line_fault_state(LineState.UNDETERMINED) is True
    assert classify_parametrized_value(None, windows) == LineState.UNDETERMINED


def test_tamper_alarms_while_zone_is_disarmed(im, tags, audit):
    """Task part 1: TAMPER/SHORT/FAULT_OPEN/UNDETERMINED "alarmuja
    niezaleznie od stanu uzbrojenia, jak linia calodobowa" - checked
    with the zone left DISARMED (an INSTANT line's own violations are a
    no-op while disarmed - a fault must NOT be similarly gated)."""
    tags.add_tag("AI3", 50.0, TagType.REAL, source="HARDWARE")
    zone_id = _add_zone(im)
    line_id = im.add_line("Perimeter", zone_id, "AI3", NORMAL_STATE_NC, LineType.INSTANT,
                           input_mode=LineInputMode.PARAMETRIZED, parametrization=LineParametrization.DEOL)
    assert im.get_zone_state(zone_id) == ZoneState.DISARMED

    tags.update_tag("AI3", 75.0)  # TAMPER

    assert im.get_zone_state(zone_id) == ZoneState.ALARM
    assert tags.get_value("Security.System.Alarm") is True
    assert tags.get_value(f"Security.Line.{line_id}.Fault") is True
    assert tags.get_value("Security.System.LineFault") is True
    assert any(e[0] == "INTRUSION_ALARM" and "fault" in e[2].lower() for e in audit.entries)


def test_undetermined_value_alarms_via_the_same_fault_path_as_tamper(im, tags, audit):
    """UNDETERMINED dispatches through _dispatch_line_fault() exactly
    like TAMPER/SHORT/FAULT_OPEN do - no special-casing by WHICH fault
    state triggered it."""
    tags.add_tag("AI6", 50.0, TagType.REAL, source="HARDWARE")
    zone_id = _add_zone(im)
    line_id = im.add_line("Perimeter", zone_id, "AI6", NORMAL_STATE_NC, LineType.INSTANT,
                           input_mode=LineInputMode.PARAMETRIZED, parametrization=LineParametrization.EOL)
    tags.update_tag("AI6", 37.5)  # squarely in a gap between EOL's windows

    assert im.get_line_state(line_id) == LineState.UNDETERMINED
    assert im.get_zone_state(zone_id) == ZoneState.ALARM
    assert tags.get_value(f"Security.Line.{line_id}.Fault") is True


def test_mains_ok_true_when_healthy_false_on_loss(im, tags, audit):
    """DOWOD (fix/power-supervision-polarity): MainsOk = TRUE while
    healthy, FALSE on loss - the platform-wide "TRUE = SPRAWNY"
    convention, replacing the old MainsFailed (True = failed)."""
    tags.add_tag("DI5", True, TagType.BOOL, source="HARDWARE")  # secure = mains OK (True)
    zone_id = _add_zone(im)
    assert im.configure_power_supervision(mains_tag="DI5", mains_ok_state=True, level="Engineer") is True
    assert tags.get_value("Security.Power.MainsOk") is True
    assert tags.get_value("Security.System.TechnicalAlarm") is False

    tags.update_tag("DI5", False)  # mains lost

    # DOWOD: technical alarm raises on mains LOSS, i.e. at MainsOk=False.
    assert tags.get_value("Security.Power.MainsOk") is False
    assert tags.get_value("Security.System.TechnicalAlarm") is True
    # Task: a technical alarm is a DIFFERENT category from the intrusion
    # alarm - it must never set System.Alarm/ZoneState.ALARM.
    assert tags.get_value("Security.System.Alarm") is False
    assert im.get_zone_state(zone_id) == ZoneState.DISARMED
    # Audit event-type identifiers are unchanged by the polarity fix -
    # they name the real-world event, not the tag's own raw value.
    assert any(e[0] == "INTRUSION_MAINS_FAILED" for e in audit.entries)

    # Task: "zanik zasilania NIE MOZE blokowac uzbrojenia ani rozbrojenia"
    result = im.arm_zone(zone_id, actor="Operator")
    assert result.success is True
    assert im.get_zone_state(zone_id) == ZoneState.ARMED
    assert im.disarm_zone(zone_id, actor="Operator") is True

    # Restoring mains flips back to True and clears the technical alarm.
    tags.update_tag("DI5", True)
    assert tags.get_value("Security.Power.MainsOk") is True
    assert tags.get_value("Security.System.TechnicalAlarm") is False
    assert any(e[0] == "INTRUSION_MAINS_RESTORED" for e in audit.entries)


def test_battery_ok_true_when_healthy_false_on_fault(im, tags, audit):
    """Same DOWOD as mains, for the battery signal."""
    tags.add_tag("DI6", True, TagType.BOOL, source="HARDWARE")  # secure = battery OK (True)
    assert im.configure_power_supervision(battery_tag="DI6", battery_ok_state=True, level="Engineer") is True
    assert tags.get_value("Security.Power.BatteryOk") is True

    tags.update_tag("DI6", False)  # battery faulted

    assert tags.get_value("Security.Power.BatteryOk") is False
    assert tags.get_value("Security.System.TechnicalAlarm") is True
    assert any(e[0] == "INTRUSION_BATTERY_FAULT" for e in audit.entries)

    tags.update_tag("DI6", True)
    assert tags.get_value("Security.Power.BatteryOk") is True
    assert tags.get_value("Security.System.TechnicalAlarm") is False
    assert any(e[0] == "INTRUSION_BATTERY_OK" for e in audit.entries)


def test_power_supervision_unconfigured_causes_no_errors_and_reads_inert(im, tags):
    """Task: "brak konfiguracji oznacza brak nadzoru, bez bledow" -
    unconfigured now reads Ok=True (healthy), not Failed=False, but the
    externally-observable "nothing to report" guarantee is identical."""
    assert im.get_power_supervision_config()["mains_tag"] is None
    assert tags.get_value("Security.Power.MainsOk") is True
    assert tags.get_value("Security.Power.BatteryOk") is True
    assert tags.get_value("Security.System.TechnicalAlarm") is False


# --- DOWOD (fix/power-supervision-polarity): an EXISTING persisted power-
# supervision config behaves identically after the fix - "mains_tag"/
# "mains_ok_state"/"battery_tag"/"battery_ok_state" are untouched by this
# task (they describe the RAW INPUT's own healthy-state convention, not
# the derived Security.Power.* tag's name or polarity), so no migration
# of project.json is needed or performed - this loads a project.json
# SECTION exactly as an old, pre-fix project would have persisted it, and
# confirms the real-world outcome (which raw readings raise the technical
# alarm) is unchanged.

def test_existing_power_supervision_config_behaves_identically_after_the_fix(bus, audit, history):
    pm = FakeProjectManager()
    # Exactly the shape configure_power_supervision() always persisted,
    # before AND after this task - nothing here changed shape or meaning.
    pm._power_supervision = {
        "mains_tag": "DI5", "mains_ok_state": True,
        "battery_tag": "DI6", "battery_ok_state": False,
    }
    tm = TagManager(bus)
    tm.add_tag("DI5", True, TagType.BOOL, source="HARDWARE")   # reads True -> mains_ok_state True -> healthy
    tm.add_tag("DI6", True, TagType.BOOL, source="HARDWARE")   # reads True -> battery_ok_state False -> NOT healthy
    im = IntrusionManager(bus, tm, pm, audit, history)

    # Loaded config unchanged (no migration performed or needed).
    cfg = im.get_power_supervision_config()
    assert cfg == {"mains_tag": "DI5", "mains_ok_state": True, "battery_tag": "DI6", "battery_ok_state": False}

    # Same real-world readings -> same real-world outcome as before this
    # task: mains healthy (DI5=True matches mains_ok_state=True), battery
    # NOT healthy (DI6=True does NOT match battery_ok_state=False) -
    # exactly what the pre-fix MainsFailed=False/BatteryFault=True would
    # have reported too, just spelled the other way around now.
    assert tm.get_value("Security.Power.MainsOk") is True
    assert tm.get_value("Security.Power.BatteryOk") is False
    assert tm.get_value("Security.System.TechnicalAlarm") is True

    # And the config's own persisted shape is still exactly what a fresh
    # save_project() would write back - proving set_intrusion_power_
    # supervision() was never called just from loading/recomputing.
    assert pm._power_supervision == {
        "mains_tag": "DI5", "mains_ok_state": True, "battery_tag": "DI6", "battery_ok_state": False,
    }


def test_silence_threshold_marks_line_suspect_without_alarming(im, tags, audit):
    zone_id = _add_zone(im)
    line_id = im.add_line("Rarely Used Door", zone_id, "DI1", NORMAL_STATE_NC, LineType.INSTANT,
                           silence_threshold_seconds=0.15)
    assert im.is_line_suspect(line_id) is False

    time.sleep(0.3)
    im._check_line_silence()  # normally driven by the periodic tick (start()) - called directly, no real thread needed

    assert im.is_line_suspect(line_id) is True
    assert tags.get_value(f"Security.Line.{line_id}.Suspect") is True
    assert any(e[0] == "INTRUSION_LINE_SUSPECT" for e in audit.entries)
    # Task: "to ma byc OSTRZEZENIE, nie alarm... nie wywoluje stanu alarmu"
    assert im.get_zone_state(zone_id) == ZoneState.DISARMED
    assert tags.get_value("Security.System.Alarm") is False

    # A genuine violation clears the suspect flag again.
    tags.update_tag("DI1", False)
    im._check_line_silence()
    assert im.is_line_suspect(line_id) is False


def test_silence_threshold_zero_never_marks_a_line_suspect(im, tags):
    zone_id = _add_zone(im)
    line_id = im.add_line("Door", zone_id, "DI1", NORMAL_STATE_NC, LineType.INSTANT)  # default: 0 (off)
    time.sleep(0.1)
    im._check_line_silence()
    assert im.is_line_suspect(line_id) is False


def test_line_life_snapshot_tracks_count_and_timestamps(im, tags):
    zone_id = _add_zone(im)
    line_id = im.add_line("Door", zone_id, "DI1", NORMAL_STATE_NC, LineType.INSTANT)
    snap0 = im.get_line_life_snapshot(line_id)
    assert snap0["closes"] == 0
    assert snap0["last_violation_at"] is None
    assert snap0["first_transition"] is None

    tags.update_tag("DI1", False)  # violation #1
    time.sleep(0.05)
    tags.update_tag("DI1", True)   # clears
    tags.update_tag("DI1", False)  # violation #2

    snap = im.get_line_life_snapshot(line_id)
    assert snap["closes"] == 2
    assert snap["opens"] == 1
    assert snap["last_violation_at"] is not None
    assert snap["first_transition"] is not None
    assert snap["closed_seconds"] > 0  # currently violated - live-accrued, like switching_counters' own snapshot


def test_arming_with_a_faulted_line_requires_confirmation_and_audits_it(im, tags, audit):
    tags.add_tag("AI4", 50.0, TagType.REAL, source="HARDWARE")
    zone_id = _add_zone(im)
    line_id = im.add_line("Perimeter", zone_id, "AI4", NORMAL_STATE_NC, LineType.INSTANT,
                           input_mode=LineInputMode.PARAMETRIZED, parametrization=LineParametrization.DEOL)
    tags.update_tag("AI4", 75.0)  # TAMPER - alarms immediately, any type, any zone state
    assert im.get_zone_state(zone_id) == ZoneState.ALARM
    im.disarm_zone(zone_id, actor="Operator")  # back to DISARMED - the line is STILL in fault

    result = im.arm_zone(zone_id, actor="Operator")
    assert result.success is False
    assert result.needs_confirmation is True
    assert line_id in result.fault_line_ids
    assert not any(e[0] == "INTRUSION_ZONE_ARMED" for e in audit.entries)  # not yet authorized

    forced = im.arm_zone(zone_id, actor="Operator", force=True)
    assert forced.success is True
    assert line_id in forced.fault_line_ids
    entry = next(e for e in audit.entries if e[0] == "INTRUSION_ZONE_ARMED")
    assert "fault" in entry[2].lower()


def test_cannot_assign_an_analog_tag_to_a_contact_mode_line(im, tags):
    """Task: "ma byc NIEMOZLIWE przypisanie wejscia niewlasciwego typu" -
    checked at the manager level (defense in depth behind the GUI's own
    type-filtered picker)."""
    tags.add_tag("AI5", 50.0, TagType.REAL, source="HARDWARE")
    zone_id = _add_zone(im)
    line_id = im.add_line("Door", zone_id, "AI5", NORMAL_STATE_NC, LineType.INSTANT,
                           input_mode=LineInputMode.CONTACT)
    assert line_id is None  # refused - AI5 is REAL, not BOOL


def test_cannot_assign_a_digital_tag_to_a_parametrized_mode_line(im, tags):
    zone_id = _add_zone(im)
    line_id = im.add_line("Door", zone_id, "DI1", NORMAL_STATE_NC, LineType.INSTANT,
                           input_mode=LineInputMode.PARAMETRIZED)
    assert line_id is None  # refused - DI1 is BOOL, not REAL


# =============================================================================
# Intrusion completion task: first-cause / alarm memory, walk-test mode,
# alarm event history, SUPERVISORY fault fix (see the top of this file for
# that last one's tests, right after test_supervisory_line_signals_...).
# =============================================================================

# --- first alarm cause / alarm memory ---------------------------------------

def test_first_alarm_cause_is_remembered_and_subsequent_ones_appended(im, tags, audit):
    """Task 2: "Gdy alarm wywola kilka linii pod rzad... system ma
    zapamietac i wyraznie pokazac, KTORA BYLA PIERWSZA... Kolejne
    naruszenia widoczne jako lista, ale WYRAZNIE ODDZIELONE"."""
    zone_id = _add_zone(im)
    line1 = _add_line(im, zone_id, tag="DI1", line_type=LineType.INSTANT, name="Front Door")
    line2 = _add_line(im, zone_id, tag="DI2", line_type=LineType.TWENTY_FOUR_HOUR, name="Panel Tamper")
    im.arm_zone(zone_id, actor="Operator")

    tags.update_tag("DI1", False)  # first cause
    assert im.get_zone_state(zone_id) == ZoneState.ALARM
    tags.update_tag("DI2", False)  # a SECOND alarm-worthy event, already in ALARM (24H alarms regardless)

    memory = im.get_alarm_memory(zone_id)
    assert memory["active"] is True
    assert memory["first_cause_line_id"] == line1
    assert memory["first_cause_line_name"] == "Front Door"
    assert memory["first_cause_at"] is not None
    assert len(memory["subsequent"]) == 1
    assert memory["subsequent"][0]["line_id"] == line2
    assert memory["subsequent"][0]["line_name"] == "Panel Tamper"
    # the first cause is NOT re-added to subsequent, and never overwritten
    assert not any(e["line_id"] == line1 for e in memory["subsequent"])

    assert tags.get_value(f"Security.Zone.{zone_id}.AlarmMemoryActive") is True
    assert tags.get_value(f"Security.Zone.{zone_id}.AlarmMemoryFirstCauseLine") == line1


def test_alarm_memory_survives_disarm_but_clears_only_on_explicit_command(im, tags, audit):
    """Task 3: "Po rozbrojeniu informacja o alarmie NIE MOZE zniknac bez
    sladu... az do JAWNEGO skasowania przez operatora." + "Kasowanie:
    poziom Operator lub wyzszy, zapisywane do historii alarmowej i
    dziennika audytowego."""
    zone_id = _add_zone(im)
    line_id = _add_line(im, zone_id, tag="DI1", line_type=LineType.INSTANT, name="Front Door")
    im.arm_zone(zone_id, actor="Operator")
    tags.update_tag("DI1", False)
    assert im.get_alarm_memory(zone_id)["active"] is True

    im.disarm_zone(zone_id, actor="Operator")
    memory = im.get_alarm_memory(zone_id)
    assert memory["active"] is True  # NOT cleared by disarm
    assert memory["first_cause_line_id"] == line_id

    # User (below Operator) cannot clear it
    assert im.clear_alarm_memory(zone_id, actor="User", level=AccessLevel.USER) is False
    assert im.get_alarm_memory(zone_id)["active"] is True

    # Operator can
    assert im.clear_alarm_memory(zone_id, actor="Operator", level=AccessLevel.OPERATOR) is True
    memory = im.get_alarm_memory(zone_id)
    assert memory["active"] is False
    assert memory["first_cause_line_id"] is None
    assert tags.get_value(f"Security.Zone.{zone_id}.AlarmMemoryActive") is False
    assert any(e[0] == "INTRUSION_ALARM_MEMORY_CLEARED" for e in audit.entries)

    # idempotent - clearing an already-inactive memory is a no-op, no duplicate entry
    entries_before = len(audit.entries)
    assert im.clear_alarm_memory(zone_id, actor="Operator", level=AccessLevel.OPERATOR) is False
    assert len(audit.entries) == entries_before


def test_alarm_memory_survives_a_restart(bus, tags, pm, audit, history):
    im1 = IntrusionManager(bus, tags, pm, audit, history)
    zone_id = im1.add_zone("Zone1", 0.0, 0.0)
    line_id = im1.add_line("Front Door", zone_id, "DI1", NORMAL_STATE_NC, LineType.INSTANT)
    im1.arm_zone(zone_id, actor="Operator")
    tags.update_tag("DI1", False)
    assert im1.get_alarm_memory(zone_id)["active"] is True
    im1.disarm_zone(zone_id, actor="Operator")
    tags.update_tag("DI1", True)  # secure again - a fresh instance re-seeding must not re-alarm

    bus2 = EventBus()
    tags2 = TagManager(bus2)
    for i in range(1, 9):
        tags2.add_tag(f"DI{i}", True, TagType.BOOL, source="HARDWARE")
    im2 = IntrusionManager(bus2, tags2, pm, audit, history)  # "restart": same project data, fresh instance

    memory = im2.get_alarm_memory(zone_id)
    assert memory["active"] is True
    assert memory["first_cause_line_id"] == line_id
    assert tags2.get_value(f"Security.Zone.{zone_id}.AlarmMemoryActive") is True

    assert im2.clear_alarm_memory(zone_id, actor="Operator") is True
    assert im2.get_alarm_memory(zone_id)["active"] is False


def test_alarm_memory_unknown_zone_returns_inactive_snapshot(im):
    assert im.get_alarm_memory("Z999") == {
        "active": False, "first_cause_line_id": None, "first_cause_line_name": None,
        "first_cause_reason": None, "first_cause_at": None, "subsequent": [],
    }


# --- walk-test mode ----------------------------------------------------------

def test_walk_test_violation_does_not_alarm_but_is_observed(im, tags, audit):
    """Task 4: "naruszenia sa rejestrowane i pokazywane na ekranie - NIE
    wywoluja alarmu ani nie zmieniaja stanu strefy"."""
    zone_id = _add_zone(im)
    line_id = _add_line(im, zone_id, tag="DI1", line_type=LineType.INSTANT, name="Front Door")
    im.arm_zone(zone_id, actor="Operator")

    assert im.start_walk_test(zone_id, actor="Engineer", level=AccessLevel.ENGINEER) is True
    assert im.is_walk_test_active(zone_id) is True
    assert tags.get_value(f"Security.Zone.{zone_id}.WalkTestActive") is True

    tags.update_tag("DI1", False)  # would normally alarm an ARMED INSTANT line
    assert im.get_zone_state(zone_id) == ZoneState.ARMED  # unaffected
    assert tags.get_value("Security.System.Alarm") is False
    assert tags.get_value(f"Security.Line.{line_id}.Violated") is True  # still shown on screen

    status = im.get_walk_test_status(zone_id)
    assert status["active"] is True
    confirmed = {l["id"]: l for l in status["lines"]}
    assert confirmed[line_id]["confirmed"] is True
    assert confirmed[line_id]["count"] == 1
    assert confirmed[line_id]["last_at"] is not None


def test_walk_test_line_fault_still_alarms(im, tags, audit):
    """Task 4: "WAZNE: w trybie chodzenia AWARIE LINII... maja nadal
    alarmowac normalnie. Tryb wylacza reakcje na naruszenia, nie na
    awarie."""
    tags.add_tag("AI7", 50.0, TagType.REAL, source="HARDWARE")
    zone_id = _add_zone(im)
    line_id = im.add_line("Perimeter", zone_id, "AI7", NORMAL_STATE_NC, LineType.INSTANT,
                           input_mode=LineInputMode.PARAMETRIZED, parametrization=LineParametrization.DEOL)
    im.start_walk_test(zone_id, actor="Engineer", level=AccessLevel.ENGINEER)

    tags.update_tag("AI7", 75.0)  # TAMPER
    assert im.get_zone_state(zone_id) == ZoneState.ALARM  # a fault alarms regardless of walk-test
    assert any(e[0] == "INTRUSION_ALARM" for e in audit.entries)


def test_walk_test_stop_returns_confirmed_and_silent_summary(im, tags, audit):
    zone_id = _add_zone(im)
    line1 = _add_line(im, zone_id, tag="DI1", line_type=LineType.INSTANT, name="Front Door")
    line2 = _add_line(im, zone_id, tag="DI2", line_type=LineType.INSTANT, name="Back Door")
    im.start_walk_test(zone_id, actor="Engineer", level=AccessLevel.ENGINEER)

    tags.update_tag("DI1", False)  # only line1 reacts

    summary = im.stop_walk_test(zone_id, actor="Engineer", level=AccessLevel.ENGINEER)
    assert summary is not None
    assert [c["line_id"] for c in summary["confirmed"]] == [line1]
    assert [s["line_id"] for s in summary["silent"]] == [line2]
    assert im.is_walk_test_active(zone_id) is False
    assert tags.get_value(f"Security.Zone.{zone_id}.WalkTestActive") is False
    assert any(e[0] == "INTRUSION_WALK_TEST_ENDED" for e in audit.entries)

    # already stopped - refuses/returns None, no duplicate entry
    entries_before = len(audit.entries)
    assert im.stop_walk_test(zone_id, actor="Engineer", level=AccessLevel.ENGINEER) is None
    assert len(audit.entries) == entries_before


def test_walk_test_auto_expires_after_configured_duration(im, tags, audit):
    zone_id = _add_zone(im)
    _add_line(im, zone_id, tag="DI1", line_type=LineType.INSTANT)
    assert im.start_walk_test(zone_id, actor="Engineer", level=AccessLevel.ENGINEER, duration_seconds=0.15) is True
    assert im.is_walk_test_active(zone_id) is True

    time.sleep(0.5)

    assert im.is_walk_test_active(zone_id) is False
    assert tags.get_value(f"Security.Zone.{zone_id}.WalkTestActive") is False
    entry = next(e for e in audit.entries if e[0] == "INTRUSION_WALK_TEST_ENDED")
    assert "timeout" in entry[2].lower()


def test_walk_test_requires_engineer_level(im):
    zone_id = _add_zone(im)
    assert im.start_walk_test(zone_id, actor="Operator", level=AccessLevel.OPERATOR) is False
    assert im.is_walk_test_active(zone_id) is False


def test_walk_test_cannot_start_twice_on_the_same_zone(im, tags):
    zone_id = _add_zone(im)
    assert im.start_walk_test(zone_id, actor="Engineer", level=AccessLevel.ENGINEER) is True
    assert im.start_walk_test(zone_id, actor="Engineer", level=AccessLevel.ENGINEER) is False
    im.stop_walk_test(zone_id, actor="Engineer", level=AccessLevel.ENGINEER)


# --- alarm event history (via the optional alarm_history_logger hook) ------

def test_alarm_events_reach_the_history_logger(im, tags, history):
    """Task 5's own event list, spot-checked: arm, violation (with zone
    state), alarm (first cause), disarm, bypass."""
    zone_id = _add_zone(im)
    line_id = _add_line(im, zone_id, tag="DI1", line_type=LineType.INSTANT, name="Front Door")

    im.bypass_line(line_id, True, actor="Engineer", level=AccessLevel.ENGINEER)
    im.bypass_line(line_id, False, actor="Engineer", level=AccessLevel.ENGINEER)
    im.arm_zone(zone_id, actor="Operator")
    tags.update_tag("DI1", False)
    im.disarm_zone(zone_id, actor="Operator")

    event_types = [e["event_type"] for e in history.entries]
    assert "INTRUSION_LINE_BYPASS_ON" in event_types
    assert "INTRUSION_LINE_BYPASS_OFF" in event_types
    assert "INTRUSION_ZONE_ARMED" in event_types
    assert "INTRUSION_LINE_VIOLATED" in event_types
    assert "INTRUSION_ALARM" in event_types
    assert "INTRUSION_ZONE_DISARMED" in event_types
    violated_entry = next(e for e in history.entries if e["event_type"] == "INTRUSION_LINE_VIOLATED")
    assert violated_entry["zone_id"] == zone_id
    assert violated_entry["line_id"] == line_id
    assert "ARMED" in violated_entry["detail"]  # "w jakim stanie strefy"


def test_no_alarm_history_logger_wired_up_is_inert(bus, tags, pm, audit):
    """Task's own "brak konfiguracji = brak bledu" stance, same as
    audit_logger=None already being fully optional everywhere in this
    module."""
    im = IntrusionManager(bus, tags, pm, audit)  # no alarm_history_logger
    zone_id = im.add_zone("Z", 0, 0)
    im.add_line("L", zone_id, "DI1", NORMAL_STATE_NC, LineType.INSTANT)
    im.arm_zone(zone_id, actor="Operator")
    tags.update_tag("DI1", False)  # alarms - must not raise despite no history logger
    assert im.get_zone_state(zone_id) == ZoneState.ALARM
    assert im.query_alarm_history() == []
    assert im.get_history_retention_config() == {"max_events": 0, "max_days": 0}
