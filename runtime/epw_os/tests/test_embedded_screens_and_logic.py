"""Task "Studio osadza ekrany i logikę w projekt.epw" - the runtime side:
the compiled logic and the screens come out of projekt.epw itself
(Project.logic_runtime / Project.screens); the .epwlogic.runtime.json /
.epwsyn paths in controller.local.json are only the fallback for a
project saved before that task. Same harness as test_runtime_reads_project.
"""
import json

import pytest

from epw_os.core.composition_check import find_signals_outside_composition
from epw_os.core.epwsyn_loader import load_epwsyn_data, load_epwsyn_file
from epw_os.core.logic_engine import LogicEngine
from epw_os.tests import _logic_program


def _runtime_logic(tags):
    """A logic DOCUMENT for the composition check, which only ever reads
    the raw JSON looking for signal names (see composition_check.py) -
    deliberately not a runnable program: the tags below are exactly the
    "signals that are not in this controller" the check exists to find.
    Anything that has to actually RUN uses _logic_program.py instead,
    which builds a real, checksum-signed export out of the shared block
    library."""
    return {"format": "EPW_RUNTIME_LOGIC", "schema_version": 1, "blocks": [{"id": "b", "inputs": tags}],
            "execution_order": ["b"]}


def _screens():
    return {"format": "EPW_SYNOPTIC", "schema_version": 2, "project": {"name": "S"},
            "canvas": {"width": 1920, "height": 1080},
            "objects": [{"id": "o1", "type": "scada.indicator", "tag": "Security.Zone1.Armed"}],
            "devices": []}


# --- LogicEngine ---------------------------------------------------------------

def test_logic_engine_loads_the_embedded_program():
    engine = LogicEngine(tag_manager=None)
    assert engine.load_program_data(_logic_program.di_to_do()) is True
    assert engine.load_program_data({"format": "EPW_LOGIC"}) is False
    assert engine.load_program_data("not a dict") is False
    # The marker alone is no longer enough: a document that cannot become
    # a runnable program is refused, not accepted and quietly not run.
    assert engine.load_program_data(_runtime_logic([])) is False


def test_logic_engine_file_path_still_goes_through_the_same_acceptance(tmp_path):
    path = tmp_path / "x.epwlogic.runtime.json"
    path.write_text(json.dumps(_logic_program.di_to_do()), encoding="utf-8")
    assert LogicEngine(tag_manager=None).load_program(str(path)) is True


# --- epwsyn loader -----------------------------------------------------------------

def test_epwsyn_loader_validates_an_embedded_document_like_a_file(tmp_path):
    from_data = load_epwsyn_data(_screens())
    path = tmp_path / "s.epwsyn"
    path.write_text(json.dumps(_screens()), encoding="utf-8")
    from_file = load_epwsyn_file(str(path))
    assert from_data.ok and from_file.ok
    assert len(from_data.project.objects) == len(from_file.project.objects) == 1
    assert load_epwsyn_data({"format": "WRONG"}).ok is False
    assert load_epwsyn_data([]).ok is False


# --- composition check ----------------------------------------------------------------

def test_composition_check_reads_the_embedded_sections_first():
    disabled = {"intrusion": False, "protection_process": False, "analog_inputs": False}
    issues = find_signals_outside_composition(
        disabled, logic_file=None, synoptic_file=None,
        logic_data=_runtime_logic(["Security.Zone1.Armed"]), screens_data=_screens(),
    )
    kinds = sorted((i.module, i.source_kind, i.path) for i in issues)
    assert kinds == [
        ("intrusion", "logic", "projekt.epw#logic_runtime"),
        ("intrusion", "screen", "projekt.epw#screens"),
    ]


def test_composition_check_falls_back_to_the_files_when_nothing_is_embedded(tmp_path):
    logic_path = tmp_path / "l.json"
    logic_path.write_text(json.dumps(_runtime_logic(["Security.Zone1.Armed"])), encoding="utf-8")
    issues = find_signals_outside_composition({"intrusion": False}, logic_file=str(logic_path), synoptic_file=None,
                                              logic_data={}, screens_data={})
    assert [(i.module, i.source_kind, i.path) for i in issues] == [("intrusion", "logic", str(logic_path))]


# --- the whole core -------------------------------------------------------------------

@pytest.fixture
def start_core(db):
    cores = []

    def _start(project_path):
        from epw_os.core.epw_core import EPWCore
        core = EPWCore()
        core.project_manager.project_file = str(project_path)
        core.startup()
        cores.append(core)
        return core

    yield _start
    for core in cores:
        if core.is_running:
            core.shutdown()


def test_core_runs_the_logic_embedded_in_projekt_epw(tmp_path, start_core):
    from epw_os.core import project_format as pf
    project = pf.new_project("Embedded", author="Test")
    project.logic_runtime = _logic_program.di_to_do()
    project.screens = _screens()
    path = tmp_path / "projekt.epw"
    pf.save_project(project, path)

    core = start_core(path)

    assert core.logic_engine.is_running is True
    assert core.logic_engine._project["format"] == "EPW_RUNTIME_LOGIC"
    assert core.project_manager.get_embedded_screens()["objects"][0]["id"] == "o1"
    # The screens reference Security.* while intrusion is not in the
    # composition - reported from the embedded section, not from a file.
    assert any(i["id"] == "COMPOSITION_INTRUSION_SCREEN" for i in core.startup_issues)
