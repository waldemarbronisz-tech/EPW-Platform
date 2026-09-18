"""SPEC "Wymuszanie stanów - Powiązanie" (the internal Omicron,
core/protection_test.py): a process protection is tested by forcing its
analog point past the threshold and measuring the trip against the
configured delay, then the reset; an apparatus by commanding it and
measuring the feedback; both audited, reported and reachable over
REST (Engineer)."""
import hashlib
import json
import os
import secrets
import sys
import threading
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
from epw_os.core.apparatus import Apparatus, ApparatusRegistry, apparatus_command_definitions  # noqa: E402
from epw_os.core.command_manager import CommandManager  # noqa: E402
from epw_os.core.events import EventBus  # noqa: E402
from epw_os.core.force_manager import ForceManager  # noqa: E402
from epw_os.core.process_protection_manager import ProcessProtectionManager  # noqa: E402
from epw_os.core.protection_test import ProtectionTestRunner  # noqa: E402
from epw_os.core.tag_manager import TagManager, TagType  # noqa: E402


class _Audit:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))

    def types(self):
        return [e[0] for e in self.entries]


class _Project:
    """Enough of ProjectManager for ProcessProtectionManager and its persist."""

    def __init__(self, protections):
        self.config = {"process_protections": protections}

    def get_process_protections(self):
        return list(self.config["process_protections"])

    def set_process_protections(self, data):
        self.config["process_protections"] = list(data)

    def save_project(self):
        return True

    def structure_editable(self):
        return True


class _Drivers:
    """A driver boundary whose feedback follows the coil after a short delay."""

    def __init__(self, bus, feedback_for):
        self.bus = bus
        self.feedback_for = feedback_for
        self.written = []

    def route_command(self, driver_id, tag, value):
        self.written.append((tag, value))
        fb = self.feedback_for.get(tag)
        if fb is not None:
            threading.Timer(0.05, lambda: self.bus.emit("driver_update", fb[0], fb[1] if value else not fb[1], "GOOD")).start()
        return True


class _Kernel:
    def validate_command_safety(self, *_):
        return True, ""


class _Logic:
    def validate_command(self, *_):
        return True, []


class _Core:
    def __init__(self, tmp_path, delay=0.3):
        self.is_running = True
        self.audit_logger = _Audit()
        self.event_bus = EventBus()
        self.tag_manager = TagManager(self.event_bus)
        for name, kind, value in (("ELA1.AI.1", TagType.REAL, 20.0), ("ELA1.DI.1", TagType.BOOL, True),
                                  ("ADA1.DO.1", TagType.BOOL, False), ("ADA1.DO.2", TagType.BOOL, False)):
            self.tag_manager.add_tag(name, value, kind)
        self.event_bus.subscribe("driver_update", lambda tag, value, q: self.tag_manager.publish_from_driver(tag, value))
        self.apparatus_registry = ApparatusRegistry()
        self.apparatus_registry.set_apparatuses([
            Apparatus(id="KOT_KM1", behavior="SWITCHED", kind="contactor", feedback=["ELA1.DI.1"],
                      command=["ADA1.DO.1", "ADA1.DO.2"])])
        self.force_manager = ForceManager(self.event_bus, self.tag_manager, None, self.audit_logger,
                                          self.apparatus_registry, driver_for_tag=lambda t: "SIM")
        self.drivers = _Drivers(self.event_bus, {"ADA1.DO.1": ("ELA1.DI.1", True), "ADA1.DO.2": ("ELA1.DI.1", False)})
        self.command_manager = CommandManager(self.tag_manager, _Logic(), _Kernel(), self.event_bus,
                                              driver_manager=self.drivers)
        self.command_manager.force_manager = self.force_manager
        self.command_manager.load_definitions(apparatus_command_definitions(
            [self.apparatus_registry.get("KOT_KM1")], driver_for_tag=lambda t: "SIM"))
        self.project_manager = _Project([{"id": "PP1", "name": "Boiler", "analog_tag": "ELA1.AI.1",
                                          "upper_threshold": 80.0, "lower_threshold": 0.0, "hysteresis": 2.0,
                                          "delay_seconds": delay, "enabled": True}])
        self.process_protection_manager = ProcessProtectionManager(self.event_bus, self.tag_manager,
                                                                   self.project_manager, self.audit_logger)
        self.protection_tests = ProtectionTestRunner(self, reports_file=str(tmp_path / "reports.json"))
        config = tmp_path / "api_tokens.local.json"
        self.tokens = {"Operator": secrets.token_hex(16), "Engineer": secrets.token_hex(16)}
        config.write_text(json.dumps({"token_hashes": {
            level: hashlib.sha256(t.encode("utf-8")).hexdigest() for level, t in self.tokens.items()}}))
        self.api_auth = ApiAuth(config_path=str(config))


def test_a_process_protection_trips_after_its_delay_and_clears_back_in_band(tmp_path):
    core = _Core(tmp_path, delay=0.3)
    runner = core.protection_tests
    assert runner.candidates()["process"][0]["id"] == "PP1" and runner.candidates()["apparatus"][0]["id"] == "KOT_KM1"
    report = runner.start_process_test("PP1", actor="API:Engineer")
    assert report["result"] == "RUNNING" and runner.running()["id"] == report["id"]
    assert runner.wait(10)
    final = runner.get(report["id"])
    assert final["result"] == "PASS", final
    assert 0.25 <= final["measured"]["trip_seconds"] <= 0.9
    assert final["measured"]["reset_seconds"] is not None and final["measured"]["reset_seconds"] < 1.0
    assert final["configured"]["delay_seconds"] == 0.3 and final["measured"]["forced_value"] > 80
    assert not core.tag_manager.is_forced("ELA1.AI.1") and not core.process_protection_manager.is_exceeded("PP1")
    assert any("force" in step for step in final["steps"]) and final["finished_at"]
    assert "PROTECTION_TEST_STARTED" in core.audit_logger.types() and "PROTECTION_TEST_PASS" in core.audit_logger.types()
    assert "FORCE_SET" in core.audit_logger.types() and "FORCE_RELEASED" in core.audit_logger.types()
    assert json.loads((tmp_path / "reports.json").read_text(encoding="utf-8"))[0]["result"] == "PASS"
    assert runner.running() is None

    # A second runner reads the evidence back.
    again = ProtectionTestRunner(core, reports_file=str(tmp_path / "reports.json"))
    assert again.list_reports()[0]["id"] == report["id"]


def test_blocked_tests_are_reported_not_run(tmp_path):
    core = _Core(tmp_path)
    runner = core.protection_tests
    assert runner.start_process_test("NOPE")["reason"].startswith("no process protection")
    core.process_protection_manager.update_protection("PP1", enabled=False)
    assert runner.start_process_test("PP1")["result"] == "BLOCKED"
    core.process_protection_manager.update_protection("PP1", enabled=True)
    assert runner.start_apparatus_test("NOPE")["result"] == "BLOCKED"
    assert [r["result"] for r in runner.list_reports()] == ["BLOCKED"] * 3
    assert core.audit_logger.types().count("PROTECTION_TEST_BLOCKED") == 3


def test_an_apparatus_is_commanded_and_its_feedback_timed_then_restored(tmp_path):
    core = _Core(tmp_path)
    runner = core.protection_tests
    report = runner.start_apparatus_test("KOT_KM1", actor="API:Engineer")
    assert report["result"] == "RUNNING" and report["configured"]["first_command"] == "OPEN"   # it reads closed
    assert runner.wait(10)
    final = runner.get(report["id"])
    assert final["result"] == "PASS", final
    assert 0.03 <= final["measured"]["first_seconds"] <= 1.0 and final["measured"]["restore_seconds"] is not None
    # Two maintained coils: the CLOSE coil is released first, then OPEN energized; afterwards the restore.
    assert ("ADA1.DO.2", True) in core.drivers.written and ("ADA1.DO.1", True) in core.drivers.written
    assert core.tag_manager.get_value("ELA1.DI.1") is True
    assert any("KOT_KM1.OPEN -> " in s for s in final["steps"])


def test_rest_lists_starts_and_reports_a_test_for_an_engineer(tmp_path):
    core = _Core(tmp_path, delay=0.2)
    app.state.core = core
    http = TestClient(app)
    listing = http.get("/api/v1/protection-tests").json()
    assert listing["available"] and listing["candidates"]["process"][0]["id"] == "PP1" and listing["running"] is None
    assert http.post("/api/v1/protection-tests", json={"kind": "process", "id": "PP1"}).status_code == 401
    engineer = {"Authorization": f"Bearer {core.tokens['Engineer']}"}
    assert http.post("/api/v1/protection-tests", json={"kind": "weird", "id": "PP1"}, headers=engineer).status_code == 400
    blocked = http.post("/api/v1/protection-tests", json={"kind": "process", "id": "NOPE"}, headers=engineer)
    assert blocked.status_code == 409 and blocked.json()["detail"]["reason"].startswith("no process protection")
    started = http.post("/api/v1/protection-tests", json={"kind": "process", "id": "PP1"}, headers=engineer)
    assert started.status_code == 200 and started.json()["result"] == "RUNNING"
    test_id = started.json()["id"]
    assert http.get("/api/v1/protection-tests").json()["running"]["id"] == test_id
    deadline = time.time() + 10
    while time.time() < deadline and http.get(f"/api/v1/protection-tests/{test_id}").json()["result"] == "RUNNING":
        time.sleep(0.05)
    final = http.get(f"/api/v1/protection-tests/{test_id}").json()
    assert final["result"] == "PASS", final
    assert http.get("/api/v1/protection-tests/nope").status_code == 404
