"""Task "runtime czyta projekt.epw" - runtime works from the project Studio
saves, keeps its running state apart from it, and writes settings back.

Every project used here is built with Studio's OWN code - the shared
format module and studio/shell/project_panels.py's sync_points_for_card(),
the function Studio's point registry calls when a card is added - and
saved with Studio's save_project(). Runtime then starts on that file
through its normal EPWCore.startup(), the same path main.py takes.

Grouped by the task's stages:
  etap 2  runtime_state.json - arming written at once and restored,
          counters never touching the project, losing the file
  etap 3  cards/points -> tags, apparatuses, composition, logic check,
          structure refused
  etap 4  a panel setting -> projekt.epw revision + 1, "panel", audit
  etap 5  migration of the old project.json, REST header, install
  etap 1  (runtime side) a damaged projekt.epw does not bring runtime down
"""
import gzip
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core import project_format as pf
from epw_os.core.access_manager import AccessLevel
from epw_os.core.addressing import is_address
from epw_os.core.epw_core import EPWCore
from epw_os.core.project_manager import ProjectManager

ALL_MODULES = ("intrusion", "analog_inputs", "switching_counters", "protection_process", "protection_settings",
               "engineer_mode", "service_notes")


def _studio_project(directory: Path, modules=ALL_MODULES, with_zone=True, name="Test site") -> Path:
    from studio.shell.project_format import (Card, Device, Line, Location, ProcessProtection, Zone, new_project,
                                             save_project)
    from studio.shell.project_panels import sync_points_for_card

    directory.mkdir(parents=True, exist_ok=True)
    project = new_project(name, author="Test")
    project.modules = list(modules)
    project.locations = [Location("KOT", "Kotłownia"), Location("MH", "Maszynownia")]
    for card in (Card("DI1", "ELA01", "DI", 8, location="KOT"), Card("DO1", "ADA01", "DO", 4, location="KOT"),
                 Card("AI1", "EPM01", "AI", 2, location="MH")):
        project.cards.append(card)
        sync_points_for_card(project, card)
    points = {p.address: p for p in project.points}
    points["DI1.DI.1"].description = "Q1 feedback"
    points["DI1.DI.2"].location = "MH"
    points["DI1.DI.2"].technical_note = "X2:14, LiYCY 2x0.75"
    points["DO1.DO.1"].description = "Q1 coil"
    boiler = points["AI1.AI.1"]
    boiler.description, boiler.signal_type, boiler.unit, boiler.decimals = "Boiler temperature", "4-20mA", "°C", 1
    boiler.raw_min, boiler.raw_max, boiler.eng_min, boiler.eng_max = 4.0, 20.0, 0.0, 120.0
    project.devices = [
        Device(id="KOT_Q1", behavior="SWITCHED", feedback=["DI1.DI.1"], command=["DO1.DO.1"]),
        Device(id="KOT_KM1", behavior="SWITCHED", feedback=["DI1.DI.3"], command=["DO1.DO.3"]),
        Device(id="KOT_ALARM", behavior="SIGNAL", feedback=["DI1.DI.6"]),
    ]
    if with_zone:
        project.zones = [Zone("Z1", "Ground floor", exit_delay_seconds=0.0, entry_delay_seconds=30.0)]
        project.lines = [Line("L1", "Front door", "Z1", tag="DI1.DI.4")]
    project.process_protections = [ProcessProtection("PP1", "Boiler overheat", analog_tag="AI1.AI.1",
                                                     upper_threshold=95.0, lower_threshold=0.0)]
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


def _audit_details(event_type: str) -> list:
    from epw_os.db.database import SessionLocal
    from epw_os.db.models import AuditLog
    session = SessionLocal()
    try:
        return [row.detail for row in session.query(AuditLog).filter(AuditLog.event_type == event_type).all()]
    finally:
        session.close()


def _names(core, kind) -> list:
    return sorted(t.name for t in core.tag_manager.list_tags() if is_address(t.name, kind))


# --- etap 3: cards, points, apparatuses, composition ----------------------------

def test_full_cycle_studio_project_runtime_tags_match_the_point_registry(tmp_path, start_core):
    core = start_core(_studio_project(tmp_path, with_zone=False))

    registry = core.project_manager.get_point_registry()
    assert _names(core, "DI") == sorted(p["address"] for p in registry if p["kind"] == "DI")
    assert _names(core, "DI") == [f"DI1.DI.{n}" for n in range(1, 9)]
    assert _names(core, "DO") == [f"DO1.DO.{n}" for n in range(1, 5)]
    assert _names(core, "AI") == ["AI1.AI.1", "AI1.AI.2"]

    q1 = core.tag_manager.get_tag("DI1.DI.1")
    assert (q1.description, q1.location) == ("Q1 feedback", "KOT")
    inherited_override = core.tag_manager.get_tag("DI1.DI.2")
    assert (inherited_override.location, inherited_override.technical_note) == ("MH", "X2:14, LiYCY 2x0.75")
    assert core.project_manager.get_output_descriptions() == {"DO1.DO.1": "Q1 coil"}

    boiler = next(p for p in core.project_manager.get_analog_points() if p["tag"] == "AI1.AI.1")
    assert (boiler["signal_type"], boiler["raw_min"], boiler["eng_max"], boiler["unit"]) == ("4-20mA", 4.0, 120.0, "°C")
    assert core.startup_issues == []


def test_apparatus_register_and_main_view_symbols_come_from_the_project(tmp_path, start_core):
    core = start_core(_studio_project(tmp_path, with_zone=False))

    q1 = core.apparatus_registry.get("KOT_Q1")
    assert (q1.behavior, q1.feedback, q1.command) == ("SWITCHED", ["DI1.DI.1"], ["DO1.DO.1"])
    assert core.apparatus_registry.get_by_role("main_view.q1").id == "KOT_Q1"
    assert core.apparatus_registry.get_by_role("main_view.km1").id == "KOT_KM1"
    assert core.apparatus_registry.get_by_role("main_view.kmg") is None
    assert core.apparatus_registry.testable_ids() == ["KOT_KM1", "KOT_Q1"]


def test_a_module_outside_the_composition_does_not_exist_at_all(tmp_path, start_core):
    core = start_core(_studio_project(tmp_path, modules=("analog_inputs",)))

    assert core.intrusion_manager is None
    assert core.process_protection_manager is None
    assert core.switching_counters is None
    assert [t.name for t in core.tag_manager.list_tags() if t.name.startswith(("Security.", "Process."))] == []
    result = core.set_feature_enabled("intrusion", True, actor="Engineer", level=AccessLevel.ENGINEER)
    assert result["success"] is False
    assert core.intrusion_manager is None


def test_logic_referring_to_signals_of_a_missing_module_is_reported_at_startup(tmp_path, start_core):
    path = _studio_project(tmp_path, modules=("analog_inputs",), with_zone=False)
    logic = tmp_path / "site.epwlogic.runtime.json"
    logic.write_text(json.dumps({
        "format": "EPW_RUNTIME_LOGIC", "schema_version": 4,
        "blocks": {"b1": {"type": "AND", "properties": {"input": "Security.Zone.Z1.State"}},
                   "b2": {"type": "NOT", "properties": {"input": "Process.PP1.Exceeded"}},
                   "b3": {"type": "GT", "properties": {"input": "AI1.AI.1"}}},
        "io_labels": {},
    }), encoding="utf-8")
    (tmp_path / "controller.local.json").write_text(json.dumps(
        {"format": "EPW_CONTROLLER_SETTINGS", "schema_version": 1, "logic_project": str(logic)}), encoding="utf-8")

    core = start_core(path)

    issues = {issue["id"]: issue for issue in core.startup_issues}
    assert set(issues) == {"COMPOSITION_INTRUSION_LOGIC", "COMPOSITION_PROTECTION_PROCESS_LOGIC"}
    intrusion = issues["COMPOSITION_INTRUSION_LOGIC"]
    assert intrusion["key"] == "startup.composition_logic"
    assert intrusion["params"]["module"] == "intrusion"
    assert intrusion["params"]["signals"] == "Security.Zone.Z1.State"
    assert str(logic) in intrusion["text"]
    assert "COMPOSITION_INTRUSION_LOGIC" in {alarm.id for alarm in core.alarm_manager.get_active_alarms()}

    from epw_os.gui.startup_issues import format_startup_issue
    from epw_os.i18n import set_language
    set_language("pl")
    try:
        text = format_startup_issue(intrusion)
    finally:
        set_language("en")
    assert "którego nie ma w składzie" in text and "Security.Zone.Z1.State" in text


def test_a_screen_file_is_checked_the_same_way():
    from epw_os.core.composition_check import find_signals_outside_composition
    from epw_os.core.feature_config import normalize_enabled_features
    import tempfile
    import os
    features = normalize_enabled_features({"analog_inputs": False})
    with tempfile.TemporaryDirectory() as directory:
        screen = os.path.join(directory, "hall.epwsyn")
        with open(screen, "w", encoding="utf-8") as f:
            json.dump({"format": "EPW_SYNOPTIC", "objects": [{"id": "o1", "tag": "AI2.AI.7"}, {"id": "o2", "tag": "DI1.DI.1"}]}, f)
        issues = find_signals_outside_composition(features, synoptic_file=screen)
    assert [(i.module, i.source_kind, i.signals) for i in issues] == [("analog_inputs", "screen", ["AI2.AI.7"])]


def test_structure_cannot_be_changed_from_the_panel(tmp_path, start_core):
    path = _studio_project(tmp_path)
    core = start_core(path)
    before = path.read_bytes()

    assert core.intrusion_manager.add_zone("New zone", 0, 0, level=AccessLevel.ENGINEER) is None
    assert core.intrusion_manager.update_zone("Z1", name="Renamed", level=AccessLevel.ENGINEER) is False
    assert core.intrusion_manager.update_line("L1", tag="DI1.DI.5", level=AccessLevel.ENGINEER) is False
    assert core.intrusion_manager.remove_line("L1", level=AccessLevel.ENGINEER) is False
    assert core.process_protection_manager.remove_protection("PP1", level=AccessLevel.ENGINEER) is False
    assert core.add_analog_point({"tag": "AI1.AI.9", "description": ""}) is False
    assert core.project_manager.set_tag_description("DI1.DI.1", "renamed") is False

    # A write that goes around the modules is refused by ProjectManager itself.
    core.project_manager.config["intrusion_zones"].append(
        {"id": "Z9", "name": "Sneaky", "exit_delay_seconds": 0.0, "entry_delay_seconds": 0.0})
    assert core.project_manager.save_project() is False
    assert path.read_bytes() == before
    assert [z["id"] for z in core.project_manager.get_intrusion_zones()] == ["Z1"]
    assert any("intrusion_zones[Z9] added" in d for d in _audit_details("PROJECT_STRUCTURE_CHANGE_REFUSED"))


# --- etap 4: settings go back into projekt.epw ---------------------------------------

def test_a_setting_changed_on_the_panel_raises_the_revision_says_panel_and_is_audited(tmp_path, start_core):
    path = _studio_project(tmp_path)
    core = start_core(path)
    assert pf.read_project(path).project.revision == 1

    assert core.intrusion_manager.update_zone("Z1", exit_delay_seconds=45.0, level=AccessLevel.ENGINEER)
    saved = pf.read_project(path).project
    assert (saved.revision, saved.modified_by, saved.zones[0].exit_delay_seconds) == (2, "panel", 45.0)

    assert core.process_protection_manager.update_protection("PP1", upper_threshold=90.0, level=AccessLevel.ENGINEER)
    saved = pf.read_project(path).project
    assert (saved.revision, saved.process_protections[0].upper_threshold) == (3, 90.0)
    assert saved.process_protections[0].name == "Boiler overheat"

    details = _audit_details("PROJECT_SETTING_CHANGED")
    assert "intrusion_zones[Z1].exit_delay_seconds: 0.0 -> 45.0 (projekt.epw revision 2)" in details
    assert "process_protections[PP1].upper_threshold: 95.0 -> 90.0 (projekt.epw revision 3)" in details
    assert pf.read_project(str(path) + ".bak").project.revision == 2


def test_analog_scaling_and_electrical_stage_settings_are_written_back_but_descriptions_are_not(tmp_path, start_core):
    path = _studio_project(tmp_path, with_zone=False)
    core = start_core(path)
    boiler = next(p for p in core.project_manager.get_analog_points() if p["tag"] == "AI1.AI.1")

    assert core.update_analog_point("AI1.AI.1", {**boiler, "eng_max": 150.0}) is None
    saved = pf.read_project(path).project
    assert (saved.revision, next(p for p in saved.points if p.address == "AI1.AI.1").eng_max) == (2, 150.0)

    before = path.read_bytes()
    assert core.update_analog_point("AI1.AI.1", {**boiler, "description": "Renamed on the panel"}) is False
    assert path.read_bytes() == before

    pm = core.project_manager
    pm.set_electrical_protection_stages([{"function_id": "50 Instantaneous Overcurrent", "stage_name": "Stage 1",
                                          "enabled": True, "setting": 85.0, "hysteresis": 5.0, "delay_ms": 100,
                                          "action": "Trip"}])
    assert pm.save_project() is True
    stage = pf.read_project(path).project.electrical_protection_stages[0]
    assert (stage.function_id, stage.setting, stage.delay_ms) == ("50 Instantaneous Overcurrent", 85.0, 100)
    assert pf.read_project(path).project.revision == 3


# --- etap 2: runtime_state.json --------------------------------------------------------

def test_arming_is_on_disk_before_the_call_returns(tmp_path, start_core):
    path = _studio_project(tmp_path)
    core = start_core(path)
    project_bytes = path.read_bytes()

    result = core.intrusion_manager.arm_zone("Z1", actor="Operator", level=AccessLevel.OPERATOR, force=True)
    assert result.success
    on_disk = json.loads((tmp_path / "runtime_state.json").read_text(encoding="utf-8"))
    assert on_disk["intrusion_state"]["armed_zones"] == ["Z1"]

    assert core.intrusion_manager.disarm_zone("Z1", actor="Operator", level=AccessLevel.OPERATOR)
    on_disk = json.loads((tmp_path / "runtime_state.json").read_text(encoding="utf-8"))
    assert on_disk["intrusion_state"]["armed_zones"] == []
    assert path.read_bytes() == project_bytes


def test_arming_and_bypass_survive_a_restart(tmp_path, start_core):
    path = _studio_project(tmp_path)
    first = start_core(path)
    assert first.intrusion_manager.arm_zone("Z1", actor="Operator", level=AccessLevel.OPERATOR, force=True).success
    assert first.intrusion_manager.bypass_line("L1", True, actor="Engineer", level=AccessLevel.ENGINEER)
    first.shutdown()

    second = start_core(path)
    assert second.intrusion_manager.get_zone_state("Z1") == "ARMED"
    assert second.intrusion_manager.is_line_bypassed("L1") is True
    assert second.startup_issues == []
    assert any("Ground floor" in d for d in _audit_details("INTRUSION_ZONE_ARM_RESTORED"))


def test_switching_counters_go_to_the_state_file_and_never_touch_projekt_epw(tmp_path, start_core):
    path = _studio_project(tmp_path, with_zone=False)
    core = start_core(path)
    before_bytes, before_mtime = path.read_bytes(), path.stat().st_mtime_ns

    for value in (False, True, False, True):
        core.tag_manager.update_tag("DI1.DI.1", value)
    core.switching_counters.flush_to_project()

    assert path.read_bytes() == before_bytes
    assert path.stat().st_mtime_ns == before_mtime
    assert not Path(str(path) + ".bak").exists()
    record = json.loads((tmp_path / "runtime_state.json").read_text(encoding="utf-8"))["switching_counters"]["DI1.DI.1"]
    assert (record["closes"], record["opens"]) == (2, 1)


def test_losing_the_state_file_is_harmless_but_a_lost_arming_state_is_reported(tmp_path, start_core):
    plain = start_core(_studio_project(tmp_path / "plain", with_zone=False))
    assert plain.startup_issues == []
    assert plain.switching_counters.get_snapshot("DI1.DI.1")["closes"] == 0

    guarded_dir = tmp_path / "guarded"
    path = _studio_project(guarded_dir)
    (guarded_dir / "runtime_state.json").write_text("{ this is not json", encoding="utf-8")
    guarded = start_core(path)
    assert [(i["id"], i["key"]) for i in guarded.startup_issues] == [("RUNTIME_STATE_LOST", "startup.state_damaged")]
    assert guarded.intrusion_manager.get_zone_state("Z1") == "DISARMED"
    assert "RUNTIME_STATE_LOST" in {alarm.id for alarm in guarded.alarm_manager.get_active_alarms()}
    assert (guarded_dir / "runtime_state.json.corrupt").read_text(encoding="utf-8") == "{ this is not json"


def test_the_last_screen_is_state_not_project(tmp_path):
    path = _studio_project(tmp_path, with_zone=False)
    pm = ProjectManager(str(path))
    pm.load_project()
    before = path.read_bytes()
    assert pm.set_last_screen("alarms") is True
    assert pm.set_intrusion_operation_state(["Z1"], []) is True
    # written at once, so nothing is left "unsaved" to ask about on exit
    assert pm.is_dirty() is False

    reloaded = ProjectManager(str(path))
    reloaded.load_project()
    assert reloaded.get_last_screen() == "alarms"
    assert path.read_bytes() == before


# --- etap 1 (runtime side): a damaged project ------------------------------------------

def test_a_damaged_projekt_epw_does_not_bring_runtime_down_and_is_never_overwritten(tmp_path, start_core):
    path = tmp_path / "projekt.epw"
    path.write_bytes(gzip.compress(json.dumps({
        "format": "EPW_PROJECT_FILE", "schema_version": 1, "project": {"name": "Broken"},
        "cards": [{"id": "DI1", "kind": "DI", "channels": 8}],
    }).encode("utf-8")))
    before = path.read_bytes()

    core = start_core(path)

    assert core.is_running is True
    assert [i["id"] for i in core.startup_issues] == ["PROJECT_NOT_LOADED"]
    issue = core.startup_issues[0]
    assert (issue["key"], issue["detail_key"], issue["detail_params"]["field"]) == (
        "startup.project_refused", "project_format.missing_field", "cards[0].model")
    assert _names(core, "DI") == []
    core.project_manager.config["process_protections"] = [{"id": "PP9", "name": "x"}]
    assert core.project_manager.save_project() is False
    assert path.read_bytes() == before


def test_a_missing_projekt_epw_starts_an_empty_controller_and_says_so(tmp_path, start_core):
    core = start_core(tmp_path / "projekt.epw")
    assert core.is_running is True
    assert [(i["id"], i["key"]) for i in core.startup_issues] == [("PROJECT_NOT_LOADED", "startup.project_missing")]
    assert not (tmp_path / "projekt.epw").exists()


# --- etap 5: migration, REST, installing a project ---------------------------------------

def _migration():
    path = Path(__file__).resolve().parents[2] / "tools" / "migrate_project_json.py"
    spec = importlib.util.spec_from_file_location("migrate_project_json", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _legacy_project(directory: Path) -> Path:
    from epw_os.core.analog_scaling import SIGNAL_TYPE_READY
    legacy = {
        "format": "EPW_OS_PROJECT", "schema_version": 1, "project_id": "OLD_SITE", "language": "pl",
        "synoptic_project": None, "logic_project": None, "tag_descriptions": {}, "output_descriptions": {},
        "analog_points": [{"tag": f"AI{n}", "description": f"Channel {n}", "technical_note": "",
                           "signal_type": SIGNAL_TYPE_READY if n != 5 else "4-20mA", "raw_min": 4.0, "raw_max": 20.0,
                           "eng_min": 0.0, "eng_max": 10.0 * n, "unit": "bar", "decimals": 2}
                          for n in range(1, 17)],
        "switching_counters": {
            "DI1": {"closes": 3, "opens": 2, "closed_seconds": 12.5, "closed_since": None, "first_transition": 1.0,
                    "last_transition": 2.0, "warning_threshold": 100},
            "DI40": {"closes": 1, "opens": 1, "closed_seconds": 1.0, "closed_since": None, "first_transition": 1.0,
                     "last_transition": 2.0, "warning_threshold": None},
        },
        "intrusion_zones": [{"id": "Z1", "name": "Old zone", "exit_delay_seconds": 5, "entry_delay_seconds": 5}],
    }
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / "project.json"
    source.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")
    return source


def test_migration_into_a_studio_project_moves_16_analog_points_and_the_counters(tmp_path):
    source = _legacy_project(tmp_path)
    original = source.read_bytes()
    target = pf.new_project("Studio site")
    target.cards = [pf.Card(id="DI1", model="ELA01", kind="DI", channels=32)]
    target.points = [pf.Point(address=f"DI1.DI.{n}") for n in range(1, 33)]
    pf.save_project(target, tmp_path / "projekt.epw")

    report = _migration().migrate(source, tmp_path / "projekt.epw", flat_di_card="DI1")

    project = pf.read_project(tmp_path / "projekt.epw").project
    analog = [p for p in project.points if p.address.startswith("AI1.AI.")]
    assert [p.address for p in analog] == [f"AI1.AI.{n}" for n in range(1, 17)]
    assert (analog[4].signal_type, analog[4].eng_max, analog[4].unit, analog[4].decimals) == ("4-20mA", 50.0, "bar", 2)
    assert [c.id for c in project.cards] == ["DI1", "AI1"]
    assert (project.revision, project.modified_by) == (2, "panel")

    state = json.loads((tmp_path / "runtime_state.json").read_text(encoding="utf-8"))
    assert state["switching_counters"]["DI1.DI.1"]["closes"] == 3
    assert state["switching_counters"]["DI1.DI.1"]["warning_threshold"] == 100
    assert report["counters_not_migrated"] == ["DI40"]  # the card has 32 channels - no DI1.DI.40
    assert report["left_to_studio"] == ["intrusion_zones"]
    assert json.loads((tmp_path / "controller.local.json").read_text(encoding="utf-8"))["language"] == "pl"
    assert source.read_bytes() == original


def test_a_migrated_old_project_runs_with_its_analog_points_and_the_old_file_stays(tmp_path, start_core):
    source = _legacy_project(tmp_path)
    original = source.read_bytes()

    report = _migration().migrate(source, tmp_path / "projekt.epw")

    assert report["target_created"] is True
    assert sorted(report["counters_not_migrated"]) == ["DI1", "DI40"]  # no DI card to put the flat names on
    core = start_core(tmp_path / "projekt.epw")
    assert _names(core, "AI") == sorted(f"AI1.AI.{n}" for n in range(1, 17))
    assert core.enabled_features["intrusion"] is True  # an old project had every module on
    assert core.project_manager.get_language() == "pl"
    assert source.read_bytes() == original


def test_rest_reports_which_project_and_revision_the_controller_runs(tmp_path, start_core):
    from fastapi.testclient import TestClient
    from epw_os.backend.api import app

    path = _studio_project(tmp_path)
    core = start_core(path)
    app.state.core = core
    client = TestClient(app)

    body = client.get("/api/v1/project").json()
    assert (body["source"], body["loaded"], body["name"], body["revision"], body["modified_by"]) == (
        "projekt.epw", True, "Test site", 1, "studio")
    assert body["counts"] == {"cards": 3, "points": 14, "devices": 3, "zones": 1, "lines": 1,
                              "process_protections": 1, "electrical_protection_stages": 0}

    core.intrusion_manager.update_zone("Z1", entry_delay_seconds=20.0, level=AccessLevel.ENGINEER)
    body = client.get("/api/v1/project").json()
    assert (body["revision"], body["modified_by"]) == (2, "panel")


def test_installing_a_project_file_checks_it_first_and_keeps_the_previous_one(tmp_path):
    active = _studio_project(tmp_path / "controller", with_zone=False, name="Running site")
    pm = ProjectManager(str(active))
    pm.load_project()

    junk = tmp_path / "junk.epw"
    junk.write_bytes(b"not a project")
    ok, error = pm.install_project_file(str(junk))
    assert ok is False and error["key"] == "project_format.unreadable"
    assert pf.read_project(active).project.metadata.name == "Running site"

    replacement = _studio_project(tmp_path / "laptop", with_zone=False, name="New design")
    ok, error = pm.install_project_file(str(replacement))
    assert (ok, error) == (True, None)
    assert pf.read_project(active).project.metadata.name == "New design"
    assert pf.read_project(str(active) + ".bak").project.metadata.name == "Running site"
