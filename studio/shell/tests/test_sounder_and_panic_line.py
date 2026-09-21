"""The engineer's side of the sounder, in Studio.

Owner's instruction: "chce moc to swobodnie programowac ustawiajac bit
wewnetrzny alarm i pobudzenie danego DO ktory wyjdzie na syrene" - so
what Studio offers here is SETTINGS, never an output to pick. The siren
is wired in Logic Studio, from SEC.SYSTEM.SIREN_ACTIVE to whatever DO the
installation uses.

Plus the PANIC (napadowa) line type, which simply had no entry before.
"""
import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from studio.shell.project_format import (
    Line, LineType, Sounder, Zone, new_project, read_project, save_project,
    settings_diff, settings_snapshot,
)
from studio.shell.project_panels import LinesPanel, ZonesPanel


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


class FakeStudioWindow:
    """Only what these two panels touch on their window."""

    def __init__(self, project):
        self._project = project
        self._lines_panel = None
        self.changes = 0

    def _on_project_changed(self):
        self.changes += 1


def _project():
    project = new_project("Sounder test")
    project.zones.append(Zone(id="Z1", name="Hall"))
    return project


@pytest.fixture
def panel(app):
    project = _project()
    window = FakeStudioWindow(project)
    widget = ZonesPanel(window)
    yield widget, window, project
    widget.deleteLater()


# --- the sounder as settings ------------------------------------------------

def test_the_sounder_is_settings_with_no_output_to_choose(panel):
    """The absence is the point: nothing on this panel picks a DO."""
    widget, _, _ = panel
    assert hasattr(widget, "siren_seconds_spin")
    assert hasattr(widget, "panic_silent_check")
    assert not [name for name in vars(widget) if "siren" in name and "tag" in name], \
        "the siren output belongs in Logic Studio, not in a config dialog"


def test_changing_the_sounding_time_reaches_the_project(panel):
    widget, window, project = panel
    widget.siren_seconds_spin.setValue(90.0)

    assert project.sounder.siren_seconds == 90.0
    assert window.changes >= 1, "the project is marked dirty like any other edit"


def test_a_hold_up_line_can_be_made_audible(panel):
    widget, _, project = panel
    assert project.sounder.panic_silent is True, "silent is the sensible default"

    widget.panic_silent_check.setChecked(False)

    assert project.sounder.panic_silent is False


def test_zero_reads_as_no_limit_not_as_an_instantly_silent_siren(panel):
    widget, _, _ = panel
    widget.siren_seconds_spin.setValue(0.0)
    assert widget.siren_seconds_spin.text() == widget.siren_seconds_spin.specialValueText()


def test_the_panel_shows_what_the_project_already_holds(app):
    project = _project()
    project.sounder = Sounder(siren_seconds=45.0, panic_silent=False)
    widget = ZonesPanel(FakeStudioWindow(project))
    try:
        assert widget.siren_seconds_spin.value() == 45.0
        assert widget.panic_silent_check.isChecked() is False
    finally:
        widget.deleteLater()


# --- the panic line type ----------------------------------------------------

def test_panic_is_offered_as_a_line_type(app):
    project = _project()
    project.lines.append(Line(id="L1", name="Hold-up button", zone_id="Z1"))
    window = FakeStudioWindow(project)
    widget = LinesPanel(window)
    try:
        combo = widget.table.cellWidget(0, 3)
        assert combo.findData(LineType.PANIC) >= 0, "napadowa had no entry at all before"

        combo.setCurrentIndex(combo.findData(LineType.PANIC))

        assert project.lines[0].line_type == LineType.PANIC
    finally:
        widget.deleteLater()


def test_the_sounder_and_the_panic_line_survive_a_project_round_trip(tmp_path):
    project = _project()
    project.sounder = Sounder(siren_seconds=90.0, panic_silent=False)
    project.lines.append(Line(id="L1", name="Hold-up", zone_id="Z1", line_type=LineType.PANIC))
    path = tmp_path / "projekt.epw"
    save_project(project, path)

    result = read_project(path)

    assert not result.warnings
    assert result.project.sounder == Sounder(siren_seconds=90.0, panic_silent=False)
    assert result.project.lines[0].line_type == LineType.PANIC


def test_a_project_saved_before_the_sounder_existed_still_opens(tmp_path):
    """No migration: a project with no sounder section gets the
    defaults, without a warning."""
    path = tmp_path / "projekt.epw"
    save_project(_project(), path)

    result = read_project(path)

    assert not result.warnings
    assert result.project.sounder == Sounder()


def test_the_sounder_is_a_setting_studio_can_compare_with_the_controller():
    """So "the siren sounds for 45 s here and 180 s there" shows up in
    the live-settings table like any other nastawa."""
    mine = _project()
    mine.sounder = Sounder(siren_seconds=45.0, panic_silent=True)
    theirs = _project()

    differences = dict((path, (a, b)) for path, a, b in
                       settings_diff(settings_snapshot(mine), settings_snapshot(theirs)))

    assert differences["sounder/system/siren_seconds"] == (45.0, 180.0)
    assert "sounder/system/panic_silent" not in differences
