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
etap 1)."""

from dataclasses import dataclass, field


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
        """Replaces the whole known apparatus list - called by whoever
        loads a project (today: nobody in production code; tests only.
        See this module's own docstring for the future projekt.epw
        wiring point)."""
        self._by_id = {a.id: a for a in apparatuses}

    def get(self, apparatus_id):
        return self._by_id.get(apparatus_id)

    def list_ids(self):
        return sorted(self._by_id.keys())

    def is_empty(self):
        return not self._by_id

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
