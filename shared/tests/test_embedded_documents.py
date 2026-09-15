"""Task "Studio osadza ekrany i logikę w projekt.epw" - the format side:
`screens`, `logic` and `logic_runtime` are sections of projekt.epw,
kept verbatim, omitted when empty, tolerated when malformed (a warning
and empty, like every other section), invisible to a file saved before
they existed."""
import gzip
import json

import shared.project_format as pf


def _screens():
    return {"format": "EPW_SYNOPTIC", "schema_version": 2, "project": {"name": "Kotlownia"},
            "canvas": {"width": 1920, "height": 1080}, "objects": [{"id": "o1", "type": "water.ball_valve"}]}


def _logic():
    return {"format": "EPW_LOGIC", "schema_version": 3, "settings": {}, "blocks": [{"id": "b1"}], "wires": []}


def _runtime():
    return {"format": "EPW_RUNTIME_LOGIC", "blocks": [], "execution_order": []}


def test_the_three_documents_round_trip_verbatim(tmp_path):
    p = pf.new_project("T")
    p.screens, p.logic, p.logic_runtime = _screens(), _logic(), _runtime()
    path = tmp_path / "p.epw"
    pf.save_project(p, path)
    loaded = pf.load_project(path)
    assert loaded.screens == _screens()
    assert loaded.logic == _logic()
    assert loaded.logic_runtime == _runtime()


def test_empty_documents_are_omitted_from_the_file(tmp_path):
    p = pf.new_project("T")
    path = tmp_path / "p.epw"
    pf.save_project(p, path)
    with gzip.open(path, "rt", encoding="utf-8") as f:
        data = json.load(f)
    assert "screens" not in data and "logic" not in data and "logic_runtime" not in data


def test_a_file_from_before_the_task_loads_with_empty_documents(tmp_path):
    data = {"format": "EPW_PROJECT_FILE", "schema_version": 2, "project": {"name": "old"}}
    path = tmp_path / "old.epw"
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(data, f)
    result = pf.read_project(path)
    assert result.ok and result.warnings == []
    assert (result.project.screens, result.project.logic, result.project.logic_runtime) == ({}, {}, {})


def test_a_malformed_section_is_a_warning_and_empty_not_a_refusal(tmp_path):
    data = {"format": "EPW_PROJECT_FILE", "schema_version": 2, "project": {"name": "x"},
            "screens": "not an object", "logic": 7}
    path = tmp_path / "bad.epw"
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(data, f)
    result = pf.read_project(path)
    assert result.ok
    assert sorted((w.key, w.params["field"]) for w in result.warnings) == [
        ("wrong_type_empty", "logic"), ("wrong_type_empty", "screens"),
    ]
    assert result.project.screens == {} and result.project.logic == {}
