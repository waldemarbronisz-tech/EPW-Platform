"""The `projekt.epw` file format - shared/docs/SPEC_PROJEKT_EPW.md is the
authoritative contract this module implements. Read that document before
changing anything here; this module's own docstrings quote it rather than
restate it from memory, so the two don't quietly drift apart.

Scope of THIS module, deliberately: the "structural" fields the contract
itself groups under Studio's exclusive editing layer (Nagłówek, Skład
urządzenia, Sprzęt, Punkty, Aparaty) - not yet `screens`/`logic`
(embedding the Synoptic/Logic Studio editors' own content into this file
is a separate, much larger integration - SynopticPanel/LogicPanel keep
their own .epwsyn/.epwlogic save flow entirely unchanged until that
lands, so nothing about how Ekrany/Logika save today is touched by this
module), and not yet `intrusion`/`protection` (each is its own later
step in the contract's own "Kolejność wdrożenia"). Adding a field here
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
    id="DI1", model="ELA01", kind="DI", channels=32."""

    id: str
    model: str
    kind: str
    channels: int


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
    feedback: list = field(default_factory=list)
    command: list = field(default_factory=list)
    supervision: dict = field(default_factory=dict)
    safe_state: dict = field(default_factory=dict)  # onStartup, onLinkLoss


@dataclass
class Project:
    """The whole of `projekt.epw`'s in-memory representation - only the
    fields this module currently implements (see module docstring for
    what's deliberately still missing and why)."""

    metadata: ProjectMetadata
    modules: list = field(default_factory=list)  # list[str]
    cards: list = field(default_factory=list)  # list[Card]
    locations: list = field(default_factory=list)  # list[Location]
    points: list = field(default_factory=list)  # list[Point]
    devices: list = field(default_factory=list)  # list[Device]
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
    project.is_dirty = False
    return project
