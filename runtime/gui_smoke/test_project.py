"""Project-file related menu features: Tools > Export Signal List..., the
Project Properties dialog (view/edit gating), and the Recently Opened
submenu.

Split out of the old test_gui_smoke.py (refactor/test-suite-split task,
"interface pages" axis).
"""
import json
import os
import tempfile

from gui_smoke._mocks import MockAccessManager, MockAuditLogger, MockCommandManager, MockControllableAccessManager, MockProjectManager, MockTagManager


def test_export_signal_list_writes_valid_versioned_json(make_window):
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    w = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), MockProjectManager())
    export_dir = tempfile.mkdtemp()
    export_path = os.path.join(export_dir, "signals.json")
    orig_get_save = QFileDialog.getSaveFileName
    orig_msgbox_info = QMessageBox.information
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (export_path, ""))
    QMessageBox.information = staticmethod(lambda *a, **k: None)
    try:
        w._export_tag_list()
    finally:
        QFileDialog.getSaveFileName = orig_get_save
        QMessageBox.information = orig_msgbox_info
    assert os.path.exists(export_path), "signal list export did not write a file"
    with open(export_path, encoding="utf-8") as f:
        export_data = json.load(f)
    assert export_data["format_version"] == "1.0"
    assert export_data["tag_count"] == 3
    export_names = {t["name"] for t in export_data["tags"]}
    assert export_names == {"DI1", "System.Theme", "Meas.L1"}, export_names
    theme_entry = next(t for t in export_data["tags"] if t["name"] == "System.Theme")
    assert theme_entry["direction"] == "READ_WRITE", theme_entry
    di1_entry = next(t for t in export_data["tags"] if t["name"] == "DI1")
    assert di1_entry["direction"] == "READ_ONLY", di1_entry
    meas_entry = next(t for t in export_data["tags"] if t["name"] == "Meas.L1")
    assert meas_entry["is_simulated"] is True
    assert di1_entry["is_simulated"] is False
    assert export_data["request_tags"] == []
    assert "DI" in export_data["groups"] and "DI1" in export_data["groups"]["DI"]


def test_project_properties_viewable_at_every_level_editable_only_engineer(make_window):
    from epw_os.gui.widgets.project_properties_dialog import ProjectPropertiesDialog

    w = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), MockProjectManager())

    props_dlg_user = ProjectPropertiesDialog(
        MockProjectManager(), MockTagManager(), MockControllableAccessManager(), MockAuditLogger(),
        parent=w,
    )
    assert props_dlg_user.edit_name.isReadOnly(), "User must not be able to edit Project Properties fields"
    assert not props_dlg_user.btn_save.isEnabled(), "Save must be disabled (not just fields) for User"
    props_dlg_user.deleteLater()

    props_eng_access = MockControllableAccessManager()
    props_eng_access.attempt_login("Engineer", MockControllableAccessManager.CORRECT_PIN)
    props_pm = MockProjectManager()
    props_audit = MockAuditLogger()
    props_dlg_eng = ProjectPropertiesDialog(
        props_pm, MockTagManager(), props_eng_access, props_audit, parent=w,
    )
    assert not props_dlg_eng.edit_name.isReadOnly(), "Engineer must be able to edit"
    assert props_dlg_eng.btn_save.isEnabled()
    props_dlg_eng.edit_name.setText("Substation A")
    props_dlg_eng.edit_description.setText("Test substation")
    props_dlg_eng.edit_location.setText("Building 3")
    props_dlg_eng.edit_author.setText("J. Kowalski")
    props_dlg_eng._try_save()
    assert props_pm.get_metadata()["name"] == "Substation A"
    assert props_pm.get_metadata()["created"] is not None, "created must be stamped on first save"
    assert any(e[0] == "PROJECT_METADATA_CHANGE" for e in props_audit.entries), \
        "a metadata change must be recorded to the audit log"


def test_project_properties_access_re_checked_at_save_time(make_window):
    # DOWÓD: execution-time re-check, not just the visual gate at
    # construction time - access can lapse (5-minute auto-logout keeps
    # running under a modal .exec() loop) while this dialog is still open.
    from epw_os.gui.widgets.project_properties_dialog import ProjectPropertiesDialog

    w = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), MockProjectManager())

    props_eng_access2 = MockControllableAccessManager()
    props_eng_access2.attempt_login("Engineer", MockControllableAccessManager.CORRECT_PIN)
    props_pm2 = MockProjectManager()
    props_dlg_lapse = ProjectPropertiesDialog(
        props_pm2, MockTagManager(), props_eng_access2, MockAuditLogger(), parent=w,
    )
    props_dlg_lapse.edit_name.setText("Should never be saved")
    props_eng_access2.demote("User")  # access lapses while the dialog is still open, unbeknownst to the dialog
    props_dlg_lapse._try_save()
    assert props_pm2.get_metadata()["name"] == "", \
        "a lapsed access level must block the save even though the dialog was opened as Engineer"


def test_recently_opened_missing_files_marked_valid_one_opens_and_reorders(make_window):
    from epw_os.core.project_manager import ProjectManager as RealProjectManager
    from epw_os.gui import window_state as ws_module

    real_pm = RealProjectManager(os.path.join(tempfile.mkdtemp(), "active.json"))
    real_pm.load_project()  # no file yet -> in-memory default
    w = make_window(MockTagManager(), MockCommandManager(), MockAccessManager(), real_pm)

    ws_module.clear_recent_projects()
    missing_path = os.path.join(tempfile.mkdtemp(), "does_not_exist.json")
    target_path = os.path.join(tempfile.mkdtemp(), "target_project.json")
    with open(target_path, "w", encoding="utf-8") as f:
        f.write('{"format": "EPW_OS_PROJECT", "schema_version": 1, "project_id": "RECENT_TARGET"}')
    ws_module.add_recent_project(missing_path)
    ws_module.add_recent_project(target_path)  # added last -> newest -> listed first

    w._refresh_recent_projects_menu()  # must not raise for a file that doesn't exist
    recent_actions = [a for a in w._recent_projects_menu.actions() if not a.isSeparator()]
    missing_action = next(a for a in recent_actions if os.path.basename(missing_path) in a.text())
    target_action = next(a for a in recent_actions if os.path.basename(target_path) in a.text())

    assert not missing_action.isEnabled(), \
        "DOWÓD: a missing project file must be disabled, not left clickable to fail later"
    assert missing_action.text() != os.path.basename(missing_path), \
        "a missing file must also be marked in its label, not just disabled"
    assert target_action.isEnabled()

    target_action.trigger()
    assert w.project_manager.config.get("project_id") == "RECENT_TARGET", \
        "clicking a valid Recently Opened entry must actually open that project"
    # DOWÓD: survives a "restart" - there is no in-memory cache anywhere
    # in window_state.py, only the file itself, so re-reading it fresh
    # already proves this.
    assert target_path in ws_module.load_recent_projects()
    assert ws_module.load_recent_projects()[0] == target_path, "opening it again must move it back to the front"
