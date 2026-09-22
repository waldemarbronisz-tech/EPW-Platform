"""Signal register etap 4 - point roles (shared/logic/point_roles.py):
the roles are the catalogue's own PWR/UPS/PROT entries, the contact
type gives the bit its sense, and a Point carries both through
projekt.epw."""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from shared import project_format as pf  # noqa: E402
from shared.logic import point_roles, system_signals  # noqa: E402


def test_every_role_is_a_catalogue_signal_of_pwr_ups_or_prot_and_nothing_is_invented():
    catalogue = {s["id"]: s for s in system_signals.raw_signals()}
    ids = point_roles.role_ids()
    assert ids and len(ids) == len(set(ids))
    for role in point_roles.roles():
        assert role["id"] in catalogue, role
        assert role["category"] in ("PWR", "UPS", "PROT") and role["id"].startswith(role["category"] + ".")
        assert role["description"] == catalogue[role["id"]]["description"]
        assert catalogue[role["id"]]["source"] == "runtime"
    # the register's UPS group, in full, and the contacts an external relay offers
    assert {"UPS.ONLINE", "UPS.ON_BATTERY", "UPS.BYPASS", "UPS.LOW_BATTERY", "UPS.BATTERY_FAULT", "UPS.OVERLOAD",
            "UPS.FAULT", "UPS.MAINS_PRESENT"} <= set(ids)
    assert {"PWR.MAINS_OK", "PWR.POWER_24V_OK", "PROT.ANY_TRIP", "PROT.FAIL", "PROT.UNDERVOLTAGE"} <= set(ids)


def test_what_a_contact_cannot_carry_is_not_a_role():
    ids = set(point_roles.role_ids())
    assert not any("<" in i for i in ids), "a per-stage pattern is ADA01's, not a contact's"
    assert "PWR.MAINS_LOST" not in ids and "PWR.POWER_24V_FAULT" not in ids   # derived from the OK bits
    assert "PROT.SETTINGS_MISMATCH" not in ids and "PROT.TEST_OK" not in ids
    assert "PROT.UV_STAGE1.TRIP" not in ids
    assert point_roles.is_role("PWR.MAINS_OK") and not point_roles.is_role("PWR.MAINS_LOST")
    assert not point_roles.is_role("") and not point_roles.is_role(None)


def test_polarity_no_equals_the_input_nc_negates_it():
    assert point_roles.bit_from_contact("NO", True) is True and point_roles.bit_from_contact("NO", False) is False
    assert point_roles.bit_from_contact("NC", True) is False and point_roles.bit_from_contact("NC", False) is True
    # the register's own rule: "mains OK" on an NC relay contact reads TRUE while the input is open
    assert point_roles.bit_from_contact("NC", 0) is True
    assert point_roles.bit_from_contact("NO", 1) is True


def test_two_contacts_on_one_role_combine_by_the_healthy_rule():
    assert point_roles.combine("PWR.MAINS_OK", [True, False]) is False      # healthy needs every contact
    assert point_roles.combine("PWR.MAINS_OK", [True, True]) is True
    assert point_roles.combine("UPS.ON_BATTERY", [False, True]) is True     # an event needs any contact
    assert point_roles.combine("PROT.ANY_TRIP", [False, False]) is False
    for role in point_roles.HEALTHY_TRUE:
        assert role.endswith(("_OK", "ONLINE", "PRESENT", "AVAILABLE", "READY", "ACTIVE")), role
    assert point_roles.combine("UPS.FAULT", []) is True and point_roles.combine("UPS.ONLINE", []) is False


def test_the_safe_value_is_the_catalogues_and_the_device_source_names_the_other_block():
    assert point_roles.safe_value("UPS.FAULT") is True
    assert point_roles.safe_value("UPS.ONLINE") is False and point_roles.safe_value("PWR.MAINS_OK") is False
    assert point_roles.safe_value("PWR.MAINS_LOST") is True and point_roles.safe_value("PROT.FAIL") is True
    assert point_roles.device_source_for("PWR.L2_OK") == "EPM"
    assert point_roles.device_source_for("PROT.ANY_TRIP") == "ADA"
    assert point_roles.device_source_for("UPS.ONLINE") is None


def test_a_point_carries_its_role_and_contact_through_the_file_and_an_old_file_has_none(tmp_path):
    project = pf.new_project("Role")
    project.cards = [pf.Card(id="ELA1", model="ELA01", channel_kinds={"DI": 2})]
    project.points = [pf.Point(address="ELA1.DI.1", role="PWR.MAINS_OK", contact="NC"),
                      pf.Point(address="ELA1.DI.2")]
    path = tmp_path / "projekt.epw"
    pf.save_project(project, path)
    import gzip
    with gzip.open(path, "rb") as f:                 # projekt.epw is gzip + JSON
        text = f.read().decode("utf-8")
    assert '"role": "PWR.MAINS_OK"' in text and '"contact": "NC"' in text
    reloaded = pf.load_project(path)
    first, second = sorted(reloaded.points, key=lambda p: p.address)
    assert (first.role, first.contact) == ("PWR.MAINS_OK", "NC")
    assert (second.role, second.contact) == (None, "NO")
    # a file written before etap 4 has no such keys: no role, NO contact
    import json
    data = json.loads(text)
    for point in data["points"]:
        point.pop("role", None)
        point.pop("contact", None)
    with gzip.open(path, "wb") as f:
        f.write(json.dumps(data).encode("utf-8"))
    old = pf.load_project(path)
    assert all(p.role is None and p.contact == "NO" for p in old.points)
