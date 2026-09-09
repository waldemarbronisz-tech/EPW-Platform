"""Signal (tag) list export (Task: "eksport listy wszystkich tagow
systemowych do pliku, zeby Logic Studio i Synoptic Editor mogly z niej
korzystac przy projektowaniu"). Headless (no Qt/FastAPI import), same
rule every other core/ module in this codebase follows - the GUI menu
action (main_window.py) and the REST API endpoint (backend/api.py)
both call build_tag_list_export() and just decide what to DO with the
result (write it to a file, or return it as a JSON response).

SCOPE: this module only ever READS TagManager/ProjectManager - it never
calls add_tag()/update_tag()/remove_tag(), never calls
project_manager.save_project(), and never mutates project.json (Task's
own GRANICE: "eksport to odczyt"). See
test_never_writes_anything.

FORMAT VERSION: bump TAG_LIST_FORMAT_VERSION whenever the shape of the
export changes in a way an existing Logic Studio/Synoptic Editor parser
could not tolerate (a field renamed or removed, a type changed) - Task's
own requirement: "Logic Studio moze odmowic wczytania listy z
niezgodnej wersji zamiast zgadywac." Purely ADDING a new field is not
normally a reason to bump it (a reasonable parser should already ignore
unknown keys) - use judgement, document the reason in this docstring's
own changelog note when it happens.

REQUEST.* PLACEHOLDER (Task part 4 - "zostaw miejsce w formacie, ale
nic nie implementuj"): "request_tags" is always [] today - the
Request.* layer (a future, separate family of logic-writable command
tags, distinct from the ordinary tags this module already exports) does
not exist in the code yet, and this task does not build it. The key
exists now so a future task can start populating it without forcing
Logic Studio to handle a brand-new top-level key it's never seen (and
without a format-version bump for that alone).

DIRECTION / WRITABLE-BY-LOGIC (Task part 4): Tag.read_only (tag_manager.py)
was NOT what this field reported - a full-codebase search found every
single tag in this program registered with read_only=False (the
dataclass default), NEVER SET to True anywhere in over a dozen call
sites reviewed - including things that clearly aren't meant for logic
to poke at, like DI1 or Security.Line.<id>.State. That field was
effectively unused/vestigial, not a real signal of intent - and has
since been REMOVED from the Tag dataclass entirely (Task:
"System.Mode i polykane wyjatki" - "Tag.read_only - martwe pole"; see
tag_manager.py's own comment on the Tag dataclass for the removal
reasoning). The one place a *documented* logic-write contract already
exists is
System.Theme (see epw_core.py's own comment: "System.Theme: writable,
drives the GUI's visual theme... changed via logic" and
ThemeManager._on_tag_changed()'s real, working handling of an external
write). Other tags that happen to get READ reactively by a manager
watching for external writes (e.g. Security.Zone.<id>.ArmRequest -
IntrusionManager treats ANY write to it as an arm/disarm request) are
a different, ad hoc pattern each manager built for itself, not a
declared part of this exported contract - the Task's own framing
("dzis JEDYNYM tagiem, ktory logika ma prawo zapisac, jest
System.Theme") together with the explicit "Request.* nie ma powstac"
boundary reads as: today's export should show ONLY the one tag with an
intentional, general-purpose write contract, and leave the rest to be
formalized by the future Request.* layer. LOGIC_WRITABLE_TAGS below is
therefore a small, explicit, hand-maintained allowlist - not derived
from Tag.read_only, and not derived from scanning which managers
happen to subscribe to which tag names.
"""

from datetime import datetime, timezone

from epw_os.core.tag_manager import TagQuality
from epw_os.version import __version__ as EPW_OS_VERSION

TAG_LIST_FORMAT_VERSION = "1.0"

# Task part 4's own explicit ground truth - see the module docstring's
# "DIRECTION / WRITABLE-BY-LOGIC" section for why this is a hand-
# maintained allowlist, not derived from Tag.read_only (removed).
LOGIC_WRITABLE_TAGS = frozenset({"System.Theme"})

DIRECTION_READ_ONLY = "READ_ONLY"
DIRECTION_READ_WRITE = "READ_WRITE"

# Known tag-name prefixes -> a human-readable owning-module label (Task:
# "modul bedacy wlascicielem"). Built from an actual inventory of every
# add_tag() call site in this codebase (core/*.py) at the time this was
# written - see SESSION_REPORT.md for the full list. A prefix NOT listed
# here (a multi-device hardware tag like "ELA01"/"ADA01"/"EPM01" from
# TagManager.configure()'s multi-device path, or an operator-renamed
# Analog Input point) falls back to using the prefix itself as both the
# module label and the group (see _group_for_tag() below) - deliberately
# not guessed at, so an unrecognized prefix is still exported correctly,
# just without a nicer label.
_KNOWN_MODULE_NAMES = {
    "Security": "Intrusion Alarm System",
    "Safety": "Safety Kernel",
    "Process": "Process Protections",
    "System": "System / Core",
    "Cabinet": "Cabinet Monitoring",
    "Device": "Device Communication Status",
    "Sim": "Simulation Sandbox",
    "Meas": "Simulated Measurements",
    "DI": "Digital Inputs",
    "DO": "Digital Outputs",
    "AI": "Analog Inputs",
    "EMERGENCY_STOP": "System / Core",
}


def _group_for_tag(name: str) -> str:
    """The prefix used both for the per-tag "group" field and for the
    top-level "groups" tree (Task part 3: "pogrupowane po prefiksie...
    zeby dalo sie je pokazac w drzewie"). A dotted name ("Security.Zone.
    Z1.State", "ELA01.DI01") groups on its first segment; a flat name
    with no dot (DI1, DO05, EMERGENCY_STOP - this program's fixed-slot
    hardware I/O, see TagManager.init_default_tags()) groups on its
    leading alphabetic run, so DI1..DI64 group together as "DI",
    DO05..DO64 as "DO", and a genuine one-off flat tag becomes its own
    single-tag group rather than silently merging into something else."""
    if "." in name:
        return name.split(".", 1)[0]
    i = 0
    while i < len(name) and (name[i].isalpha() or name[i] == "_"):
        i += 1
    return name[:i] if i > 0 else name


def _module_for_group(group: str) -> str:
    return _KNOWN_MODULE_NAMES.get(group, group)


def _direction_for_tag(name: str) -> str:
    return DIRECTION_READ_WRITE if name in LOGIC_WRITABLE_TAGS else DIRECTION_READ_ONLY


def _unit_lookup(project_manager) -> dict:
    """tag name -> unit, for every configured Analog Input point (Task:
    "jednostka, dla punktow analogowych"). Every other tag has no unit
    (None in the export, never an empty string, so a consumer can
    unambiguously tell "not an analog point" apart from "analog point
    with no unit set yet"). project_manager may be None (an isolated
    caller with no real project) - the export is still complete, just
    with unit=None for everything.

    Deliberately does NOT call project_manager.get_analog_points()
    directly - that method MIGRATES an old-format project.json (no
    "analog_points" key yet) and immediately calls save_project() the
    very first time it's ever invoked (see its own docstring). Calling
    it from here would make a plain, read-only export able to write to
    project.json on a project nothing has touched yet - a real
    violation of this module's own GRANICE ("eksport to odczyt"), not
    just a theoretical one (caught by
    test_tag_export.py::test_export_does_not_write_project_json).
    Reading project_manager.config directly instead is always a pure
    read; in real use this is a non-issue either way, since EPWCore.
    startup() always calls get_analog_points() once, unconditionally,
    long before an export could ever run (see epw_core.py's own
    _register_analog_input_tags()) - this fallback only matters for a
    ProjectManager nothing has started yet, which never happens outside
    a test."""
    if project_manager is None:
        return {}
    config = getattr(project_manager, "config", None)
    if not isinstance(config, dict):
        return {}
    points = config.get("analog_points", [])
    if not isinstance(points, list):
        return {}
    return {p["tag"]: p.get("unit") or None for p in points if isinstance(p, dict) and "tag" in p}


def _project_name(project_manager) -> str:
    if project_manager is None:
        return ""
    try:
        name = project_manager.get_metadata().get("name", "")
    except AttributeError:
        # Deliberate, not logged: project_manager is a minimal stand-in
        # without get_metadata() in some isolated callers/tests - name
        # just stays "" and the caller falls back to project_id below.
        # Would fire routinely for every such caller, not just a real
        # problem.
        name = ""
    if name:
        return name
    # Metadata's own "name" field is operator-entered and often never
    # set (see project_manager.py's own get_metadata() docstring) -
    # project_id is the one identifier every project.json always has,
    # migrated or not (ProjectManager._default_config()).
    config = getattr(project_manager, "config", None)
    if isinstance(config, dict):
        return config.get("project_id", "")
    return ""


def build_tag_list_export(tag_manager, project_manager=None) -> dict:
    """The one function both the GUI menu action and the REST API
    endpoint call - builds the complete, JSON-serializable export
    structure. Read-only: never calls anything on tag_manager/
    project_manager other than list_tags()/get_analog_points()/
    get_metadata() (all read accessors) - see the module docstring's
    own SCOPE note."""
    tags = sorted(tag_manager.list_tags(), key=lambda t: t.name)
    units = _unit_lookup(project_manager)

    tag_entries = []
    groups: "dict[str, list[str]]" = {}
    for tag in tags:
        group = _group_for_tag(tag.name)
        groups.setdefault(group, []).append(tag.name)
        tag_entries.append({
            "name": tag.name,
            "data_type": tag.data_type.value,
            "direction": _direction_for_tag(tag.name),
            "module": _module_for_group(group),
            "group": group,
            "description": tag.description or "",
            "is_simulated": tag.quality == TagQuality.SIMULATED,
            "unit": units.get(tag.name),
            "value": tag.value,
        })

    return {
        "format_version": TAG_LIST_FORMAT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "project_name": _project_name(project_manager),
        "epw_os_version": EPW_OS_VERSION,
        "tag_count": len(tag_entries),
        "tags": tag_entries,
        "groups": groups,
        # Task part 4 - see the module docstring's own REQUEST.*
        # PLACEHOLDER section. Always empty today.
        "request_tags": [],
    }
