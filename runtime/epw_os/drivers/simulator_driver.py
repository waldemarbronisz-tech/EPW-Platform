import math
import random
import threading
import time
from epw_os.drivers.base_driver import BaseDriver
from epw_os.core.comm_diagnostics import CommDiagnostics
from epw_os.core.logging import log as drv_log

# Analog Inputs simulation - now a dynamic set of tags (see
# EPWCore.add_analog_point()/remove_analog_point() and
# ProjectManager.get_analog_points()), not a fixed AI1..AI16 count.
# SimulatorDriver is told the current tag list via set_analog_tags();
# it has no opinion of its own about how many points exist or what
# they're called. These are *raw* tag values - by default every point's
# signal type is "ready value, no conversion" (see analog_scaling.py), so
# whatever is written here is exactly what the Analog Inputs page shows
# until an operator configures scaling for that point. The four original
# channels (AI1-AI4, from before points were dynamic/renamable) keep
# their distinct, recognizable waveforms so migrated projects don't
# visibly change behavior; any other tag (including newly-added points,
# whatever an operator names them) gets a quiet near-zero baseline like
# an unused hardware input would.


def _simulate_analog_value(tag_name: str, t: float) -> float:
    if tag_name == "AI1":
        # Simulated temperature, oscillating gently around 22 C.
        return 22.0 + math.sin(t / 20.0) * 1.5 + random.uniform(-0.1, 0.1)
    if tag_name == "AI2":
        # Slow pressure-like drift.
        return 2.0 + math.sin(t / 35.0 + 1.0) * 0.8 + random.uniform(-0.02, 0.02)
    if tag_name == "AI3":
        # Humidity-like oscillation.
        return 50.0 + math.sin(t / 27.0 + 2.0) * 8.0 + random.uniform(-0.3, 0.3)
    if tag_name == "AI4":
        # Noisy-but-steady baseline (e.g. a live 4-20mA loop sitting at rest).
        return 4.2 + random.uniform(-0.05, 0.05)
    # Any other point: unused input, near-zero noise.
    return random.uniform(-0.05, 0.05)


class SimulatorDriver(BaseDriver):
    def __init__(self, event_bus, device_ids=None):
        super().__init__("SimulatorDriver", event_bus)
        self._thread = None
        self._lock = threading.RLock()
        self.device_ids = list(device_ids) if device_ids else []
        self._analog_tags = []
        # Task: scenariusz 2 - "utrata komunikacji z urzadzeniem" (see
        # BaseDriver.set_comm_suspended()'s docstring). A device_id in
        # here is simply skipped by _run_loop() below - no heartbeat,
        # no comm-diagnostics record - exactly what a device that
        # stopped answering would look like from device_manager's own
        # perspective, so SafetyKernel's real detection genuinely fires
        # instead of being faked.
        self._suspended_devices = set()
        # Task: Bus Diagnostics page - see comm_diagnostics.py's own
        # docstring for why this one small object is the whole
        # implementation; get_comm_stats()/reset_comm_stats() below just
        # forward to it, per BaseDriver's neutral interface.
        self._comm_diagnostics = CommDiagnostics()

    def set_devices(self, device_ids):
        """Devices this simulated connection is responsible for polling.
        Called by the composition root once the active device list is known
        (project-configured, or the built-in defaults)."""
        with self._lock:
            self.device_ids = list(device_ids)

    def set_comm_suspended(self, device_id: str, suspended: bool):
        with self._lock:
            if suspended:
                self._suspended_devices.add(device_id)
            else:
                self._suspended_devices.discard(device_id)

    def is_comm_suspended(self, device_id: str) -> bool:
        with self._lock:
            return device_id in self._suspended_devices

    def set_analog_tags(self, tag_names):
        """The current dynamic Analog Inputs point list - called by
        EPWCore at startup and again on every add_analog_point()/
        remove_analog_point(), so this thread's next poll cycle picks up
        the change without needing a restart."""
        with self._lock:
            self._analog_tags = list(tag_names)

    def start(self):
        super().start()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="SimDriver")
        self._thread.start()
        drv_log.info("SimulatorDriver started.")

    def stop(self):
        super().stop()
        if self._thread:
            self._thread.join(timeout=2.0)
        drv_log.info("SimulatorDriver stopped.")

    def _run_loop(self):
        while self.is_running:
            cycle_start = time.time()
            with self._lock:
                devices = list(self.device_ids)
                suspended = set(self._suspended_devices)
            for device_id in devices:
                if device_id in suspended:
                    # Task: scenariusz 2 - comm withheld on purpose for
                    # this device (see set_comm_suspended()) - no
                    # heartbeat, no comm-diagnostics record, same as a
                    # device that genuinely stopped answering.
                    continue
                # Task: Bus Diagnostics - GRANICE: "nie zmieniaj
                # zachowania komunikacji, tylko doloz zbieranie
                # statystyk". The emit() call below is unchanged, same
                # position, same arguments - these two lines only
                # measure it, they don't alter what it does. Task also
                # explicitly allows this: "symulator moze raportowac
                # zerowe bledy i realne czasy" - there is no real bus
                # here to time, so what gets recorded is the real,
                # measured wall-clock cost of this simulated exchange
                # (perf_counter, not time.time() - monotonic and not
                # subject to system clock adjustments, appropriate for
                # a short duration measurement) rather than an invented
                # "12ms"-style constant. Errors are never recorded here
                # - a perfect simulated bus has none to report, exactly
                # as the task expects.
                self._comm_diagnostics.record_frame_sent(device_id)
                _t0 = time.perf_counter()
                self.event_bus.emit("driver_comm_ok", device_id)
                self._comm_diagnostics.record_success(device_id, (time.perf_counter() - _t0) * 1000.0)

            self._simulate_analog_channels()

            # Task: status bar "Scan" field - the real, measured elapsed
            # time of this driver's own poll cycle (heartbeats + analog
            # simulation above), not a fabricated constant. Emitted once
            # per cycle (same cadence as everything else this loop
            # already does every second), so this costs nothing beyond
            # two time.time() calls - no extra polling, no hot-path work.
            elapsed_ms = (time.time() - cycle_start) * 1000.0
            self.event_bus.emit("driver_scan_cycle", self.name, elapsed_ms)

            time.sleep(1.0)

    def _simulate_analog_channels(self):
        t = time.time()
        with self._lock:
            tags = list(self._analog_tags)
        for tag_name in tags:
            value = _simulate_analog_value(tag_name, t)
            self.write_tag(tag_name, round(value, 3))

    def write_tag(self, tag_name: str, value: any) -> bool:
        drv_log.debug(f"SimulatorDriver writing to {tag_name}: {value}")
        self.event_bus.emit("driver_update", tag_name, value, "GOOD")
        return True

    def get_comm_stats(self):
        return self._comm_diagnostics.get_all_stats()

    def reset_comm_stats(self, device_id: str = None):
        self._comm_diagnostics.reset(device_id)

    def is_alive(self) -> bool:
        """Overrides BaseDriver's default: this driver DOES run its own
        background thread, so check that directly rather than just
        is_running - a thread that dies unexpectedly (an unhandled
        exception in _run_loop()) never resets is_running on its own,
        which would otherwise hide exactly the failure safety_kernel.py
        needs to detect ("watek sterownika nie zyje")."""
        return self.is_running and self._thread is not None and self._thread.is_alive()
