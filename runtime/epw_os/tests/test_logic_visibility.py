"""The logic program, made visible and replaceable while the controller
runs (task "co mamy do roboty", p. 1).

Executing the user's logic is worth nothing to the person standing at the
cabinet if nothing says whether it is running: /api/v1/health only ever
reported RUNNING/FAULT/DEGRADED for the whole subsystem, which cannot
tell "this project has no logic" from "the program was refused". And a
corrected program meant restarting the controller - for the one part of
projekt.epw that does not need one.
"""
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core import project_format as pf
from epw_os.core.access_manager import AccessLevel
from epw_os.core.epw_core import EPWCore
from epw_os.tests import _logic_program

DI = "ELA1.DI.1"
DO = "ADA1.DO.1"
DO2 = "ADA1.DO.2"


def _write_project(directory: Path, logic_runtime) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    project = pf.new_project("Logic visibility")
    project.cards = [pf.Card(id="ELA1", model="ELA", channel_kinds={"DI": 2}, modbus_unit_id=1),
                     pf.Card(id="ADA1", model="ADA", channel_kinds={"DO": 2}, modbus_unit_id=2)]
    project.points = [pf.Point(address=DI), pf.Point(address="ELA1.DI.2"),
                      pf.Point(address=DO), pf.Point(address=DO2)]
    project.logic_runtime = logic_runtime
    path = directory / "projekt.epw"
    pf.save_project(project, path)
    return path


@pytest.fixture
def core(tmp_path, db):
    instance = EPWCore()
    instance.project_manager.project_file = str(_write_project(tmp_path, _logic_program.di_to_do(DI, DO)))
    instance.startup()
    yield instance
    if instance.is_running:
        instance.shutdown()


# --- what the scan reports ---------------------------------------------------

def test_the_status_says_what_the_scan_is_actually_doing(core):
    status = core.logic_engine.get_status()
    assert status["configured"] is True
    assert status["loaded"] is True
    assert status["running"] is True
    assert status["block_count"] == 2
    assert status["cycle_time_ms"] == 20
    assert status["driven_outputs"] == [DO]
    assert status["last_error"] == ""


def test_a_refused_program_says_why_rather_than_just_being_stopped(tmp_path, db):
    tampered = _logic_program.di_to_do(DI, DO)
    tampered["cycle_time_ms"] = 999  # covered by the checksum
    instance = EPWCore()
    instance.project_manager.project_file = str(_write_project(tmp_path / "bad", tampered))
    instance.startup()
    try:
        status = instance.logic_engine.get_status()
        assert status["configured"] is True
        assert (status["loaded"], status["running"]) == (False, False)
        assert "checksum" in status["last_error"]
    finally:
        instance.shutdown()


# --- reloading the program while the controller runs -------------------------

def test_a_new_program_can_replace_the_running_one_without_a_restart(core, tmp_path):
    """The scan is the only thing that changes - the controller, its
    drivers, its database and its pages keep running."""
    assert core.logic_engine.driven_outputs() == frozenset({DO})

    _write_project(tmp_path, _logic_program.di_to_do(DI, DO2, cycle_time_ms=40))
    result = core.reload_logic(actor="Test", level=AccessLevel.ENGINEER)

    assert result["success"] is True, result["reason"]
    assert core.logic_engine.is_running is True
    assert core.logic_engine.driven_outputs() == frozenset({DO2})
    assert core.logic_engine.get_status()["cycle_time_ms"] == 40
    assert core.is_running is True
    assert core.health_manager.get_health()["LOGIC_RUNTIME"] == "RUNNING"


def test_reloading_is_engineer_only(core):
    result = core.reload_logic(actor="Operator", level=AccessLevel.OPERATOR)
    assert result["success"] is False
    assert "Engineer" in result["reason"]
    # The program that was running is untouched by a refused reload.
    assert core.logic_engine.is_running is True


def test_a_broken_new_program_leaves_the_controller_saying_why(core, tmp_path):
    tampered = _logic_program.di_to_do(DI, DO)
    tampered["project_name"] = "edited after compilation"
    _write_project(tmp_path, tampered)

    result = core.reload_logic(actor="Test", level=AccessLevel.ENGINEER)

    assert result["success"] is False
    assert "checksum" in result["reason"]
    # Fail-safe: the old program is NOT left running either - it was
    # stopped for the swap, and what the panel shows is the truth.
    assert core.logic_engine.is_running is False
    assert core.health_manager.get_health()["LOGIC_RUNTIME"] == "FAULT"


def test_the_reload_is_audited(core, tmp_path):
    _write_project(tmp_path, _logic_program.di_to_do(DI, DO2))
    core.reload_logic(actor="Test", level=AccessLevel.ENGINEER)

    entries = core.audit_logger.query(limit=50)
    assert any(e.event_type == "LOGIC_PROGRAM_RELOADED" for e in entries), [e.event_type for e in entries]


# --- the REST surface --------------------------------------------------------

def test_rest_reports_the_scan(core):
    from fastapi.testclient import TestClient
    from epw_os.backend.api import app
    app.state.core = core

    response = TestClient(app).get("/api/v1/logic")

    assert response.status_code == 200
    body = response.json()
    assert body["running"] is True
    assert body["driven_outputs"] == [DO]


def test_rest_reload_needs_an_engineer_token(core):
    from fastapi.testclient import TestClient
    from epw_os.backend.api import app
    app.state.core = core

    response = TestClient(app).post("/api/v1/logic/reload")

    assert response.status_code == 401
    assert core.logic_engine.is_running is True
