"""The controller's own IOProvider - what the shared execution engine
reads and writes while it scans the user's logic on this machine.

Logic Studio runs the identical engine against SimulationIOProvider (an
in-memory image). Here the same three address spaces are served by the
real controller:

  * physical DI/AI - read straight off TagManager, the one image every
    driver publishes into;
  * physical DO/AO - written through DriverManager.route_command(), the
    driver layer's single boundary. That is deliberate: it is exactly
    where Training Mode cuts, and where a forced output is refused, so
    logic gets no private path to the hardware that an operator command
    does not have;
  * internal signals (M./MR./MW./MWR.) - this process's own memory;
  * system signals (SYS.*) - mapped onto what this controller actually
    knows about itself (health, access level, comms, time sync), with
    the PULSE_*/BLINK_* generators computed from the SAME shared table
    the simulation uses, so a blink rate never differs between the
    engineer's test and the running plant.

Retentive internal signals (MR./MWR.) are NOT yet persisted across a
restart - they behave exactly like non-retentive ones here. Logic Studio
only ever stored and exported the flag (see shared/logic/internal_bits.py's
own note: making the value survive a restart is EPW-OS's responsibility),
and nothing in this file pretends otherwise.
"""
import sys
import threading
from pathlib import Path

# The block library and the execution engine are the CONTRACT with Logic
# Studio and live in shared/logic/ - so the repository root has to be
# importable here. Unlike shared/addressing.py (loaded by path in
# epw_os/core/addressing.py, precisely to avoid this), shared.logic is a
# package whose ~30 modules import each other by absolute name, so there
# is nothing to load by path: it is imported as a package or not at all.
# Appended, never inserted at position 0, so it can never shadow a
# runtime module of the same name.
_REPO_ROOT = str(Path(__file__).resolve().parents[3])
if _REPO_ROOT not in sys.path:
    sys.path.append(_REPO_ROOT)

from shared.logic.engine.io_provider import IOProvider, pulse_signal_value  # noqa: E402
from epw_os.core.logging import log  # noqa: E402


class SystemSignalSource:
    """Serves the SYS.* half of the system-signal catalog from this
    controller's own managers.

    Every collaborator is optional - a controller built without one (or a
    test) gets the safe value for that signal rather than an AttributeError
    mid-scan. Anything this class cannot answer comes back False/0.0, the
    same "defined, falsy" rule the catalog itself uses for an unset signal.

    The alarm half (SEC.SYSTEM.* state and the REQ.SEC.* requests) is
    served by core/security_signals.py, which is where the decision about
    what a system-wide signal means on a per-ZONE intrusion model is
    written down. The handful it deliberately does not answer (partial
    arming, the sounder, a panic line - none of which exist on this
    controller) keep the catalog's safe value on a read, and a WRITE to
    one is reported rather than silently vanishing (see TagIOProvider.
    write_system_signal).
    """

    # SYS.ACCESS_LEVEL is a number, in the catalog's own order: the same
    # ranking AccessManager uses (User < Operator < Engineer).
    _ACCESS_LEVEL_VALUES = {"User": 0.0, "Operator": 1.0, "Engineer": 2.0}

    def __init__(self, health_manager=None, access_manager=None, training_mode=None,
                 time_sync_monitor=None, security=None, sources=()):
        self.health_manager = health_manager
        self.access_manager = access_manager
        self.training_mode = training_mode
        self.time_sync_monitor = time_sync_monitor
        # The register's other groups, each its own source with serves()/
        # read() and - for REQ.* - required_level()/execute(): SYS lifecycle,
        # RT, MODE (core/runtime_state_signals.py), and the groups the
        # later stages add. Asked in order; the first that serves a signal
        # answers it.
        self.sources = list(sources)
        for source in self.sources:
            attach = getattr(source, "attach", None)
            if callable(attach):
                attach(self)
        # The alarm half of the catalog (core/security_signals.py), which
        # maps the system-wide alarm-panel vocabulary onto this
        # controller's per-zone intrusion model. None -> every SEC
        # signal keeps the catalog's safe value.
        self.security = security

        # Set by the scan loop itself (LogicEngine) before each scan -
        # this class never measures them.
        self.scan_time_ms = 0.0
        self.cycle_count = 0.0
        self.first_scan = False
        self.scan_overrun = False
        self.ready = False

    def read(self, signal_id: str, now_ms: int = 0):
        pulse = pulse_signal_value(signal_id, now_ms)
        if pulse is not None:
            return pulse

        if self.security is not None:
            value = self.security.read(signal_id)
            if value is not None:
                return value

        for source in self.sources:
            if source.serves(signal_id):
                value = source.read(signal_id)
                return False if value is None else value

        handler = self._HANDLERS.get(signal_id)
        if handler is None:
            return False
        return handler(self)

    def request_source(self, signal_id: str):
        """Whoever executes a REQ.* signal: the alarm half, or one of the
        attached sources. None when nothing on this controller does."""
        if self.security is not None and self.security.serves(signal_id):
            return self.security
        for source in self.sources:
            if source.serves(signal_id) and hasattr(source, "execute"):
                return source
        return None

    # --- individual signals -------------------------------------------------

    def _health_states(self) -> dict:
        if self.health_manager is None:
            return {}
        return self.health_manager.get_health()

    def _any_fault(self) -> bool:
        return any(state == "FAULT" for state in self._health_states().values())

    def _read_ready(self):
        return bool(self.ready)

    def _read_health(self):
        return not self._any_fault()

    def _read_fault(self):
        return self._any_fault()

    def _read_training_mode(self):
        return bool(getattr(self.training_mode, "active", False))

    def _read_comms_ok(self):
        """The DRIVERS subsystem, which HealthManager already degrades on
        every COMM_FAILURE a device reports - not a second, independent
        notion of "comms" invented here."""
        return self._health_states().get("DRIVERS") == "RUNNING"

    def _read_time_sync_ok(self):
        return getattr(self.time_sync_monitor, "status", None) == "SYNCED"

    def _read_access_level(self):
        level = getattr(self.access_manager, "level", None)
        return self._ACCESS_LEVEL_VALUES.get(level, 0.0)

    def _has_access(self, required: str) -> bool:
        if self.access_manager is None:
            return False
        return bool(self.access_manager.has_access(required))

    _HANDLERS = {
        "SYS.READY": _read_ready,
        "SYS.HEALTH": _read_health,
        "SYS.FAULT": _read_fault,
        "SYS.SCAN_OVERRUN": lambda self: bool(self.scan_overrun),
        "SYS.FIRST_SCAN": lambda self: bool(self.first_scan),
        "SYS.TRAINING_MODE": _read_training_mode,
        "SYS.SCAN_TIME": lambda self: float(self.scan_time_ms),
        "SYS.CYCLE_COUNT": lambda self: float(self.cycle_count),
        "SYS.COMMS_OK": _read_comms_ok,
        "SYS.TIME_SYNC_OK": _read_time_sync_ok,
        "SYS.ACCESS_LEVEL": _read_access_level,
        "SYS.ACCESS_USER": lambda self: self._has_access("User"),
        "SYS.ACCESS_OPERATOR": lambda self: self._has_access("Operator"),
        "SYS.ACCESS_ENGINEER": lambda self: self._has_access("Engineer"),
    }


class TagIOProvider(IOProvider):
    """The IOProvider the controller's ExecutionEngine runs against.

    `write_digital`/`write_analog` are the two callables that actually
    reach hardware - EPWCore passes its own driver-routing methods, so
    this class never looks a driver up itself and Training Mode/forces
    keep working exactly as they do for an operator command.
    """

    def __init__(self, tag_manager, write_digital=None, write_analog=None,
                 force_manager=None, system_signals=None, access_manager=None, audit_logger=None):
        self.tag_manager = tag_manager
        self._write_digital = write_digital
        self._write_analog = write_analog
        self.force_manager = force_manager
        self.system_signals = system_signals or SystemSignalSource()
        # Who is logged in - consulted for a system-signal command whose
        # own block demands a minimum access level (see command_levels).
        self.access_manager = access_manager
        # Rule Z2 of the register work: a request the logic issued and the
        # controller refused must be visible - the audit log, not only a
        # line in the debug log.
        self.audit_logger = audit_logger

        # signal_id -> the "Minimalny poziom dostepu" its own
        # system.signal_out block declares ("Brak"/"User"/"Operator"/
        # "Engineer"). Filled by LogicEngine from the compiled program:
        # Logic Studio stores the level on the block and states plainly
        # that EPW-OS is what enforces it (see blocks/system_signals.py's
        # own PROPERTY_TOOLTIPS), so this is that enforcement.
        self.command_levels = {}

        # Last value seen per writable system signal - a command executes
        # on the RISING edge only. A block holding REQ.SEC.ARM_ALL true would
        # otherwise re-issue it every single scan, i.e. dozens of times a
        # second.
        self._last_command_value = {}

        # Internal signal memory (feat/internal-bits' third address space).
        # Guarded because the scan thread writes it while the REST API/GUI
        # may read a snapshot.
        self._internal = {}
        self._lock = threading.RLock()

        # System signals this controller does not serve yet, reported once
        # each rather than on every scan (see write_system_signal).
        self._unserved_writes = set()

        # ExecutionEngine.step() keeps these two current on whatever
        # IOProvider it has (see its step(), step 4) - held here so
        # SYS.SCAN_TIME/SYS.CYCLE_COUNT read back the real numbers.
        self.scan_time_ms = 0.0
        self.cycle_count = 0.0

    # --- physical inputs ----------------------------------------------------

    def read_digital_input(self, address: str) -> bool:
        return bool(self.tag_manager.get_value(address))

    def read_digital_output(self, address: str) -> bool:
        return bool(self.tag_manager.get_value(address))

    def read_analog_input(self, address: str) -> float:
        """The ENGINEERING value (42.0 °C, 65 %), which is what the tag
        already holds - an analog input is scaled once, on the way in
        (analog_scaling.py), and the logic's own range checks are
        configured in those same units."""
        return _as_float(self.tag_manager.get_value(address))

    def read_analog_output(self, address: str) -> float:
        return _as_float(self.tag_manager.get_value(address))

    # --- physical outputs ---------------------------------------------------

    def write_digital_output(self, address: str, value: bool):
        if self._refuse_forced(address):
            return
        if self._write_digital is None:
            return
        self._write_digital(address, bool(value))

    def write_analog_output(self, address: str, value: float):
        if self._refuse_forced(address):
            return
        if self._write_analog is None:
            return
        self._write_analog(address, _as_float(value))

    def _refuse_forced(self, address: str) -> bool:
        """A forced output belongs to the person forcing it, not to logic -
        the same rule CommandManager applies to an operator command
        (command_manager.py's own "forced output" branch). Silent by
        design: the force itself is already audited and shown, and the
        scan runs every cycle_time_ms."""
        if self.force_manager is None:
            return False
        return bool(self.force_manager.is_forced(address))

    # --- internal signals ---------------------------------------------------

    def read_internal(self, name: str, default=False):
        with self._lock:
            return self._internal.get(name, default)

    def write_internal(self, name: str, value):
        with self._lock:
            self._internal[name] = value

    def internal_snapshot(self) -> dict:
        with self._lock:
            return dict(self._internal)

    def preload_internal(self, values: dict):
        """Puts stored values into the internal-signal memory before the
        first scan - how a RETENTIVE signal (MR./MWR.) comes back after a
        restart. Only ever called with the ids the program itself
        declares retentive (LogicEngine); everything else starts at its
        own default, as it always has."""
        with self._lock:
            self._internal.update(values or {})

    # --- system signals -----------------------------------------------------

    def read_system_signal(self, signal_id: str, now_ms: int = 0):
        self.system_signals.scan_time_ms = self.scan_time_ms
        self.system_signals.cycle_count = self.cycle_count
        return self.system_signals.read(signal_id, now_ms)

    def write_system_signal(self, signal_id: str, value):
        """Executes a system-signal command (the SEC.CMD_* family, the
        only writable signals the catalog has today).

        Three rules, in this order: on the RISING EDGE only (a block
        holding the command true would otherwise re-issue it every scan);
        only if the access level the block itself demands is currently
        held; and only for a command this controller actually implements -
        anything else is reported once, rather than vanishing, so a
        command that does nothing is never a mystery.
        """
        rising = bool(value) and not self._last_command_value.get(signal_id, False)
        self._last_command_value[signal_id] = bool(value)
        if not rising:
            return

        finder = getattr(self.system_signals, "request_source", None)
        source = finder(signal_id) if callable(finder) else None
        if source is None:
            if signal_id not in self._unserved_writes:
                self._unserved_writes.add(signal_id)
                log.warning(f"Logic issued the system command {signal_id}, which this controller does not "
                            f"execute - it was not applied.")
                self._audit_refusal(signal_id, "this controller does not execute it")
            return

        # The gate is the stricter of what the block asked for and what
        # the request itself demands (the same level the panel needs for
        # the same action - rule Z2).
        required = self.command_levels.get(signal_id, "Brak")
        source_level = getattr(source, "required_level", None)
        demanded = source_level(signal_id) if callable(source_level) else None
        if demanded and _level_rank(demanded) > _level_rank(required):
            required = demanded
        if not self._has_command_access(required):
            log.warning(f"Logic issued {signal_id}, but it requires {required} access and the "
                        f"controller is at a lower level - not applied.")
            self._audit_refusal(signal_id, f"requires {required}, the controller is at "
                                           f"{getattr(self.access_manager, 'level', None)}")
            return

        if source is getattr(self.system_signals, "security", None):
            source.execute(signal_id, actor="LOGIC")
        else:
            source.execute(signal_id, actor="LOGIC", level=getattr(self.access_manager, "level", None))

    def _audit_refusal(self, signal_id: str, reason: str):
        if self.audit_logger is not None:
            self.audit_logger.record("LOGIC_REQUEST_REFUSED", "LOGIC", f"{signal_id}: {reason}", success=False)

    def _has_command_access(self, required: str) -> bool:
        """"Brak" (none) is the default for every non-safety command and
        means no gate at all. Any other level is checked against whoever
        is logged in right now - with no access manager to ask, only
        "Brak" passes, because a controller that cannot tell who is
        present must not execute a command that asked for someone."""
        if not required or required == "Brak":
            return True
        if self.access_manager is None:
            return False
        return bool(self.access_manager.has_access(required))


def _level_rank(level) -> int:
    from epw_os.core.access_manager import AccessLevel
    try:
        return AccessLevel._ORDER.index(level)
    except ValueError:
        return -1


def _as_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
