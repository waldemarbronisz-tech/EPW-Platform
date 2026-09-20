"""Replacing a controller, end to end, against a real core.

test_controller_backup.py proves what a bundle contains. This proves
the thing that actually matters: take a backup from a running
controller, put it on a different one, and the second controller is
running the first one's installation - project, counters, arming state,
alarm memory - without a restart, and says exactly which secrets nobody
can restore for it.
"""
import hashlib
import json
import os
import secrets as secrets_module
import sys
from pathlib import Path

os.environ["EPW_TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.backend.api import app
from epw_os.core import project_format as pf
from epw_os.core.access_manager import AccessLevel
from epw_os.core.api_auth import ApiAuth
from epw_os.core.epw_core import EPWCore
from epw_os.core.feature_config import TOGGLABLE_FEATURES

POINT = "ELA1.DI.1"


def _project(name, zone="Hala"):
    project = pf.new_project(name, author="t")
    project.modules = list(TOGGLABLE_FEATURES)
    project.cards.append(pf.Card(id="ELA1", model="ELA01", channel_kinds={"DI": 4}))
    for channel in range(1, 5):
        project.points.append(pf.Point(address=f"ELA1.DI.{channel}"))
    project.zones.append(pf.Zone(id="Z1", name=zone))
    project.intrusion_users.append(pf.IntrusionUser(id="U1", name="Kowalski",
                                                     level=AccessLevel.OPERATOR))
    return project


def _core(tmp_path, name):
    """A controller with its OWN secret files.

    The secrets do not live next to projekt.epw - they sit in
    epw_os/config/, one set per installed controller, so two cores in
    one test process would otherwise share them and "the code did not
    travel" would pass for the wrong reason. Each manager reads its
    path once, at construction, from an environment variable."""
    directory = tmp_path / name
    directory.mkdir()
    pf.save_project(_project(name), directory / "projekt.epw")
    previous = {key: os.environ.get(key) for key in ("EPW_ACCESS_FILE", "EPW_API_TOKENS_FILE")}
    os.environ["EPW_ACCESS_FILE"] = str(directory / "access.local.json")
    os.environ["EPW_API_TOKENS_FILE"] = str(directory / "api_tokens.local.json")
    try:
        core = EPWCore()
        core.project_manager.project_file = str(directory / "projekt.epw")
        core.startup()
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    return core, directory


def _tokens(core, tmp_path, name):
    config = tmp_path / f"{name}-tokens.json"
    tokens = {"Operator": secrets_module.token_hex(16), "Engineer": secrets_module.token_hex(16)}
    config.write_text(json.dumps({"token_hashes": {
        level: hashlib.sha256(value.encode()).hexdigest() for level, value in tokens.items()}}))
    core.api_auth = ApiAuth(config_path=str(config))
    return tokens


@pytest.fixture
def original(tmp_path, db):
    core, directory = _core(tmp_path, "original")
    tokens = _tokens(core, tmp_path, "original")
    yield core, directory, tokens
    core.shutdown()


@pytest.fixture
def replacement(tmp_path, db):
    """A second controller, with a DIFFERENT project on it - the real
    case is a spare from the shelf, not a clone."""
    core, directory = _core(tmp_path, "replacement")
    tokens = _tokens(core, tmp_path, "replacement")
    yield core, directory, tokens
    core.shutdown()


def _client(core):
    app.state.core = core
    return TestClient(app)


def _engineer(tokens):
    return {"Authorization": f"Bearer {tokens['Engineer']}"}


def _operator(tokens):
    return {"Authorization": f"Bearer {tokens['Operator']}"}


# --- taking a backup ----------------------------------------------------------

def test_a_backup_needs_an_engineer_token(original):
    core, _dir, tokens = original
    http = _client(core)

    assert http.get("/api/v1/controller/backup").status_code == 401
    assert http.get("/api/v1/controller/backup", headers=_operator(tokens)).status_code == 401
    assert http.get("/api/v1/controller/backup", headers=_engineer(tokens)).status_code == 200


def test_a_backup_comes_back_as_a_file_and_is_written_to_the_audit_log(original):
    core, _dir, tokens = original
    http = _client(core)

    response = http.get("/api/v1/controller/backup", headers=_engineer(tokens))

    assert response.headers["content-type"] == "application/gzip"
    assert ".epwbak" in response.headers["content-disposition"]
    assert len(response.content) > 100
    from epw_os.db.database import SessionLocal
    from epw_os.db.models import AuditLog
    session = SessionLocal()
    try:
        assert session.query(AuditLog).filter(
            AuditLog.event_type == "CONTROLLER_BACKUP_TAKEN").count() == 1
    finally:
        session.close()


def test_a_bundle_can_be_inspected_before_anybody_applies_it(original):
    core, _dir, tokens = original
    http = _client(core)
    core.intrusion_manager.arm_zone("Z1", actor="test")
    bundle = http.get("/api/v1/controller/backup", headers=_engineer(tokens)).content

    body = http.post("/api/v1/controller/backup/inspect", content=bundle,
                     headers=_engineer(tokens)).json()

    assert body["summary"]["project_name"] == "original"
    assert body["summary"]["armed_zones"] == ["Z1"]
    assert isinstance(body["checklist"], list)


# --- the whole point: replacing a controller ----------------------------------

def test_a_replacement_comes_up_running_the_originals_installation(original, replacement):
    """The case this feature exists for: the card died, there is a spare
    controller, and everything that lived only on that card has to come
    back."""
    core, _dir, tokens = original
    core.intrusion_manager.arm_zone("Z1", actor="test")
    bundle = _client(core).get("/api/v1/controller/backup", headers=_engineer(tokens)).content

    spare, spare_dir, spare_tokens = replacement
    assert spare.project_manager.get_project_header()["name"] == "replacement"

    body = _client(spare).post("/api/v1/controller/restore", content=bundle,
                               headers=_engineer(spare_tokens)).json()

    assert body["success"] is True
    assert spare.project_manager.get_project_header()["name"] == "original"
    assert spare.restart_requested in (None, "", False), "a restore needs no restart"
    assert spare.is_running is True
    assert [zone["name"] for zone in spare.intrusion_manager.get_zones()] == ["Hala"]


def test_the_arming_state_comes_back_the_way_it_was_left(original, replacement):
    """The one thing the contract names explicitly: a zone that was
    armed comes back armed. A controller that comes back disarmed is
    lying about the building."""
    core, _dir, tokens = original
    core.intrusion_manager.arm_zone("Z1", actor="test")
    bundle = _client(core).get("/api/v1/controller/backup", headers=_engineer(tokens)).content

    spare, _spare_dir, spare_tokens = replacement
    _client(spare).post("/api/v1/controller/restore", content=bundle, headers=_engineer(spare_tokens))

    from epw_os.core.intrusion_manager import ZoneState
    assert spare.intrusion_manager.get_zone_state("Z1") == ZoneState.ARMED


def test_the_restore_hands_over_the_list_of_what_it_could_not_do(original, replacement):
    core, _dir, tokens = original
    core.access_manager.set_user_pin("U1", "4711", level=AccessLevel.ENGINEER)
    bundle = _client(core).get("/api/v1/controller/backup", headers=_engineer(tokens)).content

    spare, _spare_dir, spare_tokens = replacement
    body = _client(spare).post("/api/v1/controller/restore", content=bundle,
                               headers=_engineer(spare_tokens)).json()

    people = [item for item in body["checklist"] if item["kind"] == "user"]
    assert any(item["detail"] == "Kowalski" and "code" in item["needs"] for item in people)
    assert any("access.local.json" == item["what"] for item in body["skipped"])


def test_no_secret_of_the_original_reaches_the_replacement(original, replacement):
    """The rule the design turns on, checked where it matters: after a
    full restore, the original's keypad code does not work on the
    replacement."""
    core, _dir, tokens = original
    core.access_manager.set_user_pin("U1", "4711", level=AccessLevel.ENGINEER)
    assert core.access_manager.attempt_user_login("4711") is not None
    bundle = _client(core).get("/api/v1/controller/backup", headers=_engineer(tokens)).content

    spare, _spare_dir, spare_tokens = replacement
    _client(spare).post("/api/v1/controller/restore", content=bundle, headers=_engineer(spare_tokens))

    assert spare.access_manager.attempt_user_login("4711") is None, \
        "a code travelled in the bundle"
    assert any(user["name"] == "Kowalski" for user in spare.access_manager.get_users()), \
        "but the person exists, ready for a code to be set"


# --- refusals ------------------------------------------------------------------

def test_a_damaged_bundle_is_refused_without_touching_anything(replacement):
    spare, _spare_dir, spare_tokens = replacement
    before = spare.project_manager.get_project_header()["name"]

    response = _client(spare).post("/api/v1/controller/restore", content=b"not a backup",
                                   headers=_engineer(spare_tokens))

    assert response.status_code == 400
    assert "readable" in response.json()["detail"]["reason"]
    assert spare.project_manager.get_project_header()["name"] == before


def test_a_restore_needs_an_engineer_token(original, replacement):
    core, _dir, tokens = original
    bundle = _client(core).get("/api/v1/controller/backup", headers=_engineer(tokens)).content
    spare, _spare_dir, spare_tokens = replacement
    http = _client(spare)

    assert http.post("/api/v1/controller/restore", content=bundle).status_code == 401
    assert http.post("/api/v1/controller/restore", content=bundle,
                     headers=_operator(spare_tokens)).status_code == 401


def test_an_empty_body_is_refused(replacement):
    spare, _spare_dir, spare_tokens = replacement
    response = _client(spare).post("/api/v1/controller/restore", content=b"",
                                   headers=_engineer(spare_tokens))
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "empty_body"
