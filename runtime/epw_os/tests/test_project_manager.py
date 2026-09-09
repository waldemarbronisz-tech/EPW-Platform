"""Tests for ProjectManager file operations that back the File menu."""

import json
import os

import pytest

from epw_os.core.project_manager import ProjectManager


@pytest.fixture
def pm(tmp_path):
    manager = ProjectManager(str(tmp_path / "project.json"))
    manager.load_project()  # no file -> in-memory default
    return manager


def _valid_project(project_id="EXTERNAL"):
    return {
        "format": "EPW_OS_PROJECT",
        "schema_version": 1,
        "project_id": project_id,
    }


def test_fresh_default_project_is_clean(pm):
    assert not pm.is_dirty()


def test_edit_marks_dirty_and_save_clears_it(pm):
    pm.config["project_id"] = "SITE_A"
    assert pm.is_dirty()
    pm.save_project()
    assert not pm.is_dirty()
    assert os.path.exists(pm.project_file)


def test_new_project_is_dirty_until_saved(pm):
    pm.config["project_id"] = "SITE_A"
    pm.save_project()
    pm.new_project()
    assert pm.is_dirty()
    assert pm.config["project_id"] == "DEFAULT_PROJECT"


def test_save_project_as_moves_active_file(pm, tmp_path):
    target = str(tmp_path / "renamed.json")
    pm.save_project_as(target)
    assert pm.project_file == target
    assert os.path.exists(target)
    assert not pm.is_dirty()


def test_load_from_valid_makes_it_active(pm, tmp_path):
    ext = tmp_path / "ext.json"
    ext.write_text(json.dumps(_valid_project("FROM_DISK")), encoding="utf-8")
    assert pm.load_from(str(ext))
    assert pm.config["project_id"] == "FROM_DISK"
    assert pm.project_file == str(ext)
    assert not pm.is_dirty()


def test_load_from_invalid_is_rejected(pm, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"not": "a project"}), encoding="utf-8")
    assert pm.load_from(str(bad)) is False


# --- Acceptance-review finding: a CORRUPTED (not just wrong-shape) file
# used to crash the whole program - _read() called json.load() with no
# exception handling at all, so a truncated/malformed project.json (a
# very real scenario on an embedded deployment: power loss mid-write,
# a full SD card) raised an unhandled JSONDecodeError straight out of
# load_project()/load_from()/import_from(), before there was even a
# window to show an error in. Found by actually constructing a
# ProjectManager against a garbage file and calling load_project() -
# not just by reading the code. Fixed: _read() now catches
# JSONDecodeError/UnicodeDecodeError/OSError and returns None, treated
# by every caller exactly like _is_valid() already treats a
# wrong-shape-but-parseable file (logged, existing config kept,
# returns False) - never raises.

def test_load_project_with_malformed_json_does_not_raise(tmp_path):
    bad_path = tmp_path / "project.json"
    bad_path.write_text("{ this is not valid json !!!", encoding="utf-8")
    manager = ProjectManager(str(bad_path))
    assert manager.load_project() is False
    assert manager.config == {}  # unchanged from __init__, not crashed


def test_load_from_with_malformed_json_is_rejected_not_raised(pm, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ this is not valid json !!!", encoding="utf-8")
    assert pm.load_from(str(bad)) is False


def test_import_from_with_malformed_json_is_rejected_not_raised(pm, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ this is not valid json !!!", encoding="utf-8")
    assert pm.import_from(str(bad)) is False


def test_import_keeps_active_file_but_pulls_contents(pm, tmp_path):
    active = pm.project_file
    src = tmp_path / "incoming.json"
    src.write_text(json.dumps(_valid_project("IMPORTED")), encoding="utf-8")
    assert pm.import_from(str(src))
    assert pm.config["project_id"] == "IMPORTED"
    assert pm.project_file == active
    assert os.path.exists(active)  # persisted to the active file
    assert not pm.is_dirty()


def test_import_invalid_is_rejected(pm, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    assert pm.import_from(str(bad)) is False


def test_export_writes_backup_without_touching_active_project(pm, tmp_path):
    pm.config["project_id"] = "SITE_A"
    pm.save_project()
    backup = str(tmp_path / "backup.json")
    pm.export_to(backup)
    assert os.path.exists(backup)
    with open(backup, encoding="utf-8") as f:
        assert json.load(f)["project_id"] == "SITE_A"
    assert not pm.is_dirty()


def test_language_accessors(pm):
    assert pm.get_language() == "en"
    pm.set_language("pl")
    assert pm.get_language() == "pl"
    assert pm.config["language"] == "pl"


def test_analog_config_round_trips_through_save_and_reload(pm):
    assert pm.get_analog_configs() == {}
    config = {
        "signal_type": "4-20mA", "raw_min": 4.0, "raw_max": 20.0,
        "eng_min": 0.0, "eng_max": 100.0, "unit": "°C", "decimals": 1,
    }
    pm.set_analog_config("AI1", config)
    assert pm.get_analog_configs()["AI1"] == config
    pm.save_project()

    reloaded = ProjectManager(pm.project_file)
    reloaded.load_project()
    assert reloaded.get_analog_configs()["AI1"] == config


def test_analog_config_is_independent_per_channel(pm):
    pm.set_analog_config("AI1", {"unit": "°C"})
    pm.set_analog_config("AI2", {"unit": "bar"})
    configs = pm.get_analog_configs()
    assert configs["AI1"]["unit"] == "°C"
    assert configs["AI2"]["unit"] == "bar"
    assert len(configs) == 2


# --- Project metadata (Task: Project menu > Properties) --------------------

def test_metadata_defaults_when_missing(pm):
    assert pm.get_metadata() == {
        "name": "", "description": "", "location": "", "author": "",
        "created": None, "modified": None,
    }


def test_set_metadata_stamps_created_once(pm):
    pm.set_metadata(name="Substation A", description="Test", location="Building 3", author="J. Kowalski")
    meta = pm.get_metadata()
    assert meta["name"] == "Substation A"
    assert meta["description"] == "Test"
    assert meta["location"] == "Building 3"
    assert meta["author"] == "J. Kowalski"
    assert meta["created"] is not None
    created_first = meta["created"]

    pm.set_metadata(name="Substation A (renamed)")
    meta2 = pm.get_metadata()
    assert meta2["created"] == created_first, "created must never change once it's set (task: 'ustawiana raz')"
    assert meta2["name"] == "Substation A (renamed)"


def test_touch_metadata_modified_updates_modified_and_backfills_created(pm):
    assert pm.get_metadata()["modified"] is None
    pm.touch_metadata_modified()
    meta = pm.get_metadata()
    assert meta["modified"] is not None
    assert meta["created"] is not None, "the first-ever touch must also backfill created"
    created_first = meta["created"]

    pm.touch_metadata_modified()
    meta2 = pm.get_metadata()
    assert meta2["created"] == created_first, "created must not change on a later touch"


def test_metadata_persists_through_save_and_reload(pm):
    pm.set_metadata(name="Substation A", description="Desc", location="Loc", author="Author")
    pm.touch_metadata_modified()
    pm.save_project()

    reloaded = ProjectManager(pm.project_file)
    reloaded.load_project()
    meta = reloaded.get_metadata()
    assert meta["name"] == "Substation A"
    assert meta["description"] == "Desc"
    assert meta["location"] == "Loc"
    assert meta["author"] == "Author"
    assert meta["created"] is not None
    assert meta["modified"] is not None


def test_old_format_project_without_metadata_loads_and_reads_fine(tmp_path):
    """DOWÓD: a project.json from before this feature existed (no
    "metadata" key at all, not even an empty one) must load with no
    error, and get_metadata() must return sensible empty defaults rather
    than raising - no migration step required."""
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps({
        "format": "EPW_OS_PROJECT", "schema_version": 1, "project_id": "LEGACY_SITE",
    }), encoding="utf-8")
    manager = ProjectManager(str(path))
    assert manager.load_project() is True
    assert manager.config["project_id"] == "LEGACY_SITE"
    assert "metadata" not in manager.config, "must not silently add a metadata key just by loading/reading"
    meta = manager.get_metadata()
    assert meta == {
        "name": "", "description": "", "location": "", "author": "",
        "created": None, "modified": None,
    }
    # Saving an old-format project afterwards must not error either.
    manager.save_project()
    with open(path, encoding="utf-8") as f:
        on_disk = json.load(f)
    assert on_disk["project_id"] == "LEGACY_SITE"
