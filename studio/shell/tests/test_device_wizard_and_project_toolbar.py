"""Two user reports from one screenshot session, both about "what does the
chrome do for the PROJECT":

1. "nie działa pasek na górze gdzie wpisujemy projekt zapis odczyt" -
   the fixed top toolbar's Nowy/Otwórz/Zapisz/Zapisz jako used to be the
   active EDITOR's own document (Logic/Synoptic) and did nothing at all
   on every other branch (Cards, Point Registry, ...). They are the
   project's (projekt.epw) now, everywhere - main_window._build_shared_
   toolbar; the editor documents moved to their contextual toolbars.

2. "stwórz kreator urządzenia gdzie krok po kroku mówi co gdzie
   dodawać" - device_wizard.DeviceWizard, exercised here page by page
   without exec() (the same real widgets a user drives, minus the modal
   loop), then apply_to_project() against a real Project.

Same harness as test_aspect_container_reuse.py. QMessageBox.warning is
monkeypatched wherever a validation refusal is expected - a real modal
would block forever offscreen.
"""
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

from studio.shell.device_wizard import DeviceWizard
from studio.shell.main_window import StudioMainWindow
from studio.shell.project_format import Card, Location, new_project


def _app():
    return QApplication.instance() or QApplication([])


def _window(tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    return StudioMainWindow(settings=settings)


def _no_dialogs(monkeypatch):
    calls = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: calls.append(a) or QMessageBox.StandardButton.Ok)
    return calls


# ---- 1. the top toolbar is the project's ------------------------------------

def test_top_toolbar_project_actions_are_live_with_no_editor_open(tmp_path):
    _app()
    win = _window(tmp_path)
    win._open_io_cards()  # a plain project branch, not Logic/Screens
    assert win.act_shared_new.isEnabled()
    assert win.act_shared_open.isEnabled()
    assert win.act_shared_save.isEnabled()
    assert win.act_shared_save_as.isEnabled()


def test_top_toolbar_save_saves_the_project_file(tmp_path, monkeypatch):
    """Save on a Cards branch must reach _save_project() - the .epw
    writer - not silently do nothing (the report) and not the editor's
    own document."""
    _app()
    win = _window(tmp_path)
    win._open_io_cards()
    path = tmp_path / "projekt.epw"
    win._project_path = str(path)
    win.act_shared_save.trigger()
    assert path.exists()


def test_top_toolbar_new_and_open_route_to_the_project(tmp_path, monkeypatch):
    _app()
    win = _window(tmp_path)
    win._open_point_registry()
    calls = []
    monkeypatch.setattr(win, "_new_project", lambda: calls.append("new"))
    monkeypatch.setattr(win, "_open_project", lambda: calls.append("open"))
    monkeypatch.setattr(win, "_save_project_as", lambda: calls.append("save_as"))
    win.act_shared_new.trigger()
    win.act_shared_open.trigger()
    win.act_shared_save_as.trigger()
    assert calls == ["new", "open", "save_as"]


def test_logic_document_lifecycle_moved_to_its_contextual_toolbar(tmp_path):
    """Not lost, moved: the Logic diagram's own New/Open/Save/Save As
    sit on the Logika contextual toolbar now."""
    _app()
    win = _window(tmp_path)
    win._open_logic()
    labels = [a.text() for a in win._aspect_containers["logic"].context_toolbar.actions()]
    from studio.shell.i18n import tr
    for key in ("toolbar.logic_new", "toolbar.logic_open", "toolbar.logic_save", "toolbar.logic_save_as"):
        assert tr(key) in labels


# ---- 2. the device wizard -----------------------------------------------------

def _wizard(project):
    _app()
    return DeviceWizard(project)


def _tick_kind(cards_page, row, kind, count):
    editor = cards_page.table.cellWidget(row, cards_page._COL_KINDS)
    editor._checks[kind].setChecked(True)
    editor._spins[kind].setValue(count)


def test_wizard_builds_a_whole_project_from_nothing(monkeypatch):
    calls = _no_dialogs(monkeypatch)
    project = new_project("x")
    w = _wizard(project)

    w.info_page.name_edit.setText("Kotlownia")
    w.info_page.author_edit.setText("WB")
    assert w.info_page.validatePage()

    w.modules_page.checks["intrusion"].setChecked(True)
    w.modules_page.checks["analog_inputs"].setChecked(True)

    w.locations_page.add_row("KOT", "Kotlownia")
    w.locations_page.add_row("MH", "Maszynownia")
    assert w.locations_page.validatePage()

    w.cards_page.initializePage()
    w.cards_page.add_row()
    w.cards_page.table.item(0, w.cards_page._COL_ID).setText("ELA1")
    w.cards_page.table.item(0, w.cards_page._COL_MODEL).setText("ELA01")
    _tick_kind(w.cards_page, 0, "DI", 8)
    _tick_kind(w.cards_page, 0, "AI", 4)
    combo = w.cards_page.table.cellWidget(0, w.cards_page._COL_LOCATION)
    combo.setCurrentIndex(combo.findData("KOT"))
    assert w.cards_page.validatePage()
    assert calls == []

    w.summary_page.initializePage()
    assert "Kotlownia" in w.summary_page.counts_label.text()
    assert "12" in w.summary_page.counts_label.text()  # 8 DI + 4 AI points

    added = w.apply_to_project(project)

    assert (project.metadata.name, project.metadata.author) == ("Kotlownia", "WB")
    assert set(project.modules) >= {"intrusion", "analog_inputs"}
    assert [(l.code, l.description) for l in project.locations] == [("KOT", "Kotlownia"), ("MH", "Maszynownia")]
    assert len(project.cards) == 1
    card = project.cards[0]
    assert (card.id, card.model, card.channel_kinds, card.location) == ("ELA1", "ELA01", {"DI": 8, "AI": 4}, "KOT")
    assert card.modbus_unit_id == 1
    addresses = {p.address for p in project.points}
    assert addresses == {f"ELA1.DI.{n}" for n in range(1, 9)} | {f"ELA1.AI.{n}" for n in range(1, 5)}
    assert added == {"modules": 2, "locations": 2, "cards": 1, "points": 12}
    assert project.is_dirty


def test_wizard_refuses_a_card_without_any_kind(monkeypatch):
    calls = _no_dialogs(monkeypatch)
    project = new_project("x")
    w = _wizard(project)
    w.cards_page.add_row()
    w.cards_page.table.item(0, w.cards_page._COL_ID).setText("ELA1")
    assert w.cards_page.validatePage() is False
    assert len(calls) == 1


def test_wizard_refuses_a_dotted_id_and_a_duplicate_id(monkeypatch):
    calls = _no_dialogs(monkeypatch)
    project = new_project("x")
    w = _wizard(project)
    w.cards_page.add_row()
    w.cards_page.table.item(0, w.cards_page._COL_ID).setText("ELA.1")
    _tick_kind(w.cards_page, 0, "DI", 2)
    assert w.cards_page.validatePage() is False

    w.cards_page.table.item(0, w.cards_page._COL_ID).setText("ELA1")
    w.cards_page.add_row()
    w.cards_page.table.item(1, w.cards_page._COL_ID).setText("ELA1")
    _tick_kind(w.cards_page, 1, "DO", 2)
    w.cards_page.table.cellWidget(1, w.cards_page._COL_MODBUS).setValue(9)
    assert w.cards_page.validatePage() is False
    assert len(calls) == 2


def test_wizard_refuses_a_bad_location_code(monkeypatch):
    calls = _no_dialogs(monkeypatch)
    w = _wizard(new_project("x"))
    w.locations_page.add_row("kot łownia", "x")
    assert w.locations_page.validatePage() is False
    assert len(calls) == 1


def test_wizard_never_removes_what_the_project_already_has(monkeypatch):
    """Add-and-update only: an existing module stays, an existing card
    keeps a kind the wizard page happens not to show ticked, an existing
    location keeps its code."""
    _no_dialogs(monkeypatch)
    project = new_project("Existing")
    project.modules.append("trends")
    project.locations.append(Location(code="KOT", description="old"))
    card = Card(id="ELA1", model="ELA01", channel_kinds={"DI": 4, "AI": 2}, modbus_unit_id=3, location="KOT")
    project.cards.append(card)
    from studio.shell.project_panels import sync_points_for_card
    sync_points_for_card(project, card)

    w = _wizard(project)
    # prefilled from the project
    assert w.info_page.name_edit.text() == "Existing"
    assert w.modules_page.checks["trends"].isChecked() and not w.modules_page.checks["trends"].isEnabled()
    assert w.locations_page.entries() == [("KOT", "old")]
    assert w.cards_page.entries()[0].channel_kinds == {"DI": 4, "AI": 2}

    # the removal buttons refuse existing rows
    w.locations_page.table.setCurrentCell(0, 0)
    w.locations_page._remove_selected()
    w.cards_page.table.setCurrentCell(0, 0)
    w.cards_page._remove_selected()
    assert w.locations_page.table.rowCount() == 1 and w.cards_page.table.rowCount() == 1

    w.locations_page.table.item(0, 1).setText("Kotlownia")  # description IS editable
    editor = w.cards_page.table.cellWidget(0, w.cards_page._COL_KINDS)
    editor._checks["AI"].setChecked(False)  # unticked here...
    _tick_kind(w.cards_page, 0, "DI", 8)     # ...and DI grown
    assert w.cards_page.validatePage()
    w.apply_to_project(project)

    assert project.modules == ["trends"]
    assert [(l.code, l.description) for l in project.locations] == [("KOT", "Kotlownia")]
    assert project.cards[0].channel_kinds == {"DI": 8, "AI": 2}  # AI kept, DI grown
    addresses = {p.address for p in project.points}
    assert addresses == {f"ELA1.DI.{n}" for n in range(1, 9)} | {"ELA1.AI.1", "ELA1.AI.2"}


def test_wizard_is_wired_into_the_window(tmp_path, monkeypatch):
    """File -> Kreator urządzenia... exists, and Finish lands on the Point
    Registry with the panels refreshed."""
    _app()
    win = _window(tmp_path)
    assert win.act_menu_device_wizard is not None

    from PySide6.QtWidgets import QDialog
    import studio.shell.device_wizard as dw

    class _Instant(dw.DeviceWizard):
        def exec(self):
            self.info_page.name_edit.setText("Via wizard")
            self.cards_page.add_row()
            self.cards_page.table.item(0, self.cards_page._COL_ID).setText("ADA1")
            _tick_kind(self.cards_page, 0, "DO", 4)
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(dw, "DeviceWizard", _Instant)
    win._run_device_wizard()

    assert win._project.metadata.name == "Via wizard"
    assert [c.id for c in win._project.cards] == ["ADA1"]
    assert win._active == "point_registry"
    assert win._point_registry_panel.table.rowCount() == 4
