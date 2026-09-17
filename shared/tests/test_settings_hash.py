"""SPEC "Wersjonowanie": `settings_hash` - a checksum of the settings
alone (what the panel may change), written into every saved file and
compared by Studio before sending a project to a controller. The
snapshot behind it lines up field by field so a mismatch can be shown
("tu 25 A, tam 40 A"), and the field lists agree with runtime's own
setting/structure split in project_epw.py.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from shared import project_format as pf  # noqa: E402


def _project():
    project = pf.new_project("Site", author="t")
    project.locations = [pf.Location("KOT", "Kotlownia")]
    project.cards = [pf.Card("DI1", "ELA01", channel_kinds={"DI": 4, "AI": 2}, location="KOT")]
    project.points = [pf.Point(address="DI1.DI.1"), pf.Point(address="DI1.DI.2"),
                      pf.Point(address="DI1.AI.1", signal_type="4-20mA", raw_min=4.0, raw_max=20.0, eng_min=0.0,
                               eng_max=120.0, unit="°C", decimals=1)]
    project.zones = [pf.Zone("Z1", "Ground floor", exit_delay_seconds=10.0, entry_delay_seconds=30.0)]
    project.lines = [pf.Line("L1", "Door", "Z1", tag="DI1.DI.1")]
    project.process_protections = [pf.ProcessProtection("PP1", "Boiler", analog_tag="DI1.AI.1",
                                                        upper_threshold=95.0, lower_threshold=0.0)]
    project.electrical_protection_stages = [pf.ElectricalProtectionStage(
        function_id="50 Instantaneous Overcurrent", stage_name="Stage 1", enabled=True, setting=25.0,
        hysteresis=3.0, delay_ms=150, action="Trip")]
    return project


def test_snapshot_lists_every_setting_by_its_own_identity():
    snap = pf.settings_snapshot(_project())
    assert snap["zones/Z1/exit_delay_seconds"] == 10.0
    assert snap["lines/L1/min_violation_seconds"] is not None or "lines/L1/min_violation_seconds" in snap
    assert snap["process_protections/PP1/upper_threshold"] == 95.0
    assert snap["electrical_protection_stages/50 Instantaneous Overcurrent / Stage 1/setting"] == 25.0
    assert snap["analog_points/DI1.AI.1/eng_max"] == 120.0
    assert "analog_points/DI1.DI.1/eng_max" not in snap          # a DI has no analog scaling
    assert not any(k.startswith("power_supervision/") for k in snap)  # not configured -> absent
    assert list(snap) == sorted(snap)                            # stable order


def test_hash_changes_only_when_a_setting_changes():
    a, b = _project(), _project()
    assert pf.settings_hash(a) == pf.settings_hash(b)
    b.metadata.description = "structure/metadata is not a setting"
    b.points.append(pf.Point(address="DI1.DI.3"))
    assert pf.settings_hash(a) == pf.settings_hash(b)
    b.electrical_protection_stages[0].setting = 40.0
    assert pf.settings_hash(a) != pf.settings_hash(b)
    assert len(pf.settings_hash(a)) == 64


def test_diff_names_the_path_and_both_values():
    a, b = _project(), _project()
    b.electrical_protection_stages[0].setting = 40.0
    b.zones[0].entry_delay_seconds = 45.0
    diff = pf.settings_diff(pf.settings_snapshot(a), pf.settings_snapshot(b))
    assert diff == [("electrical_protection_stages/50 Instantaneous Overcurrent / Stage 1/setting", 25.0, 40.0),
                    ("zones/Z1/entry_delay_seconds", 30.0, 45.0)]
    b.zones.append(pf.Zone("Z2", "Attic", exit_delay_seconds=1.0, entry_delay_seconds=2.0))
    diff = pf.settings_diff(pf.settings_snapshot(a), pf.settings_snapshot(b))
    assert ("zones/Z2/exit_delay_seconds", None, 1.0) in diff
    assert pf.settings_diff({}, {}) == []


def test_the_saved_file_carries_the_hash_and_reads_back(tmp_path):
    project = _project()
    path = tmp_path / "projekt.epw"
    pf.save_project(project, path)
    import gzip
    import json
    with gzip.open(path, "rt", encoding="utf-8") as f:
        data = json.load(f)
    assert data["settings_hash"] == pf.settings_hash(project)
    result = pf.read_project(path)
    assert result.ok and result.warnings == []
    assert pf.settings_hash(result.project) == data["settings_hash"]


def test_setting_fields_agree_with_runtimes_own_split():
    sys.path.insert(0, str(REPO / "runtime"))
    from epw_os.core import project_epw
    assert pf.SETTING_FIELDS["zones"] == project_epw.ZONE_SETTINGS
    assert pf.SETTING_FIELDS["lines"] == project_epw.LINE_SETTINGS
    assert pf.SETTING_FIELDS["process_protections"] == project_epw.PROCESS_SETTINGS
    assert pf.SETTING_FIELDS["electrical_protection_stages"] == project_epw.ELECTRICAL_SETTINGS
    assert pf.SETTING_FIELDS["analog_points"] == project_epw.ANALOG_SETTINGS
    assert pf.SETTING_FIELDS["power_supervision"] == project_epw.POWER_SUPERVISION_KEYS
