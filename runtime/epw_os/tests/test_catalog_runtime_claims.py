"""feat/signal-register §2.2 — the catalogue may not promise what this
controller does not compute.

Studio's Signals panel shows a "runtime support" column, read straight
off the catalogue's own `runtime` field. A field nothing checks is a
field that drifts: somebody adds a signal, marks it "served" because
everything else is, and the logic then reads a bit that never changes
for the rest of the installation's life. That failure is silent - no
error, no warning, a defined value of False for ever - which is exactly
why it is worth a test rather than a convention.

So this compares the CLAIM against the three dispatch tables that
actually answer a read: SystemSignalSource._HANDLERS (the SYS.* half),
pulse_signal_value (the clock generators, computed rather than looked
up), and SecuritySignalSource.serves (the alarm half, which keeps its own
UNSERVED_SIGNALS list for the same reason).

It runs in the RUNTIME's suite deliberately. The catalogue lives in
shared/, Studio reads it, but only EPW-OS knows what EPW-OS implements -
and Studio must never import the runtime to find out.
"""
import pytest

from epw_os.core.comm_signals import CommSignals
from epw_os.core.device_signals import DeviceSignals
from epw_os.core.logic_runtime import SystemSignalSource
from epw_os.core.point_role_signals import PointRoleSignals
from epw_os.core.runtime_state_signals import RuntimeStateSignals
from epw_os.core.security_signals import SecuritySignalSource
from shared.logic import system_signals
from shared.logic.engine.io_provider import pulse_signal_value


def _controller_answers(signal_id: str) -> bool:
    """Whether a read of `signal_id` reaches something that computes a
    value, rather than falling through to the blanket `return False`."""
    if signal_id in SystemSignalSource._HANDLERS:
        return True
    if pulse_signal_value(signal_id, 0) is not None:
        return True
    # None manager on purpose: `serves` answers from the tables, not from
    # whether an intrusion module happens to be fitted right now.
    if SecuritySignalSource(None).serves(signal_id):
        return True
    # The register's other groups (signal-register etaps): each source
    # answers serves() from its own tables, with no controller behind it.
    return any(source.serves(signal_id) for source in _REGISTER_SOURCES)


_REGISTER_SOURCES = [RuntimeStateSignals(None), CommSignals(None), PointRoleSignals(None), DeviceSignals(None)]


CATALOG = system_signals.get_all_signals()


class _Installation:
    """A project with an alarm system, so the catalogue's per-instance
    PATTERNS expand into real ids. Without one, get_all_signals() returns
    the fixed 42 and every SEC.ZONE.* claim would go unchecked - which is
    precisely where a promise with nothing behind it would hide."""
    settings = {}
    external_zones = [{"id": "PARTER", "name": "Parter"}]
    external_lines = [{"id": "L1", "name": "Drzwi"}]
    external_cards = [{"id": "ELA1", "kind": "DI", "channels": 16}, {"id": "ELA1", "kind": "AI", "channels": 8},
                      {"id": "ADA1", "kind": "DO", "channels": 16}]


EXPANDED = [s for s in system_signals.get_all_signals(_Installation())
            if s["id"] not in {c["id"] for c in CATALOG}]


def test_the_patterns_actually_expanded():
    assert len(EXPANDED) >= 20, "no per-instance signal was produced at all"


@pytest.mark.parametrize("signal", EXPANDED, ids=lambda s: s["id"])
def test_every_per_instance_signal_is_answered_too(signal):
    """A pattern promises one signal PER zone. If the controller cannot
    answer SEC.ZONE.PARTER.ARMED, the catalogue is offering the engineer
    a bit for every zone in the installation that never changes."""
    assert _controller_answers(signal["id"]), signal["id"]


def test_the_catalogue_is_not_empty():
    """A passing empty walk would prove nothing about anything."""
    assert len(CATALOG) >= 40


@pytest.mark.parametrize("signal", CATALOG, ids=lambda s: s["id"])
def test_every_signal_states_its_runtime_support(signal):
    assert signal.get("runtime") in ("served", "planned"), signal["id"]


@pytest.mark.parametrize("signal", CATALOG, ids=lambda s: s["id"])
def test_a_signal_claimed_served_really_is(signal):
    """The direction that matters: a promise with nothing behind it."""
    if signal.get("runtime") != "served":
        pytest.skip("declared planned")
    assert _controller_answers(signal["id"]), (
        f"{signal['id']} is marked \"served\" in the catalogue, but no handler, "
        f"pulse generator or SEC table answers a read of it - logic would see "
        f"its safe default for ever."
    )


@pytest.mark.parametrize("signal", CATALOG, ids=lambda s: s["id"])
def test_a_signal_the_controller_answers_is_not_hidden_as_planned(signal):
    """The other direction, so the field cannot be left stale after the
    implementation lands: a signal EPW-OS serves must say so, or Studio
    warns an engineer off something that works."""
    if signal.get("runtime") != "planned":
        pytest.skip("declared served")
    assert not _controller_answers(signal["id"]), (
        f"{signal['id']} is marked \"planned\", but this controller already "
        f"answers for it - update the catalogue."
    )


def test_a_writable_signal_the_controller_cannot_execute_is_never_served():
    """A source == "logic" command is only real if something executes it.
    Reading such a signal back is not the point - issuing it is."""
    security = SecuritySignalSource(None)
    executors = [security] + [s for s in _REGISTER_SOURCES if hasattr(s, "execute")]
    for signal in CATALOG:
        if signal.get("source") != "logic" or signal.get("runtime") != "served":
            continue
        assert any(source.serves(signal["id"]) for source in executors), (
            f"{signal['id']} is offered to the logic as a writable command and "
            f"marked served, but nothing on this controller executes it."
        )


def test_an_unknown_name_is_reported_as_planned_not_served():
    """The honest answer for a name this build has never heard of."""
    assert system_signals.runtime_status("SEC.NIE.MA.TAKIEGO") == "planned"
