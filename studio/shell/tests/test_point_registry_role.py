"""Signal register etap 4 - the point registry's "Rola" and "Styk"
columns (a DI contact carrying a PWR/UPS/PROT signal), and the checks
"Sprawdź projekt" makes on them: a role the catalogue knows, on a DI
point, one point per role, and "two sources of one bit" when a device
block on the bus serves the same group."""
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication, QComboBox

from shared.logic import point_roles
from studio.shell.main_window import StudioMainWindow
from studio.shell.project_format import Card, Point, load_project, new_project, save_project
from studio.shell.project_panels import sync_points_for_card, validate_project


def _app():
    return QApplication.instance() or QApplication([])


def _window(tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    return StudioMainWindow(settings=settings)


def _close(win):
    for timer in win.findChildren(QTimer):
        timer.stop()
    win.hide()


def _panel_with_card(tmp_path):
    _app()
    win = _window(tmp_path)
    card = Card("ELA1", "ELA01", channel_kinds={"DI": 2, "AI": 1})
    win._project.cards.append(card)
    sync_points_for_card(win._project, card)
    win._open_point_registry()
    panel = win._point_registry_panel
    rows = {panel.table.item(r, 0).text(): r for r in range(panel.table.rowCount())}
    return win, panel, rows


def test_a_di_row_offers_exactly_the_catalogues_roles_and_an_ai_row_offers_none(tmp_path):
    win, panel, rows = _panel_with_card(tmp_path)
    try:
        role_col, contact_col = panel._COLS.index("role"), panel._COLS.index("contact")
        combo = panel.table.cellWidget(rows["ELA1.DI.1"], role_col)
        assert isinstance(combo, QComboBox)
        offered = [combo.itemData(i) for i in range(combo.count())]
        assert offered[0] is None and offered[1:] == point_roles.role_ids()
        assert "PWR.MAINS_OK" in offered and "UPS.ON_BATTERY" in offered and "PROT.ANY_TRIP" in offered
        assert "PWR.MAINS_LOST" not in offered and "PROT.UV_STAGE1.TRIP" not in offered
        assert combo.itemText(offered.index("PWR.MAINS_OK")).startswith("PWR.MAINS_OK")
        contact = panel.table.cellWidget(rows["ELA1.DI.1"], contact_col)
        assert isinstance(contact, QComboBox) and not contact.isEnabled(), "no role, no contact type to choose"
        assert [contact.itemData(i) for i in range(contact.count())] == ["NO", "NC"]
        assert panel.table.cellWidget(rows["ELA1.AI.1"], role_col) is None
        assert panel.table.cellWidget(rows["ELA1.AI.1"], contact_col) is None
        assert panel.table.item(rows["ELA1.AI.1"], role_col).text() == ""
        assert panel.table.horizontalHeaderItem(role_col).text() in ("Rola", "Role")
        assert panel.table.horizontalHeaderItem(contact_col).text() in ("Styk", "Contact")
    finally:
        _close(win)


def test_picking_a_role_and_a_contact_writes_the_point_and_survives_the_file(tmp_path):
    win, panel, rows = _panel_with_card(tmp_path)
    try:
        project = win._project
        role_col, contact_col = panel._COLS.index("role"), panel._COLS.index("contact")
        combo = panel.table.cellWidget(rows["ELA1.DI.2"], role_col)
        contact = panel.table.cellWidget(rows["ELA1.DI.2"], contact_col)
        combo.setCurrentIndex(combo.findData("PWR.MAINS_OK"))
        point = next(p for p in project.points if p.address == "ELA1.DI.2")
        assert point.role == "PWR.MAINS_OK" and point.contact == "NO" and project.is_dirty
        assert contact.isEnabled()
        contact.setCurrentIndex(contact.findData("NC"))
        assert point.contact == "NC"

        path = tmp_path / "projekt.epw"
        save_project(project, path)
        reloaded = next(p for p in load_project(path).points if p.address == "ELA1.DI.2")
        assert (reloaded.role, reloaded.contact) == ("PWR.MAINS_OK", "NC")

        # a reopened registry shows what the file holds
        panel.refresh()
        rows = {panel.table.item(r, 0).text(): r for r in range(panel.table.rowCount())}
        combo = panel.table.cellWidget(rows["ELA1.DI.2"], role_col)
        contact = panel.table.cellWidget(rows["ELA1.DI.2"], contact_col)
        assert combo.currentData() == "PWR.MAINS_OK" and contact.currentData() == "NC" and contact.isEnabled()

        combo.setCurrentIndex(0)
        assert point.role is None and not contact.isEnabled()
    finally:
        _close(win)


def test_the_device_column_and_the_live_column_still_sit_where_the_panel_says(tmp_path):
    win, panel, rows = _panel_with_card(tmp_path)
    try:
        assert panel._COLS[panel._DEVICE_COL] == "device" and panel._COLS[panel._LIVE_COL] == "live"
        assert panel.table.item(rows["ELA1.DI.1"], panel._DEVICE_COL) is not None
        assert panel.table.item(rows["ELA1.DI.1"], panel._LIVE_COL) is not None
        assert panel.table.columnCount() == len(panel._COLS)
    finally:
        _close(win)


def test_check_project_warns_about_two_sources_of_one_bit_and_two_contacts_on_one_role():
    project = new_project("Test")
    project.cards.append(Card(id="ELA1", model="ELA01", channel_kinds={"DI": 3}))
    project.cards.append(Card(id="EPM1", model="EPM", channel_kinds={}))
    project.points.append(Point(address="ELA1.DI.1", role="PWR.MAINS_OK", contact="NC"))
    project.points.append(Point(address="ELA1.DI.2", role="UPS.ON_BATTERY"))
    project.points.append(Point(address="ELA1.DI.3", role="UPS.ON_BATTERY"))
    issues = validate_project(project)
    assert all(i.severity == "warning" for i in issues), [i.message for i in issues]
    messages = [i.message for i in issues]
    assert any("PWR.MAINS_OK" in m and "EPM1" in m and "ELA1.DI.1" in m for m in messages), messages
    assert any("UPS.ON_BATTERY" in m and "ELA1.DI.2" in m and "ELA1.DI.3" in m for m in messages), messages
    assert len(issues) == 2
    assert all(i.target == "points" and i.selector == "select_address" for i in issues)
    # no EPM on the bus: the mains contact is the only source, nothing to warn about
    project.cards = [c for c in project.cards if c.id != "EPM1"]
    project.points = [p for p in project.points if p.address != "ELA1.DI.3"]
    assert validate_project(project) == []
    # an ADA on the bus and a PROT role: the same two-sources warning
    project.cards.append(Card(id="ADA1", model="ADA01", channel_kinds={"DO": 2}))
    project.points[0].role = "PROT.ANY_TRIP"
    issues = validate_project(project)
    assert len(issues) == 1 and "PROT.ANY_TRIP" in issues[0].message and "ADA1" in issues[0].message


def test_check_project_refuses_an_unknown_role_a_role_on_an_ai_point_and_a_bad_contact():
    project = new_project("Test")
    project.cards.append(Card(id="ELA1", model="ELA01", channel_kinds={"DI": 1, "AI": 1}))
    project.points.append(Point(address="ELA1.DI.1", role="PWR.NOT_A_ROLE"))
    project.points.append(Point(address="ELA1.AI.1", role="UPS.FAULT"))
    issues = validate_project(project)
    assert [i.severity for i in issues] == ["error", "error"]
    assert "PWR.NOT_A_ROLE" in issues[0].message and issues[0].arg == "ELA1.DI.1"
    assert "UPS.FAULT" in issues[1].message and issues[1].arg == "ELA1.AI.1"
    project.points = [Point(address="ELA1.DI.1", role="UPS.FAULT", contact="XX")]
    issues = validate_project(project)
    assert len(issues) == 1 and issues[0].severity == "error" and "XX" in issues[0].message
