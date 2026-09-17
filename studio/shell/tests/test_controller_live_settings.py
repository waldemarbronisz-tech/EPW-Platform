"""SPEC "Studio — sterownik", point 4: the controller's settings live in
Studio, differences marked, and the controller's values taken into the
project on request. Same fake controller as the project-sync tests."""
from PySide6.QtWidgets import QApplication, QMessageBox

from studio.shell.project_format import load_project, new_project, settings_hash, settings_snapshot
from studio.shell.tests.test_controller_project_sync import (ENGINEER, FakeController, _close, _quiet_boxes,
                                                             _saved_project, _stage, _window)


def _app():
    return QApplication.instance() or QApplication([])


def test_fetch_shows_only_the_differences_marked_and_the_status_names_the_revisions(tmp_path, monkeypatch):
    _app()
    path = _saved_project(tmp_path, setting=25.0)                      # Studio: 25 A
    on_controller = new_project("Site", author="t")
    on_controller.electrical_protection_stages = [_stage(40.0)]        # controller: 40 A
    controller = FakeController(path.read_bytes(), revision=7, settings=settings_snapshot(on_controller),
                                stored_hash=settings_hash(on_controller))
    win = _window(tmp_path, path, controller.url)
    _quiet_boxes(monkeypatch)
    try:
        panel = win._controller_panel
        assert panel.take_settings_button.isEnabled() is False
        panel._fetch_settings()
        rows = panel.settings_rows()
        assert [r for r in rows if r[3]] == [
            ("electrical_protection_stages/50 Instantaneous Overcurrent / Stage 1/setting", 25.0, 40.0, True)]
        assert panel.settings_table.rowCount() == 1                      # differences only
        assert panel.settings_table.item(0, 1).text() == "25.0" and panel.settings_table.item(0, 2).text() == "40.0"
        assert panel.settings_table.item(0, 2).background().color().name() == "#fff1b8"
        assert "7" in panel.settings_status_label.text() and "1" in panel.settings_status_label.text()
        assert panel.take_settings_button.isEnabled()

        panel.settings_diff_only_check.setChecked(False)
        assert panel.settings_table.rowCount() == len(rows) > 1
        same_rows = [r for r in range(panel.settings_table.rowCount())
                     if panel.settings_table.item(r, 0).text().endswith("/hysteresis")]
        assert same_rows and panel.settings_table.item(same_rows[0], 1).background().color().name() != "#fff1b8"
    finally:
        _close(win)
        controller.close()


def test_taking_the_controllers_values_writes_them_into_the_project(tmp_path, monkeypatch):
    _app()
    path = _saved_project(tmp_path, setting=25.0)
    on_controller = new_project("Site", author="t")
    on_controller.electrical_protection_stages = [_stage(40.0)]
    controller = FakeController(path.read_bytes(), revision=3, settings=settings_snapshot(on_controller),
                                stored_hash=settings_hash(on_controller))
    win = _window(tmp_path, path, controller.url)
    shown = _quiet_boxes(monkeypatch, answer=QMessageBox.StandardButton.Yes)
    try:
        panel = win._controller_panel
        panel._fetch_settings()
        panel._take_controller_settings()
        assert shown["question"] and shown["info"]
        assert win._project.electrical_protection_stages[0].setting == 40.0
        assert win._project.is_dirty
        assert [r for r in panel.settings_rows() if r[3]] == []           # nothing differs any more
        assert panel.take_settings_button.isEnabled() is False
        assert "identical" in panel.settings_status_label.text() or "identyczne" in panel.settings_status_label.text()
        win._save_project()
        assert load_project(path).electrical_protection_stages[0].setting == 40.0
    finally:
        _close(win)
        controller.close()


def test_live_refresh_stops_itself_when_the_controller_stops_answering(tmp_path, monkeypatch):
    _app()
    path = _saved_project(tmp_path)
    controller = FakeController(path.read_bytes(), revision=1, settings=settings_snapshot(load_project(path)),
                                stored_hash=settings_hash(load_project(path)))
    win = _window(tmp_path, path, controller.url)
    _quiet_boxes(monkeypatch)
    try:
        panel = win._controller_panel
        panel.settings_live_check.setChecked(True)
        assert panel._settings_timer.isActive() and panel._remote_settings is not None
        controller.close()
        panel._fetch_settings()
        assert panel._remote_settings is None and not panel._settings_timer.isActive()
        assert panel.settings_live_check.isChecked() is False
        assert panel.settings_table.rowCount() == 0
    finally:
        _close(win)
