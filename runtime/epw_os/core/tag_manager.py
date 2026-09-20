import time
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional
from enum import Enum

class TagQuality(Enum):
    NOT_INITIALIZED = "NOT_INITIALIZED"
    GOOD = "GOOD"
    BAD = "BAD"
    UNCERTAIN = "UNCERTAIN"
    STALE = "STALE"
    COMM_FAILURE = "COMM_FAILURE"
    # Task: "usunac atrapy z interfejsu i zatrzymac zapisywanie zmyslonych
    # pomiarow do bazy danych". A value computed by an on-screen simulator
    # (no physical sensor/meter behind it) rather than read from real
    # hardware or logic - distinct from BAD/STALE/COMM_FAILURE, which all
    # mean "a real source exists but its data can't currently be trusted".
    # SIMULATED means the opposite: the data is trustworthy *as a
    # simulation*, it just isn't a measurement at all. Flows through the
    # existing tag_changed -> Historian.record_tag_change() pipeline
    # exactly like every other quality value (quality.value is already a
    # plain string on that event, and TagHistory.quality is already a
    # free-text String column) - so simulated rows land in the database
    # clearly marked and filterable instead of needing a parallel
    # mechanism (a new tag flag, a naming convention) or being silently
    # dropped, which would make historian_export_dialog.py's "does this
    # range contain simulated data" check impossible to answer honestly.
    SIMULATED = "SIMULATED"

class TagType(Enum):
    BOOL = "BOOL"
    INT = "INT"
    DINT = "DINT"
    REAL = "REAL"
    STRING = "STRING"
    TIME = "TIME"

@dataclass
class Tag:
    name: str
    value: Any
    data_type: TagType
    description: str = ""
    timestamp: float = 0.0
    quality: TagQuality = TagQuality.GOOD
    last_update: float = 0.0
    timeout: float = 5.0 # Seconds before STALE/BAD quality
    source: str = "SYSTEM"
    # From the project's point registry (task "runtime czyta projekt.epw"
    # 3.1) - where the terminal physically is and the technician's note for
    # it. Informational; nothing in the program branches on either.
    location: str = ""
    technical_note: str = ""
    # read_only removed (Task: "Tag.read_only - martwe pole"): a full
    # repo-wide search confirmed EVERY add_tag() call site (100+, across
    # every core/ module) either omitted this parameter or passed the
    # same False default - nothing ever set it True, so
    # _apply_update()'s own read_only check (formerly here) never once
    # blocked a write in this program's history. DECISION: removed
    # rather than "started using", because this codebase already has a
    # real, working, CENTRALIZED answer to the exact question this field
    # was meant to answer ("which tags can logic write?") -
    # tag_export.py's own LOGIC_WRITABLE_TAGS allowlist (currently just
    # {"System.Theme"}), which that module's own docstring already
    # explains was deliberately chosen over deriving anything from this
    # field. Wiring this field up instead would have meant touching
    # every one of those 100+ call sites to set read_only=True (a large,
    # error-prone diff for this task's own GRANICE: "nie zmieniaj
    # zachowania programu poza naprawa System.Mode" - enforcing a
    # previously-inert check for the first time IS a behavior change),
    # while producing a SECOND, competing source of truth for the same
    # concept that could drift out of sync with LOGIC_WRITABLE_TAGS -
    # more confusing than the dead field it would replace, not less.

class TagManager:
    """
    Framework-independent TagManager.
    Single source of truth for process data.
    """
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self._tags: Dict[str, Tag] = {}
        self._forced = set()   # tag names pinned by ForceManager
        self._lock = threading.RLock()
        self.mode = "SIMULATION MODE" # LIVE MODE or SIMULATION MODE
        # Bug fix (Task: "System.Mode nie jest zarejestrowany"): set_mode()
        # below has ALWAYS called update_tag("System.Mode", ...) - since
        # the very first version of this class - but nothing ever
        # registered that tag with add_tag() first, so every single call
        # raised ValueError("Unknown tag: System.Mode"), silently
        # swallowed by EventBus.emit()'s own per-subscriber try/except
        # (see events.py). self.mode itself still updated correctly - only
        # the TAG never existed, so mode switching never actually reached
        # TagManager, logic, MQTT, or the REST API's own tag list.
        #
        # Registered HERE, in __init__ - not in init_default_tags() or
        # configure() (both of which run CONDITIONALLY, exactly one or
        # the other, depending on whether project.json defines its own
        # "devices" - see EPWCore.startup()) - so the tag exists
        # unconditionally, before ANY other startup step, and is already
        # readable even before the very first mode change (Task's own
        # requirement: "dostepny zawsze, takze zanim ktokolwiek pierwszy
        # raz zmieni tryb"). Seeded with self.mode itself, not a
        # hardcoded literal, so the tag's initial value can never drift
        # from the attribute it mirrors.
        self.add_tag("System.Mode", self.mode, TagType.STRING,
                     description="Current run mode - SIMULATION MODE / LIVE MODE (ENGINEER MODE is a "
                                 "legacy third value set_mode() still accepts but nothing currently sets). "
                                 "Read-only from logic; toggled via the status bar's run-mode button or "
                                 "TagManager.toggle_mode()/set_mode().",
                     source="SYSTEM")

    def toggle_mode(self):
        new_mode = "LIVE MODE" if self.mode == "SIMULATION MODE" else "SIMULATION MODE"
        self.event_bus.emit("mode_change_request", new_mode)
        
    def set_mode(self, new_mode: str):
        with self._lock:
            if new_mode in ["SIMULATION MODE", "LIVE MODE", "ENGINEER MODE"]:
                self.mode = new_mode
                self.update_tag("System.Mode", self.mode)

    def add_tag(self, name: str, value: Any, data_type: TagType, description: str = "", timeout: float = 5.0, source: str = "SYSTEM", quality: TagQuality = TagQuality.GOOD):
        with self._lock:
            if name not in self._tags:
                t = time.time()
                self._tags[name] = Tag(
                    name=name, value=value, data_type=data_type,
                    description=description, timestamp=t, last_update=t,
                    timeout=timeout, source=source, quality=quality
                )
                self.event_bus.emit("tag_added", self._tags[name])

    def remove_tag(self, name: str) -> bool:
        """Counterpart to add_tag() - needed now that a set of tags can
        shrink at runtime (dynamic Analog Inputs points), not just grow.
        DI/DO/Cabinet tags never call this - their tag set is fixed at
        startup. Returns False for an unknown tag (nothing to remove)."""
        with self._lock:
            if name in self._tags:
                del self._tags[name]
                self.event_bus.emit("tag_removed", name)
                return True
            return False

    def list_tags(self):
        with self._lock:
            import copy
            return [copy.copy(tag) for tag in self._tags.values()]
            
    def configure(self, devices: list):
        """The ONLY way DI/DO channel tags come into existence (task
        "migracja adresacji" - init_default_tags()'s own flat DI1..DI64/
        DO05..DO64 scheme is gone, see that method's own docstring).
        `devices` may be empty - a brand-new project with no cards yet
        correctly ends up with zero DI/DO tags, not 64 fake ones; a
        module's channels don't exist until the module itself is part of
        the project, same "absent = does not exist, not disabled"
        stance Studio's own Skład urządzenia already applies.

        Tag names use addressing.format_address() - <card>.<KIND>.<n>,
        no leading zero, `card` taken verbatim from the project (never
        assumed to start with "ELA"/"ADA")."""
        from epw_os.core.addressing import format_address
        for dev in devices:
            dev_id = dev.get("id")
            dev_type = dev.get("type")
            # A projekt.epw card says what its channels ARE ("kind": DI/DO/
            # AI/AO); the older device list said which module family it was
            # ("type": ELA/ADA/EPM). Same tags either way.
            kind = dev.get("kind")
            if kind == "DI":
                dev_type = "ELA"
            elif kind == "DO":
                dev_type = "ADA"
            elif kind == "AI":
                # AI points become tags through the Analog Inputs module
                # (EPWCore._register_analog_input_tags(), only when that
                # module is part of the device) - they are a module's
                # points, not plain channels.
                continue
            elif kind == "AO":
                # An analog OUTPUT is a channel of the card, like DO: it
                # exists because the card has it, not because a module is
                # switched on. The tag holds the RAW register value (same
                # as an analog input); analog_scaling.compute_raw_value()
                # turns an engineering value into it on the way out.
                for i in range(1, int(dev.get("channels", 0) or 0) + 1):
                    self.add_tag(format_address(dev_id, "AO", i), 0.0, TagType.REAL,
                                 quality=TagQuality.NOT_INITIALIZED, source="HARDWARE",
                                 description=f"Analog output channel {i} on module '{dev_id}' - the raw value "
                                             f"written to the card. NOT_INITIALIZED until something writes it.")
                continue
            if dev_type == "ELA":
                for i in range(1, dev.get("channels", 32) + 1):
                    self.add_tag(format_address(dev_id, "DI", i), False, TagType.BOOL, quality=TagQuality.NOT_INITIALIZED,
                                 source="HARDWARE",
                                 description=f"Digital input channel {i} on ELA module '{dev_id}' - True while "
                                             f"the field contact is closed. NOT_INITIALIZED until the driver "
                                             f"reports a real reading at least once.")
            elif dev_type == "ADA":
                for i in range(1, dev.get("channels", 32) + 1):
                    self.add_tag(format_address(dev_id, "DO", i), False, TagType.BOOL, quality=TagQuality.NOT_INITIALIZED,
                                 source="HARDWARE",
                                 description=f"Digital output channel {i} on ADA module '{dev_id}' - True while "
                                             f"commanded/reading closed. NOT_INITIALIZED until the driver "
                                             f"reports a real reading at least once.")
            elif dev_type == "EPM":
                for phase in ("UL1", "UL2", "UL3"):
                    self.add_tag(f"{dev_id}.{phase}.RMS", 0.0, TagType.REAL, quality=TagQuality.NOT_INITIALIZED,
                                 source="HARDWARE",
                                 description=f"RMS phase-to-neutral voltage, phase {phase[-1]}, from power "
                                             f"meter '{dev_id}' (volts). NOT_INITIALIZED until the driver "
                                             f"reports a real reading at least once.")
                self.add_tag(f"{dev_id}.FREQ", 0.0, TagType.REAL, quality=TagQuality.NOT_INITIALIZED,
                             source="HARDWARE",
                             description=f"Mains frequency measured by power meter '{dev_id}' (Hz). "
                                         f"NOT_INITIALIZED until the driver reports a real reading at least once.")

    def publish_from_driver(self, name, value, quality=TagQuality.GOOD):
        return self._apply_update(name, value, quality, source="DRIVER")
        
    def publish_from_runtime(self, name, value, quality=TagQuality.GOOD):
        return self._apply_update(name, value, quality, source="LOGIC_RUNTIME")
        
    def publish_system(self, name, value):
        return self._apply_update(name, value, TagQuality.GOOD, source="SYSTEM")

    # --- forcing (core/force_manager.py) ------------------------------------------------
    # A forced tag keeps its forced value whatever a driver, the logic
    # runtime or the system publish - publish_forced() is the one door
    # that still writes it, and ForceManager is the only caller.

    def set_forced(self, name: str, forced: bool):
        with self._lock:
            if forced:
                self._forced.add(name)
            else:
                self._forced.discard(name)

    def is_forced(self, name: str) -> bool:
        with self._lock:
            return name in self._forced

    def forced_tags(self) -> list:
        with self._lock:
            return sorted(self._forced)

    def publish_forced(self, name, value):
        return self._apply_update(name, value, TagQuality.GOOD, source="FORCE")

    def update_tag(self, name: str, value: Any, quality: TagQuality = TagQuality.GOOD):
        return self._apply_update(name, value, quality, source="SYSTEM")

    def _apply_update(self, name: str, value: Any, quality: TagQuality, source: str):
        with self._lock:
            if name in self._forced and source != "FORCE":
                return False          # pinned by a force - the real value waits until it is released
            if name in self._tags:
                tag = self._tags[name]

                # Enforce basic type casting/checking (skeleton implementation)
                try:
                    if tag.data_type == TagType.BOOL:
                        if isinstance(value, bool): pass
                        elif isinstance(value, int) and value in (0, 1): value = bool(value)
                        elif isinstance(value, str):
                            norm = value.strip().lower()
                            if norm in ("1", "true", "on", "yes"): value = True
                            elif norm in ("0", "false", "off", "no"): value = False
                            else: raise ValueError(f"Invalid BOOL string: {value}")
                        else: raise ValueError(f"Invalid BOOL type: {type(value)}")
                    elif tag.data_type in (TagType.INT, TagType.DINT):
                        value = int(value)
                    elif tag.data_type == TagType.REAL:
                        value = float(value)
                    elif tag.data_type == TagType.STRING:
                        value = str(value)
                except (ValueError, TypeError):
                    from epw_os.core.logging import log
                    log.error(f"Type mismatch updating tag {name} (expected {tag.data_type.value}, got {type(value)})")
                    return

                tag.value = value
                tag.quality = quality
                tag.last_update = time.time()
                tag.timestamp = time.time()
                
                # Emit standard event via EventBus instead of PyQt signal
                self.event_bus.emit("tag_changed", name, value, quality.value)
                return True
            else:
                raise ValueError(f"Unknown tag: {name}")

    def get_tag(self, name: str) -> Optional[Tag]:
        with self._lock:
            tag = self._tags.get(name)
            if tag:
                # Return a copy to prevent unsynchronized external mutation
                import copy
                return copy.copy(tag)
            return None

    def get_value(self, name: str) -> Any:
        with self._lock:
            tag = self._tags.get(name)
            return tag.value if tag else None

    def set_description(self, name: str, description: str) -> bool:
        with self._lock:
            tag = self._tags.get(name)
            if not tag:
                return False
            tag.description = description
            self.event_bus.emit("tag_changed", name, tag.value, tag.quality.value)
            return True

    def set_point_info(self, name: str, location: str = None, technical_note: str = None) -> bool:
        """Location and technical note from the project's point registry.
        No tag_changed event - value and quality are untouched."""
        with self._lock:
            tag = self._tags.get(name)
            if not tag:
                return False
            if location is not None:
                tag.location = location
            if technical_note is not None:
                tag.technical_note = technical_note
            return True

    def check_watchdogs(self):
        with self._lock:
            now = time.time()
            for name, tag in self._tags.items():
                if tag.timeout > 0 and (now - tag.last_update) > tag.timeout:
                    if tag.quality != TagQuality.STALE:
                        tag.quality = TagQuality.STALE
                        self.event_bus.emit("tag_changed", name, tag.value, tag.quality.value)
                        
    def init_simulation_and_cabinet_tags(self):
        """Task "migracja adresacji" - was init_default_tags(), which
        bundled TWO unrelated things: the flat DI1..DI64/DO05..DO64
        channel scheme (now GONE - see configure()'s own docstring; no
        bridge, no compatibility mode, per Waldek's own explicit
        decision) and this method's own remaining content, which has
        NOTHING to do with DI/DO channel addressing at all - Main
        View's cabinet-status panel and its electricity-simulation
        tags. Splitting them apart means epw_core.py can call THIS
        unconditionally (Main View's demo panel keeps working exactly
        as before, on every project, regardless of whether it has any
        real DI/DO cards configured) while the flat channel scheme
        stays gone for good, not because these tags happened to live
        in the same method.

        Renamed rather than kept as init_default_tags() with the DI/DO
        loops simply deleted - the old name specifically promised "the
        default TAG SET" (implying DI/DO among them); this name says
        what's actually left."""

        # The Main View used to carry a cabinet panel - health, inside and
        # outside temperature, humidity, door, heater, fan, alarm, fault -
        # whose nine values no sensor ever wrote: seeded defaults sitting
        # there looking like readings (24.8 C, "CLOSED", "RUNNING"). The
        # page is gone and so are they. A real cabinet measurement now
        # arrives as a real point on a real card and is drawn on the
        # Synoptic screen like any other value.
        #
        # What stays below is genuinely written by something: the
        # Device.*.Status tags (DeviceManager's poll-cycle watchdog) and
        # EMERGENCY_STOP.
        cabinet_tags = {
            # Seeded OFFLINE (not a hopeful "ONLINE" default): these flip to
            # ONLINE for real once DriverManager/DeviceManager report an
            # actual comm heartbeat (see EPWCore._on_device_status_changed).
            "Device.OrangePi.Status": ("OFFLINE", TagType.STRING,
                                        "Communication status (ONLINE/OFFLINE/COMM_FAILURE) of the Orange Pi "
                                        "controller itself, as tracked by DeviceManager's poll-cycle watchdog."),
            "Device.ELA01.Status": ("OFFLINE", TagType.STRING,
                                     "Communication status (ONLINE/OFFLINE/COMM_FAILURE) of digital-input "
                                     "module ELA01, as tracked by DeviceManager's poll-cycle watchdog."),
            "Device.ADA01.Status": ("OFFLINE", TagType.STRING,
                                     "Communication status (ONLINE/OFFLINE/COMM_FAILURE) of digital-output "
                                     "module ADA01, as tracked by DeviceManager's poll-cycle watchdog."),
            "Device.Modbus.Status": ("OFFLINE", TagType.STRING,
                                      "Communication status (ONLINE/OFFLINE/COMM_FAILURE) of the Modbus bus "
                                      "itself, as tracked by DeviceManager's poll-cycle watchdog."),
            "EMERGENCY_STOP": (False, TagType.BOOL,
                                "True while the hardware E-STOP circuit is tripped. Nothing in this simulated "
                                "environment currently writes it, but SafetyKernel/AlarmManager both react to "
                                "it as a real safety-relevant signal if something does."),
        }
        for k, (v, t, desc) in cabinet_tags.items():
            self.add_tag(k, v, t, description=desc)

        # Sim.Voltage: page_power_quality.py's voltage-amplitude slider
        # (simulation sandbox, no real signal) - was registered here with
        # the default GOOD quality, indistinguishable from a real reading
        # for any Historian export filtering on quality. Now explicit
        # SIMULATED, alongside Sim.Frequency just below it.
        self.add_tag(
            "Sim.Voltage", 230.0, TagType.REAL,
            description="Power Quality page voltage slider (simulation sandbox, no real signal)",
            source="SIMULATION", quality=TagQuality.SIMULATED,
        )

        # Meas.L1/L2/L3 (Task: zatrzymac zapisywanie zmyslonych pomiarow
        # do bazy danych) - page_entry_gate.py's recalculate_electricity()
        # writes these every 250ms, but nothing ever registered them as
        # real tags: every one of those update_tag() calls was silently
        # raising "Unknown tag" (caught only by main.py's top-level Qt
        # excepthook, which logs and moves on) and never reaching
        # tag_changed/Historian at all - a premise correction from the
        # task's own description ("baza wypelnia sie zmyslonymi
        # pomiarami"), documented in SESSION_REPORT.md. Registering them
        # properly, with quality=SIMULATED from the start (there is no
        # physical power meter behind them, see recalculate_electricity's
        # own update_tag() calls, which now pass quality=SIMULATED
        # explicitly on every write), is the prerequisite for Part 1's fix
        # to be meaningful and empirically testable at all - both the
        # "it doesn't crash" and "it's marked, not pretending to be real"
        # halves of the fix land on this one line.
        for meas_tag in ("Meas.L1", "Meas.L2", "Meas.L3"):
            self.add_tag(
                meas_tag, 0.0, TagType.REAL,
                description=f"Simulated bus voltage {meas_tag[-2:]} (no physical power meter installed)",
                source="SIMULATION", quality=TagQuality.SIMULATED,
            )

        # Meas.I1: the exact same "Unknown tag" gap as Meas.L1-3 above,
        # found while building this task's new "overload/rising current"
        # presentation scenario - protection_verifier.py's own Overcurrent
        # test mapping (see start_verification()) already targets
        # "Meas.I1" too, so this was a pre-existing gap in a fresh/
        # default project (Engineer Mode's own Overcurrent verification
        # test would have hit the same "Unknown tag" error), not
        # something newly introduced by this task - registering it here,
        # SIMULATED like every other Meas.* tag, fixes both at once.
        self.add_tag(
            "Meas.I1", 0.0, TagType.REAL,
            description="Simulated feeder current I1 (no physical CT installed)",
            source="SIMULATION", quality=TagQuality.SIMULATED,
        )

        # Sim.Frequency: same "Unknown tag" gap as Meas.L1-3 above, found
        # while fixing those - page_power_quality.py's frequency slider
        # (Part 3a of the same task) writes this tag on every move and was
        # silently raising every single time. Sim.Voltage already existed
        # (see cabinet_tags above); this just gives it the frequency
        # counterpart it never had.
        self.add_tag(
            "Sim.Frequency", 50.0, TagType.REAL,
            description="Power Quality page frequency slider (simulation sandbox, no real signal)",
            source="SIMULATION", quality=TagQuality.SIMULATED,
        )

