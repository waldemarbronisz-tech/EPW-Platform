"""Apparatus (aparat) registry - task "migracja adresacji", point 1.2's
own doprecyzowanie (Waldek's reply, wariant C).

An apparatus is exactly what Studio's own project format already calls
it (studio/shell/project_format.py's `Device` dataclass): an id, a list
of `feedback` addresses (which points it is OBSERVED through) and a
list of `command` addresses (which points it is DRIVEN through). Those
addresses are point-registry entries - `ELA1.DI.5`-shaped strings from
this same platform's one grammar (epw_os/core/addressing.py) - NEVER a
second, apparatus-owned namespace. Per the contract Waldek stated
verbatim: "Jeden zacisk = jeden adres = jedna nazwa w całym projekcie
[...] Aparat NIE tworzy nowych nazw." An `Apparatus` object here is
purely an INDEX into the point registry (which two - or more - existing
addresses does this id group together), never a place that invents
`KOT_KMG1.feedback`-style derived names.

Why this module exists instead of the two paths already ruled out:
runtime does not read `projekt.epw` yet (a separate, not-yet-built
task) and `project.json`/its own config-screen convention is on its
way out (Studio is where a project's structure gets designed now) - so
neither "persist a new project.json section" nor "build a runtime
settings screen for this" is the right home; both would need undoing
the moment runtime CAN read projekt.epw. This module is deliberately
the SMALLEST thing that stops lying: an in-memory registry, populated
by whoever constructs EPWCore, empty by default (see EPWCore.__init__'s
own comment for exactly where it's `None`/empty today and where the
future projekt.epw-reading task should populate it instead).

Consumers (page_entry_gate.py, protection_verifier.py) ask this
registry "what does apparatus X look like right now" rather than
keeping their own copy of DI2/DI3/DI4/DO01-04-style literals - the
same "one source of truth" principle GRANICE already applies to
Main View vs. System Topology (two screens, one real device list) and
to intrusion_manager.py's own DI/AI candidate picker (one shared
grammar check, not three disagreeing ones - see this task's own
etap 1).

UPDATE (task "runtime czyta projekt.epw", 3.2): the registry is no longer
empty in production - EPWCore.startup() fills it from projekt.epw's own
apparatus register ("devices") through apparatuses_from_records(), and
binds the Main View roles with bind_roles_by_designation() below. It is
still a plain in-memory index; the project file remains the only place an
apparatus is defined."""

from dataclasses import dataclass, field

from epw_os.core.logging import log


@dataclass
class Apparatus:
    """One row of the (future) rejestr aparatów, as runtime needs to
    see it. `feedback`/`command` are point-registry addresses (task's
    own grammar) - not apparatus-owned identifiers. Either list may be
    empty (an apparatus with no feedback assigned yet, or a read-only
    one with no command) - callers must check, never assume index [0]
    exists."""

    id: str
    feedback: list = field(default_factory=list)
    command: list = field(default_factory=list)
    behavior: str = ""  # SWITCHED | SIGNAL | MEASURED | MODULATED | SELECTOR
    kind: str = ""      # free-text label, no functional meaning (SPEC_PROJEKT_EPW.md)
    # Task "wyłącznik jednocewkowy bistabilny" - HOW the command outputs
    # drive the apparatus (shared/project_format.py's Device.command_style):
    #   MAINTAINED   level: energized = ON (one coil), or one coil per
    #                direction held energized (two coils)
    #   PULSE        a pulse_ms pulse per direction, one coil each
    #   PULSE_TOGGLE a single-coil impulse relay (R15/3P-class): EVERY
    #                pulse toggles, whichever output (or a local push-
    #                button) delivered it - so an output is pulsed only
    #                when the feedback says the apparatus is NOT already
    #                in the requested state. Feedback is mandatory.
    command_style: str = "MAINTAINED"
    pulse_ms: int = 0


COMMAND_STYLES = ("MAINTAINED", "PULSE", "PULSE_TOGGLE")


def apparatus_command_definitions(apparatuses) -> dict:
    """CommandManager.load_definitions() entries - `<id>.CLOSE` and
    `<id>.OPEN` - for every SWITCHED apparatus that has a command output,
    derived from its command_style (see Apparatus above). `feedback[0]`
    is the CLOSED indication (Studio's Device.feedback keeps the closed
    contact first - SPEC_PROJEKT_EPW.md "Aparaty"); `command[0]` is the
    CLOSE output and `command[1]`, when present, the OPEN one.

    Before this, an apparatus had NO command definitions of its own at
    all - only the per-DO `ELA1.DO.3.CLOSE`-style defaults existed, which
    write a level and never release it, so a pulsed coil could not be
    driven correctly from the project. Returns {} for an apparatus that
    can't be commanded honestly (no command output; PULSE_TOGGLE without
    feedback - pulsing blind would flip it the wrong way half the time),
    logged, never guessed."""
    definitions = {}
    for apparatus in apparatuses:
        if apparatus.behavior != "SWITCHED" or not apparatus.command:
            continue
        style = apparatus.command_style if apparatus.command_style in COMMAND_STYLES else "MAINTAINED"
        close_out = apparatus.command[0]
        open_out = apparatus.command[1] if len(apparatus.command) > 1 else None
        closed_fb = apparatus.feedback[0] if apparatus.feedback else None
        pulse = int(apparatus.pulse_ms or 0) if style != "MAINTAINED" else None
        if style != "MAINTAINED" and not pulse:
            log.warning(f"Apparatus {apparatus.id}: {style} without pulse_ms - not commandable")
            continue
        if style == "PULSE_TOGGLE" and not closed_fb:
            log.warning(f"Apparatus {apparatus.id}: PULSE_TOGGLE without feedback - not commandable")
            continue

        def _definition(output_tag, output_value, feedback_value, reset_tag=None):
            entry = {"driver_id": "SIM_DRIVER", "output_tag": output_tag, "output_value": output_value,
                     "timeout_ms": 1500}
            if closed_fb:
                entry["feedback_tag"] = closed_fb
                entry["feedback_value"] = feedback_value
            if pulse:
                entry["pulse_ms"] = pulse
            if style == "PULSE_TOGGLE":
                entry["skip_when_feedback_matches"] = True
            if reset_tag:
                entry["also_reset_tag"] = reset_tag
            return entry

        if style == "MAINTAINED":
            if open_out:
                definitions[f"{apparatus.id}.CLOSE"] = _definition(close_out, True, True, reset_tag=open_out)
                definitions[f"{apparatus.id}.OPEN"] = _definition(open_out, True, False, reset_tag=close_out)
            else:
                definitions[f"{apparatus.id}.CLOSE"] = _definition(close_out, True, True)
                definitions[f"{apparatus.id}.OPEN"] = _definition(close_out, False, False)
        elif style == "PULSE":
            definitions[f"{apparatus.id}.CLOSE"] = _definition(close_out, True, True)
            if open_out:
                definitions[f"{apparatus.id}.OPEN"] = _definition(open_out, True, False)
        else:  # PULSE_TOGGLE - one coil behind one or two outputs
            definitions[f"{apparatus.id}.CLOSE"] = _definition(close_out, True, True)
            definitions[f"{apparatus.id}.OPEN"] = _definition(open_out or close_out, True, False)
    return definitions


class ApparatusRegistry:
    """Holds "which apparatuses exist right now" for the running
    program. Empty by default - "no apparatus configured" is the
    honest starting state (task's own explicit decision: no fallback
    literal, no invented default), not silently substituted data.

    `role` in get_by_role()/set_role_binding() is a FIXED, code-level
    identifier for a specific slot a screen or a safety check needs to
    fill (e.g. page_entry_gate.py's "main_view.q1" - the main incomer
    breaker symbol on the Main View one-line diagram, a specific
    drawn position, not project data) - separate from `id`, which is
    the apparatus's own real identity in the project's own rejestr
    aparatów. The role->id binding is itself a small piece of
    configuration this module also holds empty by default, for the
    identical reason: which real apparatus fills the "main incomer"
    role on a given site is an operator/engineer decision, not
    something this module may guess."""

    def __init__(self):
        self._by_id = {}
        self._role_bindings = {}

    def set_apparatuses(self, apparatuses):
        """Replaces the whole known apparatus list - called by
        EPWCore.startup() with the project's own apparatus register."""
        self._by_id = {a.id: a for a in apparatuses}

    def get(self, apparatus_id):
        return self._by_id.get(apparatus_id)

    def list_ids(self):
        return sorted(self._by_id.keys())

    def is_empty(self):
        return not self._by_id

    def testable_ids(self):
        """Apparatuses a protection verification test can run against: an
        output to trip and a feedback to observe the trip on - both taken
        from the apparatus's own definition."""
        return sorted(a.id for a in self._by_id.values() if a.command and a.feedback)

    def set_role_binding(self, role: str, apparatus_id):
        """`apparatus_id=None` clears the binding (role has no
        apparatus assigned) - same "absence is the honest state"
        stance as everything else in this module."""
        if apparatus_id is None:
            self._role_bindings.pop(role, None)
        else:
            self._role_bindings[role] = apparatus_id

    def get_by_role(self, role: str):
        """The Apparatus bound to `role`, or None if the role has no
        binding OR the bound id no longer exists in the registry (a
        stale binding is treated exactly like no binding - never a
        crash, never a guess)."""
        apparatus_id = self._role_bindings.get(role)
        if apparatus_id is None:
            return None
        return self._by_id.get(apparatus_id)


def apparatuses_from_records(records):
    """[{id, behavior, kind, feedback, command}] (ProjectManager.
    get_apparatuses()) -> Apparatus objects."""
    return [
        Apparatus(id=r["id"], feedback=list(r.get("feedback", [])), command=list(r.get("command", [])),
                  behavior=r.get("behavior", ""), kind=r.get("kind", ""),
                  command_style=r.get("command_style") or "MAINTAINED", pulse_ms=int(r.get("pulse_ms") or 0))
        for r in records
    ]


# Main View (page_entry_gate.py) is a FIXED drawing of an entry gate: main
# incomer Q1, generator contactor KMG, feeders KM1/KM2 and the voltage
# monitoring relay KVG1. Which real apparatus fills each symbol is decided
# by its designation - the part of the apparatus id after the location
# prefix (SPEC_PROJEKT_EPW.md: "KOT_KMG1 i MH_KMG1 to dwa różne aparaty"),
# or the whole id when it has no prefix. projekt.epw has no field binding a
# drawn symbol to an apparatus (that arrives with screens embedded in the
# project, where every screen object carries its own deviceId), so this is
# a naming rule, stated here and in the task report rather than guessed.
MAIN_VIEW_ROLE_DESIGNATIONS = {
    "main_view.q1": "Q1",
    "main_view.kmg": "KMG",
    "main_view.km1": "KM1",
    "main_view.km2": "KM2",
    "main_view.voltage_relay": "KVG1",
}


def bind_roles_by_designation(registry, role_designations):
    """Binds each role to the ONE apparatus whose id is the designation or
    ends with "_" + designation. No match, or more than one (the same
    designation in two locations), leaves the role unbound - the page then
    says "not configured" instead of picking one. Returns {role: id or None}."""
    outcome = {}
    ids = registry.list_ids()
    for role, designation in role_designations.items():
        matches = [i for i in ids if i == designation or i.endswith("_" + designation)]
        if len(matches) == 1:
            registry.set_role_binding(role, matches[0])
            outcome[role] = matches[0]
            continue
        registry.set_role_binding(role, None)
        outcome[role] = None
        if len(matches) > 1:
            log.warning(f"Main View symbol {designation} left unconfigured: several apparatuses match "
                        f"({', '.join(matches)}).")
    return outcome
