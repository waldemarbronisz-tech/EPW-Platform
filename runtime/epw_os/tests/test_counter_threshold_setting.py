"""ZADANIA p. 6: the switching counter's warning threshold is a SETTING in
the project (Point.warning_threshold on the DI point), not only a value
in the state file. The counter manager seeds its records from the
project, a panel change goes back into projekt.epw like every other
setting (revision +1, modified_by "panel"), and the counts themselves
still never touch the project file. Same harness as
test_runtime_reads_project."""
import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core import project_format as pf  # noqa: E402
from epw_os.core.epw_core import EPWCore  # noqa: E402
from epw_os.core.project_epw import apply_changes, diff_settings  # noqa: E402
from epw_os.core.project_manager import ProjectManager  # noqa: E402


def _project(directory: Path, threshold=None) -> Path:
    from studio.shell.project_format import Card, Location, new_project, save_project
    from studio.shell.project_panels import sync_points_for_card
    directory.mkdir(parents=True, exist_ok=True)
    project = new_project("Counters", author="Test")
    project.modules = ["switching_counters"]
    project.locations = [Location("KOT", "Kotlownia")]
    card = Card("DI1", "ELA01", channel_kinds={"DI": 4}, location="KOT")
    project.cards.append(card)
    sync_points_for_card(project, card)
    if threshold is not None:
        next(p for p in project.points if p.address == "DI1.DI.1").warning_threshold = threshold
    path = directory / "projekt.epw"
    save_project(project, path)
    return path


@pytest.fixture
def start_core(db):
    cores = []

    def _start(project_path):
        core = EPWCore()
        core.project_manager.project_file = str(project_path)
        core.startup()
        cores.append(core)
        return core

    yield _start
    for core in cores:
        if core.is_running:
            core.shutdown()


def test_the_projects_threshold_seeds_the_counter_and_wins_over_the_state_file(tmp_path, start_core):
    path = _project(tmp_path, threshold=5000)
    (tmp_path / "runtime_state.json").write_text(json.dumps({
        "format": "EPW_RUNTIME_STATE", "schema_version": 1,
        "switching_counters": {"DI1.DI.1": {"closes": 7, "opens": 7, "closed_seconds": 1.0, "closed_since": None,
                                            "first_transition": None, "last_transition": None,
                                            "warning_threshold": 10}}}), encoding="utf-8")
    core = start_core(path)
    snapshot = core.switching_counters.get_snapshot("DI1.DI.1")
    assert snapshot["warning_threshold"] == 5000           # the project's setting, not the state's 10
    assert snapshot["closes"] == 7                          # the counts are state and stay
    assert core.switching_counters.get_snapshot("DI1.DI.2")["warning_threshold"] is None
    assert core.project_manager.get_counter_warning_thresholds() == {f"DI1.DI.{n}": (5000 if n == 1 else None)
                                                                     for n in range(1, 5)}


def test_a_threshold_set_on_the_panel_is_written_back_as_a_setting(tmp_path, start_core):
    path = _project(tmp_path)
    core = start_core(path)
    assert pf.read_project(path).project.revision == 1

    core.switching_counters.set_warning_threshold("DI1.DI.2", 2500)

    saved = pf.read_project(path).project
    point = next(p for p in saved.points if p.address == "DI1.DI.2")
    assert (saved.revision, saved.modified_by, point.warning_threshold) == (2, "panel", 2500)
    assert next(p for p in saved.points if p.address == "DI1.DI.1").warning_threshold is None
    state = json.loads((tmp_path / "runtime_state.json").read_text(encoding="utf-8"))["switching_counters"]
    assert state["DI1.DI.2"]["warning_threshold"] == 2500
    assert "warning_threshold" not in json.dumps({k: v for k, v in saved.metadata.__dict__.items()})

    core.switching_counters.set_warning_threshold("DI1.DI.2", None)
    saved = pf.read_project(path).project
    assert next(p for p in saved.points if p.address == "DI1.DI.2").warning_threshold is None
    assert saved.revision == 3

    # The counts still never reach the project file.
    before = path.read_bytes()
    for value in (True, False, True):
        core.tag_manager.update_tag("DI1.DI.2", value)
    core.switching_counters.flush_to_project()
    assert path.read_bytes() == before


def test_a_threshold_for_a_tag_outside_the_project_stays_in_state_only(tmp_path, start_core):
    path = _project(tmp_path)
    core = start_core(path)
    assert core.project_manager.set_counter_warning_threshold("NOT.A.POINT", 3) is False
    core.switching_counters.set_warning_threshold("Legacy.DI9", 3)
    assert pf.read_project(path).project.revision == 1
    assert core.switching_counters.get_snapshot("Legacy.DI9")["warning_threshold"] == 3


def test_diff_and_apply_treat_the_threshold_as_a_setting(tmp_path):
    path = _project(tmp_path, threshold=100)
    pm = ProjectManager(str(path))
    assert pm.load_project()
    assert diff_settings(pm.project, pm.config).changes == []
    assert pm.set_counter_warning_threshold("DI1.DI.1", 250)
    diff = diff_settings(pm.project, pm.config)
    assert diff.structural == []
    assert [(c.section, c.record_id, c.field, c.old, c.new) for c in diff.changes] == [
        ("switching_counter_settings", "DI1.DI.1", "warning_threshold", 100, 250)]
    apply_changes(pm.project, diff.changes)
    assert next(p for p in pm.project.points if p.address == "DI1.DI.1").warning_threshold == 250
