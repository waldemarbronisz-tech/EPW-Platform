"""Task "runtime czyta projekt.epw", etap 1 - the reader both programs use.

Point 1.1: there is ONE implementation of the format (shared/
project_format.py). Studio reaches it through studio/shell/
project_format.py, runtime through runtime/epw_os/core/project_format.py
(loaded by path). The first test proves both handles are that one file,
and that a project Studio saves is read back by runtime's handle with
every structural field intact - no comparison test between two copies is
needed because there is no second copy to compare against.

Point 1.2: validation in the manner of runtime's epwsyn_loader.py -
refusal for a wrong format / newer schema / missing required field (with
the field's name), a warning naming the field for a wrong type, and a
damaged file never raises.
"""
import gzip
import json
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RUNTIME_ROOT = str(_REPO_ROOT / "runtime")
if _RUNTIME_ROOT not in sys.path:
    sys.path.insert(0, _RUNTIME_ROOT)

import shared.project_format as shared_format
import studio.shell.project_format as studio_format
from epw_os.core import project_format as runtime_format
from studio.shell.project_panels import sync_points_for_card


def _write_raw(path: Path, data) -> Path:
    with gzip.open(path, "wb") as f:
        f.write(json.dumps(data).encode("utf-8"))
    return path


def _minimal(**extra) -> dict:
    data = {"format": "EPW_PROJECT_FILE", "schema_version": 1, "project": {"name": "Reader"}}
    data.update(extra)
    return data


def _keys(warnings) -> list:
    return [(w.key, w.params.get("field")) for w in warnings]


def test_studio_and_runtime_share_one_implementation_and_runtime_reads_what_studio_saved(tmp_path):
    assert studio_format.read_project is shared_format.read_project
    assert runtime_format.SHARED_SOURCE_PATH == Path(shared_format.__file__).resolve()
    assert Path(runtime_format.read_project.__code__.co_filename).resolve() == Path(shared_format.__file__).resolve()

    project = studio_format.new_project("Kotłownia", author="W. B.")
    project.modules = ["intrusion", "analog_inputs"]
    project.locations = [studio_format.Location(code="KOT", description="Kotłownia")]
    di = studio_format.Card(id="DI1", model="ELA01", channel_kinds={"DI": 4}, location="KOT")
    do = studio_format.Card(id="DO1", model="ADA01", channel_kinds={"DO": 2})
    for card in (di, do):
        project.cards.append(card)
        sync_points_for_card(project, card)
    project.points[0].description = "Pompa obiegowa - potwierdzenie"
    project.points[0].technical_note = "X2:14, LiYCY 2x0,75"
    project.devices = [studio_format.Device(id="KOT_P1", behavior="SWITCHED", feedback=["DI1.DI.1"],
                                             command=["DO1.DO.1"], safe_state={"onStartup": "OFF"})]
    project.zones = [studio_format.Zone(id="Z1", name="Parter", exit_delay_seconds=45.0)]
    project.lines = [studio_format.Line(id="L1", name="Drzwi", zone_id="Z1", tag="DI1.DI.2")]
    path = tmp_path / "projekt.epw"
    studio_format.save_project(project, path)

    result = runtime_format.read_project(path)

    assert result.ok, result.error
    assert result.warnings == []
    loaded = result.project
    assert [p.address for p in loaded.points] == ["DI1.DI.1", "DI1.DI.2", "DI1.DI.3", "DI1.DI.4", "DO1.DO.1", "DO1.DO.2"]
    assert [asdict(c) for c in loaded.cards] == [asdict(di), asdict(do)]
    assert asdict(loaded.points[0]) == asdict(project.points[0])
    assert asdict(loaded.devices[0]) == asdict(project.devices[0])
    assert asdict(loaded.zones[0]) == asdict(project.zones[0])
    assert loaded.modules == ["intrusion", "analog_inputs"]
    assert loaded.revision == 1 and loaded.modified_by == "studio"


def test_a_file_that_is_not_an_epw_project_is_refused(tmp_path):
    path = _write_raw(tmp_path / "other.epw", {"format": "EPW_PROJECT", "schema_version": 1, "project": {"name": "x"}})
    result = shared_format.read_project(path)
    assert result.ok is False and result.project is None
    assert result.error.key == "wrong_format"


def test_a_newer_schema_version_is_refused_naming_both_versions(tmp_path):
    path = _write_raw(tmp_path / "future.epw", _minimal(schema_version=shared_format.SCHEMA_VERSION + 1))
    result = shared_format.read_project(path)
    assert result.ok is False
    assert result.error.key == "newer_schema"
    assert result.error.params == {"version": shared_format.SCHEMA_VERSION + 1,
                                   "supported": shared_format.SCHEMA_VERSION}
    assert str(shared_format.SCHEMA_VERSION + 1) in str(result.error)


@pytest.mark.parametrize("data, field", [
    ({"format": "EPW_PROJECT_FILE", "project": {"name": "x"}}, "schema_version"),
    ({"format": "EPW_PROJECT_FILE", "schema_version": 1}, "project"),
    (_minimal(project={"author": "nobody"}), "project.name"),
    (_minimal(cards=[{"id": "DI1"}]), "cards[0].model"),
    (_minimal(points=[{"address": "DI1.DI.1"}, {"description": "no address"}]), "points[1].address"),
    (_minimal(devices=[{"id": "Q1"}]), "devices[0].behavior"),
    (_minimal(intrusion={"lines": [{"id": "L1", "name": "Door"}]}), "intrusion.lines[0].zone_id"),
])
def test_a_missing_required_field_is_refused_with_its_name(tmp_path, data, field):
    result = shared_format.read_project(_write_raw(tmp_path / "missing.epw", data))
    assert result.ok is False
    assert result.error.key == "missing_field"
    assert result.error.params["field"] == field
    assert field in str(result.error)


def test_wrong_types_are_warnings_naming_the_field_and_the_rest_still_loads(tmp_path):
    data = _minimal(
        cards=[
            {"id": "DI1", "model": "ELA01", "kind": "DI", "channels": 8},
            {"id": "DI2", "model": "ELA01", "kind": "DI", "channels": "32"},
        ],
        points=[{"address": "DI1.DI.1", "description": 7, "location": None}],
        locations="KOT",
        revision="seven",
    )
    result = shared_format.read_project(_write_raw(tmp_path / "types.epw", data))

    assert result.ok, result.error
    assert _keys(result.warnings) == [
        ("wrong_type_skipped", "cards[1].channels"),
        ("wrong_type_empty", "locations"),
        ("wrong_type_default", "points[0].description"),
        ("wrong_type_default", "revision"),
    ]
    project = result.project
    assert [c.id for c in project.cards] == ["DI1"]
    assert project.points[0].description == ""
    assert project.points[0].location is None
    assert project.locations == []
    assert project.revision == 0
    assert "cards[1].channels" in str(result.warnings[0])


def test_unknown_fields_and_repeated_ids_are_warnings_not_crashes(tmp_path):
    """Before this reader, Card(**record) raised TypeError on any key the
    dataclass did not know - one hand-edited field took the whole file
    (and the program opening it) down."""
    data = _minimal(
        cards=[{"id": "DI1", "model": "ELA01", "kind": "DI", "channels": 8, "colour": "red"},
               {"id": "DI1", "model": "ELA01", "kind": "DI", "channels": 16}],
        gadgets=[],
    )
    result = shared_format.read_project(_write_raw(tmp_path / "extra.epw", data))
    assert result.ok, result.error
    assert _keys(result.warnings) == [
        ("unknown_field", "cards[0].colour"),
        ("duplicate_id", "cards[1].id"),
        ("unknown_field", "gadgets"),
    ]
    assert [(c.id, c.channel_kinds) for c in result.project.cards] == [("DI1", {"DI": 8})]


def _truncated_gzip() -> bytes:
    whole = gzip.compress(json.dumps(_minimal(points=[{"address": f"DI1.DI.{n}"} for n in range(1, 200)])).encode())
    return whole[: len(whole) // 2]


@pytest.mark.parametrize("payload, key", [
    (b"", "not_json"),
    (b"this is not gzip data at all", "unreadable"),
    (_truncated_gzip(), "unreadable"),
    (gzip.compress(b"\xff\xfe\xfa not utf-8"), "not_json"),
    (gzip.compress(b"{\"format\": "), "not_json"),
    (gzip.compress(b"[1, 2, 3]"), "not_object"),
    (gzip.compress(b"{\"format\": \"EPW_PROJECT_FILE\", \"schema_version\": true, \"project\": {}}"), "invalid_required"),
])
def test_a_damaged_file_never_raises(tmp_path, payload, key):
    path = tmp_path / "damaged.epw"
    path.write_bytes(payload)
    result = shared_format.read_project(path)
    assert result.ok is False
    assert result.error.key == key


def test_a_missing_file_is_a_refusal_not_an_exception(tmp_path):
    result = shared_format.read_project(tmp_path / "nowhere.epw")
    assert result.ok is False and result.error.key == "unreadable"


def test_saving_keeps_one_backup_leaves_no_temporary_file_and_records_who_saved(tmp_path):
    path = tmp_path / "projekt.epw"
    project = shared_format.new_project("Backup")
    shared_format.save_project(project, path)
    shared_format.save_project(project, path, modified_by="panel")

    assert sorted(p.name for p in tmp_path.iterdir()) == ["projekt.epw", "projekt.epw.bak"]
    current = shared_format.read_project(path).project
    previous = shared_format.read_project(Path(str(path) + ".bak")).project
    assert (current.revision, current.modified_by) == (2, "panel")
    assert (previous.revision, previous.modified_by) == (1, "studio")
