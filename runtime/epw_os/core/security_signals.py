"""The alarm half of the system-signal catalog, on this controller.

The catalog names the intrusion system as ONE alarm panel - SEC.SYSTEM.ARMED,
SEC.SYSTEM.ALARM, REQ.SEC.DISARM_ALL. This controller's intrusion model
is per ZONE: every state and every command belongs to a zone, and a site
can have several. Mapping one onto the other is a decision about what
"the alarm system is armed" means when three zones are armed and one is
not - which is why it was left unmapped when the logic engine first
started executing, rather than guessed at silently.

The decision, taken here and visible in one place:

  * ARMED means EVERY zone is armed (and there is at least one zone) -
    "full watch". ARMED_PARTIAL means some are and some are not. This is
    deliberately stricter than IntrusionManager.get_system_state(), whose
    own docstring says it treats "at least one zone watching" as ARMED
    because that is the more useful single answer for a status
    indicator. For LOGIC it is not: a schematic that energizes a
    contactor "while the building is armed" must not see ARMED when half
    the building is open.
  * Anything a zone can be in reads as true for the SYSTEM if ANY zone is
    in it (EXIT_DELAY, ENTRY_DELAY, ALARM, TAMPER, FAULT): a
    single zone in alarm IS the alarm system in alarm.
  * A command applies to EVERY zone, because the catalog's command has
    no zone to name. Per-zone control stays where it already is (the
    Intrusion page, the REST API).

Partial arming is real now (ArmMode.NIGHT - "dozór nocny"): ARMED means
every zone armed FULLY, ARMED_PARTIAL covers both "some zones armed" and
"armed, but only at night", and REQ.SEC.ARM_ALL_PARTIAL arms every zone in NIGHT
mode. A schematic that must know the difference gets it.

The sounder is real now, and it is real in the way the owner asked for:
the controller owns the STATE - SIREN_ACTIVE, SIREN_TIME_LEFT,
STROBE_ACTIVE, PANIC, and REQ.SEC.SILENCE to stop the noise without touching
the alarm - while the siren itself hangs on whatever DO the engineer
wires it to in Logic Studio. Nothing here energizes an output; these are
the facts a schematic reads to decide that for itself.

UNSERVED_SIGNALS is empty, and stays in place as the mechanism rather
than the list: a read of an unserved signal gets the catalog's own safe
value while a WRITE to one is reported instead of vanishing (see
logic_runtime.py's TagIOProvider.write_system_signal).
"""
from epw_os.core.access_manager import AccessLevel
from epw_os.core.intrusion_manager import ArmMode, LineState, ZoneState
from epw_os.core.logging import log

# Signals this controller cannot answer honestly yet - see the module
# docstring. Kept as data rather than as gaps in the dispatch table below
# so that "unserved" is a statement, not an accident of omission.
UNSERVED_SIGNALS = frozenset()

# The line states that ARE sabotage, as the catalog describes it
# ("obudowa, przewod, zwarcie linii") - a subset of what this controller
# counts as a line FAULT, which also covers an open circuit and a reading
# inside no configured window.
_TAMPER_STATES = (LineState.TAMPER, LineState.SHORT)


class SecuritySignalSource:
    """Reads SEC.SYSTEM.* and executes REQ.SEC.* against an IntrusionManager.

    `intrusion_manager` is None whenever the intrusion module is not part
    of this controller's composition - every read then answers the safe
    value and every command is refused, which is exactly right: logic
    that arms an alarm system this controller does not have must not
    appear to work.

    It may also be a CALLABLE returning the manager, which is how EPWCore
    passes it: the intrusion module can be switched on and off while the
    controller runs (feature configuration, no restart), replacing the
    manager object - a reference captured once at startup would then
    point at a module that no longer exists, or stay None forever after
    the module was turned on.
    """

    def __init__(self, intrusion_manager=None):
        self.intrusion_manager = intrusion_manager

    def _manager(self):
        source = self.intrusion_manager
        return source() if callable(source) else source

    # --- reads --------------------------------------------------------------

    def serves(self, signal_id: str) -> bool:
        """Whether this source answers for the signal at all. Asked of the
        tables rather than of the "SEC." prefix: with UNSERVED_SIGNALS
        empty, a prefix test would claim every name in the namespace,
        including a command this controller has no implementation for -
        which is precisely the case logic_runtime.py wants reported.

        feat/signal-register §3.3: a per-instance signal
        (SEC.ZONE.<id>.ARMED and friends) is judged by its SUFFIX, not by
        whether that zone exists right now. A zone can be added or
        removed while the controller runs, and "this controller has no
        implementation for that command" is a different statement from
        "that zone is gone" - conflating them would report a perfectly
        implemented request as unimplemented the moment a zone was
        deleted."""
        if signal_id in UNSERVED_SIGNALS:
            return False
        if signal_id in _READERS or signal_id in _COMMANDS or signal_id in _SYSTEM_COMMANDS:
            return True
        return _parse_instance_signal(signal_id) is not None

    def read(self, signal_id: str):
        """The signal's value, or None when this source does not answer
        for it at all (not an SEC signal, or one of UNSERVED_SIGNALS) -
        the caller then falls back to the catalog's safe value."""
        if signal_id in UNSERVED_SIGNALS:
            return None

        parsed = _parse_instance_signal(signal_id)
        if parsed is not None:
            kind, instance_id, suffix = parsed
            per_instance = (_ZONE_READERS if kind == "ZONE" else _LINE_READERS).get(suffix)
            if per_instance is None:
                return None          # a request, not a readable state
            manager = self._manager()
            if manager is None:
                return False
            return per_instance(manager, instance_id)

        handler = _READERS.get(signal_id)
        if handler is None:
            return None
        manager = self._manager()
        if manager is None:
            # Type-appropriate and defined, never None: a project whose
            # logic reads SEC on a controller without the intrusion
            # module sees "nothing is armed, nothing is wrong".
            return 0.0 if signal_id in _REAL_SIGNALS else False
        return handler(manager)

    # --- commands -----------------------------------------------------------

    def required_level(self, signal_id: str):
        """The level a per-zone request demands of whoever is present
        (logic_runtime.py takes the stricter of this and the block's
        own) - only for the requests added by etap 6; the earlier ones
        keep the block-level gate they were accepted with."""
        parsed = _parse_instance_signal(signal_id)
        if parsed is None or parsed[0] != "ZONE":
            return None
        return _ZONE_REQUEST_LEVELS.get(parsed[2])

    def execute(self, signal_id: str, actor: str) -> bool:
        """Runs a SEC.CMD_* command on every zone. True when it was
        carried out (on at least one zone), False when it was refused or
        there was nothing to run it on.

        `level=None` on every call into IntrusionManager: the access
        check for a logic-issued command is the BLOCK's own "Minimalny
        poziom dostepu" property, enforced before this method is reached
        (logic_runtime.py) - passing a level here as well would apply the
        operator gate to a program that is not an operator.
        """
        if signal_id in UNSERVED_SIGNALS:
            return False

        # A request aimed at ONE zone, rather than at every zone in turn.
        parsed = _parse_instance_signal(signal_id)
        if parsed is not None:
            kind, instance_id, suffix = parsed
            per_zone = _ZONE_REQUESTS.get(suffix) if kind == "ZONE" else None
            if per_zone is None:
                return False
            manager = self._manager()
            if manager is None:
                log.warning(f"Logic issued {signal_id}, but this controller has no intrusion module.")
                return False
            if not any(zone["id"] == instance_id for zone in manager.get_zones()):
                # Named a zone this installation does not have. Reported,
                # not silently dropped: a request that does nothing is
                # otherwise indistinguishable from one that worked.
                log.warning(f"Logic issued {signal_id}, but there is no zone {instance_id!r} "
                            f"on this controller - it was not applied.")
                return False
            done = bool(per_zone(manager, instance_id, actor))
            log.info(f"Logic issued {signal_id}: {'carried out' if done else 'refused'}.")
            return done

        system_command = _SYSTEM_COMMANDS.get(signal_id)
        command = _COMMANDS.get(signal_id)
        if command is None and system_command is None:
            return False
        manager = self._manager()
        if manager is None:
            log.warning(f"Logic issued {signal_id}, but this controller has no intrusion module.")
            return False

        if system_command is not None:
            done = system_command(manager, actor)
            log.info(f"Logic issued {signal_id}: {'carried out' if done else 'nothing to do'}.")
            return done

        zones = manager.get_zones()
        if not zones:
            log.warning(f"Logic issued {signal_id}, but this controller has no intrusion zones.")
            return False

        done = 0
        for zone in zones:
            if command(manager, zone["id"], actor):
                done += 1
        log.info(f"Logic issued {signal_id}: carried out on {done} of {len(zones)} zone(s).")
        return done > 0


# --- per-instance signals (feat/signal-register §3.3) ------------------------
#
# SEC.ZONE.<zone_id>.ARMED, SEC.LINE.<line_id>.VIOLATED,
# REQ.SEC.ZONE.<zone_id>.ARM. The catalog holds these as patterns and
# expands them from the project's own zones and lines; this end answers
# them against the live IntrusionManager.
#
# An id is parsed rather than matched against a generated table: the set
# of zones changes while the controller runs (a zone added in Studio and
# installed without a restart), and a table built at import would answer
# for yesterday's installation.

_INSTANCE_PREFIXES = (
    ("REQ.SEC.ZONE.", "ZONE"),
    ("SEC.ZONE.", "ZONE"),
    ("SEC.LINE.", "LINE"),
)


def _parse_instance_signal(signal_id: str):
    """("ZONE"|"LINE", instance_id, SUFFIX) for a per-instance signal, or
    None. The instance id may not contain a dot - an id that did would be
    ambiguous against the suffix, which is why the project's own ids are
    validated elsewhere."""
    for prefix, kind in _INSTANCE_PREFIXES:
        if not signal_id.startswith(prefix):
            continue
        rest = signal_id[len(prefix):]
        instance_id, _, suffix = rest.partition(".")
        if not instance_id or not suffix or "." in suffix:
            return None
        known = _ZONE_SUFFIXES if kind == "ZONE" else _LINE_SUFFIXES
        if suffix not in known:
            return None
        if signal_id.startswith("REQ.") != (suffix in _ZONE_REQUESTS):
            return None
        return kind, instance_id, suffix
    return None


def _zone_in_state(state):
    return lambda manager, zone_id: manager.get_zone_state(zone_id) == state


def _zone_lines(manager, zone_id) -> list:
    return [line for line in manager.get_lines() if line.get("zone_id") == zone_id]


def _zone_fault(manager, zone_id) -> bool:
    """"Awaria strefy" - any line of this zone in a fault state. The
    manager has no separate per-zone fault flag, and inventing one would
    mean deciding something this module has no business deciding; what it
    CAN answer truthfully is whether anything in the zone is faulty."""
    return any(manager.is_line_fault(line["id"]) for line in _zone_lines(manager, zone_id))


def _zone_bypassed(manager, zone_id) -> bool:
    return any(manager.is_line_bypassed(line["id"]) for line in _zone_lines(manager, zone_id))


def _zone_alarm_memory(manager, zone_id) -> bool:
    return bool(manager.get_alarm_memory(zone_id).get("active"))


_ZONE_READERS = {
    "ARMED": _zone_in_state(ZoneState.ARMED),
    "DISARMED": _zone_in_state(ZoneState.DISARMED),
    "ALARM": _zone_in_state(ZoneState.ALARM),
    "ENTRY_DELAY": _zone_in_state(ZoneState.ENTRY_DELAY),
    "EXIT_DELAY": _zone_in_state(ZoneState.EXIT_DELAY),
    "ALARM_MEMORY": _zone_alarm_memory,
    "WALK_TEST": lambda manager, zone_id: bool(manager.is_walk_test_active(zone_id)),
    "FAULT": _zone_fault,
    "BYPASSED": _zone_bypassed,
    # Signal register etap 6: arming inhibited (IntrusionManager.set_zone_inhibited).
    "INHIBITED": lambda manager, zone_id: bool(_call(manager, "is_zone_inhibited", zone_id)),
}


def _call(manager, method: str, *args):
    """A manager method that an older stand-in may not have: False then."""
    function = getattr(manager, method, None)
    return function(*args) if callable(function) else False


def _line_in_state(state):
    return lambda manager, line_id: manager.get_line_state(line_id) == state


_LINE_READERS = {
    "SECURE": _line_in_state(LineState.SECURE),
    "VIOLATED": lambda manager, line_id: bool(manager.is_line_violated_now(line_id)),
    "FAULT": lambda manager, line_id: bool(manager.is_line_fault(line_id)),
    "TAMPER": _line_in_state(LineState.TAMPER),
    "SHORT": _line_in_state(LineState.SHORT),
    # The register calls it OPEN_FAULT; this controller's own state is
    # FAULT_OPEN. The register names the signal, the code names the state.
    "OPEN_FAULT": _line_in_state(LineState.FAULT_OPEN),
    "UNDETERMINED": _line_in_state(LineState.UNDETERMINED),
    "BYPASSED": lambda manager, line_id: bool(manager.is_line_bypassed(line_id)),
    "SUSPECT": lambda manager, line_id: bool(manager.is_line_suspect(line_id)),
    "WALK_TEST_SEEN": lambda manager, line_id: bool(_call(manager, "is_line_walk_test_seen", line_id)),
}


def _bypass_zone(manager, zone_id: str, actor: str, bypassed: bool) -> bool:
    """Every line of the zone bypassed (or restored). Carried out when
    the zone has lines and each of them ends up in the requested state -
    a line already there counts as done, not as a failure."""
    lines = _zone_lines(manager, zone_id)
    if not lines:
        log.warning(f"SEC bypass request for zone {zone_id}: the zone has no lines.")
        return False
    for line in lines:
        if bool(manager.is_line_bypassed(line["id"])) != bypassed:
            manager.bypass_line(line["id"], bypassed, actor)
    return all(bool(manager.is_line_bypassed(line["id"])) == bypassed for line in lines)


def _inhibit_zone(manager, zone_id: str, actor: str, inhibited: bool) -> bool:
    setter = getattr(manager, "set_zone_inhibited", None)
    if not callable(setter):
        return False
    setter(zone_id, inhibited, actor)
    return bool(_call(manager, "is_zone_inhibited", zone_id)) == inhibited


_ZONE_REQUESTS = {
    "ARM": lambda manager, zone_id, actor: _arm(manager, zone_id, actor),
    "DISARM": lambda manager, zone_id, actor: _disarm(manager, zone_id, actor),
    "CLEAR_MEMORY": lambda manager, zone_id, actor: _reset(manager, zone_id, actor),
    "START_WALK_TEST": lambda manager, zone_id, actor: bool(
        manager.start_walk_test(zone_id, actor=actor)),
    "STOP_WALK_TEST": lambda manager, zone_id, actor: bool(
        manager.stop_walk_test(zone_id, actor=actor) is not None),
    # Signal register etap 6.
    "BYPASS": lambda manager, zone_id, actor: _bypass_zone(manager, zone_id, actor, True),
    "UNBYPASS": lambda manager, zone_id, actor: _bypass_zone(manager, zone_id, actor, False),
    "INHIBIT": lambda manager, zone_id, actor: _inhibit_zone(manager, zone_id, actor, True),
    "UNINHIBIT": lambda manager, zone_id, actor: _inhibit_zone(manager, zone_id, actor, False),
}

# The level the same action needs from the panel (rule Z2): a bypass is
# an engineer's (IntrusionManager.bypass_line), an inhibit an operator's.
_ZONE_REQUEST_LEVELS = {
    "BYPASS": AccessLevel.ENGINEER, "UNBYPASS": AccessLevel.ENGINEER,
    "INHIBIT": AccessLevel.OPERATOR, "UNINHIBIT": AccessLevel.OPERATOR,
}

_ZONE_SUFFIXES = frozenset(_ZONE_READERS) | frozenset(_ZONE_REQUESTS)
_LINE_SUFFIXES = frozenset(_LINE_READERS)


# --- the per-signal readers -------------------------------------------------
# Each takes the manager and returns that signal's value. Plain functions
# in one table so the whole mapping is readable top to bottom.

def _zone_states(manager) -> list:
    return [manager.get_zone_state(zone["id"]) for zone in manager.get_zones()]


def _zone_modes(manager) -> list:
    return [manager.get_zone_arm_mode(zone["id"]) for zone in manager.get_zones()]


def _armed(manager) -> bool:
    """Every zone armed, and every one of them armed FULLY. A site whose
    perimeter watches while the people inside move around is NOT "armed"
    to a schematic that energizes something on it - that is exactly what
    ARMED_PARTIAL is for."""
    zones = manager.get_zones()
    if not zones:
        return False
    return all(manager.get_zone_state(zone["id"]) == ZoneState.ARMED
               and manager.get_zone_arm_mode(zone["id"]) == ArmMode.FULL for zone in zones)


def _armed_partial(manager) -> bool:
    """Something is watching, but not everything: either some zones are
    armed and some are not, or a zone is armed at night (watching only
    the lines flagged for it)."""
    zones = manager.get_zones()
    if not zones:
        return False
    armed = [z for z in zones if manager.get_zone_state(z["id"]) == ZoneState.ARMED]
    if not armed:
        return False
    if len(armed) != len(zones):
        return True
    return any(manager.get_zone_arm_mode(z["id"]) == ArmMode.NIGHT for z in armed)


def _disarmed(manager) -> bool:
    states = _zone_states(manager)
    return bool(states) and all(state == ZoneState.DISARMED for state in states)


def _any_state(state):
    return lambda manager: any(s == state for s in _zone_states(manager))


def _ready_to_arm(manager) -> bool:
    """"wszystkie linie w spoczynku" - every line that would block an
    arm: violated now, or in a fault state. A bypassed line is
    deliberately still counted as blocking readiness: bypass is what an
    operator uses to arm ANYWAY, not a reason to call the system ready.
    """
    lines = manager.get_lines()
    if not manager.get_zones():
        return False
    return not any(manager.is_line_violated_now(line["id"]) or manager.is_line_fault(line["id"])
                   for line in lines)


def _delay_remaining(manager) -> float:
    """The longest countdown still running on any zone - the one that
    matters to a schematic holding a door release open "while the exit
    delay runs"."""
    remaining = [manager.get_countdown_remaining(zone["id"]) for zone in manager.get_zones()]
    return float(max(remaining)) if remaining else 0.0


def _alarm_memory(manager) -> bool:
    return any(manager.get_alarm_memory(zone["id"]).get("active") for zone in manager.get_zones())


def _alarm_latched(manager) -> bool:
    """The latch that outlives the condition: a zone whose alarm memory is
    still set although the zone itself is no longer in ALARM - i.e. the
    system is waiting for someone to clear it. While the alarm is still
    active, SEC.SYSTEM.ALARM is the signal that says so."""
    return any(manager.get_alarm_memory(zone["id"]).get("active")
               and manager.get_zone_state(zone["id"]) != ZoneState.ALARM
               for zone in manager.get_zones())


def _tamper(manager) -> bool:
    return any(manager.get_line_state(line["id"]) in _TAMPER_STATES for line in manager.get_lines())


def _fault(manager) -> bool:
    return any(manager.is_line_fault(line["id"]) for line in manager.get_lines())


def _active_count(manager) -> float:
    return float(sum(1 for line in manager.get_lines() if manager.is_line_violated_now(line["id"])))


def _last_trigger(manager) -> float:
    """"Numer linii, ktora wywolala ostatni alarm" - taken from the alarm
    memory's own recorded first cause, as the digits of that line's id
    (the ids this controller mints are "<prefix><n>"). 0 when nothing has
    triggered since the last clear, or when the id carries no number."""
    for zone in manager.get_zones():
        cause = manager.get_alarm_memory(zone["id"]).get("first_cause_line_id")
        if not cause:
            continue
        digits = "".join(ch for ch in str(cause) if ch.isdigit())
        if digits:
            return float(digits)
    return 0.0


def _siren_active(manager) -> bool:
    """What a schematic drives the siren DO from. It goes false on its
    own when the configured sounding time is up, while SEC.SYSTEM.ALARM and
    STROBE_ACTIVE carry on - the noise stops, the alarm does not."""
    return bool(manager.siren_active())


def _strobe_active(manager) -> bool:
    return bool(manager.strobe_active())


def _siren_time_left(manager) -> float:
    return float(manager.siren_time_left())


def _panic(manager) -> bool:
    """A hold-up line fired and nobody has cleared the alarm memory yet.
    Separate from SEC.SYSTEM.ALARM on purpose: a schematic may want to send
    THIS one somewhere quietly and leave the siren alone."""
    return bool(manager.panic_active())


_READERS = {
    "SEC.SYSTEM.ARMED": _armed,
    "SEC.SYSTEM.ARMED_PARTIAL": _armed_partial,
    "SEC.SYSTEM.DISARMED": _disarmed,
    "SEC.SYSTEM.READY_TO_ARM": _ready_to_arm,
    "SEC.SYSTEM.EXIT_DELAY": _any_state(ZoneState.EXIT_DELAY),
    "SEC.SYSTEM.ENTRY_DELAY": _any_state(ZoneState.ENTRY_DELAY),
    "SEC.SYSTEM.DELAY_REMAINING": _delay_remaining,
    "SEC.SYSTEM.ALARM": _any_state(ZoneState.ALARM),
    "SEC.SYSTEM.ALARM_LATCHED": _alarm_latched,
    "SEC.SYSTEM.ALARM_MEMORY": _alarm_memory,
    "SEC.SYSTEM.TAMPER": _tamper,
    "SEC.SYSTEM.FAULT": _fault,
    "SEC.SYSTEM.LAST_TRIGGER": _last_trigger,
    "SEC.SYSTEM.ACTIVE_COUNT": _active_count,
    "SEC.SYSTEM.SIREN_ACTIVE": _siren_active,
    "SEC.SYSTEM.STROBE_ACTIVE": _strobe_active,
    "SEC.SYSTEM.SIREN_TIME_LEFT": _siren_time_left,
    "SEC.SYSTEM.PANIC": _panic,
    # Signal register etap 6: the register's own aggregates, each what
    # the manager can answer truthfully.
    "SEC.SYSTEM.TECHNICAL_ALARM": lambda manager: bool(_call(manager, "technical_alarm_active")),
    "SEC.SYSTEM.ANY_ZONE_ARMED": _any_state(ZoneState.ARMED),
    "SEC.SYSTEM.ANY_ZONE_ALARM": _any_state(ZoneState.ALARM),
    "SEC.SYSTEM.ANY_LINE_VIOLATED": lambda manager: any(
        manager.is_line_violated_now(line["id"]) for line in manager.get_lines()),
    "SEC.SYSTEM.ANY_LINE_FAULT": _fault,
    "SEC.SYSTEM.WALK_TEST": lambda manager: any(
        bool(manager.is_walk_test_active(zone["id"])) for zone in manager.get_zones()),
}

_REAL_SIGNALS = frozenset({"SEC.SYSTEM.DELAY_REMAINING", "SEC.SYSTEM.LAST_TRIGGER", "SEC.SYSTEM.ACTIVE_COUNT",
                           "SEC.SYSTEM.SIREN_TIME_LEFT"})


# --- the commands -----------------------------------------------------------

def _arm(manager, zone_id: str, actor: str, mode: str = ArmMode.FULL) -> bool:
    result = manager.arm_zone(zone_id, actor=actor, mode=mode)
    if not getattr(result, "success", False):
        # A zone that will not arm (a violated line, a fault) is the
        # normal reason - logged so a command that quietly did nothing is
        # never a mystery.
        log.warning(f"SEC arm refused for zone {zone_id}: {getattr(result, 'reason', '')}")
    return bool(getattr(result, "success", False))


def _disarm(manager, zone_id: str, actor: str) -> bool:
    return bool(manager.disarm_zone(zone_id, actor=actor))


def _reset(manager, zone_id: str, actor: str) -> bool:
    return bool(manager.clear_alarm_memory(zone_id, actor=actor))


def _arm_night(manager, zone_id: str, actor: str) -> bool:
    """"Załącz dozór częściowy" - every zone armed in NIGHT mode, where
    only the lines flagged `active_at_night` watch."""
    return _arm(manager, zone_id, actor, mode=ArmMode.NIGHT)


def _silence(manager, actor: str) -> bool:
    """"Wycisz sygnalizator" - the sounder only. The zone stays in ALARM,
    the memory stays, the strobe stays on. Not per zone: there is one
    sounder state, so silencing it "on every zone" would be four calls
    doing one thing."""
    return bool(manager.silence(actor=actor))


_COMMANDS = {
    "REQ.SEC.ARM_ALL": _arm,
    "REQ.SEC.ARM_ALL_PARTIAL": _arm_night,
    "REQ.SEC.DISARM_ALL": _disarm,
    "REQ.SEC.CLEAR_ALARM_MEMORY": _reset,
}

# Commands that act on the SYSTEM rather than on each zone in turn - run
# once, with no zone id. Kept as a table beside _COMMANDS so that
# "per-zone" stays the readable default.
_SYSTEM_COMMANDS = {
    "REQ.SEC.SILENCE": _silence,
}
