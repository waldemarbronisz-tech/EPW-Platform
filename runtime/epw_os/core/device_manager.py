from typing import Dict, Any, Optional
import time

class DeviceStatus:
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    COMM_FAILURE = "COMM_FAILURE"

class DeviceManager:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.devices: Dict[str, Dict[str, Any]] = {}
        
    def register_device(self, device_id: str, driver_id: str, timeout: float = 5.0):
        self.devices[device_id] = {
            "driver_id": driver_id,
            "status": DeviceStatus.OFFLINE,
            "last_comm": 0.0,
            "timeout": timeout
        }
        
    def update_comm(self, device_id: str):
        if device_id in self.devices:
            self.devices[device_id]["last_comm"] = time.time()
            if self.devices[device_id]["status"] != DeviceStatus.ONLINE:
                self.devices[device_id]["status"] = DeviceStatus.ONLINE
                self.event_bus.emit("device_status_changed", device_id, DeviceStatus.ONLINE)
                
    def check_watchdogs(self):
        now = time.time()
        for device_id, info in self.devices.items():
            if info["status"] == DeviceStatus.ONLINE and info["timeout"] > 0:
                if (now - info["last_comm"]) > info["timeout"]:
                    info["status"] = DeviceStatus.COMM_FAILURE
                    self.event_bus.emit("device_status_changed", device_id, DeviceStatus.COMM_FAILURE)
