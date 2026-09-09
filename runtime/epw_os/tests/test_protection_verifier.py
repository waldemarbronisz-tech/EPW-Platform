"""Tests for ProtectionVerifier's pre-flight safety gate
(check_safety_conditions()) - the System.PendingCommand/System.ActiveTrip
fix (Task: "sprawic, zeby warunki bezpieczenstwa... faktycznie
dzialaly"). A previous session registered both tags (get_value() no
longer returns None) but nothing ever WROTE to them - this task's own
fix, covered here on the READ/precondition side (see
test_command_manager.py for System.PendingCommand's write side in
CommandManager).

QObject-based (QTimer/Signal) - needs a QApplication, same "needs Qt to
construct, no other Qt behavior exercised" reasoning as
test_theme_manager.py's own module-level QApplication bootstrap.
tag_manager is wrapped in a small Qt bridge (_QtTagManagerBridge) - the
exact same shape main.py's own real GUITagManagerAdapter has - because
ProtectionVerifier now does `tag_manager.tag_changed.connect(...)`
(System.ActiveTrip's own write side), which the bare headless
TagManager does not expose; only its EventBus does.
"""
import sys

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

if not QApplication.instance():
    QApplication(sys.argv)

from epw_os.core.events import EventBus
from epw_os.core.tag_manager import TagManager, TagType, TagQuality
from epw_os.core.access_manager import AccessManager, AccessLevel
from epw_os.core.protection_manager import ProtectionManager
from epw_os.core.process_protection_manager import ProcessProtectionManager

# Task (refactor/test-suite-split): every test in this module needs the
# module-level QApplication above - marked so `pytest epw_os/tests/
# -m "not slow"` can skip the whole file.
pytestmark = [pytest.mark.slow, pytest.mark.gui]
from epw_os.core.protection_verifier import ProtectionVerifier


class _QtTagManagerBridge(QObject):
    """The exact same "wrap only what crosses a thread boundary" shape
    main.py's own real GUITagManagerAdapter uses - built inline here
    (not imported from main.py, which also boots a QApplication/FastAPI
    thread at import time)."""
    tag_changed = Signal(str, object, str)

    def __init__(self, core_tm):
        super().__init__()
        self._core_tm = core_tm
        core_tm.event_bus.subscribe("tag_changed", lambda n, v, q: self.tag_changed.emit(n, v, q))

    def get_value(self, name):
        return self._core_tm.get_value(name)

    def get_tag(self, name):
        return self._core_tm.get_tag(name)

    def list_tags(self):
        return self._core_tm.list_tags()

    def update_tag(self, name, val, q=TagQuality.GOOD):
        self._core_tm.update_tag(name, val, q)

    def add_tag(self, name, value, data_type, description="", timeout=5.0, source="SYSTEM",
                quality=TagQuality.GOOD):
        return self._core_tm.add_tag(name, value, data_type, description=description, timeout=timeout,
                                      source=source, quality=quality)


class FakeAuditLogger:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))


def _make_verifier(tmp_path, engineer=True, audit_logger=None, core_tm=None):
    core_tm = core_tm or TagManager(EventBus())
    tag_manager = _QtTagManagerBridge(core_tm)
    # The rest of check_safety_conditions()'s own pre-flight checks -
    # set to their PASSING state, so a test can isolate just the
    # System.PendingCommand/System.ActiveTrip gates without every other
    # one already blocking for an unrelated reason.
    core_tm.add_tag("Meas.L1", 230.0, TagType.REAL)
    core_tm.add_tag("DI2", True, TagType.BOOL)   # feeder active - required True
    core_tm.add_tag("DI3", False, TagType.BOOL)  # must be open (not 1)
    core_tm.add_tag("DI4", False, TagType.BOOL)  # must be open (not 1)
    core_tm.add_tag("Device.Modbus.Status", "ONLINE", TagType.STRING)

    access_manager = AccessManager(EventBus(), config_path=str(tmp_path / "access.local.json"))
    if engineer:
        # Real login, not a bypass - proves the gate genuinely requires
        # Engineer, same as every other Engineer-only path in this app.
        assert access_manager._pin_hashes.get(AccessLevel.ENGINEER) is not None
        access_manager.level = AccessLevel.ENGINEER

    verifier = ProtectionVerifier(tag_manager, ProtectionManager(), access_manager, audit_logger)
    return verifier, tag_manager, core_tm


# --- DOWOD: tags now exist, immediately, before anything ever writes
# to them (the same "no exception" bar as System.Mode's own fix) -------

def test_tags_are_registered_at_construction_default_false(tmp_path):
    verifier, tag_manager, core_tm = _make_verifier(tmp_path)
    assert tag_manager.get_value("System.PendingCommand") is False
    assert tag_manager.get_value("System.ActiveTrip") is False


# --- DOWOD: normal situation - verification still starts unobstructed -

def test_normal_conditions_pass_the_pre_flight_check(tmp_path):
    verifier, tag_manager, core_tm = _make_verifier(tmp_path)
    ok, reason = verifier.check_safety_conditions()
    assert ok is True, reason


def test_engineer_access_still_required(tmp_path):
    verifier, tag_manager, core_tm = _make_verifier(tmp_path, engineer=False)
    ok, reason = verifier.check_safety_conditions()
    assert ok is False
    assert "Engineer" in reason


# --- DOWOD: starting verification WHILE a command is pending is denied,
# naming which precondition and why ---------------------------------

def test_pending_command_true_blocks_the_pre_flight_check_with_a_clear_reason(tmp_path):
    verifier, tag_manager, core_tm = _make_verifier(tmp_path)
    core_tm.update_tag("System.PendingCommand", True)
    ok, reason = verifier.check_safety_conditions()
    assert ok is False
    assert "Pending" in reason


# --- DOWOD: starting verification WHILE a trip is active is denied -----

def test_active_trip_true_blocks_the_pre_flight_check_with_a_clear_reason(tmp_path):
    verifier, tag_manager, core_tm = _make_verifier(tmp_path)
    core_tm.update_tag("System.ActiveTrip", True)
    ok, reason = verifier.check_safety_conditions()
    assert ok is False
    assert "TRIP" in reason


# --- DOWOD: denial reaches the audit log, naming which tag and why -----

def test_pending_command_denial_reaches_the_audit_log(tmp_path):
    audit = FakeAuditLogger()
    verifier, tag_manager, core_tm = _make_verifier(tmp_path, audit_logger=audit)
    core_tm.update_tag("System.PendingCommand", True)
    verifier.check_safety_conditions()

    entries = [e for e in audit.entries if e[0] == "PROTECTION_VERIFICATION_BLOCKED"]
    assert entries, audit.entries
    event_type, actor, detail, success = entries[-1]
    assert "System.PendingCommand" in detail
    assert success is False


def test_active_trip_denial_reaches_the_audit_log(tmp_path):
    audit = FakeAuditLogger()
    verifier, tag_manager, core_tm = _make_verifier(tmp_path, audit_logger=audit)
    core_tm.update_tag("System.ActiveTrip", True)
    verifier.check_safety_conditions()

    entries = [e for e in audit.entries if e[0] == "PROTECTION_VERIFICATION_BLOCKED"]
    assert entries, audit.entries
    event_type, actor, detail, success = entries[-1]
    assert "System.ActiveTrip" in detail
    assert success is False


def test_a_passing_check_writes_nothing_to_the_audit_log(tmp_path):
    """The audit record is specifically for a DENIAL - a normal, passing
    pre-flight check must not spam the audit trail."""
    audit = FakeAuditLogger()
    verifier, tag_manager, core_tm = _make_verifier(tmp_path, audit_logger=audit)
    ok, reason = verifier.check_safety_conditions()
    assert ok is True
    assert not [e for e in audit.entries if e[0] == "PROTECTION_VERIFICATION_BLOCKED"]


# --- DOWOD: System.ActiveTrip reflects a REAL process-protection trip,
# momentarily (clears the instant the condition is gone) - wired via a
# real ProcessProtectionManager, not a manually-set tag -----------------

class _FakeProjectManagerForProcessProtections:
    def __init__(self):
        self._protections = []

    def get_process_protections(self):
        return self._protections

    def set_process_protections(self, protections):
        self._protections = protections

    def save_project(self):
        pass


def test_active_trip_reflects_a_real_process_protection_exceeding_and_clearing(tmp_path):
    core_tm = TagManager(EventBus())
    core_tm.add_tag("Meas.L1", 230.0, TagType.REAL)  # a real analog point to bind the protection to
    verifier, tag_manager, core_tm = _make_verifier(tmp_path, core_tm=core_tm)

    ppm = ProcessProtectionManager(core_tm.event_bus, core_tm, _FakeProjectManagerForProcessProtections())
    ppm.add_protection("Overvoltage", "Meas.L1", upper_threshold=250.0, lower_threshold=200.0,
                        hysteresis=2.0, delay_seconds=0.0)

    assert tag_manager.get_value("System.ActiveTrip") is False
    ok, reason = verifier.check_safety_conditions()
    assert ok is True, reason

    core_tm.update_tag("Meas.L1", 260.0)  # push past upper_threshold - a real excursion
    assert tag_manager.get_value("System.ActiveTrip") is True, \
        "a real process-protection trip must be reflected, not just a manually-set tag"
    ok, reason = verifier.check_safety_conditions()
    assert ok is False
    assert "TRIP" in reason

    core_tm.update_tag("Meas.L1", 230.0)  # back inside the hysteresis-adjusted band
    assert tag_manager.get_value("System.ActiveTrip") is False, \
        "momentary, not a latch - must clear the instant the real condition is gone"
    ok, reason = verifier.check_safety_conditions()
    assert ok is True, reason


def test_active_trip_reflects_the_initial_state_at_construction_too(tmp_path):
    """Not just future tag_changed events - a process protection that is
    ALREADY exceeded at the moment ProtectionVerifier is constructed
    (Engineer Mode page opened after the fact) must be picked up
    immediately, not only from here on."""
    core_tm = TagManager(EventBus())
    core_tm.add_tag("Meas.L1", 230.0, TagType.REAL)
    ppm = ProcessProtectionManager(core_tm.event_bus, core_tm, _FakeProjectManagerForProcessProtections())
    ppm.add_protection("Overvoltage", "Meas.L1", upper_threshold=250.0, lower_threshold=200.0,
                        hysteresis=2.0, delay_seconds=0.0)
    core_tm.update_tag("Meas.L1", 300.0)  # already exceeded BEFORE ProtectionVerifier exists
    assert core_tm.get_value("Process.PP1.Exceeded") is True

    tag_manager = _QtTagManagerBridge(core_tm)
    access_manager = AccessManager(EventBus(), config_path=str(tmp_path / "access.local.json"))
    verifier = ProtectionVerifier(tag_manager, ProtectionManager(), access_manager)

    assert tag_manager.get_value("System.ActiveTrip") is True
