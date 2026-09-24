"""The control place - MODE.LOCAL / MODE.REMOTE (owner's decision
2026-09-24): LOCAL locks every change arriving over the engineering link
(Studio's REST) and remote control (MQTT); it is set from the panel
only, survives a restart, and the register reads it."""
import hashlib
import json
import os
import secrets
import sys
import time
from pathlib import Path
from types import SimpleNamespace

os.environ["EPW_TESTING"] = "1"

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core import operating_mode as modes  # noqa: E402
from epw_os.core.access_manager import AccessLevel  # noqa: E402
from epw_os.core.events import EventBus  # noqa: E402
from epw_os.core.logic_runtime import SystemSignalSource  # noqa: E402
from epw_os.core.operating_mode import OperatingModeManager  # noqa: E402
from epw_os.core.remote_commands import RemoteCommandGateway  # noqa: E402
from epw_os.core.runtime_state_signals import RuntimeStateSignals  # noqa: E402
from shared.logic import system_signals  # noqa: E402


class _Audit:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))

    def types(self):
        return [e[0] for e in self.entries]


def test_the_place_is_remote_by_default_persisted_and_an_operators_to_set():
    audit = _Audit()
    saved = []
    manager = OperatingModeManager(EventBus(), audit, load=lambda: None, save=lambda m: None,
                                   load_place=lambda: None, save_place=saved.append)
    assert manager.control_place == "REMOTE" and manager.remote_allowed() is True
    assert manager.set_control_place("LOCAL", actor="User (panel)", level=AccessLevel.USER) == (
        False, "LOCAL requires Operator, User (panel) is User")
    assert audit.types()[-1] == "CONTROL_PLACE_REFUSED" and manager.control_place == "REMOTE"
    assert manager.set_control_place("LOCAL", actor="Operator (panel)", level=AccessLevel.OPERATOR) == (True, "")
    assert saved == ["LOCAL"] and manager.remote_allowed() is False
    assert audit.entries[-1][:3] == ("CONTROL_PLACE_CHANGED", "Operator (panel)", "REMOTE -> LOCAL")
    assert manager.set_control_place("SIDEWAYS", actor="x")[0] is False
    restored = OperatingModeManager(EventBus(), audit, load_place=lambda: "LOCAL", save_place=saved.append)
    assert restored.control_place == "LOCAL", "a lock the operator set must survive a restart"


def test_the_register_reads_the_place_and_the_catalogue_serves_it():
    manager = OperatingModeManager(EventBus(), _Audit())
    core = SimpleNamespace(operating_mode=manager, health_manager=None, logic_engine=None, project_manager=None,
                           synoptic_status={}, training_mode=SimpleNamespace(active=False),
                           tag_manager=SimpleNamespace(mode="LIVE MODE"), time_sync_monitor=None, lifecycle="RUNNING")
    source = SystemSignalSource(sources=[RuntimeStateSignals(core)])
    assert source.read("MODE.REMOTE") is True and source.read("MODE.LOCAL") is False
    manager.set_control_place("LOCAL", actor="Operator (panel)", level=AccessLevel.OPERATOR)
    assert source.read("MODE.LOCAL") is True and source.read("MODE.REMOTE") is False
    ids = {s["id"]: s for s in system_signals.raw_signals()}
    assert ids["MODE.LOCAL"]["runtime"] == "served" and ids["MODE.REMOTE"]["source"] == "runtime"
    assert "REQ.MODE.LOCAL" not in ids, "the place is set from the panel only - never a logic request"


def test_in_local_control_the_engineering_link_may_read_but_not_change(tmp_path):
    from fastapi.testclient import TestClient
    from epw_os.backend.api import app
    from epw_os.core.api_auth import ApiAuth
    audit = _Audit()
    manager = OperatingModeManager(EventBus(), audit)
    tokens = {"Operator": secrets.token_hex(16), "Engineer": secrets.token_hex(16)}
    config = tmp_path / "api_tokens.local.json"
    config.write_text(json.dumps({"token_hashes": {
        level: hashlib.sha256(t.encode("utf-8")).hexdigest() for level, t in tokens.items()}}))
    commands = []
    forces = SimpleNamespace(heartbeat=lambda: commands.append("heartbeat"), snapshot=lambda: [],
                             heartbeat_timeout_s=30.0, seconds_since_heartbeat=lambda: None,
                             force=lambda tag, value, actor="": (True, ""), is_forced=lambda t: False)
    core = SimpleNamespace(
        operating_mode=manager, audit_logger=audit, api_auth=ApiAuth(config_path=str(config)),
        command_manager=SimpleNamespace(request_command_ex=lambda *a, **k: (commands.append(("cmd", a)) or
                                                                             SimpleNamespace(state="VALIDATED", reason="",
                                                                                             id="1", requested_at=0.0))),
        force_manager=forces, internal_bits=None, tag_manager=SimpleNamespace(list_tags=lambda: []),
        health_manager=SimpleNamespace(get_health=lambda: {}), is_running=True,
    )
    app.state.core = core
    http = TestClient(app)
    engineer = {"Authorization": f"Bearer {tokens['Engineer']}"}
    operator = {"Authorization": f"Bearer {tokens['Operator']}"}
    assert http.get("/api/v1/control-place").json() == {"control_place": "REMOTE", "remote_allowed": True}
    assert http.post("/api/v1/commands", json={"device_tag": "KOT_KM1", "command": "CLOSE"}, headers=operator).status_code == 200
    manager.set_control_place("LOCAL", actor="Operator (panel)", level=AccessLevel.OPERATOR)
    assert http.get("/api/v1/control-place").json()["remote_allowed"] is False
    assert http.get("/api/v1/health").status_code == 200, "reads keep working"
    for path, body, headers in (("/api/v1/commands", {"device_tag": "KOT_KM1", "command": "OPEN"}, operator),
                                ("/api/v1/forces", {"tag": "ELA1.DI.1", "value": True}, engineer),
                                ("/api/v1/mode", {"mode": "MANUAL"}, operator),
                                ("/api/v1/bits/M.X", {"value": True}, operator)):
        response = http.post(path, json=body, headers=headers)
        assert response.status_code == 423, (path, response.status_code, response.text)
        assert response.json()["detail"]["error"] == "local_control"
    assert manager.mode == "NORMAL" and len([c for c in commands if c != "heartbeat"]) == 1
    assert http.post("/api/v1/forces/heartbeat", headers=engineer).status_code == 200, "what is held stays held"
    refused = [e for e in audit.entries if e[0] == "REMOTE_REFUSED_LOCAL"]
    assert len(refused) == 4 and all("LOCAL control" in e[2] for e in refused)
    manager.set_control_place("REMOTE", actor="Operator (panel)", level=AccessLevel.OPERATOR)
    assert http.post("/api/v1/mode", json={"mode": "MANUAL"}, headers=operator).json() == {"mode": "MANUAL"}


def test_in_local_control_a_remote_command_is_refused_and_answered():
    audit = _Audit()
    manager = OperatingModeManager(EventBus(), audit)
    calls = []
    published = []

    class _Access:
        def resolve_remote_token(self, token):
            return {"id": "U1", "name": "Kowalski", "level": "Operator", "zones": [], "enabled": True} if token == "tok" else None

    class _Commands:
        def request_command(self, target, what, user="Operator"):
            calls.append((target, what))
            return True, []

    gateway = RemoteCommandGateway(access_manager=_Access(), command_manager=_Commands(), audit_logger=audit,
                                   publish_result=published.append, operating_mode=lambda: manager)

    def send(**body):
        body.setdefault("id", f"c{len(published)}-{time.time()}")
        body.setdefault("ts", time.time())
        body.setdefault("token", "tok")
        return gateway.handle("epw/x/cmd", json.dumps(body).encode("utf-8"))

    assert send(action="apparatus", target="KOT_KM1", what="CLOSE")["accepted"] is True
    manager.set_control_place("LOCAL", actor="Operator (panel)", level=AccessLevel.OPERATOR)
    result = send(action="apparatus", target="KOT_KM1", what="OPEN")
    assert result["accepted"] is False and "LOCAL control" in result["reason"]
    assert calls == [("KOT_KM1", "CLOSE")], "nothing reached the command manager in LOCAL"
    assert audit.types()[-1] == "REMOTE_COMMAND_REFUSED"
    manager.set_control_place("REMOTE", actor="Operator (panel)", level=AccessLevel.OPERATOR)
    assert send(action="apparatus", target="KOT_KM1", what="OPEN")["accepted"] is True


def test_the_panel_menu_offers_the_place_at_operator_level_and_the_indicator_shows_it():
    from epw_os.i18n import set_language, tr
    set_language("pl")
    assert modes.CONTROL_PLACE_LEVEL == AccessLevel.OPERATOR and modes.DEFAULT_CONTROL_PLACE == "REMOTE"
    assert tr("modes.local") == "LOKALNE" and tr("modes.remote") == "ZDALNE"
    assert tr("statusbar.control_place", place=tr("modes.local")) == "STEROWANIE: LOKALNE"
    set_language("en")
    assert tr("statusbar.control_place_set", place=tr("modes.remote"), level="Operator") == "Control REMOTE (Operator)"
