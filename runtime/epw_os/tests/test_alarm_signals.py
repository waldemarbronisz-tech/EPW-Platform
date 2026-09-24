"""Signal register etap 5: ALM.* and REQ.ALM.* (core/alarm_signals.py)
over the process protections the controller computes itself
(core/process_protection_manager.py) and the AlarmManager's lifecycle."""
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

os.environ["EPW_TESTING"] = "1"

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core.access_manager import AccessLevel  # noqa: E402
from epw_os.core.alarm_manager import AlarmManager, AlarmState  # noqa: E402
from epw_os.core.alarm_signals import TEST_ALARM_ID, AlarmSignals, process_alarm_id  # noqa: E402
from epw_os.core.events import EventBus  # noqa: E402
from epw_os.core.logic_runtime import SystemSignalSource, TagIOProvider  # noqa: E402
from epw_os.core.process_protection_manager import ProcessProtectionManager  # noqa: E402
from epw_os.core.tag_manager import TagManager, TagType  # noqa: E402
from shared.logic import system_signals  # noqa: E402


class _Audit:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))


class _ProjectManager:
    def __init__(self, protections):
        self._protections = list(protections)

    def get_process_protections(self):
        return self._protections

    def set_process_protections(self, data):
        self._protections = list(data)

    def get_analog_points(self):
        return [{"tag": "ELA1.AI.1", "description": "Temperatura"}]

    def save_project(self):
        pass


def _core(protections=(), with_manager=True, features=None):
    bus = EventBus()
    tags = TagManager(bus)
    tags.add_tag("ELA1.AI.1", 50.0, TagType.REAL, source="HARDWARE")
    alarms = AlarmManager(bus)
    pm = _ProjectManager(protections)
    core = SimpleNamespace(event_bus=bus, tag_manager=tags, alarm_manager=alarms, project_manager=pm,
                           audit_logger=_Audit(), process_protection_manager=None,
                           enabled_features=features if features is not None else {"protection_process": True})
    if with_manager:
        core.process_protection_manager = ProcessProtectionManager(bus, tags, pm, core.audit_logger, alarm_manager=alarms)
    return core


_PP1 = {"id": "PP1", "name": "Temperatura kotla", "analog_tag": "ELA1.AI.1", "upper_threshold": 80.0,
        "lower_threshold": 10.0, "hysteresis": 2.0, "delay_seconds": 0.0, "enabled": True}


def test_a_process_protection_that_trips_is_an_alarm_with_the_registers_lifecycle():
    core = _core([_PP1])
    system = SystemSignalSource(sources=[AlarmSignals(core)])
    read = system.read
    assert read("ALM.PROCESS_PP1.ACTIVE") is False and read("ALM.ANY_ACTIVE") is False and read("ALM.NEW_ALARM") is False
    core.tag_manager.publish_from_driver("ELA1.AI.1", 95.0)
    assert core.tag_manager.get_value("Process.PP1.Exceeded") is True
    alarm = next(a for a in core.alarm_manager.get_active_alarms() if a.id == process_alarm_id("PP1"))
    assert alarm.priority == 3 and "Temperatura kotla" in alarm.message and "95.0" in alarm.message
    assert read("ALM.PROCESS_PP1.ACTIVE") is True and read("ALM.PROCESS_PP1.ACKNOWLEDGED") is False
    assert read("ALM.PROCESS_PP1.LATCHED") is False
    assert read("ALM.ANY_ACTIVE") is True and read("ALM.ANY_UNACK") is True and read("ALM.NEW_ALARM") is True
    core.alarm_manager.acknowledge_alarm(process_alarm_id("PP1"), "Operator")
    assert read("ALM.PROCESS_PP1.ACKNOWLEDGED") is True and read("ALM.NEW_ALARM") is False and read("ALM.ANY_UNACK") is False
    # back inside the band (past the hysteresis): the condition is gone, the alarm is not a latch (it was acknowledged)
    core.tag_manager.publish_from_driver("ELA1.AI.1", 50.0)
    assert read("ALM.PROCESS_PP1.ACTIVE") is False and read("ALM.PROCESS_PP1.LATCHED") is False and read("ALM.ANY_ACTIVE") is False
    # a second trip nobody acknowledges, then the condition clears: the alarm memory = LATCHED
    core.tag_manager.publish_from_driver("ELA1.AI.1", 5.0)
    core.tag_manager.publish_from_driver("ELA1.AI.1", 50.0)
    assert read("ALM.PROCESS_PP1.ACTIVE") is False and read("ALM.PROCESS_PP1.LATCHED") is True and read("ALM.ANY_UNACK") is True
    assert read("ALM.NEW_ALARM") is False
    # every other alarm of the manager reads by its own id, the same way
    core.alarm_manager.trigger_alarm("DEVICE_COMM_ELA1", "ELA1 communication failure", priority=3)
    assert read("ALM.DEVICE_COMM_ELA1.ACTIVE") is True and read("ALM.DEVICE_COMM_ELA1.ACKNOWLEDGED") is False
    assert read("ALM.DEVICE_COMM_XYZ.ACTIVE") is False, "an alarm never raised reads FALSE, not an error"
    assert read("ALM.NEW_ALARM") is True


def test_the_aggregates_read_the_whole_alarm_manager_by_priority_and_the_horn_re_arms():
    core = _core([])
    signals = AlarmSignals(core)
    read = SystemSignalSource(sources=[signals]).read
    core.alarm_manager.trigger_alarm("NOTE", "low", priority=1)
    assert read("ALM.ANY_WARNING") is True and read("ALM.ANY_CRITICAL") is False and read("ALM.HORN_REQUIRED") is False
    core.alarm_manager.trigger_alarm("DEVICE_COMM_ELA1", "ELA1 communication failure", priority=3)
    assert read("ALM.HORN_REQUIRED") is True and read("ALM.ANY_CRITICAL") is False
    core.alarm_manager.trigger_alarm("ESTOP", "emergency stop", priority=4)
    assert read("ALM.ANY_CRITICAL") is True
    assert signals.execute("REQ.ALM.SILENCE_HORN", "LOGIC") is True
    assert read("ALM.HORN_REQUIRED") is False and read("ALM.ANY_UNACK") is True
    core.alarm_manager.trigger_alarm("PUMP", "pump fault", priority=3)      # a new alarm re-arms the horn
    assert read("ALM.HORN_REQUIRED") is True
    for alarm_id in ("NOTE", "DEVICE_COMM_ELA1", "ESTOP", "PUMP"):
        core.alarm_manager.acknowledge_alarm(alarm_id, "Operator")
    assert read("ALM.HORN_REQUIRED") is False and read("ALM.ANY_ACTIVE") is True and read("ALM.NEW_ALARM") is False


def test_ack_all_and_reset_do_different_things_and_both_are_audited():
    core = _core([_PP1])
    signals = AlarmSignals(core)
    read = SystemSignalSource(sources=[signals]).read
    core.tag_manager.publish_from_driver("ELA1.AI.1", 95.0)                 # PP1 active, unacknowledged
    core.alarm_manager.trigger_alarm("DEVICE_COMM_ELA1", "ELA1 communication failure", priority=3)
    core.alarm_manager.clear_alarm("DEVICE_COMM_ELA1")                       # cleared, unacknowledged = a latch
    assert read("ALM.ANY_UNACK") is True
    assert signals.execute("REQ.ALM.RESET", "LOGIC") is True
    assert core.audit_logger.entries[-1][0] == "ALARM_REQUEST" and "1 cleared alarm(s) reset" in core.audit_logger.entries[-1][2]
    assert core.alarm_manager._alarms["DEVICE_COMM_ELA1"].state == AlarmState.NORMAL
    assert read("ALM.PROCESS_PP1.ACTIVE") is True and read("ALM.PROCESS_PP1.ACKNOWLEDGED") is False, "a persisting condition is not a latch"
    assert signals.execute("REQ.ALM.ACK_ALL", "LOGIC") is True
    assert "1 alarm(s) acknowledged" in core.audit_logger.entries[-1][2]
    assert read("ALM.PROCESS_PP1.ACKNOWLEDGED") is True and read("ALM.ANY_UNACK") is False
    assert core.alarm_manager._alarms[process_alarm_id("PP1")].ack_user == "LOGIC"
    # no alarm manager at all: refused, with the reason in the audit log
    core.alarm_manager = None
    assert signals.execute("REQ.ALM.ACK_ALL", "LOGIC") is False
    assert core.audit_logger.entries[-1][0] == "ALARM_REQUEST_REFUSED" and "no alarm manager" in core.audit_logger.entries[-1][2]


def test_the_test_request_needs_an_engineer_raises_a_test_alarm_and_leaves_no_memory():
    core = _core([])
    signals = AlarmSignals(core)
    system = SystemSignalSource(sources=[signals])
    access = SimpleNamespace(level=AccessLevel.OPERATOR,
                             has_access=lambda req: AccessLevel._ORDER.index(AccessLevel.OPERATOR) >= AccessLevel._ORDER.index(req))
    io = TagIOProvider(core.tag_manager, access_manager=access, audit_logger=core.audit_logger, system_signals=system)
    io.write_system_signal("REQ.ALM.TEST", True)
    assert core.audit_logger.entries[-1][0] == "LOGIC_REQUEST_REFUSED" and "Engineer" in core.audit_logger.entries[-1][2]
    assert not core.alarm_manager.get_active_alarms()
    access.level = AccessLevel.ENGINEER
    access.has_access = lambda req: True
    io.write_system_signal("REQ.ALM.TEST", False)
    io.write_system_signal("REQ.ALM.TEST", True)
    assert [a.id for a in core.alarm_manager.get_active_alarms()] == [TEST_ALARM_ID]
    assert system.read("ALM.ANY_ACTIVE") is True and system.read("ALM.HORN_REQUIRED") is False   # priority 1: no horn
    assert signals.execute("REQ.ALM.TEST", "LOGIC") is False                                       # already running
    assert core.audit_logger.entries[-1][0] == "ALARM_REQUEST_REFUSED"
    deadline = time.time() + 6.0
    while time.time() < deadline and core.alarm_manager.get_active_alarms():
        time.sleep(0.1)
    assert not core.alarm_manager.get_active_alarms()
    assert core.alarm_manager._alarms[TEST_ALARM_ID].state == AlarmState.NORMAL, "a test leaves no alarm memory"
    assert system.read("ALM.ANY_UNACK") is False


def test_system_fault_names_a_module_that_should_run_and_a_protection_on_a_missing_point():
    core = _core([_PP1])
    read = SystemSignalSource(sources=[AlarmSignals(core)]).read
    assert read("ALM.SYSTEM_FAULT") is False
    core.tag_manager.remove_tag("ELA1.AI.1")
    assert read("ALM.SYSTEM_FAULT") is True
    missing = _core([_PP1], with_manager=False)
    assert SystemSignalSource(sources=[AlarmSignals(missing)]).read("ALM.SYSTEM_FAULT") is True
    not_wanted = _core([], with_manager=False, features={"protection_process": False})
    assert SystemSignalSource(sources=[AlarmSignals(not_wanted)]).read("ALM.SYSTEM_FAULT") is False


def test_the_catalogue_expands_one_alarm_per_process_protection_and_the_controller_answers_each():
    class _Project:
        settings = {}
        external_zones = []
        external_lines = []
        external_cards = []
        external_alarms = [{"id": "PROCESS_PP1", "name": "Temperatura kotla"}, {"id": "DEVICE_COMM_ELA1", "name": "Komunikacja z ELA1"}]

    ids = {s["id"]: s for s in system_signals.get_all_signals(_Project())}
    assert "ALM.PROCESS_PP1.ACTIVE" in ids and "ALM.DEVICE_COMM_ELA1.LATCHED" in ids and "ALM.<alarm_id>.ACTIVE" not in ids
    assert ids["ALM.PROCESS_PP1.ACTIVE"]["description"].endswith("- Temperatura kotla")
    signals = AlarmSignals(_core([_PP1]))
    for sid in ("ALM.PROCESS_PP1.ACTIVE", "ALM.DEVICE_COMM_ELA1.ACKNOWLEDGED", "ALM.ANY_ACTIVE", "REQ.ALM.ACK_ALL"):
        assert signals.serves(sid), sid
    assert not signals.serves("ALM.PROCESS_PP1.NOPE") and not signals.serves("ALM.NOPE")
    assert signals.read("ALM.DEVICE_COMM_ELA1.ACTIVE") is False, "an alarm the project has but nothing raised"
