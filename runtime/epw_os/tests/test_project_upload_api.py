"""Task "wysyłanie projektu na sterownik przez REST" (PROJEKT_EPW_ZADANIA
p. 5): Engineer-token project endpoints, the revision guard, and the
rollback to .bak when the installed file is refused at the next start.
Real ProjectManager on scratch files, real ApiAuth on a scratch token
file, FastAPI TestClient.

Since p. 3a an install REBUILDS the running controller instead of asking
for a restart (EPWCore.reload_project) - the restart is now the fallback
for a reload that did not happen or did not work, and the tests below say
which of the two each request got.
"""
import hashlib
import json
import os
import secrets
import time

os.environ["EPW_TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient

from epw_os.backend.api import app
from epw_os.core import project_format as pf
from epw_os.core.api_auth import ApiAuth
from epw_os.core.events import EventBus
from epw_os.core.project_manager import PENDING_INSTALL_SUFFIX, ProjectManager


class _Audit:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))


class _Core:
    def __init__(self, tmp_path, project_path):
        self.is_running = True
        self.audit_logger = _Audit()
        self.event_bus = EventBus()
        self.restart_requested = None
        self.restarts = []
        config = tmp_path / "api_tokens.local.json"
        self.tokens = {"Operator": secrets.token_hex(16), "Engineer": secrets.token_hex(16)}
        config.write_text(json.dumps({"token_hashes": {
            level: hashlib.sha256(t.encode("utf-8")).hexdigest() for level, t in self.tokens.items()}}))
        self.api_auth = ApiAuth(config_path=str(config))
        self.project_manager = ProjectManager(str(project_path))
        self.project_manager.set_audit_sink(self.audit_logger, lambda: "Engineer")
        self.project_manager.load_project()

        self.reloads = []
        self.reload_succeeds = True

    def request_restart(self, reason, actor="SYSTEM"):
        self.restart_requested = reason
        self.restarts.append((reason, actor))

    def reload_project(self, actor="", level=None):
        """What EPWCore does for real (rebuilds itself from the new
        file) - here only recorded, so these tests stay about the
        ENDPOINT. The rebuild itself is proved in
        test_project_hot_reload.py against a real core."""
        self.reloads.append((actor, level))
        return {"success": self.reload_succeeds,
                "reason": "" if self.reload_succeeds else "the project file was refused",
                "removed_tags": ["ELA1.DI.9"], "issues": [],
                "logic": {"success": True, "reason": ""}}


def _project(name, setting=25.0, revision_saves=1):
    project = pf.new_project(name, author="t")
    project.electrical_protection_stages = [pf.ElectricalProtectionStage(
        function_id="50 Instantaneous Overcurrent", stage_name="Stage 1", enabled=True, setting=setting,
        hysteresis=3.0, delay_ms=150, action="Trip")]
    return project


def _write(project, path, times=1):
    for _ in range(times):
        pf.save_project(project, path)
    return path


@pytest.fixture
def client(tmp_path):
    controller = tmp_path / "controller"
    controller.mkdir()
    running = _write(_project("Running site"), controller / "projekt.epw")
    core = _Core(tmp_path, running)
    app.state.core = core
    return TestClient(app), core, running


def _engineer(core):
    return {"Authorization": f"Bearer {core.tokens['Engineer']}"}


def _operator(core):
    return {"Authorization": f"Bearer {core.tokens['Operator']}"}


# --- reading -----------------------------------------------------------------------

def test_project_header_and_settings_carry_the_settings_hash(client):
    http, core, path = client
    header = http.get("/api/v1/project").json()
    settings = http.get("/api/v1/project/settings").json()
    expected = pf.settings_hash(pf.read_project(path).project)
    assert header["revision"] == 1 and header["settings_hash"] == expected
    assert settings["loaded"] and settings["revision"] == 1 and settings["settings_hash"] == expected
    assert settings["settings"]["electrical_protection_stages/50 Instantaneous Overcurrent / Stage 1/setting"] == 25.0


def test_download_needs_engineer_and_returns_the_file_as_is(client):
    http, core, path = client
    assert http.get("/api/v1/project/file").status_code == 401
    assert http.get("/api/v1/project/file", headers=_operator(core)).status_code == 401
    response = http.get("/api/v1/project/file", headers=_engineer(core))
    assert response.status_code == 200
    assert response.content == path.read_bytes()
    assert response.headers["content-disposition"].endswith('filename="projekt.epw"')
    assert ("API_PROJECT_DOWNLOADED", "API:Engineer", str(path), True) in core.audit_logger.entries
    assert any(e[0] == "API_AUTH_FAILED" and not e[3] for e in core.audit_logger.entries)


# --- installing ---------------------------------------------------------------------

def test_install_replaces_the_file_keeps_a_backup_and_rebuilds_the_controller(client, tmp_path):
    http, core, path = client
    new_path = _write(_project("New design", setting=40.0), tmp_path / "laptop" / "projekt.epw", times=3)
    payload = new_path.read_bytes()

    assert http.post("/api/v1/project/install", content=payload).status_code == 401
    assert http.post("/api/v1/project/install", content=payload, headers=_operator(core)).status_code == 401

    response = http.post("/api/v1/project/install?expected_revision=1", content=payload, headers=_engineer(core))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["installed"] and body["revision"] == 3 and body["previous_revision"] == 1
    assert body["restart_scheduled"] is False, "nothing to restart for - it was rebuilt in place"
    assert body["reloaded"]["success"] is True
    assert body["reloaded"]["removed_tags"] == ["ELA1.DI.9"], "the caller is told what disappeared"
    assert body["actor"] == "API:Engineer"
    assert body["settings_hash"] == pf.settings_hash(pf.read_project(new_path).project)
    assert pf.read_project(path).project.metadata.name == "New design"
    assert pf.read_project(str(path) + ".bak").project.metadata.name == "Running site"
    assert os.path.exists(str(path) + PENDING_INSTALL_SUFFIX)
    assert not [f for f in os.listdir(path.parent) if f.startswith("upload.")]  # the temp upload is gone
    assert ("PROJECT_FILE_INSTALLED", "API:Engineer") == core.audit_logger.entries[-1][:2]

    assert core.reloads == [("API:Engineer", None)]
    time.sleep(0.3)
    assert core.restarts == []


def test_install_without_restart_and_with_a_stale_revision(client, tmp_path):
    http, core, path = client
    payload = _write(_project("New design"), tmp_path / "laptop" / "projekt.epw").read_bytes()

    stale = http.post("/api/v1/project/install?expected_revision=7", content=payload, headers=_engineer(core))
    assert stale.status_code == 409
    detail = stale.json()["detail"]
    assert detail["error"] == "revision_mismatch" and detail["controller"]["revision"] == 1
    assert pf.read_project(path).project.metadata.name == "Running site"
    assert ("API_PROJECT_INSTALL_REFUSED", "API:Engineer", "expected revision 7, controller has 1", False) \
        in core.audit_logger.entries

    ok = http.post("/api/v1/project/install?restart=false", content=payload, headers=_engineer(core))
    assert ok.status_code == 200 and ok.json()["restart_scheduled"] is False
    time.sleep(0.3)
    assert core.restarts == []


def test_install_refuses_junk_and_an_empty_body(client):
    http, core, path = client
    empty = http.post("/api/v1/project/install", content=b"", headers=_engineer(core))
    assert empty.status_code == 400 and empty.json()["detail"]["error"] == "empty_body"
    junk = http.post("/api/v1/project/install", content=b"not a project", headers=_engineer(core))
    assert junk.status_code == 400
    assert junk.json()["detail"]["error"] == "project_refused"
    assert pf.read_project(path).project.metadata.name == "Running site"
    assert not os.path.exists(str(path) + PENDING_INSTALL_SUFFIX)


# --- the next start: rollback --------------------------------------------------------------

def test_a_refused_installed_project_is_rolled_back_at_the_next_start(tmp_path):
    controller = tmp_path / "controller"
    controller.mkdir()
    path = _write(_project("Running site"), controller / "projekt.epw")
    pm = ProjectManager(str(path))
    assert pm.load_project()
    good = _write(_project("New design"), tmp_path / "laptop" / "projekt.epw")
    assert pm.install_project_file(str(good)) == (True, None)
    # The installed file is damaged before the controller comes back up.
    path.write_bytes(b"\x1f\x8b garbage")

    restarted = ProjectManager(str(path))
    assert restarted.load_project() is True
    assert restarted.project.metadata.name == "Running site"
    assert restarted.rolled_back["backup"] == str(path) + ".bak"
    assert os.path.exists(str(path) + ".rejected")
    assert not os.path.exists(str(path) + PENDING_INSTALL_SUFFIX)
    assert restarted.load_error is None

    # A start that loads the installed project fine just drops the marker.
    assert pm.install_project_file(str(good)) == (True, None)
    again = ProjectManager(str(path))
    assert again.load_project() and again.project.metadata.name == "New design"
    assert again.rolled_back is None and not os.path.exists(str(path) + PENDING_INSTALL_SUFFIX)


def test_a_damaged_file_without_a_pending_install_is_not_touched(tmp_path):
    controller = tmp_path / "controller"
    controller.mkdir()
    path = _write(_project("Running site"), controller / "projekt.epw", times=2)  # .bak exists from the 2nd save
    path.write_bytes(b"\x1f\x8b garbage")
    pm = ProjectManager(str(path))
    assert pm.load_project() is False
    assert pm.rolled_back is None and pm.load_error is not None
    assert path.read_bytes() == b"\x1f\x8b garbage"


def test_core_reports_the_rollback_as_a_startup_issue(tmp_path, db):
    from epw_os.core.epw_core import EPWCore
    controller = tmp_path / "controller"
    controller.mkdir()
    path = _write(_project("Running site"), controller / "projekt.epw")
    pm = ProjectManager(str(path))
    pm.load_project()
    assert pm.install_project_file(str(_write(_project("New"), tmp_path / "l" / "projekt.epw"))) == (True, None)
    path.write_bytes(b"\x1f\x8b garbage")

    core = EPWCore()
    core.project_manager.project_file = str(path)
    core.startup()
    try:
        ids = [i["id"] for i in core.startup_issues]
        assert "PROJECT_ROLLED_BACK" in ids and "PROJECT_NOT_LOADED" not in ids
        assert core.project_manager.project.metadata.name == "Running site"
        core.request_restart("test", actor="Engineer")
        assert core.restart_requested == "test"
    finally:
        core.shutdown()


def test_a_reload_that_failed_falls_back_to_the_restart(client, tmp_path):
    """The one case the restart still exists for: the controller could
    not take the new project up in place, so it is asked to come back on
    it instead."""
    http, core, path = client
    core.reload_succeeds = False
    payload = _write(_project("New design"), tmp_path / "laptop" / "projekt.epw").read_bytes()

    body = http.post("/api/v1/project/install", content=payload, headers=_engineer(core)).json()

    assert body["reloaded"]["success"] is False
    assert body["restart_scheduled"] is True
    deadline = time.time() + 5
    while core.restart_requested is None and time.time() < deadline:
        time.sleep(0.05)
    assert core.restarts and core.restarts[0][1] == "API:Engineer"


def test_reload_false_installs_for_the_next_start_as_before(client, tmp_path):
    http, core, path = client
    payload = _write(_project("New design"), tmp_path / "laptop" / "projekt.epw").read_bytes()

    body = http.post("/api/v1/project/install?reload=false&restart=false",
                     content=payload, headers=_engineer(core)).json()

    assert body["reloaded"] is None
    assert core.reloads == []
    assert body["restart_scheduled"] is False
