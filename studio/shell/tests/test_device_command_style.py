"""Task "wyłącznik jednocewkowy bistabilny": Device.command_style /
pulse_ms - the file format (round trip, camelCase keys, a pre-task file
without them), "Sprawdź projekt" (check 8) and the Apparatus Registry
panel's own two new columns. Same harness as test_cards_panel_multi_kind.
"""
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from studio.shell.main_window import StudioMainWindow
from studio.shell.project_format import Device, load_project, new_project, save_project
from studio.shell.project_panels import validate_project


def _app():
    return QApplication.instance() or QApplication([])


def _window(tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    return StudioMainWindow(settings=settings)


def _km1(**overrides):
    fields = dict(id="KOT_KM1", behavior="SWITCHED", feedback=["ELA1.DI.2"], command=["ADA1.DO.3", "ADA1.DO.4"],
                  command_style="PULSE_TOGGLE", pulse_ms=100)
    fields.update(overrides)
    return Device(**fields)


# --- format -----------------------------------------------------------------

def test_command_style_and_pulse_round_trip(tmp_path):
    p = new_project("T")
    p.devices.append(_km1())
    path = tmp_path / "p.epw"
    save_project(p, path)
    loaded = load_project(path)
    assert (loaded.devices[0].command_style, loaded.devices[0].pulse_ms) == ("PULSE_TOGGLE", 100)


def test_a_device_saved_before_this_task_loads_as_maintained(tmp_path):
    """A file without commandStyle/pulseMs keeps meaning what it always
    meant - a level on the output."""
    import gzip, json
    data = {"format": "EPW_PROJECT_FILE", "schema_version": 2, "project": {"name": "old"},
            "devices": [{"id": "D1", "behavior": "SWITCHED", "feedback": [], "command": ["ADA1.DO.1"]}]}
    path = tmp_path / "old.epw"
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(data, f)
    loaded = load_project(path)
    assert (loaded.devices[0].command_style, loaded.devices[0].pulse_ms) == ("MAINTAINED", 0)


# --- Sprawdź projekt ----------------------------------------------------------

def _project_with(device):
    from studio.shell.project_format import Card, Point
    p = new_project("T")
    p.cards.append(Card(id="ELA1", model="ELA01", channel_kinds={"DI": 4}))
    p.cards.append(Card(id="ADA1", model="ADA01", channel_kinds={"DO": 4}))
    for n in range(1, 5):
        p.points.append(Point(address=f"ELA1.DI.{n}"))
        p.points.append(Point(address=f"ADA1.DO.{n}"))
    p.devices.append(device)
    return p


def test_the_schematic_configuration_validates_clean():
    assert validate_project(_project_with(_km1())) == []


def test_toggle_without_feedback_is_an_error():
    issues = validate_project(_project_with(_km1(feedback=[])))
    assert [i.severity for i in issues] == ["error"]
    assert "KOT_KM1" in issues[0].message and issues[0].target == "devices"


def test_pulsed_style_without_pulse_time_is_an_error():
    for style in ("PULSE", "PULSE_TOGGLE"):
        issues = validate_project(_project_with(_km1(command_style=style, pulse_ms=0)))
        assert any("0 ms" in i.message and i.severity == "error" for i in issues), style


def test_maintained_never_needs_a_pulse_time():
    assert validate_project(_project_with(_km1(command_style="MAINTAINED", pulse_ms=0))) == []


# --- panel ---------------------------------------------------------------------

def test_registry_panel_edits_style_and_pulse(tmp_path):
    _app()
    win = _window(tmp_path)
    win._project.devices.append(Device(id="KOT_KM1", behavior="SWITCHED", command=["ADA1.DO.3"]))
    win._open_devices()
    panel = win._devices_panel

    style_combo = panel.table.cellWidget(0, 5)
    pulse_spin = panel.table.cellWidget(0, 6)
    assert style_combo.currentData() == "MAINTAINED"
    assert not pulse_spin.isEnabled()  # a level has no pulse time

    style_combo.setCurrentIndex(style_combo.findData("PULSE_TOGGLE"))
    assert pulse_spin.isEnabled()
    pulse_spin.setValue(150)

    device = win._project.devices[0]
    assert (device.command_style, device.pulse_ms) == ("PULSE_TOGGLE", 150)


def test_registry_panel_disables_style_for_a_non_switched_apparatus(tmp_path):
    _app()
    win = _window(tmp_path)
    win._project.devices.append(Device(id="KOT_S1", behavior="SIGNAL", feedback=["ELA1.DI.1"]))
    win._open_devices()
    panel = win._devices_panel
    assert not panel.table.cellWidget(0, 5).isEnabled()
    assert not panel.table.cellWidget(0, 6).isEnabled()
