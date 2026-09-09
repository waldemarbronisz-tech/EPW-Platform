"""Tests for epw_os.core.epwsyn_loader - reading .epwsyn files (the EPW
Synoptic Editor's project format) and exposing their device registry.

Four real files, exported by the actual editor (not hand-built fixtures),
live in the sibling EPW-Synoptic-Editor project at studio/synoptic/
examples/ and are used directly here for the "does a real export load"
tests:

    GOSPODARKA_WODNA.epwsyn         schema_version 2, 15 objects, 9
                                     devices (cards/locations/meters/
                                     signalPanels all present)
    ENTRY_GATE_LIBRARY_TEST.epwsyn  schema_version 1, 25 objects, none
                                     of the optional fields present
    LIBRARY_TEST.epwsyn             schema_version 1, 13 objects
    STATEFUL_SYMBOLS.epwsyn         schema_version 1, 12 objects

Everything else (corrupted JSON, an unsupported schema_version, a
duplicate object id, an unresolved deviceId) is exercised with small
hand-built fixtures via tmp_path - real files don't naturally exhibit
error conditions, and per this repo's own convention (see
project_manager tests) a verification test must never touch a real
project/config file.
"""

import json
import os

import pytest

from epw_os.core.epwsyn_loader import (
    CURRENT_SCHEMA_VERSION,
    DEVICE_BEHAVIORS,
    load_epwsyn_file,
)
from epw_os.core.project_manager import ProjectManager

EXAMPLES_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "studio", "synoptic", "examples"
)
pytestmark_examples = pytest.mark.skipif(
    not os.path.isdir(EXAMPLES_DIR),
    reason="EPW-Synoptic-Editor's studio/synoptic/examples/ not present in this checkout",
)


def _example(name):
    return os.path.join(EXAMPLES_DIR, name)


def _write(tmp_path, name, data):
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def _minimal_valid(**overrides):
    doc = {
        "format": "EPW_SYNOPTIC",
        "schema_version": 2,
        "project": {"name": "Test", "description": "", "created_at": "", "modified_at": ""},
        "canvas": {"width": 100, "height": 100, "background": "#FFFFFF"},
        "objects": [{"id": "obj-1", "type": "lamp", "category": "electrical"}],
    }
    doc.update(overrides)
    return doc


# --- Real exports from the editor ------------------------------------

@pytestmark_examples
def test_real_v2_file_loads_objects_and_devices():
    result = load_epwsyn_file(_example("GOSPODARKA_WODNA.epwsyn"))
    assert result.ok
    assert result.error is None
    assert result.project.schema_version == 2
    assert result.project.object_count() == 15
    assert len(result.project.devices) == 9
    counts = result.project.devices.count_by_behavior()
    assert counts["SWITCHED"] == 5
    assert counts["MEASURED"] == 2
    assert counts["SIGNAL"] == 2
    assert counts["MODULATED"] == 0
    assert counts["SELECTOR"] == 0
    # Optional sections this file DOES carry - passed through, not dropped.
    assert len(result.project.cards) == 3
    assert len(result.project.locations) == 2
    assert len(result.project.meters) == 1
    assert len(result.project.signal_panels) == 1
    # A device is found by id, and its full record (feedback/command/
    # supervision/safeState/switchCounter/publishToHa - everything, not
    # just the common fields) survived untouched.
    dev = result.project.devices.get("KOT_ZAW1")
    assert dev is not None
    assert dev.behavior == "SWITCHED"
    assert dev.raw["safeState"] == {"onStartup": "NO_CHANGE", "onLinkLoss": "NO_CHANGE"}
    assert dev.raw["supervision"]["discrepancyAlarm"] is True
    assert "switchCounter" in dev.raw
    # The same deviceId legitimately appears on more than one object in
    # this file (e.g. a meter/signal panel row referencing it too, plus
    # its own schematic symbol) - this must never be flagged as a warning.
    assert not any("KOT_ZAW1" in w and "unknown" in w for w in result.warnings)


@pytest.mark.parametrize("filename,expected_objects", [
    ("ENTRY_GATE_LIBRARY_TEST.epwsyn", 25),
    ("LIBRARY_TEST.epwsyn", 13),
    ("STATEFUL_SYMBOLS.epwsyn", 12),
])
@pytestmark_examples
def test_real_v1_files_without_optional_fields_load_cleanly(filename, expected_objects):
    result = load_epwsyn_file(_example(filename))
    assert result.ok, result.error
    assert result.project.schema_version == 1
    assert result.project.object_count() == expected_objects
    # None of these files have ever had a device registry (schema_version
    # 1, predates it entirely) - absent, not an error, and every other
    # optional section defaults to an empty list.
    assert len(result.project.devices) == 0
    assert result.project.connections == []
    assert result.project.locations == []
    assert result.project.cards == []
    assert result.project.meters == []
    assert result.project.signal_panels == []
    assert result.project.frames == []
    assert result.project.group_commands == []
    assert result.project.setpoint_panels == []
    assert result.warnings == []
    # An older file's objects still carry every field they were saved
    # with (editor/animation/customProperties/... for STATEFUL_SYMBOLS) -
    # nothing here strips unknown fields.
    assert result.project.objects[0]["id"]


# --- Schema version handling ------------------------------------------

def test_newer_schema_version_is_rejected_with_message(tmp_path):
    path = _write(tmp_path, "future.epwsyn", _minimal_valid(schema_version=CURRENT_SCHEMA_VERSION + 1))
    result = load_epwsyn_file(path)
    assert not result.ok
    assert result.project is None
    assert str(CURRENT_SCHEMA_VERSION + 1) in result.error
    assert str(CURRENT_SCHEMA_VERSION) in result.error


# --- Corrupted / malformed files never crash the caller ----------------

def test_corrupted_json_does_not_raise(tmp_path):
    path = tmp_path / "broken.epwsyn"
    path.write_text("{ this is not json", encoding="utf-8")
    result = load_epwsyn_file(str(path))
    assert result.ok is False
    assert result.project is None
    assert result.error


def test_missing_file_does_not_raise(tmp_path):
    result = load_epwsyn_file(str(tmp_path / "does_not_exist.epwsyn"))
    assert result.ok is False
    assert result.error


def test_wrong_format_tag_is_rejected(tmp_path):
    path = _write(tmp_path, "wrong_format.epwsyn", _minimal_valid(format="SOME_OTHER_FORMAT"))
    result = load_epwsyn_file(path)
    assert not result.ok
    assert "EPW_SYNOPTIC" in result.error


def test_missing_required_field_is_rejected(tmp_path):
    doc = _minimal_valid()
    del doc["canvas"]
    path = _write(tmp_path, "no_canvas.epwsyn", doc)
    result = load_epwsyn_file(path)
    assert not result.ok
    assert "canvas" in result.error


# --- Object id rules -----------------------------------------------------

def test_duplicate_object_id_is_rejected(tmp_path):
    doc = _minimal_valid(objects=[
        {"id": "dup", "type": "lamp", "category": "electrical"},
        {"id": "dup", "type": "valve", "category": "water"},
    ])
    path = _write(tmp_path, "dup_ids.epwsyn", doc)
    result = load_epwsyn_file(path)
    assert not result.ok
    assert "dup" in result.error


# --- Device registry: the core of this task -----------------------------

def test_unresolved_device_id_is_a_warning_not_a_refusal(tmp_path):
    doc = _minimal_valid(
        objects=[{"id": "obj-1", "type": "lamp", "category": "electrical", "deviceId": "GHOST"}],
        devices=[],
    )
    path = _write(tmp_path, "ghost_device.epwsyn", doc)
    result = load_epwsyn_file(path)
    assert result.ok
    assert result.project is not None
    assert any("GHOST" in w for w in result.warnings)
    # The object itself still loaded, deviceId and all.
    assert result.project.find_object("obj-1")["deviceId"] == "GHOST"


def test_same_device_id_on_multiple_objects_is_valid(tmp_path):
    doc = _minimal_valid(
        objects=[
            {"id": "obj-1", "type": "lamp", "category": "electrical", "deviceId": "KOT_KMG1"},
            {"id": "obj-2", "type": "lamp", "category": "electrical", "deviceId": "KOT_KMG1"},
        ],
        devices=[{
            "id": "KOT_KMG1", "designation": "-K1", "name": "Stycznik grzalki",
            "behavior": "SWITCHED", "kind": "contactor", "publishToHa": False,
        }],
    )
    path = _write(tmp_path, "shared_device.epwsyn", doc)
    result = load_epwsyn_file(path)
    assert result.ok
    assert result.warnings == []
    assert len(result.project.devices) == 1
    assert result.project.devices.get("KOT_KMG1").behavior == "SWITCHED"


def test_device_lookup_and_filter_by_behavior(tmp_path):
    doc = _minimal_valid(devices=[
        {"id": "D1", "designation": "-Y1", "name": "Valve", "behavior": "SWITCHED", "kind": "valve", "publishToHa": False},
        {"id": "D2", "designation": "-B1", "name": "Level", "behavior": "MEASURED", "kind": "level", "publishToHa": True},
        {"id": "D3", "designation": "-B2", "name": "Rain", "behavior": "SIGNAL", "kind": "sensor", "publishToHa": False},
    ])
    path = _write(tmp_path, "three_devices.epwsyn", doc)
    result = load_epwsyn_file(path)
    assert result.ok
    reg = result.project.devices
    assert {d.id for d in reg.all()} == {"D1", "D2", "D3"}
    assert reg.get("D2").name == "Level"
    assert reg.get("MISSING") is None
    assert [d.id for d in reg.by_behavior("SWITCHED")] == ["D1"]
    for behavior in DEVICE_BEHAVIORS:
        assert behavior in reg.count_by_behavior()


# --- Loading a screen must never touch project.json ---------------------

def test_loading_a_synoptic_screen_does_not_touch_project_json(tmp_path):
    project_file = tmp_path / "project.json"
    pm = ProjectManager(str(project_file))
    pm.load_project()          # creates the in-memory default
    pm.save_project()          # and persists it, same as a real session
    before = project_file.read_bytes()

    doc = _minimal_valid()
    screen_path = _write(tmp_path, "screen.epwsyn", doc)
    result = load_epwsyn_file(screen_path)

    assert result.ok
    after = project_file.read_bytes()
    assert before == after
