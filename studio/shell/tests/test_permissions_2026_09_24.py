"""Studio's side of the owner's decisions of 2026-09-24: the "Wymuszanie"
column of the internal bits (an OUT bit's force permission) and the
"Zezwolenie" column of a DO point (its own permission bit), with the
checks "Sprawdź projekt" makes on the latter."""
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox

from studio.shell import i18n as shell_i18n
from studio.shell.main_window import StudioMainWindow
from studio.shell.project_format import Card, load_project, new_project, save_project
from studio.shell.project_panels import internal_bit_entries, sync_points_for_card, validate_project

IN_BIT = {"name": "START", "type": "BOOL", "retentive": False, "direction": "IN", "panel_level": "Operator",
          "remote_write": False, "description": "Zezwolenie z panelu", "label": "", "category": ""}
OUT_BIT = {"name": "KMG1_ZEZW", "type": "BOOL", "retentive": False, "direction": "OUT",
           "description": "Blokada od Q1 otwartego", "label": "", "category": ""}
OUT_REAL = {"name": "POZIOM", "type": "REAL", "retentive": False, "direction": "OUT",
            "description": "", "label": "", "category": ""}


def _app():
    return QApplication.instance() or QApplication([])


def _window(tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    return StudioMainWindow(settings=settings)


def _close(win):
    for timer in win.findChildren(QTimer):
        timer.stop()
    win.hide()


def _project_with_bits():
    project = new_project("Test")
    project.cards.append(Card("ELA1", "ELA01", channel_kinds={"DI": 1}))
    project.cards.append(Card("ADA1", "ADA01", channel_kinds={"DO": 2}))
    for card in project.cards:
        sync_points_for_card(project, card)
    project.logic = {"settings": {"internal_bits": [dict(IN_BIT), dict(OUT_BIT), dict(OUT_REAL)]}}
    return project


def _permission_issues(project):
    return [i for i in validate_project(project) if "zezwolenie" in i.message.lower()]


def test_the_force_column_is_a_choice_on_an_out_bit_and_a_given_on_an_in_bit(tmp_path):
    _app()
    shell_i18n.set_language("pl")
    win = _window(tmp_path)
    try:
        win._open_signals()
        tab = win._signals_panel.internal_tab
        # the registry lives in the embedded logic project - the tab edits THAT object
        tab.logic_project().settings["internal_bits"] = [dict(IN_BIT), dict(OUT_BIT), dict(OUT_REAL)]
        tab.refresh()
        headers = [tab.table.horizontalHeaderItem(c).text() for c in range(tab.table.columnCount())]
        assert headers[tab.COL_FORCE] == "Wymuszanie"
        rows = {tab.table.item(r, tab.COL_NAME).text(): r for r in range(tab.table.rowCount())}
        in_box = tab.table.cellWidget(rows["START"], tab.COL_FORCE)
        out_box = tab.table.cellWidget(rows["KMG1_ZEZW"], tab.COL_FORCE)
        assert isinstance(in_box, QCheckBox) and in_box.isChecked() and not in_box.isEnabled(), "an IN bit: always forceable"
        assert isinstance(out_box, QCheckBox) and not out_box.isChecked() and out_box.isEnabled()
        assert "logik" in out_box.toolTip().lower()
        out_box.setChecked(True)
        entries = tab.logic_project().settings["internal_bits"]
        assert internal_bit_entries(win) == entries, "the point registry reads the same object"
        entry = next(e for e in entries if e["name"] == "KMG1_ZEZW")
        assert entry["force_allowed"] is True
        assert next(e for e in entries if e["name"] == "START").get("force_allowed", True) is True
    finally:
        _close(win)


def test_a_do_row_offers_the_out_bool_bits_as_its_permission_and_a_di_row_offers_none(tmp_path):
    _app()
    shell_i18n.set_language("pl")
    win = _window(tmp_path)
    try:
        win._project = _project_with_bits()
        win._open_point_registry()
        panel = win._point_registry_panel
        panel.refresh()
        assert panel._COLS[panel._PERMISSION_COL] == "permission"
        assert panel._COLS[panel._DEVICE_COL] == "device" and panel._COLS[panel._LIVE_COL] == "live"
        assert panel.table.horizontalHeaderItem(panel._PERMISSION_COL).text() == "Zezwolenie"
        rows = {panel.table.item(r, 0).text(): r for r in range(panel.table.rowCount())}
        combo = panel.table.cellWidget(rows["ADA1.DO.1"], panel._PERMISSION_COL)
        assert isinstance(combo, QComboBox)
        offered = [combo.itemData(i) for i in range(combo.count())]
        assert offered == ["", "M.KMG1_ZEZW"], "only OUT BOOL bits - not the IN bit, not the REAL"
        assert combo.itemText(1) == "M.KMG1_ZEZW — Blokada od Q1 otwartego"
        assert not isinstance(panel.table.cellWidget(rows["ELA1.DI.1"], panel._PERMISSION_COL), QComboBox)
        combo.setCurrentIndex(1)
        point = next(p for p in win._project.points if p.address == "ADA1.DO.1")
        assert point.permission_bit == "M.KMG1_ZEZW" and win._project.is_dirty
        path = tmp_path / "projekt.epw"
        save_project(win._project, path)
        reloaded = next(p for p in load_project(path).points if p.address == "ADA1.DO.1")
        assert reloaded.permission_bit == "M.KMG1_ZEZW"
        # a bit the registry no longer has is shown, not silently dropped
        point.permission_bit = "M.STARY"
        panel.refresh()
        rows = {panel.table.item(r, 0).text(): r for r in range(panel.table.rowCount())}
        combo = panel.table.cellWidget(rows["ADA1.DO.1"], panel._PERMISSION_COL)
        assert combo.currentData() == "M.STARY" and "M.STARY" in combo.currentText()
    finally:
        _close(win)


def test_check_project_refuses_a_permission_on_a_di_an_unknown_bit_and_a_bit_that_is_not_out_bool():
    shell_i18n.set_language("pl")
    project = _project_with_bits()
    by_address = {p.address: p for p in project.points}
    by_address["ELA1.DI.1"].permission_bit = "M.KMG1_ZEZW"
    by_address["ADA1.DO.1"].permission_bit = "M.NIE_MA"
    by_address["ADA1.DO.2"].permission_bit = "M.START"
    issues = _permission_issues(project)
    assert sorted(i.message for i in issues) == sorted([
        "Punkt ELA1.DI.1 ma zezwolenie 'M.KMG1_ZEZW', ale zezwolenie może mieć tylko wyjście dwustanowe (DO).",
        "Punkt ADA1.DO.1 ma zezwolenie 'M.NIE_MA', którego nie ma w rejestrze bitów wewnętrznych logiki "
        "— sterownik potraktuje to jako brak zezwolenia.",
        "Punkt ADA1.DO.2: zezwolenie 'M.START' musi być bitem BOOL o kierunku WY (pisze go logika).",
    ])
    assert all(i.severity == "error" and i.target == "points" for i in issues)
    # a correct one is silent, a REAL OUT is not a permission
    by_address["ELA1.DI.1"].permission_bit = ""
    by_address["ADA1.DO.1"].permission_bit = "M.KMG1_ZEZW"
    by_address["ADA1.DO.2"].permission_bit = "MW.POZIOM"
    assert [i.message for i in _permission_issues(project)] == [
        "Punkt ADA1.DO.2: zezwolenie 'MW.POZIOM' musi być bitem BOOL o kierunku WY (pisze go logika)."]
    by_address["ADA1.DO.2"].permission_bit = ""
    assert not _permission_issues(project)


def test_the_two_columns_speak_both_languages():
    for language, force, permission in (("pl", "Wymuszanie", "Zezwolenie"), ("en", "Forcing", "Permission")):
        shell_i18n.set_language(language)
        assert shell_i18n.tr("signals.col_force") == force
        assert shell_i18n.tr("points.col_permission") == permission
        assert shell_i18n.tr("signals.force_tooltip") != "signals.force_tooltip"
        assert shell_i18n.tr("points.permission_tooltip") != "points.permission_tooltip"
