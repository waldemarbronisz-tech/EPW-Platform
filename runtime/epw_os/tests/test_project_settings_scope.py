"""Decided 2026-09-18 (ZADANIA p. 6, "Ustawienia sterownika spoza
formatu"): the MQTT integration and the service notes are SETTINGS of the
project - runtime reads them from projekt.epw, a panel change (the MQTT
dialog, a note added at the cabinet) goes back into the file as revision
+1 by "panel", and Studio can read everything else the controller holds
through GET /api/v1/controller/settings. Counters can be zeroed from
Studio through POST /api/v1/counters/<tag>/reset (Engineer)."""
import hashlib
import json
import os
import secrets
import sys
from pathlib import Path

os.environ["EPW_TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.backend.api import app  # noqa: E402
from epw_os.core import project_format as pf  # noqa: E402
from epw_os.core.api_auth import ApiAuth  # noqa: E402
from epw_os.core.events import EventBus  # noqa: E402
from epw_os.core.project_epw import MQTT_SETTINGS, SERVICE_NOTE_SETTINGS, apply_changes, diff_settings  # noqa: E402
from epw_os.core.project_manager import ProjectManager  # noqa: E402
from epw_os.core.service_notes import ServiceNoteManager  # noqa: E402
from epw_os.core.switching_counters import SwitchingCounterManager  # noqa: E402


def _project(directory: Path) -> Path:
    from studio.shell.project_format import Card, Location, new_project, save_project
    from studio.shell.project_panels import sync_points_for_card
    directory.mkdir(parents=True, exist_ok=True)
    project = new_project("Scope", author="Test")
    project.modules = ["switching_counters", "service_notes"]
    project.locations = [Location("KOT", "Kotlownia")]
    card = Card("ELA1", "ELA", channel_kinds={"DI": 2}, location="KOT", modbus_unit_id=1)
    project.cards.append(card)
    sync_points_for_card(project, card)
    project.mqtt.enabled = True
    project.mqtt.host = "haos.local"
    project.mqtt.topic_prefix = "epw/site"
    project.mqtt.link_in = [{"topic": "home/pump", "tag": "Link.HA.In1", "type": "BOOL", "stale_after_s": 30}]
    project.service_notes = {"ELA1.DI.1": [{"text": "contact set replaced", "timestamp": 1758000000.0,
                                            "author_level": "Engineer"}]}
    path = directory / "projekt.epw"
    save_project(project, path)
    return path


class _Audit:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))


def _manager(path: Path) -> ProjectManager:
    pm = ProjectManager(str(path))
    pm.set_audit_sink(_Audit(), lambda: "Engineer")
    pm.load_project()
    return pm


# --- the settings live in the project ----------------------------------------------------

def test_the_field_lists_agree_with_the_shared_format():
    assert pf.SETTING_FIELDS["mqtt"] == MQTT_SETTINGS
    assert pf.SETTING_FIELDS["service_notes"] == SERVICE_NOTE_SETTINGS


def test_runtime_reads_mqtt_and_notes_from_the_project_not_the_local_file(tmp_path):
    path = _project(tmp_path)
    (tmp_path / "controller.local.json").write_text(json.dumps({
        "format": "EPW_CONTROLLER_SETTINGS", "schema_version": 1, "language": "pl",
        "mqtt": {"enabled": False, "host": "old.local"},           # a file from before the move - ignored
        "service_notes": {"ELA1.DI.1": [{"text": "stale", "timestamp": 1.0, "author_level": "Operator"}]},
    }), encoding="utf-8")
    pm = _manager(path)
    mqtt = pm.get_mqtt_config()
    assert mqtt["enabled"] is True and mqtt["host"] == "haos.local" and mqtt["topic_prefix"] == "epw/site"
    assert mqtt["link_in"] == [{"topic": "home/pump", "tag": "Link.HA.In1", "type": "BOOL", "stale_after_s": 30}]
    assert "password" not in mqtt
    assert pm.get_service_notes() == {"ELA1.DI.1": [{"text": "contact set replaced", "timestamp": 1758000000.0,
                                                     "author_level": "Engineer"}]}
    assert pm.get_language() == "pl"
    local = pm.local_settings()
    assert local["language"] == "pl" and "mqtt" not in local and "service_notes" not in local


def test_the_mqtt_dialogs_change_goes_back_into_projekt_epw_as_a_setting(tmp_path):
    path = _project(tmp_path)
    pm = _manager(path)
    config = pm.get_mqtt_config()
    config.update({"host": "broker.lan", "port": 8883, "tls": True, "password": "never"})
    pm.set_mqtt_config(config)
    assert pm.save_project()
    saved = pf.load_project(path)
    assert saved.revision == 2 and saved.modified_by == "panel"
    assert saved.mqtt.host == "broker.lan" and saved.mqtt.port == 8883 and saved.mqtt.tls is True
    assert "password" not in json.dumps(pf.settings_snapshot(saved))
    audited = [e for e in pm._audit_logger.entries if e[0] == "PROJECT_SETTING_CHANGED"]
    assert {e[2].split(":")[0] for e in audited} == {"mqtt[broker].host", "mqtt[broker].port", "mqtt[broker].tls"}
    assert (tmp_path / "controller.local.json").exists() is False or \
        "mqtt" not in json.loads((tmp_path / "controller.local.json").read_text(encoding="utf-8"))


def test_a_note_added_at_the_cabinet_is_written_to_the_project_immediately(tmp_path):
    path = _project(tmp_path)
    pm = _manager(path)
    notes = ServiceNoteManager(pm)
    assert notes.add_note("ELA1.DI.2", "pitting visible on contact", "Operator", timestamp=1758100000.0)
    saved = pf.load_project(path)
    assert saved.revision == 2 and saved.modified_by == "panel"
    assert [n["text"] for n in saved.service_notes["ELA1.DI.2"]] == ["pitting visible on contact"]
    assert [n["text"] for n in saved.service_notes["ELA1.DI.1"]] == ["contact set replaced"]   # untouched
    audit = [e[2] for e in pm._audit_logger.entries if e[0] == "PROJECT_SETTING_CHANGED"]
    assert audit == ["service_notes[ELA1.DI.2].notes: 0 -> 1 entries (projekt.epw revision 2)"]
    assert pf.settings_snapshot(saved)["service_notes/ELA1.DI.2/notes"][0]["author_level"] == "Operator"


def test_diff_and_apply_treat_mqtt_and_notes_as_settings_never_structure():
    from studio.shell.project_format import new_project
    project = new_project("Scope", author="t")
    project.mqtt.host = "a"
    from epw_os.core.project_epw import build_project_view
    config = build_project_view(project)
    config["mqtt"] = {**config["mqtt"], "host": "b", "deadband_per_tag": {"ELA1.AI.1": 0.5}}
    config["service_notes"] = {"X": [{"text": "t", "timestamp": 1.0, "author_level": "Engineer"}]}
    diff = diff_settings(project, config)
    assert diff.structural == []
    assert sorted(c.describe() for c in diff.changes) == [
        "mqtt[broker].deadband_per_tag: {} -> {'ELA1.AI.1': 0.5}", "mqtt[broker].host: 'a' -> 'b'",
        "service_notes[X].notes: 0 -> 1 entries"]
    apply_changes(project, diff.changes)
    assert project.mqtt.host == "b" and project.mqtt.deadband_per_tag == {"ELA1.AI.1": 0.5}
    assert project.service_notes["X"][0]["text"] == "t"
    bad = build_project_view(project)
    bad["mqtt"] = "not a dict"
    assert diff_settings(project, bad).structural == ["mqtt"]


# --- REST: what Studio can read and do -----------------------------------------------------

class _Core:
    def __init__(self, tmp_path, project_path):
        self.is_running = True
        self.audit_logger = _Audit()
        self.event_bus = EventBus()
        config = tmp_path / "api_tokens.local.json"
        self.tokens = {"Operator": secrets.token_hex(16), "Engineer": secrets.token_hex(16)}
        config.write_text(json.dumps({"token_hashes": {
            level: hashlib.sha256(t.encode("utf-8")).hexdigest() for level, t in self.tokens.items()}}))
        self.api_auth = ApiAuth(config_path=str(config))
        self.project_manager = ProjectManager(str(project_path))
        self.project_manager.set_audit_sink(self.audit_logger, lambda: "Engineer")
        self.project_manager.load_project()
        self.switching_counters = SwitchingCounterManager(self.event_bus, self.project_manager)


@pytest.fixture
def client(tmp_path):
    path = _project(tmp_path / "controller")
    core = _Core(tmp_path, path)
    app.state.core = core
    return TestClient(app), core, path


def _engineer(core):
    return {"Authorization": f"Bearer {core.tokens['Engineer']}"}


def test_studio_reads_the_controller_local_settings_and_the_project_settings_carry_mqtt_and_notes(client, tmp_path):
    http, core, path = client
    (tmp_path / "controller" / "controller.local.json").write_text(json.dumps({
        "format": "EPW_CONTROLLER_SETTINGS", "schema_version": 1, "language": "pl", "api_port": 8010,
        "historian_retention": {"max_days": 30}}), encoding="utf-8")
    core.project_manager.load_project()
    body = http.get("/api/v1/controller/settings").json()
    assert body["source"] == "controller.local.json" and body["language"] == "pl"
    assert body["settings"]["api_port"] == 8010 and body["settings"]["historian_retention"] == {"max_days": 30}
    assert "mqtt" not in body["settings"]
    settings = http.get("/api/v1/project/settings").json()["settings"]
    assert settings["mqtt/broker/host"] == "haos.local"
    assert settings["service_notes/ELA1.DI.1/notes"][0]["text"] == "contact set replaced"


def test_counters_are_listed_and_reset_from_studio_with_an_engineer_token(client):
    http, core, path = client
    counters = core.switching_counters
    core.event_bus.emit("tag_changed", "ELA1.DI.1", 0, "GOOD")
    core.event_bus.emit("tag_changed", "ELA1.DI.1", 1, "GOOD")
    core.event_bus.emit("tag_changed", "ELA1.DI.1", 0, "GOOD")
    listed = http.get("/api/v1/counters").json()
    assert listed["available"] is True
    assert listed["counters"]["ELA1.DI.1"]["closes"] == 1 and listed["counters"]["ELA1.DI.1"]["opens"] == 1

    assert http.post("/api/v1/counters/ELA1.DI.1/reset").status_code == 401
    assert http.post("/api/v1/counters/NOPE/reset", headers=_engineer(core)).status_code == 404
    response = http.post("/api/v1/counters/ELA1.DI.1/reset", headers=_engineer(core))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reset"] and body["previous"]["closes"] == 1 and body["actor"] == "API:Engineer"
    assert counters.get_snapshot("ELA1.DI.1")["closes"] == 0
    assert ("COUNTER_RESET", "API:Engineer", "ELA1.DI.1: switching counter reset (was 1 closes, 1 opens)", True) \
        in core.audit_logger.entries
    state = json.loads((path.parent / "runtime_state.json").read_text(encoding="utf-8"))
    assert state["switching_counters"]["ELA1.DI.1"]["closes"] == 0

    core.switching_counters = None
    assert http.get("/api/v1/counters").json() == {"available": False, "counters": {}}
    assert http.post("/api/v1/counters/ELA1.DI.1/reset", headers=_engineer(core)).status_code == 404
