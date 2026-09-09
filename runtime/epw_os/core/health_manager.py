from enum import Enum
import threading
from typing import Dict

class SubsystemState(Enum):
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    FAULT = "FAULT"
    STOPPING = "STOPPING"

class HealthManager:
    """
    Tracks and exposes the health of core subsystems for diagnostics and the API.
    """
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.event_bus.subscribe("device_status_changed", self._on_device_status)
        self._states: Dict[str, SubsystemState] = {
            "DATABASE": SubsystemState.STARTING,
            "HISTORIAN": SubsystemState.STARTING,
            "LOGIC_RUNTIME": SubsystemState.STARTING,
            "API": SubsystemState.STARTING,
            "DRIVERS": SubsystemState.STARTING
        }
        self._lock = threading.RLock()

    def _on_device_status(self, device_id: str, status: str):
        with self._lock:
            if status == "COMM_FAILURE":
                self._states["DRIVERS"] = SubsystemState.DEGRADED
            
    def update_subsystem(self, name: str, state: SubsystemState):
        with self._lock:
            self._states[name] = state
            
    def get_health(self) -> Dict[str, str]:
        with self._lock:
            return {k: v.value for k, v in self._states.items()}
