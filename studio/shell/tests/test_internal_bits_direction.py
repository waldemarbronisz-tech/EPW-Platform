"""Internal bits IN/OUT in Studio (owner's decisions 2026-09-22): the
Signals department sets a bit's direction and who may write it, the
apparatus registry names an OUT bit as an apparatus's permission, the
point registry shows the bits with their live value, and "Sprawdź
projekt" refuses a permission the logic does not compute. Every
assertion on the registry reads the LOGIC project's own list, never the
panel."""
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox

from studio.shell import i18n as shell_i18n
from studio.shell.main_window import StudioMainWindow
from studio.shell.project_format import Card, Device, Point, load_project, new_project, save_project
from studio.shell.project_panels import (device_from_synoptic_dict, device_to_synoptic_dict, sync_points_for_card,
                                         validate_project)


def _app():
    return QApplication.instance() or QApplication([])


def _window(tmp_path):
    shell_i18n.set_language("pl")
    return StudioMainWindow(settings=QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat))


def _close(win):
    for timer in win.findChildren(QTimer):
        timer.stop()
    win.hide()


def _registry(win):
    return win._logic_panel.main_window().project.settings["internal_bits"]


def _bit(name, **over):
    entry = {"name": name, "type": "BOOL", "retentive": False, "description": "", "label": "", "category": ""}
    entry.update(over)
    return entry


def test_the_signals_department_sets_direction_and_writers_into_the_logic_registry(tmp_path):
    _app()
    win = _window(tmp_path)
    try:
        win._open_signals()
        tab = win._signals_panel.internal_tab
        _registry(win).append(_bit("START", description="Start z panelu"))
        _registry(win).append(_bit("ZEZW", direction="IN", panel_level="Engineer", remote_write=True))
        tab.refresh()
        direction = tab.table.cellWidget(0, tab.COL_DIRECTION)
        panel = tab.table.cellWidget(0, tab.COL_PANEL)
        remote = tab.table.cellWidget(0, tab.COL_REMOTE)
        assert isinstance(direction, QComboBox) and direction.currentData() == "OUT"
        assert not panel.isEnabled() and not remote.isEnabled(), "an OUT bit has no outside writers"
        assert tab.table.cellWidget(1, tab.COL_DIRECTION).currentData() == "IN"
        assert tab.table.cellWidget(1, tab.COL_PANEL).currentData() == "Engineer"
        assert isinstance(tab.table.cellWidget(1, tab.COL_REMOTE), QCheckBox) and tab.table.cellWidget(1, tab.COL_REMOTE).isChecked()
        # switching START to IN: the owner's default - the panel may, at Operator, nothing remote
        direction.setCurrentIndex(direction.findData("IN"))
        entry = _registry(win)[0]
        assert entry["direction"] == "IN" and entry["panel_level"] == "Operator" and not entry.get("remote_write")
        panel = tab.table.cellWidget(0, tab.COL_PANEL)
        assert panel.isEnabled() and panel.currentData() == "Operator"
        panel.setCurrentIndex(panel.findData(""))
        assert _registry(win)[0]["panel_level"] == ""
        tab.table.cellWidget(0, tab.COL_REMOTE).setChecked(True)
        assert _registry(win)[0]["remote_write"] is True
        headers = [tab.table.horizontalHeaderItem(c).text() for c in (tab.COL_DIRECTION, tab.COL_PANEL, tab.COL_REMOTE)]
        assert headers == ["Kierunek", "Panel", "Zdalnie"]
    finally:
        _close(win)


def test_the_apparatus_registry_offers_only_out_bool_bits_as_a_permission(tmp_path):
    _app()
    win = _window(tmp_path)
    try:
        win._open_signals()                       # builds the embedded logic editor that owns the registry
        _registry(win).extend([_bit("KMG1_ZEZW", description="Blokada od Q1 otwartego"),
                               _bit("START", direction="IN"),
                               _bit("POMIAR", type="REAL")])
        win._project.devices.append(Device(id="KOT_KMG1", behavior="SWITCHED", kind="contactor",
                                           feedback=["ELA1.DI.1"], command=["ADA1.DO.1"]))
        win._project.devices.append(Device(id="KOT_T1", behavior="MEASURED", feedback=["ELA1.AI.1"]))
        win._open_devices()
        panel = win._devices_panel
        combo = panel.table.cellWidget(0, panel.COL_PERMISSION)
        offered = [combo.itemData(i) for i in range(combo.count())]
        assert offered == ["", "M.KMG1_ZEZW"], "an IN bit and a REAL register are not permissions"
        assert combo.itemText(1) == "M.KMG1_ZEZW — Blokada od Q1 otwartego"
        assert panel.table.horizontalHeaderItem(panel.COL_PERMISSION).text() == "Zezwolenie"
        assert not panel.table.cellWidget(1, panel.COL_PERMISSION).isEnabled(), "only a SWITCHED apparatus is commanded"
        combo.setCurrentIndex(1)
        assert win._project.devices[0].permission_bit == "M.KMG1_ZEZW" and win._project.is_dirty
        path = tmp_path / "projekt.epw"
        save_project(win._project, path)
        assert load_project(path).devices[0].permission_bit == "M.KMG1_ZEZW"
        combo.setCurrentIndex(0)
        assert win._project.devices[0].permission_bit == ""
    finally:
        _close(win)


def test_check_project_refuses_a_permission_the_logic_does_not_compute():
    project = new_project("Test")
    project.cards.append(Card(id="ELA1", model="ELA01", channel_kinds={"DI": 1, "AI": 1}))
    project.cards.append(Card(id="ADA1", model="ADA01", channel_kinds={"DO": 1}))
    project.points.extend([Point(address="ELA1.DI.1"), Point(address="ELA1.AI.1"), Point(address="ADA1.DO.1")])
    project.logic = {"settings": {"internal_bits": [_bit("KMG1_ZEZW"), _bit("START", direction="IN"),
                                                    _bit("POMIAR", type="REAL")]}}
    km = Device(id="KOT_KMG1", behavior="SWITCHED", feedback=["ELA1.DI.1"], command=["ADA1.DO.1"], permission_bit="M.KMG1_ZEZW")
    project.devices.append(km)
    assert validate_project(project) == []
    km.permission_bit = "M.NIE_MA"
    issues = validate_project(project)
    assert len(issues) == 1 and issues[0].severity == "error" and "M.NIE_MA" in issues[0].message
    assert issues[0].target == "devices" and issues[0].arg == "KOT_KMG1"
    km.permission_bit = "M.START"
    issues = validate_project(project)
    assert len(issues) == 1 and issues[0].severity == "error" and "WY" in issues[0].message
    km.permission_bit = "MW.POMIAR"
    assert [i.severity for i in validate_project(project)] == ["error"]
    km.permission_bit = "M.KMG1_ZEZW"
    km.behavior = "SIGNAL"
    km.command = []
    issues = validate_project(project)
    assert len(issues) == 1 and issues[0].severity == "warning" and "SWITCHED" in issues[0].message


def test_the_point_registry_lists_the_bits_with_their_live_value(tmp_path):
    _app()
    win = _window(tmp_path)
    try:
        win._open_signals()
        _registry(win).extend([_bit("START", direction="IN", description="Start z panelu"), _bit("KMG1_ZEZW")])
        card = Card(id="ELA1", model="ELA01", channel_kinds={"DI": 1})
        win._project.cards.append(card)
        sync_points_for_card(win._project, card)
        win._open_point_registry()
        panel = win._point_registry_panel
        addresses = [panel.table.item(r, 0).text() for r in range(panel.table.rowCount())]
        assert addresses == ["ELA1.DI.1", "M.START", "M.KMG1_ZEZW"]
        row = addresses.index("M.START")
        assert panel.table.item(row, 1).text() == "Start z panelu"
        assert not bool(panel.table.item(row, 1).flags() & panel.table.item(row, 1).flags().ItemIsEditable)
        assert "WE" in panel.table.item(row, 3).text()
        panel.apply_live({"M.START": {"value": True, "quality": "GOOD"}}, {})
        assert panel.live_rows()[row] == ("M.START", "1", False)
        # the bits' own filter
        combo = panel.card_filter
        combo.setCurrentIndex(combo.findData("__internal_bits__"))
        assert [panel.table.item(r, 0).text() for r in range(panel.table.rowCount())] == ["M.START", "M.KMG1_ZEZW"]
        combo.setCurrentIndex(combo.findData("ELA1"))
        assert [panel.table.item(r, 0).text() for r in range(panel.table.rowCount())] == ["ELA1.DI.1"]
    finally:
        _close(win)


def test_the_synoptic_bridge_keeps_the_permission_bit():
    device = Device(id="KOT_KMG1", behavior="SWITCHED", feedback=["ELA1.DI.1"], command=["ADA1.DO.1"],
                    permission_bit="M.KMG1_ZEZW")
    data = device_to_synoptic_dict(device)
    assert data["permissionBit"] == "M.KMG1_ZEZW"
    assert device_from_synoptic_dict(data).permission_bit == "M.KMG1_ZEZW"
    data.pop("permissionBit")
    assert device_from_synoptic_dict(data).permission_bit == ""
