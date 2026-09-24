"""The `projekt.epw` file format - shared/docs/SPEC_PROJEKT_EPW.md is the
authoritative contract this module implements.

ONE implementation for the whole platform (task "runtime czyta
projekt.epw", point 1.1): Studio writes the file with it, runtime reads
it with it. It lives in shared/ for the same reason shared/addressing.py
does - two hand-kept copies of one format are two formats a few months
later. Studio imports it through studio/shell/project_format.py, runtime
through runtime/epw_os/core/project_format.py (by path); both are thin
re-exports. Standard library only, and no user-facing text of its own:
every refusal and warning is a `key` + `params` pair, translated by
whichever program shows it (see ISSUE_TEXT_EN below). Read that document before
changing anything here; this module's own docstrings quote it rather than
restate it from memory, so the two don't quietly drift apart.

Scope of THIS module: the "structural" fields the contract groups under
Studio's exclusive editing layer (Nagłówek, Skład urządzenia, Sprzęt,
Punkty, Aparaty, Alarmówka, Nastawy zabezpieczeń) AND - task "Studio
osadza ekrany i logikę w projekt.epw" (user report: "tworząc synoptykę
w projekcie i zapisując projekt na głównym pasku, synoptyka nie zapisuje
się [...] dalej to traktowane jest jako osobne programy") - the two
editors' own documents, embedded whole:

  screens        the Synoptic Editor's project (the EPW_SYNOPTIC
                 document, identical to a .epwsyn file's content -
                 SPEC: "struktura obiektu pozostaje identyczna")
  logic          the Logic Studio project (EPW_LOGIC - the editable
                 source, blocks and wires)
  logic_runtime  the compiled logic (EPW_RUNTIME_LOGIC - what runtime's
                 LogicEngine executes; refreshed by Studio on every save
                 the source compiles on)

All three are plain dicts kept verbatim - this module validates that
they are objects, nothing more; each editor/loader validates its own
document (ProjectManager.loadProject, Project.deserialize,
epwsyn_loader, LogicEngine). .epwsyn/.epwlogic stay as EXCHANGE formats
(SPEC: "format wymiany"), never the project's source of truth.

ElectricalProtectionStage/ProcessProtection ("Zabezpieczenia: na maksa
dużo opcji") are TWO DIFFERENT real domains, kept separate here exactly
as runtime/epw_os/core/protection_manager.py (electrical) and
process_protection_manager.py (process) keep them:
  - Electrical: a FIXED catalog of ANSI-coded relay functions (27/59/
    50/51/...), delegated to ADA01 hardware, never evaluated by
    software - Studio stores per-STAGE VALUES (enabled/setting/
    hysteresis/delay_ms/action) against project_panels.py's own
    ELECTRICAL_PROTECTION_CATALOG constant (a hand-copy of
    protection_manager.py's init_defaults() - GRANICE forbids a
    runtime/ import here), never new functions/stages - the catalog
    itself is what the hardware implements, not something a project
    can invent.
  - Process: a dynamic, user-created list, evaluated LIVE in software
    against a real analog point - field-for-field match to
    process_protection_manager.add_protection()/update_protection().
Both share the same runtime-tag-name gap already documented for
Line.tag: `analog_tag` here is a Point.address, not yet a resolvable
runtime tag.

Zone/Line/PowerSupervision below intentionally carry MORE fields than
the contract's own terse "Alarmówka" section spells out (`lines typ
linii (EOL/DEOL), punkt, opóźnienia`) - runtime/epw_os/core/
intrusion_manager.py already implements a considerably richer, real,
tested parameter set (multiplicity/lockout/alarm_hold/silence_threshold
per line, mains/battery power supervision system-wide) that predates
this module. Task "Alarmówka: na maksa dużo opcji" chose to expose
runtime's REAL ceiling, not just the contract's minimal illustrative
subset - every field here has a concrete, already-executing meaning on
the runtime side, named identically. Update (task "migracja adresacji"):
that future wiring step's grammar half is done - intrusion_manager.py's
own `tag` is now the SAME `<card>.<KIND>.<channel>` shape as this
module's Point.address (both go through shared/addressing.py), not the
flat "DI5"/"ELA01.DI05" TagManager name this comment used to describe.
Line.tag below stores a Point.address; runtime reading `projekt.epw`
directly (rather than today's `project.json`) is the remaining, still
genuinely unbuilt half of that gap - not an address-format mismatch
anymore, just a file this program doesn't read yet.

The contract's own "timings: czas na wyjście, czas na wejście, czas
sygnalizacji" doesn't fully match runtime either: exit/entry delay are
real, per-ZONE fields (Zone.exit_delay_seconds/entry_delay_seconds) -
but no "czas sygnalizacji" (a zone-wide siren/signaling duration)
exists in intrusion_manager.py at all. The closest real thing is
Line.alarm_hold_seconds - per-LINE, how long a raised alarm auto-holds
before clearing - a different concept under a different name. No
"signaling duration" field is invented here to paper over that gap;
alarm_hold_seconds is exposed under its own, real name.

Adding a field here
is safe and additive - `load_project()` tolerates every field's absence
(the contract's own rule for the old multi-file archive - "katalogi
nieużywane mogą nie istnieć, czytnik ma to znieść bez błędu" - applied
here to JSON keys instead of archive members) and `save_project()` never
writes a key whose collection is empty, so a bare-metadata-only project
is exactly as valid a file as one with everything filled in.

Physical container: **gzip-compressed UTF-8 JSON**, not a ZIP archive.
This is a decision this module makes, not something the contract itself
states outright - the old SPEC_FORMAT_EPW.md's "zwykłe archiwum ZIP"
reasoning (each part viewable separately, extensibility) stops applying
once every part lives as fields inside ONE JSON document rather than
separate files; there is nothing left inside the archive for a ZIP
container to usefully separate. Gzip keeps a real project (many screens'
worth of graphics, compiled logic) from being an unreasonably large text
file, using only the standard library (`gzip`, `json` - GRANICE: "nie
dodawaj zależności"), and keeps "jeden plik" literally true - one
compressed byte stream, not an archive of members. Flagged here plainly
because it is a genuine engineering call the contract leaves open, not
because anything in the contract required it - revisit if that
assumption turns out wrong.
"""
import gzip
import json
import os
import shutil
import tempfile
import types
import typing
import zlib
from dataclasses import MISSING, asdict, dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

FORMAT_MARKER = "EPW_PROJECT_FILE"
SCHEMA_VERSION = 2


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class ProjectMetadata:
    """SPEC_PROJEKT_EPW.md, "Nagłówek": `project nazwa, opis, autor,
    daty utworzenia i zmiany`."""

    name: str
    description: str = ""
    author: str = ""
    created_at: str = field(default_factory=_utc_now_iso)
    modified_at: str = field(default_factory=_utc_now_iso)


@dataclass
class Card:
    """SPEC_PROJEKT_EPW.md, "Sprzęt": `id (nadane przez użytkownika),
    model, kanały (rodzaj -> liczba kanałów)`. Example from the
    contract's own single-kind case: id="DI1", model="ELA01",
    channel_kinds={"DI": 32}.

    `channel_kinds` (task follow-up, user report: "karta ELA1 ma DI oraz
    AI" - real hardware, one physical module with more than one channel
    kind) maps EVERY kind this card actually has to ITS OWN channel
    count - {"DI": 8, "AI": 4} for a mixed digital+analog module,
    {"DI": 32} for the common single-kind case. One Card row is one
    physical module - one id, one Modbus address, one location.
    (An earlier version of this fix represented a mixed module as TWO
    Card rows sharing an id, one per kind - abandoned because it forced
    modbus_unit_id/location to be entered twice and kept in sync by
    hand, for no reason the address grammar, <id>.<KIND>.<channel> with
    KIND already its own segment, ever required.) schema_version 1
    files hand-copy their old "kind"/"channels" pair into this shape on
    load - see _migrate_schema_v1_cards() below; saving always writes
    the current shape.

    `modbus_unit_id` (task: "ELA i ADA i EPM będą łączyły się z orange
    pi [...] po modbus - trzeba dać opcję adresowania") is GREENFIELD -
    unlike Zone/Line/ElectricalProtectionStage, no ModbusDriver exists
    in runtime yet to mirror field-for-field (confirmed: runtime/epw_os/
    core/comm_diagnostics.py's own docstring describes itself as built
    FOR a still-nonexistent future ModbusDriver). This is a standard
    Modbus unit/slave address (1-247, RTU/TCP alike) - `None` means
    "not addressed yet", same "absent = not configured" convention
    every other optional field in this module already uses.

    `location` (task "jedno źródło listy kart" 3.4) is where the MODULE
    itself physically sits (the cabinet/panel) - a card in one cabinet
    routinely feeds terminals in several different physical locations
    (kotłownia, piwnica, brama), so this is only ever a DEFAULT for its
    own points to inherit, never a claim about where every one of its
    terminals actually goes - see Point.location's own docstring for
    the inheritance rule itself."""

    id: str
    model: str
    channel_kinds: Dict[str, int] = field(default_factory=dict)
    modbus_unit_id: Optional[int] = None
    location: str = ""


@dataclass
class Location:
    """SPEC_PROJEKT_EPW.md, "Sprzęt": `kod (prefiks), opis`. Example:
    code="KOT", description="Kotłownia". The prefix a Location supplies
    is what SPEC_PROJEKT_EPW.md's own "Aparaty" section relies on for
    apparatus-id uniqueness (KOT_KMG1 vs MH_KMG1) - enforced by whatever
    UI creates Device ids, not by this module itself."""

    code: str
    description: str = ""


@dataclass
class Point:
    """SPEC_PROJEKT_EPW.md, "Punkty - rejestr zacisków". `address` is
    card-relative per the contract's own addressing rule (`<id_karty>.
    <RODZAJ>.<KANAŁ>`, e.g. "DI1.DI.1") - deliberately NOT validated
    against `cards` by this dataclass itself (a point can be constructed
    before its card exists, e.g. during migration); whatever builds the
    point registry UI is responsible for that check, same division of
    responsibility as Card/Location above.

    The five analog-only fields are None for a digital point - the
    contract lists them as "dla punktów analogowych dodatkowo", not as
    always-present-but-empty.

    `location` (task "jedno źródło listy kart" 3.4): `None` means
    "inherit the owning card's own `location`" (Card.location above) -
    the DEFAULT for every point, since most of a card's terminals really
    do share its cabinet as their nearest useful location label. A real
    string (including `""`) is an EXPLICIT override - a user who typed
    something different for this one terminal, or deliberately cleared
    it back to blank despite the card having a location. Distinguishing
    None from "" is exactly what makes "changing the card's location
    must never overwrite a point's own explicit choice" possible without
    a second, parallel "is this overridden" flag - same "absent = not
    configured, distinct from empty" convention Card.modbus_unit_id
    already uses. Always resolve through project_panels.py's own
    effective_location(), never read this field raw outside the one
    place (the point registry table) that needs to tell inherited and
    explicit apart."""

    address: str
    description: str = ""
    location: Optional[str] = None
    technical_note: str = ""
    signal_type: Optional[str] = None
    raw_min: Optional[float] = None
    raw_max: Optional[float] = None
    eng_min: Optional[float] = None
    eng_max: Optional[float] = None
    unit: Optional[str] = None
    decimals: Optional[int] = None
    # ZADANIA p. 6 (2026-09-17): the switching counter's warning threshold
    # is a SETTING (SPEC "Nastawa"), so it lives on the DI point it counts
    # for - None = no warning. The panel may change it (written back like
    # every other setting); the counts themselves stay runtime state.
    warning_threshold: Optional[int] = None
    # Signal register etap 4: a DI point can CARRY a register signal that
    # arrives as a dry contact (a UPS status contact, an external
    # protection relay's trip contact, a mains-present relay) - `role` is
    # that signal's id from shared/logic/point_roles.py (the catalogue's
    # PWR/UPS/PROT entries a contact can carry), None = no role. `contact`
    # is the contact type: "NO" (closed = TRUE) or "NC" (open = TRUE), so
    # a supervision bit reads TRUE for the healthy state whichever contact
    # the relay offers. The controller exposes the bit under the role's
    # own name; only DI points may carry one.
    role: Optional[str] = None
    contact: str = "NO"


def effective_location(point: Point, card) -> str:
    """User report 3.4 ("dziedziczenie z karty"): the location a reader
    (export, validation, the point registry, runtime's DI/DO pages)
    should actually SHOW - `point.location` if the user explicitly set
    one (a real string, "" included - "deliberately no location despite
    the card having one"), otherwise the owning card's own `location`
    (or "" if `card` is None or has none either). See Point.location's
    own docstring for why None vs "" is the distinction that makes this
    possible. Lives here, next to Point, so Studio and runtime resolve
    it with the same rule."""
    if point.location is not None:
        return point.location
    return card.location if card is not None else ""


@dataclass
class Device:
    """SPEC_PROJEKT_EPW.md, "Aparaty" (the contract's "wariant B" -
    apparatus configuration lives here once, never inside a screen
    file). `feedback`/`command` are lists of Point addresses; this
    dataclass does not itself enforce SPEC_PROJEKT_EPW.md's "Aparat
    zużywa punkty [...] Studio ma to wykryć przy przypisaniu" rule - a
    plain dataclass has no notion of "the rest of the project" to check
    against; that belongs in whatever UI assigns a point to a device."""

    id: str
    behavior: str  # SWITCHED | SIGNAL | MEASURED | MODULATED | SELECTOR
    kind: str = ""
    feedback: list[str] = field(default_factory=list)
    command: list[str] = field(default_factory=list)
    supervision: dict = field(default_factory=dict)
    safe_state: dict = field(default_factory=dict)  # onStartup, onLinkLoss
    # Task "wyłącznik jednocewkowy bistabilny" - HOW `command` drives a
    # SWITCHED apparatus (SPEC_PROJEKT_EPW.md, "Aparaty"):
    #   MAINTAINED   a level - energized = ON (one output), or one output
    #                per direction held energized (two outputs)
    #   PULSE        a `pulse_ms` pulse per direction, separate coils
    #   PULSE_TOGGLE one impulse-relay coil (R15/3P-class) behind one or
    #                two outputs: EVERY pulse toggles, so the runtime
    #                pulses only when feedback[0] (the CLOSED contact,
    #                always first) says the apparatus is not already in
    #                the requested state - feedback is mandatory.
    # File keys: "commandStyle"/"pulseMs" (camelCase, like safeState).
    command_style: str = "MAINTAINED"
    pulse_ms: int = 0
    # Internal bits IN/OUT (owner's decision 2026-09-22): the logic's
    # PERMISSION for switching this apparatus ON - the id of an OUT bit
    # (M.<name>) the logic writes. While it is not TRUE the controller
    # REFUSES the close/switch-on command with a reason that names the
    # bit and its description; open/switch-off is never blocked by it,
    # and no logic at all (stopped, before its first scan) means no
    # permission. "" = no permission bit. File key "permissionBit".
    permission_bit: str = ""


@dataclass
class Zone:
    """SPEC_PROJEKT_EPW.md, "Alarmówka": a named group of lines,
    armed/disarmed as a unit (runtime/epw_os/core/intrusion_manager.py's
    own Zone dict - IntrusionManager.add_zone()'s exact three
    parameters, plus id). exit_delay_seconds/entry_delay_seconds are the
    contract's own "czas na wyjście"/"czas na wejście" - real, per-zone
    fields on the runtime side, not a separate global "timings" struct
    (see this module's own docstring)."""

    id: str
    name: str
    exit_delay_seconds: float = 30.0
    entry_delay_seconds: float = 30.0


class LineType:
    """NATYCHMIASTOWA / ZWŁOCZNA / CAŁODOBOWA / DOZOROWA - copied as
    plain string constants (not imported) so this module stays free of
    any runtime/ dependency, same GRANICE every other studio/ module
    already follows; the four values themselves are intrusion_manager.
    LineType._ALL, verbatim."""
    INSTANT = "INSTANT"
    DELAYED = "DELAYED"
    TWENTY_FOUR_HOUR = "24H"
    SUPERVISORY = "SUPERVISORY"
    # NAPADOWA: a hold-up button. Alarms in ANY zone state, like a 24H
    # line, but raises SEC.SYSTEM.PANIC and - unless the installation says
    # otherwise - does NOT start the sounder: the point of a hold-up
    # alarm is that the person standing over you does not learn you
    # pressed it.
    PANIC = "PANIC"
    ALL = (INSTANT, DELAYED, TWENTY_FOUR_HOUR, SUPERVISORY, PANIC)


class LineInputMode:
    """CONTACT (a DI Point + NC/NO) or PARAMETRIZED (an AI Point +
    EOL/DEOL value windows) - intrusion_manager.LineInputMode._ALL."""
    CONTACT = "CONTACT"
    PARAMETRIZED = "PARAMETRIZED"
    ALL = (CONTACT, PARAMETRIZED)


class LineParametrization:
    """EOL (single end-of-line resistor) or DEOL (double) - only
    meaningful when input_mode is PARAMETRIZED.
    intrusion_manager.LineParametrization._ALL."""
    EOL = "EOL"
    DEOL = "DEOL"
    ALL = (EOL, DEOL)


NORMAL_STATE_NC = "NC"
NORMAL_STATE_NO = "NO"


def default_value_windows(parametrization: str) -> dict:
    """Verbatim copy of intrusion_manager.default_value_windows() -
    sensible placeholder [lo, hi] engineering-unit windows per
    classified state, deliberately not tied to a specific resistor
    network (that module's own docstring: "NIE zaszywaj konkretnych
    rezystancji ani pradow"). Kept in sync by hand (no runtime/
    dependency, GRANICE) - the two are cross-referenced in each other's
    docstring so a change to one prompts checking the other."""
    if parametrization == LineParametrization.DEOL:
        return {
            "SHORT": [0.0, 10.0], "VIOLATED": [20.0, 30.0], "SECURE": [45.0, 55.0],
            "TAMPER": [70.0, 80.0], "FAULT_OPEN": [90.0, 100.0],
        }
    return {"VIOLATED": [0.0, 20.0], "SECURE": [45.0, 55.0], "FAULT_OPEN": [90.0, 100.0]}


@dataclass
class Line:
    """SPEC_PROJEKT_EPW.md, "Alarmówka": one supervised input, bound to
    a zone. Field-for-field match to intrusion_manager.add_line()'s own
    parameters (see this module's own docstring for the one real gap:
    `tag` here is a Point.address, not yet a runtime tag name)."""

    id: str
    name: str
    zone_id: str
    tag: str = ""  # a Point.address (DI for CONTACT, AI for PARAMETRIZED)
    normal_state: str = NORMAL_STATE_NC
    line_type: str = LineType.INSTANT
    input_mode: str = LineInputMode.CONTACT
    parametrization: Optional[str] = None  # EOL | DEOL, only when input_mode == PARAMETRIZED
    value_windows: dict = field(default_factory=dict)  # state -> [lo, hi], only when PARAMETRIZED
    min_violation_seconds: float = 0.0       # debounce - 0 = off
    multiplicity_count: int = 1              # violations required - 1 = off ("dwukrotność" = 2)
    multiplicity_window_seconds: float = 10.0  # only consulted when multiplicity_count > 1
    lockout_after_count: int = 0             # auto-lock after N alarms this arm cycle - 0 = off
    alarm_hold_seconds: float = 0.0          # auto-clear alarm after N seconds - 0 = holds until disarm
    silence_threshold_seconds: float = 0.0   # mark SUSPECT if no violation for this long - 0 = off
    # Night (partial) arming: whether THIS line still watches while its
    # zone is armed in NIGHT mode. The usual shape of a night arm is
    # "the perimeter watches, the motion detectors inside do not", so
    # this is a flag per line rather than a second list of lines per
    # zone. Default True: a zone armed at night before anyone configures
    # anything protects exactly as much as a full arm, never less. A 24H
    # line ignores it entirely - it alarms whatever the zone is doing.
    active_at_night: bool = True


class ArmMode:
    """How a zone is armed. FULL watches every line in it; NIGHT watches
    only the lines flagged `active_at_night` (plus, always, the 24H ones)
    - the "dozór nocny / częściowy" of a real alarm panel.
    intrusion_manager.ArmMode._ALL, verbatim."""
    FULL = "FULL"
    NIGHT = "NIGHT"
    ALL = (FULL, NIGHT)


@dataclass
class IntrusionUser:
    """One named person who may operate the alarm system.

    The panel's three ACCESS LEVELS (User/Operator/Engineer) answer "how
    much may whoever is standing here do"; they cannot answer "only
    Kowalski may disarm the warehouse", because two operators are the
    same Operator to them. This record is that answer: a person, the
    level their own code grants, and the zones they may arm and disarm.

    `zones` empty means EVERY zone - the sensible default for a small
    site, and what an installation that never configures this keeps.

    NO PIN LIVES HERE. This record travels in projekt.epw, which goes
    into Studio, into git and over REST; a code that opens a building
    does not belong in any of them. The controller keeps the hashes in
    its own gitignored access file, keyed by this `id` (runtime/epw_os/
    core/access_manager.py) - so a user exists as soon as the project
    lands, and can sign in as soon as someone sets their code ON the
    panel."""

    id: str
    name: str
    level: str = "Operator"
    zones: list[str] = field(default_factory=list)
    # A user who has left: kept in the project (the event register still
    # names them in past entries) but refused at the keypad.
    enabled: bool = True


@dataclass
class Sounder:
    """The alarm system's sounder, as SETTINGS - never as an output.

    EPW-OS deliberately drives no siren itself (owner's decision: "chcę
    móc to swobodnie programować ustawiając bit wewnętrzny alarm i
    pobudzenie danego DO który wyjdzie na syrenę"). What the controller
    owns is the STATE - is the sounder supposed to be sounding right now,
    for how much longer, has somebody silenced it - published as
    SEC.SYSTEM.SIREN_ACTIVE / SIREN_TIME_LEFT / STROBE_ACTIVE. Which physical
    output that reaches, through which interlocks, is a line of logic the
    engineer draws in Logic Studio.

    That split is what makes one siren, two sirens, a siren plus a
    strobe, or a siren wired through a contactor all the same problem -
    a schematic - instead of five options in a config dialog.

    `siren_seconds`: how long the sounder may sound for one alarm. 0
    means until the alarm is cleared or the zone disarmed. Real
    installations are usually bound by local noise regulations here.
    `panic_silent`: whether a PANIC line keeps the sounder quiet."""

    siren_seconds: float = 180.0
    panic_silent: bool = True


@dataclass
class PowerSupervision:
    """SPEC_PROJEKT_EPW.md, "Alarmówka" (system-wide, not per-zone/line)
    - intrusion_manager.py's own single mains/battery config
    (get_intrusion_power_supervision()/configure_power_supervision()).
    `None` tag means "not supervised" - intrusion_manager.py's own rule,
    "brak konfiguracji oznacza brak nadzoru, bez błędów"."""

    mains_tag: Optional[str] = None
    mains_ok_state: bool = True
    battery_tag: Optional[str] = None
    battery_ok_state: bool = True


ELECTRICAL_PROTECTION_ACTIONS = ("Disabled", "Information", "Warning", "Trip", "Custom Logic")


@dataclass
class ElectricalProtectionStage:
    """SPEC_PROJEKT_EPW.md, "Nastawy zabezpieczeń" (electrical side) -
    see this module's own docstring for why the CATALOG (which function/
    stage ids exist at all) is fixed, hand-copied from protection_
    manager.py's init_defaults() as project_panels.
    ELECTRICAL_PROTECTION_CATALOG - only VALUES live here, per stage."""

    function_id: str   # e.g. "50 Instantaneous Overcurrent" - catalog key
    stage_name: str     # e.g. "Stage 1" - catalog key, together with function_id
    enabled: bool = True
    setting: float = 0.0
    hysteresis: float = 0.0
    delay_ms: int = 0
    action: str = "Trip"  # one of ELECTRICAL_PROTECTION_ACTIONS


@dataclass
class ProcessProtection:
    """SPEC_PROJEKT_EPW.md, "Nastawy zabezpieczeń" (process side) -
    field-for-field match to process_protection_manager.py's own
    add_protection()/update_protection() parameters."""

    id: str
    name: str
    analog_tag: str = ""  # a Point.address (see this module's own docstring)
    upper_threshold: float = 100.0
    lower_threshold: float = 0.0
    hysteresis: float = 0.0
    delay_seconds: float = 0.0
    enabled: bool = True


@dataclass
class ModbusBusConfig:
    """The single serial/TCP bus the controller (Orange Pi) uses to
    reach every ELA/ADA/EPM module - one bus, many unit ids (Card.
    modbus_unit_id above addresses individual modules on it). GREENFIELD
    (see Card.modbus_unit_id's own docstring) - `transport` picks which
    of the two address shapes below apply, matching how Modbus RTU vs
    TCP are actually configured (a serial port has no IP, a TCP gateway
    has no baud rate)."""

    transport: str = "RTU"  # "RTU" (serial) | "TCP"
    port: str = ""          # RTU: "/dev/ttyUSB0" or "COM3"
    baud_rate: int = 9600   # RTU only
    parity: str = "N"       # RTU only - "N" | "E" | "O"
    data_bits: int = 8      # RTU only
    stop_bits: int = 1      # RTU only
    host: str = ""          # TCP only - the Modbus TCP gateway's address
    tcp_port: int = 502     # TCP only


@dataclass
class MqttConfig:
    """The controller's MQTT integration (HAOS) - a SETTING of the
    project (decided 2026-09-18, ZADANIA p. 6 "Ustawienia sterownika
    spoza formatu"): the broker and topics belong to the installation
    and travel with the project to a replacement controller; the panel
    may change them (Engineer, audited) and Studio sees the difference.
    Never the broker password - runtime keeps that in its own local,
    gitignored file, the same rule as access.local.json. Field names are
    exactly runtime's get_mqtt_config() keys so both sides read one
    shape. `link_in`: [{"topic", "tag", "type", "stale_after_s"}] -
    incoming mappings, remote topic -> local Link.* tag."""

    enabled: bool = False
    host: str = ""
    port: int = 1883
    username: str = ""
    tls: bool = False
    client_id: str = ""
    topic_prefix: str = ""
    publish_interval_s: float = 2.0
    default_deadband: float = 0.0
    deadband_per_tag: Dict[str, float] = field(default_factory=dict)
    queue_max: int = 1000
    link_in: list = field(default_factory=list)


@dataclass
class Project:
    """The whole of `projekt.epw`'s in-memory representation - only the
    fields this module currently implements (see module docstring for
    what's deliberately still missing and why)."""

    metadata: ProjectMetadata
    modules: list[str] = field(default_factory=list)
    cards: list[Card] = field(default_factory=list)
    locations: list[Location] = field(default_factory=list)
    points: list[Point] = field(default_factory=list)
    devices: list[Device] = field(default_factory=list)
    zones: list[Zone] = field(default_factory=list)
    lines: list[Line] = field(default_factory=list)
    intrusion_users: list[IntrusionUser] = field(default_factory=list)
    power_supervision: PowerSupervision = field(default_factory=PowerSupervision)
    sounder: Sounder = field(default_factory=Sounder)
    electrical_protection_stages: list[ElectricalProtectionStage] = field(default_factory=list)
    process_protections: list[ProcessProtection] = field(default_factory=list)
    modbus_bus: ModbusBusConfig = field(default_factory=ModbusBusConfig)
    mqtt: MqttConfig = field(default_factory=MqttConfig)
    # Service notes - the per-device maintenance logbook written on the
    # panel (runtime's ServiceNoteManager): {device tag: [{"text",
    # "timestamp", "author_level"}]}, append-only there. In the project
    # since 2026-09-18 so the installation's history travels with it and
    # Studio can read it; treated as a setting (each panel entry comes
    # back as revision +1 by "panel"; Studio takes it like any other).
    service_notes: dict = field(default_factory=dict)
    # The two editors' documents, embedded whole - see the module
    # docstring. {} = nothing drawn / no logic yet (a fresh project).
    screens: dict = field(default_factory=dict)
    logic: dict = field(default_factory=dict)
    logic_runtime: dict = field(default_factory=dict)
    # SPEC_PROJEKT_EPW.md, "Wersjonowanie": incremented on every save,
    # by Studio or (once that connection exists) by runtime - kept from
    # day one even though the "reject an older revision on upload"
    # CHECK is a later, controller-connection-dependent step (the
    # contract's own "Kolejność wdrożenia" puts it after this one) -
    # doing so avoids a schema migration once that check lands.
    revision: int = 0
    modified_by: str = "studio"
    is_dirty: bool = False

    def touch(self):
        """Marks the project as having unsaved changes - called by
        whatever UI mutates it (see main_window.py's project-aspect
        panels, once those exist). Does NOT bump `revision` - that only
        happens on an actual save (save_project() below), matching the
        contract's own "revision, rosnąca przy KAŻDYM zapisie" (at
        every SAVE, not at every edit)."""
        self.is_dirty = True


def new_project(name: str, author: str = "") -> Project:
    """SPEC_PROJEKT_EPW.md's own "Kolejność wdrożenia" step 1 -
    "zakładanie [...] projektu". A brand new project starts dirty (an
    unsaved new project IS unsaved work, same as any editor's own "new
    document" - StudioMainWindow's close handler must not treat it as
    nothing-to-lose)."""
    project = Project(metadata=ProjectMetadata(name=name, author=author))
    project.is_dirty = True
    return project


def _to_json_dict(project: Project) -> dict:
    data = {
        "format": FORMAT_MARKER,
        "schema_version": SCHEMA_VERSION,
        "project": asdict(project.metadata),
        "revision": project.revision,
        "modified_by": project.modified_by,
        # SPEC "Wersjonowanie": "settings_hash - suma kontrolna samych
        # nastaw" - recomputed at every save from settings_snapshot().
        "settings_hash": settings_hash(project),
    }
    # Every structural collection is OMITTED when empty (module
    # docstring: "czytnik ma to znieść bez błędu", applied to JSON keys)
    # - a bare project (just metadata) is a fully valid, minimal file.
    if project.modules:
        data["modules"] = list(project.modules)
    if project.cards:
        data["cards"] = [asdict(c) for c in project.cards]
    if project.locations:
        data["locations"] = [asdict(l) for l in project.locations]
    if project.points:
        data["points"] = [asdict(p) for p in project.points]
    if project.devices:
        data["devices"] = [
            {
                "id": d.id,
                "behavior": d.behavior,
                "kind": d.kind,
                "feedback": list(d.feedback),
                "command": list(d.command),
                "supervision": dict(d.supervision),
                "safeState": dict(d.safe_state),  # contract's own field name, camelCase
                "commandStyle": d.command_style,
                "pulseMs": d.pulse_ms,
                "permissionBit": d.permission_bit,
            }
            for d in project.devices
        ]
    # SPEC_PROJEKT_EPW.md, "Alarmówka" - nested under one "intrusion" key
    # (the contract's own section name), omitted entirely when the
    # module isn't in this project's composition at all (empty zones AND
    # lines AND an unconfigured power_supervision - the same "absent
    # section = module not present" reading modules/cards/etc. already
    # use, just checked across three fields instead of one list).
    ps = project.power_supervision
    power_configured = ps.mains_tag is not None or ps.battery_tag is not None
    sounder_configured = (project.sounder.siren_seconds != Sounder.siren_seconds
                          or project.sounder.panic_silent != Sounder.panic_silent)
    if (project.zones or project.lines or project.intrusion_users or power_configured
            or sounder_configured):
        intrusion = {}
        if project.zones:
            intrusion["zones"] = [asdict(z) for z in project.zones]
        if project.lines:
            intrusion["lines"] = [asdict(l) for l in project.lines]
        if project.intrusion_users:
            intrusion["users"] = [asdict(u) for u in project.intrusion_users]
        if power_configured:
            intrusion["power_supervision"] = asdict(ps)
        if sounder_configured:
            intrusion["sounder"] = asdict(project.sounder)
        data["intrusion"] = intrusion
    # SPEC_PROJEKT_EPW.md, "Nastawy zabezpieczeń" - nested under
    # "protection", same "absent = module not present" reading.
    if project.electrical_protection_stages or project.process_protections:
        protection = {}
        if project.electrical_protection_stages:
            protection["electrical"] = [asdict(s) for s in project.electrical_protection_stages]
        if project.process_protections:
            protection["process"] = [asdict(p) for p in project.process_protections]
        data["protection"] = protection
    # Modbus bus - task "adresowanie ELA/ADA/EPM" - omitted when the
    # bus is still at its all-defaults, untouched state (no port/host
    # ever set) - same "absent = not configured" reading as everything
    # else in this function.
    bus = project.modbus_bus
    if bus.port or bus.host:
        data["modbus_bus"] = asdict(bus)
    # MQTT and service notes (settings, 2026-09-18) - same "absent =
    # untouched / nothing written" reading.
    if project.mqtt != MqttConfig():
        data["mqtt"] = asdict(project.mqtt)
    if project.service_notes:
        data["service_notes"] = project.service_notes      # kept verbatim, like the editors' documents
    # Embedded editor documents - same "omitted when empty" reading.
    if project.screens:
        data["screens"] = project.screens
    if project.logic:
        data["logic"] = project.logic
    if project.logic_runtime:
        data["logic_runtime"] = project.logic_runtime
    return data


def save_project(project: Project, path, modified_by: str = "studio") -> None:
    """Writes `project` to `path` as projekt.epw (gzip+JSON - see
    module docstring). Bumps `revision` and `modified_at`/`modified_by`
    and clears `is_dirty` - the same "a save is what actually commits a
    revision" rule new_project()/touch() above already document.

    `modified_by` is SPEC_PROJEKT_EPW.md's own header field: "studio"
    when Studio saves, "panel" when runtime writes a changed setting
    back (task "runtime czyta projekt.epw", etap 4).

    Task point 8.2 - "Kopia zapasowa przy zapisie - poprzednia wersja
    jako projekt.epw.bak, jedna generacja wstecz." Whatever is on disk
    at `path` BEFORE this write (the previous save's own output) is
    copied to `path` + ".bak" first - each save overwrites that one
    backup file rather than accumulating a history, which is exactly
    "jedna generacja wstecz", not a version history. A missing source
    file (first-ever save to this path) or a copy failure (e.g. a
    read-only backup left over from something else) is never allowed to
    block the actual save - the backup is a nicety layered on top of
    the real operation, not a precondition for it.

    The new content goes to a temporary file in the same directory and
    replaces `path` in one os.replace() - on the controller this file is
    written by the panel while the device runs, and a power cut halfway
    through a plain in-place write would leave a truncated project the
    next start refuses to read."""
    path = Path(path)
    if path.exists():
        try:
            shutil.copy2(path, str(path) + ".bak")
        except OSError:
            pass
    project.revision += 1
    project.metadata.modified_at = _utc_now_iso()
    project.modified_by = modified_by
    data = _to_json_dict(project)
    payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as f:
                f.write(payload)
            raw.flush()
            os.fsync(raw.fileno())
        # mkstemp creates the file private (0600 on POSIX); keep whatever
        # access the project file already had, or ordinary 0644 for a new one.
        try:
            os.chmod(tmp_name, path.stat().st_mode if path.exists() else 0o644)
        except OSError:
            pass
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    project.is_dirty = False


# --- Reading: refusals and warnings ---------------------------------------
#
# Task "runtime czyta projekt.epw", point 1.2 - the same validation stance
# runtime's epwsyn_loader.py takes for .epwsyn files:
#   - not a project file / unreadable / not JSON  -> refusal
#   - schema_version newer than SCHEMA_VERSION    -> refusal
#   - a required field missing                    -> refusal, naming the field
#   - a field of the wrong type                   -> warning, naming the field
#     (optional field: default used; required field: that record skipped;
#     whole collection of the wrong type: treated as empty)
#   - an unknown field                            -> warning, ignored
# A damaged file must never raise out of read_project() - runtime reads it
# while starting a controller, and a crash there is a controller that does
# not come up at all.
#
# "Required" is not a second list kept by hand: it is every dataclass field
# above WITHOUT a default (Card.id/model/kind/channels, Point.address, ...),
# and the expected type of every field is its own annotation - adding a
# field to a dataclass updates the reader with it.

# English text of every issue key - what str() of an issue shows, and the
# fallback a program uses for a key its own translation file lacks. Each
# program translates `project_format.<key>` through its own tr().
ISSUE_TEXT_EN = {
    "unreadable": "Cannot read the project file: {detail}",
    "not_json": "The file is not a valid EPW project file: {detail}",
    "not_object": "The project file does not contain a JSON object.",
    "wrong_format": "The file is not an EPW project (missing or wrong 'format' marker).",
    "missing_field": "Required field {field} is missing.",
    "invalid_required": "Required field {field} has an invalid value (expected {expected}, got {actual}).",
    "newer_schema": "The file uses format version {version}, newer than the supported version {supported}. "
                    "Update the program to open it.",
    "wrong_type_default": "Field {field} has the wrong type (expected {expected}, got {actual}) - "
                          "the default value is used.",
    "wrong_type_skipped": "Field {field} has the wrong type (expected {expected}, got {actual}) - "
                          "the record is skipped.",
    "wrong_type_empty": "Field {field} has the wrong type (expected {expected}, got {actual}) - "
                        "treated as empty.",
    "record_not_object": "Entry {field} is not an object - skipped.",
    "unknown_field": "Unknown field {field} - ignored.",
    "duplicate_id": "{field} repeats the identifier '{value}' - only the first occurrence is kept.",
}


def format_issue(key: str, params: dict) -> str:
    template = ISSUE_TEXT_EN.get(key, key)
    try:
        return template.format(**params)
    except (KeyError, IndexError, ValueError):
        return template


class ProjectFormatError(Exception):
    """A refusal: read_project() gives up on the file. `key` names the
    rule (see ISSUE_TEXT_EN), `params` the details a translated message
    needs (`field`, `version`, ...). str() is the English text."""

    def __init__(self, key: str, **params):
        self.key = key
        self.params = params
        super().__init__(format_issue(key, params))


@dataclass(frozen=True)
class FormatIssue:
    """A warning: the file still loads. Same `key`/`params` shape as
    ProjectFormatError."""

    key: str
    params: dict

    def __str__(self) -> str:
        return format_issue(self.key, self.params)


@dataclass
class ProjectReadResult:
    """What read_project() returns. `ok=False`: `error` says why and
    `project` is None. `ok=True`: `project` is loaded and `warnings`
    lists everything that had to be skipped or defaulted on the way."""

    ok: bool
    project: Optional[Project] = None
    error: Optional[ProjectFormatError] = None
    warnings: list = field(default_factory=list)


def _type_name(annotation) -> str:
    origin = typing.get_origin(annotation)
    if origin in (typing.Union, types.UnionType):
        return " or ".join(_type_name(a) for a in typing.get_args(annotation))
    if annotation is type(None):
        return "null"
    if origin is not None:
        return getattr(origin, "__name__", str(origin))
    return getattr(annotation, "__name__", str(annotation))


def _json_type_name(value) -> str:
    if value is None:
        return "null"
    return type(value).__name__


def _coerce(value, annotation):
    """(True, value) when `value` fits `annotation`, else (False, None).
    bool is never accepted where a number is expected (JSON true is not
    a channel count); an int is accepted where a float is expected."""
    origin = typing.get_origin(annotation)
    if origin in (typing.Union, types.UnionType):
        for arg in typing.get_args(annotation):
            if arg is type(None):
                if value is None:
                    return True, None
                continue
            ok, coerced = _coerce(value, arg)
            if ok:
                return True, coerced
        return False, None
    if annotation is bool:
        return (True, value) if isinstance(value, bool) else (False, None)
    if annotation is int:
        return (True, value) if isinstance(value, int) and not isinstance(value, bool) else (False, None)
    if annotation is float:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return True, float(value)
        return False, None
    if annotation is str:
        return (True, value) if isinstance(value, str) else (False, None)
    if annotation is list or origin is list:
        if not isinstance(value, list):
            return False, None
        args = typing.get_args(annotation)
        if args and args[0] is str and not all(isinstance(v, str) for v in value):
            return False, None
        return True, list(value)
    if annotation is dict or origin is dict:
        return (True, dict(value)) if isinstance(value, dict) else (False, None)
    return True, value


def _build(cls, raw, where: str, warnings: list, json_names=None, skippable: bool = True):
    """One dataclass instance from one JSON object, or None when the
    record had to be skipped. `json_names` maps a field name to the key
    the file uses for it when they differ (Device.safe_state is
    "safeState" in the file). Raises ProjectFormatError for a missing
    required field - and, when `skippable` is False (the header), for a
    required field of the wrong type too, since there is no "skip the
    header" to fall back on."""
    if not isinstance(raw, dict):
        warnings.append(FormatIssue("record_not_object", {"field": where}))
        return None
    json_names = json_names or {}
    hints = typing.get_type_hints(cls)
    kwargs = {}
    known_keys = set()
    for f in fields(cls):
        key = json_names.get(f.name, f.name)
        known_keys.add(key)
        required = f.default is MISSING and f.default_factory is MISSING
        name = f"{where}.{key}"
        if key not in raw:
            if required:
                raise ProjectFormatError("missing_field", field=name)
            continue
        ok, value = _coerce(raw[key], hints[f.name])
        if not ok:
            details = {"field": name, "expected": _type_name(hints[f.name]), "actual": _json_type_name(raw[key])}
            if required and not skippable:
                raise ProjectFormatError("invalid_required", **details)
            if required:
                warnings.append(FormatIssue("wrong_type_skipped", details))
                return None
            warnings.append(FormatIssue("wrong_type_default", details))
            continue
        kwargs[f.name] = value
    for key in raw:
        if key not in known_keys:
            warnings.append(FormatIssue("unknown_field", {"field": f"{where}.{key}"}))
    return cls(**kwargs)


def _section(data: dict, key: str, where: str, expected, warnings: list):
    """data[key] when it has the expected container type; an absent key
    is simply empty (the format omits empty collections); a present key
    of the wrong type is a warning and empty."""
    if key not in data:
        return expected()
    value = data[key]
    if isinstance(value, expected):
        return value
    warnings.append(FormatIssue("wrong_type_empty", {
        "field": where, "expected": expected.__name__, "actual": _json_type_name(value)}))
    return expected()


def _records(data: dict, key: str, where: str, cls, warnings: list, id_field=None, json_names=None) -> list:
    result = []
    seen = set()
    for index, raw in enumerate(_section(data, key, where, list, warnings)):
        record = _build(cls, raw, f"{where}[{index}]", warnings, json_names=json_names)
        if record is None:
            continue
        if id_field is not None:
            identity = getattr(record, id_field)
            if identity in seen:
                warnings.append(FormatIssue("duplicate_id", {"field": f"{where}[{index}].{id_field}",
                                                              "value": identity}))
                continue
            seen.add(identity)
        result.append(record)
    return result


_TOP_LEVEL_KEYS = {
    "format", "schema_version", "project", "revision", "modified_by", "settings_hash", "modules", "cards",
    "locations", "points", "devices", "intrusion", "protection", "modbus_bus", "mqtt", "service_notes",
    "screens", "logic", "logic_runtime",
}


def _migrate_schema_v1_cards(data: dict, warnings: list) -> None:
    """schema_version 1 stored one channel kind per Card row ("kind":
    "DI", "channels": 32); schema_version 2 replaced that with
    channel_kinds ({"DI": 32}), one row per physical module (see Card's
    own docstring for why). Rewrites data["cards"] in place, raw dict to
    raw dict, before _records()/_build() ever see it - _build() only
    knows "does this key exist for the CURRENT dataclass shape", it has
    no notion of an older version's different key meaning, so the
    translation has to happen here, once, up front.

    channel_kinds has no default-required tension the way "channels"
    did in schema 1 (it defaults to {}, a legitimate "not configured
    yet" card - see Card's own docstring), so _build() has no hook left
    to catch a v1 record that declared a "kind" without a usable
    "channels" the way it would once have caught a plain missing/wrong-
    typed required field. Handled here instead, in the SAME spirit as
    every other skippable-record wrong-type problem this reader already
    reports: a warning naming the field, and the record dropped - Card
    records have always been skippable (_records()'s own id_field="id"
    call below never passes skippable=False), so this doesn't create a
    new failure mode, only keeps an old one working the same way through
    the migration."""
    cards = data.get("cards")
    if not isinstance(cards, list):
        return
    migrated = []
    for index, raw in enumerate(cards):
        if not isinstance(raw, dict) or "channel_kinds" in raw or "kind" not in raw:
            migrated.append(raw)
            continue
        kind = raw.pop("kind")
        channels = raw.pop("channels", None)
        if isinstance(kind, str) and isinstance(channels, int) and not isinstance(channels, bool):
            raw["channel_kinds"] = {kind: channels}
            migrated.append(raw)
        else:
            warnings.append(FormatIssue("wrong_type_skipped", {
                "field": f"cards[{index}].channels", "expected": "int", "actual": _json_type_name(channels),
            }))
    data["cards"] = migrated


def _parse(path) -> tuple:
    path = Path(path)
    try:
        with gzip.open(path, "rb") as f:
            payload = f.read()
    except (OSError, EOFError, zlib.error) as e:
        raise ProjectFormatError("unreadable", detail=str(e)) from e

    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        raise ProjectFormatError("not_json", detail=str(e)) from e

    if not isinstance(data, dict):
        raise ProjectFormatError("not_object")
    if data.get("format") != FORMAT_MARKER:
        raise ProjectFormatError("wrong_format")
    if "schema_version" not in data:
        raise ProjectFormatError("missing_field", field="schema_version")
    schema_version = data["schema_version"]
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        raise ProjectFormatError("invalid_required", field="schema_version", expected="int",
                                 actual=_json_type_name(schema_version))
    if schema_version > SCHEMA_VERSION:
        raise ProjectFormatError("newer_schema", version=schema_version, supported=SCHEMA_VERSION)
    warnings = []
    if schema_version < 2:
        _migrate_schema_v1_cards(data, warnings)

    if "project" not in data:
        raise ProjectFormatError("missing_field", field="project")
    if not isinstance(data["project"], dict):
        raise ProjectFormatError("invalid_required", field="project", expected="object",
                                 actual=_json_type_name(data["project"]))

    metadata = _build(ProjectMetadata, data["project"], "project", warnings, skippable=False)

    modules = []
    for index, name in enumerate(_section(data, "modules", "modules", list, warnings)):
        if isinstance(name, str):
            if name not in modules:
                modules.append(name)
        else:
            warnings.append(FormatIssue("wrong_type_skipped", {
                "field": f"modules[{index}]", "expected": "str", "actual": _json_type_name(name)}))

    project = Project(
        metadata=metadata,
        modules=modules,
        cards=_records(data, "cards", "cards", Card, warnings, id_field="id"),
        locations=_records(data, "locations", "locations", Location, warnings, id_field="code"),
        points=_records(data, "points", "points", Point, warnings, id_field="address"),
        devices=_records(data, "devices", "devices", Device, warnings, id_field="id",
                         json_names={"safe_state": "safeState", "command_style": "commandStyle",
                                     "pulse_ms": "pulseMs", "permission_bit": "permissionBit"}),
    )

    intrusion = _section(data, "intrusion", "intrusion", dict, warnings)
    project.zones = _records(intrusion, "zones", "intrusion.zones", Zone, warnings, id_field="id")
    project.lines = _records(intrusion, "lines", "intrusion.lines", Line, warnings, id_field="id")
    project.intrusion_users = _records(intrusion, "users", "intrusion.users", IntrusionUser, warnings,
                                       id_field="id")
    if "sounder" in intrusion:
        sounder = _build(Sounder, intrusion["sounder"], "intrusion.sounder", warnings)
        if sounder is not None:
            project.sounder = sounder
    if "power_supervision" in intrusion:
        supervision = _build(PowerSupervision, intrusion["power_supervision"], "intrusion.power_supervision",
                             warnings)
        if supervision is not None:
            project.power_supervision = supervision
    for key in intrusion:
        if key not in ("zones", "lines", "users", "sounder", "power_supervision"):
            warnings.append(FormatIssue("unknown_field", {"field": f"intrusion.{key}"}))

    protection = _section(data, "protection", "protection", dict, warnings)
    project.electrical_protection_stages = _records(
        protection, "electrical", "protection.electrical", ElectricalProtectionStage, warnings)
    project.process_protections = _records(
        protection, "process", "protection.process", ProcessProtection, warnings, id_field="id")
    for key in protection:
        if key not in ("electrical", "process"):
            warnings.append(FormatIssue("unknown_field", {"field": f"protection.{key}"}))

    if "modbus_bus" in data:
        bus = _build(ModbusBusConfig, data["modbus_bus"], "modbus_bus", warnings)
        if bus is not None:
            project.modbus_bus = bus
    if "mqtt" in data:
        mqtt = _build(MqttConfig, data["mqtt"], "mqtt", warnings)
        if mqtt is not None:
            project.mqtt = mqtt
    # Service notes: kept verbatim (only the container type is checked) -
    # runtime's ServiceNoteManager validates each entry when it loads them.
    project.service_notes = dict(_section(data, "service_notes", "service_notes", dict, warnings))

    # Embedded editor documents: kept verbatim, only their container type
    # is checked here (a non-object is a warning and empty, like any other
    # section) - each editor validates its own document on load.
    project.screens = _section(data, "screens", "screens", dict, warnings)
    project.logic = _section(data, "logic", "logic", dict, warnings)
    project.logic_runtime = _section(data, "logic_runtime", "logic_runtime", dict, warnings)

    revision = data.get("revision", 0)
    if isinstance(revision, int) and not isinstance(revision, bool):
        project.revision = revision
    else:
        warnings.append(FormatIssue("wrong_type_default", {
            "field": "revision", "expected": "int", "actual": _json_type_name(revision)}))
    modified_by = data.get("modified_by", "studio")
    if isinstance(modified_by, str):
        project.modified_by = modified_by
    else:
        warnings.append(FormatIssue("wrong_type_default", {
            "field": "modified_by", "expected": "str", "actual": _json_type_name(modified_by)}))

    for key in data:
        if key not in _TOP_LEVEL_KEYS:
            warnings.append(FormatIssue("unknown_field", {"field": key}))

    project.is_dirty = False
    return project, warnings


def read_project(path) -> ProjectReadResult:
    """Reads `projekt.epw` without ever raising - the entry point for
    runtime, which reads the file while a controller starts. Refusals
    come back as ok=False with `error`; everything that could be read
    around comes back as `warnings` (see the rules above)."""
    try:
        project, warnings = _parse(path)
    except ProjectFormatError as e:
        return ProjectReadResult(ok=False, error=e)
    except Exception as e:  # a reader bug must not take the caller down with it
        return ProjectReadResult(ok=False, error=ProjectFormatError("unreadable", detail=f"{type(e).__name__}: {e}"))
    return ProjectReadResult(ok=True, project=project, warnings=warnings)


def load_project(path) -> Project:
    """Reads `projekt.epw` from `path`, raising ProjectFormatError for a
    refusal - Studio's entry point (its Open dialog shows the message).
    Same rules as read_project(); warnings are not reported here."""
    result = read_project(path)
    if not result.ok:
        raise result.error
    return result.project


# --- settings: what the panel may change (SPEC "Nastawa") ------------------------
#
# The same field lists runtime/epw_os/core/project_epw.py uses to tell a
# setting from structure (a test keeps the two in step). settings_snapshot()
# flattens exactly those values into {path: value}; settings_hash() is the
# header's "suma kontrolna samych nastaw"; settings_diff() is what Studio
# shows before overwriting a controller whose file moved on without it
# (SPEC "Wersjonowanie": "pokazać, co się rozjechało (tu 25 A, tam 40 A)").

SETTING_FIELDS = {
    "zones": ("exit_delay_seconds", "entry_delay_seconds"),
    "lines": ("min_violation_seconds", "multiplicity_count", "multiplicity_window_seconds",
              "lockout_after_count", "alarm_hold_seconds", "silence_threshold_seconds", "value_windows"),
    "process_protections": ("upper_threshold", "lower_threshold", "hysteresis", "delay_seconds", "enabled"),
    "electrical_protection_stages": ("enabled", "setting", "hysteresis", "delay_ms", "action"),
    "analog_points": ("signal_type", "raw_min", "raw_max", "eng_min", "eng_max", "unit", "decimals"),
    "switching_counters": ("warning_threshold",),
    "power_supervision": ("mains_tag", "mains_ok_state", "battery_tag", "battery_ok_state"),
    # The sounder (one record, "system"): how long the siren may sound and
    # whether a hold-up line sounds at all are nastawy of the same kind as
    # a line's alarm_hold_seconds. Which OUTPUT the siren hangs on is
    # nowhere in the project - see Sounder's own docstring.
    "sounder": ("siren_seconds", "panic_silent"),
    # 2026-09-18: MQTT (one record, "broker") and the service notes (one
    # record per device tag, its whole list) are settings - the panel
    # writes them, Studio diffs and takes them.
    "mqtt": ("enabled", "host", "port", "username", "tls", "client_id", "topic_prefix", "publish_interval_s",
             "default_deadband", "deadband_per_tag", "queue_max", "link_in"),
    "service_notes": ("notes",),
}


def _setting_value(value):
    """JSON-safe copy; None stays None so "not set" and "set to 0" differ."""
    if isinstance(value, (list, tuple)):
        return [_setting_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _setting_value(v) for k, v in value.items()}
    return value


def settings_snapshot(project: Project) -> dict:
    """{"<section>/<record id>/<field>": value} for every setting of the
    project, in a stable order. Records are keyed by their own identity
    (zone/line/protection id, "function / stage" for an electrical stage,
    the point address for an analog point), so two files of the same
    installation line up field by field."""
    out = {}

    def record(section, key, obj):
        for name in SETTING_FIELDS[section]:
            out[f"{section}/{key}/{name}"] = _setting_value(getattr(obj, name, None))

    for zone in project.zones:
        record("zones", zone.id, zone)
    for line in project.lines:
        record("lines", line.id, line)
    for protection in project.process_protections:
        record("process_protections", protection.id, protection)
    for stage in project.electrical_protection_stages:
        record("electrical_protection_stages", f"{stage.function_id} / {stage.stage_name}", stage)
    for point in project.points:
        kind = point.address.split(".")[1:2]
        if kind == ["AI"]:
            record("analog_points", point.address, point)
        elif kind == ["DI"]:
            record("switching_counters", point.address, point)
    supervision = project.power_supervision
    if getattr(supervision, "mains_tag", None) is not None or getattr(supervision, "battery_tag", None) is not None:
        record("power_supervision", "system", supervision)
    record("sounder", "system", project.sounder)
    record("mqtt", "broker", project.mqtt)
    for tag, notes in sorted(project.service_notes.items()):
        out[f"service_notes/{tag}/notes"] = _setting_value(notes)
    return dict(sorted(out.items()))


def settings_hash(project: Project) -> str:
    """SHA-256 (hex) of the canonical JSON of settings_snapshot()."""
    import hashlib
    canonical = json.dumps(settings_snapshot(project), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def settings_diff(mine: dict, theirs: dict) -> list:
    """[(path, my value, their value)] for every setting the two
    snapshots disagree on - a setting only one side has counts too
    (the other side reports None). Sorted by path."""
    paths = sorted(set(mine) | set(theirs))
    return [(path, mine.get(path), theirs.get(path)) for path in paths
            if mine.get(path) != theirs.get(path) or (path in mine) != (path in theirs)]


def apply_settings_snapshot(project: Project, values: dict) -> list:
    """The reverse of settings_snapshot(): writes {path: value} entries
    into the project's own records (SPEC "Studio łączy się ze sterownikiem
    [...] podgląd nastaw na żywo": what Studio applies when the operator
    takes the controller's values). Only paths of SETTING_FIELDS on records
    the project has are written; anything else is ignored. Returns the
    paths applied, sorted."""
    zones = {z.id: z for z in project.zones}
    lines = {l.id: l for l in project.lines}
    processes = {p.id: p for p in project.process_protections}
    stages = {f"{s.function_id} / {s.stage_name}": s for s in project.electrical_protection_stages}
    points = {p.address: p for p in project.points}
    targets = {
        "zones": zones, "lines": lines, "process_protections": processes,
        "electrical_protection_stages": stages, "analog_points": points, "switching_counters": points,
        "power_supervision": {"system": project.power_supervision}, "mqtt": {"broker": project.mqtt},
        "sounder": {"system": project.sounder},
    }
    applied = []
    for path, value in values.items():
        section, _, rest = str(path).partition("/")
        key, _, name = rest.rpartition("/")
        fields = SETTING_FIELDS.get(section)
        if not fields or name not in fields:
            continue
        if section == "service_notes":
            # The device's whole logbook: a list replaces it, None/[] removes it.
            if value:
                if not isinstance(value, list) or not all(isinstance(n, dict) for n in value):
                    continue
                project.service_notes[key] = [dict(n) for n in value]
            else:
                project.service_notes.pop(key, None)
            applied.append(path)
            continue
        record = targets.get(section, {}).get(key)
        if record is None:
            continue
        setattr(record, name, _setting_value(value))
        applied.append(path)
    if applied:
        project.touch()
    return sorted(applied)
