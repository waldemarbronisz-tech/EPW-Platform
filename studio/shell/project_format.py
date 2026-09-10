"""The `projekt.epw` file format - shared/docs/SPEC_PROJEKT_EPW.md is the
authoritative contract this module implements. Read that document before
changing anything here; this module's own docstrings quote it rather than
restate it from memory, so the two don't quietly drift apart.

Scope of THIS module, deliberately: the "structural" fields the contract
itself groups under Studio's exclusive editing layer (Nagłówek, Skład
urządzenia, Sprzęt, Punkty, Aparaty, Alarmówka, Nastawy zabezpieczeń) -
not yet `screens`/`logic` (embedding the Synoptic/Logic Studio editors'
own content into this file is a separate, much larger integration -
SynopticPanel/LogicPanel keep their own .epwsyn/.epwlogic save flow
entirely unchanged until that lands, so nothing about how Ekrany/Logika
save today is touched by this module).

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
the runtime side, named identically, so a future "Migracja adresacji"-
style wiring step has a field-for-field match to work from rather than
a second design pass. The one field intrusion_manager.py's own contract
DOESN'T have a Studio equivalent for yet: its `tag` is a flat
TagManager name ("DI5", "ELA01.DI05") - a DIFFERENT address grammar
from this module's own card-relative Point.address ("ELA1.DI.5"), the
same unresolved gap project_panels.py's own module docstring already
flags for Logic Studio. Line.tag below stores a Point.address (Studio's
own consistent address space) - translating that to a real runtime tag
name is deferred with everything else in that gap, not solved here.

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
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

FORMAT_MARKER = "EPW_PROJECT_FILE"
SCHEMA_VERSION = 1


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
    model, rodzaj kanałów, liczba kanałów`. Example from the contract:
    id="DI1", model="ELA01", kind="DI", channels=32.

    `modbus_unit_id` (task: "ELA i ADA i EPM będą łączyły się z orange
    pi [...] po modbus - trzeba dać opcję adresowania") is GREENFIELD -
    unlike Zone/Line/ElectricalProtectionStage, no ModbusDriver exists
    in runtime yet to mirror field-for-field (confirmed: runtime/epw_os/
    core/comm_diagnostics.py's own docstring describes itself as built
    FOR a still-nonexistent future ModbusDriver). This is a standard
    Modbus unit/slave address (1-247, RTU/TCP alike) - `None` means
    "not addressed yet", same "absent = not configured" convention
    every other optional field in this module already uses."""

    id: str
    model: str
    kind: str
    channels: int
    modbus_unit_id: Optional[int] = None


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
    always-present-but-empty."""

    address: str
    description: str = ""
    location: str = ""
    technical_note: str = ""
    signal_type: Optional[str] = None
    raw_min: Optional[float] = None
    raw_max: Optional[float] = None
    eng_min: Optional[float] = None
    eng_max: Optional[float] = None
    unit: Optional[str] = None
    decimals: Optional[int] = None


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
    ALL = (INSTANT, DELAYED, TWENTY_FOUR_HOUR, SUPERVISORY)


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
    power_supervision: PowerSupervision = field(default_factory=PowerSupervision)
    electrical_protection_stages: list[ElectricalProtectionStage] = field(default_factory=list)
    process_protections: list[ProcessProtection] = field(default_factory=list)
    modbus_bus: ModbusBusConfig = field(default_factory=ModbusBusConfig)
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
    if project.zones or project.lines or power_configured:
        intrusion = {}
        if project.zones:
            intrusion["zones"] = [asdict(z) for z in project.zones]
        if project.lines:
            intrusion["lines"] = [asdict(l) for l in project.lines]
        if power_configured:
            intrusion["power_supervision"] = asdict(ps)
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
    return data


def save_project(project: Project, path) -> None:
    """Writes `project` to `path` as projekt.epw (gzip+JSON - see
    module docstring). Bumps `revision` and `modified_at`/`modified_by`
    and clears `is_dirty` - the same "a save is what actually commits a
    revision" rule new_project()/touch() above already document."""
    project.revision += 1
    project.metadata.modified_at = _utc_now_iso()
    project.modified_by = "studio"
    data = _to_json_dict(project)
    payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as f:
        f.write(payload)
    project.is_dirty = False


class ProjectFormatError(Exception):
    """Raised by load_project() for anything SPEC_PROJEKT_EPW.md's own
    "Wersjonowanie i zgodność" section requires an application to refuse
    outright, with a message, rather than guess at - not a real project
    file at all, or a schema_version newer than this module understands."""


def load_project(path) -> Project:
    """Reads `projekt.epw` from `path`. Per the contract's own
    versioning rule: refuses a `schema_version` newer than
    SCHEMA_VERSION with a clear ProjectFormatError (never silently
    guesses); a schema_version OLDER than SCHEMA_VERSION would be
    migrated here once SCHEMA_VERSION > 1 exists - nothing to migrate
    yet at version 1."""
    path = Path(path)
    try:
        with gzip.open(path, "rb") as f:
            payload = f.read()
    except OSError as e:
        raise ProjectFormatError(f"Nie można odczytać pliku projektu: {e}") from e

    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ProjectFormatError(f"Plik nie jest poprawnym plikiem projektu EPW: {e}") from e

    if data.get("format") != FORMAT_MARKER:
        raise ProjectFormatError(
            f"Plik nie jest projektem EPW (brak lub nieprawidłowy znacznik 'format')."
        )
    schema_version = data.get("schema_version")
    if not isinstance(schema_version, int) or schema_version > SCHEMA_VERSION:
        raise ProjectFormatError(
            f"Plik ma wersję formatu {schema_version!r}, nowszą niż obsługiwana "
            f"({SCHEMA_VERSION}). Zaktualizuj Studio, żeby go otworzyć."
        )

    meta = data.get("project", {})
    metadata = ProjectMetadata(
        name=meta.get("name", ""),
        description=meta.get("description", ""),
        author=meta.get("author", ""),
        created_at=meta.get("created_at", _utc_now_iso()),
        modified_at=meta.get("modified_at", _utc_now_iso()),
    )

    project = Project(
        metadata=metadata,
        modules=list(data.get("modules", [])),
        cards=[Card(**c) for c in data.get("cards", [])],
        locations=[Location(**l) for l in data.get("locations", [])],
        points=[Point(**p) for p in data.get("points", [])],
        devices=[
            Device(
                id=d["id"],
                behavior=d["behavior"],
                kind=d.get("kind", ""),
                feedback=list(d.get("feedback", [])),
                command=list(d.get("command", [])),
                supervision=dict(d.get("supervision", {})),
                safe_state=dict(d.get("safeState", {})),
            )
            for d in data.get("devices", [])
        ],
        revision=data.get("revision", 0),
        modified_by=data.get("modified_by", "studio"),
    )
    intrusion = data.get("intrusion", {})
    project.zones = [Zone(**z) for z in intrusion.get("zones", [])]
    project.lines = [Line(**l) for l in intrusion.get("lines", [])]
    if "power_supervision" in intrusion:
        project.power_supervision = PowerSupervision(**intrusion["power_supervision"])
    protection = data.get("protection", {})
    project.electrical_protection_stages = [
        ElectricalProtectionStage(**s) for s in protection.get("electrical", [])
    ]
    project.process_protections = [ProcessProtection(**p) for p in protection.get("process", [])]
    if "modbus_bus" in data:
        project.modbus_bus = ModbusBusConfig(**data["modbus_bus"])
    project.is_dirty = False
    return project
