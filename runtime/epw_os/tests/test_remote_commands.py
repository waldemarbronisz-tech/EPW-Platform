"""Commands from Home Assistant over MQTT (owner's decision: "docelowo
chcę wszystkim sterować z HAOS", konkretne osoby, cichy alarm przy
odmowie).

The thing under test is a GATE. Every one of these is a way in that must
stay shut: a retained replay, a captured message sent again, a stale one,
somebody else's token, a person reaching a zone that is not theirs, an
Operator changing a setting, forcing at all. The happy paths are here
too, but they are the smaller half - what matters is that each refusal
is refused for its OWN reason, and that the ones that look like an
attempt to break in raise the silent alarm the owner asked for.
"""
import json
import sys
import time
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core.access_manager import AccessLevel
from epw_os.core.intrusion_manager import ArmMode
from epw_os.core.remote_commands import FRESHNESS_WINDOW_S, SECURITY_ALARM_ID, RemoteCommandGateway

KOWALSKI = {"id": "U1", "name": "Kowalski", "level": "Operator", "zones": ["Z1"], "enabled": True}
NOWAK = {"id": "U2", "name": "Nowak", "level": "Operator", "zones": ["Z2"], "enabled": True}
INZYNIER = {"id": "U3", "name": "Inżynier", "level": "Engineer", "zones": [], "enabled": True}
TOKENS = {"tok-kowalski": KOWALSKI, "tok-nowak": NOWAK, "tok-inz": INZYNIER}


class FakeAccess:
    def resolve_remote_token(self, token):
        user = TOKENS.get(token)
        return dict(user) if user else None


class FakeIntrusion:
    def __init__(self):
        self.calls = []
        self.armed = {}

    def get_zones(self):
        return [{"id": "Z1", "name": "Hall"}, {"id": "Z2", "name": "Store"}]

    def arm_zone(self, zone_id, actor, level=None, force=False, mode=ArmMode.FULL, user=None):
        allowed = user is None or zone_id in (TOKENS_BY_ID[user]["zones"] or [zone_id])
        self.calls.append(("arm", zone_id, mode, user, actor))
        if not allowed:
            return type("R", (), {"success": False, "needs_confirmation": False,
                                  "reason": f"{user} may not arm {zone_id}"})()
        self.armed[zone_id] = mode
        return type("R", (), {"success": True, "needs_confirmation": False, "reason": ""})()

    def disarm_zone(self, zone_id, actor, level=None, user=None):
        allowed = user is None or zone_id in (TOKENS_BY_ID[user]["zones"] or [zone_id])
        self.calls.append(("disarm", zone_id, user, actor))
        if allowed:
            self.armed.pop(zone_id, None)
        return allowed

    def clear_alarm_memory(self, zone_id, actor, level=None):
        self.calls.append(("reset", zone_id, actor))
        return True


TOKENS_BY_ID = {user["id"]: user for user in TOKENS.values()}


class FakeCommands:
    def __init__(self, permitted=True):
        self.calls = []
        self.permitted = permitted

    def request_command(self, device_tag, command, user="Operator", validate_only=False):
        self.calls.append((device_tag, command, user))
        return (True, []) if self.permitted else (False, ["Platform Safety: device offline"])


class FakeAlarms:
    def __init__(self):
        self.raised = []

    def trigger_alarm(self, alarm_id, message, source_tag="", priority=1):
        self.raised.append((alarm_id, message, priority))


class FakeAudit:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail, success=True):
        self.entries.append((event_type, actor, detail, success))


class FakeProcessProtection:
    def __init__(self):
        self.calls = []

    def update_protection(self, protection_id, level=None, **fields):
        self.calls.append((protection_id, level, fields))
        return protection_id == "PP1"


class FakeProjectManager:
    def __init__(self):
        self.stages = []

    def set_electrical_stage(self, function_id, stage_name, level=None, **fields):
        self.stages.append((function_id, stage_name, level, fields))
        return function_id == "50"


@pytest.fixture
def gateway():
    published = []
    gate = RemoteCommandGateway(
        access_manager=FakeAccess(), intrusion_manager=FakeIntrusion(), command_manager=FakeCommands(),
        project_manager=FakeProjectManager(), process_protection_manager=FakeProcessProtection(),
        alarm_manager=FakeAlarms(), audit_logger=FakeAudit(),
        publish_result=published.append,
    )
    gate.published = published
    return gate


def _message(gateway, **body):
    body.setdefault("id", f"cmd-{len(gateway.published)}-{time.time()}")
    body.setdefault("ts", time.time())
    body.setdefault("token", "tok-kowalski")
    return json.dumps(body).encode("utf-8")


def _send(gateway, retained=False, **body):
    return gateway.handle("epw/TEST/cmd", _message(gateway, **body), retained=retained)


# --- the ways in that must stay shut -----------------------------------------

def test_a_retained_command_is_refused_and_raises_the_alarm(gateway):
    result = _send(gateway, retained=True, action="intrusion", what="disarm", zone="Z1")

    assert result["accepted"] is False and "retained" in result["reason"]
    assert gateway.intrusion_manager.calls == []
    assert gateway.alarm_manager.raised and gateway.alarm_manager.raised[0][0] == SECURITY_ALARM_ID


def test_a_captured_command_replayed_later_is_stale(gateway):
    result = _send(gateway, ts=time.time() - FRESHNESS_WINDOW_S - 60,
                   action="intrusion", what="disarm", zone="Z1")

    assert result["accepted"] is False and "stale" in result["reason"]
    assert gateway.intrusion_manager.calls == []
    assert gateway.alarm_manager.raised


def test_the_same_command_delivered_twice_runs_once(gateway):
    """QoS 1 means "at least once" - a duplicate is ordinary MQTT, not an
    attack: answered again, executed once, and no alarm."""
    payload = _message(gateway, id="same-id", action="intrusion", what="arm", zone="Z1")

    first = gateway.handle("epw/TEST/cmd", payload)
    second = gateway.handle("epw/TEST/cmd", payload)

    assert first["accepted"] is True
    assert second["accepted"] is True and second["duplicate"] is True
    assert len(gateway.intrusion_manager.calls) == 1
    assert gateway.alarm_manager.raised == []


def test_an_unknown_token_is_refused_and_raises_the_alarm(gateway):
    result = _send(gateway, token="nie-ten-token", action="intrusion", what="disarm", zone="Z1")

    assert result["accepted"] is False and "unknown user" in result["reason"]
    assert gateway.intrusion_manager.calls == []
    assert gateway.alarm_manager.raised


def test_claiming_to_be_someone_else_is_refused(gateway):
    """Holding Nowak's token while saying "I am Kowalski" - the identity
    that counts is the one the token proves."""
    result = _send(gateway, user="U1", token="tok-nowak", action="intrusion", what="arm", zone="Z2")

    assert result["accepted"] is False
    assert gateway.intrusion_manager.calls == []


def test_a_person_cannot_reach_a_zone_that_is_not_theirs(gateway):
    """The same rule as at the cabinet - and enforced by the same
    manager, not re-implemented here."""
    result = _send(gateway, token="tok-nowak", user="U2", action="intrusion", what="disarm", zone="Z1")

    assert result["accepted"] is False
    assert gateway.intrusion_manager.armed == {}


def test_an_operator_cannot_change_a_setting(gateway):
    result = _send(gateway, action="setting", what="process_protection", target="PP1",
                   values={"upper_threshold": 90.0})

    assert result["accepted"] is False and "Engineer" in result["reason"]
    assert gateway.process_protection_manager.calls == []


def test_forcing_is_not_an_action_at_all(gateway):
    """Not "refused for this user" - there is no force action in the
    gateway's table, on purpose: a force is a tool for somebody standing
    at the cabinet, held alive by their heartbeat."""
    result = _send(gateway, token="tok-inz", action="force", target="ADA1.DO.1", value=True)

    assert result["accepted"] is False and "unknown action" in result["reason"]


def test_rubbish_on_the_topic_is_refused_without_crashing(gateway):
    assert gateway.handle("epw/TEST/cmd", b"\xff\xfe not json")["accepted"] is False
    assert gateway.handle("epw/TEST/cmd", b'"a string"')["accepted"] is False
    assert gateway.handle("epw/TEST/cmd", b'{"no": "id"}')["accepted"] is False
    assert gateway.intrusion_manager.calls == []


# --- what a real command does -------------------------------------------------

def test_arming_reaches_the_alarm_system_as_that_person(gateway):
    result = _send(gateway, action="intrusion", what="arm", zone="Z1")

    assert result["accepted"] is True
    action, zone, mode, user, actor = gateway.intrusion_manager.calls[0]
    assert (action, zone, mode, user) == ("arm", "Z1", ArmMode.FULL, "U1")
    assert "Kowalski" in actor, "the event register must name the person, not the channel"


def test_night_arming_is_its_own_action(gateway):
    _send(gateway, action="intrusion", what="arm_night", zone="Z1")
    assert gateway.intrusion_manager.calls[0][2] == ArmMode.NIGHT


def test_a_command_without_a_zone_applies_to_every_zone_the_person_may_touch(gateway):
    result = _send(gateway, token="tok-inz", user="U3", action="intrusion", what="arm")

    assert result["accepted"] is True
    assert [c[1] for c in gateway.intrusion_manager.calls] == ["Z1", "Z2"]


def test_an_apparatus_command_goes_through_the_ordinary_command_path(gateway):
    """Not to a driver: through CommandManager, so the safety kernel, the
    logic interlocks, a force on that output and Training Mode all apply
    exactly as they do from the panel."""
    result = _send(gateway, action="apparatus", target="Q1", what="CLOSE")

    assert result["accepted"] is True
    assert gateway.command_manager.calls == [("Q1", "CLOSE", "MQTT:Kowalski")]


def test_a_command_the_safety_path_refuses_comes_back_with_its_reason(gateway):
    gateway.command_manager.permitted = False

    result = _send(gateway, action="apparatus", target="Q1", what="CLOSE")

    assert result["accepted"] is False and "device offline" in result["reason"]
    # A refusal by the plant's own rules is not a break-in attempt.
    assert gateway.alarm_manager.raised == []


def test_an_engineer_can_change_a_process_protection(gateway):
    result = _send(gateway, token="tok-inz", user="U3", action="setting",
                   what="process_protection", target="PP1",
                   values={"upper_threshold": 90.0, "enabled": True})

    assert result["accepted"] is True
    target, level, fields = gateway.process_protection_manager.calls[0]
    assert (target, level) == ("PP1", AccessLevel.ENGINEER)
    assert fields == {"upper_threshold": 90.0, "enabled": True}


def test_an_engineer_can_change_a_protection_stage(gateway):
    result = _send(gateway, token="tok-inz", user="U3", action="setting",
                   what="electrical_stage", target="50", stage="Stage 1", values={"setting": 42.0})

    assert result["accepted"] is True
    assert gateway.project_manager.stages == [("50", "Stage 1", AccessLevel.ENGINEER, {"setting": 42.0})]


def test_every_outcome_is_published_back(gateway):
    """MQTT gives no answer of its own - without this, the automation
    that sent the command never learns whether it worked."""
    _send(gateway, action="intrusion", what="arm", zone="Z1")
    _send(gateway, token="zły", action="intrusion", what="disarm", zone="Z1")

    assert len(gateway.published) == 2
    assert gateway.published[0]["accepted"] is True
    assert gateway.published[1]["accepted"] is False and gateway.published[1]["reason"]


def test_every_command_is_audited_either_way(gateway):
    _send(gateway, action="intrusion", what="arm", zone="Z1")
    _send(gateway, token="zły", action="intrusion", what="disarm", zone="Z1")

    kinds = [entry[0] for entry in gateway.audit_logger.entries]
    assert "REMOTE_COMMAND" in kinds and "REMOTE_COMMAND_REFUSED" in kinds
