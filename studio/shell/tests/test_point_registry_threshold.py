"""ZADANIA p. 6: the switching counter's warning threshold is a setting on
the DI point - a column of the point registry, editable for DI points
only, saved with the project and part of settings_hash."""
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from studio.shell.main_window import StudioMainWindow
from studio.shell.project_format import Card, Location, load_project, save_project, settings_snapshot
from studio.shell.project_panels import sync_points_for_card


def _app():
    return QApplication.instance() or QApplication([])


def _window(tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    return StudioMainWindow(settings=settings)


def _close(win):
    from PySide6.QtCore import QTimer
    for timer in win.findChildren(QTimer):
        timer.stop()
    win.hide()


def test_threshold_column_is_editable_for_di_points_only_and_saves_with_the_project(tmp_path):
    _app()
    win = _window(tmp_path)
    project = win._project
    project.locations = [Location("KOT", "Kotlownia")]
    card = Card("ELA1", "ELA01", channel_kinds={"DI": 2, "AI": 1}, location="KOT")
    project.cards.append(card)
    sync_points_for_card(project, card)
    win._open_point_registry()
    panel = win._point_registry_panel
    try:
        col = panel._COLS.index("warning_threshold")
        rows = {panel.table.item(r, 0).text(): r for r in range(panel.table.rowCount())}
        di_item = panel.table.item(rows["ELA1.DI.1"], col)
        ai_item = panel.table.item(rows["ELA1.AI.1"], col)
        assert di_item.text() == "" and ai_item.text() == ""
        assert bool(di_item.flags() & di_item.flags().ItemIsEditable)
        assert not bool(ai_item.flags() & ai_item.flags().ItemIsEditable)

        di_item.setText("5000")
        point = next(p for p in project.points if p.address == "ELA1.DI.1")
        assert point.warning_threshold == 5000 and project.is_dirty
        assert settings_snapshot(project)["switching_counters/ELA1.DI.1/warning_threshold"] == 5000

        path = tmp_path / "projekt.epw"
        save_project(project, path)
        reloaded = load_project(path)
        assert next(p for p in reloaded.points if p.address == "ELA1.DI.1").warning_threshold == 5000

        di_item.setText("")
        assert point.warning_threshold is None
        assert panel.table.item(rows["ELA1.DI.1"], panel._COLS.index("device")) is not None
    finally:
        _close(win)
