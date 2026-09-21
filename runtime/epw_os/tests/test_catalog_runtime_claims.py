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
up), and SswinSignalSource.serves (the alarm half, which keeps its own
UNSERVED_SIGNALS list for the same reason).

It runs in the RUNTIME's suite deliberately. The catalogue lives in
shared/, Studio reads it, but only EPW-OS knows what EPW-OS implements -
and Studio must never import the runtime to find out.
"""
import pytest

from epw_os.core.logic_runtime import SystemSignalSource
from epw_os.core.sswin_signals import SswinSignalSource
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
    return SswinSignalSource(None).serves(signal_id)


CATALOG = system_signals.get_all_signals()


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
        f"pulse generator or SSWIN table answers a read of it - logic would see "
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
    sswin = SswinSignalSource(None)
    for signal in CATALOG:
        if signal.get("source") != "logic" or signal.get("runtime") != "served":
            continue
        assert sswin.serves(signal["id"]), (
            f"{signal['id']} is offered to the logic as a writable command and "
            f"marked served, but nothing on this controller executes it."
        )


def test_an_unknown_name_is_reported_as_planned_not_served():
    """The honest answer for a name this build has never heard of."""
    assert system_signals.runtime_status("SEC.NIE.MA.TAKIEGO") == "planned"
