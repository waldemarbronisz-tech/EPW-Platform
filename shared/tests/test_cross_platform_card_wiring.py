"""Task "migracja adresacji", etap 4 - THE actual platform-wide proof.

The vector tests (shared/addressing_grammar_vectors.json and its four
per-program drivers) prove all four programs PARSE an address string the
same way. That is necessary but not sufficient: two programs can agree
perfectly on grammar and still disagree on WHICH addresses a given card
produces - numbering from 0 instead of 1, an off-by-one at the channel
count boundary, a different channel order. Either bug would mean an
address Studio shows the user is silently not the same terminal runtime
or Logic Studio thinks it is, even though every individual address
string is perfectly well-formed on its own - exactly the gap the etap-4
follow-up asked this test to close.

This test takes ONE card definition - id "ELA01" (a DI/ELA-type card,
satisfying every program's own naming expectations for a realistic
example) with a specific channel count - and feeds it through:

  1. Studio's OWN point-registry generator (project_panels.py's
     sync_points_for_card(), the real function the point-registry UI
     calls, not a re-implementation of it here).
  2. runtime's OWN tag generator (TagManager.configure(), the real,
     only way DI/DO tags come into existence - epw_os/core/
     tag_manager.py's own docstring).
  3. Logic Studio's OWN address generator (DeviceModel.get_ela_addresses(),
     via project.settings, the real function device_explorer.py's UI
     calls).

...and asserts the three produce the EXACT SAME SET of address strings,
character for character, with no translation step in between - the same
"ELA01.DI.1".."ELA01.DI.<N>" from all three, or the test fails.

Also checks the boundary explicitly (does "ELA01.DI.<N>" exist and
"ELA01.DI.<N+1>" not exist, for the exact channel count configured) -
an off-by-one here is exactly the "numbered from 0, or channel N missing
at count N" class of bug the etap-4 follow-up named directly.

HOW TO SEE THIS TEST ACTUALLY CATCH A DIVERGENCE (not just pass because
nothing is currently broken): temporarily change ONE of the three real
call sites below to disagree - e.g. runtime/epw_os/core/tag_manager.py's
`range(1, dev.get("channels", 32) + 1)` to `range(0, dev.get("channels", 32))`
(0-based instead of 1-based) - and re-run. This was done once, by hand,
while writing this test (a bigger, deliberate divergence - the runtime
side simply not generating a card's tags at all), confirmed it failed
with a clear "runtime is missing ... / has extra ..." message, then
reverted. See the etap-4 report for the transcript.
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _extra_root in (_REPO_ROOT / "runtime", _REPO_ROOT / "studio" / "logic"):
    _extra_root_str = str(_extra_root)
    if _extra_root_str not in sys.path:
        sys.path.insert(0, _extra_root_str)

import pytest

from epw_os.core.tag_manager import TagManager
from epw_os.core.events import EventBus
from epw_os.core.addressing import is_address
from logic_studio.core.device_model import DeviceModel
from logic_studio.core.project import Project as LogicProject
from studio.shell.project_format import Card, new_project as new_studio_project
from studio.shell.project_panels import sync_points_for_card


def _studio_addresses(card_id: str, kind: str, channels: int) -> set:
    project = new_studio_project(name="cross-platform-test")
    card = Card(id=card_id, model="ELA01", kind=kind, channels=channels)
    sync_points_for_card(project, card)
    return {p.address for p in project.points}


def _runtime_addresses(card_id: str, dev_type: str, channels: int, kind: str) -> set:
    tm = TagManager(EventBus())
    tm.configure([{"id": card_id, "type": dev_type, "channels": channels}])
    return {t.name for t in tm.list_tags() if is_address(t.name, kind)}


def _logic_studio_addresses(card_id: str, channels: int) -> set:
    project = LogicProject()
    DeviceModel.set_ela_devices(project, [card_id])
    DeviceModel.set_ela_channels(project, channels)
    return set(DeviceModel.get_ela_addresses(project))


# card_id "ELA01" satisfies every program's own conventions for a
# realistic example: runtime's own tests use exactly this id for an
# "ELA" (DI) device (test_core.py::test_canonical_tags), and Logic
# Studio's set_ela_devices() only accepts "ELA<NN>"-shaped names
# (device_model.py's own is_valid_device_name()) - using anything else
# would need a second, DI-card-only naming exception just for this test.
CARD_ID = "ELA01"


@pytest.mark.parametrize("channels", [1, 5, 32])
def test_same_card_produces_identical_addresses_everywhere(channels):
    studio = _studio_addresses(CARD_ID, "DI", channels)
    runtime = _runtime_addresses(CARD_ID, "ELA", channels, "DI")
    logic = _logic_studio_addresses(CARD_ID, channels)

    expected = {f"{CARD_ID}.DI.{n}" for n in range(1, channels + 1)}

    assert studio == expected, f"Studio: missing {expected - studio}, extra {studio - expected}"
    assert runtime == expected, f"runtime: missing {expected - runtime}, extra {runtime - expected}"
    assert logic == expected, f"Logic Studio: missing {expected - logic}, extra {logic - expected}"


def test_channel_count_boundary_is_exact():
    """The etap-4 follow-up's own named risk: "czy kanał 32 istnieje przy
    channels=32" - the last channel must exist and there must be no
    channel one past it, in all three programs, not just in the
    parametrized set-equality check above (which would also catch this,
    but not name the boundary explicitly for a future reader)."""
    channels = 32
    last = f"{CARD_ID}.DI.{channels}"
    one_past = f"{CARD_ID}.DI.{channels + 1}"

    for label, addresses in (
        ("Studio", _studio_addresses(CARD_ID, "DI", channels)),
        ("runtime", _runtime_addresses(CARD_ID, "ELA", channels, "DI")),
        ("Logic Studio", _logic_studio_addresses(CARD_ID, channels)),
    ):
        assert last in addresses, f"{label}: {last} missing at channels={channels}"
        assert one_past not in addresses, f"{label}: {one_past} exists at channels={channels}"


def test_do_card_also_agrees_between_runtime_and_studio():
    """The same proof for a DO/ADA-type card - Logic Studio's own ADA
    equivalent (get_ada_addresses/set_ada_devices/set_ada_channels)
    mirrors the ELA path exactly, so this is deliberately a smaller,
    non-parametrized companion rather than a full repeat of every case
    above."""
    channels = 8
    card_id = "ADA01"

    studio = _studio_addresses(card_id, "DO", channels)
    runtime_tm = TagManager(EventBus())
    runtime_tm.configure([{"id": card_id, "type": "ADA", "channels": channels}])
    runtime = {t.name for t in runtime_tm.list_tags() if is_address(t.name, "DO")}

    logic_project = LogicProject()
    DeviceModel.set_ada_devices(logic_project, [card_id])
    DeviceModel.set_ada_channels(logic_project, channels)
    logic = set(DeviceModel.get_ada_addresses(logic_project))

    expected = {f"{card_id}.DO.{n}" for n in range(1, channels + 1)}
    assert studio == expected
    assert runtime == expected
    assert logic == expected
