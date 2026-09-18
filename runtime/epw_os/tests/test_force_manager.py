"""SPEC "Wymuszanie stanów - dozwolone, obwarowane" (core/force_manager.py,
REST /api/v1/forces): Engineer only and audited, visible to everyone,
gone in one move / when the heartbeat stops / at shutdown, and never on
the protection path. A forced input pins the tag against the driver; a
forced output goes through the driver boundary and refuses commands."""
import hashlib
import json
import os
import secrets
import sys
import time
from pathlib import Path

os.environ["EPW_TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.backend.api import app  # noqa: E402
from epw_os.core.api_auth import ApiAuth  # noqa: E402
from epw_os.core.apparatus import Apparatus, ApparatusRegistry  # noqa: E402
from epw_os.core.events import EventBus  # noqa: E402
from epw_os.core.force_manager import ForceManager  # noqa: E402
from epw_os.core.tag_manager import TagManager, TagQuality, TagType  # noqa: E402


class _Audit:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))

    def types(self):
        return [e[0] for e in self.entries]


class _Drivers:
    def __init__(self):
        self.written = []

    def route_command(self, driver_id, tag, value):
        self.written.append((driver_id, tag, value))
        return True


def _world():
    bus = EventBus()
    tags = TagManager(bus)
    for name, kind in (("ELA1.DI.1", TagType.BOOL), ("ELA1.AI.1", TagType.REAL), ("ADA1.DO.1", TagType.BOOL),
                       ("ADA1.DO.2", TagType.BOOL), ("ELA1.DI.2", TagType.BOOL)):
        tags.add_tag(name, False if kind is TagType.BOOL else 0.0, kind)
    tags.add_tag("Safety.ELA1.Healthy", True, TagType.BOOL)
    registry = ApparatusRegistry()
    registry.set_apparatuses([
        Apparatus(id="KOT_Q1", behavior="SWITCHED", kind="Circuit breaker", feedback=["ELA1.DI.2"], command=["ADA1.DO.2"]),
        Apparatus(id="KOT_KM1", behavior="SWITCHED", kind="Contactor", feedback=["ELA1.DI.1"], command=["ADA1.DO.1"]),
    ])
    audit = _Audit()
    drivers = _Drivers()
    manager = ForceManager(bus, tags, drivers, audit, registry, driver_for_tag=lambda t: "MODBUS_DRIVER",
                           heartbeat_timeout_s=0.3)
    events = []
    bus.subscribe("forces_changed", lambda count: events.append(count))
    return bus, tags, manager, audit, drivers, events


def test_a_forced_input_is_pinned_against_the_driver_until_released():
    bus, tags, manager, audit, drivers, events = _world()
    ok, reason = manager.force("ELA1.DI.1", True, actor="API:Engineer")
    assert ok and reason == ""
    assert tags.get_value("ELA1.DI.1") is True and tags.is_forced("ELA1.DI.1")
    tags.publish_from_driver("ELA1.DI.1", False)              # the field says otherwise - ignored
    bus.emit("driver_update", "ELA1.DI.1", False, "GOOD")
    assert tags.get_value("ELA1.DI.1") is True
    assert manager.snapshot()[0]["tag"] == "ELA1.DI.1" and manager.snapshot()[0]["actor"] == "API:Engineer"
    assert events == [1] and ("FORCE_SET", "API:Engineer") == audit.entries[-1][:2]
    assert drivers.written == []                                # an input is never written to a driver

    assert manager.release("ELA1.DI.1", actor="API:Engineer")
    assert not tags.is_forced("ELA1.DI.1")
    assert tags.get_tag("ELA1.DI.1").quality is TagQuality.UNCERTAIN   # the real value is unknown until the next poll
    tags.publish_from_driver("ELA1.DI.1", False)
    assert tags.get_value("ELA1.DI.1") is False and tags.get_tag("ELA1.DI.1").quality is TagQuality.GOOD
    assert audit.types()[-1] == "FORCE_RELEASED" and events == [1, 0]
    assert manager.release("ELA1.DI.1") is False


def test_a_forced_output_goes_through_the_driver_boundary_and_blocks_commands():
    bus, tags, manager, audit, drivers, events = _world()
    ok, _ = manager.force("ADA1.DO.1", True, actor="API:Engineer")
    assert ok and drivers.written == [("MODBUS_DRIVER", "ADA1.DO.1", True)]
    assert tags.get_value("ADA1.DO.1") is True

    from epw_os.core.command_manager import CommandManager

    class _Kernel:
        def validate_command_safety(self, *_):
            return True, ""

    class _Logic:
        def validate_command(self, *_):
            return True, []

    commands = CommandManager(tags, _Logic(), _Kernel(), bus, driver_manager=drivers)
    commands.force_manager = manager
    commands.load_definitions({"KOT_KM1.CLOSE": {"target": "KOT_KM1", "action": "CLOSE", "output_tag": "ADA1.DO.1",
                                                 "output_value": True, "driver_id": "MODBUS_DRIVER",
                                                 "feedback_tag": None}})
    record = commands.request_command_ex("KOT_KM1", "CLOSE", user="Operator")
    assert record.state == "BLOCKED" and "forced" in record.reason
    manager.release("ADA1.DO.1")
    assert len(drivers.written) == 1                              # a release leaves the output as it is


def test_the_protection_path_and_system_tags_are_never_forced():
    bus, tags, manager, audit, drivers, events = _world()
    for tag in ("ADA1.DO.2", "ELA1.DI.2"):                        # KOT_Q1's points - a breaker
        ok, reason = manager.force(tag, True)
        assert not ok and "protection path" in reason
    ok, reason = manager.force("Safety.ELA1.Healthy", False)
    assert not ok and "never forced" in reason
    ok, reason = manager.force("ELA1.DI.9", True)
    assert not ok and "unknown tag" in reason
    assert manager.snapshot() == [] and events == []
    assert audit.types() == ["FORCE_REFUSED"] * 4


def test_forces_expire_without_a_heartbeat_and_die_with_the_process():
    bus, tags, manager, audit, drivers, events = _world()
    manager.force("ELA1.DI.1", True)
    manager.force("ELA1.AI.1", 42.5)
    assert manager.check_expiry() == 0
    manager.heartbeat()
    time.sleep(0.15)
    manager.heartbeat()
    time.sleep(0.2)
    assert manager.check_expiry() == 0                            # the second heartbeat kept them alive
    time.sleep(0.35)
    assert manager.check_expiry() == 2                            # silence longer than the timeout: all gone
    assert manager.snapshot() == [] and not tags.is_forced("ELA1.AI.1")
    assert audit.types()[-1] == "FORCE_RELEASED_ALL" and "heartbeat" in audit.entries[-1][2]

    manager.force("ELA1.DI.1", True)
    deadline = time.time() + 3.0
    while manager.snapshot() and time.time() < deadline:        # the watch thread releases on its own
        time.sleep(0.05)
    assert manager.snapshot() == []

    manager.force("ELA1.DI.1", True)
    manager.shutdown()
    assert manager.snapshot() == [] and "shutdown" in audit.entries[-1][2]


# --- REST ------------------------------------------------------------------------------------

class _Core:
    def __init__(self, tmp_path):
        self.is_running = True
        self.audit_logger = _Audit()
        self.event_bus, self.tag_manager, self.force_manager, _audit, self.drivers, self.events = _world()
        self.force_manager.audit_logger = self.audit_logger
        config = tmp_path / "api_tokens.local.json"
        self.tokens = {"Operator": secrets.token_hex(16), "Engineer": secrets.token_hex(16)}
        config.write_text(json.dumps({"token_hashes": {
            level: hashlib.sha256(t.encode("utf-8")).hexdigest() for level, t in self.tokens.items()}}))
        self.api_auth = ApiAuth(config_path=str(config))


@pytest.fixture
def client(tmp_path):
    core = _Core(tmp_path)
    app.state.core = core
    return TestClient(app), core


def _engineer(core):
    return {"Authorization": f"Bearer {core.tokens['Engineer']}"}


def test_rest_forces_need_an_engineer_token_and_are_visible_to_everyone(client):
    http, core = client
    assert http.post("/api/v1/forces", json={"tag": "ELA1.DI.1", "value": True}).status_code == 401
    assert http.post("/api/v1/forces", json={"tag": "ELA1.DI.1", "value": True},
                     headers={"Authorization": f"Bearer {core.tokens['Operator']}"}).status_code == 401
    response = http.post("/api/v1/forces", json={"tag": "ELA1.DI.1", "value": True}, headers=_engineer(core))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["forced"] and body["forces"][0]["tag"] == "ELA1.DI.1" and body["heartbeat_timeout_s"] == 0.3
    assert http.get("/api/v1/forces").json()["forces"][0]["actor"] == "API:Engineer"
    assert core.tag_manager.get_value("ELA1.DI.1") is True

    refused = http.post("/api/v1/forces", json={"tag": "ADA1.DO.2", "value": True}, headers=_engineer(core))
    assert refused.status_code == 403 and "protection path" in refused.json()["detail"]["reason"]

    assert http.post("/api/v1/forces/heartbeat", headers=_engineer(core)).json()["seconds_since_heartbeat"] < 0.2
    assert http.delete("/api/v1/forces/ELA1.DI.9", headers=_engineer(core)).status_code == 404
    assert http.delete("/api/v1/forces/ELA1.DI.1", headers=_engineer(core)).json()["released"] is True
    http.post("/api/v1/forces", json={"tag": "ELA1.DI.1", "value": True}, headers=_engineer(core))
    http.post("/api/v1/forces", json={"tag": "ADA1.DO.1", "value": False}, headers=_engineer(core))
    assert http.delete("/api/v1/forces", headers=_engineer(core)).json()["released"] == 2
    assert http.get("/api/v1/forces").json()["forces"] == []
    assert core.audit_logger.types().count("FORCE_SET") == 3 and "FORCE_RELEASED_ALL" in core.audit_logger.types()
