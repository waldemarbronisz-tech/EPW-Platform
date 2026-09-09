"""Reads .epwsyn files (the EPW Synoptic Editor's project format, format
tag "EPW_SYNOPTIC") and exposes their content to the rest of EPW OS - a
schematic screen's objects, and above all its DEVICE REGISTRY.

Headless (no PyQt import) on purpose, same rule as every other core/
module (see project_manager.py, help_content.py): this is parsing and
validation logic the GUI layer (Project > Load Synoptic Screen...) calls
into, not something that needs a QApplication to be unit-tested.

THE DEVICE REGISTRY IS THE POINT OF THIS MODULE. Per the editor's own
architecture (its src/project/DeviceSchema.ts and src/project/
DeviceBindingValidation.ts, read directly from the editor's repository,
not from memory): device configuration does not live on a screen. A
screen object only says "at this spot, with this symbol, show device
KOT_KMG1" (SynopticObject.deviceId) - all behavioural configuration
(feedback/command/supervision/safeState/switchCounter/positions/...)
lives once in the file's own "devices" list, however many objects or
screens reference it. The SAME deviceId legitimately appearing on
several objects is not a defect to flag - it is this format's whole
point (DeviceBindingValidation.ts never checks for that). An object
whose deviceId does not resolve to any device in the registry IS worth
flagging, but only as a WARNING, never a refusal - same stance as that
file's own validateDeviceBindings().

Devices are classified by BEHAVIOR, not by device "kind". There are
exactly five behaviors (DeviceSchema.ts's own DeviceBehavior type) -
nothing else exists: SWITCHED, SIGNAL, MEASURED, MODULATED, SELECTOR.
"kind" (e.g. "zawor", "pompa") is a free-text display label with NO
functional meaning - this module never branches on it, and neither
should any caller.

Every device record - and every screen object - is kept in full (see
Device.raw / SynopticProject.objects): behaviour-specific fields
(feedback/command/supervision/safeState/switchCounter/interlock/
positions/input/unit/rangeMin/... and any field this module has never
heard of) are never parsed or dropped, only carried through verbatim.

Channel addresses (e.g. "DI1.DI.1", "AI1.AO.4") are CARD_ID.CHANNEL_KIND.
CHANNEL strings, where CARD_ID is whatever id the project's own "cards"
list assigns it - user-chosen at authoring time, no fixed prefix. This
module treats a channel address as an opaque string: it does NOT parse,
validate, or map it onto EPW OS's own DI1..DI64/AO1..AOx addressing.
Bridging the two addressing schemes is a deliberately separate, future
task - see this task's own GRANICE.

SCHEMA VERSIONING: this module supports schema_version 2 (the editor's
current CURRENT_SCHEMA_VERSION) and loads any lower version
permissively - every optional section read below already defaults
safely when absent, so an older file (e.g. one still predating the
device registry entirely) loads exactly as if those newer sections
were never in the file at all; no separate migration step is needed
here. A version HIGHER than this module understands is refused
outright - guessing at a newer format's shape is how silent data loss
happens.

A malformed or corrupted .epwsyn file must never crash the caller -
the same rule ProjectManager already applies to a corrupted
project.json. load_epwsyn_file() never raises; it always returns an
EpwsynLoadResult.
"""

import json
from dataclasses import dataclass, field
from typing import Optional

from epw_os.core.logging import log

SYNOPTIC_FORMAT = "EPW_SYNOPTIC"
CURRENT_SCHEMA_VERSION = 2

# The five device behaviors this format allows - "nic poza nimi" (nothing
# else exists, see DeviceSchema.ts). A device record with any other
# value is still kept in full (its raw record is never discarded) but is
# flagged as a warning - the same "warn, don't refuse the whole file"
# treatment as an unresolved deviceId below.
DEVICE_BEHAVIORS = ("SWITCHED", "SIGNAL", "MEASURED", "MODULATED", "SELECTOR")

DEFAULT_CANVAS_BACKGROUND = "#FFFFFF"
DEFAULT_SCREEN_KIND = "SCHEMATIC"

# An older file may still carry the isometric plan-mode value the editor
# itself has since removed entirely (its own chore/remove-isometric-plan-
# mode) - per the format spec, treat it exactly like SCHEMATIC, not as
# an unknown/invalid kind.
_LEGACY_SCREEN_KINDS = {"PLAN": DEFAULT_SCREEN_KIND}


def _as_list(data: dict, key: str, warnings: list) -> list:
    """`data[key]` if it's already a list, else [] - a corrupted file
    with e.g. "devices": "oops" must not crash iteration downstream. An
    entirely ABSENT optional key is exactly as valid as an empty one and
    produces no warning (format spec: "KAZDE pole opcjonalne, ktorego
    brakuje, ma byc traktowane jak pusta lista... Nigdy jako blad
    wczytania"). A key that IS present but the wrong type is a different
    case - silently discarding it would mean the whole device registry
    (say) can vanish with zero trace, so it's appended to `warnings`
    (never a refusal - the rest of the file still loads)."""
    if key not in data:
        return []
    value = data[key]
    if isinstance(value, list):
        return value
    warnings.append(
        f"'{key}' was present but not a list (got {type(value).__name__}) - treated as empty."
    )
    return []


@dataclass(frozen=True)
class Device:
    """One entry of the file's device registry. `raw` is the complete,
    untouched dict as read from the file - every behavior-specific field
    (feedback/command/supervision/safeState/switchCounter/positions/
    input/unit/... - whatever this device's own behavior carries) lives
    there, unparsed by this module on purpose: this task builds the
    reader, not a bridge into TagManager/CommandManager (see the module
    docstring's GRANICE note). The typed fields below are only the ones
    common to every device regardless of behavior (DeviceSchema.ts's own
    DeviceCommon), enough to list/look up/filter devices without every
    caller having to reach into `raw` for the basics."""
    id: str
    designation: str
    name: str
    behavior: str
    kind: str
    publish_to_ha: bool
    raw: dict


class DeviceRegistry:
    """The project's aparaty: list, lookup by id, filter by behavior.
    Deliberately read-only and inert - nothing here talks to TagManager
    or CommandManager, and nothing here knows what a channel address
    means (that wiring/bridging is a separate, future task)."""

    def __init__(self, devices):
        self._devices = list(devices)
        self._by_id = {}
        for dev in self._devices:
            # A duplicate id WITHIN THE REGISTRY (distinct from two
            # OBJECTS sharing one deviceId, which is always valid and
            # never warned about) can never be resolved unambiguously -
            # keep the first occurrence. load_epwsyn_file() is the one
            # that records the warning; this constructor just needs a
            # deterministic rule to apply.
            self._by_id.setdefault(dev.id, dev)

    def all(self) -> list:
        return list(self._devices)

    def get(self, device_id: str) -> Optional[Device]:
        return self._by_id.get(device_id)

    def by_behavior(self, behavior: str) -> list:
        return [d for d in self._devices if d.behavior == behavior]

    def count_by_behavior(self) -> dict:
        """{behavior: count} for all five known behaviors (always
        present, even at 0) plus any unrecognized behavior actually
        found in the file, keyed by its literal (bad) value."""
        counts = {b: 0 for b in DEVICE_BEHAVIORS}
        for dev in self._devices:
            counts[dev.behavior] = counts.get(dev.behavior, 0) + 1
        return counts

    def __len__(self):
        return len(self._devices)


@dataclass
class SynopticProject:
    """The full, parsed content of one .epwsyn file. Every field below
    is either obligatory in the format or defaults to an empty list/
    sensible value when the file's own optional section is absent -
    never None where a caller would have to guard for it first."""
    source_path: str
    schema_version: int
    name: str
    description: str
    created_at: Optional[str]
    modified_at: Optional[str]
    canvas: dict
    kind: str
    help_language: Optional[str]
    objects: list             # raw dicts, every field preserved verbatim
    connections: list         # raw dicts, opaque to this module
    locations: list           # raw dicts: {"code", "description"}
    cards: list                # raw dicts: {"id", "model", "channelKind", "channelCount"}
    meters: list
    signal_panels: list
    frames: list
    group_commands: list
    setpoint_panels: list
    devices: DeviceRegistry

    def object_count(self) -> int:
        return len(self.objects)

    def find_object(self, object_id: str) -> Optional[dict]:
        for obj in self.objects:
            if obj.get("id") == object_id:
                return obj
        return None


@dataclass
class EpwsynLoadResult:
    """Result of load_epwsyn_file(). `ok=False` is a hard refusal
    (odmowa) - `error` then names exactly which rule/field failed and
    `project` is None. `ok=True` means the file loaded, however many
    `warnings` (soft issues, never fatal) were collected along the way -
    e.g. an object referencing a deviceId the registry doesn't have."""
    ok: bool
    error: Optional[str] = None
    warnings: list = field(default_factory=list)
    project: Optional[SynopticProject] = None


def _fail(path: str, message: str) -> EpwsynLoadResult:
    log.error(f"Refused to load synoptic screen {path!r}: {message}")
    return EpwsynLoadResult(ok=False, error=message)


def load_epwsyn_file(path: str) -> EpwsynLoadResult:
    """Reads and validates one .epwsyn file. Never raises - any failure
    (missing/unreadable file, invalid JSON, wrong format, unsupported
    schema_version, a missing required field, duplicate object ids)
    comes back as ok=False with a human-readable `error`, exactly like
    ProjectManager's own handling of a corrupted project.json. A
    resolvable-but-imperfect file (an unknown deviceId reference, say)
    still loads (ok=True) with the issue recorded in `warnings`."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_text = f.read()
    except OSError as e:
        return _fail(path, f"Could not read file: {e}")

    try:
        data = json.loads(raw_text)
    except ValueError as e:
        # json.JSONDecodeError is a ValueError subclass - the same catch
        # ProjectManager._read()/epw_os.i18n._load() already use for "the
        # file exists but isn't parseable JSON at all".
        return _fail(path, f"Not a valid JSON file: {e}")

    if not isinstance(data, dict):
        return _fail(path, "File does not contain a JSON object.")

    # --- Required top-level fields (section 1 of the format spec) -------

    if data.get("format") != SYNOPTIC_FORMAT:
        return _fail(path, f"Not an EPW Synoptic Editor file (format must be {SYNOPTIC_FORMAT!r}).")

    schema_version = data.get("schema_version")
    # bool is a subclass of int in Python - explicitly excluded so a
    # stray JSON `true`/`false` isn't accepted as a version number.
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        return _fail(path, "Missing or invalid required field: schema_version.")
    if schema_version > CURRENT_SCHEMA_VERSION:
        return _fail(
            path,
            f"Unsupported schema_version {schema_version} (this version of EPW OS reads up to "
            f"schema_version {CURRENT_SCHEMA_VERSION}). Update EPW OS before loading this file.",
        )
    # schema_version < CURRENT_SCHEMA_VERSION loads permissively from here
    # on - every optional section below already defaults safely when
    # absent, which is exactly what an older file needs (GRANICE: no
    # migration, no addressing bridge - just load what's there and
    # default the rest).

    project_meta = data.get("project")
    if not isinstance(project_meta, dict):
        return _fail(path, "Missing required field: project.")

    canvas = data.get("canvas")
    if not isinstance(canvas, dict):
        return _fail(path, "Missing required field: canvas.")
    # width/height are required NUMBERS - the editor's own validator
    # (ProjectSchema.ts's validateProjectSchema, INVALID_CANVAS) refuses
    # a canvas missing either as invalid; this reader must not be looser
    # than the tool that produces these files. bool excluded, same
    # reasoning as the schema_version check above.
    canvas_width = canvas.get("width")
    if not isinstance(canvas_width, (int, float)) or isinstance(canvas_width, bool):
        return _fail(path, "Missing or invalid required field: canvas.width.")
    canvas_height = canvas.get("height")
    if not isinstance(canvas_height, (int, float)) or isinstance(canvas_height, bool):
        return _fail(path, "Missing or invalid required field: canvas.height.")

    objects_raw = data.get("objects")
    if not isinstance(objects_raw, list):
        return _fail(path, "Missing required field: objects.")

    # --- Object ids: required, unique (section 2 + this task's own DOWOD) -

    seen_ids = set()
    duplicate_ids = set()
    for obj in objects_raw:
        if not isinstance(obj, dict) or not obj.get("id"):
            return _fail(path, "An object is missing its required 'id' field.")
        obj_id = obj["id"]
        if obj_id in seen_ids:
            duplicate_ids.add(obj_id)
        seen_ids.add(obj_id)
    if duplicate_ids:
        return _fail(path, f"Duplicate object id(s): {', '.join(sorted(duplicate_ids))}.")

    warnings = []

    # --- Device registry (section 3 - the point of this whole module) ---

    devices = []
    seen_device_ids = set()
    for entry in _as_list(data, "devices", warnings):
        if not isinstance(entry, dict) or not entry.get("id"):
            warnings.append("A device entry is missing its required 'id' field and was skipped.")
            continue
        dev_id = entry["id"]
        if dev_id in seen_device_ids:
            warnings.append(f"Duplicate device id '{dev_id}' in the registry - first occurrence kept.")
            continue
        seen_device_ids.add(dev_id)
        behavior = entry.get("behavior", "")
        if behavior not in DEVICE_BEHAVIORS:
            warnings.append(f"Device '{dev_id}' has an unrecognized behavior {behavior!r}.")
        devices.append(Device(
            id=dev_id,
            designation=entry.get("designation", ""),
            name=entry.get("name", ""),
            behavior=behavior,
            kind=entry.get("kind", ""),
            publish_to_ha=bool(entry.get("publishToHa", False)),
            raw=entry,
        ))
    registry = DeviceRegistry(devices)

    # An object's deviceId not resolving to any device in the registry is
    # a WARNING, never a refusal - the object still loads, simply with
    # nothing to look up (spec section 3 + DeviceBindingValidation.ts).
    # The SAME deviceId appearing on multiple objects is not checked for
    # at all here - it is explicitly not an issue.
    known_device_ids = {d.id for d in devices}
    for obj in objects_raw:
        device_id = obj.get("deviceId")
        if device_id and device_id not in known_device_ids:
            warnings.append(f"Object '{obj['id']}' references unknown device '{device_id}'.")

    # --- Everything else: pure pass-through, defaulting when absent -----

    kind = data.get("kind") or DEFAULT_SCREEN_KIND
    kind = _LEGACY_SCREEN_KINDS.get(kind, kind)

    project = SynopticProject(
        source_path=path,
        schema_version=schema_version,
        name=project_meta.get("name", ""),
        description=project_meta.get("description", ""),
        created_at=project_meta.get("created_at"),
        modified_at=project_meta.get("modified_at"),
        canvas={
            "width": canvas_width,
            "height": canvas_height,
            "background": canvas.get("background", DEFAULT_CANVAS_BACKGROUND),
            "gridSize": canvas.get("gridSize"),
        },
        kind=kind,
        help_language=data.get("helpLanguage"),
        objects=objects_raw,
        connections=_as_list(data, "connections", warnings),
        locations=_as_list(data, "locations", warnings),
        cards=_as_list(data, "cards", warnings),
        meters=_as_list(data, "meters", warnings),
        signal_panels=_as_list(data, "signalPanels", warnings),
        frames=_as_list(data, "frames", warnings),
        group_commands=_as_list(data, "groupCommands", warnings),
        setpoint_panels=_as_list(data, "setpointPanels", warnings),
        devices=registry,
    )

    for w in warnings:
        log.warning(f"{path}: {w}")

    return EpwsynLoadResult(ok=True, warnings=warnings, project=project)
