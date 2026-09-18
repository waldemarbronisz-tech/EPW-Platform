"""User, 2026-09-18: "jeżeli coś zmieniam w projekcie, to chcę żeby dział,
w którym coś edytowałem, zmieniał kolor na czerwony z *; ten kolor
zdejmuje dopiero zapisanie projektu" - the tree shows where unsaved
edits are. Panels mark the branch active when they report the edit; the
two editors mark themselves from their own dirty flags; a save, a new
project or an opened project clears every mark."""
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication

from studio.shell import main_window as mw
from studio.shell.main_window import StudioMainWindow
from studio.shell.project_format import new_project, save_project
from studio.shell.tests.test_controller_project_sync import _close


def _app():
    return QApplication.instance() or QApplication([])


def _window(tmp_path):
    path = tmp_path / "projekt.epw"
    save_project(new_project("Site", author="t"), path)
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    win = StudioMainWindow(settings=settings)
    win._load_project_from_path(str(path))
    return win, path


def _label(item):
    return item.text(0), item.data(0, Qt.ItemDataRole.ForegroundRole)


def test_an_edit_marks_the_active_branch_red_until_the_project_is_saved(tmp_path):
    _app()
    win, path = _window(tmp_path)
    try:
        assert win.edited_aspects() == set()
        win._open_mqtt()
        panel = win._mqtt_panel
        panel.host_edit.setText("broker.lan")
        panel.host_edit.editingFinished.emit()
        assert win.edited_aspects() == {mw._TREE_ITEM_MQTT}
        text, brush = _label(win._item_mqtt)
        assert text.endswith(" *") and brush is not None and brush.color().name() == "#c00000"
        assert not win._item_io_cards.text(0).endswith("*")

        win._open_io_cards()                                    # moving away keeps the mark
        assert win._item_mqtt.text(0).endswith(" *") and win.edited_aspects() == {mw._TREE_ITEM_MQTT}
        win._project.touch()
        win._on_project_changed()                               # an edit reported while Cards is active
        assert win.edited_aspects() == {mw._TREE_ITEM_MQTT, mw._TREE_ITEM_IO_CARDS}

        win._retranslate()                                      # a language switch keeps the marks
        assert win._item_io_cards.text(0).endswith(" *") and win._item_mqtt.text(0).endswith(" *")

        assert win._save_project()
        assert win.edited_aspects() == set()
        for item in (win._item_mqtt, win._item_io_cards):
            text, brush = _label(item)
            assert not text.endswith("*") and brush is None
    finally:
        _close(win)


def test_the_editors_mark_themselves_and_help_is_never_marked(tmp_path):
    _app()
    win, path = _window(tmp_path)
    try:
        win._open_help()
        win._project.touch()
        win._on_project_changed()
        assert win.edited_aspects() == set()                    # Help is not a project aspect

        win._note_synoptic_dirty({"isDirty": True})
        assert win.edited_aspects() == {mw._TREE_ITEM_SCREENS}
        assert win._item_screens.text(0).endswith(" *")
        win._note_synoptic_dirty({"isDirty": False})
        assert win._item_screens.text(0) == win._item_screens.text(0).rstrip(" *")
        assert not win._item_screens.text(0).endswith("*")
    finally:
        _close(win)


def test_a_new_or_opened_project_starts_without_marks(tmp_path, monkeypatch):
    _app()
    win, path = _window(tmp_path)
    try:
        win._open_locations()
        win._project.touch()
        win._on_project_changed()
        assert win.edited_aspects() == {mw._TREE_ITEM_LOCATIONS}
        monkeypatch.setattr(win, "_confirm_discard_project", lambda: True)
        win._new_project()
        assert win._project.is_dirty and win.edited_aspects() == set()
        assert not win._item_locations.text(0).endswith("*")

        win._project.touch()
        win._on_project_changed()
        assert win.edited_aspects() == {mw._TREE_ITEM_LOCATIONS}
        win._load_project_from_path(str(path))
        assert win.edited_aspects() == set()
    finally:
        _close(win)


def test_the_root_carries_the_projects_name_and_renames_it_in_place(tmp_path):
    _app()
    win, path = _window(tmp_path)
    try:
        assert win._item_root.text(0) == "Site"
        win._on_tree_item_double_clicked(win._item_root, 0)
        win._item_root.setText(0, "EntryGate")                   # what the in-place editor commits
        assert win._project.metadata.name == "EntryGate" and win._project.is_dirty
        assert win.edited_aspects() == {mw._TREE_ITEM_INFO}
        assert win._item_info.text(0).endswith(" *")
        win._open_info()
        assert win._project_info_panel.name_edit.text() == "EntryGate"
        win._project_info_panel.name_edit.setText("MainHouse")
        win._project_info_panel.name_edit.editingFinished.emit()
        assert win._item_root.text(0) == "MainHouse"
        assert win._save_project()
        assert win.edited_aspects() == set() and win._item_root.text(0) == "MainHouse"
        win._project.metadata.name = ""
        win._on_project_changed(aspect_edit=False)
        assert win._item_root.text(0) in ("PROJEKT", "PROJECT")
    finally:
        _close(win)
