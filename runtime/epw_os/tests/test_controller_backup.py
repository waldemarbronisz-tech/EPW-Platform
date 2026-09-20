"""The way back from a dead card.

A project is safe - it lives in Studio, in version control, and can be
sent over REST. What belongs to the CONTROLLER existed only on its own
SD card: switching counters that have been running for years, which
zones were armed when the power went, the alarm memory, retentive logic
bits, the audit log.

The two things worth proving here are opposites. That a backup really
carries everything that cannot be recovered any other way - and that it
carries NO secret, ever, because a bundle is a file that leaves the
site and a four-digit PIN behind a hash is not a secret.
"""
import base64
import gzip
import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core import controller_backup as backup
from epw_os.core import project_format as pf


class _ProjectManager:
    """Only what the backup reads: where the files are, the header, and
    the project's own bytes."""

    def __init__(self, directory):
        self.project_file = str(Path(directory) / "projekt.epw")

    def get_project_header(self):
        return {"name": "Kotłownia", "revision": 7}

    def project_file_bytes(self):
        path = Path(self.project_file)
        return path.read_bytes() if path.exists() else None

    def get_mqtt_config(self):
        return {"host": "homeassistant.local"}


class _AccessManager:
    def __init__(self, users):
        self._users = users

    def get_users(self):
        return list(self._users)


USERS = [
    {"id": "U1", "name": "Kowalski", "level": "Operator", "has_pin": True, "has_remote_token": True},
    {"id": "U2", "name": "Nowak", "level": "Engineer", "has_pin": True, "has_remote_token": False},
    {"id": "U3", "name": "Nikt", "level": "User", "has_pin": False, "has_remote_token": False},
]

STATE = {
    "switching_counters": {"ADA1.DO.1": {"closes": 4211, "opens": 4210, "closed_seconds": 91234.5}},
    "intrusion_state": {
        "armed_zones": ["Z1"],
        "arm_modes": {"Z1": "NIGHT"},
        "bypassed_lines": ["L4"],
        "alarm_memory": {"Z1": {"active": True, "first_cause_line_id": "L2"}},
    },
    "logic_retentive": {"MR.PumpHours": 1820.0},
    "last_screen": "Hala",
}

LOCAL = {
    "language": "pl",
    "api": {"host": "192.168.1.50", "port": 8000},
    "io_driver": {"driver": "MODBUS"},
    "historian_retention": {"max_days": 90},
}


@pytest.fixture
def controller(tmp_path):
    """A controller's directory as it really looks, secrets included -
    the backup has to walk past them."""
    project = pf.new_project("Kotłownia", author="t")
    pf.save_project(project, tmp_path / "projekt.epw")
    (tmp_path / "runtime_state.json").write_text(json.dumps(STATE), encoding="utf-8")
    (tmp_path / "controller.local.json").write_text(json.dumps(LOCAL), encoding="utf-8")
    for name, content in (
        ("access.local.json", {"pins": {"Engineer": "5e884898da280471"}, "users": {"U1": {"pin": "abc"}}}),
        ("api_tokens.local.json", {"token_hashes": {"Engineer": "deadbeef"}}),
        ("mqtt.local.json", {"password": "hunter2"}),
    ):
        (tmp_path / name).write_text(json.dumps(content), encoding="utf-8")
    return tmp_path, _ProjectManager(tmp_path), _AccessManager(USERS)


class _Secrets:
    """Stands in for ApiAuth / MqttManager: the backup asks each manager
    where ITS file is rather than guessing that the secrets sit next to
    projekt.epw - they do not, they live in epw_os/config/."""

    def __init__(self, path):
        self.config_path = self.secret_path = str(path)


def _bundle(controller, **kwargs):
    directory, pm, am = controller
    kwargs.setdefault("api_auth", _Secrets(directory / "api_tokens.local.json"))
    kwargs.setdefault("mqtt_manager", _Secrets(directory / "mqtt.local.json"))
    return backup.build_backup(pm, am, actor="Panel:Engineer", **kwargs)


# --- what a backup carries ---------------------------------------------------

def test_a_backup_carries_what_cannot_be_recovered_any_other_way(controller):
    payload = backup.read_backup(_bundle(controller, include_audit=False))

    counters = payload["state"]["switching_counters"]["ADA1.DO.1"]
    assert counters["closes"] == 4211, "four years of switching counts"
    assert payload["state"]["intrusion_state"]["armed_zones"] == ["Z1"]
    assert payload["state"]["intrusion_state"]["arm_modes"] == {"Z1": "NIGHT"}
    assert payload["state"]["intrusion_state"]["alarm_memory"]["Z1"]["active"] is True
    assert payload["state"]["logic_retentive"]["MR.PumpHours"] == 1820.0


def test_a_backup_is_self_sufficient_and_carries_the_project_itself(controller):
    _dir, pm, _am = controller
    payload = backup.read_backup(_bundle(controller, include_audit=False))

    assert payload["project"], "a bundle with no project cannot rebuild a controller"
    assert base64.b64decode(payload["project"]) == Path(pm.project_file).read_bytes()
    assert payload["meta"]["project_revision"] == 7
    assert payload["meta"]["created_by"] == "Panel:Engineer"


def test_local_settings_travel_so_the_replacement_speaks_the_same_language(controller):
    payload = backup.read_backup(_bundle(controller, include_audit=False))
    assert payload["local"]["language"] == "pl"
    assert payload["local"]["historian_retention"]["max_days"] == 90


# --- what it must never carry ------------------------------------------------

def test_no_secret_is_anywhere_in_a_bundle(controller):
    """The rule the whole design turns on. Checked against the raw
    bytes, not the parsed structure: a secret that leaked into some
    field nobody thought about would still be in the file."""
    raw = gzip.decompress(_bundle(controller)).decode("utf-8")

    for secret in ("5e884898da280471", "deadbeef", "hunter2", '"pin"'):
        assert secret not in raw, f"a secret reached the bundle: {secret}"
    for name in backup.SECRET_FILES:
        assert name not in raw or "never carries secrets" in raw


def test_the_bundle_says_who_had_a_secret_without_saying_what_it_was(controller):
    """What turns a restore into a checklist instead of a guess."""
    payload = backup.read_backup(_bundle(controller, include_audit=False))
    users = {user["name"]: user for user in payload["secrets"]["users"]}

    assert users["Kowalski"]["had_code"] is True
    assert users["Kowalski"]["had_remote_token"] is True
    assert users["Nowak"]["had_remote_token"] is False
    assert users["Nikt"]["had_code"] is False
    assert payload["secrets"]["api_tokens_set"] is True
    assert payload["secrets"]["mqtt_password_set"] is True


def test_the_checklist_names_exactly_what_a_person_has_to_redo(controller):
    payload = backup.read_backup(_bundle(controller, include_audit=False))

    checklist = backup.reissue_checklist(payload)
    kinds = [item["kind"] for item in checklist]
    assert "level_pins" in kinds and "api_tokens" in kinds and "mqtt_password" in kinds
    # The level PINs are ALWAYS on the list: a controller generates its
    # own random ones on first start, so a replacement has PINs nobody
    # knows rather than no PINs.
    assert next(i for i in checklist if i["kind"] == "level_pins")["detail"] == "Operator, Engineer"
    people = {item["detail"]: item for item in checklist if item["kind"] == "user"}
    assert set(people) == {"Kowalski", "Nowak"}, "only the people who actually had something"
    assert people["Kowalski"]["needs"] == ["code", "token"]
    assert people["Nowak"]["needs"] == ["code"]


# --- a bundle that cannot be trusted is refused, not half-applied -------------

def test_a_file_that_is_not_a_backup_is_refused_with_a_reason():
    with pytest.raises(backup.BackupError) as excinfo:
        backup.read_backup(b"not a gzip file at all")
    assert "readable" in str(excinfo.value)


def test_someone_elses_gzip_is_refused():
    with pytest.raises(backup.BackupError) as excinfo:
        backup.read_backup(gzip.compress(json.dumps({"format": "SOMETHING_ELSE"}).encode()))
    assert "not an EPW controller backup" in str(excinfo.value)


def test_a_bundle_edited_after_it_was_written_is_refused(controller):
    """The case this exists for: somebody opens the file, changes an
    arming state or a counter, and sends it back."""
    payload = backup.read_backup(_bundle(controller, include_audit=False))
    payload["state"]["switching_counters"]["ADA1.DO.1"]["closes"] = 0
    tampered = gzip.compress(json.dumps(payload).encode("utf-8"))

    with pytest.raises(backup.BackupError) as excinfo:
        backup.read_backup(tampered)
    assert "altered or truncated" in str(excinfo.value)


def test_a_bundle_from_a_different_schema_is_refused(controller):
    payload = backup.read_backup(_bundle(controller, include_audit=False))
    payload["schema_version"] = 99
    payload["checksum"] = backup._checksum(payload)

    with pytest.raises(backup.BackupError) as excinfo:
        backup.read_backup(gzip.compress(json.dumps(payload).encode("utf-8")))
    assert "different version" in str(excinfo.value)


# --- looking before applying --------------------------------------------------

def test_a_bundle_can_be_described_before_it_is_applied(controller):
    """A restore overwrites a running controller, so it has to be
    possible to look first."""
    summary = backup.describe_backup(backup.read_backup(_bundle(controller, include_audit=False)))

    assert summary["project_name"] == "Kotłownia"
    assert summary["project_revision"] == 7
    assert summary["counters"] == 1
    assert summary["armed_zones"] == ["Z1"]
    assert sorted(summary["users_to_reissue"]) == ["Kowalski", "Nowak"]
    assert summary["mqtt_password_to_reenter"] is True


# --- applying -----------------------------------------------------------------

def test_a_restore_puts_the_state_and_the_project_back(controller, tmp_path):
    payload = backup.read_backup(_bundle(controller, include_audit=False))
    target = tmp_path / "replacement"
    target.mkdir()
    pm = _ProjectManager(target)

    report = backup.apply_backup(payload, pm, actor="Panel:Engineer")

    assert "runtime_state.json" in report["written"]
    assert "projekt.epw" in report["written"]
    state = json.loads((target / "runtime_state.json").read_text(encoding="utf-8"))
    assert state["switching_counters"]["ADA1.DO.1"]["closes"] == 4211
    assert state["intrusion_state"]["armed_zones"] == ["Z1"]
    assert pf.read_project(target / "projekt.epw").project.metadata.name == "Kotłownia"


def test_the_replacements_own_hardware_settings_are_not_overwritten(controller, tmp_path):
    """A replacement controller sits on a different network and may have
    a different bus. Those settings describe the hardware it is running
    on, not the installation that was backed up."""
    payload = backup.read_backup(_bundle(controller, include_audit=False))
    target = tmp_path / "replacement"
    target.mkdir()
    (target / "controller.local.json").write_text(json.dumps({
        "api": {"host": "10.0.0.9", "port": 8000},
        "io_driver": {"driver": "SIM"},
    }), encoding="utf-8")

    report = backup.apply_backup(payload, _ProjectManager(target))

    local = json.loads((target / "controller.local.json").read_text(encoding="utf-8"))
    assert local["api"]["host"] == "10.0.0.9", "the replacement's own address stayed"
    assert local["io_driver"]["driver"] == "SIM"
    assert local["language"] == "pl", "but the installation's settings came back"
    assert any("io_driver" in item["what"] for item in report["skipped"])


def test_a_restore_keeps_the_previous_project_as_a_backup(controller, tmp_path):
    payload = backup.read_backup(_bundle(controller, include_audit=False))
    target = tmp_path / "replacement"
    target.mkdir()
    previous = pf.new_project("Something else", author="t")
    pf.save_project(previous, target / "projekt.epw")

    backup.apply_backup(payload, _ProjectManager(target))

    assert (target / "projekt.epw.bak").exists()
    assert pf.read_project(target / "projekt.epw.bak").project.metadata.name == "Something else"


def test_a_restore_says_outright_what_it_could_not_do_for_you(controller, tmp_path):
    payload = backup.read_backup(_bundle(controller, include_audit=False))
    target = tmp_path / "replacement"
    target.mkdir()

    report = backup.apply_backup(payload, _ProjectManager(target))

    skipped = {item["what"] for item in report["skipped"]}
    assert backup.SECRET_FILES[0] in skipped
    assert all(any(name == item["what"] for item in report["skipped"]) for name in backup.SECRET_FILES)
    assert report["checklist"], "and hands over the list of what to re-issue"


def test_a_controller_with_nothing_yet_still_produces_a_valid_backup(tmp_path):
    """A brand-new controller has no state file and no secrets. The
    backup has to be a backup of that, not a failure."""
    project = pf.new_project("Brand new", author="t")
    pf.save_project(project, tmp_path / "projekt.epw")

    payload = backup.read_backup(backup.build_backup(_ProjectManager(tmp_path), None,
                                                      include_audit=False))

    assert payload["state"] == {}
    assert payload["secrets"]["users"] == []
    assert payload["secrets"]["api_tokens_set"] is False
    assert payload["secrets"]["mqtt_password_set"] is False
    # Only the access levels, whose PINs a replacement always generates
    # for itself - there is nobody and nothing else to re-issue.
    assert [item["kind"] for item in backup.reissue_checklist(payload)] == ["level_pins"]
