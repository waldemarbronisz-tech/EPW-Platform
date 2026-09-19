"""Task "jedno źródło listy kart", etap 1: Logic Studio, embedded in
Studio, reads its card list from Studio's own project (LogicPanel.
sync_cards_from_studio()) - never from its own project.settings["ela_
devices"] default. Real widgets throughout (a fresh LogicPanel embeds
Logic Studio's real MainWindow - see logic_panel.py's own module
docstring for why that's the only separable piece), same "no fasada, no
Qt-free reimplementation of the bridge" reasoning as the rest of this
task's own cross-platform proof.
"""
import os
import tempfile

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from studio.shell.logic_panel import LogicPanel
from studio.shell.project_format import Card, new_project


def _app():
    return QApplication.instance() or QApplication([])


def _qsettings(tmp_path, name):
    return QSettings(str(tmp_path / f"{name}.ini"), QSettings.IniFormat)


def test_studio_card_becomes_a_logic_studio_device(tmp_path):
    """The exact bug report: a card added in Studio must be available in
    Logic Studio under the SAME address string, no translation."""
    _app()
    panel = LogicPanel(settings=_qsettings(tmp_path, "logic"))
    from logic_studio.core.device_model import DeviceModel
    studio_project = new_project("Test")
    studio_project.cards.append(Card(id="KARTA1", model="ELA01", channel_kinds={"DI": 4}))

    panel.sync_cards_from_studio(studio_project)

    addrs = DeviceModel.get_ela_addresses(panel.main_window().project)
    assert addrs == ["KARTA1.DI.1", "KARTA1.DI.2", "KARTA1.DI.3", "KARTA1.DI.4"]


def test_a_card_added_later_appears_after_the_next_sync(tmp_path):
    _app()
    panel = LogicPanel(settings=_qsettings(tmp_path, "logic"))
    from logic_studio.core.device_model import DeviceModel
    studio_project = new_project("Test")
    studio_project.cards.append(Card(id="ELA1", model="ELA01", channel_kinds={"DI": 2}))
    panel.sync_cards_from_studio(studio_project)
    assert len(DeviceModel.get_ela_addresses(panel.main_window().project)) == 2

    studio_project.cards.append(Card(id="ELA2", model="ELA01", channel_kinds={"DI": 2}))
    panel.sync_cards_from_studio(studio_project)

    addrs = DeviceModel.get_ela_addresses(panel.main_window().project)
    assert "ELA2.DI.1" in addrs and "ELA2.DI.2" in addrs


def test_a_removed_card_disappears_from_the_address_list(tmp_path):
    """1.1's own acceptance criterion: "usunięcie karty -> jej adresy
    znikają z listy wyboru"."""
    _app()
    panel = LogicPanel(settings=_qsettings(tmp_path, "logic"))
    from logic_studio.core.device_model import DeviceModel
    studio_project = new_project("Test")
    card = Card(id="ELA1", model="ELA01", channel_kinds={"DI": 2})
    studio_project.cards.append(card)
    panel.sync_cards_from_studio(studio_project)
    assert DeviceModel.get_ela_addresses(panel.main_window().project) == ["ELA1.DI.1", "ELA1.DI.2"]

    studio_project.cards.remove(card)
    panel.sync_cards_from_studio(studio_project)

    assert DeviceModel.get_ela_addresses(panel.main_window().project) == []


def test_zero_cards_gives_zero_devices_not_a_silent_default(tmp_path):
    _app()
    panel = LogicPanel(settings=_qsettings(tmp_path, "logic"))
    from logic_studio.core.device_model import DeviceModel
    panel.sync_cards_from_studio(new_project("Test"))

    project = panel.main_window().project
    assert DeviceModel.get_ela_devices(project) == []
    assert DeviceModel.get_ada_devices(project) == []


def test_cards_with_different_channel_counts_are_not_flattened(tmp_path):
    """A real limitation the OLD project.settings["ela_channels"]
    mechanism had (one shared count for every device) - the bridge must
    not reintroduce it."""
    _app()
    panel = LogicPanel(settings=_qsettings(tmp_path, "logic"))
    from logic_studio.core.device_model import DeviceModel
    studio_project = new_project("Test")
    studio_project.cards.append(Card(id="ELA1", model="ELA01", channel_kinds={"DI": 8}))
    studio_project.cards.append(Card(id="ELA2", model="ELA01", channel_kinds={"DI": 16}))
    panel.sync_cards_from_studio(studio_project)

    project = panel.main_window().project
    pairs = dict(DeviceModel.get_ela_device_channels(project))
    assert pairs == {"ELA1": 8, "ELA2": 16}


def test_a_card_with_more_than_one_kind_reaches_both_families(tmp_path):
    """User report: "karta ELA1 ma DI oraz AI" - one Studio Card with
    two kinds must flatten to a DI entry AND an AI entry in
    external_cards, both under the same id, not just whichever kind
    happens to be checked first."""
    _app()
    panel = LogicPanel(settings=_qsettings(tmp_path, "logic"))
    from logic_studio.core.device_model import DeviceModel
    studio_project = new_project("Test")
    studio_project.cards.append(Card(id="ELA1", model="ELA01", channel_kinds={"DI": 8, "AI": 4}))
    panel.sync_cards_from_studio(studio_project)

    project = panel.main_window().project
    assert DeviceModel.get_ela_addresses(project) == [f"ELA1.DI.{n}" for n in range(1, 9)]
    # AI has no Logic Studio module-list equivalent (device_model.py's
    # own docstring) - it must not have silently swallowed the DI
    # entry either, so this is really proving the flat-map covers DI,
    # not that AI is expected to show up here too.
    assert dict(DeviceModel.get_ela_device_channels(project)) == {"ELA1": 8}


def test_resyncing_with_no_change_does_not_rebuild_panels(tmp_path):
    """Etap 4 concern: switching to Logika (or any unrelated Studio edit)
    must not pay the cost of rebuilding device_explorer/simulation every
    time - only when the card list actually changed."""
    _app()
    panel = LogicPanel(settings=_qsettings(tmp_path, "logic"))
    studio_project = new_project("Test")
    studio_project.cards.append(Card(id="ELA1", model="ELA01", channel_kinds={"DI": 2}))
    panel.sync_cards_from_studio(studio_project)

    calls = []
    panel.main_window()._refresh_project_dependent_panels = lambda: calls.append(1)
    panel.sync_cards_from_studio(studio_project)  # nothing changed
    assert calls == []

    studio_project.metadata.description = "unrelated edit"
    panel.sync_cards_from_studio(studio_project)  # still nothing card-related changed
    assert calls == []

    studio_project.cards.append(Card(id="ELA2", model="ELA01", channel_kinds={"DI": 2}))
    panel.sync_cards_from_studio(studio_project)  # a real card change
    assert calls == [1]


# ---- the analog half of the same bridge ------------------------------------
# User report ("informacja, gdy nie ma kart"): while writing that notice it
# turned out an embedded Logic Studio had no analog addresses AT ALL - the
# bridge above covered DI/DO only, so every AI/AO block's Address dropdown
# was empty in Studio however many analog channels the cards declared, and
# the compiler had no engineering range to resolve for an AI block's
# quality check. A DI/DO channel is fully described by its address; an
# analog one also needs the range and unit, which live on Studio's own
# points - so the points, not just the cards, are what crosses here.

def _studio_project_with_analog_card(card_id="ELA1", kinds=None):
    from studio.shell.project_panels import sync_points_for_card
    studio_project = new_project("Test")
    card = Card(id=card_id, model="ELA01", channel_kinds=kinds or {"AI": 2})
    studio_project.cards.append(card)
    sync_points_for_card(studio_project, card)
    return studio_project


def test_an_analog_card_brings_its_input_points_into_logic_studio(tmp_path):
    _app()
    panel = LogicPanel(settings=_qsettings(tmp_path, "logic"))
    from logic_studio.core.device_model import DeviceModel

    panel.sync_cards_from_studio(_studio_project_with_analog_card())

    project = panel.main_window().project
    assert DeviceModel.get_analog_input_addresses(project) == ["ELA1.AI.1", "ELA1.AI.2"]
    assert DeviceModel.get_analog_output_addresses(project) == []


def test_an_analog_output_card_arrives_with_direction_output(tmp_path):
    _app()
    panel = LogicPanel(settings=_qsettings(tmp_path, "logic"))
    from logic_studio.core.device_model import DeviceModel

    panel.sync_cards_from_studio(_studio_project_with_analog_card("ADA1", {"AO": 3}))

    project = panel.main_window().project
    assert DeviceModel.get_analog_output_addresses(project) == ["ADA1.AO.1", "ADA1.AO.2", "ADA1.AO.3"]
    assert DeviceModel.get_analog_input_addresses(project) == []


def test_the_points_carry_studios_own_range_and_unit(tmp_path):
    """What the compiler resolves into the runtime export for an AI
    block's out-of-range check (Compiler.compile()'s set_range()) - it
    has to be the range the engineer typed in Studio's point registry,
    not a default invented at the bridge."""
    _app()
    panel = LogicPanel(settings=_qsettings(tmp_path, "logic"))
    from logic_studio.core.device_model import DeviceModel

    studio_project = _studio_project_with_analog_card()
    point = next(p for p in studio_project.points if p.address == "ELA1.AI.1")
    point.description = "Outside temperature"
    point.eng_min, point.eng_max, point.unit = -30.0, 60.0, "degC"
    panel.sync_cards_from_studio(studio_project)

    resolved = DeviceModel.get_analog_point(panel.main_window().project, "ELA1.AI.1")
    assert resolved["min"] == -30.0 and resolved["max"] == 60.0
    assert resolved["unit"] == "degC"
    assert resolved["name"] == "Outside temperature"


def test_a_digital_card_contributes_no_analog_points(tmp_path):
    _app()
    panel = LogicPanel(settings=_qsettings(tmp_path, "logic"))
    from logic_studio.core.device_model import DeviceModel

    panel.sync_cards_from_studio(_studio_project_with_analog_card("ELA1", {"DI": 4}))

    project = panel.main_window().project
    assert DeviceModel.get_analog_points(project) == []
    assert len(DeviceModel.get_ela_addresses(project)) == 4


def test_changing_only_a_points_range_still_reaches_logic_studio(tmp_path):
    """The re-sync guard compares both halves now - a range edited in the
    point registry (no card added or removed) must not be swallowed as
    "nothing changed"."""
    _app()
    panel = LogicPanel(settings=_qsettings(tmp_path, "logic"))
    from logic_studio.core.device_model import DeviceModel

    studio_project = _studio_project_with_analog_card()
    panel.sync_cards_from_studio(studio_project)
    next(p for p in studio_project.points if p.address == "ELA1.AI.1").eng_max = 250.0
    panel.sync_cards_from_studio(studio_project)

    assert DeviceModel.get_analog_point(panel.main_window().project, "ELA1.AI.1")["max"] == 250.0
