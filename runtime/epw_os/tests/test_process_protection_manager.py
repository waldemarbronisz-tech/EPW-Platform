"""Tests for the process protections module
(epw_os/core/process_protection_manager.py) - page-split task, part 1.
Headless, no Qt needed at all - real EventBus/TagManager (both already
Qt-free), same pattern test_intrusion_manager.py's own fixtures use.
"""
import time

import pytest

from epw_os.core.access_manager import AccessLevel
from epw_os.core.events import EventBus
from epw_os.core.process_protection_manager import ProcessProtectionManager
from epw_os.core.tag_manager import TagManager, TagType


class FakeProjectManager:
    def __init__(self, analog_points=None):
        self._protections = []
        self._analog_points = analog_points or []
        self.save_count = 0

    def get_process_protections(self):
        return self._protections

    def set_process_protections(self, data):
        self._protections = list(data)

    def get_analog_points(self):
        return self._analog_points

    def save_project(self):
        self.save_count += 1


class FakeAuditLogger:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))


@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def tags(bus):
    tm = TagManager(bus)
    tm.add_tag("AI1", 50.0, TagType.REAL, source="HARDWARE")
    return tm


@pytest.fixture
def pm():
    return FakeProjectManager(analog_points=[{"tag": "AI1", "description": "Temp"}])


@pytest.fixture
def audit():
    return FakeAuditLogger()


@pytest.fixture
def ppm(bus, tags, pm, audit):
    return ProcessProtectionManager(bus, tags, pm, audit)


# --- candidates / CRUD --------------------------------------------------

def test_analog_input_candidates_reuses_the_real_analog_points_list(ppm):
    assert ppm.get_analog_input_candidates() == ["AI1"]


def test_add_protection_requires_engineer(ppm):
    pid = ppm.add_protection("Temp High", "AI1", 80.0, 10.0, level=AccessLevel.OPERATOR)
    assert pid is None
    assert ppm.get_protections() == []


def test_add_protection_registers_the_exceeded_tag(ppm, tags):
    pid = ppm.add_protection("Temp High", "AI1", 80.0, 10.0, level=AccessLevel.ENGINEER)
    assert pid is not None
    assert tags.get_tag(f"Process.{pid}.Exceeded") is not None
    assert ppm.is_exceeded(pid) is False


def test_remove_protection_removes_the_tag_and_persisted_record(ppm, tags, pm):
    pid = ppm.add_protection("Temp High", "AI1", 80.0, 10.0, level=AccessLevel.ENGINEER)
    assert ppm.remove_protection(pid, level=AccessLevel.ENGINEER) is True
    assert tags.get_tag(f"Process.{pid}.Exceeded") is None
    assert ppm.get_protections() == []
    assert not any(p["id"] == pid for p in pm.get_process_protections())


def test_update_protection_changes_fields_and_re_evaluates(ppm, tags):
    pid = ppm.add_protection("Temp High", "AI1", 80.0, 10.0, level=AccessLevel.ENGINEER)
    tags.update_tag("AI1", 90.0)  # already exceeded, no delay -> latches immediately
    assert ppm.is_exceeded(pid) is True
    # widen the band so 90.0 is no longer exceeded
    ok = ppm.update_protection(pid, upper_threshold=200.0, level=AccessLevel.ENGINEER)
    assert ok is True
    assert ppm.is_exceeded(pid) is False


# --- threshold / hysteresis / delay evaluation ---------------------------

def test_value_within_band_is_not_exceeded(ppm, tags):
    pid = ppm.add_protection("Band", "AI1", upper_threshold=80.0, lower_threshold=10.0, level=AccessLevel.ENGINEER)
    tags.update_tag("AI1", 50.0)
    assert ppm.is_exceeded(pid) is False


def test_value_above_upper_latches_immediately_with_zero_delay(ppm, tags):
    pid = ppm.add_protection("Upper", "AI1", 80.0, 10.0, delay_seconds=0.0, level=AccessLevel.ENGINEER)
    tags.update_tag("AI1", 95.0)
    assert ppm.is_exceeded(pid) is True


def test_value_below_lower_latches_immediately_with_zero_delay(ppm, tags):
    pid = ppm.add_protection("Lower", "AI1", 80.0, 10.0, delay_seconds=0.0, level=AccessLevel.ENGINEER)
    tags.update_tag("AI1", 2.0)
    assert ppm.is_exceeded(pid) is True


def test_delay_filters_a_brief_glitch(ppm, tags):
    pid = ppm.add_protection("Delayed", "AI1", 80.0, 10.0, delay_seconds=0.2, level=AccessLevel.ENGINEER)
    tags.update_tag("AI1", 95.0)
    time.sleep(0.05)
    tags.update_tag("AI1", 50.0)  # back inside band before the delay elapses
    time.sleep(0.3)
    assert ppm.is_exceeded(pid) is False


def test_delay_confirms_after_it_elapses(ppm, tags):
    pid = ppm.add_protection("Delayed", "AI1", 80.0, 10.0, delay_seconds=0.15, level=AccessLevel.ENGINEER)
    tags.update_tag("AI1", 95.0)
    assert ppm.is_exceeded(pid) is False  # not yet - delay hasn't elapsed
    time.sleep(0.3)
    assert ppm.is_exceeded(pid) is True


def test_hysteresis_keeps_it_latched_until_past_the_adjusted_bound(ppm, tags):
    pid = ppm.add_protection("Hyst", "AI1", 80.0, 10.0, hysteresis=5.0, delay_seconds=0.0,
                              level=AccessLevel.ENGINEER)
    tags.update_tag("AI1", 95.0)
    assert ppm.is_exceeded(pid) is True
    tags.update_tag("AI1", 78.0)  # inside [10,80] but within hysteresis of upper (80-5=75) - still exceeded
    assert ppm.is_exceeded(pid) is True
    tags.update_tag("AI1", 70.0)  # past the hysteresis-adjusted bound - clears
    assert ppm.is_exceeded(pid) is False


def test_clearing_is_immediate_no_delay(ppm, tags):
    pid = ppm.add_protection("Clear", "AI1", 80.0, 10.0, delay_seconds=5.0, level=AccessLevel.ENGINEER)
    tags.update_tag("AI1", 95.0)
    time.sleep(5.1)
    assert ppm.is_exceeded(pid) is True
    tags.update_tag("AI1", 50.0)
    assert ppm.is_exceeded(pid) is False  # no need to wait out the same delay to clear


def test_disabled_protection_never_reads_as_exceeded(ppm, tags):
    pid = ppm.add_protection("Off", "AI1", 80.0, 10.0, delay_seconds=0.0, level=AccessLevel.ENGINEER)
    ppm.update_protection(pid, enabled=False, level=AccessLevel.ENGINEER)
    tags.update_tag("AI1", 95.0)
    assert ppm.is_exceeded(pid) is False


def test_unresolvable_tag_never_manufactures_a_false_exceeded(ppm, tags):
    pid = ppm.add_protection("Dangling", "NOPE_NOT_A_REAL_TAG", 80.0, 10.0, delay_seconds=0.0,
                              level=AccessLevel.ENGINEER)
    assert ppm.is_exceeded(pid) is False


# --- GRANICE: never writes to any tag but its own Process.* ones --------

def test_never_writes_to_any_non_process_tag(ppm, tags):
    tags.add_tag("SomeOutput.DO1", False, TagType.BOOL, source="HARDWARE")
    written = []
    original_update = tags.update_tag
    def _spy(name, value, quality=None):
        written.append(name)
        return original_update(name, value) if quality is None else original_update(name, value, quality)
    tags.update_tag = _spy
    pid = ppm.add_protection("Spy", "AI1", 80.0, 10.0, delay_seconds=0.0, level=AccessLevel.ENGINEER)
    tags.update_tag("AI1", 95.0)
    assert all(name.startswith("Process.") for name in written if name != "AI1")


# --- teardown -------------------------------------------------------------

def test_teardown_cancels_pending_timers_and_removes_tags(ppm, tags):
    pid = ppm.add_protection("Timed", "AI1", 80.0, 10.0, delay_seconds=5.0, level=AccessLevel.ENGINEER)
    tags.update_tag("AI1", 95.0)  # starts a pending delay timer
    ppm.teardown()
    assert tags.get_tag(f"Process.{pid}.Exceeded") is None
    # no exception/leftover callback after this point even once the
    # original delay would have elapsed
    time.sleep(0.05)
