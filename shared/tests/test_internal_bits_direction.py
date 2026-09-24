"""Internal bits IN/OUT (owner's decisions 2026-09-22) - the shared
contract every program reads: the direction and writer fields of a
registry entry, their defaults, and the apparatus's permission bit in
projekt.epw."""
import gzip
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from shared import project_format as pf  # noqa: E402
from shared.logic import internal_bits as ib  # noqa: E402


def test_an_entry_from_before_this_existed_is_an_out_bit_nobody_outside_writes():
    old = {"name": "DRUT", "type": "BOOL", "retentive": False}
    assert ib.direction_of(old) == "OUT" and ib.is_input_bit(old) is False
    assert ib.panel_level_of(old) == "" and ib.remote_writable(old) is False
    normalized = ib.normalize_entry(old)
    assert normalized["direction"] == "OUT" and normalized["panel_level"] == "" and normalized["remote_write"] is False
    assert old == {"name": "DRUT", "type": "BOOL", "retentive": False}, "normalize returns a copy"


def test_an_in_bit_lets_the_panel_write_at_operator_by_default_and_remote_only_when_said():
    entry = {"name": "START", "type": "BOOL", "direction": "IN"}
    assert ib.is_input_bit(entry) and ib.panel_level_of(entry) == "Operator" and ib.remote_writable(entry) is False
    assert ib.panel_level_of({**entry, "panel_level": "Engineer"}) == "Engineer"
    assert ib.panel_level_of({**entry, "panel_level": ""}) == "", "the panel may be switched off for a bit"
    assert ib.remote_writable({**entry, "remote_write": True}) is True
    # remote never applies to an OUT bit, whatever the flag says
    assert ib.remote_writable({"name": "X", "type": "BOOL", "direction": "OUT", "remote_write": True}) is False
    assert ib.direction_of({"name": "X", "direction": "in"}) == "IN"


def test_a_malformed_direction_or_level_is_a_registry_error():
    entries = [{"name": "A", "type": "BOOL", "direction": "SIDEWAYS"},
               {"name": "B", "type": "BOOL", "direction": "IN", "panel_level": "Boss"}]
    errors = ib.validate_internal_bits_registry(entries)
    assert any("'A'" in e and "SIDEWAYS" in e for e in errors)
    assert any("'B'" in e and "Boss" in e for e in errors)
    assert ib.validate_internal_bits_registry([{"name": "C", "type": "BOOL", "direction": "IN", "panel_level": ""}]) == []


def test_the_apparatus_permission_bit_travels_through_projekt_epw_and_an_old_file_has_none(tmp_path):
    project = pf.new_project("Zezwolenie")
    project.devices = [pf.Device(id="KOT_KMG1", behavior="SWITCHED", kind="contactor", feedback=["ELA1.DI.1"],
                                 command=["ADA1.DO.1"], permission_bit="M.KMG1_ZEZW"),
                       pf.Device(id="KOT_Q1", behavior="SWITCHED", feedback=[], command=["ADA1.DO.2"])]
    path = tmp_path / "projekt.epw"
    pf.save_project(project, path)
    with gzip.open(path, "rb") as f:
        data = json.loads(f.read().decode("utf-8"))
    assert data["devices"][0]["permissionBit"] == "M.KMG1_ZEZW" and data["devices"][1]["permissionBit"] == ""
    reloaded = {d.id: d for d in pf.load_project(path).devices}
    assert reloaded["KOT_KMG1"].permission_bit == "M.KMG1_ZEZW" and reloaded["KOT_Q1"].permission_bit == ""
    for device in data["devices"]:
        device.pop("permissionBit")
    with gzip.open(path, "wb") as f:
        f.write(json.dumps(data).encode("utf-8"))
    assert all(d.permission_bit == "" for d in pf.load_project(path).devices)


def test_the_id_does_not_change_with_the_direction():
    entry = {"name": "START", "type": "BOOL", "retentive": False}
    assert ib.internal_bit_id({**entry, "direction": "IN"}) == ib.internal_bit_id({**entry, "direction": "OUT"}) == "M.START"
    assert ib.internal_bit_id({**entry, "retentive": True, "direction": "IN"}) == "MR.START"
