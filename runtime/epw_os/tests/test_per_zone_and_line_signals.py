"""feat/signal-register §3.3 — one signal per zone, one per line.

The register writes these as patterns: SEC.ZONE.<zone_id>.ARMED. The
catalogue holds the pattern (the platform really does fix that every
zone HAS an ARMED, what it means and what type it is) and the project
supplies the zones, so an engineer picks SEC.ZONE.PARTER.ARMED.

This end is the half that makes it real. The tests below are about
VALUES, not about whether a name is accepted: a per-zone signal that
answers "served" and then never changes is precisely the facade this
whole task exists to avoid, and it fails silently - a defined False, for
ever, with nothing in any log.

They also pin the two judgement calls this file makes, so neither can be
quietly changed:
  * a zone's FAULT is "any line of this zone in a fault state" - the
    manager has no per-zone fault flag, and this is what it CAN answer
    truthfully rather than what would be convenient to invent;
  * a request naming a zone that does not exist is REFUSED and logged,
    not silently dropped, because a request that does nothing is
    otherwise indistinguishable from one that worked.
"""
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core.intrusion_manager import LineState, ZoneState
from epw_os.core.security_signals import SecuritySignalSource, _parse_instance_signal
from epw_os.tests.test_security_signals_and_retentive import FakeIntrusion


def _source(**kwargs):
    return SecuritySignalSource(FakeIntrusion(**kwargs))


# --- reading the name ---------------------------------------------------------

def test_a_per_instance_name_is_taken_apart_correctly():
    assert _parse_instance_signal("SEC.ZONE.PARTER.ARMED") == ("ZONE", "PARTER", "ARMED")
    assert _parse_instance_signal("SEC.LINE.L1.VIOLATED") == ("LINE", "L1", "VIOLATED")
    assert _parse_instance_signal("REQ.SEC.ZONE.PARTER.ARM") == ("ZONE", "PARTER", "ARM")


def test_a_suffix_this_controller_does_not_implement_is_not_claimed():
    """The register has SEC.ZONE.<id>.INHIBITED; nothing here answers it,
    so it must not be recognised - claiming it would be the promise with
    nothing behind it."""
    assert _parse_instance_signal("SEC.ZONE.PARTER.INHIBITED") is None
    assert _parse_instance_signal("REQ.SEC.ZONE.PARTER.BYPASS") is None


def test_a_state_is_not_mistaken_for_a_request_or_the_other_way_round():
    """ARM is a request and ARMED is a state; reading one or issuing the
    other must not resolve."""
    assert _parse_instance_signal("SEC.ZONE.PARTER.ARM") is None
    assert _parse_instance_signal("REQ.SEC.ZONE.PARTER.ARMED") is None


def test_the_system_wide_signals_are_not_parsed_as_per_instance():
    assert _parse_instance_signal("SEC.SYSTEM.ARMED") is None
    assert _parse_instance_signal("REQ.SEC.ARM_ALL") is None


def test_a_zone_that_does_not_exist_is_still_a_name_this_controller_knows():
    """serves() answers from the tables, not from today's zone list: a
    zone can be added or removed while the controller runs, and "no
    implementation" is a different statement from "that zone is gone"."""
    source = _source(zones={})

    assert source.serves("SEC.ZONE.NOWA.ARMED")


# --- reading the value --------------------------------------------------------

def test_each_zone_reports_its_own_state_not_the_systems():
    """The whole point of per-zone signals: one zone armed while another
    is not must read differently."""
    source = _source(zones={"PARTER": ZoneState.ARMED, "PIETRO": ZoneState.DISARMED})

    assert source.read("SEC.ZONE.PARTER.ARMED") is True
    assert source.read("SEC.ZONE.PIETRO.ARMED") is False
    assert source.read("SEC.ZONE.PIETRO.DISARMED") is True


def test_a_zone_in_alarm_says_so_while_its_neighbour_does_not():
    source = _source(zones={"PARTER": ZoneState.ALARM, "PIETRO": ZoneState.ARMED})

    assert source.read("SEC.ZONE.PARTER.ALARM") is True
    assert source.read("SEC.ZONE.PIETRO.ALARM") is False


def test_the_countdowns_are_per_zone_too():
    source = _source(zones={"A": ZoneState.EXIT_DELAY, "B": ZoneState.ENTRY_DELAY})

    assert source.read("SEC.ZONE.A.EXIT_DELAY") is True
    assert source.read("SEC.ZONE.A.ENTRY_DELAY") is False
    assert source.read("SEC.ZONE.B.ENTRY_DELAY") is True


def test_alarm_memory_follows_the_zone_that_has_it():
    source = _source(zones={"A": ZoneState.DISARMED, "B": ZoneState.DISARMED})
    source.intrusion_manager.memory["A"] = {"active": True, "first_cause_line_id": "L1"}

    assert source.read("SEC.ZONE.A.ALARM_MEMORY") is True
    assert source.read("SEC.ZONE.B.ALARM_MEMORY") is False


def test_the_walk_test_is_per_zone():
    source = _source(zones={"A": ZoneState.DISARMED, "B": ZoneState.DISARMED})
    source.intrusion_manager.start_walk_test("A", actor="TEST")

    assert source.read("SEC.ZONE.A.WALK_TEST") is True
    assert source.read("SEC.ZONE.B.WALK_TEST") is False


def test_a_zones_fault_is_a_fault_on_one_of_its_own_lines():
    """The judgement call, pinned: the manager has no per-zone fault
    flag, so this aggregates over the zone's lines - and must not pick up
    a fault in a DIFFERENT zone."""
    source = _source(
        zones={"A": ZoneState.DISARMED, "B": ZoneState.DISARMED},
        lines={"L1": {"zone_id": "A", "fault": True},
               "L2": {"zone_id": "B", "fault": False}},
    )

    assert source.read("SEC.ZONE.A.FAULT") is True
    assert source.read("SEC.ZONE.B.FAULT") is False


def test_a_zone_is_bypassed_when_one_of_its_lines_is():
    source = _source(
        zones={"A": ZoneState.DISARMED, "B": ZoneState.DISARMED},
        lines={"L1": {"zone_id": "A", "bypassed": True},
               "L2": {"zone_id": "B", "bypassed": False}},
    )

    assert source.read("SEC.ZONE.A.BYPASSED") is True
    assert source.read("SEC.ZONE.B.BYPASSED") is False


# --- the lines ----------------------------------------------------------------

def test_each_line_reports_its_own_classified_state():
    source = _source(lines={
        "L1": {"state": LineState.SECURE},
        "L2": {"state": LineState.TAMPER},
        "L3": {"state": LineState.SHORT},
    })

    assert source.read("SEC.LINE.L1.SECURE") is True
    assert source.read("SEC.LINE.L2.TAMPER") is True
    assert source.read("SEC.LINE.L3.SHORT") is True
    assert source.read("SEC.LINE.L1.TAMPER") is False


def test_the_registers_open_fault_is_this_controllers_fault_open():
    """The register names the signal, the code names the state. Getting
    this pair wrong produces a signal that is never true."""
    source = _source(lines={"L1": {"state": LineState.FAULT_OPEN}})

    assert source.read("SEC.LINE.L1.OPEN_FAULT") is True


def test_violated_bypassed_and_suspect_come_from_their_own_questions():
    source = _source(lines={"L1": {"violated": True, "bypassed": True, "suspect": True}})

    assert source.read("SEC.LINE.L1.VIOLATED") is True
    assert source.read("SEC.LINE.L1.BYPASSED") is True
    assert source.read("SEC.LINE.L1.SUSPECT") is True


def test_a_controller_with_no_intrusion_module_answers_safely():
    """Logic reading a zone signal on a controller without the alarm
    system must see "nothing is armed", not an exception mid-scan."""
    source = SecuritySignalSource(None)

    assert source.read("SEC.ZONE.PARTER.ARMED") is False
    assert source.read("SEC.LINE.L1.VIOLATED") is False


# --- the requests -------------------------------------------------------------

def test_a_per_zone_request_reaches_only_that_zone():
    """The system-wide REQ.SEC.ARM_ALL acts on every zone; this one must
    not."""
    source = _source(zones={"A": ZoneState.DISARMED, "B": ZoneState.DISARMED})

    assert source.execute("REQ.SEC.ZONE.A.ARM", actor="LOGIC") is True

    assert source.intrusion_manager.calls == [("arm", "A", "LOGIC")]


def test_disarming_one_zone_leaves_the_others_alone():
    source = _source(zones={"A": ZoneState.ARMED, "B": ZoneState.ARMED})

    source.execute("REQ.SEC.ZONE.B.DISARM", actor="LOGIC")

    assert source.intrusion_manager.calls == [("disarm", "B", "LOGIC")]


def test_clearing_one_zones_memory_is_not_clearing_every_zones():
    source = _source(zones={"A": ZoneState.DISARMED, "B": ZoneState.DISARMED})

    source.execute("REQ.SEC.ZONE.A.CLEAR_MEMORY", actor="LOGIC")

    assert source.intrusion_manager.calls == [("reset", "A", "LOGIC")]


def test_the_walk_test_can_be_started_and_stopped_from_the_logic():
    source = _source(zones={"A": ZoneState.DISARMED})

    assert source.execute("REQ.SEC.ZONE.A.START_WALK_TEST", actor="LOGIC") is True
    assert source.read("SEC.ZONE.A.WALK_TEST") is True

    assert source.execute("REQ.SEC.ZONE.A.STOP_WALK_TEST", actor="LOGIC") is True
    assert source.read("SEC.ZONE.A.WALK_TEST") is False


def test_a_request_the_manager_refuses_reports_failure_rather_than_success():
    """A violated line refuses an arm. The logic must be able to tell."""
    source = _source(zones={"A": ZoneState.DISARMED})
    source.intrusion_manager.arm_succeeds = False

    assert source.execute("REQ.SEC.ZONE.A.ARM", actor="LOGIC") is False


def test_a_request_naming_a_zone_that_does_not_exist_is_refused(caplog):
    """Not silently dropped: a request that does nothing is otherwise
    indistinguishable from one that worked."""
    source = _source(zones={"A": ZoneState.DISARMED})

    assert source.execute("REQ.SEC.ZONE.NIEMA.ARM", actor="LOGIC") is False
    assert source.intrusion_manager.calls == []


def test_a_zone_request_does_nothing_without_an_intrusion_module():
    source = SecuritySignalSource(None)

    assert source.execute("REQ.SEC.ZONE.A.ARM", actor="LOGIC") is False


def test_reading_a_request_is_not_a_thing():
    """REQ.SEC.ZONE.<id>.ARM is something you issue, not something you
    read back - read() must not answer for it as though it were state."""
    source = _source(zones={"A": ZoneState.DISARMED})

    assert source.read("REQ.SEC.ZONE.A.ARM") is None
