"""User report 3.4 ("lokalizacja punktu — dziedziczenie z karty"),
exercised through the real PointRegistryPanel widget - the pure-function
half (effective_location(), the "card change never overwrites an
explicit override" proof) lives in test_project_panels.py; this file
covers the parts only the real combo/table/dialog can prove: which entry
is selected and how it's styled, and the multi-row bulk action.
"""
import os
import tempfile

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QDialog

from studio.shell.main_window import StudioMainWindow
from studio.shell.project_format import Card, Location
from studio.shell.project_panels import PointRegistryPanel, sync_points_for_card


def _app():
    return QApplication.instance() or QApplication([])


def _window(tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    return StudioMainWindow(settings=settings)


def test_a_fresh_points_combo_shows_the_inherited_card_location(tmp_path):
    _app()
    win = _window(tmp_path)
    win._project.locations.append(Location(code="KOT", description="Kotlownia"))
    card = Card(id="ELA1", model="ELA01", kind="DI", channels=1, location="KOT")
    win._project.cards.append(card)
    sync_points_for_card(win._project, card)

    panel = PointRegistryPanel(win)
    combo = panel.table.cellWidget(0, 2)
    assert combo.currentIndex() == 0
    assert "KOT" in combo.currentText()
    assert combo.font().italic() is True


def test_picking_a_code_sets_an_explicit_override(tmp_path):
    _app()
    win = _window(tmp_path)
    win._project.locations.append(Location(code="KOT", description="Kotlownia"))
    win._project.locations.append(Location(code="PIWNICA", description="Piwnica"))
    card = Card(id="ELA1", model="ELA01", kind="DI", channels=1, location="KOT")
    win._project.cards.append(card)
    sync_points_for_card(win._project, card)

    panel = PointRegistryPanel(win)
    combo = panel.table.cellWidget(0, 2)
    idx = combo.findData("PIWNICA")
    combo.setCurrentIndex(idx)

    assert win._project.points[0].location == "PIWNICA"


def test_picking_inherit_again_clears_the_override(tmp_path):
    _app()
    win = _window(tmp_path)
    win._project.locations.append(Location(code="KOT", description="Kotlownia"))
    card = Card(id="ELA1", model="ELA01", kind="DI", channels=1, location="KOT")
    win._project.cards.append(card)
    sync_points_for_card(win._project, card)
    win._project.points[0].location = "KOT"  # an explicit value, same text as the card's own

    panel = PointRegistryPanel(win)
    combo = panel.table.cellWidget(0, 2)
    from studio.shell.project_panels import _INHERIT_LOCATION_SENTINEL
    idx = combo.findData(_INHERIT_LOCATION_SENTINEL)
    combo.setCurrentIndex(idx)

    assert win._project.points[0].location is None


def test_set_location_for_selected_applies_to_every_selected_row(tmp_path, monkeypatch):
    _app()
    win = _window(tmp_path)
    win._project.locations.append(Location(code="KOT", description="Kotlownia"))
    card = Card(id="ELA1", model="ELA01", kind="DI", channels=3, location="")
    win._project.cards.append(card)
    sync_points_for_card(win._project, card)

    from PySide6.QtCore import QItemSelectionModel

    panel = PointRegistryPanel(win)
    panel.table.selectRow(0)
    panel.table.selectionModel().select(
        panel.table.model().index(2, 0),
        QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
    )

    # Stub the dialog's exec() to pick "KOT" without a real click loop -
    # same "no interactive user in a test" reasoning as QMessageBox
    # stubbing elsewhere in this suite.
    from studio.shell.project_panels import QComboBox as _RealCombo  # noqa: F401
    original_exec = QDialog.exec

    def fake_exec(self):
        combo = self.findChild(_RealCombo)
        combo.setCurrentIndex(combo.findData("KOT"))
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QDialog, "exec", fake_exec)
    try:
        panel.set_location_for_selected()
    finally:
        monkeypatch.setattr(QDialog, "exec", original_exec)

    addresses_changed = {p.address for p in win._project.points if p.location == "KOT"}
    assert addresses_changed == {"ELA1.DI.1", "ELA1.DI.3"}
    assert win._project.points[1].location is None  # row 1 (ELA1.DI.2) was never selected
