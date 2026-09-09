"""Tests for the signal (tag) list export
(epw_os/core/tag_export.py) - headless, no Qt/FastAPI needed at all.
Real EventBus/TagManager (both already Qt-free), same pattern every
other core-module test file in this codebase already uses.
"""
import json

import pytest

from epw_os.core.events import EventBus
from epw_os.core.tag_manager import TagManager, TagType, TagQuality
from epw_os.core.tag_export import (
    build_tag_list_export, TAG_LIST_FORMAT_VERSION, LOGIC_WRITABLE_TAGS,
    _group_for_tag, _module_for_group, _direction_for_tag,
)


class FakeProjectManager:
    def __init__(self, analog_points=None, metadata_name="", project_id="DEFAULT_PROJECT"):
        self._analog_points = analog_points or []
        self._metadata_name = metadata_name
        # tag_export.py deliberately reads .config["analog_points"]
        # directly, not get_analog_points() (see _unit_lookup()'s own
        # docstring for why) - kept in sync here the same way a real
        # ProjectManager's own getter just returns this same list.
        self.config = {"project_id": project_id, "analog_points": self._analog_points}

    def get_analog_points(self):
        return self._analog_points

    def get_metadata(self):
        return {"name": self._metadata_name}


@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def tags(bus):
    tm = TagManager(bus)
    tm.add_tag("DI1", True, TagType.BOOL, description="Feeder 1 feedback", source="HARDWARE")
    tm.add_tag("DO05", False, TagType.BOOL, description="Output 5", source="HARDWARE")
    tm.add_tag("System.Theme", 0, TagType.INT, description="Active visual theme")
    tm.add_tag("Security.Zone.Z1.State", "DISARMED", TagType.STRING, description="Intrusion zone state")
    tm.add_tag("Security.Zone.Z1.ArmRequest", False, TagType.BOOL, description="Arm/disarm from logic")
    tm.add_tag("Safety.System.Healthy", True, TagType.BOOL, description="Aggregate health")
    tm.add_tag("Process.PP1.Exceeded", False, TagType.BOOL, description="Process protection signal")
    tm.add_tag("Meas.L1", 230.0, TagType.REAL, description="Sim voltage", source="SIMULATION",
               quality=TagQuality.SIMULATED)
    tm.add_tag("AI1", 12.3, TagType.REAL, description="Custom analog", source="HARDWARE")
    tm.add_tag("EMERGENCY_STOP", False, TagType.BOOL, description="E-stop")
    return tm


@pytest.fixture
def pm():
    return FakeProjectManager(
        analog_points=[{"tag": "AI1", "unit": "°C", "description": "Custom analog"}],
        metadata_name="Test Substation",
    )


# --- DOWÓD: export contains every tag registered in TagManager ---------

def test_export_contains_every_registered_tag(tags, pm):
    export = build_tag_list_export(tags, pm)
    exported_names = {t["name"] for t in export["tags"]}
    real_names = {t.name for t in tags.list_tags()}
    assert exported_names == real_names
    assert export["tag_count"] == len(real_names) == len(tags.list_tags())


def test_export_is_json_serializable(tags, pm):
    export = build_tag_list_export(tags, pm)
    raw = json.dumps(export, ensure_ascii=False)
    reparsed = json.loads(raw)
    assert reparsed["tag_count"] == export["tag_count"]


# --- DOWÓD: System.Theme writable, everything else read-only ------------

def test_system_theme_is_the_only_writable_tag(tags, pm):
    export = build_tag_list_export(tags, pm)
    for entry in export["tags"]:
        if entry["name"] == "System.Theme":
            assert entry["direction"] == "READ_WRITE"
        else:
            assert entry["direction"] == "READ_ONLY", entry

    writable = {t["name"] for t in export["tags"] if t["direction"] == "READ_WRITE"}
    assert writable == {"System.Theme"}


def test_logic_writable_tags_constant_is_exactly_system_theme():
    """Task's own explicit ground truth - see tag_export.py's own
    module docstring for why this is a hand-maintained allowlist, not
    derived from Tag.read_only (removed entirely - see tag_manager.py's
    own comment on the Tag dataclass)."""
    assert LOGIC_WRITABLE_TAGS == frozenset({"System.Theme"})


def test_arm_request_style_tags_are_not_writable_despite_being_reacted_to():
    """Security.Zone.<id>.ArmRequest is READ by IntrusionManager and
    treated as an external command - but it is NOT part of this
    export's declared write contract (Task's own Request.* boundary -
    see the module docstring). Explicitly checked so a future change
    can't silently start reporting it as writable without a deliberate
    decision."""
    assert _direction_for_tag("Security.Zone.Z1.ArmRequest") == "READ_ONLY"


# --- DOWÓD: export does not touch any configuration file ----------------

def test_export_never_calls_any_mutating_method(tags, pm):
    """Read-only, by construction - patches every write-shaped method
    TagManager/ProjectManager expose to raise if ever called, then
    builds a real export against real data."""
    def _forbidden(*a, **k):
        raise AssertionError("tag_export must never write/mutate anything")

    tags.add_tag = _forbidden
    tags.update_tag = _forbidden
    tags.remove_tag = _forbidden
    tags.set_description = _forbidden
    pm.set_analog_points = _forbidden
    pm.save_project = _forbidden

    export = build_tag_list_export(tags, pm)
    assert export["tag_count"] > 0  # still produced a real result


def test_export_does_not_write_project_json(tmp_path, tags):
    """A real ProjectManager, isolated to a scratch project.json (memory
    rule: never touch the real one) - confirms the file's bytes are
    byte-for-byte unchanged after an export, not just that no setter
    was called."""
    from epw_os.core.project_manager import ProjectManager
    scratch = tmp_path / "project.json"
    real_pm = ProjectManager(project_file=str(scratch))
    real_pm.load_project()
    real_pm.save_project()  # create a known-good baseline file to diff against
    before = scratch.read_bytes()

    build_tag_list_export(tags, real_pm)

    after = scratch.read_bytes()
    assert before == after, "export must never modify project.json"


def test_export_works_with_no_project_manager_at_all(tags):
    """A caller with no real project (project_manager=None) still gets
    a complete, valid export - just with unit=None everywhere and an
    empty project_name."""
    export = build_tag_list_export(tags, None)
    assert export["tag_count"] == len(tags.list_tags())
    assert export["project_name"] == ""
    assert all(t["unit"] is None for t in export["tags"])


# --- header fields --------------------------------------------------------

def test_header_fields_present(tags, pm):
    export = build_tag_list_export(tags, pm)
    assert export["format_version"] == TAG_LIST_FORMAT_VERSION
    assert export["project_name"] == "Test Substation"
    assert isinstance(export["epw_os_version"], str) and export["epw_os_version"]
    assert "exported_at" in export and "T" in export["exported_at"]  # ISO 8601


def test_project_name_falls_back_to_project_id_when_metadata_name_unset():
    pm_no_meta = FakeProjectManager(metadata_name="", project_id="MY_SITE")
    bus = EventBus()
    tm = TagManager(bus)
    tm.add_tag("DI1", True, TagType.BOOL)
    export = build_tag_list_export(tm, pm_no_meta)
    assert export["project_name"] == "MY_SITE"


# --- unit (analog points only) --------------------------------------------

def test_unit_present_only_for_configured_analog_points(tags, pm):
    export = build_tag_list_export(tags, pm)
    ai1 = next(t for t in export["tags"] if t["name"] == "AI1")
    assert ai1["unit"] == "°C"
    di1 = next(t for t in export["tags"] if t["name"] == "DI1")
    assert di1["unit"] is None


# --- is_simulated ----------------------------------------------------------

def test_is_simulated_reflects_quality(tags, pm):
    export = build_tag_list_export(tags, pm)
    meas = next(t for t in export["tags"] if t["name"] == "Meas.L1")
    assert meas["is_simulated"] is True
    di1 = next(t for t in export["tags"] if t["name"] == "DI1")
    assert di1["is_simulated"] is False


# --- grouping / module (Task part 3) ---------------------------------------

@pytest.mark.parametrize("name,expected_group", [
    ("Security.Zone.Z1.State", "Security"),
    ("Safety.System.Healthy", "Safety"),
    ("Process.PP1.Exceeded", "Process"),
    ("System.Theme", "System"),
    ("DI1", "DI"),
    ("DO05", "DO"),
    ("AI1", "AI"),
    ("EMERGENCY_STOP", "EMERGENCY_STOP"),
    ("ELA01.DI01", "ELA01"),
])
def test_group_for_tag(name, expected_group):
    assert _group_for_tag(name) == expected_group


def test_module_for_known_groups_is_a_readable_label():
    assert _module_for_group("Security") == "Intrusion Alarm System"
    assert _module_for_group("Safety") == "Safety Kernel"
    assert _module_for_group("Process") == "Process Protections"


def test_module_for_unknown_group_falls_back_to_the_group_itself():
    assert _module_for_group("ELA01") == "ELA01"


def test_groups_tree_lists_every_tag_exactly_once(tags, pm):
    export = build_tag_list_export(tags, pm)
    all_grouped_names = [name for names in export["groups"].values() for name in names]
    assert sorted(all_grouped_names) == sorted(t["name"] for t in export["tags"])
    assert len(all_grouped_names) == len(set(all_grouped_names))  # no duplicates


def test_di_do_tags_group_together(tags, pm):
    export = build_tag_list_export(tags, pm)
    assert "DI1" in export["groups"]["DI"]
    assert "DO05" in export["groups"]["DO"]


# --- Request.* placeholder (Task part 4) -----------------------------------

def test_request_tags_placeholder_is_always_empty(tags, pm):
    export = build_tag_list_export(tags, pm)
    assert export["request_tags"] == []
