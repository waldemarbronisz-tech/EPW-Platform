"""Studio against a REAL running controller (the software-commissioning
stack: virtual Modbus bus, EPWCore, uvicorn): "Na żywo" shows the bus's
inputs in the point registry and the cards' health, a force from the
point registry pins an input against the bus and drives a coil, the
protection path is refused, and leaving force mode releases everything
on the controller."""
import os

os.environ["EPW_TESTING"] = "1"

from epw_os.tests.test_software_commissioning import _wait, stack  # noqa: E402,F401 - the fixture


def test_live_values_and_forces_travel_between_studio_and_the_controller(stack, tmp_path, monkeypatch):
    bus, core, project_path, url, tokens = stack
    from PySide6.QtCore import QSettings, QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox
    from studio.shell.main_window import StudioMainWindow
    QApplication.instance() or QApplication([])

    laptop = tmp_path / "laptop" / "projekt.epw"
    laptop.parent.mkdir()
    laptop.write_bytes(project_path.read_bytes())
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    settings.setValue("controller/host", url)
    settings.setValue("controller/token", tokens["Engineer"])
    win = StudioMainWindow(settings=settings)
    win._load_project_from_path(str(laptop))
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.StandardButton.Yes)
    try:
        assert _wait(lambda: core.tag_manager.get_tag("ELA1.DI.1").quality.value == "GOOD")
        bus.set_input(1, 2, True)
        assert _wait(lambda: core.tag_manager.get_value("ELA1.DI.2") is True)

        win._open_point_registry()
        win._open_io_cards()
        win._toggle_live(True)
        assert win.live_monitor().connected
        rows = {a: text for a, text, _f in win._point_registry_panel.live_rows()}
        assert rows["ELA1.DI.2"] == "1" and rows["ELA1.DI.1"] == "0"
        assert _wait(lambda: core.tag_manager.get_tag("Safety.ELA1.Healthy") is not None, timeout=8)
        win.live_monitor().poll()
        assert dict(win._cards_panel.responds_rows())["ELA1"] in ("tak", "yes")

        # A force from the registry (KOT_KM1's feedback, a contactor): the
        # input reads False on the panel although the bus says True, until
        # it is released.
        assert win.set_force_mode(True)
        assert win._point_registry_panel.apply_forces([("ELA1.DI.2", False)]) == []
        assert core.force_manager.snapshot()[0]["tag"] == "ELA1.DI.2"
        assert core.tag_manager.get_value("ELA1.DI.2") is False and core.tag_manager.is_forced("ELA1.DI.2")
        bus.set_input(1, 2, True)
        assert not _wait(lambda: core.tag_manager.get_value("ELA1.DI.2") is True, timeout=0.5)
        rows = {a: (text, forced) for a, text, forced in win._point_registry_panel.live_rows()}
        assert rows["ELA1.DI.2"][1] is True and rows["ELA1.DI.2"][0].startswith("F")
        assert core.force_manager.seconds_since_heartbeat() < 5

        # The protection path (KOT_Q1 is a breaker: its feedback and its command) is refused with the reason shown.
        refused = win._point_registry_panel.apply_forces([("ADA1.DO.1", True), ("ELA1.DI.1", True)])
        assert len(refused) == 2
        assert refused and "protection path" in refused[0][1]

        # A forced output reaches the bus through the driver boundary.
        assert win._point_registry_panel.apply_forces([("ADA1.DO.4", True)]) == []
        assert _wait(lambda: (1, "coil", 4, True) in bus.writes)
        assert core.tag_manager.get_value("ADA1.DO.4") is True

        # Leaving force mode drops everything on the controller; the input
        # follows the bus again on the next poll.
        assert win.set_force_mode(False) is False
        assert _wait(lambda: core.force_manager.snapshot() == [])
        assert _wait(lambda: core.tag_manager.get_value("ELA1.DI.2") is True)
        assert not any(forced for _a, _t, forced in win._point_registry_panel.live_rows())
    finally:
        win._force_mode = False
        for timer in win.findChildren(QTimer):
            timer.stop()
        win.hide()
