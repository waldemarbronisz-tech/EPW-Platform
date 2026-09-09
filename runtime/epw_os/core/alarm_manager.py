from dataclasses import dataclass
from typing import Dict, List
import time
import threading
from enum import Enum

class AlarmState(Enum):
    NORMAL = "NORMAL"
    ACTIVE_UNACK = "ACTIVE_UNACK"
    ACTIVE_ACK = "ACTIVE_ACK"
    CLEARED_UNACK = "CLEARED_UNACK"

@dataclass
class Alarm:
    id: str
    message: str
    source_tag: str
    priority: int  # 1 = Low, 2 = Medium, 3 = High, 4 = Critical
    state: AlarmState
    activation_time: float
    clear_time: float = 0.0
    ack_time: float = 0.0
    ack_user: str = ""  # access level of whoever acknowledged (User/Operator/Engineer)
    
    @property
    def active(self):
        return self.state in (AlarmState.ACTIVE_UNACK, AlarmState.ACTIVE_ACK)
        
    @property
    def acknowledged(self):
        return self.state in (AlarmState.ACTIVE_ACK, AlarmState.NORMAL)

class AlarmManager:
    """
    Framework-independent AlarmManager.
    """
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self._alarms: Dict[str, Alarm] = {}
        self._lock = threading.RLock()

    def trigger_alarm(self, id: str, message: str, source_tag: str = "", priority: int = 2):
        with self._lock:
            if id not in self._alarms or not self._alarms[id].active:
                alarm = Alarm(
                    id=id, message=message, source_tag=source_tag, priority=priority,
                    state=AlarmState.ACTIVE_UNACK, activation_time=time.time()
                )
                self._alarms[id] = alarm
                self.event_bus.emit("alarm_triggered", alarm)

    def clear_alarm(self, id: str):
        with self._lock:
            if id in self._alarms and self._alarms[id].active:
                alarm = self._alarms[id]
                alarm.clear_time = time.time()
                if alarm.state == AlarmState.ACTIVE_UNACK:
                    alarm.state = AlarmState.CLEARED_UNACK
                else:
                    alarm.state = AlarmState.NORMAL
                self.event_bus.emit("alarm_cleared", alarm)

    def acknowledge_alarm(self, id: str, user: str = ""):
        with self._lock:
            if id in self._alarms:
                alarm = self._alarms[id]
                if alarm.state == AlarmState.ACTIVE_UNACK:
                    alarm.state = AlarmState.ACTIVE_ACK
                    alarm.ack_time = time.time()
                    alarm.ack_user = user
                    self.event_bus.emit("alarm_acknowledged", alarm)
                elif alarm.state == AlarmState.CLEARED_UNACK:
                    alarm.state = AlarmState.NORMAL
                    alarm.ack_time = time.time()
                    alarm.ack_user = user
                    self.event_bus.emit("alarm_acknowledged", alarm)

    def get_active_alarms(self) -> List[Alarm]:
        with self._lock:
            return [alarm for alarm in self._alarms.values() if alarm.active]

    def get_all_alarms(self) -> List[Alarm]:
        """Active alarms plus recently NORMAL/CLEARED_UNACK ones still
        held in memory - for a listing page where an operator should
        still see an alarm settle back to normal, not have it vanish the
        instant it clears."""
        with self._lock:
            return sorted(self._alarms.values(), key=lambda a: a.activation_time, reverse=True)
