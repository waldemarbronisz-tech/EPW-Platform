"""REST API (Task: "zamknac luke bezpieczenstwa w REST API").

Covers every DOWOD item explicitly: an unauthenticated request to the
state-changing endpoint is rejected; an authenticated-as-User caller
(no token - see api_auth.py's own docstring for why that IS "User" in
this system's model, the same way the GUI needs no PIN to view at User
level) cannot issue a command, exactly like the GUI; the audit trail
records the identity the SYSTEM resolved via the token, never anything
the request body claims; a failed authentication attempt reaches the
audit trail; GET /api/v1/tags returns real tag content, not just "some
list"; POST /api/v1/commands returns a real body on success, not null.

Uses a REAL TagManager (BLAD 2's fix needs to be checked against real
list_tags() behavior, not a hand-rolled dict) and a REAL ApiAuth
pointed at a scratch config path (memory rule: never let a test touch
the real epw_os/config/api_tokens.local.json) - CommandManager and
AuditLogger stay lightweight fakes, since what matters here is the
API layer's own behavior, not re-testing CommandManager/AuditLogger
themselves (already covered elsewhere).
"""
import os
os.environ["EPW_TESTING"] = "1"

import tempfile

from fastapi.testclient import TestClient

from epw_os.backend.api import app
from epw_os.core.api_auth import ApiAuth
from epw_os.core.tag_manager import TagManager, TagType, TagQuality
from epw_os.core.events import EventBus


class _RecordingAuditLogger:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))


class _FakeCommandManager:
    """Configurable stand-in - `outcome` picks what request_command_ex()
    returns, so the same fake can drive both the "accepted" and
    "blocked" test paths. Records every call so a test can assert on
    exactly what reached it (target/action/user/source)."""

    def __init__(self, outcome="SUCCESS", reason=""):
        self.outcome = outcome
        self.reason = reason
        self.calls = []

    def request_command_ex(self, target, action, user="Operator", source="GUI"):
        self.calls.append((target, action, user, source))

        class _Record:
            pass

        rec = _Record()
        rec.id = "cmd-123"
        rec.state = self.outcome
        rec.reason = self.reason
        rec.requested_at = 1234567890.0
        return rec

    def request_command(self, *args, **kwargs):
        raise AssertionError("issue_command() must use request_command_ex(), not the legacy request_command()")


class _FakeAlarm:
    def __init__(self):
        self.id = "DEMO"
        self.message = "msg"
        self.priority = 2

        class _State:
            value = "ACTIVE_UNACK"

        self.state = _State()
        self.activation_time = 111.0


class MockCore:
    def __init__(self, tmp_path, command_outcome="SUCCESS", command_reason="", extra_tags=None):
        self.is_running = True
        self.health_manager = type("MockHM", (), {"get_health": lambda *a, **k: {"API": "RUNNING"}})()

        bus = EventBus()
        self.tag_manager = TagManager(bus)
        self.tag_manager.add_tag("DI1", True, TagType.BOOL, description="Feeder 1 feedback")
        self.tag_manager.add_tag("Meas.L1", 231.5, TagType.REAL, quality=TagQuality.SIMULATED)
        self.tag_manager.add_tag("System.Theme", 0, TagType.INT, description="Active visual theme")
        for name, value, dtype in (extra_tags or []):
            self.tag_manager.add_tag(name, value, dtype)

        self.alarm_manager = type("MockAM", (), {"get_active_alarms": staticmethod(lambda: [_FakeAlarm()])})()
        self.command_manager = _FakeCommandManager(outcome=command_outcome, reason=command_reason)
        self.audit_logger = _RecordingAuditLogger()
        # Scratch path - never the real epw_os/config/api_tokens.local.json.
        self.api_auth = ApiAuth(config_path=os.path.join(tmp_path, "api_tokens.local.json"))
        # Task: signal-list export (GET /api/v1/tags/export) - a minimal
        # stand-in with just the two read accessors build_tag_list_export()
        # actually calls.
        self.project_manager = type("MockPM", (), {
            "config": {"project_id": "MOCK_PROJECT"},
            "get_metadata": lambda self: {"name": "Mock Substation"},
        })()


def _make_client(**kwargs):
    tmp_path = tempfile.mkdtemp()
    core = MockCore(tmp_path, **kwargs)
    app.state.core = core
    return TestClient(app), core


def _make_authed_core_and_tokens(tmp_path, **kwargs):
    """Builds a MockCore and separately captures the plaintext tokens
    ApiAuth generated for it - by constructing ApiAuth's config file
    ourselves first (same shape _load_or_create_config() writes), then
    pointing MockCore's ApiAuth at that same path so it loads (not
    regenerates) those exact tokens. This is the only way to get a
    token a test can present - production code never exposes one
    after the one-time startup log line, by design."""
    import hashlib
    import json
    import secrets

    config_path = os.path.join(tmp_path, "api_tokens.local.json")
    tokens = {"Operator": secrets.token_hex(32), "Engineer": secrets.token_hex(32)}
    hashes = {level: hashlib.sha256(t.encode("utf-8")).hexdigest() for level, t in tokens.items()}
    os.makedirs(tmp_path, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump({"token_hashes": hashes}, f)

    core = MockCore(tmp_path, **kwargs)  # loads the tokens above, doesn't regenerate
    return core, tokens


# --- DOWOD: unauthenticated request to the state-changing endpoint is rejected ---

def test_commands_without_a_token_is_rejected():
    client, core = _make_client()
    response = client.post("/api/v1/commands", json={"device_tag": "DO01", "command": "OPEN"})
    assert response.status_code == 401
    assert core.command_manager.calls == [], "CommandManager must never be reached without valid auth"


def test_commands_with_a_garbage_token_is_rejected():
    client, core = _make_client()
    response = client.post(
        "/api/v1/commands",
        json={"device_tag": "DO01", "command": "OPEN"},
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401
    assert core.command_manager.calls == []


# --- DOWOD: an authenticated-as-User caller cannot issue a command, like the GUI ---

def test_no_token_means_user_level_which_cannot_control_exactly_like_the_gui():
    """No Authorization header at all is this system's own definition
    of "User" (see api_auth.py's docstring: User never gets a PIN or a
    token anywhere in this app - it's the no-credential default), so
    this is the literal DOWOD case: an (unauthenticated-as-)User caller
    is refused control, the same rule mv_control.md documents for the
    GUI's own Force button."""
    client, core = _make_client()
    response = client.post("/api/v1/commands", json={"device_tag": "DO01", "command": "OPEN"})
    assert response.status_code == 401
    assert "Operator" in response.json()["detail"]


# --- DOWOD: the audit log records the SYSTEM-resolved identity, not a claimed one ---

def test_successful_command_audits_the_token_resolved_identity_not_a_client_claim():
    tmp_path = tempfile.mkdtemp()
    core, tokens = _make_authed_core_and_tokens(tmp_path, command_outcome="SUCCESS")
    app.state.core = core
    client = TestClient(app)

    response = client.post(
        "/api/v1/commands",
        json={"device_tag": "DO01", "command": "CLOSE"},
        headers={"Authorization": f"Bearer {tokens['Operator']}"},
    )
    assert response.status_code == 200

    # The identity CommandManager itself saw must be the resolved level,
    # not anything client-supplied (the request body has no "user" field
    # at all any more - see api.py's CommandRequest model).
    assert core.command_manager.calls == [("DO01", "CLOSE", "API:Operator", "API")]

    audit_events = [e for e in core.audit_logger.entries if e[0] == "API_COMMAND"]
    assert len(audit_events) == 1
    assert audit_events[0][1] == "API:Operator"  # actor - system-resolved, not client-supplied
    assert audit_events[0][3] is True  # success


def test_engineer_token_also_authenticates_and_is_recorded_as_such():
    tmp_path = tempfile.mkdtemp()
    core, tokens = _make_authed_core_and_tokens(tmp_path, command_outcome="SUCCESS")
    app.state.core = core
    client = TestClient(app)

    response = client.post(
        "/api/v1/commands",
        json={"device_tag": "DO02", "command": "OPEN"},
        headers={"Authorization": f"Bearer {tokens['Engineer']}"},
    )
    assert response.status_code == 200
    assert core.command_manager.calls == [("DO02", "OPEN", "API:Engineer", "API")]


# --- DOWOD: a failed authentication attempt reaches the audit log --------------

def test_failed_authentication_is_audited():
    client, core = _make_client()
    client.post("/api/v1/commands", json={"device_tag": "DO01", "command": "OPEN"})

    auth_failures = [e for e in core.audit_logger.entries if e[0] == "API_AUTH_FAILED"]
    assert len(auth_failures) == 1
    assert auth_failures[0][3] is False  # success=False


def test_bad_token_authentication_failure_is_also_audited():
    client, core = _make_client()
    client.post(
        "/api/v1/commands",
        json={"device_tag": "DO01", "command": "OPEN"},
        headers={"Authorization": "Bearer wrong"},
    )
    auth_failures = [e for e in core.audit_logger.entries if e[0] == "API_AUTH_FAILED"]
    assert len(auth_failures) == 1


# --- BLAD 2: /api/v1/tags returns real content, not just "a list" --------------

def test_api_tags_returns_actual_tag_content():
    client, core = _make_client()
    response = client.get("/api/v1/tags")
    assert response.status_code == 200
    body = response.json()
    names = {t["name"] for t in body}
    assert "DI1" in names and "Meas.L1" in names, "BLAD 2: must reflect real TagManager content, not []"

    di1 = next(t for t in body if t["name"] == "DI1")
    assert di1["value"] is True
    assert di1["data_type"] == "BOOL"
    l1 = next(t for t in body if t["name"] == "Meas.L1")
    assert l1["quality"] == "SIMULATED"


def test_api_tags_prefix_filter():
    client, core = _make_client(extra_tags=[("DI2", False, TagType.BOOL)])
    response = client.get("/api/v1/tags", params={"prefix": "DI"})
    names = {t["name"] for t in response.json()}
    assert names == {"DI1", "DI2"}


def test_api_tags_endpoints_need_no_authentication():
    """GET endpoints stay open - a User-level caller sees this much in
    the GUI with no PIN either (al_matrix.md)."""
    client, core = _make_client()
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/tags").status_code == 200
    assert client.get("/api/v1/alarms").status_code == 200


# --- Task: GET /api/v1/tags/export - signal-list export for Logic Studio ------

def test_api_tags_export_needs_no_authentication():
    client, core = _make_client()
    response = client.get("/api/v1/tags/export")
    assert response.status_code == 200


def test_api_tags_export_matches_build_tag_list_export():
    """The endpoint must be a thin wrapper - not a second, drifting copy
    of the export logic (already covered exhaustively by
    test_tag_export.py)."""
    from epw_os.core.tag_export import build_tag_list_export
    client, core = _make_client()
    response = client.get("/api/v1/tags/export")
    body = response.json()
    expected = build_tag_list_export(core.tag_manager, core.project_manager)
    assert body["tag_count"] == expected["tag_count"]
    assert {t["name"] for t in body["tags"]} == {t["name"] for t in expected["tags"]}
    assert body["format_version"] == expected["format_version"]


def test_api_tags_export_route_does_not_shadow_the_single_tag_route():
    """/api/v1/tags/export must resolve to the export endpoint, not be
    swallowed by GET /api/v1/tags/{tag_name} with tag_name="export"."""
    client, core = _make_client()
    response = client.get("/api/v1/tags/export")
    assert response.status_code == 200
    body = response.json()
    assert "tags" in body and "format_version" in body  # the export shape, not a 404 "Tag not found"


def test_api_tags_export_marks_system_theme_writable():
    client, core = _make_client()
    body = client.get("/api/v1/tags/export").json()
    theme = next(t for t in body["tags"] if t["name"] == "System.Theme")
    assert theme["direction"] == "READ_WRITE"
    others = [t for t in body["tags"] if t["name"] != "System.Theme"]
    assert others and all(t["direction"] == "READ_ONLY" for t in others)


# --- BLAD 4: a successful command returns a real, useful body ------------------

def test_successful_command_returns_command_id_state_and_timestamp():
    tmp_path = tempfile.mkdtemp()
    core, tokens = _make_authed_core_and_tokens(tmp_path, command_outcome="DISPATCHED")
    app.state.core = core
    client = TestClient(app)

    response = client.post(
        "/api/v1/commands",
        json={"device_tag": "DO01", "command": "OPEN"},
        headers={"Authorization": f"Bearer {tokens['Operator']}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["command_id"] == "cmd-123"
    assert body["state"] == "DISPATCHED"
    assert body["requested_at"] == 1234567890.0
    assert body["actor"] == "API:Operator"


def test_blocked_command_still_returns_403_with_reasons():
    """The BLOCKED/FAILED path's response shape is unchanged by this
    task - only the accepted path (which used to end on a bare `pass`)
    was actually broken."""
    tmp_path = tempfile.mkdtemp()
    core, tokens = _make_authed_core_and_tokens(
        tmp_path, command_outcome="BLOCKED", command_reason="Blocked by interlock"
    )
    app.state.core = core
    client = TestClient(app)

    response = client.post(
        "/api/v1/commands",
        json={"device_tag": "ADA01.DO01", "command": "OPEN"},
        headers={"Authorization": f"Bearer {tokens['Operator']}"},
    )
    assert response.status_code == 403
    assert "Blocked by interlock" in response.json()["detail"]["reasons"]

    audit_events = [e for e in core.audit_logger.entries if e[0] == "API_COMMAND"]
    assert audit_events[0][3] is False  # success=False - blocked, still audited


# --- health/alarms still return real content (already true before this task,
# kept here as regression coverage per the DOWOD's own instruction to check
# every API test for "type only" checks) --------------------------------------

def test_api_health_returns_status_and_subsystems():
    client, core = _make_client()
    response = client.get("/api/v1/health")
    body = response.json()
    assert body["status"] == "UP"
    assert body["subsystems"] == {"API": "RUNNING"}


def test_api_alarms_returns_real_alarm_content():
    client, core = _make_client()
    response = client.get("/api/v1/alarms")
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == "DEMO"
    assert body[0]["state"] == "ACTIVE_UNACK"
