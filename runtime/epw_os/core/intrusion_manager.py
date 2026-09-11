"""Intrusion (burglar) alarm system - supervision lines, zones, arming
(Task: "system alarmowy: uzbrajanie, stan systemu, konfigurowalne linie
dozorowe i strefy"). Headless (no PyQt import), same rule as every other
core/ module.

DIFFERENT DOMAIN from epw_os/core/alarm_manager.py (Task's own GRANICE:
"nie mieszaj z AlarmManagerem od alarmow procesowych... jesli uznasz, ze
warto je polaczyc, ZATRZYMAJ SIE i uzasadnij zamiast decydowac samemu").
Kept deliberately separate here - not touched, not imported, not
subclassed:

- AlarmManager models PROCESS alarms (device comm failure, EMERGENCY_STOP)
  - conditions about the plant/hardware itself, always active regardless
  of any "armed" concept, acknowledged one at a time, independent of any
  zone.
- IntrusionManager models an INTRUSION DETECTION panel - zones that are
  deliberately either watching or not (armed/disarmed), lines that only
  matter in some states and not others, entry/exit grace periods, and a
  bypass concept - none of which have any equivalent in AlarmManager's
  model at all. Forcing them into one shape (one Alarm class, one
  "active alarms" list) would need bolting zone/arming/bypass concepts
  onto a class that has no such fields today, or duplicating this
  module's own state machine inside AlarmManager - strictly worse than
  two small, focused modules. Recommendation, not touched here: if a
  later task wants a single "all alarms" GUI view, that view can read
  both managers and merge for DISPLAY only, without either manager's
  own model changing.

SCOPE, per GRANICE ("OS dostarcza STAN i KONFIGURACJE... reakcje na
naruszenie naleza do logiki uzytkownika"): this module NEVER writes to
any driver, output tag, or notification channel. It only (a) reads DI
tag values already published by TagManager/drivers, (b) writes its own
"Security.*" tags (see the module-level docstring section below the
class for the full list) so logic can react however the user wants, and
(c) accepts zone arm/disarm requests, from the GUI or from logic through
those same tags (Task 5: "Przyjmuj tez jako WEJSCIE z logiki: zadanie
uzbrojenia i rozbrojenia strefy"). Nothing here ever calls
tag_manager.update_tag() on a DI/DO/output tag, and nothing here imports
driver_manager - see test_intrusion_manager.py's
test_never_writes_to_any_non_security_tag for the empirical proof of
that boundary, not just the claim.

ARCHITECTURE
------------
- A LINE (linia dozorowa) is a user-named binding of one existing
  TagManager tag (typically a DI, but nothing here assumes that - any
  tag works) to a `line_type` and a `zone_id`. `normal_state` says which
  raw tag value means "secure" (NC: True/closed is secure, tripped ->
  False; NO: False/open is secure, tripped -> True) - see
  is_line_violated() below.
- A ZONE (strefa) is a user-named group of lines, armed/disarmed as a
  unit, with its own exit_delay_seconds/entry_delay_seconds.
- Both are plain persisted dicts (project.json's new "intrusion_zones"/
  "intrusion_lines" lists - see ProjectManager.get_intrusion_zones()/
  get_intrusion_lines()), same shape/lifecycle as
  ProjectManager.get_analog_points()'s dynamic list-of-records pattern -
  not a fixed slot count, not a migration target (this is a brand new
  section; GRANICE requires no migration for existing projects, and
  there is nothing to migrate FROM).
- BYPASS is deliberately session-only, never persisted - same reasoning
  epw_os/core/training_mode.py already established for its own on/off
  flag: a restarted system must never silently come back up with a
  sensor invisible to arming/alarm without a person re-deciding that
  today, on this run. A bypass is recorded to the audit log (Task
  requirement) but is gone on the next restart.

ZONE STATE MACHINE (Task 3's 5 states, exactly)
------------------------------------------------
DISARMED -> EXIT_DELAY -> ARMED -> ENTRY_DELAY -> ALARM, plus ARMED can
go straight to ALARM (an INSTANT line trips) and DISARMED can go
straight to ALARM (a 24H line trips, any zone state). disarm_zone()
always returns a zone to DISARMED from any state, cancelling whatever
timer is pending - see disarm_zone()'s own docstring.

Per-line-type reaction to a (non-bypassed) violation - see
_handle_violation() for the actual dispatch:
- SUPERVISORY (DOZOROWA): NEVER changes any zone/system state, in any
  zone state, ever. Only its own Line.<id>.Violated tag and the
  Supervisory.Violated aggregate move (Task: "sygnalizowane, ale NIE
  wywoluje alarmu").
- 24H (CALODOBOWA): ALWAYS raises ALARM on its own zone, regardless of
  that zone's current state - including DISARMED (Task: "alarm
  niezaleznie od stanu uzbrojenia").
- INSTANT (NATYCHMIASTOWA): raises ALARM immediately, but only while its
  zone is ARMED. While DISARMED, EXIT_DELAY or ENTRY_DELAY, a violation
  is a no-op for this line type (see the EXIT_DELAY/ENTRY_DELAY note
  below for why).
- DELAYED (ZWLOCZNA): while ARMED, starts that zone's entry-delay
  countdown (-> ENTRY_DELAY); while already in ENTRY_DELAY, a further
  trip (the same line flapping, or a second delayed line) does not
  restart or shorten the countdown already running. While DISARMED or
  EXIT_DELAY, a no-op.

EXIT_DELAY/ENTRY_DELAY are zone-wide grace periods, not per-line: while
either is running, INSTANT/DELAYED lines in that zone are deliberately
inert (the whole point of a grace period is "the system is not yet/no
longer treating this zone as watching"). Only a 24H line pierces that,
by design, on any state.

LINE SUPERVISION (this task's own additions - see the class docstring
sections just above each area's own code for the full detail)
-----------------------------------------------------------------------
- INPUT MODE (LineInputMode): every line is CONTACT (a DI + NC/NO,
  exactly what a line always was) or PARAMETRIZED (an analog point +
  EOL/DEOL value windows). Classification -> LineState.* via
  _classify_line_state() - SECURE/VIOLATED are the only two states a
  CONTACT-mode line ever produces; a PARAMETRIZED-mode line can also
  produce TAMPER/SHORT/FAULT_OPEN/UNDETERMINED, collectively a LINE
  FAULT (is_line_fault_state()) - a fault alarms immediately, in every
  zone state, for EVERY line type INCLUDING SUPERVISORY (a severed
  cable or a removed tamper resistor is a maintenance/sabotage event,
  not "motion in front of a sensor" - SUPERVISORY's "never alarms" rule
  is specifically about the latter; see _dispatch_line_fault()'s own
  docstring for the full reasoning). Only a plain VIOLATION (not a
  fault) still respects SUPERVISORY's "never alarms, any state" rule -
  see _handle_violation().
- POWER SUPERVISION (mains/battery) is a single, optional, system-wide
  config (not per-zone/per-line) - see configure_power_supervision()/
  _recompute_power_state(). Raises Security.System.TechnicalAlarm, a
  DIFFERENT category from the intrusion Security.System.Alarm above,
  and never blocks arm_zone()/disarm_zone() (neither method reads it).
- LINE LIFE/SILENCE SUPERVISION: a per-line violation-history record
  (count/timestamps/total-violated-time - see _new_line_life_record())
  plus an optional silence_threshold_seconds; exceeding it marks a line
  SUSPECT (a WARNING, never an alarm) - see _check_line_silence().
"""
import math
import threading
import time

from epw_os.core.access_manager import AccessLevel
from epw_os.core.logging import log
from epw_os.core.tag_manager import TagType

PROJECT_KEY_ZONES = "intrusion_zones"
PROJECT_KEY_LINES = "intrusion_lines"

TAG_PREFIX = "Security"

# Task "migracja adresacji": was a bespoke regex (`r"(^|\.)DI\d+$"`) -
# already the ONE of three independent, disagreeing "what is a DI tag"
# opinions (ADDRESSING_INVENTORY.md §3.2c) that DID match this
# codebase's own multi-device shape at the time (`{dev}.DI01`) - but not
# the platform-wide three-segment grammar this task establishes
# (`{dev}.DI.1`, a dot before the channel number too). Replaced with the
# one shared grammar check every subsystem now uses instead of its own
# opinion - see epw_os/core/addressing.py.
from epw_os.core.addressing import is_address


def list_digital_input_candidates(tag_manager) -> list:
    """Every BOOL tag that looks like a digital input - the CONTACT-mode
    picker Task part 1 requires ("w trybie stykowym tylko cyfrowe").
    Excludes DO/Security.*/other internal BOOL flags by construction
    (name pattern, not just data_type) - a generic TagType.BOOL scan
    alone would also catch every digital OUTPUT and internal flag."""
    return sorted(
        t.name for t in tag_manager.list_tags()
        if t.data_type == TagType.BOOL and is_address(t.name, "DI")
    )


def list_analog_input_candidates(project_manager) -> list:
    """Every configured analog point's tag - the PARAMETRIZED-mode
    picker Task part 1 requires ("w parametryzowanym tylko analogowe").
    Reads project_manager.get_analog_points() (the authoritative,
    already-existing source of "which analog points exist" - see
    page_analog_inputs.py) rather than a heuristic TagType.REAL scan of
    every tag, which would also catch measurement tags that are real
    numbers but not analog INPUT POINTS at all (UL1.RMS, FREQ,
    Cabinet.TempInside, ...)."""
    return sorted(p["tag"] for p in project_manager.get_analog_points())


class LineType:
    """NATYCHMIASTOWA / ZWLOCZNA / CALODOBOWA / DOZOROWA - see the module
    docstring's "per-line-type reaction" section for what each one does."""
    INSTANT = "INSTANT"
    DELAYED = "DELAYED"
    TWENTY_FOUR_HOUR = "24H"
    SUPERVISORY = "SUPERVISORY"
    _ALL = (INSTANT, DELAYED, TWENTY_FOUR_HOUR, SUPERVISORY)


class ZoneState:
    """ROZBROJONA / ODLICZANIE_WYJSCIA / UZBROJONA / ODLICZANIE_WEJSCIA /
    ALARM - Task 3's 5 states, exactly, both per-zone and (via
    IntrusionManager.get_system_state()) system-wide."""
    DISARMED = "DISARMED"
    EXIT_DELAY = "EXIT_DELAY"
    ARMED = "ARMED"
    ENTRY_DELAY = "ENTRY_DELAY"
    ALARM = "ALARM"
    # Priority order for the system-wide aggregate (most urgent first) -
    # see get_system_state()'s docstring for the exact rule.
    _PRIORITY = (ALARM, ENTRY_DELAY, EXIT_DELAY, ARMED, DISARMED)


NORMAL_STATE_NC = "NC"  # Normally Closed - secure = tag True, tripped = False
NORMAL_STATE_NO = "NO"  # Normally Open   - secure = tag False, tripped = True

# --- line input mode (Task: "tryb pracy linii - dwa wykluczajace sie
# warianty") --------------------------------------------------------------


class LineInputMode:
    """STYKOWY (contact) or PARAMETRYZOWANY (parametrized) - which input
    a line is bound to and how its state gets read. CONTACT is the
    DEFAULT and is exactly what every line was before this task existed
    (a DI tag + NC/NO) - an old project.json line dict has no
    `input_mode` key at all, and _normalize_line() below backfills
    CONTACT for it, so nothing about an unsupervised line's behavior
    changes (Task: "wszystkie istniejace konfiguracje maja automatycznie
    trafic do niego, bez migracji i bez zmiany zachowania")."""
    CONTACT = "CONTACT"
    PARAMETRIZED = "PARAMETRIZED"
    _ALL = (CONTACT, PARAMETRIZED)


DEFAULT_LINE_INPUT_MODE = LineInputMode.CONTACT


class LineParametrization:
    """EOL (pojedyncza/single) or DEOL (podwojna/double) - only
    meaningful for a PARAMETRIZED-mode line. See default_value_windows()
    for each variant's state set and default windows."""
    EOL = "EOL"
    DEOL = "DEOL"
    _ALL = (EOL, DEOL)


DEFAULT_PARAMETRIZATION = LineParametrization.EOL


class LineState:
    """The classified state of a line's monitored input, RAW - i.e.
    bypass-independent, the same "always show the truth" stance
    is_line_violated_now() already has for the simpler CONTACT-only
    True/False case this generalizes.

    A CONTACT-mode line only ever produces SECURE or VIOLATED (exactly
    is_line_violated()'s own two outcomes, renamed to fit this shared
    vocabulary). A PARAMETRIZED-mode line can produce any of the six -
    TAMPER/SHORT/FAULT_OPEN/UNDETERMINED are collectively a LINE FAULT
    (see is_line_fault_state()) - Task: "traktowane jako AWARIA LINII -
    alarmuja niezaleznie od stanu uzbrojenia, jak linia calodobowa"."""
    SECURE = "SECURE"
    VIOLATED = "VIOLATED"
    TAMPER = "TAMPER"
    SHORT = "SHORT"
    FAULT_OPEN = "FAULT_OPEN"       # "przerwa"
    UNDETERMINED = "UNDETERMINED"   # value inside no configured window at all


_LINE_FAULT_STATES = (LineState.TAMPER, LineState.SHORT, LineState.FAULT_OPEN, LineState.UNDETERMINED)


def is_line_fault_state(state: str) -> bool:
    return state in _LINE_FAULT_STATES


# Deterministic check order for classify_parametrized_value() below - not
# dict-iteration order, so a misconfigured OVERLAPPING set of windows still
# resolves the same way every time rather than depending on dict internals.
_PARAM_STATE_CHECK_ORDER = (
    LineState.SHORT, LineState.VIOLATED, LineState.SECURE, LineState.TAMPER, LineState.FAULT_OPEN,
)


def default_value_windows(parametrization: str) -> dict:
    """Sensible PLACEHOLDER windows on a plain 0-100 engineering-unit
    scale (matching analog_scaling.py's own default_channel_config()
    eng_min/eng_max=0..100) - Task: "NIE zaszywaj konkretnych
    rezystancji ani pradow... podaj sensowne wartosci domyslne i pozwol
    je zmienic". The real ELA01 resistor-network bands depend on
    hardware not yet chosen; whatever they turn out to be, an Engineer
    edits these same windows per line in ENGINEERING units (i.e. after
    analog_scaling.py's own raw->engineering conversion already ran),
    not raw ADC counts - one less thing to reconcile once real values
    exist. Deliberately spaced with a gap between every band, so an
    out-of-range reading reliably lands in UNDETERMINED rather than one
    band silently bleeding into its neighbor."""
    if parametrization == LineParametrization.DEOL:
        return {
            LineState.SHORT: [0.0, 10.0],
            LineState.VIOLATED: [20.0, 30.0],
            LineState.SECURE: [45.0, 55.0],
            LineState.TAMPER: [70.0, 80.0],
            LineState.FAULT_OPEN: [90.0, 100.0],
        }
    return {  # EOL - also the fallback for an unrecognized parametrization
        LineState.VIOLATED: [0.0, 20.0],
        LineState.SECURE: [45.0, 55.0],
        LineState.FAULT_OPEN: [90.0, 100.0],
    }


def classify_parametrized_value(value, value_windows: dict) -> str:
    """Which state's window `value` (already in engineering units) falls
    into - the first match in _PARAM_STATE_CHECK_ORDER, not raw dict
    order. A value inside no window at all - or no value at all (an
    unresolvable analog tag) - is UNDETERMINED (Task: "wartosc poza
    wszystkimi oknami = stan nieokreslony, traktowany jako awaria
    linii"). A parametrization missing a given state's window entirely
    (e.g. EOL has no TAMPER/SHORT band) just never matches it - no
    special-casing needed here, the windows dict IS the state set."""
    if value is None:
        return LineState.UNDETERMINED
    for state in _PARAM_STATE_CHECK_ORDER:
        window = value_windows.get(state)
        if window is None or len(window) != 2:
            continue
        lo, hi = window
        if lo <= value <= hi:
            return state
    return LineState.UNDETERMINED


# --- false-alarm filtering (Task, part 2) -----------------------------------
# Per-line, all defaulting to exactly today's behavior - an old project.json
# line dict predates every one of these keys, and _normalize_line_filters()
# (called wherever a line dict is loaded or created) backfills them via
# dict.setdefault(), so an existing configuration needs no migration step at
# all: it simply reads back with every filter off.
DEFAULT_MIN_VIOLATION_SECONDS = 0.0        # 0 = off: any instantaneous trip counts, as today
DEFAULT_MULTIPLICITY_COUNT = 1             # 1 = off: a single violation is enough, as today
DEFAULT_MULTIPLICITY_WINDOW_SECONDS = 10.0  # only consulted when multiplicity_count > 1
DEFAULT_LOCKOUT_AFTER_COUNT = 0            # 0 = off: never auto-locks, as today
DEFAULT_ALARM_HOLD_SECONDS = 0.0           # 0 = off: alarm persists until manual disarm, as today


DEFAULT_SILENCE_THRESHOLD_SECONDS = 0  # 0 = off: life/silence supervision disabled, as today

# Task (tryb chodzenia - "wylacza sie SAM po konfigurowalnym czasie
# (domyslnie 30 minut)"): the default duration a caller gets by not
# passing duration_seconds to start_walk_test() explicitly.
DEFAULT_WALK_TEST_DURATION_SECONDS = 1800.0


def _normalize_line_filters(line: dict) -> dict:
    """Backfills every OPTIONAL per-line parameter this task and its
    predecessor added, onto a line dict that may predate some or all of
    them - the ONLY place their defaults are spelled out, so
    _load_from_project() (an old project.json), add_line() (a brand new
    line) and update_line()'s own read-modify-write all agree. Mutates
    and returns `line`.

    input_mode defaulting to CONTACT is what makes an old line dict (no
    input_mode/parametrization/value_windows keys at all) behave
    exactly as before, unmigrated (Task: "wszystkie istniejace
    konfiguracje maja automatycznie trafic do niego, bez migracji i bez
    zmiany zachowania") - normal_state/tag, its existing CONTACT-mode
    fields, are untouched here."""
    line.setdefault("min_violation_seconds", DEFAULT_MIN_VIOLATION_SECONDS)
    line.setdefault("multiplicity_count", DEFAULT_MULTIPLICITY_COUNT)
    line.setdefault("multiplicity_window_seconds", DEFAULT_MULTIPLICITY_WINDOW_SECONDS)
    line.setdefault("lockout_after_count", DEFAULT_LOCKOUT_AFTER_COUNT)
    line.setdefault("alarm_hold_seconds", DEFAULT_ALARM_HOLD_SECONDS)
    line.setdefault("silence_threshold_seconds", DEFAULT_SILENCE_THRESHOLD_SECONDS)
    line.setdefault("input_mode", DEFAULT_LINE_INPUT_MODE)
    line.setdefault("parametrization", DEFAULT_PARAMETRIZATION)
    if "value_windows" not in line or not line["value_windows"]:
        line["value_windows"] = default_value_windows(line["parametrization"])
    return line


def is_line_violated(tag_value, normal_state: str) -> bool:
    """True when the raw tag value is NOT the configured secure state.
    NC (normally closed - most burglar contacts): secure = closed loop =
    True; a break (tamper, door open) reads False -> violated. NO
    (normally open): secure = open = False; a trip closes the contact ->
    True -> violated. An unrecognized normal_state defaults to NC (the
    more common wiring), never raises."""
    secure_value = (normal_state != NORMAL_STATE_NO)
    return bool(tag_value) != secure_value


class ArmResult:
    """Returned by arm_zone() - never raises for the "line violated" or
    "line faulted" case (Task 4 (predecessor): "Uzbrojenie mimo to ma
    byc mozliwe, ale musi wymagac jawnego potwierdzenia"; this task's
    own part 4: the same requirement, extended to a line in FAULT -
    sabotage/short/break/undetermined), so both the GUI and a
    logic-driven caller get a uniform, inspectable answer instead of an
    exception. `fault_line_ids` is disjoint from `violated_line_ids` -
    a line is classified into exactly one LineState.* at a time (see
    that class's own docstring), never both."""
    def __init__(self, success: bool, needs_confirmation: bool = False,
                 violated_line_ids=None, fault_line_ids=None, reason: str = ""):
        self.success = success
        self.needs_confirmation = needs_confirmation
        self.violated_line_ids = list(violated_line_ids or [])
        self.fault_line_ids = list(fault_line_ids or [])
        self.reason = reason

    def __repr__(self):
        return (f"ArmResult(success={self.success}, needs_confirmation={self.needs_confirmation}, "
                f"violated_line_ids={self.violated_line_ids}, fault_line_ids={self.fault_line_ids}, "
                f"reason={self.reason!r})")


def _level_rank(level) -> int:
    try:
        return AccessLevel._ORDER.index(level)
    except (ValueError, TypeError):
        # Already deliberate/documented (fail-closed, -1 sorts below
        # every real level) - now also logged, since `level` reaching
        # here unrecognized is always a caller bug, and silence is
        # exactly the "polykane wyjatki" pattern System.Mode had.
        log.warning(f"IntrusionManager._level_rank() got an unrecognized level {level!r} - denying.")
        return -1  # unrecognized level is always denied, not trusted


def _next_id(prefix: str, existing: dict) -> str:
    """"Z1", "Z2", ... / "L1", "L2", ... - a stable-for-life internal
    identity (used in tag names and every persisted reference), distinct
    from the user-editable "name" - so renaming a zone/line never
    breaks a tag path or a project.json cross-reference (same
    "identity != description" split as output_descriptions/DO0N tags
    elsewhere in this codebase)."""
    max_seen = 0
    for existing_id in existing:
        if existing_id.startswith(prefix) and existing_id[len(prefix):].isdigit():
            max_seen = max(max_seen, int(existing_id[len(prefix):]))
    return f"{prefix}{max_seen + 1}"


# --- line life/silence supervision (Task part 3) ----------------------------
# "Wykorzystaj mechanizm licznikow polaczen (switching_counters.py), jesli
# sie nadaje - nie buduj drugiego rownoleglego." Evaluated, partially
# reused, partially not - see SESSION_REPORT.md for the full reasoning.
# In short: SwitchingCounterManager the CLASS doesn't fit - its
# _on_tag_changed() is hardcoded to tag names starting with "DI" (a
# PARAMETRIZED-mode line watches an analog tag, which would silently
# never be counted at all) and it has no public method to record a
# transition for an arbitrary key without going through that filter.
# What DOES transfer directly: the RECORD SHAPE and its display helper -
# imported below, not reimplemented - so "how a growing counter is
# persisted efficiently" isn't invented a second time, only "which
# object watches for a transition and calls the counter" differs (this
# module's own violation-transition detection, which already exists and
# already knows about CONTACT vs PARAMETRIZED, bypass, and every filter
# from the prior task - re-deriving violation detection a SECOND time
# via a generic tag-name watcher would be the actual parallel mechanism
# this instruction warns against).
from epw_os.core.switching_counters import new_record as _new_switching_record, format_duration  # noqa: E402

_LINE_LIFE_RECORD_KEYS = (
    "closes", "opens", "closed_seconds", "closed_since",
    "first_transition", "last_transition", "last_violation_at",
)


def _new_line_life_record() -> dict:
    """Same base shape as switching_counters.new_record() (closes/opens/
    closed_seconds/closed_since/first_transition/last_transition,
    "closed" read here as "violated") plus one field that shape didn't
    need: `last_violation_at`, updated ONLY on a violation-entering
    edge - `last_transition` (inherited) fires on either edge, which
    would answer "when was this line last disturbed at all", not the
    Task's own more specific "czas ostatniego naruszenia". This
    record's own `warning_threshold` (inherited, a violation-COUNT
    concept in switching_counters.py) is left unused/None here - line
    supervision's threshold is TIME-based (silence_threshold_seconds,
    on the line dict itself, not in this record)."""
    record = _new_switching_record()
    record["last_violation_at"] = None
    return record


def _normalize_line_life_record(raw, line_id: str = None) -> dict:
    """Never raises - a corrupt/partial/old-format persisted record
    falls back to a fresh one, same defensive stance as every other
    load_*() in this codebase (e.g. window_state.py,
    switching_counters._normalize_record()). `line_id` is optional and
    used only for the log line below - passing it costs the caller
    nothing when known, and its absence changes no behavior."""
    record = _new_line_life_record()
    if not isinstance(raw, dict):
        return record
    for key in _LINE_LIFE_RECORD_KEYS:
        if key in raw:
            record[key] = raw[key]
    try:
        record["closes"] = int(record["closes"])
        record["opens"] = int(record["opens"])
        record["closed_seconds"] = float(record["closed_seconds"])
    except (TypeError, ValueError):
        # A corrupt/incompatible persisted line-life record silently
        # resetting a line's violation-counting history is real data
        # loss with no other trace - worth a log line, same "polykane
        # wyjatki" pattern as System.Mode.
        log.warning(f"Resetting corrupt line-life record for line {line_id!r}: {raw!r}")
        return _new_line_life_record()
    return record


# --- power supervision (Task part 2) ----------------------------------------

_POWER_SUPERVISION_KEYS = ("mains_tag", "mains_ok_state", "battery_tag", "battery_ok_state")


def _normalize_power_supervision(raw) -> dict:
    """Never raises. Missing/invalid keys default to "not configured, no
    supervision" (mains_tag/battery_tag None) - Task: "brak konfiguracji
    oznacza brak nadzoru, bez bledow" - never "assume some tag" as a
    fallback."""
    result = {"mains_tag": None, "mains_ok_state": True, "battery_tag": None, "battery_ok_state": True}
    if not isinstance(raw, dict):
        return result
    for key in _POWER_SUPERVISION_KEYS:
        if key in raw:
            result[key] = raw[key]
    result["mains_tag"] = result["mains_tag"] or None
    result["battery_tag"] = result["battery_tag"] or None
    result["mains_ok_state"] = bool(result["mains_ok_state"])
    result["battery_ok_state"] = bool(result["battery_ok_state"])
    return result


# --- alarm memory / first cause (Task: "pierwsza przyczyna alarmu" +
# "pamiec alarmu") ------------------------------------------------------
# A per-zone LATCH, same principle safety_kernel.py's own latch already
# uses ("zdarzenie, ktore minelo, nadal sie wydarzylo") - once any alarm
# raises for a zone, "active" goes True and the triggering line/reason/
# time are recorded as the FIRST CAUSE. Every further alarm in that same
# zone - whether a second line trips moments later, or the zone auto-
# recovers (alarm_hold_seconds) and then alarms again on a LATER, still-
# uncleared cycle - is appended to `subsequent`, never overwrites the
# first cause. disarm_zone() deliberately does NOT touch this (Task 3:
# "po rozbrojeniu informacja... NIE MOZE zniknac bez sladu") - only
# clear_alarm_memory() (Operator+, explicit) resets it, and it is
# persisted so it also survives a restart (Task: "MA PRZEZYC restart
# programu").
_ALARM_MEMORY_KEYS = (
    "active", "first_cause_line_id", "first_cause_line_name", "first_cause_reason", "first_cause_at", "subsequent",
)


def _new_zone_alarm_memory() -> dict:
    return {
        "active": False,
        "first_cause_line_id": None, "first_cause_line_name": None,
        "first_cause_reason": None, "first_cause_at": None,
        "subsequent": [],  # list of {"line_id", "line_name", "reason", "at"}, oldest first
    }


def _normalize_zone_alarm_memory(raw) -> dict:
    """Never raises - a corrupt/partial/old-format persisted record
    falls back to a fresh, inactive one, same defensive stance
    _normalize_line_life_record() already has."""
    record = _new_zone_alarm_memory()
    if not isinstance(raw, dict):
        return record
    for key in _ALARM_MEMORY_KEYS:
        if key in raw:
            record[key] = raw[key]
    record["active"] = bool(record["active"])
    if not isinstance(record["subsequent"], list):
        record["subsequent"] = []
    return record


class IntrusionManager:
    def __init__(self, event_bus, tag_manager, project_manager, audit_logger=None, alarm_history_logger=None):
        self.event_bus = event_bus
        self.tag_manager = tag_manager
        self.project_manager = project_manager
        self.audit_logger = audit_logger
        # Task (historia zdarzen alarmowych): optional, same "works fine
        # if not wired up" stance audit_logger already has everywhere in
        # this module (every self.audit_logger call is already guarded
        # by `if self.audit_logger is not None`) - see intrusion_history.py.
        self.alarm_history_logger = alarm_history_logger

        self._lock = threading.RLock()
        self._zones = {}          # zone_id -> {"id", "name", "exit_delay_seconds", "entry_delay_seconds"}
        self._lines = {}          # line_id -> {"id", "name", "zone_id", "tag", "normal_state", "line_type"}
        self._zone_state = {}     # zone_id -> ZoneState.*
        self._zone_timer = {}     # zone_id -> threading.Timer or None
        self._zone_deadline = {}  # zone_id -> time.monotonic() when the current countdown ends
        self._entry_trigger_line = {}  # zone_id -> line_id that started the current ENTRY_DELAY
        self._line_bypassed = {}  # line_id -> bool, session-only (see module docstring)

        # --- false-alarm filtering (Task, part 2) - all session-only,
        # same reasoning as _line_bypassed: a restarted system starts
        # every filter's running state fresh, never silently resuming a
        # half-finished debounce/multiplicity window or a lock from
        # before restart. The line's own CONFIGURATION (min_violation_
        # seconds etc., in self._lines) IS persisted, as normal.
        self._line_raw_violated = {}       # line_id -> bool, last raw (pre-filter) reading
        self._line_counted_violated = {}   # line_id -> bool, post-min_violation_seconds state (drives the Violated tag)
        self._line_debounce_timer = {}     # line_id -> Timer or None (min_violation_seconds)
        self._line_multiplicity_count = {}  # line_id -> int, violations counted in the current window
        self._line_multiplicity_timer = {}  # line_id -> Timer or None (window reset)
        self._line_locked = {}             # line_id -> bool (auto-lock after repeated alarms)
        self._line_alarm_count_cycle = {}  # line_id -> int, alarms raised THIS arm cycle (reset on disarm)
        self._zone_alarm_trigger_line = {}  # zone_id -> line_id that raised the current ALARM, or None
        self._zone_alarm_hold_timer = {}   # zone_id -> Timer or None (alarm_hold_seconds)

        # --- line supervision (this task) - RAW classified state and the
        # FAULT axis are session-only, same reasoning as everything
        # above; the LIFE record (violation counters/timestamps) is the
        # one thing here that IS persisted - see _new_line_life_record()
        # and start()/flush_line_supervision() below.
        self._line_state = {}              # line_id -> LineState.* (RAW, bypass-independent - drives the State tag)
        self._line_raw_fault = {}          # line_id -> bool, last raw (pre-bypass) fault reading
        self._line_counted_fault = {}      # line_id -> bool, bypass-adjusted - drives the Fault tag
        self._line_life = {}               # line_id -> record dict (see _new_line_life_record())
        self._line_life_dirty = False
        self._line_suspect = {}            # line_id -> bool (silence_threshold_seconds exceeded)
        self._line_supervision_started_at = {}  # line_id -> time.time() when first loaded/added - the
                                                 # "uruchomienia" baseline for a line with no violation yet

        # --- power supervision (this task) - the CONFIG is persisted
        # (project_manager.get/set_intrusion_power_supervision()); the
        # live ok/not-ok booleans are session-only, recomputed from
        # whatever the referenced tags currently say, same as every
        # other live status in this module. "mains_ok_state"/
        # "battery_ok_state" (below) are UNCHANGED by the polarity fix -
        # they describe which RAW INPUT reading means healthy, entirely
        # independent of how the DERIVED Security.Power.* tag is named
        # or polarized (see fix/power-supervision-polarity's own
        # SESSION_REPORT.md for why no project.json migration was
        # needed for this section at all).
        self._power_supervision = {
            "mains_tag": None, "mains_ok_state": True,
            "battery_tag": None, "battery_ok_state": True,
        }
        # Fix (power-supervision-polarity): renamed from _mains_failed/
        # _battery_fault, TRUE now means HEALTHY (matches the tags these
        # drive - Security.Power.MainsOk/BatteryOk) - the exact same
        # rename+invert this whole task applies everywhere the old
        # Failed/Fault booleans appeared, so nothing in this module is
        # left mixing "True=healthy" and "True=failed" variables.
        self._mains_ok = True
        self._battery_ok = True

        # --- alarm memory / first cause (this task) - PERSISTED (see
        # module docstring section above _new_zone_alarm_memory()) -
        # written immediately on every change, not buffered.
        self._zone_alarm_memory = {}  # zone_id -> record (see _new_zone_alarm_memory())

        # --- walk-test mode (this task) - entirely session-only, same
        # reasoning as bypass: a restarted system must never silently
        # come back up mid-test with sensors not actually being
        # monitored for real - see start_walk_test()'s own docstring.
        self._zone_walk_test_active = {}     # zone_id -> bool
        self._zone_walk_test_deadline = {}   # zone_id -> time.monotonic() when it auto-ends, or None
        self._zone_walk_test_timer = {}      # zone_id -> Timer or None
        self._zone_walk_test_observed = {}   # zone_id -> {line_id: {"count": int, "last_at": time.time()}}

        self._stop_event = threading.Event()
        self._thread = None

        self._load_from_project()
        self.event_bus.subscribe("tag_changed", self._on_tag_changed)

    # --- persistence / loading -----------------------------------------

    def _load_from_project(self):
        now = time.time()
        for zone in self.project_manager.get_intrusion_zones():
            zone = dict(zone)
            self._zones[zone["id"]] = zone
            self._zone_state[zone["id"]] = ZoneState.DISARMED
            self._zone_timer[zone["id"]] = None
            self._zone_deadline[zone["id"]] = None
            self._zone_walk_test_active[zone["id"]] = False
            self._zone_walk_test_deadline[zone["id"]] = None
            self._zone_walk_test_timer[zone["id"]] = None
            self._zone_walk_test_observed[zone["id"]] = {}
        for line in self.project_manager.get_intrusion_lines():
            line = _normalize_line_filters(dict(line))
            self._lines[line["id"]] = line
            self._line_bypassed[line["id"]] = False
            self._line_supervision_started_at[line["id"]] = now
        for line_id, raw in self.project_manager.get_intrusion_line_supervision().items():
            if line_id in self._lines:
                self._line_life[line_id] = _normalize_line_life_record(raw, line_id=line_id)
        self._power_supervision.update(
            _normalize_power_supervision(self.project_manager.get_intrusion_power_supervision())
        )
        # Task (pamiec alarmu): loaded BEFORE _register_tags() so the
        # State-tag-style pattern below (register with a static default,
        # then correct it to the real persisted value) has something to
        # correct FROM - same two-step _line_state/State tag already
        # uses for the exact same reason (tag_manager needs the tag to
        # exist before update_tag() can set its real value).
        raw_memory = self.project_manager.get_intrusion_alarm_memory()
        for zone_id in self._zones:
            self._zone_alarm_memory[zone_id] = _normalize_zone_alarm_memory(raw_memory.get(zone_id))
        self._register_tags()
        # Seed live violated/fault state from whatever the referenced
        # tags already hold right now (construction happens after DI/
        # device/analog tags exist - see epw_core.py's startup()
        # ordering) - not just future tag_changed events, same "don't
        # rely solely on a future signal" pattern this codebase uses for
        # every other status indicator (time sync, training mode,
        # alarms).
        for line_id in list(self._lines.keys()):
            self._recompute_line_violation(line_id, initial=True)
        for zone_id in list(self._zones.keys()):
            self._refresh_zone_alarm_memory_tags(zone_id)
        self._refresh_system_tags()
        self._recompute_power_state()

    def _persist_zones(self):
        self.project_manager.set_intrusion_zones(list(self._zones.values()))
        self.project_manager.save_project()

    def _persist_lines(self):
        # Bypass is intentionally NOT part of the persisted record - see
        # module docstring. Strip it defensively even though _lines
        # itself never carries the key, so a future field addition can't
        # silently leak a runtime-only flag into project.json.
        self.project_manager.set_intrusion_lines(
            [{k: v for k, v in line.items() if k != "bypassed"} for line in self._lines.values()]
        )
        self.project_manager.save_project()

    def _persist_alarm_memory(self):
        """Caller already holds self._lock is NOT required/assumed here -
        called after releasing the lock in every caller (same pattern
        _persist_lines()/_persist_zones() already have from their own
        callers), since project_manager/json-file I/O should never run
        while self._lock is held any longer than necessary."""
        with self._lock:
            snapshot = {zid: dict(record) for zid, record in self._zone_alarm_memory.items()}
        self.project_manager.set_intrusion_alarm_memory(snapshot)
        self.project_manager.save_project()

    def _refresh_zone_alarm_memory_tags(self, zone_id: str):
        with self._lock:
            record = self._zone_alarm_memory.get(zone_id)
        if record is None:
            return
        self.tag_manager.update_tag(self._zone_tag(zone_id, "AlarmMemoryActive"), record["active"])
        self.tag_manager.update_tag(self._zone_tag(zone_id, "AlarmMemoryFirstCauseLine"),
                                     record["first_cause_line_id"] or "")

    # --- alarm event history (Task: "historia zdarzen alarmowych") -------

    def _record_alarm_history(self, event_type: str, actor: str, detail: str = "",
                               zone_id: str = None, zone_name: str = None, line_id: str = None, line_name: str = None):
        """Thin, always-safe wrapper around self.alarm_history_logger
        (optional, same "silently does nothing if not wired up" stance
        every self.audit_logger call in this module already has) - the
        single call site every alarm-system event funnels through, so
        the full event list (Task: "uzbrojenie i rozbrojenie... naruszenie
        linii... alarm z oznaczeniem pierwszej przyczyny... awarie linii i
        zasilania... bypass... linie oznaczone jako podejrzane... tryb
        chodzenia... skasowanie pamieci alarmu") is covered from ONE
        place per event, not re-derived at each call site."""
        if self.alarm_history_logger is None:
            return
        self.alarm_history_logger.record(event_type, actor, detail, zone_id=zone_id, zone_name=zone_name,
                                          line_id=line_id, line_name=line_name)

    def query_alarm_history(self, limit: int = 500, zone_id: str = None, event_type: str = None,
                             start=None, end=None):
        """GUI convenience - query_alarm_history() without the caller
        needing its own alarm_history_logger reference. Returns an empty
        list if no logger was wired up (Task: "brak konfiguracji = brak
        bledu")."""
        if self.alarm_history_logger is None:
            return []
        return self.alarm_history_logger.query(limit=limit, zone_id=zone_id, event_type=event_type,
                                                start=start, end=end)

    def get_history_event_types(self) -> list:
        """GUI convenience - populates the History tab's event-type
        filter dropdown from whatever actually got recorded, rather
        than a hand-maintained list that could drift out of sync with
        the event_type strings this module actually uses."""
        if self.alarm_history_logger is None:
            return []
        return self.alarm_history_logger.distinct_event_types()

    def get_history_retention_config(self) -> dict:
        if self.alarm_history_logger is None:
            return {"max_events": 0, "max_days": 0}
        return self.alarm_history_logger.get_retention_config()

    def configure_history_retention(self, max_events: int = None, max_days: int = None, level: str = None) -> bool:
        if level is not None and _level_rank(level) < _level_rank(AccessLevel.ENGINEER):
            log.warning(f"Refused to configure intrusion history retention: level {level!r} is below Engineer.")
            return False
        if self.alarm_history_logger is None:
            return False
        self.alarm_history_logger.configure_retention(max_events=max_events, max_days=max_days)
        return True

    # --- tag registration ------------------------------------------------

    def _zone_tag(self, zone_id: str, suffix: str) -> str:
        return f"{TAG_PREFIX}.Zone.{zone_id}.{suffix}"

    def _line_tag(self, line_id: str, suffix: str) -> str:
        return f"{TAG_PREFIX}.Line.{line_id}.{suffix}"

    def _register_tags(self):
        for zone_id in self._zones:
            self.tag_manager.add_tag(self._zone_tag(zone_id, "State"), ZoneState.DISARMED, TagType.STRING,
                                      description="This zone's current lifecycle state - DISARMED / EXIT_DELAY / "
                                                  "ARMED / ENTRY_DELAY / ALARM (see Arming, Disarming, and "
                                                  "Entry/Exit Delays)", source="SYSTEM")
            # Writable from logic (Task 5: "Przyjmuj tez jako WEJSCIE z
            # logiki: zadanie uzbrojenia i rozbrojenia strefy") - a level
            # change (not just True) is what's watched, see
            # _on_tag_changed(), so a key switch (a maintained level, not
            # a pulse) drives this exactly as well as a momentary button
            # would.
            self.tag_manager.add_tag(self._zone_tag(zone_id, "ArmRequest"), False, TagType.BOOL,
                                      description="Write True to arm, False to disarm this zone from logic",
                                      source="SYSTEM")
            self.tag_manager.add_tag(self._zone_tag(zone_id, "CountdownRemaining"), 0, TagType.INT,
                                      description="Seconds left in this zone's exit/entry countdown (0 otherwise)",
                                      source="SYSTEM")
            # This task's own additions:
            self.tag_manager.add_tag(self._zone_tag(zone_id, "AlarmMemoryActive"), False, TagType.BOOL,
                                      description="True while an alarm has occurred in this zone since the last "
                                                  "explicit clear (survives disarm and a restart) - see "
                                                  "clear_alarm_memory()", source="SYSTEM")
            self.tag_manager.add_tag(self._zone_tag(zone_id, "AlarmMemoryFirstCauseLine"), "", TagType.STRING,
                                      description="The line id that first raised the currently-remembered alarm "
                                                  "in this zone, empty if AlarmMemoryActive is False", source="SYSTEM")
            self.tag_manager.add_tag(self._zone_tag(zone_id, "WalkTestActive"), False, TagType.BOOL,
                                      description="True while walk-test mode is running on this zone - "
                                                  "violations are recorded but never alarm while this is True",
                                      source="SYSTEM")
        for line_id in self._lines:
            self.tag_manager.add_tag(self._line_tag(line_id, "Violated"), False, TagType.BOOL,
                                      description="This supervision line's current violated state", source="SYSTEM")
            self.tag_manager.add_tag(self._line_tag(line_id, "Locked"), False, TagType.BOOL,
                                      description="True while auto-locked after repeated alarms this arm cycle "
                                                  "(lockout_after_count) - stays locked until the zone is disarmed",
                                      source="SYSTEM")
            self.tag_manager.add_tag(self._line_tag(line_id, "MultiplicityCounting"), False, TagType.BOOL,
                                      description="True while counting violations toward multiplicity_count, "
                                                  "within multiplicity_window_seconds of the first one",
                                      source="SYSTEM")
            # This task's own additions:
            self.tag_manager.add_tag(self._line_tag(line_id, "State"), LineState.SECURE, TagType.STRING,
                                      description="This line's classified state - SECURE/VIOLATED, plus (PARAMETRIZED "
                                                  "mode only) TAMPER/SHORT/FAULT_OPEN/UNDETERMINED", source="SYSTEM")
            self.tag_manager.add_tag(self._line_tag(line_id, "Fault"), False, TagType.BOOL,
                                      description="True while this line is in a FAULT state (TAMPER/SHORT/"
                                                  "FAULT_OPEN/UNDETERMINED) - alarms regardless of arm state",
                                      source="SYSTEM")
            self.tag_manager.add_tag(self._line_tag(line_id, "Suspect"), False, TagType.BOOL,
                                      description="True once silence_threshold_seconds has elapsed with no "
                                                  "violation - a WARNING (never an alarm) that the sensor may be dead",
                                      source="SYSTEM")
        self.tag_manager.add_tag(f"{TAG_PREFIX}.System.State", ZoneState.DISARMED, TagType.STRING,
                                  description="Aggregate intrusion system state across every zone", source="SYSTEM")
        self.tag_manager.add_tag(f"{TAG_PREFIX}.System.Alarm", False, TagType.BOOL,
                                  description="True while any zone is in ALARM", source="SYSTEM")
        self.tag_manager.add_tag(f"{TAG_PREFIX}.System.EntryCountdownActive", False, TagType.BOOL,
                                  description="True while any zone is counting down its entry delay", source="SYSTEM")
        self.tag_manager.add_tag(f"{TAG_PREFIX}.System.ExitCountdownActive", False, TagType.BOOL,
                                  description="True while any zone is counting down its exit delay", source="SYSTEM")
        self.tag_manager.add_tag(f"{TAG_PREFIX}.Supervisory.Violated", False, TagType.BOOL,
                                  description="True while any SUPERVISORY line is violated (e.g. for lighting logic)",
                                  source="SYSTEM")
        # This task's own system-wide additions - always registered
        # (Task: "brak konfiguracji oznacza brak nadzoru, BEZ BLEDOW" -
        # a logic program reading these must never see a missing tag,
        # only an inert False, if power supervision was never configured).
        self.tag_manager.add_tag(f"{TAG_PREFIX}.System.LineFault", False, TagType.BOOL,
                                  description="True while any supervision line is in a FAULT state", source="SYSTEM")
        # Platform-wide convention (fix/power-supervision-polarity):
        # TRUE means HEALTHY, matching real protection-relay practice
        # (a healthy signal is HIGH; a severed cable or a dead module
        # reads LOW - failing safe, looking like a fault rather than
        # like a normal state). Seeded True ("healthy") - unconfigured
        # power supervision must stay inert/no-error (Task: "brak
        # konfiguracji oznacza brak nadzoru, bez bledow"), and True is
        # now the "nothing to report" resting value - see
        # _recompute_power_state()'s own docstring for the full
        # reasoning.
        self.tag_manager.add_tag(f"{TAG_PREFIX}.Power.MainsOk", True, TagType.BOOL,
                                  description="True while mains power is not supervised, or is supervised and "
                                              "reads healthy - False only while supervised AND reading failed",
                                  source="SYSTEM")
        self.tag_manager.add_tag(f"{TAG_PREFIX}.Power.BatteryOk", True, TagType.BOOL,
                                  description="True while the battery is not supervised, or is supervised and "
                                              "reads healthy - False only while supervised AND reading faulted",
                                  source="SYSTEM")
        self.tag_manager.add_tag(f"{TAG_PREFIX}.System.TechnicalAlarm", False, TagType.BOOL,
                                  description="True while mains has failed or the battery is faulted - a "
                                              "technical alarm, a DIFFERENT category from the intrusion "
                                              "System.Alarm above", source="SYSTEM")

    # --- tag_changed dispatch --------------------------------------------

    def _on_tag_changed(self, tag_name, value, quality):
        # Only identify WHAT to do while holding the lock (cheap dict
        # lookups, no I/O - same "never becomes the bottleneck for tag
        # processing" stance as switching_counters.py); the actual calls
        # below all happen outside it, in the caller's own thread, same
        # reasoning as the ArmRequest branch: _recompute_line_violation()
        # itself may call out to audit_logger.record() (via _raise_alarm())
        # and arm_zone()/disarm_zone() always do - none of that should run
        # with self._lock held any longer than necessary.
        matched_line_id = None
        matched_zone_id = None
        matched_power = False
        request_arm = False
        with self._lock:
            for line_id, line in self._lines.items():
                if line["tag"] == tag_name:
                    matched_line_id = line_id
                    break
            else:
                for zone_id, zone in self._zones.items():
                    if self._zone_tag(zone_id, "ArmRequest") == tag_name:
                        matched_zone_id = zone_id
                        request_arm = bool(value)
                        break
                else:
                    # Task part 2 (nadzor zasilania): the mains/battery
                    # tags are a single config, not a per-id collection
                    # like lines/zones above - a plain equality check
                    # against whichever tag names are CURRENTLY configured.
                    if tag_name in (self._power_supervision.get("mains_tag"), self._power_supervision.get("battery_tag")):
                        matched_power = True
                    else:
                        return
        if matched_line_id is not None:
            self._recompute_line_violation(matched_line_id)
            return
        if matched_power:
            self._recompute_power_state()
            return
        zone_id = matched_zone_id
        if request_arm:
            self.arm_zone(zone_id, actor="LOGIC", level=AccessLevel.ENGINEER)
        else:
            self.disarm_zone(zone_id, actor="LOGIC")

    # --- zone/line configuration (Engineer-only, Task 1: "dostep: Engineer") --

    def add_zone(self, name: str, exit_delay_seconds: float, entry_delay_seconds: float,
                 level: str = None) -> "str | None":
        if level is not None and _level_rank(level) < _level_rank(AccessLevel.ENGINEER):
            log.warning(f"Refused to add intrusion zone {name!r}: level {level!r} is below Engineer.")
            return None
        with self._lock:
            zone_id = _next_id("Z", self._zones)
            zone = {
                "id": zone_id, "name": name,
                "exit_delay_seconds": float(exit_delay_seconds),
                "entry_delay_seconds": float(entry_delay_seconds),
            }
            self._zones[zone_id] = zone
            self._zone_state[zone_id] = ZoneState.DISARMED
            self._zone_timer[zone_id] = None
            self._zone_deadline[zone_id] = None
            self._zone_walk_test_active[zone_id] = False
            self._zone_walk_test_deadline[zone_id] = None
            self._zone_walk_test_timer[zone_id] = None
            self._zone_walk_test_observed[zone_id] = {}
            self._zone_alarm_memory[zone_id] = _new_zone_alarm_memory()
        self.tag_manager.add_tag(self._zone_tag(zone_id, "State"), ZoneState.DISARMED, TagType.STRING,
                                  description="This zone's current lifecycle state - DISARMED / EXIT_DELAY / "
                                              "ARMED / ENTRY_DELAY / ALARM (see Arming, Disarming, and "
                                              "Entry/Exit Delays)", source="SYSTEM")
        self.tag_manager.add_tag(self._zone_tag(zone_id, "ArmRequest"), False, TagType.BOOL,
                                  description="Write True to arm, False to disarm this zone from logic",
                                  source="SYSTEM")
        self.tag_manager.add_tag(self._zone_tag(zone_id, "CountdownRemaining"), 0, TagType.INT,
                                  description="Seconds left in this zone's exit/entry countdown (0 otherwise)",
                                  source="SYSTEM")
        self.tag_manager.add_tag(self._zone_tag(zone_id, "AlarmMemoryActive"), False, TagType.BOOL,
                                  description="True while an alarm has occurred in this zone since the last "
                                              "explicit clear", source="SYSTEM")
        self.tag_manager.add_tag(self._zone_tag(zone_id, "AlarmMemoryFirstCauseLine"), "", TagType.STRING,
                                  description="The line id that first raised the currently-remembered alarm "
                                              "in this zone, empty if AlarmMemoryActive is False", source="SYSTEM")
        self.tag_manager.add_tag(self._zone_tag(zone_id, "WalkTestActive"), False, TagType.BOOL,
                                  description="True while walk-test mode is running on this zone", source="SYSTEM")
        self._persist_zones()
        self._refresh_system_tags()
        return zone_id

    def update_zone(self, zone_id: str, name: str = None, exit_delay_seconds: float = None,
                     entry_delay_seconds: float = None, level: str = None) -> bool:
        if level is not None and _level_rank(level) < _level_rank(AccessLevel.ENGINEER):
            log.warning(f"Refused to update intrusion zone {zone_id!r}: level {level!r} is below Engineer.")
            return False
        with self._lock:
            zone = self._zones.get(zone_id)
            if zone is None:
                return False
            if name is not None:
                zone["name"] = name
            if exit_delay_seconds is not None:
                zone["exit_delay_seconds"] = float(exit_delay_seconds)
            if entry_delay_seconds is not None:
                zone["entry_delay_seconds"] = float(entry_delay_seconds)
        self._persist_zones()
        return True

    def remove_zone(self, zone_id: str, level: str = None) -> bool:
        """Refuses (returns False) while the zone still has lines
        assigned - remove/reassign those first. Avoids silently
        orphaning a line's zone_id reference, which would make
        get_zone_snapshot() and arming logic have to guess what an
        unresolvable zone_id means."""
        if level is not None and _level_rank(level) < _level_rank(AccessLevel.ENGINEER):
            log.warning(f"Refused to remove intrusion zone {zone_id!r}: level {level!r} is below Engineer.")
            return False
        with self._lock:
            if zone_id not in self._zones:
                return False
            if any(line["zone_id"] == zone_id for line in self._lines.values()):
                log.warning(f"Refused to remove intrusion zone {zone_id!r}: it still has lines assigned.")
                return False
            self._cancel_timer(zone_id)
            self._cancel_zone_alarm_hold_timer(zone_id)
            walk_timer = self._zone_walk_test_timer.get(zone_id)
            if walk_timer is not None:
                walk_timer.cancel()
            del self._zones[zone_id]
            del self._zone_state[zone_id]
            del self._zone_timer[zone_id]
            del self._zone_deadline[zone_id]
            self._entry_trigger_line.pop(zone_id, None)
            self._zone_alarm_trigger_line.pop(zone_id, None)
            self._zone_alarm_hold_timer.pop(zone_id, None)
            self._zone_walk_test_active.pop(zone_id, None)
            self._zone_walk_test_deadline.pop(zone_id, None)
            self._zone_walk_test_timer.pop(zone_id, None)
            self._zone_walk_test_observed.pop(zone_id, None)
            self._zone_alarm_memory.pop(zone_id, None)
        for suffix in ("State", "ArmRequest", "CountdownRemaining", "AlarmMemoryActive",
                       "AlarmMemoryFirstCauseLine", "WalkTestActive"):
            self.tag_manager.remove_tag(self._zone_tag(zone_id, suffix))
        self._persist_zones()
        self._persist_alarm_memory()
        self._refresh_system_tags()
        return True

    def _validate_line_input_tag(self, input_mode: str, tag: str) -> "str | None":
        """Defense in depth behind the GUI's own type-filtered picker
        (Task part 1: "ma byc NIEMOZLIWE przypisanie wejscia
        niewlasciwego typu") - only checks a tag that's already
        resolvable in tag_manager (an unregistered/not-yet-loaded tag
        is let through optimistically, same lenient stance this module
        already has elsewhere for an unresolvable tag - see
        is_line_violated_now()). Returns an error message, or None if
        the tag type matches (or can't yet be checked)."""
        existing = self.tag_manager.get_tag(tag) if tag else None
        if existing is None:
            return None
        if input_mode == LineInputMode.PARAMETRIZED:
            if existing.data_type != TagType.REAL:
                return f"tag {tag!r} is not an analog (REAL) point - required for a PARAMETRIZED-mode line"
        else:
            if existing.data_type != TagType.BOOL:
                return f"tag {tag!r} is not a digital (BOOL) input - required for a CONTACT-mode line"
        return None

    def add_line(self, name: str, zone_id: str, tag: str, normal_state: str, line_type: str,
                 level: str = None, min_violation_seconds: float = None, multiplicity_count: int = None,
                 multiplicity_window_seconds: float = None, lockout_after_count: int = None,
                 alarm_hold_seconds: float = None, silence_threshold_seconds: float = None,
                 input_mode: str = None, parametrization: str = None, value_windows: dict = None) -> "str | None":
        if level is not None and _level_rank(level) < _level_rank(AccessLevel.ENGINEER):
            log.warning(f"Refused to add intrusion line {name!r}: level {level!r} is below Engineer.")
            return None
        if line_type not in LineType._ALL:
            log.warning(f"Refused to add intrusion line {name!r}: unknown line_type {line_type!r}.")
            return None
        input_mode = input_mode if input_mode in LineInputMode._ALL else DEFAULT_LINE_INPUT_MODE
        type_error = self._validate_line_input_tag(input_mode, tag)
        if type_error:
            log.warning(f"Refused to add intrusion line {name!r}: {type_error}.")
            return None
        with self._lock:
            if zone_id not in self._zones:
                log.warning(f"Refused to add intrusion line {name!r}: unknown zone_id {zone_id!r}.")
                return None
            line_id = _next_id("L", self._lines)
            line = _normalize_line_filters({
                "id": line_id, "name": name, "zone_id": zone_id, "tag": tag,
                "normal_state": normal_state if normal_state in (NORMAL_STATE_NC, NORMAL_STATE_NO) else NORMAL_STATE_NC,
                "line_type": line_type, "input_mode": input_mode,
            })
            # Task part 2 (predecessor)/part 1&3 (this task): an explicit
            # None (the default for every one of these) means "use the
            # off-equivalent default" - _normalize_line_filters() above
            # already seeded that; only overwrite when the caller
            # actually passed something.
            if min_violation_seconds is not None:
                line["min_violation_seconds"] = float(min_violation_seconds)
            if multiplicity_count is not None:
                line["multiplicity_count"] = int(multiplicity_count)
            if multiplicity_window_seconds is not None:
                line["multiplicity_window_seconds"] = float(multiplicity_window_seconds)
            if lockout_after_count is not None:
                line["lockout_after_count"] = int(lockout_after_count)
            if alarm_hold_seconds is not None:
                line["alarm_hold_seconds"] = float(alarm_hold_seconds)
            if silence_threshold_seconds is not None:
                line["silence_threshold_seconds"] = float(silence_threshold_seconds)
            if parametrization in LineParametrization._ALL:
                line["parametrization"] = parametrization
                if value_windows is None:
                    # A fresh parametrization with no explicit windows
                    # gets ITS OWN defaults (EOL vs DEOL have different
                    # state sets) - _normalize_line_filters() already ran
                    # before `parametrization` was possibly overwritten
                    # here, so redo the windows default against the
                    # FINAL parametrization.
                    line["value_windows"] = default_value_windows(parametrization)
            if value_windows is not None:
                line["value_windows"] = {k: list(v) for k, v in value_windows.items()}
            self._lines[line_id] = line
            self._line_bypassed[line_id] = False
            self._line_supervision_started_at[line_id] = time.time()
        self.tag_manager.add_tag(self._line_tag(line_id, "Violated"), False, TagType.BOOL,
                                  description="This supervision line's current violated state", source="SYSTEM")
        self.tag_manager.add_tag(self._line_tag(line_id, "Locked"), False, TagType.BOOL,
                                  description="True while auto-locked after repeated alarms this arm cycle",
                                  source="SYSTEM")
        self.tag_manager.add_tag(self._line_tag(line_id, "MultiplicityCounting"), False, TagType.BOOL,
                                  description="True while counting violations toward multiplicity_count",
                                  source="SYSTEM")
        self.tag_manager.add_tag(self._line_tag(line_id, "State"), LineState.SECURE, TagType.STRING,
                                  description="This line's classified state", source="SYSTEM")
        self.tag_manager.add_tag(self._line_tag(line_id, "Fault"), False, TagType.BOOL,
                                  description="True while this line is in a FAULT state", source="SYSTEM")
        self.tag_manager.add_tag(self._line_tag(line_id, "Suspect"), False, TagType.BOOL,
                                  description="True once silence_threshold_seconds has elapsed with no violation",
                                  source="SYSTEM")
        self._persist_lines()
        self._recompute_line_violation(line_id, initial=True)
        return line_id

    def update_line(self, line_id: str, name: str = None, zone_id: str = None, tag: str = None,
                     normal_state: str = None, line_type: str = None, level: str = None,
                     min_violation_seconds: float = None, multiplicity_count: int = None,
                     multiplicity_window_seconds: float = None, lockout_after_count: int = None,
                     alarm_hold_seconds: float = None, silence_threshold_seconds: float = None,
                     input_mode: str = None, parametrization: str = None, value_windows: dict = None) -> bool:
        if level is not None and _level_rank(level) < _level_rank(AccessLevel.ENGINEER):
            log.warning(f"Refused to update intrusion line {line_id!r}: level {level!r} is below Engineer.")
            return False
        with self._lock:
            line = self._lines.get(line_id)
            if line is None:
                return False
            if zone_id is not None and zone_id not in self._zones:
                log.warning(f"Refused to update intrusion line {line_id!r}: unknown zone_id {zone_id!r}.")
                return False
            if line_type is not None and line_type not in LineType._ALL:
                log.warning(f"Refused to update intrusion line {line_id!r}: unknown line_type {line_type!r}.")
                return False
            if input_mode is not None and input_mode not in LineInputMode._ALL:
                log.warning(f"Refused to update intrusion line {line_id!r}: unknown input_mode {input_mode!r}.")
                return False
            # Validate against the EFFECTIVE mode this update would leave
            # the line in (a new tag AND a mode change in the same call,
            # or just a new tag under the line's current mode) - the GUI
            # is expected to re-prompt for the input on a mode change
            # (Task part 1: "zmiana trybu... ma wymagac ponownego
            # wskazania wejscia... ostrzez... zamiast po cichu czyscic
            # konfiguracje"), but this check holds regardless of whether
            # it does.
            effective_tag = tag if tag is not None else line["tag"]
            effective_mode = input_mode if input_mode is not None else line.get("input_mode", DEFAULT_LINE_INPUT_MODE)
            type_error = self._validate_line_input_tag(effective_mode, effective_tag)
            if type_error:
                log.warning(f"Refused to update intrusion line {line_id!r}: {type_error}.")
                return False
            if name is not None:
                line["name"] = name
            if zone_id is not None:
                line["zone_id"] = zone_id
            if tag is not None:
                line["tag"] = tag
            if normal_state is not None and normal_state in (NORMAL_STATE_NC, NORMAL_STATE_NO):
                line["normal_state"] = normal_state
            if line_type is not None:
                line["line_type"] = line_type
            if input_mode is not None:
                line["input_mode"] = input_mode
            if min_violation_seconds is not None:
                line["min_violation_seconds"] = float(min_violation_seconds)
            if multiplicity_count is not None:
                line["multiplicity_count"] = int(multiplicity_count)
            if multiplicity_window_seconds is not None:
                line["multiplicity_window_seconds"] = float(multiplicity_window_seconds)
            if lockout_after_count is not None:
                line["lockout_after_count"] = int(lockout_after_count)
            if alarm_hold_seconds is not None:
                line["alarm_hold_seconds"] = float(alarm_hold_seconds)
            if silence_threshold_seconds is not None:
                line["silence_threshold_seconds"] = float(silence_threshold_seconds)
            if parametrization in LineParametrization._ALL:
                line["parametrization"] = parametrization
                if value_windows is None:
                    line["value_windows"] = default_value_windows(parametrization)
            if value_windows is not None:
                line["value_windows"] = {k: list(v) for k, v in value_windows.items()}
        self._persist_lines()
        self._recompute_line_violation(line_id)
        return True

    def remove_line(self, line_id: str, level: str = None) -> bool:
        if level is not None and _level_rank(level) < _level_rank(AccessLevel.ENGINEER):
            log.warning(f"Refused to remove intrusion line {line_id!r}: level {level!r} is below Engineer.")
            return False
        with self._lock:
            if line_id not in self._lines:
                return False
            del self._lines[line_id]
            self._line_bypassed.pop(line_id, None)
            self._cancel_line_debounce_timer(line_id)
            timer = self._line_multiplicity_timer.pop(line_id, None)
            if timer is not None:
                timer.cancel()
            self._line_raw_violated.pop(line_id, None)
            self._line_counted_violated.pop(line_id, None)
            self._line_multiplicity_count.pop(line_id, None)
            self._line_locked.pop(line_id, None)
            self._line_alarm_count_cycle.pop(line_id, None)
            self._line_state.pop(line_id, None)
            self._line_raw_fault.pop(line_id, None)
            self._line_counted_fault.pop(line_id, None)
            self._line_life.pop(line_id, None)
            self._line_suspect.pop(line_id, None)
            self._line_supervision_started_at.pop(line_id, None)
            self._line_life_dirty = True
        self.tag_manager.remove_tag(self._line_tag(line_id, "Violated"))
        self.tag_manager.remove_tag(self._line_tag(line_id, "Locked"))
        self.tag_manager.remove_tag(self._line_tag(line_id, "MultiplicityCounting"))
        self.tag_manager.remove_tag(self._line_tag(line_id, "State"))
        self.tag_manager.remove_tag(self._line_tag(line_id, "Fault"))
        self.tag_manager.remove_tag(self._line_tag(line_id, "Suspect"))
        self._persist_lines()
        self._refresh_supervisory_tag()
        self._refresh_system_line_fault_tag()
        return True

    def bypass_line(self, line_id: str, bypassed: bool, actor: str, level: str = None) -> bool:
        """Task 1 (bypass with audit) + Task 4 ("kazdy... bypass...
        zapisuj do dziennika audytowego: kto, kiedy... ktora linia").
        Session-only (see module docstring) - does NOT touch any
        already-active ALARM state (a bypass silences future violations
        of this line, it is not a way to clear an alarm already raised;
        use disarm_zone() for that)."""
        if level is not None and _level_rank(level) < _level_rank(AccessLevel.ENGINEER):
            log.warning(f"Refused to bypass intrusion line {line_id!r}: level {level!r} is below Engineer.")
            return False
        with self._lock:
            line = self._lines.get(line_id)
            if line is None:
                return False
            bypassed = bool(bypassed)
            if self._line_bypassed.get(line_id) == bypassed:
                return False  # idempotent, no duplicate audit entry - same stance as TrainingModeManager
            self._line_bypassed[line_id] = bypassed
            zone = self._zones.get(line["zone_id"])
            zone_name = zone["name"] if zone else line["zone_id"]
            line_name = line["name"]
        bypass_detail = f"Zone '{zone_name}': line '{line_name}' bypass {'enabled' if bypassed else 'disabled'}"
        bypass_event = "INTRUSION_LINE_BYPASS_ON" if bypassed else "INTRUSION_LINE_BYPASS_OFF"
        if self.audit_logger is not None:
            self.audit_logger.record(bypass_event, actor, bypass_detail, success=True)
        self._record_alarm_history(bypass_event, actor, bypass_detail, zone_id=line["zone_id"], zone_name=zone_name,
                                    line_id=line_id, line_name=line_name)
        self._recompute_line_violation(line_id)
        return True

    # --- arming (Task 4: "wymaga poziomu Operator lub wyzszy") -----------

    def arm_zone(self, zone_id: str, actor: str, level: str = None, force: bool = False) -> ArmResult:
        """force=False (default): if any non-bypassed line in the zone is
        currently violated OR faulted, arming is refused with
        needs_confirmation=True and the offending line ids (split into
        violated_line_ids/fault_line_ids) - no state change, no audit
        entry (nothing was authorized yet). The caller (GUI or logic) is
        expected to show/consider that and call again with force=True to
        actually arm anyway (predecessor Task 4: "Uzbrojenie mimo to ma
        byc mozliwe, ale musi wymagac jawnego potwierdzenia - nie po
        cichu"; this task's own part 4: the same requirement, extended
        to a line in FAULT)."""
        if level is not None and _level_rank(level) < _level_rank(AccessLevel.OPERATOR):
            log.warning(f"Refused to arm intrusion zone {zone_id!r}: level {level!r} is below Operator.")
            return ArmResult(False, reason="Access denied - Operator level or higher required.")
        with self._lock:
            zone = self._zones.get(zone_id)
            if zone is None:
                return ArmResult(False, reason=f"Unknown zone: {zone_id}")
            if self._zone_state[zone_id] not in (ZoneState.DISARMED,):
                return ArmResult(False, reason=f"Zone is not disarmed (current state: {self._zone_state[zone_id]})")

            violated_ids = []
            fault_ids = []
            for lid, line in self._lines.items():
                if line["zone_id"] != zone_id or self._line_bypassed.get(lid, False):
                    continue
                state = self._classify_line_state(line)
                if state == LineState.VIOLATED:
                    violated_ids.append(lid)
                elif is_line_fault_state(state):
                    fault_ids.append(lid)
            if (violated_ids or fault_ids) and not force:
                reason = []
                if violated_ids:
                    reason.append("one or more lines are violated")
                if fault_ids:
                    reason.append("one or more lines are in FAULT")
                return ArmResult(False, needs_confirmation=True, violated_line_ids=violated_ids,
                                  fault_line_ids=fault_ids, reason="; ".join(reason).capitalize() + ".")

            exit_delay = zone["exit_delay_seconds"]
            if exit_delay > 0:
                self._set_zone_state(zone_id, ZoneState.EXIT_DELAY)
                self._start_timer(zone_id, exit_delay, self._on_exit_delay_elapsed)
            else:
                self._set_zone_state(zone_id, ZoneState.ARMED)

        detail = f"Zone '{zone['name']}' armed"
        if violated_ids:
            names = [self._lines[lid]["name"] for lid in violated_ids]
            detail += f" DESPITE violated line(s): {', '.join(names)} (explicitly confirmed)"
        if fault_ids:
            # Task part 4: "zapisane w dzienniku audytowym jako
            # uzbrojenie z pominieciem awarii" - a distinct phrase
            # from the violated-lines case above, both can appear in
            # the same entry if both kinds were present.
            names = [self._lines[lid]["name"] for lid in fault_ids]
            detail += f" WITH FAULT bypassed on line(s): {', '.join(names)} (armed despite fault, explicitly confirmed)"
        if self.audit_logger is not None:
            self.audit_logger.record("INTRUSION_ZONE_ARMED", actor, detail, success=True)
        self._record_alarm_history("INTRUSION_ZONE_ARMED", actor, detail, zone_id=zone_id, zone_name=zone["name"])
        return ArmResult(True, violated_line_ids=violated_ids, fault_line_ids=fault_ids)

    def disarm_zone(self, zone_id: str, actor: str, level: str = None) -> bool:
        """Always returns the zone to DISARMED from whatever state it was
        in - including ALARM (disarming is how an operator silences an
        intrusion alarm) - cancelling any pending exit/entry timer.
        Idempotent: already-DISARMED is a no-op, no duplicate audit
        entry (same stance as arm_zone/TrainingModeManager)."""
        if level is not None and _level_rank(level) < _level_rank(AccessLevel.OPERATOR):
            log.warning(f"Refused to disarm intrusion zone {zone_id!r}: level {level!r} is below Operator.")
            return False
        with self._lock:
            zone = self._zones.get(zone_id)
            if zone is None:
                return False
            if self._zone_state[zone_id] == ZoneState.DISARMED:
                return False
            self._cancel_timer(zone_id)
            self._cancel_zone_alarm_hold_timer(zone_id)
            self._zone_alarm_trigger_line[zone_id] = None
            self._set_zone_state(zone_id, ZoneState.DISARMED)
            # Task part 2 (lockout_after_count): "do rozbrojenia" - a
            # line auto-locked during this arm cycle unlocks HERE, and
            # every line's per-cycle alarm count starts over, so the
            # next arm cycle gets its own full lockout_after_count
            # budget rather than inheriting whatever count this cycle
            # left behind.
            newly_unlocked = []
            for lid, line in self._lines.items():
                if line["zone_id"] != zone_id:
                    continue
                self._line_alarm_count_cycle[lid] = 0
                if self._line_locked.get(lid, False):
                    self._line_locked[lid] = False
                    newly_unlocked.append(lid)
        disarm_detail = f"Zone '{zone['name']}' disarmed"
        if self.audit_logger is not None:
            self.audit_logger.record("INTRUSION_ZONE_DISARMED", actor, disarm_detail, success=True)
        self._record_alarm_history("INTRUSION_ZONE_DISARMED", actor, disarm_detail, zone_id=zone_id, zone_name=zone["name"])
        for lid in newly_unlocked:
            self.tag_manager.update_tag(self._line_tag(lid, "Locked"), False)
        return True

    # --- walk-test mode (Task 4: "tryb chodzenia") ------------------------

    def start_walk_test(self, zone_id: str, actor: str, level: str = None, duration_seconds: float = None) -> bool:
        """Engineer-only. While active, violations on this zone's lines
        are recorded (see _recompute_line_violation()'s own observation
        hook) but never alarm or change zone state (see
        _register_counted_violation_for_multiplicity()'s own gate) - a
        line FAULT still alarms normally either way (a different path,
        never gated by this). Auto-ends after `duration_seconds`
        (default DEFAULT_WALK_TEST_DURATION_SECONDS, Task: "domyslnie 30
        minut") regardless of whether anyone remembers to stop it by
        hand. Idempotent: already-running on this zone refuses (False) -
        stop it first to restart with a different duration."""
        if level is not None and _level_rank(level) < _level_rank(AccessLevel.ENGINEER):
            log.warning(f"Refused to start walk-test on intrusion zone {zone_id!r}: level {level!r} is below Engineer.")
            return False
        with self._lock:
            if zone_id not in self._zones:
                return False
            if self._zone_walk_test_active.get(zone_id, False):
                return False
            # A tiny positive floor (not a realistic-minutes minimum) -
            # just guards against a literal 0/negative duration turning
            # into an instant/never-firing threading.Timer; a caller
            # (test or otherwise) asking for a short test duration is
            # honored as asked.
            duration = max(0.05, float(duration_seconds) if duration_seconds is not None
                            else DEFAULT_WALK_TEST_DURATION_SECONDS)
            self._zone_walk_test_active[zone_id] = True
            self._zone_walk_test_deadline[zone_id] = time.monotonic() + duration
            self._zone_walk_test_observed[zone_id] = {}
            timer = threading.Timer(duration, self._on_walk_test_expired, args=(zone_id,))
            timer.daemon = True
            self._zone_walk_test_timer[zone_id] = timer
            timer.start()
            zone_name = self._zones[zone_id]["name"]
        self.tag_manager.update_tag(self._zone_tag(zone_id, "WalkTestActive"), True)
        detail = f"Zone '{zone_name}': walk-test mode started ({duration:.0f}s)"
        if self.audit_logger is not None:
            self.audit_logger.record("INTRUSION_WALK_TEST_STARTED", actor, detail, success=True)
        self._record_alarm_history("INTRUSION_WALK_TEST_STARTED", actor, detail, zone_id=zone_id, zone_name=zone_name)
        return True

    def stop_walk_test(self, zone_id: str, actor: str, level: str = None) -> "dict | None":
        """Engineer-only. Returns the end-of-test summary dict (see
        _end_walk_test()) or None if walk-test wasn't running on this
        zone (refused level, or not active)."""
        if level is not None and _level_rank(level) < _level_rank(AccessLevel.ENGINEER):
            log.warning(f"Refused to stop walk-test on intrusion zone {zone_id!r}: level {level!r} is below Engineer.")
            return None
        return self._end_walk_test(zone_id, actor, reason="manual")

    def _on_walk_test_expired(self, zone_id: str):
        self._end_walk_test(zone_id, actor="SYSTEM", reason="timeout")

    def _end_walk_test(self, zone_id: str, actor: str, reason: str) -> "dict | None":
        with self._lock:
            if not self._zone_walk_test_active.get(zone_id, False):
                return None
            self._zone_walk_test_active[zone_id] = False
            self._zone_walk_test_deadline[zone_id] = None
            timer = self._zone_walk_test_timer.get(zone_id)
            if timer is not None:
                timer.cancel()
            self._zone_walk_test_timer[zone_id] = None
            observed = self._zone_walk_test_observed.get(zone_id, {})
            self._zone_walk_test_observed[zone_id] = {}
            zone = self._zones.get(zone_id)
            zone_name = zone["name"] if zone else zone_id
            confirmed = [
                {"line_id": lid, "line_name": self._lines[lid]["name"] if lid in self._lines else lid,
                 "count": obs["count"], "last_at": obs["last_at"]}
                for lid, obs in observed.items()
            ]
            silent = [
                {"line_id": lid, "line_name": line["name"]}
                for lid, line in self._lines.items()
                if line["zone_id"] == zone_id and lid not in observed
            ]
        self.tag_manager.update_tag(self._zone_tag(zone_id, "WalkTestActive"), False)
        summary = {"zone_id": zone_id, "zone_name": zone_name, "confirmed": confirmed, "silent": silent}
        detail = (f"Zone '{zone_name}': walk-test ended ({reason}) - "
                  f"{len(confirmed)} line(s) confirmed, {len(silent)} silent")
        if self.audit_logger is not None:
            self.audit_logger.record("INTRUSION_WALK_TEST_ENDED", actor, detail, success=True)
        self._record_alarm_history("INTRUSION_WALK_TEST_ENDED", actor, detail, zone_id=zone_id, zone_name=zone_name)
        return summary

    def is_walk_test_active(self, zone_id: str) -> bool:
        with self._lock:
            return self._zone_walk_test_active.get(zone_id, False)

    def get_walk_test_remaining(self, zone_id: str) -> int:
        """Whole seconds left, rounded up - same reasoning
        get_countdown_remaining() already documents for the exit/entry
        countdown."""
        with self._lock:
            deadline = self._zone_walk_test_deadline.get(zone_id)
        if deadline is None:
            return 0
        return max(0, math.ceil(deadline - time.monotonic()))

    def get_walk_test_status(self, zone_id: str) -> dict:
        """A read-only, GUI-ready snapshot: whether it's active, seconds
        left, and every line in the zone with its live confirmed/silent
        status (Task: "widoczna lista linii z czasem ostatniego
        naruszenia i wyraznym oznaczeniem, ktore juz zareagowaly, a
        ktore jeszcze nie") - usable WHILE a test is running, unlike the
        one-shot summary stop_walk_test()/the "ended" event return."""
        with self._lock:
            active = self._zone_walk_test_active.get(zone_id, False)
            observed = dict(self._zone_walk_test_observed.get(zone_id, {}))
            lines = [{"id": lid, "name": line["name"]} for lid, line in self._lines.items() if line["zone_id"] == zone_id]
        return {
            "active": active,
            "remaining": self.get_walk_test_remaining(zone_id),
            "lines": [
                {**line, "confirmed": line["id"] in observed,
                 "count": observed.get(line["id"], {}).get("count", 0),
                 "last_at": observed.get(line["id"], {}).get("last_at")}
                for line in lines
            ],
        }

    # --- internal state machine ------------------------------------------

    def _set_zone_state(self, zone_id: str, state: str):
        """Caller already holds self._lock. Updates the in-memory state,
        its State tag, CountdownRemaining, and the system-wide aggregate
        tags - the one place any of those actually change."""
        self._zone_state[zone_id] = state
        if state in (ZoneState.EXIT_DELAY, ZoneState.ENTRY_DELAY):
            zone = self._zones[zone_id]
            delay = zone["exit_delay_seconds"] if state == ZoneState.EXIT_DELAY else zone["entry_delay_seconds"]
            self._zone_deadline[zone_id] = time.monotonic() + delay
        else:
            self._zone_deadline[zone_id] = None
        self.tag_manager.update_tag(self._zone_tag(zone_id, "State"), state)
        remaining = self.get_countdown_remaining(zone_id)
        self.tag_manager.update_tag(self._zone_tag(zone_id, "CountdownRemaining"), remaining)
        self._refresh_system_tags()

    def _start_timer(self, zone_id: str, delay_seconds: float, callback):
        self._cancel_timer(zone_id)
        timer = threading.Timer(delay_seconds, callback, args=(zone_id,))
        timer.daemon = True
        self._zone_timer[zone_id] = timer
        timer.start()

    def _cancel_timer(self, zone_id: str):
        timer = self._zone_timer.get(zone_id)
        if timer is not None:
            timer.cancel()
        self._zone_timer[zone_id] = None
        self._entry_trigger_line.pop(zone_id, None)

    def _cancel_zone_alarm_hold_timer(self, zone_id: str):
        """Caller already holds self._lock (same convention as
        _cancel_timer() above)."""
        timer = self._zone_alarm_hold_timer.get(zone_id)
        if timer is not None:
            timer.cancel()
        self._zone_alarm_hold_timer[zone_id] = None

    def _on_exit_delay_elapsed(self, zone_id: str):
        with self._lock:
            if self._zone_state.get(zone_id) != ZoneState.EXIT_DELAY:
                return  # disarmed (or otherwise moved on) while the timer was pending - nothing to do
            self._zone_timer[zone_id] = None
            self._set_zone_state(zone_id, ZoneState.ARMED)

    def _on_entry_delay_elapsed(self, zone_id: str):
        with self._lock:
            if self._zone_state.get(zone_id) != ZoneState.ENTRY_DELAY:
                return  # disarmed before the entry delay ran out - nothing to do
            self._zone_timer[zone_id] = None
            trigger_line_id = self._entry_trigger_line.get(zone_id)
        self._raise_alarm(zone_id, trigger_line_id, "Entry delay expired without disarm")

    def _raise_alarm(self, zone_id: str, line_id, reason: str):
        with self._lock:
            zone = self._zones.get(zone_id)
            if zone is None:
                return
            self._cancel_timer(zone_id)
            self._set_zone_state(zone_id, ZoneState.ALARM)
            line = self._lines.get(line_id)
            line_name = line["name"] if line else "?"
            # Task part 2 (alarm_hold_seconds): the line that triggered
            # THIS alarm is what _on_alarm_hold_elapsed() below checks
            # for recovery - a later alarm from a different line while
            # already in ALARM (e.g. a second 24H line, which alarms
            # regardless of zone state) takes over as the new trigger,
            # restarting the hold countdown against ITS OWN hold time.
            self._cancel_zone_alarm_hold_timer(zone_id)
            self._zone_alarm_trigger_line[zone_id] = line_id
            hold_seconds = float(line.get("alarm_hold_seconds", DEFAULT_ALARM_HOLD_SECONDS)) if line else 0.0
            if hold_seconds > 0:
                timer = threading.Timer(hold_seconds, self._on_alarm_hold_elapsed, args=(zone_id,))
                timer.daemon = True
                self._zone_alarm_hold_timer[zone_id] = timer
                timer.start()
        if self.audit_logger is not None:
            self.audit_logger.record(
                "INTRUSION_ALARM", "SYSTEM",
                f"Zone '{zone['name']}': {reason} (line '{line_name}')",
                success=False,
            )
        self._record_alarm_history("INTRUSION_ALARM", "SYSTEM", f"Zone '{zone['name']}': {reason} (line '{line_name}')",
                                    zone_id=zone_id, zone_name=zone["name"], line_id=line_id, line_name=line_name)
        # Task ("pierwsza przyczyna alarmu" + "pamiec alarmu"): every
        # alarm this module ever raises funnels through here - the one
        # place to latch the first-cause/subsequent record, regardless
        # of which line TYPE or path (INSTANT/24H immediate, DELAYED via
        # _on_entry_delay_elapsed, or a line FAULT via
        # _dispatch_line_fault) triggered it.
        self._record_alarm_cause(zone_id, line_id, line_name, reason)

    def _record_alarm_cause(self, zone_id: str, line_id, line_name, reason: str):
        """A LATCH, same principle as safety_kernel.py's own ("zdarzenie,
        ktore minelo, nadal sie wydarzylo") - see the module-level
        _new_zone_alarm_memory()'s own docstring for the full reasoning.
        Persisted immediately (not buffered) - an alarm event is exactly
        the kind of low-frequency, safety-relevant write immediate
        persistence exists for."""
        now = time.time()
        newly_activated = False
        with self._lock:
            memory = self._zone_alarm_memory.setdefault(zone_id, _new_zone_alarm_memory())
            if not memory["active"]:
                memory["active"] = True
                memory["first_cause_line_id"] = line_id
                memory["first_cause_line_name"] = line_name
                memory["first_cause_reason"] = reason
                memory["first_cause_at"] = now
                memory["subsequent"] = []
                newly_activated = True
            else:
                memory["subsequent"].append(
                    {"line_id": line_id, "line_name": line_name, "reason": reason, "at": now}
                )
        if newly_activated:
            self._refresh_zone_alarm_memory_tags(zone_id)
        self._persist_alarm_memory()

    def get_alarm_memory(self, zone_id: str) -> dict:
        """A read-only copy of `zone_id`'s alarm-memory record (Task:
        "pierwsza przyczyna", "pamiec alarmu") - empty/inactive if the
        zone doesn't exist or nothing has been recorded since the last
        clear."""
        with self._lock:
            record = self._zone_alarm_memory.get(zone_id)
            return dict(record) if record is not None else _new_zone_alarm_memory()

    def clear_alarm_memory(self, zone_id: str, actor: str, level: str = None) -> bool:
        """Task 3: "Kasowanie: poziom Operator lub wyzszy, zapisywane do
        historii alarmowej i dziennika audytowego." The ONLY way this
        record is ever reset - never by disarm_zone(), never by time,
        never automatically (see the module-level docstring's "LATCH"
        reasoning)."""
        if level is not None and _level_rank(level) < _level_rank(AccessLevel.OPERATOR):
            log.warning(f"Refused to clear intrusion alarm memory for zone {zone_id!r}: level {level!r} is below Operator.")
            return False
        with self._lock:
            if zone_id not in self._zones:
                return False
            memory = self._zone_alarm_memory.get(zone_id)
            if memory is None or not memory["active"]:
                return False  # idempotent, no duplicate audit/history entry - same stance as bypass/arm/disarm
            self._zone_alarm_memory[zone_id] = _new_zone_alarm_memory()
            zone_name = self._zones[zone_id]["name"]
        self._refresh_zone_alarm_memory_tags(zone_id)
        self._persist_alarm_memory()
        if self.audit_logger is not None:
            self.audit_logger.record("INTRUSION_ALARM_MEMORY_CLEARED", actor,
                                      f"Zone '{zone_name}': alarm memory cleared", success=True)
        self._record_alarm_history("INTRUSION_ALARM_MEMORY_CLEARED", actor, f"Zone '{zone_name}': alarm memory cleared",
                                    zone_id=zone_id, zone_name=zone_name)
        return True

    def _on_alarm_hold_elapsed(self, zone_id: str):
        """Task part 2 (alarm_hold_seconds): the MINIMUM time an alarm
        is held before it's even eligible to auto-return to ARMED. If
        the triggering line is still violated when this fires, we do
        nothing further here - _maybe_recover_from_alarm_hold() (called
        whenever a line's counted-violated state clears) checks again
        the moment it actually does clear, since the hold timer is by
        then already gone (self._zone_alarm_hold_timer[zone_id] is
        None) and won't fire a second time on its own."""
        with self._lock:
            self._zone_alarm_hold_timer[zone_id] = None
            if self._zone_state.get(zone_id) != ZoneState.ALARM:
                return
            trigger_line_id = self._zone_alarm_trigger_line.get(zone_id)
        self._maybe_return_to_armed_after_hold(zone_id, trigger_line_id)

    def _maybe_return_to_armed_after_hold(self, zone_id: str, trigger_line_id):
        if trigger_line_id is None or self.is_line_violated_now(trigger_line_id):
            return  # no trigger on record, or still violated - stays in ALARM
        with self._lock:
            if self._zone_state.get(zone_id) != ZoneState.ALARM:
                return
            self._set_zone_state(zone_id, ZoneState.ARMED)
            self._zone_alarm_trigger_line[zone_id] = None

    def _maybe_recover_from_alarm_hold(self, line_id: str):
        """Called whenever `line_id`'s COUNTED violation clears (see
        _set_line_counted_violated() below) - the other half of
        _on_alarm_hold_elapsed() above: that one handles "the hold
        time elapsed, is the line clear yet?"; this one handles "the
        line just cleared, has the hold time already elapsed?" Only
        acts if the hold timer is no longer pending (None) - if it's
        still running, _on_alarm_hold_elapsed() will make this exact
        check itself once it fires, so doing it again here would just
        race it for no benefit."""
        with self._lock:
            line = self._lines.get(line_id)
            if line is None:
                return
            zone_id = line["zone_id"]
            if self._zone_state.get(zone_id) != ZoneState.ALARM:
                return
            if self._zone_alarm_trigger_line.get(zone_id) != line_id:
                return
            hold_seconds = float(line.get("alarm_hold_seconds", DEFAULT_ALARM_HOLD_SECONDS))
            if hold_seconds <= 0:
                return  # feature off for this line - manual disarm only, as today
            if self._zone_alarm_hold_timer.get(zone_id) is not None:
                return  # still within the hold window
        self._maybe_return_to_armed_after_hold(zone_id, line_id)

    def _handle_violation(self, line_id: str, line: dict):
        """Caller already holds self._lock. Returns (zone_id, line_id,
        reason) if an alarm should be raised (the actual _raise_alarm()
        call happens back in _recompute_line_violation(), OUTSIDE the
        lock - see there for why), or None otherwise. Returning this
        rather than stashing it on self avoids a shared-mutable-instance-
        -attribute race if two threads process two different lines'
        tag_changed events concurrently (EventBus.emit() runs each
        subscriber on whatever thread emitted the event - GUI, the API's
        uvicorn thread, and a real driver's poll thread could all call
        this at once for different tags). See the module docstring's
        "per-line-type reaction" section for the full behavior table."""
        zone_id = line["zone_id"]
        state = self._zone_state.get(zone_id)
        if state is None:
            return None
        line_type = line["line_type"]

        if line_type == LineType.SUPERVISORY:
            return None  # Task: never alarms, any state

        if line_type == LineType.TWENTY_FOUR_HOUR:
            return (zone_id, line_id, "24H line violated")
        elif line_type == LineType.INSTANT:
            if state != ZoneState.ARMED:
                return None
            return (zone_id, line_id, "Instant line violated while armed")
        elif line_type == LineType.DELAYED:
            if state == ZoneState.ARMED:
                self._set_zone_state(zone_id, ZoneState.ENTRY_DELAY)
                # _start_timer() calls _cancel_timer() first (to clear
                # any previous timer), which also clears
                # _entry_trigger_line as a side effect - so this line
                # must record it AFTER _start_timer(), not before, or
                # _start_timer()'s own internal cancel wipes it out
                # immediately (found empirically: _on_entry_delay_elapsed
                # read back None instead of this line's id).
                self._start_timer(zone_id, self._zones[zone_id]["entry_delay_seconds"], self._on_entry_delay_elapsed)
                self._entry_trigger_line[zone_id] = line_id
            return None  # ENTRY_DELAY/EXIT_DELAY/DISARMED: no-op, see module docstring
        return None

    # --- live violation tracking ------------------------------------------

    def _classify_line_state(self, line: dict) -> str:
        """Bypass-INDEPENDENT classification of `line`'s current raw
        reading into a LineState.* - CONTACT or PARAMETRIZED aware.
        Always reflects the true sensor/analog reading, the same "show
        the truth regardless of bypass" stance is_line_violated_now()
        already has for the simpler CONTACT-only case. An unresolvable
        tag reads SECURE for CONTACT mode (matches is_line_violated_now()'s
        own "no data = not violated" stance) but UNDETERMINED for
        PARAMETRIZED mode (an analog reading that can't even be fetched
        is itself a fault worth reporting, not silently "fine" -
        classify_parametrized_value()'s own rule for value=None)."""
        raw_value = self.tag_manager.get_value(line["tag"])
        if line.get("input_mode", DEFAULT_LINE_INPUT_MODE) == LineInputMode.PARAMETRIZED:
            windows = line.get("value_windows") or default_value_windows(
                line.get("parametrization", DEFAULT_PARAMETRIZATION))
            return classify_parametrized_value(raw_value, windows)
        if raw_value is None:
            return LineState.SECURE
        return LineState.VIOLATED if is_line_violated(raw_value, line["normal_state"]) else LineState.SECURE

    def _recompute_line_violation(self, line_id: str, initial: bool = False):
        """Classifies `line_id`'s current state (RAW, bypass-independent
        - always what the State tag shows) and dispatches on TWO
        independent axes from the bypass-ADJUSTED version of it
        (SECURE when bypassed, regardless of the raw reading - Task's
        own predecessor: "bypass... arming and alarming both ignore it
        entirely"):

        - the VIOLATION axis (unchanged from the predecessor task):
          only a SECURE<->VIOLATED transition does anything; a
          transition INTO violated doesn't "count" immediately unless
          min_violation_seconds is 0 (or this is the startup seed,
          `initial`) - see _confirm_line_violation()/_set_line_counted_violated().
        - the FAULT axis (this task, part 1): TAMPER/SHORT/FAULT_OPEN/
          UNDETERMINED are collectively "line fault" - any transition
          INTO a fault state dispatches an alarm IMMEDIATELY,
          unconditionally (no debounce/multiplicity/lockout - Task:
          "alarmuja niezaleznie od stanu uzbrojenia, jak linia
          calodobowa" - the same "always alarms, any zone state, any
          line TYPE" treatment 24H already gets, applied here
          regardless of this line's own line_type).

        Repeated tag_changed events that don't actually change either
        axis's reading are a no-op (TagManager itself normally only
        fires on an actual value change, but this guards it explicitly
        rather than assuming that)."""
        with self._lock:
            line = self._lines.get(line_id)
            if line is None:
                return
            line_type = line["line_type"]
            min_violation = float(line.get("min_violation_seconds", DEFAULT_MIN_VIOLATION_SECONDS))
            bypassed = self._line_bypassed.get(line_id, False)
            raw_state = self._classify_line_state(line)  # bypass-INDEPENDENT - always the truth, for the State tag
            if raw_state == LineState.UNDETERMINED and self.tag_manager.get_value(line["tag"]) is None and not initial:
                log.warning(f"Intrusion line '{line['name']}' references unknown tag {line['tag']!r}.")
            effective_state = LineState.SECURE if bypassed else raw_state

            prev_state = self._line_state.get(line_id)
            self._line_state[line_id] = raw_state
            state_changed = initial or (prev_state != raw_state)

            raw_violated = (effective_state == LineState.VIOLATED)
            raw_fault = is_line_fault_state(effective_state)
            prev_raw_violated = self._line_raw_violated.get(line_id, False)
            prev_raw_fault = self._line_raw_fault.get(line_id, False)
            self._line_raw_violated[line_id] = raw_violated
            self._line_raw_fault[line_id] = raw_fault
            violation_changed = raw_violated != prev_raw_violated
            fault_changed = raw_fault != prev_raw_fault

            # Task (tryb chodzenia): record the observation IMMEDIATELY
            # on the raw edge, regardless of min_violation_seconds/
            # bypass filtering below - the whole point of a walk-test is
            # "did the sensor physically react at all", not "would this
            # have counted as a real alarm-worthy violation". The ALARM
            # dispatch itself is separately suppressed, further down the
            # pipeline, in _register_counted_violation_for_multiplicity().
            if not initial and violation_changed and raw_violated:
                zone_id = line["zone_id"]
                if self._zone_walk_test_active.get(zone_id, False):
                    entry = self._zone_walk_test_observed.setdefault(zone_id, {}) \
                        .setdefault(line_id, {"count": 0, "last_at": None})
                    entry["count"] += 1
                    entry["last_at"] = time.time()

        if state_changed:
            self.tag_manager.update_tag(self._line_tag(line_id, "State"), raw_state)

        # --- fault axis: immediate, unconditional, unfiltered ---
        if initial:
            self._set_line_counted_fault(line_id, raw_fault, effective_state if raw_fault else None)
        elif fault_changed:
            if raw_fault:
                self._dispatch_line_fault(line_id, effective_state)
            else:
                self._set_line_counted_fault(line_id, False, None)

        # --- violation axis (predecessor task, unchanged in spirit) ---
        if initial:
            self._set_line_counted_violated(line_id, raw_violated, line_type, initial=True)
            return
        if not violation_changed:
            return  # no violation-axis transition - nothing more to do

        if not raw_violated:
            self._cancel_line_debounce_timer(line_id)
            self._set_line_counted_violated(line_id, False, line_type)
            return

        if min_violation > 0:
            self._start_line_debounce_timer(line_id, min_violation)
        else:
            self._confirm_line_violation(line_id)

    def _start_line_debounce_timer(self, line_id: str, delay_seconds: float):
        with self._lock:
            self._cancel_line_debounce_timer(line_id)
            timer = threading.Timer(delay_seconds, self._on_line_debounce_elapsed, args=(line_id,))
            timer.daemon = True
            self._line_debounce_timer[line_id] = timer
            timer.start()

    def _cancel_line_debounce_timer(self, line_id: str):
        with self._lock:
            timer = self._line_debounce_timer.get(line_id)
            if timer is not None:
                timer.cancel()
            self._line_debounce_timer[line_id] = None

    def _on_line_debounce_elapsed(self, line_id: str):
        with self._lock:
            self._line_debounce_timer[line_id] = None
        self._confirm_line_violation(line_id)

    def _confirm_line_violation(self, line_id: str):
        """min_violation_seconds has elapsed (or the filter was off) -
        the violation now COUNTS. Re-checks the raw state first: it may
        already have cleared while the debounce timer was pending (the
        exact "krotki zaklocenie" case min_violation_seconds exists to
        filter - a bounce that never lasted the full threshold must
        never reach here counted at all)."""
        with self._lock:
            line = self._lines.get(line_id)
            if line is None or not self._line_raw_violated.get(line_id, False):
                return
            line_type = line["line_type"]
        self._set_line_counted_violated(line_id, True, line_type)
        self._register_counted_violation_for_multiplicity(line_id)

    def _set_line_counted_violated(self, line_id: str, violated: bool, line_type: str, initial: bool = False):
        zone_id = zone_name = zone_state = line_name = None
        with self._lock:
            if self._line_counted_violated.get(line_id, False) == violated:
                return
            self._line_counted_violated[line_id] = violated
            line = self._lines.get(line_id)
            if line is not None:
                zone_id = line["zone_id"]
                zone = self._zones.get(zone_id)
                zone_name = zone["name"] if zone else zone_id
                zone_state = self._zone_state.get(zone_id)
                line_name = line["name"]
        self.tag_manager.update_tag(self._line_tag(line_id, "Violated"), violated)
        if line_type == LineType.SUPERVISORY:
            self._refresh_supervisory_tag()
        if not violated:
            self._maybe_recover_from_alarm_hold(line_id)
        # Task part 3 (line life/silence supervision): a genuine, COUNTED
        # violation transition (post every filter above) is exactly what
        # "naruszenie" means for this record - a min_violation_seconds-
        # filtered bounce that never got this far is correctly never
        # counted here either.
        self._update_line_life_record(line_id, entering_violation=violated)
        # Task (historia zdarzen alarmowych: "naruszenie linii, w jakim
        # stanie strefy") - every COUNTED violation ONSET, whether or
        # not it goes on to actually alarm (SUPERVISORY never does; an
        # INSTANT line violated while not ARMED is a no-op too) - the
        # zone state at the moment of violation is exactly what the
        # Task asks this entry to carry.
        if violated and zone_id is not None and not initial:
            self._record_alarm_history(
                "INTRUSION_LINE_VIOLATED", "SYSTEM",
                f"Zone '{zone_name}' ({zone_state}): line '{line_name}' violated",
                zone_id=zone_id, zone_name=zone_name, line_id=line_id, line_name=line_name,
            )

    def _dispatch_line_fault(self, line_id: str, fault_state: str):
        """A line entering TAMPER/SHORT/FAULT_OPEN/UNDETERMINED alarms
        immediately and unconditionally - no debounce, no multiplicity,
        no lockout (those all exist to tame false INTRUSION alarms; a
        physical fault - a cut cable, a removed tamper resistor - is a
        different, more urgent kind of signal that should never be
        auto-suppressed), regardless of the ZONE's current state (same
        zone-state-independence 24H already has), and regardless of
        line TYPE - SUPERVISORY included.

        RESOLVED DESIGN DECISION (previously flagged for review - see
        git history/old SESSION_REPORT.md for the original, incorrect
        reasoning this replaces): SUPERVISORY's "never alarms" rule is
        specifically about a VIOLATION (motion in front of an outdoor
        sensor that should only signal, never wake the whole system) -
        it was never meant to cover a FAULT (a cut cable, a removed
        tamper resistor, a shorted loop). Those two are different
        things: "don't alarm on a rabbit walking past" is not the same
        promise as "don't alarm on a severed wire". A fault is a
        maintenance/sabotage event on every line without exception, so
        this function no longer special-cases SUPERVISORY - it alarms
        exactly like every other type on a fault, via the same
        _raise_alarm() path 24H already uses (and the same one
        alarm_hold_seconds already knows how to recover from once the
        line clears - reused here for free). Only _handle_violation()
        (the VIOLATION axis, called from _register_counted_violation_for_
        multiplicity() - a completely separate path from this one)
        still exempts SUPERVISORY, and only there."""
        with self._lock:
            line = self._lines.get(line_id)
            if line is None:
                return
            zone_id = line["zone_id"]
        self._set_line_counted_fault(line_id, True, fault_state)
        self._raise_alarm(zone_id, line_id, f"Line fault: {fault_state}")

    def _set_line_counted_fault(self, line_id: str, is_fault: bool, fault_state):
        with self._lock:
            line = self._lines.get(line_id)
            if line is None or self._line_counted_fault.get(line_id, False) == is_fault:
                return
            self._line_counted_fault[line_id] = is_fault
            zone_id = line["zone_id"]
            zone = self._zones.get(zone_id)
            zone_name = zone["name"] if zone else zone_id
            line_name = line["name"]
        self.tag_manager.update_tag(self._line_tag(line_id, "Fault"), is_fault)
        self._refresh_system_line_fault_tag()
        if not is_fault:
            # The fault ONSET already gets its own history entry via
            # _raise_alarm() (every fault alarms - see
            # _dispatch_line_fault()); only the recovery direction needs
            # one of its own here. Never fires from the initial=True
            # startup seed (that path only ever calls this with
            # is_fault matching whatever the line already reads, so a
            # transition INTO False from the untouched default False is
            # a same-value no-op above, not a real "cleared" edge).
            self._record_alarm_history("INTRUSION_LINE_FAULT_CLEARED", "SYSTEM",
                                        f"Zone '{zone_name}': line '{line_name}' fault cleared",
                                        zone_id=zone_id, zone_name=zone_name, line_id=line_id, line_name=line_name)

    def _refresh_system_line_fault_tag(self):
        with self._lock:
            any_fault = any(self._line_counted_fault.values())
        self.tag_manager.update_tag(f"{TAG_PREFIX}.System.LineFault", any_fault)

    # --- line life/silence supervision (Task part 3) -----------------------

    def _update_line_life_record(self, line_id: str, entering_violation: bool):
        """`entering_violation=True`: a genuine, COUNTED transition INTO
        violated just happened. `False`: a transition back to secure.
        Only ever called from _set_line_counted_violated() - i.e. on the
        FILTERED violation edge, never on raw electrical noise a
        min_violation_seconds debounce already absorbed - Task: this
        observes genuine violations, the same thing the rest of the
        module already treats as "a violation happened"."""
        now = time.time()
        with self._lock:
            record = self._line_life.setdefault(line_id, _new_line_life_record())
            if entering_violation:
                record["closes"] += 1
                record["closed_since"] = now
                record["last_violation_at"] = now
                if record["first_transition"] is None:
                    record["first_transition"] = now
            else:
                record["opens"] += 1
                if record["closed_since"] is not None:
                    record["closed_seconds"] += now - record["closed_since"]
                    record["closed_since"] = None
            record["last_transition"] = now
            self._line_life_dirty = True

    def _check_line_silence(self):
        """Task: "Dodaj konfigurowalny per linia MAKSYMALNY CZAS BEZ
        NARUSZENIA. Po jego przekroczeniu linia zostaje oznaczona jako
        PODEJRZANA" - a WARNING, never an alarm (Task: "to ma byc
        OSTRZEZENIE... nie wywoluje stanu alarmu"), so this only ever
        writes the Suspect tag and an audit WARNING entry, never touches
        zone/alarm state. Polled from the periodic tick (see
        _periodic_tick()) rather than event-driven, since "no event
        happened for a long time" cannot be detected by a tag_changed
        handler at all."""
        now = time.time()
        became_suspect = []
        became_ok = []
        with self._lock:
            for line_id, line in self._lines.items():
                threshold = float(line.get("silence_threshold_seconds", DEFAULT_SILENCE_THRESHOLD_SECONDS) or 0)
                if threshold <= 0:
                    continue
                record = self._line_life.get(line_id)
                last_violation_at = record["last_violation_at"] if record else None
                # No violation ever recorded yet: measure silence from
                # when this line was first loaded/added ("uruchomienia"),
                # not from epoch 0 - otherwise a freshly added line would
                # already read SUSPECT the instant its own threshold
                # elapses against a nonexistent baseline.
                baseline = last_violation_at if last_violation_at is not None \
                    else self._line_supervision_started_at.get(line_id, now)
                is_suspect = (now - baseline) > threshold
                was_suspect = self._line_suspect.get(line_id, False)
                if is_suspect != was_suspect:
                    self._line_suspect[line_id] = is_suspect
                    zone = self._zones.get(line["zone_id"])
                    zone_name = zone["name"] if zone else line["zone_id"]
                    (became_suspect if is_suspect else became_ok).append((line_id, line["name"], line["zone_id"], zone_name))
        for line_id, line_name, zone_id, zone_name in became_suspect:
            self.tag_manager.update_tag(self._line_tag(line_id, "Suspect"), True)
            detail = (f"Line '{line_name}' marked SUSPECT - no violation recorded within its configured "
                      f"silence threshold (possible dead sensor or cut cable)")
            if self.audit_logger is not None:
                self.audit_logger.record("INTRUSION_LINE_SUSPECT", "SYSTEM", detail, success=False)
            self._record_alarm_history("INTRUSION_LINE_SUSPECT", "SYSTEM", detail,
                                        zone_id=zone_id, zone_name=zone_name, line_id=line_id, line_name=line_name)
        for line_id, line_name, zone_id, zone_name in became_ok:
            self.tag_manager.update_tag(self._line_tag(line_id, "Suspect"), False)
            detail = f"Line '{line_name}' no longer SUSPECT - a violation was recorded"
            if self.audit_logger is not None:
                self.audit_logger.record("INTRUSION_LINE_SUSPECT_CLEARED", "SYSTEM", detail, success=True)
            self._record_alarm_history("INTRUSION_LINE_SUSPECT_CLEARED", "SYSTEM", detail,
                                        zone_id=zone_id, zone_name=zone_name, line_id=line_id, line_name=line_name)

    def flush_line_supervision(self):
        """Copies the current life-supervision snapshot into
        project_manager's config and saves - the only place any of it
        touches disk (Task/predecessor: "zapis na dysk nie przy kazdej
        zmianie stanu - buforuj i zapisuj okresowo", the same
        performance stance switching_counters.py's own flush_to_project()
        already documents). Safe to call anytime; a no-op if nothing
        changed since the last flush."""
        with self._lock:
            if not self._line_life_dirty:
                return
            snapshot = {lid: dict(record) for lid, record in self._line_life.items()}
            self._line_life_dirty = False
        self.project_manager.set_intrusion_line_supervision(snapshot)
        self.project_manager.save_project()

    # --- power supervision (Task part 2) ------------------------------------

    def configure_power_supervision(self, mains_tag: str = None, mains_ok_state: bool = True,
                                     battery_tag: str = None, battery_ok_state: bool = True,
                                     level: str = None) -> bool:
        """Both inputs optional (Task: "brak konfiguracji oznacza brak
        nadzoru, bez bledow") - pass None/"" to leave one (or both)
        unsupervised. Re-evaluates immediately against whatever the
        newly-configured tag(s) currently read, not just future
        tag_changed events - same "don't rely solely on a future
        signal" stance every other status indicator in this module
        already has."""
        if level is not None and _level_rank(level) < _level_rank(AccessLevel.ENGINEER):
            log.warning(f"Refused to configure power supervision: level {level!r} is below Engineer.")
            return False
        with self._lock:
            self._power_supervision = {
                "mains_tag": mains_tag or None, "mains_ok_state": bool(mains_ok_state),
                "battery_tag": battery_tag or None, "battery_ok_state": bool(battery_ok_state),
            }
            snapshot = dict(self._power_supervision)
        self.project_manager.set_intrusion_power_supervision(snapshot)
        self.project_manager.save_project()
        self._recompute_power_state()
        return True

    def get_power_supervision_config(self) -> dict:
        with self._lock:
            return dict(self._power_supervision)

    def get_digital_input_candidates(self) -> list:
        """GUI convenience - list_digital_input_candidates(tag_manager)
        without the caller needing its own tag_manager reference."""
        return list_digital_input_candidates(self.tag_manager)

    def get_analog_input_candidates(self) -> list:
        """GUI convenience - list_analog_input_candidates(project_manager)
        without the caller needing its own project_manager reference."""
        return list_analog_input_candidates(self.project_manager)

    def _recompute_power_state(self):
        """Task: "Zanik zasilania i niesprawnosc akumulatora maja:
        podnosic alarm techniczny (nie wlamaniowy - to inna kategoria)...
        byc widoczne... trafiac do dziennika audytowego... byc
        wystawione jako tagi". Deliberately never touches ZoneState/
        System.Alarm - System.TechnicalAlarm is a SEPARATE aggregate,
        and neither arm_zone() nor disarm_zone() ever reads it (Task:
        "zanik zasilania NIE MOZE blokowac uzbrojenia ani rozbrojenia" -
        trivially true by simply never checking it there).

        Fix (power-supervision-polarity): Security.Power.MainsOk/
        BatteryOk are TRUE-means-HEALTHY now (platform-wide convention -
        see this module's own tag docstrings above). mains_ok/battery_ok
        are computed as the direct logical negation of the old mains_
        failed/battery_fault expressions (De Morgan's law - "NOT
        (configured AND known AND reads-wrong)" = "NOT configured OR NOT
        known OR reads-right"), so the *externally observable*
        System.TechnicalAlarm behavior - and the "unconfigured = no
        alarm" guarantee - are BYTE-FOR-BYTE unchanged from before this
        task; only the two underlying tags' own name and polarity did."""
        with self._lock:
            cfg = dict(self._power_supervision)
        mains_tag = cfg["mains_tag"]
        battery_tag = cfg["battery_tag"]
        # An unresolvable/not-yet-registered tag reads as "ok" (healthy)
        # - a typo'd or not-yet-loaded tag name must never manufacture a
        # false technical alarm from nothing. "mains_ok_state"/
        # "battery_ok_state" (the CONFIG - which RAW reading counts as
        # healthy, per input) are untouched by this task - see
        # __init__'s own comment on _power_supervision.
        mains_val = self.tag_manager.get_value(mains_tag) if mains_tag else None
        mains_configured_and_known = bool(mains_tag) and mains_val is not None
        mains_ok = (not mains_configured_and_known) or (bool(mains_val) == cfg["mains_ok_state"])
        battery_val = self.tag_manager.get_value(battery_tag) if battery_tag else None
        battery_configured_and_known = bool(battery_tag) and battery_val is not None
        battery_ok = (not battery_configured_and_known) or (bool(battery_val) == cfg["battery_ok_state"])

        with self._lock:
            prev_mains_ok = self._mains_ok
            prev_battery_ok = self._battery_ok
            self._mains_ok = mains_ok
            self._battery_ok = battery_ok

        # Audit event-type identifiers and human detail text describe
        # the real-world event ("mains lost"/"mains restored") - neither
        # changes here, only the CONDITION deciding which one fires (now
        # keyed off "not ok" instead of "failed" - the inversion Task
        # part 2 requires: "odwrocenie znaczenia wymaga odwrocenia
        # warunku").
        if mains_ok != prev_mains_ok:
            self.tag_manager.update_tag(f"{TAG_PREFIX}.Power.MainsOk", mains_ok)
            event = "INTRUSION_MAINS_RESTORED" if mains_ok else "INTRUSION_MAINS_FAILED"
            detail = "Mains power restored" if mains_ok else "Mains power lost"
            if self.audit_logger is not None:
                self.audit_logger.record(event, "SYSTEM", detail, success=mains_ok)
            self._record_alarm_history(event, "SYSTEM", detail)
        if battery_ok != prev_battery_ok:
            self.tag_manager.update_tag(f"{TAG_PREFIX}.Power.BatteryOk", battery_ok)
            event = "INTRUSION_BATTERY_OK" if battery_ok else "INTRUSION_BATTERY_FAULT"
            detail = "Battery restored" if battery_ok else "Battery fault"
            if self.audit_logger is not None:
                self.audit_logger.record(event, "SYSTEM", detail, success=battery_ok)
            self._record_alarm_history(event, "SYSTEM", detail)
        # Task part 4: "po odwroceniu warunek musi sie odwrocic, inaczej
        # alarm bedzie sie zglaszal przy sprawnym zasilaniu" - the
        # technical alarm's OWN polarity (True = alarm) is unchanged;
        # only the expression feeding it is, since its two inputs are
        # now "is ok" instead of "is failed".
        self.tag_manager.update_tag(f"{TAG_PREFIX}.System.TechnicalAlarm", (not mains_ok) or (not battery_ok))

    # --- periodic lifecycle (Task part 3: flush + silence check) -----------

    def start(self):
        """Periodic background tick only (GRANICE/predecessor pattern:
        "zapisuj okresowo oraz przy zamykaniu programu", never on every
        state change) - mirrors switching_counters.py's own start()/
        stop() shape. Everything else in this module has already been
        live since __init__; this only drives flush_line_supervision()
        and _check_line_silence(), neither of which needs to run more
        often than once in a while."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._periodic_tick_loop, daemon=True, name="IntrusionSupervisionSaver")
        self._thread.start()

    def _periodic_tick_loop(self, interval_seconds: float = 60.0):
        while not self._stop_event.wait(interval_seconds):
            self._check_line_silence()
            self.flush_line_supervision()

    def _register_counted_violation_for_multiplicity(self, line_id: str):
        """Task part 2 (multiplicity_count/multiplicity_window_seconds):
        multiplicity_count<=1 (the default) dispatches every counted
        violation individually - today's behavior, exactly. Above that,
        counts violations and (re)starts a multiplicity_window_seconds
        reset timer on EACH one; reaching multiplicity_count before that
        timer fires dispatches (and resets the count for the next
        cycle); the timer firing first (no further violation within the
        window) resets the count to 0 without ever dispatching - Task:
        "Licznik zeruje sie po uplywie okna bez kolejnego naruszenia"."""
        dispatch = False
        counting = False
        with self._lock:
            line = self._lines.get(line_id)
            if line is None:
                return
            # Task (tryb chodzenia): "NIE wywoluja alarmu ani nie
            # zmieniaja stanu strefy" - the Violated tag and line-life
            # record are already updated by the caller (_set_line_
            # counted_violated(), before this runs), and the raw edge
            # was already recorded as an observation in
            # _recompute_line_violation() regardless of debounce/
            # multiplicity - only the actual alarm dispatch is
            # suppressed here, for every line type. Faults are NOT
            # gated here (a different path - _dispatch_line_fault() -
            # goes straight to _raise_alarm(), never through this
            # method - so a fault still alarms during a walk-test, per
            # Task: "awarie linii MAJA NADAL alarmowac normalnie").
            if self._zone_walk_test_active.get(line["zone_id"], False):
                return
            mult_count = max(1, int(line.get("multiplicity_count", DEFAULT_MULTIPLICITY_COUNT)))
            if mult_count <= 1:
                dispatch = True
            else:
                window = float(line.get("multiplicity_window_seconds", DEFAULT_MULTIPLICITY_WINDOW_SECONDS))
                old_timer = self._line_multiplicity_timer.get(line_id)
                if old_timer is not None:
                    old_timer.cancel()
                count = self._line_multiplicity_count.get(line_id, 0) + 1
                if count >= mult_count:
                    self._line_multiplicity_count[line_id] = 0
                    self._line_multiplicity_timer[line_id] = None
                    dispatch = True
                else:
                    self._line_multiplicity_count[line_id] = count
                    counting = True
                    timer = threading.Timer(window, self._on_multiplicity_window_elapsed, args=(line_id,))
                    timer.daemon = True
                    self._line_multiplicity_timer[line_id] = timer
                    timer.start()
        self.tag_manager.update_tag(self._line_tag(line_id, "MultiplicityCounting"), counting)
        if dispatch:
            self._dispatch_violation_after_lockout_check(line_id)

    def _on_multiplicity_window_elapsed(self, line_id: str):
        with self._lock:
            self._line_multiplicity_count[line_id] = 0
            self._line_multiplicity_timer[line_id] = None
        self.tag_manager.update_tag(self._line_tag(line_id, "MultiplicityCounting"), False)

    def _dispatch_violation_after_lockout_check(self, line_id: str):
        """The actual _handle_violation()/_raise_alarm() dispatch, same
        two-phase locked/unlocked split every other alarm path in this
        module already uses. Task part 2 (lockout_after_count): a
        LOCKED line is suppressed here, before _handle_violation() ever
        runs - same "completely inert" treatment as a bypassed line,
        just a different (automatic, not manual) reason. Counting
        toward the lock only happens for a violation that actually WOULD
        alarm (_handle_violation() returned something) - a SUPERVISORY
        line (which never alarms) or an INSTANT line violated while not
        ARMED (also a no-op) never counts toward its own lockout."""
        should_lock = False
        zone_id = zone_name = line_name = None
        with self._lock:
            line = self._lines.get(line_id)
            if line is None:
                return
            if self._line_locked.get(line_id, False):
                return
            raise_alarm_args = self._handle_violation(line_id, line)
            if raise_alarm_args is not None:
                lockout_after = int(line.get("lockout_after_count", DEFAULT_LOCKOUT_AFTER_COUNT))
                if lockout_after > 0:
                    cycle_count = self._line_alarm_count_cycle.get(line_id, 0) + 1
                    self._line_alarm_count_cycle[line_id] = cycle_count
                    if cycle_count >= lockout_after:
                        self._line_locked[line_id] = True
                        should_lock = True
                        zone_id = line["zone_id"]
                        zone = self._zones.get(zone_id)
                        zone_name = zone["name"] if zone else zone_id
                        line_name = line["name"]
        if raise_alarm_args is not None:
            self._raise_alarm(*raise_alarm_args)
        if should_lock:
            self.tag_manager.update_tag(self._line_tag(line_id, "Locked"), True)
            lock_detail = (f"Zone '{zone_name}': line '{line_name}' auto-locked after {lockout_after} alarms "
                            f"this arm cycle - stays locked until the zone is disarmed")
            if self.audit_logger is not None:
                self.audit_logger.record("INTRUSION_LINE_LOCKED", "SYSTEM", lock_detail, success=False)
            self._record_alarm_history("INTRUSION_LINE_LOCKED", "SYSTEM", lock_detail,
                                        zone_id=zone_id, zone_name=zone_name, line_id=line_id, line_name=line_name)

    def _refresh_supervisory_tag(self):
        with self._lock:
            any_violated = any(
                line["line_type"] == LineType.SUPERVISORY
                and self.tag_manager.get_value(self._line_tag(lid, "Violated"))
                for lid, line in self._lines.items()
            )
        self.tag_manager.update_tag(f"{TAG_PREFIX}.Supervisory.Violated", any_violated)

    def _refresh_system_tags(self):
        with self._lock:
            states = list(self._zone_state.values())
        aggregate = self.get_system_state()
        self.tag_manager.update_tag(f"{TAG_PREFIX}.System.State", aggregate)
        self.tag_manager.update_tag(f"{TAG_PREFIX}.System.Alarm", ZoneState.ALARM in states)
        self.tag_manager.update_tag(f"{TAG_PREFIX}.System.EntryCountdownActive", ZoneState.ENTRY_DELAY in states)
        self.tag_manager.update_tag(f"{TAG_PREFIX}.System.ExitCountdownActive", ZoneState.EXIT_DELAY in states)

    # --- reading (GUI/logic-facing) ---------------------------------------

    def get_zones(self) -> list:
        with self._lock:
            return [dict(z) for z in self._zones.values()]

    def get_lines(self) -> list:
        with self._lock:
            return [dict(l) for l in self._lines.values()]

    def get_zone_state(self, zone_id: str) -> "str | None":
        with self._lock:
            return self._zone_state.get(zone_id)

    def get_countdown_remaining(self, zone_id: str) -> int:
        """Whole seconds left, rounded UP (ceil), not to the nearest
        second - a genuinely pending countdown (deadline still
        microseconds away) must never display as 0 seconds left, the
        same way a real countdown timer shows "1" up until it actually
        hits zero, not "0" while a fraction of a second remains."""
        with self._lock:
            deadline = self._zone_deadline.get(zone_id)
        if deadline is None:
            return 0
        return max(0, math.ceil(deadline - time.monotonic()))

    def is_line_bypassed(self, line_id: str) -> bool:
        with self._lock:
            return self._line_bypassed.get(line_id, False)

    def is_line_locked(self, line_id: str) -> bool:
        """Task part 2 (lockout_after_count): True while this line is
        auto-locked after repeated alarms this arm cycle - mirrors the
        already-persisted Security.Line.<id>.Locked tag, for a caller
        that has an IntrusionManager reference handy rather than a
        TagManager one (same convenience is_line_bypassed() already
        provides for the bypass flag)."""
        with self._lock:
            return self._line_locked.get(line_id, False)

    def is_line_violated_now(self, line_id: str) -> bool:
        """Live read, independent of bypass/filters/debounce - True only
        for the narrow VIOLATED state specifically, mode-aware
        (CONTACT or PARAMETRIZED) via _classify_line_state(). A FAULT
        state (TAMPER/SHORT/FAULT_OPEN/UNDETERMINED) reads False here -
        see is_line_fault()/get_line_state() for that."""
        with self._lock:
            line = self._lines.get(line_id)
            if line is None:
                return False
        return self._classify_line_state(line) == LineState.VIOLATED

    def is_line_fault(self, line_id: str) -> bool:
        """Live read (RAW, bypass-independent, same stance as
        is_line_violated_now()) of whether this line is currently in
        ANY fault state - Task: "awaria linii (zbiorczo i per linia)"."""
        with self._lock:
            line = self._lines.get(line_id)
            if line is None:
                return False
        return is_line_fault_state(self._classify_line_state(line))

    def get_line_state(self, line_id: str) -> "str | None":
        """The full RAW classification (LineState.*) - Task: "stan
        kazdej linii (spokoj / naruszenie / sabotaz / zwarcie / przerwa
        / nieokreslony)". Mirrors the already-persisted
        Security.Line.<id>.State tag."""
        with self._lock:
            return self._line_state.get(line_id)

    def is_line_suspect(self, line_id: str) -> bool:
        """Task part 3: True once silence_threshold_seconds has elapsed
        with no violation - a WARNING, not a fault and not an alarm."""
        with self._lock:
            return self._line_suspect.get(line_id, False)

    def get_line_life_snapshot(self, line_id: str) -> dict:
        """A read-only copy of `line_id`'s violation-history record
        (Task part 3: count/last-violation-time/total-violated-time/
        first-violation-date), with closed_seconds already including
        the CURRENTLY-open violated interval (if any) up to this exact
        moment - what a display should show right now, same "live, not
        stale-until-the-next-close" stance switching_counters.py's own
        get_snapshot() already has."""
        with self._lock:
            record = self._line_life.get(line_id)
            if record is None:
                return _new_line_life_record()
            snapshot = dict(record)
        if snapshot["closed_since"] is not None:
            snapshot["closed_seconds"] += time.time() - snapshot["closed_since"]
        return snapshot

    def get_zone_snapshot(self, zone_id: str) -> dict:
        """One read-only dict for a GUI row: state, countdown, and every
        line in the zone with its violated/bypassed/locked/fault/
        suspect flags plus its full classified state."""
        with self._lock:
            zone = self._zones.get(zone_id)
            if zone is None:
                return {}
            lines = [dict(l) for l in self._lines.values() if l["zone_id"] == zone_id]
        return {
            "zone": dict(zone),
            "state": self.get_zone_state(zone_id),
            "countdown_remaining": self.get_countdown_remaining(zone_id),
            "lines": [
                {**line, "violated": self.is_line_violated_now(line["id"]), "bypassed": self.is_line_bypassed(line["id"]),
                 "locked": self.is_line_locked(line["id"]), "fault": self.is_line_fault(line["id"]),
                 "suspect": self.is_line_suspect(line["id"]), "line_state": self.get_line_state(line["id"])}
                for line in lines
            ],
        }

    def get_system_state(self) -> str:
        """Aggregate across every zone, most-urgent-first (ALARM >
        ENTRY_DELAY > EXIT_DELAY > ARMED > DISARMED) - a single zone in
        ALARM makes the whole system read ALARM even if every other zone
        is calmly DISARMED, and so on down the priority order. A system
        with zero zones configured reads DISARMED. This does not
        distinguish "every zone ARMED" from "some armed, some disarmed,
        none counting down or alarming" - both read ARMED, on the
        reasoning that "at least one zone is actively watching" is the
        more useful single answer for a status indicator than adding a
        6th state Task 3 never asked for; get_zones()/get_zone_state()
        give the real per-zone picture when that distinction matters."""
        with self._lock:
            states = set(self._zone_state.values())
        for state in ZoneState._PRIORITY:
            if state in states:
                return state
        return ZoneState.DISARMED

    def shutdown(self):
        """Cancels every pending timer - exit/entry (as before), plus
        the predecessor task's per-line debounce/multiplicity timers and
        per-zone alarm-hold timers - called from EPWCore.shutdown() so
        no threading.Timer outlives the process (same concern
        PresentationMode.stop() already addresses for its own scheduled
        timer). Also stops this task's own periodic thread (started via
        start()) and does a final flush_line_supervision() - the same
        "save periodically AND on shutdown" stance switching_counters.py's
        own stop() already documents."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        self.flush_line_supervision()
        with self._lock:
            zone_ids = list(self._zone_timer.keys())
            hold_zone_ids = list(self._zone_alarm_hold_timer.keys())
            line_ids = list(self._line_debounce_timer.keys())
            mult_line_ids = list(self._line_multiplicity_timer.keys())
            walk_test_zone_ids = list(self._zone_walk_test_timer.keys())
        for zone_id in zone_ids:
            self._cancel_timer(zone_id)
        for zone_id in hold_zone_ids:
            with self._lock:
                self._cancel_zone_alarm_hold_timer(zone_id)
        for line_id in line_ids:
            self._cancel_line_debounce_timer(line_id)
        for line_id in mult_line_ids:
            with self._lock:
                timer = self._line_multiplicity_timer.get(line_id)
                if timer is not None:
                    timer.cancel()
                self._line_multiplicity_timer[line_id] = None
        for zone_id in walk_test_zone_ids:
            with self._lock:
                timer = self._zone_walk_test_timer.get(zone_id)
                if timer is not None:
                    timer.cancel()
                self._zone_walk_test_timer[zone_id] = None

    def teardown(self):
        """Full LIVE teardown for the feature-configuration toggle
        (Task: "wylaczona funkcja... nie tworzy watkow ani timerow...
        nie rejestruje swoich tagow"). Different from shutdown() above:
        that one runs at PROCESS exit, where leaving this instance's own
        Security.* tags sitting in TagManager is harmless (the whole
        TagManager is about to disappear too) - this one is for turning
        the module off while the REST of the program keeps running, so
        it also detaches from tag_changed (shutdown() alone leaves this
        subscribed - see _on_tag_changed()'s own subscribe() call in
        __init__) and removes every tag this instance ever registered,
        system-wide ones included (remove_zone()/remove_line() only
        ever cleaned up ONE zone/line's own tags at a time, on purpose -
        neither one is a "turn the whole module off" path).

        Deliberately does NOT touch project.json (zones/lines/power
        config/history retention all stay exactly as configured) and
        does NOT clear alarm memory or line-life history - Task: "nigdy
        nie kasuje danych... po ponownym wlaczeniu maja byc na miejscu".
        A later re-enable is expected to construct a brand new
        IntrusionManager from that same, untouched project data (see
        epw_core.py's set_feature_enabled())."""
        self.shutdown()
        self.event_bus.unsubscribe("tag_changed", self._on_tag_changed)
        with self._lock:
            zone_ids = list(self._zones.keys())
            line_ids = list(self._lines.keys())
        for zone_id in zone_ids:
            for suffix in ("State", "ArmRequest", "CountdownRemaining", "AlarmMemoryActive",
                           "AlarmMemoryFirstCauseLine", "WalkTestActive"):
                self.tag_manager.remove_tag(self._zone_tag(zone_id, suffix))
        for line_id in line_ids:
            for suffix in ("Violated", "Locked", "MultiplicityCounting", "State", "Fault", "Suspect"):
                self.tag_manager.remove_tag(self._line_tag(line_id, suffix))
        for suffix in ("System.State", "System.Alarm", "System.EntryCountdownActive", "System.ExitCountdownActive",
                       "Supervisory.Violated", "System.LineFault", "Power.MainsOk", "Power.BatteryOk",
                       "System.TechnicalAlarm"):
            self.tag_manager.remove_tag(f"{TAG_PREFIX}.{suffix}")
