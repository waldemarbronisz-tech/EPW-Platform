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
    studio_project.cards.append(Card(id="KARTA1", model="ELA01", kind="DI", channels=4))

    panel.sync_cards_from_studio(studio_project)

    addrs = DeviceModel.get_ela_addresses(panel.main_window().project)
    assert addrs == ["KARTA1.DI.1", "KARTA1.DI.2", "KARTA1.DI.3", "KARTA1.DI.4"]


def test_a_card_added_later_appears_after_the_next_sync(tmp_path):
    _app()
    panel = LogicPanel(settings=_qsettings(tmp_path, "logic"))
    from logic_studio.core.device_model import DeviceModel
    studio_project = new_project("Test")
    studio_project.cards.append(Card(id="ELA1", model="ELA01", kind="DI", channels=2))
    panel.sync_cards_from_studio(studio_project)
    assert len(DeviceModel.get_ela_addresses(panel.main_window().project)) == 2

    studio_project.cards.append(Card(id="ELA2", model="ELA01", kind="DI", channels=2))
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
    card = Card(id="ELA1", model="ELA01", kind="DI", channels=2)
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
    studio_project.cards.append(Card(id="ELA1", model="ELA01", kind="DI", channels=8))
    studio_project.cards.append(Card(id="ELA2", model="ELA01", kind="DI", channels=16))
    panel.sync_cards_from_studio(studio_project)

    project = panel.main_window().project
    pairs = dict(DeviceModel.get_ela_device_channels(project))
    assert pairs == {"ELA1": 8, "ELA2": 16}


def test_resyncing_with_no_change_does_not_rebuild_panels(tmp_path):
    """Etap 4 concern: switching to Logika (or any unrelated Studio edit)
    must not pay the cost of rebuilding device_explorer/simulation every
    time - only when the card list actually changed."""
    _app()
    panel = LogicPanel(settings=_qsettings(tmp_path, "logic"))
    studio_project = new_project("Test")
    studio_project.cards.append(Card(id="ELA1", model="ELA01", kind="DI", channels=2))
    panel.sync_cards_from_studio(studio_project)

    calls = []
    panel.main_window()._refresh_project_dependent_panels = lambda: calls.append(1)
    panel.sync_cards_from_studio(studio_project)  # nothing changed
    assert calls == []

    studio_project.metadata.description = "unrelated edit"
    panel.sync_cards_from_studio(studio_project)  # still nothing card-related changed
    assert calls == []

    studio_project.cards.append(Card(id="ELA2", model="ELA01", kind="DI", channels=2))
    panel.sync_cards_from_studio(studio_project)  # a real card change
    assert calls == [1]
