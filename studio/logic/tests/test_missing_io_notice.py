"""User report: "gdy w logice dodajemy coś, co wymaga fizycznego wejścia
lub wyjścia, a nie ma kart, niech wyskoczy informacja".

Placing a DI block in a project with no DI card used to produce an
Address dropdown that was simply EMPTY - the same blank box you get for
"no cards at all" and for "cards exist, none of this kind" - with the
real explanation arriving only at compile time, as "Invalid DI Address:
''". These tests cover the three places that now say it out loud:
core/io_availability.py (the sentence itself), the Address editor (what
the dropdown shows and what opening it does) and the canvas (the drop).
"""
import pytest
from PySide6.QtWidgets import QApplication, QComboBox, QMessageBox

from shared.logic.blocks import register_builtin_blocks
from shared.logic.blocks.registry import BlockRegistry
from logic_studio.core import io_availability
from logic_studio.core.project import Project
from logic_studio.ui.panels.property_grid import PropertyGridPanel, _MissingIOCombo

register_builtin_blocks()


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _project_with_cards():
    project = Project()
    project.settings["ela_devices"] = ["ELA01"]
    project.settings["ada_devices"] = ["ADA01"]
    project.settings["analog_points"] = [
        {"address": "AI.1", "name": "", "unit": "%", "min": 0.0, "max": 100.0, "direction": "input"},
        {"address": "AO.1", "name": "", "unit": "%", "min": 0.0, "max": 100.0, "direction": "output"},
    ]
    return project


# ---- the sentence --------------------------------------------------------

@pytest.mark.parametrize("type_id,kind", [
    ("input.di", "DI"), ("output.do", "DO"), ("input.ai", "AI"), ("output.ao", "AO"),
])
def test_an_empty_project_explains_which_kind_is_missing(type_id, kind):
    message = io_availability.missing_io_message(Project(), type_id)
    assert message is not None
    assert f"no {kind} channel is defined" in message


@pytest.mark.parametrize("type_id", ["input.di", "output.do", "input.ai", "output.ao"])
def test_a_project_that_has_the_channel_says_nothing(type_id):
    assert io_availability.missing_io_message(_project_with_cards(), type_id) is None


def test_a_block_that_addresses_nothing_is_never_reported():
    """Every block carries an "Address" key, most never use it - asking
    about a gate must not produce a warning about missing cards."""
    assert io_availability.needs_physical_io("logic.and") is False
    assert io_availability.missing_io_message(Project(), "logic.and") is None


def test_where_to_add_a_card_depends_on_who_hosts_the_editor():
    """Inside EPW Studio the card list is Studio's (bridged in), so the
    engineer has to go to Studio's own I/O Cards - not to Logic Studio's
    Project Settings, which is ignored entirely while bridged."""
    standalone = Project()
    hosted = Project()
    hosted.external_cards = []  # bridged, and Studio has no cards yet

    assert "Project Settings" in io_availability.missing_io_message(standalone, "input.di")
    assert "I/O Cards" in io_availability.missing_io_message(hosted, "input.di")


def test_analog_addresses_bridged_from_studio_count_as_present():
    """The analog half of the bridge (studio/shell/logic_panel.py): with
    Studio's own analog points mirrored in, an AI block has somewhere to
    point and there is nothing to warn about."""
    hosted = Project()
    hosted.external_cards = [{"id": "ELA1", "kind": "AI", "channels": 2}]
    hosted.external_analog_points = [
        {"address": "ELA1.AI.1", "name": "", "unit": "%", "min": 0.0, "max": 100.0, "direction": "input"},
    ]
    assert io_availability.available_addresses(hosted, "input.ai") == ["ELA1.AI.1"]
    assert io_availability.missing_io_message(hosted, "input.ai") is None
    # ...and the output direction still has none, which IS worth saying.
    assert io_availability.missing_io_message(hosted, "output.ao") is not None


# ---- the Address editor --------------------------------------------------

def test_the_address_row_names_the_missing_kind_instead_of_being_blank(qsettings):
    _app()
    project = Project()
    block = BlockRegistry.create_block("input.di")
    project.add_block(block)
    panel = PropertyGridPanel(settings=qsettings)
    panel.load_block_properties(block, project)

    field = panel.field_widget("Address")
    assert isinstance(field, _MissingIOCombo)
    assert field.currentText() == "(no DI channels in this project)"
    assert "I/O" in field.toolTip() or "DI" in field.toolTip()


def test_opening_the_empty_address_list_explains_it(qsettings, monkeypatch):
    _app()
    project = Project()
    block = BlockRegistry.create_block("output.do")
    project.add_block(block)
    panel = PropertyGridPanel(settings=qsettings)
    panel.load_block_properties(block, project)

    shown = []
    monkeypatch.setattr(QMessageBox, "information",
                        lambda parent, title, text, *a, **k: shown.append((title, text)))
    panel.field_widget("Address").showPopup()

    assert len(shown) == 1
    title, text = shown[0]
    assert "no DO channel is defined" in text
    assert "I/O" in title


def test_a_project_with_cards_still_gets_the_ordinary_address_list(qsettings):
    _app()
    project = _project_with_cards()
    block = BlockRegistry.create_block("input.di")
    project.add_block(block)
    panel = PropertyGridPanel(settings=qsettings)
    panel.load_block_properties(block, project)

    field = panel.field_widget("Address")
    assert isinstance(field, QComboBox) and not isinstance(field, _MissingIOCombo)
    assert field.itemText(0) == "ELA01.DI.1"


# ---- the drop ------------------------------------------------------------

def test_dropping_a_block_with_nowhere_to_point_says_so_without_a_dialog(qsettings, monkeypatch):
    """Not a modal: dropping ten DI blocks before wiring the cards is
    normal work. The status bar and the Warnings tab carry it instead."""
    from logic_studio.ui.main_window import MainWindow
    _app()
    monkeypatch.setattr(QMessageBox, "information",
                        lambda *a, **k: pytest.fail("a modal dialog interrupted a block drop"))

    window = MainWindow(settings=qsettings)
    window.scene.add_block_from_library("input.di", 0, 0)

    assert "no DI channel is defined" in window.statusBar().currentMessage()
    assert "no DI channel is defined" in window.output_panel.warnings_log.toPlainText()


def test_dropping_a_block_that_has_somewhere_to_point_is_silent(qsettings):
    from logic_studio.ui.main_window import MainWindow
    _app()
    window = MainWindow(settings=qsettings)
    window.project.settings["ela_devices"] = ["ELA01"]

    window.scene.add_block_from_library("input.di", 0, 0)

    assert "DI channel" not in window.output_panel.warnings_log.toPlainText()
