"""Adding a controller with a plus, and renaming one with a click.

Owner, 2026-09-20: "Nowy projekt i sterownik powinno się dodawać
plusikiem - trzeba to zrobić dużo łatwiej - nie trzeba też zapisywać
itp musi to być proste i intuicyjne", and "przy liście urządzeń
jednoklik jak w windows powinien umożliwiać zmianę nazwy".

Adding a controller used to mean: save the current project, name an
object, choose where to put the object file, name the controller - four
dialogs and two files on disk before anything appeared in the list.

These tests are mostly about what does NOT happen: no dialog, no file,
no save.
"""
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from studio.shell.logic_path import ensure_importable

ensure_importable()

from studio.shell.main_window import StudioMainWindow


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(tmp_path, app, monkeypatch):
    """A window, and a guarantee that nothing here opens a dialog: any
    of them firing is the failure this whole change is about."""
    for name in ("getText", "getItem", "getInt"):
        monkeypatch.setattr(QInputDialog, name, lambda *a, **k: pytest.fail("a dialog was opened"))
    for name in ("getSaveFileName", "getOpenFileName", "getExistingDirectory"):
        monkeypatch.setattr(QFileDialog, name, staticmethod(lambda *a, **k: pytest.fail("a file dialog was opened")))
    for name in ("question", "information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, name, staticmethod(lambda *a, **k: pytest.fail("a message box was opened")))
    w = StudioMainWindow(settings=QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat))
    yield w
    for timer in w.findChildren(QTimer):
        timer.stop()
    w.hide()
    w.deleteLater()


def _rows(window):
    root = window._device_root_item
    return [root.child(i).text(0) for i in range(root.childCount())]


# --- the plus -----------------------------------------------------------------

def test_the_plus_adds_a_controller_without_a_single_dialog(window, tmp_path):
    before = len(_rows(window))

    window._add_device_button.click()

    assert len(_rows(window)) == before + 1
    assert list(tmp_path.glob("*.epw")) == [], "a file was written"
    assert list(tmp_path.glob("*.epwsite")) == [], "an object file was written"


def test_the_new_controller_has_no_file_until_somebody_saves(window):
    window._add_device_quickly()

    assert window._slots[-1].path is None
    assert window._project_path is None


def test_the_new_controller_becomes_the_active_one(window):
    window._add_device_quickly()

    assert window._active_slot == len(window._slots) - 1
    assert window._project is window._slots[-1].project


def test_controllers_are_numbered_by_position(window):
    window._add_device_quickly()
    window._add_device_quickly()

    names = [name.rstrip(" *") for name in _rows(window)]
    assert names[1].endswith("2") and names[2].endswith("3"), names


def test_the_new_row_is_put_straight_into_rename(window):
    """"Controller 2" is a placeholder, not a decision."""
    window._add_device_quickly()

    item = window._device_item_for(window._active_slot)
    assert window.device_tree.currentItem() is item
    assert item.flags() & Qt.ItemFlag.ItemIsEditable


# --- renaming -----------------------------------------------------------------

def test_renaming_a_row_renames_its_project(window):
    window._add_device_quickly()
    item = window._device_item_for(window._active_slot)

    item.setText(0, "Kotłownia")

    assert window._project.metadata.name == "Kotłownia"
    assert "Kotłownia" in _rows(window)[-1]


def test_the_unsaved_marker_is_not_baked_into_the_name(window):
    """The row shows "Name *" while there are unsaved changes. Editing
    that row hands the whole string back, asterisk included."""
    window._add_device_quickly()
    item = window._device_item_for(window._active_slot)

    item.setText(0, "Hala *")

    assert window._project.metadata.name == "Hala"


def test_a_blank_name_is_not_a_rename(window):
    window._add_device_quickly()
    before = window._project.metadata.name
    item = window._device_item_for(window._active_slot)

    item.setText(0, "   ")

    assert window._project.metadata.name == before


def test_renaming_an_inactive_controller_renames_that_one(window):
    window._add_device_quickly()
    first, second = 0, window._active_slot
    assert first != second

    window._device_item_for(first).setText(0, "Brama")

    assert window._slots[first].project.metadata.name == "Brama"
    assert window._project.metadata.name != "Brama", "the active controller was renamed instead"


# --- the Windows gesture ------------------------------------------------------

def test_a_second_click_on_the_same_row_starts_editing_it(window):
    window._add_device_quickly()
    item = window._device_item_for(window._active_slot)
    edited = []
    window.device_tree.editItem = lambda target, column=0: edited.append(target)

    window._on_device_item_clicked(item, 0)   # selects
    window._on_device_item_clicked(item, 0)   # renames

    assert edited == [item]


def test_clicking_a_different_row_only_selects_it(window):
    """Otherwise switching controllers would put you in a text box
    every single time."""
    window._add_device_quickly()
    first = window._device_item_for(0)
    second = window._device_item_for(1)
    edited = []
    window.device_tree.editItem = lambda target, column=0: edited.append(target)

    window._on_device_item_clicked(first, 0)
    window._on_device_item_clicked(second, 0)

    assert edited == []
