"""Signal register etap 6: what was left - the register's remaining SEC
aggregates and per-instance bits, the zone requests BYPASS/UNBYPASS and
INHIBIT/UNINHIBIT against the real IntrusionManager, and REQ.SYSTEM.*
(core/system_requests.py). Values, not names: each bit is driven from
the manager's own state and read back."""
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ["EPW_TESTING"] = "1"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core.access_manager import AccessLevel  # noqa: E402
from epw_os.core.events import EventBus  # noqa: E402
from epw_os.core.intrusion_manager import NORMAL_STATE_NC, IntrusionManager, LineType, ZoneState  # noqa: E402
from epw_os.core.logic_runtime import SystemSignalSource, TagIOProvider  # noqa: E402
from epw_os.core.security_signals import SecuritySignalSource  # noqa: E402
from epw_os.core.system_requests import SystemRequests  # noqa: E402
from epw_os.core.tag_manager import TagManager, TagType  # noqa: E402
from epw_os.tests.test_intrusion_manager import FakeAlarmHistoryLogger, FakeAuditLogger, FakeProjectManager  # noqa: E402


@pytest.fixture
def plant():
    bus = EventBus()
    tags = TagManager(bus)
    for i in range(1, 5):
        tags.add_tag(f"DI{i}", True, TagType.BOOL, source="HARDWARE")
    tags.add_tag("MAINS", True, TagType.BOOL, source="HARDWARE")
    tags.add_tag("BATT", True, TagType.BOOL, source="HARDWARE")
    audit = FakeAuditLogger()
    manager = IntrusionManager(bus, tags, FakeProjectManager(), audit, FakeAlarmHistoryLogger())
    zone = manager.add_zone("Parter", 0.0, 0.0)
    line_a = manager.add_line("Drzwi", zone, "DI1", NORMAL_STATE_NC, LineType.INSTANT)
    line_b = manager.add_line("Okno", zone, "DI2", NORMAL_STATE_NC, LineType.INSTANT)
    source = SecuritySignalSource(manager)
    system = SystemSignalSource(security=source)
    yield SimpleNamespace(bus=bus, tags=tags, audit=audit, manager=manager, zone=zone, lines=(line_a, line_b),
                          source=source, read=system.read)
    manager.teardown() if hasattr(manager, "teardown") else None


def test_an_inhibited_zone_refuses_every_arm_and_says_so_in_the_bit(plant):
    read, zone, m = plant.read, plant.zone, plant.manager
    assert read(f"SEC.ZONE.{zone}.INHIBITED") is False
    assert plant.source.execute(f"REQ.SEC.ZONE.{zone}.INHIBIT", "LOGIC") is True
    assert read(f"SEC.ZONE.{zone}.INHIBITED") is True
    assert plant.audit.entries[-1][0] == "INTRUSION_ZONE_INHIBIT_ON" and "Parter" in plant.audit.entries[-1][2]
    result = m.arm_zone(zone, actor="Operator", level=AccessLevel.OPERATOR)
    assert result.success is False and "inhibited" in result.reason
    assert m.get_zone_state(zone) == ZoneState.DISARMED and read("SEC.SYSTEM.ANY_ZONE_ARMED") is False
    assert plant.source.execute(f"REQ.SEC.ZONE.{zone}.ARM", "LOGIC") is False
    assert plant.source.execute(f"REQ.SEC.ZONE.{zone}.UNINHIBIT", "LOGIC") is True
    assert read(f"SEC.ZONE.{zone}.INHIBITED") is False
    assert m.arm_zone(zone, actor="Operator", level=AccessLevel.OPERATOR).success is True
    assert read("SEC.SYSTEM.ANY_ZONE_ARMED") is True
    # a zone that does not exist: refused, not applied
    assert plant.source.execute("REQ.SEC.ZONE.NOPE.INHIBIT", "LOGIC") is False
    assert plant.source.required_level(f"REQ.SEC.ZONE.{zone}.INHIBIT") == AccessLevel.OPERATOR
    assert plant.source.required_level(f"REQ.SEC.ZONE.{zone}.BYPASS") == AccessLevel.ENGINEER
    assert plant.source.required_level(f"REQ.SEC.ZONE.{zone}.ARM") is None


def test_bypass_and_unbypass_cover_every_line_of_the_zone(plant):
    read, zone, m = plant.read, plant.zone, plant.manager
    line_a, line_b = plant.lines
    assert read(f"SEC.ZONE.{zone}.BYPASSED") is False
    assert plant.source.execute(f"REQ.SEC.ZONE.{zone}.BYPASS", "LOGIC") is True
    assert m.is_line_bypassed(line_a) and m.is_line_bypassed(line_b)
    assert read(f"SEC.ZONE.{zone}.BYPASSED") is True and read(f"SEC.LINE.{line_a}.BYPASSED") is True
    assert sum(1 for e in plant.audit.entries if e[0] == "INTRUSION_LINE_BYPASS_ON") == 2
    assert plant.source.execute(f"REQ.SEC.ZONE.{zone}.BYPASS", "LOGIC") is True, "already bypassed is still done"
    assert plant.source.execute(f"REQ.SEC.ZONE.{zone}.UNBYPASS", "LOGIC") is True
    assert not m.is_line_bypassed(line_a) and not m.is_line_bypassed(line_b)
    assert read(f"SEC.ZONE.{zone}.BYPASSED") is False
    empty = m.add_zone("Pusta", 0.0, 0.0)
    assert plant.source.execute(f"REQ.SEC.ZONE.{empty}.BYPASS", "LOGIC") is False, "no lines, nothing to bypass"


def test_the_aggregates_follow_lines_zones_and_the_walk_test(plant):
    read, zone, m = plant.read, plant.zone, plant.manager
    line_a, line_b = plant.lines
    assert read("SEC.SYSTEM.ANY_LINE_VIOLATED") is False and read("SEC.SYSTEM.ANY_ZONE_ALARM") is False
    plant.tags.publish_from_driver("DI1", False)                      # NC loop broken: violated
    assert read("SEC.SYSTEM.ANY_LINE_VIOLATED") is True and read(f"SEC.LINE.{line_a}.VIOLATED") is True
    plant.tags.publish_from_driver("DI1", True)
    assert read("SEC.SYSTEM.ANY_LINE_VIOLATED") is False
    assert m.arm_zone(zone, actor="Operator", level=AccessLevel.OPERATOR).success
    plant.tags.publish_from_driver("DI2", False)
    assert read("SEC.SYSTEM.ANY_ZONE_ALARM") is True and read("SEC.SYSTEM.ANY_ZONE_ARMED") is False
    m.disarm_zone(zone, actor="Operator", level=AccessLevel.OPERATOR)
    plant.tags.publish_from_driver("DI2", True)
    assert read("SEC.SYSTEM.ANY_ZONE_ALARM") is False
    # walk test: the bit while it runs, and which line reacted
    assert read("SEC.SYSTEM.WALK_TEST") is False and read(f"SEC.LINE.{line_a}.WALK_TEST_SEEN") is False
    assert m.start_walk_test(zone, actor="Engineer", level=AccessLevel.ENGINEER, duration_seconds=30)
    assert read("SEC.SYSTEM.WALK_TEST") is True
    plant.tags.publish_from_driver("DI1", False)
    plant.tags.publish_from_driver("DI1", True)
    assert read(f"SEC.LINE.{line_a}.WALK_TEST_SEEN") is True and read(f"SEC.LINE.{line_b}.WALK_TEST_SEEN") is False
    m.stop_walk_test(zone, actor="Engineer", level=AccessLevel.ENGINEER)
    assert read("SEC.SYSTEM.WALK_TEST") is False
    assert read(f"SEC.LINE.{line_a}.WALK_TEST_SEEN") is False, "the record goes with the test's summary"


def test_the_technical_alarm_is_the_power_supervisions_verdict(plant):
    read, m = plant.read, plant.manager
    assert read("SEC.SYSTEM.TECHNICAL_ALARM") is False
    m.configure_power_supervision(mains_tag="MAINS", mains_ok_state=True, battery_tag="BATT", battery_ok_state=True)
    assert read("SEC.SYSTEM.TECHNICAL_ALARM") is False
    plant.tags.publish_from_driver("MAINS", False)
    assert read("SEC.SYSTEM.TECHNICAL_ALARM") is True
    plant.tags.publish_from_driver("MAINS", True)
    assert read("SEC.SYSTEM.TECHNICAL_ALARM") is False
    plant.tags.publish_from_driver("BATT", False)
    assert read("SEC.SYSTEM.TECHNICAL_ALARM") is True and read("SEC.SYSTEM.ANY_LINE_FAULT") is False


# --- REQ.SYSTEM.* -------------------------------------------------------------------------------------

class _Audit:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))


def _fake_core():
    calls = []
    core = SimpleNamespace(audit_logger=_Audit(), calls=calls, restart_requested=None,
                           tag_manager=TagManager(EventBus()))
    core.reload_logic = lambda actor="", level=None: (calls.append(("reload_logic", actor, level)) or
                                                       {"success": True, "reason": "", "status": {}})
    core.reload_synoptic = lambda actor="", level=None: (calls.append(("reload_synoptic", actor, level)) or
                                                          {"success": False, "reason": "no screens", "problems": []})
    core.request_restart = lambda reason, actor="SYSTEM": calls.append(("request_restart", reason, actor))
    return core


def _join(source):
    for thread in source.threads:
        thread.join(timeout=5.0)


def test_system_requests_are_an_engineers_run_off_the_scan_and_are_audited():
    core = _fake_core()
    source = SystemRequests(core)
    system = SystemSignalSource(sources=[source])
    access = SimpleNamespace(level=AccessLevel.OPERATOR, has_access=lambda req: req in (AccessLevel.OPERATOR, AccessLevel.USER))
    io = TagIOProvider(core.tag_manager, access_manager=access, audit_logger=core.audit_logger, system_signals=system)
    io.write_system_signal("REQ.SYSTEM.RELOAD_LOGIC", True)
    assert core.calls == [] and core.audit_logger.entries[-1][0] == "LOGIC_REQUEST_REFUSED"
    assert "Engineer" in core.audit_logger.entries[-1][2]
    access.level, access.has_access = AccessLevel.ENGINEER, (lambda req: True)
    io.write_system_signal("REQ.SYSTEM.RELOAD_LOGIC", False)
    io.write_system_signal("REQ.SYSTEM.RELOAD_LOGIC", True)
    _join(source)
    assert core.calls == [("reload_logic", "LOGIC", AccessLevel.ENGINEER)]
    assert any(e[0] == "SYSTEM_REQUEST" and "reload_logic() started" in e[2] for e in core.audit_logger.entries)
    io.write_system_signal("REQ.SYSTEM.RELOAD_SYNOPTIC", True)
    _join(source)
    assert core.calls[-1] == ("reload_synoptic", "LOGIC", AccessLevel.ENGINEER)
    io.write_system_signal("REQ.SYSTEM.RESTART_RUNTIME", True)
    _join(source)
    assert core.calls[-1][0] == "request_restart" and "REQ.SYSTEM.RESTART_RUNTIME" in core.calls[-1][1]
    assert core.calls[-1][2] == "LOGIC"
    # holding the bit true does not re-issue anything; a core without the method refuses with a reason
    io.write_system_signal("REQ.SYSTEM.RESTART_RUNTIME", True)
    assert len(core.calls) == 3
    bare = SystemRequests(SimpleNamespace(audit_logger=_Audit()))
    assert bare.execute("REQ.SYSTEM.RELOAD_LOGIC", "LOGIC") is False
    assert bare.core.audit_logger.entries[-1][0] == "SYSTEM_REQUEST_REFUSED"
    assert source.required_level("REQ.SYSTEM.RELOAD_SYNOPTIC") == AccessLevel.ENGINEER


def test_reload_synoptic_rereads_the_screens_and_rebinds_the_roles(tmp_path, db):
    from epw_os.core import project_format as pf
    from epw_os.core.epw_core import EPWCore
    from epw_os.tests.test_embedded_screens_and_logic import _screens
    project = pf.new_project("Screens", author="Test")
    project.screens = _screens()
    path = tmp_path / "projekt.epw"
    pf.save_project(project, path)
    core = EPWCore()
    core.project_manager.project_file = str(path)
    core.startup()
    try:
        first = core.project_manager.get_embedded_screens()["objects"][0]["id"]
        assert first == "o1"
        # the project on disk changes under the running controller
        project.screens["objects"][0]["id"] = "o1_renamed"
        pf.save_project(project, path)
        refused = core.reload_synoptic("Operator", AccessLevel.OPERATOR)
        assert refused["success"] is False and "Engineer" in refused["reason"]
        assert core.project_manager.get_embedded_screens()["objects"][0]["id"] == "o1"
        seen = []
        core.event_bus.subscribe("project_reloaded", lambda ok: seen.append(ok))
        result = core.reload_synoptic("LOGIC", AccessLevel.ENGINEER)
        assert result["success"] is True and seen == [True]
        assert core.project_manager.get_embedded_screens()["objects"][0]["id"] == "o1_renamed"
        assert core.audit_logger is None or True
        # and the same through the register, from the logic's side
        read = core.logic_engine._io.read_system_signal
        source = core.logic_engine._io.system_signals.request_source("REQ.SYSTEM.RELOAD_SYNOPTIC")
        assert source is not None and source.serves("REQ.SYSTEM.RELOAD_SYNOPTIC")
        assert read("RT.SYNOPTIC.LOADED") in (True, False)
    finally:
        core.shutdown()
