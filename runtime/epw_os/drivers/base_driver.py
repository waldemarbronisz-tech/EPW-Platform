class BaseDriver:
    def __init__(self, name: str, event_bus):
        self.name = name
        self.event_bus = event_bus
        self.is_running = False

    def start(self):
        self.is_running = True

    def stop(self):
        self.is_running = False

    def write_tag(self, tag_name: str, value: any) -> bool:
        return False

    def get_comm_stats(self):
        """Task: "ekran diagnostyczny komunikacji szeregowej... dane maja
        pochodzic z warstwy sterownikow przez neutralny interfejs - tak,
        zeby ModbusDriver mogl je dostarczac bez zmiany tej strony."
        This method (together with reset_comm_stats() below) IS that
        interface - page_bus_diagnostics.py calls only these two, never
        anything simulator- or Modbus-specific.

        Returns {device_id: DeviceCommStats} (see
        epw_os/core/comm_diagnostics.py) for every device this driver
        currently has anything to report for. Base default: an empty
        dict - a driver that hasn't implemented this yet (or genuinely
        has nothing to report) shows as "no data" on the diagnostics
        page rather than crashing it; see SimulatorDriver for a real
        implementation, and SESSION_REPORT.md for the interface a
        future ModbusDriver is expected to implement the same way."""
        return {}

    def reset_comm_stats(self, device_id: str = None):
        """Neutral interface counterpart to get_comm_stats() - zero the
        counters for one device, or every device if device_id is None.
        Base default: a no-op (nothing to reset)."""
        pass

    def set_comm_suspended(self, device_id: str, suspended: bool):
        """Neutral interface counterpart to get_comm_stats() (Task:
        scenariusz 2 - "utrata komunikacji z urzadzeniem"). Presentation
        Mode's "device_comm" step needs SafetyKernel's real, genuine
        3-missed-cycle detection to fire - not a faked Safety.<id>.Fault
        tag write - so this tells a driver to simply stop reporting a
        healthy comm heartbeat for one device, the same way a device
        that really stopped answering would look from here. Base
        default: a no-op - a driver that hasn't implemented this (or a
        real ModbusDriver, where "suspending" comm isn't something
        software can fake) simply never goes offline this way; the
        scenario step just has no visible effect rather than crashing."""
        pass

    def is_comm_suspended(self, device_id: str) -> bool:
        """Read-only counterpart to set_comm_suspended() above. Base
        default: never suspended."""
        return False

    def is_alive(self) -> bool:
        """Read-only liveness query for safety_kernel.py's health checks
        ("watek sterownika nie zyje" criterion) - pure state inspection,
        no side effects, does not change how this or any driver actually
        communicates. Base default: a driver with no background thread
        of its own is "alive" exactly when it's marked running.
        Subclasses that run their own thread (see SimulatorDriver)
        override this to check that thread directly, since is_running
        alone can't detect a thread that died without resetting it."""
        return self.is_running
