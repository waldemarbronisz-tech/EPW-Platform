"""Tests for per-device switching (mechanical wear) counters
(epw_os/core/switching_counters.py) - headless, no Qt needed at all."""

import time

import pytest

from epw_os.core.events import EventBus
from epw_os.core.switching_counters import SwitchingCounterManager, format_duration, new_record


class FakeProjectManager:
    """Minimal stand-in matching the ProjectManager methods this module
    actually calls - get_switching_counters()/set_switching_counters()/
    save_project() - so these tests don't need a real project.json file
    or the rest of ProjectManager's machinery."""
    def __init__(self, initial=None):
        self._data = initial or {}
        self.save_count = 0

    def get_switching_counters(self):
        return self._data

    def set_switching_counters(self, data):
        self._data = data

    def save_project(self):
        self.save_count += 1


@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def pm():
    return FakeProjectManager()


@pytest.fixture
def mgr(bus, pm):
    return SwitchingCounterManager(bus, pm)


# --- DOWÓD: counter increments on a state change ------------------------

def test_no_counting_on_the_very_first_observation(bus, mgr):
    # The first time a tag is ever seen there is no "previous" state to
    # transition from - must not be counted as a close or an open.
    bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")
    snap = mgr.get_snapshot("ELA01.DI.1")
    assert snap["closes"] == 0
    assert snap["opens"] == 0
    assert snap["first_transition"] is None


def test_close_then_open_counts_each_separately(bus, mgr):
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")  # seed - not counted
    bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")    # -> closed: 1 close
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")   # -> open: 1 open
    snap = mgr.get_snapshot("ELA01.DI.1")
    assert snap["closes"] == 1
    assert snap["opens"] == 1


def test_repeated_writes_of_the_same_value_are_not_counted(bus, mgr):
    # A duplicate/no-op tag write (same value as before) is not a real
    # switching event.
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")  # seed
    bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")   # 1 close
    bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")   # duplicate - ignored
    bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")   # duplicate - ignored
    snap = mgr.get_snapshot("ELA01.DI.1")
    assert snap["closes"] == 1
    assert snap["opens"] == 0


def test_bool_and_int_tag_values_are_both_understood(bus, mgr):
    bus.emit("tag_changed", "ELA01.DI.1", 0, "GOOD")  # seed as int
    bus.emit("tag_changed", "ELA01.DI.1", 1, "GOOD")  # close, as int
    snap = mgr.get_snapshot("ELA01.DI.1")
    assert snap["closes"] == 1


def test_multiple_cycles_accumulate(bus, mgr):
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    for _ in range(5):
        bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")
        bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    snap = mgr.get_snapshot("ELA01.DI.1")
    assert snap["closes"] == 5
    assert snap["opens"] == 5


def test_counters_are_independent_per_tag(bus, mgr):
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    bus.emit("tag_changed", "ELA01.DI.2", False, "GOOD")
    bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")
    assert mgr.get_snapshot("ELA01.DI.1")["closes"] == 1
    assert mgr.get_snapshot("ELA01.DI.2")["closes"] == 0


def test_non_digital_input_tags_are_ignored(bus, mgr):
    bus.emit("tag_changed", "ADA01.DO.1", False, "GOOD")
    bus.emit("tag_changed", "ADA01.DO.1", True, "GOOD")
    bus.emit("tag_changed", "Cabinet.Door", "CLOSED", "GOOD")
    assert mgr.get_snapshot("ADA01.DO.1") == new_record()
    assert mgr.get_snapshot("Cabinet.Door") == new_record()


def test_non_boolean_int_values_on_a_di_tag_are_ignored(bus, mgr):
    # Defensive: a DI tag should only ever carry BOOL, but a malformed
    # write must not crash the counter.
    bus.emit("tag_changed", "ELA01.DI.1", "not a bool", "GOOD")
    bus.emit("tag_changed", "ELA01.DI.1", None, "GOOD")
    snap = mgr.get_snapshot("ELA01.DI.1")
    assert snap == new_record()


# --- DOWÓD: closed time accumulates correctly ---------------------------

def test_closed_time_accumulates_between_close_and_open(bus, mgr):
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")
    time.sleep(0.2)
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    snap = mgr.get_snapshot("ELA01.DI.1")
    assert snap["closed_seconds"] >= 0.2
    assert snap["closed_seconds"] < 2.0  # sanity bound, not a hang


def test_closed_time_keeps_accruing_live_while_still_closed(bus, mgr):
    # get_snapshot() must reflect the CURRENT, still-open interval, not
    # just completed cycles - read it twice, further apart, and confirm
    # it grew.
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")
    first = mgr.get_snapshot("ELA01.DI.1")["closed_seconds"]
    time.sleep(0.15)
    second = mgr.get_snapshot("ELA01.DI.1")["closed_seconds"]
    assert second > first


def test_closed_time_does_not_grow_while_open(bus, mgr):
    bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")  # seed as closed - no count
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")  # -> open, 1 "open" recorded
    first = mgr.get_snapshot("ELA01.DI.1")["closed_seconds"]
    time.sleep(0.1)
    second = mgr.get_snapshot("ELA01.DI.1")["closed_seconds"]
    assert first == second == 0.0


def test_first_and_last_transition_timestamps(bus, mgr):
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")  # seed
    bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")
    first_snap = mgr.get_snapshot("ELA01.DI.1")
    assert first_snap["first_transition"] is not None
    assert first_snap["first_transition"] == first_snap["last_transition"]

    time.sleep(0.05)
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    second_snap = mgr.get_snapshot("ELA01.DI.1")
    assert second_snap["first_transition"] == first_snap["first_transition"], \
        "first_transition must never change once set"
    assert second_snap["last_transition"] > second_snap["first_transition"]


# --- DOWÓD: the counter survives a restart ------------------------------

def test_flush_persists_and_a_fresh_manager_restores_it(bus, pm):
    mgr1 = SwitchingCounterManager(bus, pm)
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    mgr1.flush_to_project()
    assert pm.save_count == 1

    # A brand-new manager, same (fake) project store, same bus - as if
    # the app restarted with the persisted project.json still on disk.
    bus2 = EventBus()
    mgr2 = SwitchingCounterManager(bus2, pm)
    snap = mgr2.get_snapshot("ELA01.DI.1")
    assert snap["closes"] == 1
    assert snap["opens"] == 1


def test_flush_is_a_noop_when_nothing_changed(bus, pm):
    mgr1 = SwitchingCounterManager(bus, pm)
    mgr1.flush_to_project()
    assert pm.save_count == 0, "an empty/unmodified manager must not write to disk"


def test_flush_does_not_write_on_every_tag_change_only_when_called(bus, pm):
    mgr1 = SwitchingCounterManager(bus, pm)
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")
    assert pm.save_count == 0, "GRANICE: no disk write on every state change"
    mgr1.flush_to_project()
    assert pm.save_count == 1


def test_still_closed_across_a_restart_keeps_accruing_closed_time(bus, pm):
    """The important restart case: a device that is STILL closed when
    the app restarts must not lose the closed-time it's accruing - the
    interval spans the restart, using the persisted closed_since."""
    mgr1 = SwitchingCounterManager(bus, pm)
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")  # now closed
    time.sleep(0.15)
    mgr1.flush_to_project()  # persists closed_since, still-closed

    bus2 = EventBus()
    mgr2 = SwitchingCounterManager(bus2, pm)
    # The device is observed still closed after "restart" - same value,
    # so no new transition is recorded, but closed_since carries over.
    bus2.emit("tag_changed", "ELA01.DI.1", True, "GOOD")
    snap = mgr2.get_snapshot("ELA01.DI.1")
    assert snap["closes"] == 1, "the restored state must not be double-counted as a new close"
    assert snap["closed_seconds"] >= 0.15, \
        "time closed before the restart must still count towards the total"


def test_reset_survives_restart_too(bus, pm):
    mgr1 = SwitchingCounterManager(bus, pm)
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    mgr1.reset_counter("ELA01.DI.1")
    mgr1.flush_to_project()

    bus2 = EventBus()
    mgr2 = SwitchingCounterManager(bus2, pm)
    snap = mgr2.get_snapshot("ELA01.DI.1")
    assert snap["closes"] == 0
    assert snap["opens"] == 0


def test_corrupt_persisted_record_falls_back_to_a_fresh_one(bus):
    pm = FakeProjectManager(initial={"ELA01.DI.1": "not a dict", "ELA01.DI.2": {"closes": "abc"}})
    mgr = SwitchingCounterManager(bus, pm)  # must not raise
    assert mgr.get_snapshot("ELA01.DI.1") == new_record()
    assert mgr.get_snapshot("ELA01.DI.2") == new_record()


# --- reset_counter() ------------------------------------------------

def test_reset_counter_zeroes_everything_but_keeps_the_threshold(bus, mgr):
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    mgr.set_warning_threshold("ELA01.DI.1", 10000)

    old = mgr.reset_counter("ELA01.DI.1")
    assert old["closes"] == 1
    snap = mgr.get_snapshot("ELA01.DI.1")
    assert snap["closes"] == 0
    assert snap["opens"] == 0
    assert snap["closed_seconds"] == 0.0
    assert snap["first_transition"] is None
    assert snap["last_transition"] is None
    assert snap["warning_threshold"] == 10000, "resetting wear stats must not clear the threshold"


def test_reset_while_currently_closed_keeps_tracking_from_now(bus, mgr):
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")  # currently closed
    mgr.reset_counter("ELA01.DI.1")
    time.sleep(0.1)
    snap = mgr.get_snapshot("ELA01.DI.1")
    assert snap["closes"] == 0
    assert snap["closed_seconds"] >= 0.1, \
        "a device that was closed at reset time must keep accruing closed time"


def test_reset_of_an_unknown_tag_does_not_raise(bus, mgr):
    old = mgr.reset_counter("ELA01.DI.99")
    assert old == new_record()
    assert mgr.get_snapshot("ELA01.DI.99") == new_record()


# --- warning threshold (optional, per device) ---------------------------

def test_no_threshold_by_default(bus, mgr):
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")
    assert mgr.is_over_threshold("ELA01.DI.1") is False


def test_threshold_triggers_once_reached(bus, mgr):
    mgr.set_warning_threshold("ELA01.DI.1", 3)
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    for _ in range(2):
        bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")
        bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    assert mgr.is_over_threshold("ELA01.DI.1") is False  # 2 closes so far
    bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")  # 3rd close
    assert mgr.is_over_threshold("ELA01.DI.1") is True


def test_threshold_can_be_cleared(bus, mgr):
    mgr.set_warning_threshold("ELA01.DI.1", 1)
    bus.emit("tag_changed", "ELA01.DI.1", False, "GOOD")
    bus.emit("tag_changed", "ELA01.DI.1", True, "GOOD")
    assert mgr.is_over_threshold("ELA01.DI.1") is True
    mgr.set_warning_threshold("ELA01.DI.1", None)
    assert mgr.is_over_threshold("ELA01.DI.1") is False


def test_unknown_tag_is_never_over_threshold(mgr):
    assert mgr.is_over_threshold("ELA01.DI.50") is False


# --- format_duration() --------------------------------------------------

@pytest.mark.parametrize("seconds,expected", [
    (0, "00:00:00"),
    (5, "00:00:05"),
    (65, "00:01:05"),
    (3661, "01:01:01"),
    (86400, "1d 00:00:00"),
    (90061, "1d 01:01:01"),
    (-5, "00:00:00"),
])
def test_format_duration(seconds, expected):
    assert format_duration(seconds) == expected
