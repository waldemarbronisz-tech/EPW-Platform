"""Tests for CommandManager's own command lifecycle - specifically the
System.PendingCommand tag (Task: "warunki bezpieczenstwa przed testem
zabezpieczenia faktycznie dzialaja" - protection_verifier.py's own
check_safety_conditions() pre-flight gate reads this tag, but nothing
ever wrote to it. This file covers the WRITE side; see
test_protection_verifier.py for the READ side / the full precondition-
blocking behavior).

Built from small, real, headless core objects (EventBus/TagManager) plus
lightweight fakes for SafetyKernel/logic_engine/driver_manager - no Qt,
no real threads except the real threading.Timer CommandManager itself
uses for its own supervision timeout (kept short in these tests, and
_on_timeout() is also called directly where a test wants a fully
deterministic "timeout happened" without any real waiting at all).
"""
import time

import pytest

from epw_os.core.command_manager import CommandManager, CommandState
from epw_os.core.events import EventBus
from epw_os.core.tag_manager import TagManager


class _AllowAllSafetyKernel:
    def validate_command_safety(self, target, action):
        return True, ""


class _DenyingSafetyKernel:
    def validate_command_safety(self, target, action):
        return False, "Simulated safety block"


class _AllowAllLogicEngine:
    def validate_command(self, target, action):
        return True, []


class _FakeDriverManager:
    """route_command() succeeds by default; `fail_next` makes exactly
    one future call return False (simulating a real dispatch failure)
    without ever touching a real driver/thread."""
    def __init__(self):
        self.route_calls = []
        self.fail_next = False

    def route_command(self, driver_id, output_tag, output_value):
        self.route_calls.append((driver_id, output_tag, output_value))
        if self.fail_next:
            self.fail_next = False
            return False
        return True


def _make_manager(driver_manager=None, safety_kernel=None):
    bus = EventBus()
    tag_manager = TagManager(bus)
    cm = CommandManager(
        tag_manager, _AllowAllLogicEngine(), safety_kernel or _AllowAllSafetyKernel(), bus,
        driver_manager=driver_manager if driver_manager is not None else _FakeDriverManager(),
    )
    return cm, tag_manager, bus


# --- DOWOD: registered immediately, before any command ever runs -------

def test_system_pending_command_registered_and_false_at_construction():
    cm, tag_manager, bus = _make_manager()
    assert tag_manager.get_value("System.PendingCommand") is False


# --- DOWOD: True during a command, False after - success -------------

def test_pending_true_during_command_false_after_success_feedback():
    driver_manager = _FakeDriverManager()
    cm, tag_manager, bus = _make_manager(driver_manager=driver_manager)
    cm.load_definitions({
        "DEV1.CLOSE": {"driver_id": "SIM", "output_tag": "OUT1", "output_value": True,
                        "feedback_tag": "FB1", "feedback_value": True, "timeout_ms": 5000},
    })

    rec = cm.request_command_ex("DEV1", "CLOSE")
    assert rec.state == CommandState.FEEDBACK_PENDING
    assert tag_manager.get_value("System.PendingCommand") is True, "must be True while awaiting feedback"

    # Real feedback arriving, exactly as a driver/plant would report it.
    bus.emit("tag_changed", "FB1", True, "GOOD")

    assert tag_manager.get_value("System.PendingCommand") is False, \
        "must be False the instant feedback resolves the command"


# --- DOWOD: False after a DENIED command (never entered pending) -------

def test_pending_stays_false_for_a_denied_command():
    cm, tag_manager, bus = _make_manager(safety_kernel=_DenyingSafetyKernel())
    cm.load_definitions({
        "DEV1.CLOSE": {"driver_id": "SIM", "output_tag": "OUT1", "output_value": True,
                        "feedback_tag": "FB1", "feedback_value": True, "timeout_ms": 5000},
    })
    rec = cm.request_command_ex("DEV1", "CLOSE")
    assert rec.state == CommandState.BLOCKED
    assert tag_manager.get_value("System.PendingCommand") is False


# --- DOWOD: a lost/never-arriving confirmation does not leave the tag
# stuck True forever - the supervision-timeout path always clears it --

def test_lost_feedback_timeout_clears_the_tag_not_stuck_true_forever():
    driver_manager = _FakeDriverManager()
    cm, tag_manager, bus = _make_manager(driver_manager=driver_manager)
    cm.load_definitions({
        "DEV1.CLOSE": {"driver_id": "SIM", "output_tag": "OUT1", "output_value": True,
                        "feedback_tag": "FB1", "feedback_value": True, "timeout_ms": 5000},
    })
    rec = cm.request_command_ex("DEV1", "CLOSE")
    assert tag_manager.get_value("System.PendingCommand") is True

    # Simulate the supervision timeout firing directly (deterministic -
    # no real 5s wait) - exactly what CommandManager's own
    # threading.Timer would call on its own after timeout_ms elapses.
    cm._on_timeout(rec.id)

    assert rec.state == CommandState.TIMEOUT
    assert tag_manager.get_value("System.PendingCommand") is False, \
        "a lost confirmation must never leave this tag True forever"


def test_real_supervision_timer_also_clears_the_tag():
    """Not just _on_timeout() called directly - the REAL
    threading.Timer path (a short real timeout, no feedback ever sent)
    genuinely fires and clears the tag on its own."""
    driver_manager = _FakeDriverManager()
    cm, tag_manager, bus = _make_manager(driver_manager=driver_manager)
    cm.load_definitions({
        "DEV1.CLOSE": {"driver_id": "SIM", "output_tag": "OUT1", "output_value": True,
                        "feedback_tag": "FB1", "feedback_value": True, "timeout_ms": 80},
    })
    rec = cm.request_command_ex("DEV1", "CLOSE")
    assert tag_manager.get_value("System.PendingCommand") is True

    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and tag_manager.get_value("System.PendingCommand") is True:
        time.sleep(0.01)

    assert tag_manager.get_value("System.PendingCommand") is False
    assert rec.state == CommandState.TIMEOUT


# --- DOWOD: False after a driver-routing FAILURE ------------------------

def test_pending_false_after_driver_routing_failure():
    driver_manager = _FakeDriverManager()
    driver_manager.fail_next = True
    cm, tag_manager, bus = _make_manager(driver_manager=driver_manager)
    cm.load_definitions({
        "DEV1.CLOSE": {"driver_id": "SIM", "output_tag": "OUT1", "output_value": True,
                        "feedback_tag": "FB1", "feedback_value": True, "timeout_ms": 5000},
    })
    rec = cm.request_command_ex("DEV1", "CLOSE")
    assert rec.state == CommandState.FAILED
    assert tag_manager.get_value("System.PendingCommand") is False


# --- DOWOD: a command with no feedback_tag never lingers pending -------

def test_command_with_no_feedback_tag_never_leaves_the_tag_true():
    driver_manager = _FakeDriverManager()
    cm, tag_manager, bus = _make_manager(driver_manager=driver_manager)
    cm.load_definitions({
        "DEV1.CLOSE": {"driver_id": "SIM", "output_tag": "OUT1", "output_value": True, "timeout_ms": 1500},
    })
    rec = cm.request_command_ex("DEV1", "CLOSE")
    assert rec.state == CommandState.SUCCESS
    assert tag_manager.get_value("System.PendingCommand") is False


# --- DOWOD (decision): "kilka komend naraz" - a flag ("is ANYTHING
# pending"), not a counter - stays True until the LAST one resolves ----

def test_multiple_concurrent_commands_tag_stays_true_until_the_last_resolves():
    driver_manager = _FakeDriverManager()
    cm, tag_manager, bus = _make_manager(driver_manager=driver_manager)
    cm.load_definitions({
        "DEV1.CLOSE": {"driver_id": "SIM", "output_tag": "OUT1", "output_value": True,
                        "feedback_tag": "FB1", "feedback_value": True, "timeout_ms": 5000},
        "DEV2.CLOSE": {"driver_id": "SIM", "output_tag": "OUT2", "output_value": True,
                        "feedback_tag": "FB2", "feedback_value": True, "timeout_ms": 5000},
    })

    rec1 = cm.request_command_ex("DEV1", "CLOSE")
    rec2 = cm.request_command_ex("DEV2", "CLOSE")
    assert tag_manager.get_value("System.PendingCommand") is True
    assert len(cm._pending_commands) == 2

    bus.emit("tag_changed", "FB1", True, "GOOD")  # resolve the first
    assert tag_manager.get_value("System.PendingCommand") is True, \
        "one command resolving must not clear the flag while another is still pending"
    assert len(cm._pending_commands) == 1

    bus.emit("tag_changed", "FB2", True, "GOOD")  # resolve the second (last)
    assert tag_manager.get_value("System.PendingCommand") is False, \
        "must clear only once EVERY pending command has resolved"
    assert len(cm._pending_commands) == 0


def test_synchronous_self_referential_feedback_still_updates_the_tag_correctly():
    """The pre-existing self-referential-command edge case
    (output_tag == feedback_tag, resolved SYNCHRONOUSLY inside
    route_command() itself - see request_command_ex()'s own comment) -
    the tag must still end up False, not stuck True from an entry that
    was already resolved before request_command_ex() even returned."""
    bus = EventBus()
    tag_manager = TagManager(bus)

    class _SelfResolvingDriverManager:
        def route_command(self, driver_id, output_tag, output_value):
            bus.emit("tag_changed", output_tag, output_value, "GOOD")
            return True

    cm = CommandManager(tag_manager, _AllowAllLogicEngine(), _AllowAllSafetyKernel(), bus,
                         driver_manager=_SelfResolvingDriverManager())
    cm.load_definitions({
        "DEV1.CLOSE": {"driver_id": "SIM", "output_tag": "SAME_TAG", "output_value": True,
                        "feedback_tag": "SAME_TAG", "feedback_value": True, "timeout_ms": 5000},
    })
    rec = cm.request_command_ex("DEV1", "CLOSE")
    assert rec.state == CommandState.SUCCESS
    assert tag_manager.get_value("System.PendingCommand") is False
