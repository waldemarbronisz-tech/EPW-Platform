"""SafetyKernel - system health DETECTION and SIGNALING only.

Project-wide governing principle: "the screen informs, the hardware
protects" (ekran informuje, sprzet chroni). This module runs in Python
on an Orange Pi - it dies right along with the Pi, so it can never BE a
safety function, only a sensor that a real safety function (relays,
watchdog hardware, or - once it exists - the user's own Logic Studio
program) can read. Concretely, that means:

  - check_system_health() only ever DETECTS and SIGNALS (tags, an
    AlarmManager alarm, an audit record). It never decides what should
    happen about an unhealthy device - that decision belongs to the
    user logic that will eventually run in Logic Studio (not built yet -
    logic_engine.py doesn't load a runtime today).
  - enforce_safe_state() is the ONE exception, and it stays deliberately
    narrow: it blocks *new* commands from being issued while the system
    is unhealthy, and records that fact. It NEVER writes to a driver or
    an output tag itself - doing that would BE the safety reaction this
    module is explicitly not allowed to own.

validate_command_safety() (pre-existing) already gates every command
through EMERGENCY_STOP and per-target device communication status
(Task: "luka w blokadzie komend... dla urzadzen skonfigurowanych w
projekcie" - originally checked only for an active COMM_FAILURE, and
only ever worked for the four hardcoded default devices; now requires
an affirmatively-known ONLINE status for any device DeviceManager
tracks, default or project-configured, treating "unknown" as unsafe -
see validate_command_safety()'s own comment for the full reasoning);
enforce_safe_state() is wired in as one more check in that same place,
not a new command path.
"""
import threading
import time

from epw_os.core.logging import log
from epw_os.core.device_manager import DeviceStatus


class SafetyKernel:
    # "wartosc konfigurowalna, nie zaszyta" (task requirement): a named,
    # overridable constructor parameter/class constant, not a magic
    # number buried in a conditional. Not read from project.json in this
    # task - GRANICE doesn't authorize a new persisted config schema, and
    # Logic Studio's project format (which will eventually want to own
    # this) doesn't exist yet either. See SESSION_REPORT.md.
    DEFAULT_MISSED_CYCLES_THRESHOLD = 3
    DEFAULT_POLL_INTERVAL_SECONDS = 1.0

    # Per-tag staleness ("tagi urzadzenia nie odswiezone przez
    # konfigurowalny czas") deliberately reuses TagManager's own,
    # already-configurable Tag.timeout/check_watchdogs()/STALE-quality
    # mechanism instead of inventing a second one here - see
    # _device_has_stale_tags().

    SYSTEM_ALARM_ID = "SYSTEM_HEALTH"
    _DEVICE_ALARM_PREFIX = "DEVICE_HEALTH_"

    def __init__(self, tag_manager, driver_manager=None, logic_engine=None,
                 device_manager=None, alarm_manager=None, audit_logger=None,
                 missed_cycles_threshold=None, poll_interval=None):
        self.tag_manager = tag_manager
        self.driver_manager = driver_manager
        self.logic_engine = logic_engine
        self.device_manager = device_manager
        self.alarm_manager = alarm_manager
        self.audit_logger = audit_logger
        self.missed_cycles_threshold = missed_cycles_threshold or self.DEFAULT_MISSED_CYCLES_THRESHOLD
        self.poll_interval = poll_interval or self.DEFAULT_POLL_INTERVAL_SECONDS

        self._lock = threading.RLock()
        # Per-device bookkeeping - this class's own state, not read from
        # or written to DeviceManager/DriverManager (see class docstring
        # and check_system_health()'s docstring: "only ever reads their
        # state").
        self._miss_counters = {}         # device_id -> consecutive cycles with no new comm
        self._last_comm_seen = {}        # device_id -> last_comm value observed last cycle
        self._device_fault_latched = {}  # device_id -> bool
        self._system_fault_latched = False
        self._system_healthy = True      # what enforce_safe_state() consults

        self._thread = None
        self._stop_event = threading.Event()

    # --- wiring (mirrors CommandManager.set_driver_manager()'s existing
    # pattern - SafetyKernel is constructed early in EPWCore.__init__,
    # before DeviceManager/DriverManager/AlarmManager/AuditLogger exist
    # yet, so those are attached afterwards instead of only at
    # construction time) -------------------------------------------------

    def set_device_manager(self, device_manager):
        self.device_manager = device_manager

    def set_driver_manager(self, driver_manager):
        self.driver_manager = driver_manager

    def set_alarm_manager(self, alarm_manager):
        self.alarm_manager = alarm_manager

    def set_audit_logger(self, audit_logger):
        self.audit_logger = audit_logger

    # --- existing command-safety gate (unchanged, only enforce_safe_state()
    # added into it - see below) ------------------------------------------

    def validate_command_safety(self, device_tag: str, command: str) -> tuple[bool, str]:
        if self.tag_manager.get_value("EMERGENCY_STOP") == True:
            return False, "Emergency Stop active"

        ok, reason = self.enforce_safe_state()
        if not ok:
            return False, reason

        parts = device_tag.split(".")
        device_id = parts[0] if parts else device_tag

        # Bug fix (Task: "luka w blokadzie komend przy awarii komunikacji
        # dla urzadzen skonfigurowanych w projekcie" - found and reported,
        # deliberately unfixed, in a previous session). This check now
        # applies ONLY to a device_id DeviceManager itself actually
        # tracks (self.device_manager.devices - populated by
        # EPWCore.startup() via device_manager.register_device(), for
        # BOTH the four hardcoded default devices AND every device a
        # project.json configures). A device_tag whose first segment
        # names nothing DeviceManager tracks (e.g. "DO05" for a
        # standalone output channel with no separate communication
        # module of its own) was never covered by this check before and
        # still isn't - unchanged, no new blocking for that whole class
        # of command.
        #
        # For a target that DOES name a tracked device, "I don't know
        # its status" must now BLOCK, not pass - before this fix, a
        # missing Device.<id>.Status tag (which is what EVERY
        # project-configured device that isn't one of the four hardcoded
        # ones actually had: the tag was only ever registered for those
        # four) read as None from get_value(), and None == "COMM_FAILURE"
        # is False, so the command silently went through with no
        # communication-health check at all - the exact bug this task
        # fixes. Fail-safe now: only a status tag that reads exactly
        # ONLINE passes; anything else - missing (unknown), OFFLINE,
        # COMM_FAILURE, or any other value - blocks ("nie wiem, czy
        # urzadzenie zyje - nie wysylam do niego rozkazu").
        if self.device_manager is not None and device_id in self.device_manager.devices:
            status = self.tag_manager.get_value(f"Device.{device_id}.Status")
            if status != DeviceStatus.ONLINE:
                if status is None:
                    reason = f"Target device {device_id} communication status is unknown (no status reported yet)"
                else:
                    reason = f"Target device {device_id} is not ready ({status}, not {DeviceStatus.ONLINE})"
                if self.audit_logger is not None:
                    self.audit_logger.record("COMMAND_BLOCKED_DEVICE_STATUS", "SYSTEM", reason, success=False)
                return False, reason

        return True, ""

    # --- periodic driving thread ------------------------------------------
    # Same headless background-thread idiom as time_sync_monitor.py's
    # TimeSyncMonitor (daemon thread + threading.Event, no PyQt) - keeps
    # this off the GUI thread entirely (GRANICE: "sprawdzanie co sekunde
    # nie moze... blokowac GUI") and off any per-command hot path
    # (GRANICE: "nie przy komendach - ma nie spowalniac sterowania").
    # Tests call check_system_health() directly instead of waiting on
    # this real-time loop, for determinism - see test_safety_kernel.py.

    def start(self):
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="SafetyKernel")
        self._thread.start()
        log.info("SafetyKernel health monitor started.")

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        log.info("SafetyKernel health monitor stopped.")

    def _run_loop(self):
        while not self._stop_event.wait(self.poll_interval):
            try:
                self.check_system_health()
            except Exception:
                log.error("SafetyKernel.check_system_health() raised an exception", exc_info=True)

    # --- detection ---------------------------------------------------------

    def check_system_health(self):
        """Runs one health-check cycle: for every registered device,
        evaluate the three criteria below (any one is enough to call a
        device unhealthy), publish Safety.<id>.Healthy/.Fault, then
        publish the system-wide Safety.System.Healthy/.Fault aggregate.
        Detection and signaling only - see module docstring.

          - the device hasn't answered in N consecutive cycles of THIS
            check (missed_cycles_threshold, default 3 - "one lost RS-485
            packet is normal, not a fault", hence a threshold, not 1)
          - a tag belonging to this device has gone STALE per its own
            configured timeout (TagManager's own, pre-existing, already-
            configurable mechanism - see _device_has_stale_tags())
          - the driver that services this device has no live thread

        Only ever READS device_manager/driver_manager/tag_manager state
        (GRANICE: "tylko odczytuj ich stan") and writes to
        tag_manager/alarm_manager/audit_logger - never to a driver or an
        output tag."""
        if self.device_manager is None:
            return  # not wired yet - nothing to check

        with self._lock:
            self.tag_manager.check_watchdogs()  # refreshes STALE quality, used below

            any_unhealthy = False
            for device_id, info in list(self.device_manager.devices.items()):
                healthy = self._check_device_health(device_id, info)
                if not healthy:
                    any_unhealthy = True

            self._publish_system_health(any_unhealthy)

    def _check_device_health(self, device_id: str, info: dict) -> bool:
        reasons = []

        # Criterion 1: missed poll cycles.
        last_comm = info.get("last_comm", 0.0)
        previous = self._last_comm_seen.get(device_id)
        if previous is not None and last_comm == previous:
            self._miss_counters[device_id] = self._miss_counters.get(device_id, 0) + 1
        else:
            self._miss_counters[device_id] = 0
        self._last_comm_seen[device_id] = last_comm
        miss_count = self._miss_counters[device_id]
        if miss_count >= self.missed_cycles_threshold:
            reasons.append(f"No response in {miss_count} consecutive poll cycles")

        # Criterion 2: this device's own tags gone stale.
        if self._device_has_stale_tags(device_id):
            reasons.append("Device tags not refreshed within their configured timeout")

        # Criterion 3: the driver servicing this device has no live thread.
        driver_id = info.get("driver_id")
        driver = self.driver_manager.get_driver(driver_id) if self.driver_manager else None
        if driver is not None and not self._driver_alive(driver):
            reasons.append(f"Driver '{driver_id}' has no live thread")

        healthy = not reasons
        self._update_device_tags(device_id, healthy, reasons)
        return healthy

    def _device_has_stale_tags(self, device_id: str) -> bool:
        from epw_os.core.tag_manager import TagQuality
        prefix = f"{device_id}."
        for tag in self.tag_manager.list_tags():
            if tag.name.startswith(prefix) and tag.quality == TagQuality.STALE:
                return True
        return False

    @staticmethod
    def _driver_alive(driver) -> bool:
        # is_alive() is a small, additive, behavior-neutral query method
        # (see BaseDriver/SimulatorDriver) - not a change to how any
        # driver actually communicates. Falls back to the driver's own
        # is_running flag for any driver that doesn't define is_alive()
        # (kept purely defensive; every driver in this codebase does).
        is_alive = getattr(driver, "is_alive", None)
        if callable(is_alive):
            return bool(is_alive())
        return bool(getattr(driver, "is_running", False))

    # --- tag publishing / latch handling ------------------------------------

    def _ensure_bool_tag(self, name: str, default: bool, description: str):
        from epw_os.core.tag_manager import TagType
        if self.tag_manager.get_tag(name) is None:
            self.tag_manager.add_tag(name, default, TagType.BOOL, description=description, source="SYSTEM")

    def _update_device_tags(self, device_id: str, healthy: bool, reasons: list):
        healthy_tag = f"Safety.{device_id}.Healthy"
        fault_tag = f"Safety.{device_id}.Fault"
        alarm_id = f"{self._DEVICE_ALARM_PREFIX}{device_id}"
        self._ensure_bool_tag(healthy_tag, True, f"{device_id} responding to SafetyKernel health checks")
        self._ensure_bool_tag(fault_tag, False, f"{device_id} health fault latch - clears only on acknowledgement")

        previously_healthy = self.tag_manager.get_value(healthy_tag)
        if previously_healthy != healthy:
            self.tag_manager.update_tag(healthy_tag, healthy)

        if not healthy:
            if not self._device_fault_latched.get(device_id, False):
                # Rising edge into unhealthy - latch, alarm, log. Never
                # touches a driver or an output tag.
                self._device_fault_latched[device_id] = True
                self.tag_manager.update_tag(fault_tag, True)
                reason_text = "; ".join(reasons)
                if self.alarm_manager is not None:
                    self.alarm_manager.trigger_alarm(
                        alarm_id, f"{device_id} health check failed: {reason_text}",
                        source_tag=healthy_tag, priority=3,
                    )
                if self.audit_logger is not None:
                    self.audit_logger.record("DEVICE_HEALTH_FAULT", "SYSTEM",
                                              f"{device_id}: {reason_text}", success=False)
        else:
            if self._device_fault_latched.get(device_id, False) and previously_healthy is False:
                # Falling edge - the condition is gone, but the FAULT
                # LATCH stays set until acknowledged (see
                # on_alarm_acknowledged()). Only tell AlarmManager the
                # underlying condition cleared (ACTIVE_UNACK ->
                # CLEARED_UNACK - still requires acknowledgement, exactly
                # matching the latch requirement) - the Fault tag itself
                # is untouched here.
                if self.alarm_manager is not None:
                    self.alarm_manager.clear_alarm(alarm_id)

    def _publish_system_health(self, any_unhealthy: bool):
        healthy_tag = "Safety.System.Healthy"
        fault_tag = "Safety.System.Fault"
        self._ensure_bool_tag(healthy_tag, True, "Aggregate: every monitored device passes SafetyKernel health checks")
        self._ensure_bool_tag(fault_tag, False, "Aggregate health fault latch - clears only on acknowledgement")

        system_healthy = not any_unhealthy
        self._system_healthy = system_healthy  # what enforce_safe_state() consults

        previously_healthy = self.tag_manager.get_value(healthy_tag)
        if previously_healthy != system_healthy:
            self.tag_manager.update_tag(healthy_tag, system_healthy)

        if not system_healthy:
            if not self._system_fault_latched:
                self._system_fault_latched = True
                self.tag_manager.update_tag(fault_tag, True)
                if self.alarm_manager is not None:
                    self.alarm_manager.trigger_alarm(
                        self.SYSTEM_ALARM_ID, "System health check failed - one or more devices unhealthy",
                        source_tag=healthy_tag, priority=3,
                    )
                if self.audit_logger is not None:
                    self.audit_logger.record("DEVICE_HEALTH_FAULT", "SYSTEM",
                                              "System-wide health check failed", success=False)
        else:
            if self._system_fault_latched and previously_healthy is False:
                if self.alarm_manager is not None:
                    self.alarm_manager.clear_alarm(self.SYSTEM_ALARM_ID)

    def on_alarm_acknowledged(self, alarm_id: str, user: str = ""):
        """Called by the composition root (EPWCore._on_alarm_acknowledged,
        subscribed to AlarmManager's existing 'alarm_acknowledged' event)
        whenever an operator acknowledges an alarm on the existing Alarms
        page - the ONLY place a Fault latch ever clears (task requirement:
        "zatrzask kasuje sie WYLACZNIE przez reczne potwierdzenie").
        Ignores any alarm_id this class didn't itself raise."""
        with self._lock:
            if alarm_id == self.SYSTEM_ALARM_ID:
                self._clear_fault_latch(None, "Safety.System.Fault", user)
                return
            if alarm_id.startswith(self._DEVICE_ALARM_PREFIX):
                device_id = alarm_id[len(self._DEVICE_ALARM_PREFIX):]
                self._clear_fault_latch(device_id, f"Safety.{device_id}.Fault", user)

    def _clear_fault_latch(self, device_id, fault_tag: str, user: str):
        if self.tag_manager.get_value(fault_tag):
            self.tag_manager.update_tag(fault_tag, False)
        if device_id is not None:
            self._device_fault_latched[device_id] = False
        else:
            self._system_fault_latched = False
        if self.audit_logger is not None:
            label = device_id or "SYSTEM"
            self.audit_logger.record("DEVICE_HEALTH_FAULT_ACK", user or "",
                                      f"{label} health fault acknowledged", success=True)

    # --- the one allowed reaction: block new commands, nothing else -------

    def enforce_safe_state(self) -> tuple[bool, str]:
        """The ONLY thing this class does about an unhealthy system (task
        requirement + GRANICE): refuse a NEW command and record that
        refusal. Never touches a driver or an output tag - reacting to a
        fault (e.g. opening a breaker) is the user logic's job, once
        Logic Studio exists, not this module's. Wired into
        validate_command_safety() above, the same gate command_manager.py
        already calls for every command - no new command path added."""
        with self._lock:
            healthy = self._system_healthy
        if healthy:
            return True, ""
        reason = "System health check failed - new commands are blocked (screen informs, hardware protects)"
        if self.audit_logger is not None:
            self.audit_logger.record("COMMAND_BLOCKED_UNHEALTHY_SYSTEM", "SYSTEM", reason, success=False)
        return False, reason
