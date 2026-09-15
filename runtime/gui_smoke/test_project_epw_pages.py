"""Task "runtime czyta projekt.epw" - the pages with a projekt.epw behind
them. Structure (what exists, names, bindings, composition) is Studio's:
the create/remove tools are gone and structural fields are locked.
Settings stay editable and go back into the project file. Every page is
built against a REAL ProjectManager reading a real projekt.epw written by
the shared format code, so what a page shows is what the file says.
"""
import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from gui_smoke._mocks import (MockAuditLogger, MockCommandManager, MockControllableAccessManager, MockTagManager,
                              QtTagManagerBridge)


def _engineer():
    access = MockControllableAccessManager()
    assert access.attempt_login("Engineer", MockControllableAccessManager.CORRECT_PIN)
    return access


def _project(tmp_path, modules=("protection_settings", "analog_inputs"), stages=()):
    from epw_os.core import project_format as pf
    from epw_os.core.project_manager import ProjectManager
    project = pf.new_project("Pages")
    project.modules = list(modules)
    project.cards = [pf.Card(id="DI1", model="ELA01", channel_kinds={"DI": 2}, location="KOT")]
    project.points = [pf.Point(address="DI1.DI.1", description="Door contact", technical_note="X1:1"),
                      pf.Point(address="DI1.DI.2", location="MH")]
    project.electrical_protection_stages = [pf.ElectricalProtectionStage(**stage) for stage in stages]
    path = tmp_path / "projekt.epw"
    pf.save_project(project, path)
    pm = ProjectManager(str(path))
    assert pm.load_project()
    return pm, path


def test_electrical_protection_page_shows_the_project_values_and_writes_a_change_back(qapp, tmp_path):
    from epw_os.core import project_format as pf
    from epw_os.gui.pages.page_protection_electrical import PageProtectionElectrical

    pm, path = _project(tmp_path, stages=[{"function_id": "50 Instantaneous Overcurrent", "stage_name": "Stage 1",
                                           "enabled": True, "setting": 85.0, "hysteresis": 3.0, "delay_ms": 150,
                                           "action": "Warning"}])
    page = PageProtectionElectrical(MockTagManager(), _engineer(), project_manager=pm)
    stages = {s.name: s for s in page.protection_manager.protections["50 Instantaneous Overcurrent"].stages}

    assert (stages["Stage 1"].setting, stages["Stage 1"].hysteresis, stages["Stage 1"].delay_ms,
            stages["Stage 1"].action) == (85.0, 3.0, 150, "Warning")
    assert stages["Stage 2"].setting == 120.0  # not in the project: the built-in default stays

    page.on_action_changed("50 Instantaneous Overcurrent", stages["Stage 1"], "Trip", None)
    saved = pf.read_project(path).project
    assert (saved.revision, saved.modified_by, saved.electrical_protection_stages[0].action) == (2, "panel", "Trip")
    page.deleteLater()


def test_digital_inputs_show_location_and_note_from_the_registry_and_keep_descriptions(qapp, tmp_path):
    from epw_os.core.events import EventBus
    from epw_os.core.tag_manager import TagManager
    from epw_os.gui.pages.page_digital_inputs import _COL_LOCATION, _COL_TECHNICAL_NOTE, PageDigitalInputs

    pm, _path = _project(tmp_path)
    core_tm = TagManager(EventBus())
    core_tm.configure(pm.config["devices"])
    for name, description in pm.get_tag_descriptions().items():
        core_tm.set_description(name, description)
    for point in pm.get_point_registry():
        core_tm.set_point_info(point["address"], location=point["location"], technical_note=point["technical_note"])

    page = PageDigitalInputs(QtTagManagerBridge(core_tm), _engineer(), descriptions_editable=False)
    rows = {page.table.item(r, 1).text(): r for r in range(page.table.rowCount())}
    assert sorted(rows) == ["DI1.DI.1", "DI1.DI.2"]
    door = rows["DI1.DI.1"]
    assert page.table.item(door, 2).text() == "Door contact"
    assert (page.table.item(door, _COL_LOCATION).text(), page.table.item(door, _COL_TECHNICAL_NOTE).text()) == ("KOT", "X1:1")
    assert page.table.item(rows["DI1.DI.2"], _COL_LOCATION).text() == "MH"
    assert not page.table.item(door, 2).flags() & Qt.ItemFlag.ItemIsEditable

    page.table.item(door, 2).setText("Changed on the panel")
    assert page.table.item(door, 2).text() == "Door contact"
    assert core_tm.get_tag("DI1.DI.1").description == "Door contact"
    page.deleteLater()


def test_intrusion_configuration_edits_settings_only(qapp):
    from epw_os.core.intrusion_manager import _normalize_line_filters
    from epw_os.gui.pages.page_intrusion import LineConfigDialog, PageIntrusionConfiguration, ZoneConfigDialog

    page = PageIntrusionConfiguration(None, _engineer(), structure_editable=False)
    assert page.btn_power_supervision.isHidden()
    assert page.btn_configure_zones.isEnabled() and page.btn_configure_lines.isEnabled()
    assert any("Studio" in label.text() for label in page.findChildren(QLabel))

    zone = {"id": "Z1", "name": "Ground floor", "exit_delay_seconds": 30.0, "entry_delay_seconds": 20.0}
    zone_dialog = ZoneConfigDialog(zone, page, settings_only=True)
    assert zone_dialog.edit_name.isReadOnly() and zone_dialog.spin_exit_delay.isEnabled()

    line = _normalize_line_filters({"id": "L1", "name": "Front door", "zone_id": "Z1", "tag": "DI1.DI.4",
                                    "normal_state": "NC", "line_type": "INSTANT"})
    line_dialog = LineConfigDialog([zone], ["DI1.DI.4"], [], line, page, settings_only=True)
    assert line_dialog.edit_name.isReadOnly()
    for structural in (line_dialog.combo_zone, line_dialog.combo_input_mode, line_dialog.combo_tag_contact,
                       line_dialog.combo_normal_state, line_dialog.combo_type):
        assert not structural.isEnabled()
    for setting in (line_dialog.spin_min_violation, line_dialog.spin_multiplicity_count,
                    line_dialog.spin_lockout_after, line_dialog.spin_alarm_hold, line_dialog.spin_silence_threshold):
        assert setting.isEnabled()
    for widget in (zone_dialog, line_dialog, page):
        widget.deleteLater()


def test_feature_dialog_shows_the_composition_but_cannot_change_it(qapp):
    from epw_os.gui.widgets.feature_config_dialog import FeatureConfigDialog

    class CompositionFromProject:
        def get_enabled_features(self):
            return {"intrusion": True, "trends": False}

        def is_composition_editable(self):
            return False

        def set_feature_enabled(self, *args, **kwargs):
            raise AssertionError("the composition must not be changeable from the panel")

        def feature_referenced_by_logic(self, feature):
            return False

    dialog = FeatureConfigDialog(CompositionFromProject(), _engineer())
    assert dialog.composition_editable is False
    assert all(not checkbox.isEnabled() for checkbox in dialog._checkboxes.values())
    assert dialog._checkboxes["intrusion"].isChecked() and not dialog._checkboxes["trends"].isChecked()
    dialog.deleteLater()


def test_main_window_on_projekt_epw_file_menu_last_screen_and_startup_message(make_window, tmp_path):
    from epw_os.i18n import set_language

    pm, _path = _project(tmp_path)
    assert pm.set_last_screen("digital_inputs")
    issue = {"id": "PROJECT_NOT_LOADED", "key": "startup.project_refused", "params": {"path": "D:/site/projekt.epw"},
             "text": "refused", "detail_key": "project_format.missing_field",
             "detail_params": {"field": "cards[0].model"}}

    w = make_window(MockTagManager(), MockCommandManager(), _engineer(), pm, MockAuditLogger(), startup_issues=[issue])

    assert w.structure_editable is False
    hidden = {key for key, action in w._file_actions.items() if not action.isVisible()}
    assert hidden == {"menu.file_new", "menu.file_save", "menu.file_save_as", "menu.file_import"}
    assert w._current_page_id == "digital_inputs"

    w._navigate_to("events")
    state = json.loads((tmp_path / "runtime_state.json").read_text(encoding="utf-8"))
    assert state["last_screen"] == "events"

    set_language("pl")
    try:
        w._show_startup_issues()
        text = w._startup_issues_box.text()
    finally:
        set_language("en")
    assert "D:/site/projekt.epw" in text and "cards[0].model" in text and "Brak wymaganego pola" in text
    w._startup_issues_box.close()
