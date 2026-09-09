"""Process protections (Zabezpieczenia procesowe) - simple upper/lower
threshold + hysteresis + delay watchdogs on existing analog points
(Task: page-split, part 1). Headless (no PySide6 import), same rule
every other core/ module follows.

DIFFERENT MODULE from protection_manager.py's ELECTRICAL protection
settings (overcurrent/voltage/frequency relay-style function numbers,
in amps/volts/hertz/seconds, "docelowo wykonywane sprzetowo przez
ADA01" - a pure configuration table, never evaluated by this program
at all today). A process protection has no such hardware relay to
delegate to, so THIS module evaluates its own thresholds live, in
software, against a live TagManager reading of an existing analog
point - see list_analog_input_candidates() (reused directly from
intrusion_manager.py, not reimplemented; Task's own instruction:
"korzysta z listy punktow analogowych, ktora juz istnieje").

SCOPE, the same boundary intrusion_manager.py already established for
this codebase's other alarm-shaped modules (GRANICE: "NIE STERUJE
zadnym wyjsciem... wystawia sygnal przekroczenia jako tag, a reakcje
buduje uzytkownik w logice"): this module never writes to any driver/
DI/DO/output tag. It only reads an existing analog point's live value
and writes its OWN "Process.<id>.Exceeded" tag - built minimal, per
the task's own "Nic wiecej. Reszta moze dojsc pozniej."

DESIGN NOTE (this module's own call, not explicitly dictated by the
task): the "tag wyjsciowy dla logiki" the task lists as a configured
field is an AUTO-GENERATED, read-only tag name ("Process.<id>.
Exceeded"), shown in the GUI for the operator to reference from logic -
NOT a free-text field the user types a tag name into. Same convention
every other tag this codebase's alarm/supervision modules publish
already follows (Security.Line.<id>.*, Security.Zone.<id>.*) - a
user-typed arbitrary tag name would risk colliding with an existing
tag and has no precedent anywhere else in this program.

ARCHITECTURE
------------
A PROCESS PROTECTION is a user-named binding of one existing analog
point to:
- upper_threshold / lower_threshold - the "in range" band; the raw
  reading is EXCEEDED whenever it's above upper OR below lower
- hysteresis - how far back inside the band the reading must return
  before EXCEEDED clears (prevents chatter right at the boundary, the
  same purpose ProtectionStage.hysteresis already has on the
  electrical side)
- delay_seconds - how long the raw reading must stay outside the band
  before EXCEEDED actually latches (filters a brief spike/glitch, the
  same debounce concept intrusion_manager.py's own
  min_violation_seconds already uses for a line violation)
Persisted as project.json's "process_protections" list (see
ProjectManager.get/set_process_protections()) - same list-of-dicts
shape/lifecycle as intrusion's zones/lines.

Clearing (returning inside the hysteresis-adjusted band) is immediate,
no delay - the same asymmetric pickup/dropout convention a real
protection relay already has (and the electrical side's own
ProtectionStage.hysteresis/delay_ms pair implies, even though nothing
there is actually evaluated today).

A reading the module cannot resolve at all (the bound analog tag is
unregistered/removed) reads as "not exceeded" - the same "never
manufacture a false alarm from a dangling reference" stance
IntrusionManager.configure_power_supervision() already takes for an
unconfigured tag.
"""

import threading

from epw_os.core.access_manager import AccessLevel
from epw_os.core.logging import log
from epw_os.core.tag_manager import TagType
from epw_os.core.intrusion_manager import list_analog_input_candidates  # explicit reuse, not reinvented

TAG_PREFIX = "Process"

DEFAULT_HYSTERESIS = 0.0
DEFAULT_DELAY_SECONDS = 0.0

_PROTECTION_FIELDS = (
    "id", "name", "analog_tag", "upper_threshold", "lower_threshold",
    "hysteresis", "delay_seconds", "enabled",
)


def _level_rank(level) -> int:
    try:
        return AccessLevel._ORDER.index(level)
    except (ValueError, TypeError):
        # Already deliberate/documented (fail-closed, -1 sorts below
        # every real level) - now also logged, since `level` reaching
        # here unrecognized is always a caller bug, and silence is
        # exactly the "polykane wyjatki" pattern System.Mode had.
        log.warning(f"ProcessProtectionManager._level_rank() got an unrecognized level {level!r} - denying.")
        return -1  # unrecognized level is always denied, not trusted


def _next_id(prefix: str, existing: dict) -> str:
    """"PP1", "PP2", ... - a stable-for-life internal identity, distinct
    from the user-editable "name" (same "identity != description" split
    intrusion_manager.py's own _next_id() already establishes)."""
    max_seen = 0
    for existing_id in existing:
        if existing_id.startswith(prefix) and existing_id[len(prefix):].isdigit():
            max_seen = max(max_seen, int(existing_id[len(prefix):]))
    return f"{prefix}{max_seen + 1}"


def _normalize_protection(raw: dict) -> dict:
    """Backfills hysteresis/delay_seconds/enabled to their off-equivalent
    defaults for a record missing them - keeps this module symmetric
    with every other GRANICE-driven "no migration required" section in
    this codebase, even though process_protections is itself a brand
    new section with nothing to migrate FROM yet."""
    result = dict(raw)
    result.setdefault("hysteresis", DEFAULT_HYSTERESIS)
    result.setdefault("delay_seconds", DEFAULT_DELAY_SECONDS)
    result.setdefault("enabled", True)
    return result


class ProcessProtectionManager:
    def __init__(self, event_bus, tag_manager, project_manager, audit_logger=None):
        self.event_bus = event_bus
        self.tag_manager = tag_manager
        self.project_manager = project_manager
        self.audit_logger = audit_logger

        self._lock = threading.RLock()
        self._protections = {}    # id -> dict (see _PROTECTION_FIELDS)
        self._raw_exceeded = {}   # id -> bool, last raw (pre-delay) reading
        self._exceeded = {}       # id -> bool, post-delay latched state (drives the Exceeded tag)
        self._timers = {}         # id -> threading.Timer or None (pending delay_seconds confirmation)

        self._load_from_project()
        self.event_bus.subscribe("tag_changed", self._on_tag_changed)

    # --- persistence / loading -------------------------------------------

    def _load_from_project(self):
        for raw in self.project_manager.get_process_protections():
            protection = _normalize_protection(dict(raw))
            self._protections[protection["id"]] = protection
            self._raw_exceeded[protection["id"]] = False
            self._exceeded[protection["id"]] = False
            self._timers[protection["id"]] = None
        self._register_tags()
        # Seed live state from whatever the bound tag already holds right
        # now, not just future tag_changed events - construction happens
        # after analog input tags exist (see epw_core.py's startup()
        # ordering), same "don't rely solely on a future signal" pattern
        # intrusion_manager.py's own _load_from_project() already follows.
        for protection_id in list(self._protections):
            self._evaluate(protection_id, immediate=True)

    def _persist(self):
        with self._lock:
            snapshot = [dict(p) for p in self._protections.values()]
        self.project_manager.set_process_protections(snapshot)
        self.project_manager.save_project()

    # --- tags --------------------------------------------------------------

    def _exceeded_tag(self, protection_id: str) -> str:
        return f"{TAG_PREFIX}.{protection_id}.Exceeded"

    def _register_tags(self):
        for protection_id in self._protections:
            self.tag_manager.add_tag(
                self._exceeded_tag(protection_id), False, TagType.BOOL,
                description="True while this process protection's bound analog point is outside its "
                            "configured threshold band (past hysteresis/delay_seconds)", source="SYSTEM")

    # --- candidates (Task: "korzysta z listy punktow analogowych, ktora
    # juz istnieje") ---------------------------------------------------

    def get_analog_input_candidates(self) -> list:
        return list_analog_input_candidates(self.project_manager)

    # --- CRUD (Engineer-only, same pattern as intrusion_manager.py's
    # add_zone()/add_line()) ------------------------------------------

    def add_protection(self, name: str, analog_tag: str, upper_threshold: float, lower_threshold: float,
                        hysteresis: float = DEFAULT_HYSTERESIS, delay_seconds: float = DEFAULT_DELAY_SECONDS,
                        level: str = None) -> "str | None":
        if level is not None and _level_rank(level) < _level_rank(AccessLevel.ENGINEER):
            log.warning(f"Refused to add process protection {name!r}: level {level!r} is below Engineer.")
            return None
        with self._lock:
            protection_id = _next_id("PP", self._protections)
            protection = {
                "id": protection_id, "name": name, "analog_tag": analog_tag,
                "upper_threshold": float(upper_threshold), "lower_threshold": float(lower_threshold),
                "hysteresis": float(hysteresis), "delay_seconds": float(delay_seconds), "enabled": True,
            }
            self._protections[protection_id] = protection
            self._raw_exceeded[protection_id] = False
            self._exceeded[protection_id] = False
            self._timers[protection_id] = None
        self.tag_manager.add_tag(
            self._exceeded_tag(protection_id), False, TagType.BOOL,
            description="True while this process protection's bound analog point is outside its "
                        "configured threshold band (past hysteresis/delay_seconds)", source="SYSTEM")
        self._persist()
        if self.audit_logger is not None:
            self.audit_logger.record("PROCESS_PROTECTION_ADDED", level or "Engineer",
                                      f"Process protection '{name}' added on {analog_tag}", success=True)
        self._evaluate(protection_id, immediate=True)
        return protection_id

    def update_protection(self, protection_id: str, name: str = None, analog_tag: str = None,
                           upper_threshold: float = None, lower_threshold: float = None,
                           hysteresis: float = None, delay_seconds: float = None, enabled: bool = None,
                           level: str = None) -> bool:
        if level is not None and _level_rank(level) < _level_rank(AccessLevel.ENGINEER):
            log.warning(f"Refused to update process protection {protection_id!r}: level {level!r} is below Engineer.")
            return False
        with self._lock:
            protection = self._protections.get(protection_id)
            if protection is None:
                return False
            if name is not None:
                protection["name"] = name
            if analog_tag is not None:
                protection["analog_tag"] = analog_tag
            if upper_threshold is not None:
                protection["upper_threshold"] = float(upper_threshold)
            if lower_threshold is not None:
                protection["lower_threshold"] = float(lower_threshold)
            if hysteresis is not None:
                protection["hysteresis"] = float(hysteresis)
            if delay_seconds is not None:
                protection["delay_seconds"] = float(delay_seconds)
            if enabled is not None:
                protection["enabled"] = bool(enabled)
        self._persist()
        if self.audit_logger is not None:
            self.audit_logger.record("PROCESS_PROTECTION_UPDATED", level or "Engineer",
                                      f"Process protection '{protection['name']}' updated", success=True)
        self._evaluate(protection_id, immediate=True)
        return True

    def remove_protection(self, protection_id: str, level: str = None) -> bool:
        if level is not None and _level_rank(level) < _level_rank(AccessLevel.ENGINEER):
            log.warning(f"Refused to remove process protection {protection_id!r}: level {level!r} is below Engineer.")
            return False
        with self._lock:
            protection = self._protections.pop(protection_id, None)
            if protection is None:
                return False
            self._raw_exceeded.pop(protection_id, None)
            self._exceeded.pop(protection_id, None)
            timer = self._timers.pop(protection_id, None)
        if timer is not None:
            timer.cancel()
        self.tag_manager.remove_tag(self._exceeded_tag(protection_id))
        self._persist()
        if self.audit_logger is not None:
            self.audit_logger.record("PROCESS_PROTECTION_REMOVED", level or "Engineer",
                                      f"Process protection '{protection['name']}' removed", success=True)
        return True

    def get_protections(self) -> list:
        with self._lock:
            return [dict(p) for p in self._protections.values()]

    def get_protection(self, protection_id: str) -> "dict | None":
        with self._lock:
            p = self._protections.get(protection_id)
            return dict(p) if p is not None else None

    def is_exceeded(self, protection_id: str) -> bool:
        with self._lock:
            return bool(self._exceeded.get(protection_id, False))

    # --- evaluation ---------------------------------------------------

    def _on_tag_changed(self, tag_name, value, quality):
        matched = []
        with self._lock:
            for protection_id, protection in self._protections.items():
                if protection["analog_tag"] == tag_name:
                    matched.append(protection_id)
        for protection_id in matched:
            self._evaluate(protection_id, immediate=False)

    def _raw_is_exceeded(self, protection: dict) -> bool:
        """The un-hysteresis-adjusted band check - used only to DETECT a
        fresh excursion (see _evaluate() below); the actual EXCEEDED/
        clear decision always goes through the hysteresis-adjusted
        bounds so the tag doesn't chatter right at the threshold."""
        value = self.tag_manager.get_value(protection["analog_tag"])
        if value is None:
            return False  # unresolvable tag reads as "not exceeded" - see module docstring
        try:
            value = float(value)
        except (TypeError, ValueError):
            # A protection bound to a non-numeric tag (misconfiguration -
            # e.g. picked a STRING/BOOL tag by mistake) silently reading
            # as "never exceeded" is a safety-relevant silent failure: an
            # operator could believe this protection is live when it can
            # never actually trigger. Same "polykane wyjatki" pattern as
            # System.Mode - kept fail-safe (return False, unchanged), now
            # also logged.
            log.warning(f"Process protection on {protection['analog_tag']!r} read a non-numeric value "
                        f"{value!r} - treating as not-exceeded.")
            return False
        return value > protection["upper_threshold"] or value < protection["lower_threshold"]

    def _evaluate(self, protection_id: str, immediate: bool):
        """`immediate=True` (construction, or right after add/update) skips
        the delay entirely - Task: hysteresis/delay describe an ALREADY-
        RUNNING protection's behavior over time, not "wait before
        reporting the very first value ever seen", the same "seed from
        the current reading, not a future event" stance _load_from_project()
        already documents above."""
        with self._lock:
            protection = self._protections.get(protection_id)
            if protection is None:
                return
            if not protection["enabled"]:
                raw = False
            else:
                raw = self._raw_is_exceeded(protection)
            was_raw = self._raw_exceeded.get(protection_id, False)
            self._raw_exceeded[protection_id] = raw
            currently_latched = self._exceeded.get(protection_id, False)

            if currently_latched:
                # Hysteresis-adjusted clear check - only relevant while
                # already latched. Cleared immediately, no delay.
                value = self.tag_manager.get_value(protection["analog_tag"])
                cleared = True
                if value is not None:
                    try:
                        value = float(value)
                        hyst = protection["hysteresis"]
                        cleared = (protection["lower_threshold"] + hyst) <= value <= (protection["upper_threshold"] - hyst)
                    except (TypeError, ValueError):
                        # Same non-numeric-tag misconfiguration as
                        # _raw_is_exceeded() above - clearing a currently-
                        # latched protection because its own value became
                        # unreadable is the safe default (kept
                        # unchanged), but silent is still worth avoiding.
                        log.warning(f"Process protection {protection_id!r} on {protection['analog_tag']!r} "
                                    f"cleared: bound value {value!r} is not numeric.")
                        cleared = True
                if not protection["enabled"]:
                    cleared = True
                if cleared:
                    self._set_latched(protection_id, False)
                self._cancel_timer(protection_id)
                return

            if not raw:
                self._cancel_timer(protection_id)
                return

            # Freshly exceeded (or still exceeded from a prior tick that
            # hasn't latched yet) - only (re)start the delay timer on a
            # genuine secure->exceeded transition, same debounce shape
            # intrusion_manager.py's own _start_line_debounce_timer() uses.
            delay = protection["delay_seconds"]
            if immediate or delay <= 0:
                self._set_latched(protection_id, True)
                self._cancel_timer(protection_id)
                return
            if not was_raw or self._timers.get(protection_id) is None:
                self._cancel_timer(protection_id)
                timer = threading.Timer(delay, self._confirm_exceeded, args=(protection_id,))
                timer.daemon = True
                self._timers[protection_id] = timer
                timer.start()

    def _confirm_exceeded(self, protection_id: str):
        with self._lock:
            protection = self._protections.get(protection_id)
            self._timers[protection_id] = None
            if protection is None or not protection["enabled"]:
                return
            still_exceeded = self._raw_is_exceeded(protection)
        if still_exceeded:
            self._set_latched(protection_id, True)

    def _cancel_timer(self, protection_id: str):
        timer = self._timers.get(protection_id)
        if timer is not None:
            timer.cancel()
            self._timers[protection_id] = None

    def _set_latched(self, protection_id: str, exceeded: bool):
        with self._lock:
            if self._exceeded.get(protection_id) == exceeded:
                return
            self._exceeded[protection_id] = exceeded
        self.tag_manager.update_tag(self._exceeded_tag(protection_id), exceeded)

    # --- lifecycle (Task: feature-configuration toggle - "wylaczona
    # funkcja... nie tworzy watkow ani timerow... nie rejestruje swoich
    # tagow"). One method covers both a live feature-disable AND process
    # shutdown - unlike IntrusionManager this module has no background
    # thread of its own (only per-protection delay timers) and no "leave
    # tags in place, the whole TagManager is about to disappear anyway"
    # distinction worth making. Deliberately does NOT touch project.json -
    # the protections list stays exactly as configured, a later re-enable
    # constructs a brand new manager from that same, untouched data. ----

    def teardown(self):
        self.event_bus.unsubscribe("tag_changed", self._on_tag_changed)
        with self._lock:
            protection_ids = list(self._protections.keys())
            timers = list(self._timers.values())
        for timer in timers:
            if timer is not None:
                timer.cancel()
        for protection_id in protection_ids:
            self.tag_manager.remove_tag(self._exceeded_tag(protection_id))
