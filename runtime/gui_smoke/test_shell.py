"""The main window's chrome and default page-navigation shell: menu bar
contents, the Help system + About dialog, "Settings is a menu, not a nav
page", the nav tree's page set and group-click behavior, the Analog
Inputs page's dynamic points manager, window resizability, and the
Breaker/Contactor synoptic label wrap fix.

Split out of the old test_gui_smoke.py (refactor/test-suite-split task,
section 1, "interface pages" axis): every check here shares the same
single, plain default MainWindow the original script built once at the
very top and kept reusing across all of these otherwise-unrelated
checks - grouped together here for that reason, not because they are one
feature. See gui_smoke/README.md for the full split rationale.
"""
import os

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QFont, QFontMetrics, QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel

from epw_os.i18n import tr

from gui_smoke._mocks import MockAccessManager, MockCommandManager, MockProjectManager, MockTagManager


def _window(make_window):
    win = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), MockProjectManager())
    win.show()
    return win


def _open_help(window, qapp):
    # F1's shortcut only fires while the window has actually processed
    # its "shown" state through the Qt event loop at least once.
    qapp.processEvents()
    QTest.keyClick(window, Qt.Key.Key_F1)
    qapp.processEvents()
    assert window._help_window is not None, "F1 did not open the Help window"
    return window._help_window


def test_gui_constructs_and_shows(make_window):
    window = _window(make_window)
    assert window.isVisible()


def test_file_menu_present_edit_menu_gone(make_window):
    window = _window(make_window)
    menu_texts = [a.text() for a in window.menuBar().actions()]
    assert tr("menu.file") in menu_texts, menu_texts
    assert not any(t.lower() in ("edit", "edytuj") for t in menu_texts), f"Edit menu still present: {menu_texts}"

    file_menu = window.menuBar().actions()[0].menu()
    file_labels = [a.text() for a in file_menu.actions() if not a.isSeparator()]
    for key in ("menu.file_new", "menu.file_open", "menu.file_save",
                "menu.file_save_as", "menu.file_export", "menu.file_import", "menu.file_exit"):
        assert tr(key) in file_labels, (key, file_labels)
    for key in ("_file_new_project", "_file_open_project", "_file_save_project",
                "_file_save_project_as", "_file_export_project", "_file_import_project"):
        assert callable(getattr(window, key)), key


def test_project_menu_real_content_devices_menu_removed(make_window):
    window = _window(make_window)
    menu_texts = [a.text() for a in window.menuBar().actions()]
    assert not any(t.lower() in ("devices", "urządzenia") for t in menu_texts), \
        f"Devices menu still present: {menu_texts}"
    project_menu = [a.menu() for a in window.menuBar().actions() if a.text() == tr("menu.project")][0]
    project_labels = [a.text() for a in project_menu.actions() if not a.isSeparator()]
    assert tr("menu.project_properties") in project_labels, project_labels
    assert tr("menu.project_recent") in project_labels, project_labels


def test_no_menu_in_the_menu_bar_is_empty(make_window):
    # DOWÓD: this is exactly the bug an earlier task fixed for Project,
    # and permanently removed for Devices.
    window = _window(make_window)
    for menu_action in window.menuBar().actions():
        submenu = menu_action.menu()
        assert submenu is not None, f"{menu_action.text()!r} is not even a submenu"
        assert len(submenu.actions()) > 0, f"{menu_action.text()!r} menu is empty"


def test_help_menu_structure(make_window):
    window = _window(make_window)
    help_menu_action = [a for a in window.menuBar().actions() if a.text() == tr("menu.help")][0]
    help_submenu = help_menu_action.menu()
    assert [a.text() for a in help_submenu.actions() if not a.isSeparator()] == \
        [tr("menu.help_topics"), tr("menu.help_index"), tr("menu.help_about")], \
        [a.text() for a in help_submenu.actions()]
    assert help_submenu.actions()[2].isSeparator(), "separator must sit between Index and About"


def test_f1_opens_help_at_default_user_access_level(make_window, qapp):
    # DOWÓD: F1 opens Help from anywhere in the program, at every access
    # level - `window` here is at the default (User) level, no PIN prompt
    # of any kind involved.
    window = _window(make_window)
    assert getattr(window, "_help_window", None) is None
    hw = _open_help(window, qapp)
    assert hw.isVisible(), "F1 must open the Help window"


def test_help_contents_tree_built_from_files(make_window, qapp):
    window = _window(make_window)
    hw = _open_help(window, qapp)
    toc = hw._store.load_toc()
    assert hw.tree.topLevelItemCount() == len(toc["chapters"]) > 0
    total_topic_items = sum(hw.tree.topLevelItem(i).childCount() for i in range(hw.tree.topLevelItemCount()))
    assert total_topic_items == sum(len(c["topics"]) for c in toc["chapters"]) > 0


def test_help_back_forward_is_real_browsing_history(make_window, qapp):
    window = _window(make_window)
    hw = _open_help(window, qapp)

    assert not hw.btn_back.isEnabled() and not hw.btn_forward.isEnabled(), \
        "fresh window (welcome screen only) must have nothing to go back/forward to"
    hw.navigate_to("al_three")
    hw.navigate_to("saf_kernel")
    hw.navigate_to("kiosk_what")
    assert hw.btn_back.isEnabled() and not hw.btn_forward.isEnabled()
    hw._go_back()
    assert hw.windowTitle().endswith(hw._store.topic_title("saf_kernel"))
    assert hw.btn_back.isEnabled() and hw.btn_forward.isEnabled()
    hw._go_back()
    assert hw.windowTitle().endswith(hw._store.topic_title("al_three"))
    assert not hw.btn_back.isEnabled() and hw.btn_forward.isEnabled()
    hw._go_forward()
    hw._go_forward()
    assert hw.windowTitle().endswith(hw._store.topic_title("kiosk_what"))
    assert hw.btn_back.isEnabled() and not hw.btn_forward.isEnabled()
    hw._go_back()
    hw._go_back()  # back to al_three
    hw.navigate_to("mv_synoptic")
    assert not hw.btn_forward.isEnabled(), "a fresh navigation must truncate stale forward history"


def test_help_survives_a_missing_topic_and_search_finds_by_content(make_window, qapp):
    window = _window(make_window)
    hw = _open_help(window, qapp)

    # DOWÓD: a missing topic file must not crash the program (re-checked
    # here through the actual widget - already covered in isolation at
    # the HelpContentStore level in epw_os/tests/test_help_content.py).
    hw.navigate_to("this_topic_id_does_not_exist_anywhere")
    assert "not found" in hw.viewer.toPlainText().lower()

    hw.select_tab("search")
    hw.search_edit.setText("safety_kernel")
    assert hw.search_results.count() > 0, "search must find topics whose BODY mentions the term"
    hw.search_edit.setText("")
    assert hw.search_results.count() == 0


def test_help_index_tab_alphabetized_and_navigable(make_window, qapp):
    window = _window(make_window)
    hw = _open_help(window, qapp)

    hw.select_tab("index")
    assert hw.index_list.count() == len(hw._store.index_terms()) > 0
    index_terms_widget = [hw.index_list.item(i).text() for i in range(hw.index_list.count())]
    assert index_terms_widget == sorted(index_terms_widget, key=str.lower), "Index tab must be alphabetized"
    hw.index_list.itemClicked.emit(hw.index_list.item(0))
    assert hw.viewer.toPlainText().strip()


def test_about_dialog_shows_logo_when_present_and_survives_missing_file(make_window):
    from epw_os.gui.widgets.about_dialog import AboutDialog
    import epw_os.gui.widgets.about_dialog as about_mod

    window = _window(make_window)

    ad_with_logo = AboutDialog(window)
    logo_labels = [w for w in ad_with_logo.findChildren(QLabel)
                   if w.pixmap() is not None and not w.pixmap().isNull()]
    assert logo_labels, "About dialog must show the logo graphic when about_logo.png exists"
    ad_with_logo.deleteLater()

    orig_logo_path = about_mod._LOGO_PATH
    about_mod._LOGO_PATH = os.path.join(os.getcwd(), "this_logo_file_does_not_exist.png")
    try:
        ad_no_logo = AboutDialog(window)  # must not raise
        logo_labels_missing = [w for w in ad_no_logo.findChildren(QLabel)
                                if w.pixmap() is not None and not w.pixmap().isNull()]
        assert not logo_labels_missing, "no logo file -> no (broken) pixmap label"
        ad_no_logo.deleteLater()
    finally:
        about_mod._LOGO_PATH = orig_logo_path


def test_settings_is_a_menu_not_a_nav_page(make_window):
    window = _window(make_window)
    assert "settings" not in window._page_index, "SETTINGS nav page still present"
    assert not hasattr(window, "page_settings"), "page_settings view still present"
    settings_menu = None
    for a in window.menuBar().actions():
        if a.text() == tr("menu.settings"):
            settings_menu = a.menu()
    assert settings_menu is not None, "Settings menu missing"
    s_labels = [a.text() for a in settings_menu.actions()]
    assert tr("menu.settings_language") in s_labels, s_labels
    assert tr("menu.settings_change_pin") in s_labels, s_labels


def test_settings_popups_construct(make_window):
    from epw_os.gui.widgets.settings_popups import ChangePinDialog, LanguageDialog

    LanguageDialog(MockProjectManager())
    d = ChangePinDialog(MockAccessManager())
    assert d.operator_section is not None and d.engineer_section is not None


def test_nav_pages_keyed_by_stable_page_id(make_window):
    window = _window(make_window)
    expected_nav = {"main_view", "power_quality", "digital_inputs", "analog_inputs",
                     "control_outputs", "protection_electrical", "protection_process", "events", "alarms",
                     "system_topology", "audit_log", "trends", "bus_diagnostics",
                     "intrusion_overview", "intrusion_history", "intrusion_config", "engineer_mode"}
    assert set(window._page_index) == expected_nav, set(window._page_index)


def test_nav_tree_group_name_click_opens_first_page(make_window):
    # DOWÓD: "kliknięcie w nazwę grupy otwiera pierwszą stronę z grupy".
    # Control/STEROWANIE always has >= 2 children (digital_inputs,
    # control_outputs, plus analog_inputs since it's enabled by default
    # here), so it stays an expandable group (not collapsed to a single
    # leaf) and is a real test of the "click the group name itself, not
    # the [+]/[-] box" behavior.
    from epw_os.gui.widgets.nav_tree import _GROUP_ID_ROLE

    window = _window(make_window)
    control_item = None
    for i in range(window.nav_tree.topLevelItemCount()):
        it = window.nav_tree.topLevelItem(i)
        if it.data(0, _GROUP_ID_ROLE) == "control_group":
            control_item = it
            break
    assert control_item is not None, "control_group not found in nav tree"
    assert control_item.childCount() >= 2, "control_group should have multiple pages, not be collapsed"
    control_rect = window.nav_tree.visualItemRect(control_item)
    # click well to the right of the [+]/[-] box, on the group's own label
    click_pos = QPoint(control_rect.left() + 60, control_rect.center().y())
    press = QMouseEvent(QMouseEvent.Type.MouseButtonPress, click_pos, Qt.MouseButton.LeftButton,
                         Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    window.nav_tree.mousePressEvent(press)
    assert window.stacked_widget.currentIndex() == window._page_index["digital_inputs"], \
        "clicking a group's own name must open its first page (digital_inputs)"
    assert window._current_page_id == "digital_inputs"


def test_analog_inputs_page_dynamic_points_manager(make_window):
    from epw_os.gui.pages.page_analog_inputs import AnalogChannelConfigDialog, PageAnalogInputs

    window = _window(make_window)
    window._navigate_to("analog_inputs")
    assert isinstance(window.stacked_widget.currentWidget(), PageAnalogInputs)
    ai_page = window.page_ai
    assert ai_page.table.rowCount() == 1
    assert ai_page.table.item(0, 0).text() == "AI1"
    # Task: Tag(0)/Description(1)/Value(2)/Unit(3)/Timestamp(4)/
    # Technical note(5)/Configure(6) - Unit and Technical note moved out
    # of AnalogChannelConfigDialog into the table, Configure added
    # mirroring Control Outputs' Force column.
    assert ai_page.table.columnCount() == 7

    # Add a point directly against the mock tag_manager (bypassing the
    # modal config dialog) - the table must grow on rebuild.
    ai_page.tag_manager.add_analog_point({
        "tag": "AI.Test.Point", "description": "Test point", "technical_note": "smoke test",
        "signal_type": "Wartość gotowa (bez przeliczania)",
        "raw_min": 0.0, "raw_max": 100.0, "eng_min": 0.0, "eng_max": 100.0, "unit": "", "decimals": 1,
    })
    ai_page._rebuild_table()
    assert ai_page.table.rowCount() == 2
    assert "AI.Test.Point" in ai_page._row_tags

    # ... and shrink back on remove.
    ai_page.tag_manager.remove_analog_point("AI.Test.Point")
    ai_page._rebuild_table()
    assert ai_page.table.rowCount() == 1

    dlg = AnalogChannelConfigDialog(tag_name="AI1", config=None, parent=ai_page)
    # Task: Description/Unit/Technical note removed from this dialog
    # entirely - they're edited inline in the table now.
    for removed_attr in ("edit_description", "edit_unit", "edit_note"):
        assert not hasattr(dlg, removed_attr), \
            f"AnalogChannelConfigDialog must no longer have {removed_attr} - moved to the table"
    assert dlg.scaling_frame.isHidden(), "default type = ready value -> scaling hidden"
    assert dlg.edit_tag.isReadOnly(), "existing point's Tag/Address must not be renamable here"
    dlg.combo_type.setCurrentText("4-20mA")
    assert not dlg.scaling_frame.isHidden(), "scaled type -> scaling shown"
    assert dlg.spin_raw_min.value() == 4.0 and dlg.spin_raw_max.value() == 20.0
    assert "unit" not in dlg.result_config(), "Unit is no longer part of this dialog's result"

    # Add-mode dialog: Tag/Address editable, empty/duplicate names rejected.
    add_dlg = AnalogChannelConfigDialog(existing_tags={"AI1"}, parent=ai_page)
    assert not add_dlg.edit_tag.isReadOnly()
    add_dlg.edit_tag.setText("AI1")
    add_dlg._try_accept()
    assert add_dlg.lbl_error.text(), "duplicate tag name should be rejected"
    add_dlg.edit_tag.setText("")
    add_dlg.lbl_error.setText("")
    add_dlg._try_accept()
    assert add_dlg.lbl_error.text(), "empty tag name should be rejected"


def test_analog_inputs_point_missing_optional_keys_renders_correctly(make_window):
    # DOWÓD: an existing point saved before Unit/Technical note ever moved
    # out of the dialog - i.e. missing those keys entirely, not just
    # empty - must still render correctly with no migration step.
    # normalize_config() has always filled in missing keys with defaults;
    # this exercises that directly for the two keys this task touches.
    window = _window(make_window)
    window._navigate_to("analog_inputs")
    ai_page = window.page_ai
    ai_page.tag_manager.add_analog_point({
        "tag": "AI.Legacy", "description": "Legacy point",
        "signal_type": "Wartość gotowa (bez przeliczania)",
        "raw_min": 0.0, "raw_max": 100.0, "eng_min": 0.0, "eng_max": 100.0, "decimals": 1,
        # deliberately no "unit", no "technical_note" key at all
    })
    ai_page._rebuild_table()
    legacy_row = ai_page._row_for_tag("AI.Legacy")
    assert legacy_row is not None
    assert ai_page.table.item(legacy_row, 1).text() == "Legacy point"
    assert ai_page.table.item(legacy_row, 3).text() == "", "missing 'unit' key must default to empty, not crash"
    assert ai_page.table.item(legacy_row, 5).text() == "", "missing 'technical_note' key must default to empty"


def test_window_is_resizable_not_fixed(make_window):
    window = _window(make_window)
    assert window.minimumWidth() <= 900 and window.maximumWidth() >= 10000, \
        (window.minimumWidth(), window.maximumWidth())
    assert window.minimumWidth() > 0, "no minimum size set"


def test_breaker_contactor_description_wraps_not_truncates(make_window):
    # Part 5 of an earlier follow-up task: "Digital Output C..." on Main
    # View under DO01-04's synoptic symbols used to truncate instead of
    # wrapping to a second line.
    from epw_os.gui.widgets.synoptic_objects import _wrap_to_two_lines

    window = _window(make_window)
    q1_width = window.page_entry_gate.q1.width()
    fm = QFontMetrics(QFont("Tahoma", 7))
    for n in (1, 2, 3, 4):
        lines = _wrap_to_two_lines(f"Digital Output Channel {n}", fm, q1_width - 44)
        assert len(lines) <= 2 and all(not l.endswith("…") for l in lines), \
            (f"Digital Output Channel {n}", lines)
