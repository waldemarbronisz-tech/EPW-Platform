"""COMM.* - communication with the project's devices, counted by the
controller itself as the Modbus master (register group COMM).

Per device (pattern COMM.<device_id>.*, one instance per card of the
project):
  ONLINE    the device answered within its watchdog time (DeviceManager
            status ONLINE);
  OFFLINE   not ONLINE - never seen, or lost;
  FAULT     lost after having answered (status COMM_FAILURE) - the
            watchdog fired;
  TIMEOUT   the last thing that happened on the wire for this device
            was a timeout and nothing succeeded since;
  DEGRADED  online, but the driver counted errors (timeout, CRC, invalid
            reply) in the last DEGRADED_WINDOW_S seconds - it answers,
            not cleanly.
Over all devices:
  ALL_OK, ANY_DEVICE_OFFLINE, ANY_DEVICE_FAULT, LINK_DEGRADED;
  BUS_FAULT  the Modbus transport cannot be opened, the driver thread
             died, or EVERY device on the bus is silent (one card silent
             is that card; all of them at once is the bus);
  RS485_FAULT / ETHERNET_FAULT - BUS_FAULT, named by the bus type.

Every value comes from what the driver layer already records for the
Bus Diagnostics page (CommDiagnostics) and from DeviceManager's watchdog
- no second notion of "online" is invented here. DeviceManager only
re-checks its watchdogs when SOME device reports a good poll; when every
device goes silent nothing would ever flip, so a read here runs the
check itself, throttled.

The catalogue's older per-device diagnostics <dev>.ONLINE / <dev>.FAULT
/ <dev>.SAFE_PATH_OK (category "Komunikacja", from before the register)
are served here too, from the same facts: they were claimed served and
nothing answered them.
"""
import time

from epw_os.core.comm_diagnostics import ERROR_TIMEOUT
from epw_os.core.device_manager import DeviceStatus

DEGRADED_WINDOW_S = 30.0
WATCHDOG_CHECK_INTERVAL_S = 0.25

_DEVICE_SUFFIXES = ("ONLINE", "OFFLINE", "FAULT", "TIMEOUT", "DEGRADED")
_SYSTEM = ("COMM.ALL_OK", "COMM.ANY_DEVICE_OFFLINE", "COMM.ANY_DEVICE_FAULT", "COMM.BUS_FAULT",
           "COMM.RS485_FAULT", "COMM.ETHERNET_FAULT", "COMM.LINK_DEGRADED")
_LEGACY_SUFFIXES = ("ONLINE", "FAULT", "SAFE_PATH_OK")


def _split(signal_id: str):
    """COMM.<device_id>.<suffix> -> (device_id, suffix), else None."""
    parts = signal_id.split(".")
    if len(parts) == 3 and parts[0] == "COMM" and parts[2] in _DEVICE_SUFFIXES and parts[1]:
        return parts[1], parts[2]
    return None


class CommSignals:
    def __init__(self, core):
        self.core = core
        self._last_watchdog_check = 0.0

    # --- collaborators -------------------------------------------------------------------

    def _get(self, name, default=None):
        return getattr(self.core, name, default) if self.core is not None else default

    def _devices(self) -> dict:
        """{device_id: info} for the PROJECT's devices - the cards, never
        the panel's legacy simulated cabinet devices."""
        manager = self._get("device_manager")
        if manager is None:
            return {}
        self._check_watchdogs(manager)
        project_ids = self._project_device_ids()
        return {dev_id: info for dev_id, info in dict(manager.devices).items()
                if project_ids is None or dev_id in project_ids}

    def _project_device_ids(self):
        pm = self._get("project_manager")
        config = getattr(pm, "config", None)
        if not isinstance(config, dict):
            return None
        return {dev.get("id") for dev in config.get("devices", []) if dev.get("id")}

    def _check_watchdogs(self, manager):
        now = time.monotonic()
        if now - self._last_watchdog_check < WATCHDOG_CHECK_INTERVAL_S:
            return
        self._last_watchdog_check = now
        check = getattr(manager, "check_watchdogs", None)
        if callable(check):
            check()

    def _stats(self) -> dict:
        """{device_id: DeviceCommStats} from every driver that has any."""
        stats = {}
        manager = self._get("driver_manager")
        drivers = list(getattr(manager, "drivers", {}).values()) if manager is not None else []
        modbus = self._get("modbus_driver")
        if modbus is not None and modbus not in drivers:
            drivers.append(modbus)
        for driver in drivers:
            getter = getattr(driver, "get_comm_stats", None)
            if callable(getter):
                try:
                    stats.update(getter() or {})
                except Exception:  # noqa: BLE001 - a driver that cannot report is simply silent here
                    pass
        return stats

    # --- per device -----------------------------------------------------------------------

    def _status(self, device_id: str):
        info = self._devices().get(device_id)
        return info.get("status") if info else None

    def _online(self, device_id: str) -> bool:
        return self._status(device_id) == DeviceStatus.ONLINE

    def _fault(self, device_id: str) -> bool:
        return self._status(device_id) == DeviceStatus.COMM_FAILURE

    def _timeout(self, device_id: str) -> bool:
        stat = self._stats().get(device_id)
        if stat is None or not stat.recent_errors:
            return False
        last = stat.recent_errors[-1]
        if last.error_type != ERROR_TIMEOUT:
            return False
        return stat.last_success_time is None or last.timestamp >= stat.last_success_time

    def _degraded(self, device_id: str, now: float = None) -> bool:
        if not self._online(device_id):
            return False
        stat = self._stats().get(device_id)
        if stat is None:
            return False
        now = time.time() if now is None else now
        return any(now - err.timestamp <= DEGRADED_WINDOW_S for err in stat.recent_errors)

    def _safe_path_ok(self, device_id: str) -> bool:
        tags = self._get("tag_manager")
        if tags is None:
            return False
        return bool(tags.get_value(f"Safety.{device_id}.Healthy"))

    # --- the bus --------------------------------------------------------------------------

    def _bus_transport(self) -> str:
        driver = self._get("modbus_driver")
        bus = getattr(driver, "_bus", None) or {}
        return str(bus.get("transport") or "RTU").upper()

    def _modbus_device_ids(self) -> set:
        ids = self._get("_modbus_card_ids", None)
        return set(ids or [])

    def _bus_fault(self) -> bool:
        driver = self._get("modbus_driver")
        if driver is None:
            return False
        if getattr(driver, "unavailable_reason", None):
            return True
        manager = self._get("driver_manager")
        if getattr(manager, "is_running", False) and getattr(driver, "is_running", False):
            alive = getattr(driver, "is_alive", None)
            if callable(alive) and not alive():
                return True
        devices = self._devices()
        on_bus = [dev_id for dev_id in devices if dev_id in self._modbus_device_ids()]
        if not on_bus:
            return False
        # Every card on the bus silent at once: the bus, not the cards.
        return all(devices[dev_id].get("status") != DeviceStatus.ONLINE for dev_id in on_bus)

    # --- the interface --------------------------------------------------------------------

    def serves(self, signal_id: str) -> bool:
        if signal_id in _SYSTEM or _split(signal_id) is not None:
            return True
        parts = signal_id.split(".")
        if len(parts) == 2 and parts[0] and parts[1] in _LEGACY_SUFFIXES:
            # <dev>.ONLINE/FAULT/SAFE_PATH_OK: the catalogue generates them
            # for the project's cards; with no project to check against
            # (the claims test, a bare source) the shape alone decides.
            ids = self._project_device_ids()
            return ids is None or parts[0] in ids
        return False

    def read(self, signal_id: str):
        split = _split(signal_id)
        if split is not None:
            device_id, suffix = split
            if suffix == "ONLINE":
                return self._online(device_id)
            if suffix == "OFFLINE":
                return not self._online(device_id)
            if suffix == "FAULT":
                return self._fault(device_id)
            if suffix == "TIMEOUT":
                return self._timeout(device_id)
            return self._degraded(device_id)
        if signal_id in _SYSTEM:
            devices = self._devices()
            online = {dev_id: info.get("status") == DeviceStatus.ONLINE for dev_id, info in devices.items()}
            degraded = any(self._degraded(dev_id) for dev_id in devices)
            if signal_id == "COMM.ALL_OK":
                return bool(devices) and all(online.values()) and not degraded
            if signal_id == "COMM.ANY_DEVICE_OFFLINE":
                return any(not ok for ok in online.values())
            if signal_id == "COMM.ANY_DEVICE_FAULT":
                return any(info.get("status") == DeviceStatus.COMM_FAILURE for info in devices.values())
            if signal_id == "COMM.LINK_DEGRADED":
                return degraded
            bus_fault = self._bus_fault()
            if signal_id == "COMM.BUS_FAULT":
                return bus_fault
            if signal_id == "COMM.RS485_FAULT":
                return bus_fault and self._bus_transport() != "TCP"
            return bus_fault and self._bus_transport() == "TCP"
        parts = signal_id.split(".")
        if len(parts) == 2:
            device_id, suffix = parts
            if suffix == "ONLINE":
                return self._online(device_id)
            if suffix == "FAULT":
                return self._fault(device_id)
            if suffix == "SAFE_PATH_OK":
                return self._safe_path_ok(device_id)
        return None
