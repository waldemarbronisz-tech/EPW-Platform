"""ALM.* and REQ.ALM.* - the process alarms (etap 5 of the signal register).

The source is what this controller COMPUTES itself: a process
protection (core/process_protection_manager.py) watches an analog point
against its band and, when it latches EXCEEDED, raises the alarm
PROCESS_<id> in the AlarmManager; the operator's acknowledgement and
the alarm's clearing are the AlarmManager's own lifecycle. This is not
an electrical protection path, so rule Z3 does not apply - the
threshold IS the controller's to compare.

Per process protection of the project (the catalogue pattern
ALM.<alarm_id>.*, expanded by Studio from the project's own list):

    ACTIVE        the condition holds now (alarm ACTIVE_UNACK or ACTIVE_ACK)
    ACKNOWLEDGED  the condition holds and someone acknowledged it (ACTIVE_ACK)
    LATCHED       the condition cleared but the alarm waits for an
                  acknowledgement (CLEARED_UNACK) - the alarm memory

Across the AlarmManager as a whole (every alarm it holds, the device
communication alarms included - the register says "agregacja
AlarmManager"):

    ANY_ACTIVE     any alarm active
    ANY_UNACK      any alarm not yet acknowledged (active or cleared)
    ANY_CRITICAL   any active alarm of priority 4 (Critical)
    ANY_WARNING    any active alarm of priority 1-2 (Low, Medium)
    NEW_ALARM      any alarm active and not yet acknowledged
    HORN_REQUIRED  an unacknowledged alarm of priority 3-4 exists and the
                   horn has not been silenced since the last new alarm
    SYSTEM_FAULT   the process protection module should run and does
                   not, or a protection watches a point that does not
                   exist / is not numeric

The requests, each validated and executed or refused with a reason in
the audit log (rule Z2): ACK_ALL, SILENCE_HORN and RESET at Operator,
TEST at Engineer.
"""
import threading

from epw_os.core.access_manager import AccessLevel
from epw_os.core.alarm_manager import AlarmState
from epw_os.core.logging import log

PROCESS_ALARM_PREFIX = "PROCESS_"
TEST_ALARM_ID = "ALM_TEST"
TEST_ALARM_SECONDS = 3.0
HORN_PRIORITY = 3        # High and Critical sound the horn
CRITICAL_PRIORITY = 4
WARNING_MAX_PRIORITY = 2

_AGGREGATES = ("ALM.ANY_ACTIVE", "ALM.ANY_UNACK", "ALM.ANY_CRITICAL", "ALM.ANY_WARNING", "ALM.NEW_ALARM",
               "ALM.HORN_REQUIRED", "ALM.SYSTEM_FAULT")
_INSTANCE_SUFFIXES = ("ACTIVE", "ACKNOWLEDGED", "LATCHED")
_REQUESTS = {
    "REQ.ALM.ACK_ALL": AccessLevel.OPERATOR,
    "REQ.ALM.SILENCE_HORN": AccessLevel.OPERATOR,
    "REQ.ALM.RESET": AccessLevel.OPERATOR,
    "REQ.ALM.TEST": AccessLevel.ENGINEER,
}


def process_alarm_id(protection_id: str) -> str:
    return f"{PROCESS_ALARM_PREFIX}{protection_id}"


def _instance(signal_id: str):
    """("PP1", "ACTIVE") for ALM.PP1.ACTIVE, else None."""
    parts = signal_id.split(".")
    if len(parts) == 3 and parts[0] == "ALM" and parts[1] and parts[2] in _INSTANCE_SUFFIXES:
        return parts[1], parts[2]
    return None


class AlarmSignals:
    def __init__(self, core):
        self.core = core
        self.horn_silenced = False
        bus = getattr(core, "event_bus", None) if core is not None else None
        if bus is not None:
            bus.subscribe("alarm_triggered", self._on_alarm_triggered)

    def _on_alarm_triggered(self, _alarm):
        # A new alarm re-arms the horn: a silence covers what was known,
        # not what comes next.
        self.horn_silenced = False

    # --- what the controller holds --------------------------------------------------------

    def _manager(self):
        return getattr(self.core, "alarm_manager", None) if self.core is not None else None

    def _alarms(self) -> list:
        manager = self._manager()
        getter = getattr(manager, "get_all_alarms", None)
        return list(getter()) if callable(getter) else []

    def _alarm(self, alarm_id: str):
        for alarm in self._alarms():
            if alarm.id == alarm_id:
                return alarm
        return None

    def _protections(self) -> list:
        pm = getattr(self.core, "project_manager", None) if self.core is not None else None
        getter = getattr(pm, "get_process_protections", None)
        try:
            return list(getter()) if callable(getter) else []
        except Exception:  # noqa: BLE001
            return []

    def _system_fault(self) -> bool:
        if self.core is None:
            return False
        features = getattr(self.core, "enabled_features", None) or {}
        manager = getattr(self.core, "process_protection_manager", None)
        try:
            from epw_os.core.feature_config import is_feature_enabled
            wanted = is_feature_enabled(features, "protection_process")
        except Exception:  # noqa: BLE001
            wanted = False
        if wanted and manager is None:
            return True
        tags = getattr(self.core, "tag_manager", None)
        get_tag = getattr(tags, "get_tag", None)
        if manager is None or not callable(get_tag):
            return False
        for protection in manager.get_protections():
            if not protection.get("enabled", True):
                continue
            tag = get_tag(protection.get("analog_tag", ""))
            if tag is None:
                return True
            try:
                float(tag.value)
            except (TypeError, ValueError):
                return True
        return False

    # --- the interface ----------------------------------------------------------------------

    def serves(self, signal_id: str) -> bool:
        return signal_id in _AGGREGATES or signal_id in _REQUESTS or _instance(signal_id) is not None

    def read(self, signal_id: str):
        instance = _instance(signal_id)
        if instance is not None:
            alarm = self._alarm(process_alarm_id(instance[0]))
            if alarm is None:
                return False
            if instance[1] == "ACTIVE":
                return alarm.state in (AlarmState.ACTIVE_UNACK, AlarmState.ACTIVE_ACK)
            if instance[1] == "ACKNOWLEDGED":
                return alarm.state == AlarmState.ACTIVE_ACK
            return alarm.state == AlarmState.CLEARED_UNACK
        if signal_id not in _AGGREGATES:
            return None
        alarms = self._alarms()
        active = [a for a in alarms if a.state in (AlarmState.ACTIVE_UNACK, AlarmState.ACTIVE_ACK)]
        unack = [a for a in alarms if a.state in (AlarmState.ACTIVE_UNACK, AlarmState.CLEARED_UNACK)]
        if signal_id == "ALM.ANY_ACTIVE":
            return bool(active)
        if signal_id == "ALM.ANY_UNACK":
            return bool(unack)
        if signal_id == "ALM.ANY_CRITICAL":
            return any(a.priority >= CRITICAL_PRIORITY for a in active)
        if signal_id == "ALM.ANY_WARNING":
            return any(a.priority <= WARNING_MAX_PRIORITY for a in active)
        if signal_id == "ALM.NEW_ALARM":
            return any(a.state == AlarmState.ACTIVE_UNACK for a in alarms)
        if signal_id == "ALM.HORN_REQUIRED":
            return (not self.horn_silenced) and any(a.priority >= HORN_PRIORITY for a in unack)
        return self._system_fault()

    # --- the requests -----------------------------------------------------------------------

    def required_level(self, signal_id: str):
        return _REQUESTS.get(signal_id)

    def _audit(self, event, actor, detail, success=True):
        audit = getattr(self.core, "audit_logger", None) if self.core is not None else None
        if audit is not None:
            audit.record(event, actor, detail, success=success)

    def execute(self, signal_id: str, actor: str, level: str = None) -> bool:
        if signal_id not in _REQUESTS:
            return False
        manager = self._manager()
        if manager is None:
            self._audit("ALARM_REQUEST_REFUSED", actor, f"{signal_id}: this controller has no alarm manager",
                        success=False)
            log.warning(f"{signal_id} from {actor} refused: no alarm manager.")
            return False
        if signal_id == "REQ.ALM.ACK_ALL":
            targets = [a for a in self._alarms() if a.state in (AlarmState.ACTIVE_UNACK, AlarmState.CLEARED_UNACK)]
            for alarm in targets:
                manager.acknowledge_alarm(alarm.id, user=actor)
            detail = f"{signal_id}: {len(targets)} alarm(s) acknowledged"
        elif signal_id == "REQ.ALM.SILENCE_HORN":
            self.horn_silenced = True
            detail = f"{signal_id}: horn silenced until the next new alarm"
        elif signal_id == "REQ.ALM.RESET":
            # The latches: alarms whose condition has already cleared and
            # that only wait for an acknowledgement. An alarm whose
            # condition persists is not a latch and stays as it is.
            targets = [a for a in self._alarms() if a.state == AlarmState.CLEARED_UNACK]
            for alarm in targets:
                manager.acknowledge_alarm(alarm.id, user=actor)
            self.horn_silenced = True
            detail = f"{signal_id}: {len(targets)} cleared alarm(s) reset, horn silenced"
        else:
            if self._alarm(TEST_ALARM_ID) is not None and self._alarm(TEST_ALARM_ID).state != AlarmState.NORMAL:
                self._audit("ALARM_REQUEST_REFUSED", actor, f"{signal_id}: a test is already running", success=False)
                log.warning(f"{signal_id} from {actor} refused: a test is already running.")
                return False
            manager.trigger_alarm(TEST_ALARM_ID, f"Alarm system test requested by {actor}", source_tag="",
                                  priority=1)
            timer = threading.Timer(TEST_ALARM_SECONDS, self._finish_test, args=(actor,))
            timer.daemon = True
            timer.start()
            detail = f"{signal_id}: test alarm {TEST_ALARM_ID} raised for {TEST_ALARM_SECONDS:.0f} s"
        self._audit("ALARM_REQUEST", actor, detail, success=True)
        log.info(f"{actor}: {detail}.")
        return True

    def _finish_test(self, actor: str):
        manager = self._manager()
        if manager is None:
            return
        manager.clear_alarm(TEST_ALARM_ID)
        manager.acknowledge_alarm(TEST_ALARM_ID, user=actor)   # a test leaves no alarm memory behind
