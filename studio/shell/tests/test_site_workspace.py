"""User, 2026-09-18: "możliwość tworzenia wielu projektów w Studio - cały
obiekt stworzony z wielu sterowników" (Etango-style: an object, devices
added to it). An .epwsite lists the devices' projects; the device list
above the tree switches the active project, keeping each device's
unsaved edits and tree marks; Save saves the active device, Save Object
saves them all; a plain projekt.epw is an implicit one-device object."""
import json

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

from studio.shell import main_window as mw
from studio.shell.main_window import StudioMainWindow
from studio.shell.project_format import load_project, new_project, save_project
from studio.shell.site_format import (SiteFormatError, load_site, new_site, relative_project_path,
                                      resolve_project_path, save_site)
from studio.shell.tests.test_controller_project_sync import _close

import pytest


def _app():
    return QApplication.instance() or QApplication([])


def _site(tmp_path, names=("EntryGate", "MainHouse")):
    site = new_site("Dom")
    site_path = tmp_path / "dom.epwsite"
    for name in names:
        folder = tmp_path / name
        folder.mkdir()
        project = new_project(name, author="t")
        save_project(project, folder / "projekt.epw")
        site.projects.append(f"{name}/projekt.epw")
    save_site(site, site_path)
    return site_path


def _window(tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    return StudioMainWindow(settings=settings)


# --- the object file -----------------------------------------------------------------------

def test_the_object_file_round_trips_and_resolves_relative_paths(tmp_path):
    path = _site(tmp_path)
    site = load_site(path)
    assert site.name == "Dom" and site.projects == ["EntryGate/projekt.epw", "MainHouse/projekt.epw"]
    assert not site.is_dirty
    assert resolve_project_path(path, "EntryGate/projekt.epw") == str(tmp_path / "EntryGate" / "projekt.epw")
    assert relative_project_path(path, tmp_path / "Garage" / "projekt.epw") == "Garage/projekt.epw"
    (tmp_path / "bad.epwsite").write_text('{"format": "NOPE"}', encoding="utf-8")
    with pytest.raises(SiteFormatError):
        load_site(tmp_path / "bad.epwsite")
    with pytest.raises(SiteFormatError):
        load_site(tmp_path / "missing.epwsite")


# --- devices in the window ------------------------------------------------------------------

def test_opening_an_object_lists_its_devices_and_switching_keeps_each_ones_edits(tmp_path):
    _app()
    path = _site(tmp_path)
    win = _window(tmp_path)
    try:
        assert win._load_site_from_path(str(path))
        assert win.device_names() == [("EntryGate", False), ("MainHouse", False)]
        assert win._project.metadata.name == "EntryGate" and win._project_path.endswith("projekt.epw")
        assert win._tree_header.text().endswith("EntryGate")
        assert win.device_tree.topLevelItem(0).text(0) == "Dom"

        win._open_locations()
        win._project.touch()
        win._on_project_changed()                               # an edit in EntryGate's Locations
        assert win.device_names() == [("EntryGate", True), ("MainHouse", False)]
        assert win.device_tree.topLevelItem(0).child(0).text(0) == "EntryGate *"

        assert win._activate_slot(1)
        assert win._project.metadata.name == "MainHouse" and win.edited_aspects() == set()
        assert win._tree_header.text().endswith("MainHouse")
        assert win.device_tree.currentItem().text(0) == "MainHouse"
        win._open_mqtt()
        win._mqtt_panel.host_edit.setText("main.lan")
        win._mqtt_panel.host_edit.editingFinished.emit()
        assert win.device_names() == [("EntryGate", True), ("MainHouse", True)]

        assert win._activate_slot(0)
        assert win._project.metadata.name == "EntryGate"
        assert win.edited_aspects() == {mw._TREE_ITEM_LOCATIONS}   # its own marks came back
        assert win._mqtt_panel.host_edit.text() == ""              # panels show EntryGate again

        assert win._save_site()
        assert win.device_names() == [("EntryGate", False), ("MainHouse", False)]
        assert load_project(tmp_path / "MainHouse" / "projekt.epw").mqtt.host == "main.lan"
        assert load_project(tmp_path / "EntryGate" / "projekt.epw").revision == 2
    finally:
        _close(win)


def test_editor_work_survives_a_switch_as_a_parked_dirty_project(tmp_path):
    _app()
    path = _site(tmp_path)
    win = _window(tmp_path)
    try:
        win._load_site_from_path(str(path))
        win._note_synoptic_dirty({"isDirty": True})               # screens edited in EntryGate
        assert win.device_names()[0] == ("EntryGate", True)
        assert win._activate_slot(1)
        assert win._slots[0].project.is_dirty and mw._TREE_ITEM_SCREENS in win._slots[0].edited_aspects
        assert win.device_names()[0] == ("EntryGate", True)
        assert win._activate_slot(0)
        assert mw._TREE_ITEM_SCREENS in win.edited_aspects()       # still marked after coming back
        assert win._item_screens.text(0).endswith(" *")
    finally:
        _close(win)


def test_a_plain_project_is_an_implicit_object_and_can_grow_into_a_real_one(tmp_path, monkeypatch):
    _app()
    project_path = tmp_path / "solo" / "projekt.epw"
    project_path.parent.mkdir()
    save_project(new_project("Solo", author="t"), project_path)
    win = _window(tmp_path)
    try:
        win._load_project_from_path(str(project_path))
        assert win._site is None and win.device_names() == [("Solo", False)]
        assert win.device_tree.topLevelItem(0).text(0) in ("Obiekt (niezapisany)", "Object (unsaved)")

        site_path = tmp_path / "solo.epwsite"
        answers = iter([("Dom", True), ("Garage", True)])
        monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: next(answers))
        monkeypatch.setattr(win, "_ask_site_path", lambda name: str(site_path))
        win._add_new_device()
        assert site_path.exists()
        site = load_site(site_path)
        assert site.name == "Dom" and site.projects == ["solo/projekt.epw", "Garage/projekt.epw"]
        assert (tmp_path / "Garage" / "projekt.epw").exists()
        assert win.device_names() == [("Solo", False), ("Garage", False)]
        assert win._project.metadata.name == "Garage" and win._active_slot == 1
        assert win.device_tree.topLevelItem(0).text(0) == "Dom"

        monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
        win._remove_device()
        assert win.device_names() == [("Solo", False)] and win._project.metadata.name == "Solo"
        assert load_site(site_path).projects == ["solo/projekt.epw"]
        assert (tmp_path / "Garage" / "projekt.epw").exists()     # the file stays

        shown = []
        monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: shown.append(a[2]))
        win._remove_device()                                       # the last device cannot go
        assert shown and win.device_names() == [("Solo", False)]
    finally:
        _close(win)


def test_the_controller_address_is_remembered_per_device(tmp_path):
    _app()
    path = _site(tmp_path)
    win = _window(tmp_path)
    try:
        win._load_site_from_path(str(path))
        win._open_controller()
        panel = win._controller_panel
        panel.host_edit.setText("http://gate:8000")
        panel.host_edit.editingFinished.emit()
        win._activate_slot(1)
        assert panel.host_edit.text() == "http://gate:8000"        # the global fallback, nothing set yet here
        panel.host_edit.setText("http://house:8000")
        panel.host_edit.editingFinished.emit()
        win._activate_slot(0)
        assert panel.host_edit.text() == "http://gate:8000"
        win._activate_slot(1)
        assert panel.host_edit.text() == "http://house:8000"
    finally:
        _close(win)


def test_closing_asks_about_any_dirty_device_and_recent_opens_objects(tmp_path, monkeypatch):
    _app()
    path = _site(tmp_path)
    win = _window(tmp_path)
    try:
        win._load_site_from_path(str(path))
        assert str(path) in win._recent_projects()
        win._activate_slot(1)
        win._project.touch()
        win._on_project_changed()
        win._activate_slot(0)                                      # the dirty one is parked now
        assert win._workspace_dirty()
        asked = []
        monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: asked.append(a[2]) or QMessageBox.StandardButton.Save)
        assert win._confirm_discard_project()
        assert asked and not win._workspace_dirty()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert [p["path"] for p in data["projects"]] == ["EntryGate/projekt.epw", "MainHouse/projekt.epw"]
        win._open_recent_project(str(path))
        assert win.device_names() == [("EntryGate", False), ("MainHouse", False)]
    finally:
        _close(win)
