"""Owner's instruction: "alarmówka ma mieć możliwość konfigurowania takich
rzeczy, alarmy nocne alarmy częściowe stopnie dostępu itp czyli np tylko
jakiś jeden użytkownik może rozbroić daną strefę".

Two things, both configured in the project and enforced in the runtime:

  * NIGHT arming ("dozór nocny / częściowy") - a zone armed at night is
    watched only by the lines flagged `active_at_night`, so somebody can
    move about inside a building whose perimeter is armed. 24-hour lines
    and line faults are unaffected, as on any real panel.
  * NAMED USERS - a person, the level their own code grants, and the
    zones they may operate. The three access LEVELS could never answer
    "only Kowalski may disarm the warehouse"; two operators are the same
    Operator to them.
"""
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core.access_manager import AccessLevel, AccessManager
from epw_os.core.events import EventBus
from epw_os.core.intrusion_manager import ArmMode, IntrusionManager, LineType, ZoneState
from epw_os.core.tag_manager import TagManager, TagType


class FakeProjectManager:
    """Only what IntrusionManager reads - the same shape the other
    intrusion tests use, plus the two new registries."""

    def __init__(self, zones=None, lines=None, users=None):
        self.zones = zones or []
        self.lines = lines or []
        self.users = users or []
        self.armed = []
        self.bypassed = []
        self.arm_modes = {}

    def get_intrusion_zones(self): return list(self.zones)
    def get_intrusion_lines(self): return list(self.lines)
    def get_intrusion_users(self): return list(self.users)
    def set_intrusion_zones(self, zones): self.zones = list(zones)
    def set_intrusion_lines(self, lines): self.lines = list(lines)
    def get_intrusion_line_supervision(self): return {}
    def get_intrusion_power_supervision(self): return {}
    def get_intrusion_alarm_memory(self): return {}
    def get_intrusion_armed_zones(self): return list(self.armed)
    def get_intrusion_arm_modes(self): return dict(self.arm_modes)
    def get_intrusion_bypassed_lines(self): return list(self.bypassed)
    def set_intrusion_operation_state(self, armed, bypassed, arm_modes=None):
        self.armed, self.bypassed = list(armed), list(bypassed)
        if arm_modes is not None:
            self.arm_modes = dict(arm_modes)
        return True
    def save_project(self): return True
    def structure_editable(self): return True


PERIMETER = "ELA1.DI.1"   # a door - watches at night
INTERIOR = "ELA1.DI.2"    # a motion detector inside - excluded at night
ALWAYS = "ELA1.DI.3"      # a 24H line


def _build(users=None, zones=("Z1",)):
    bus = EventBus()
    tags = TagManager(bus)
    for address in (PERIMETER, INTERIOR, ALWAYS):
        tags.add_tag(address, True, TagType.BOOL, description="test line")  # NC: True = secure
    project = FakeProjectManager(
        zones=[{"id": zone, "name": f"Zone {zone}", "exit_delay_seconds": 0.0, "entry_delay_seconds": 0.0}
               for zone in zones],
        lines=[
            {"id": "L1", "name": "Front door", "zone_id": "Z1", "tag": PERIMETER,
             "normal_state": "NC", "line_type": LineType.INSTANT, "active_at_night": True},
            {"id": "L2", "name": "Hall motion", "zone_id": "Z1", "tag": INTERIOR,
             "normal_state": "NC", "line_type": LineType.INSTANT, "active_at_night": False},
            {"id": "L3", "name": "Tamper", "zone_id": "Z1", "tag": ALWAYS,
             "normal_state": "NC", "line_type": LineType.TWENTY_FOUR_HOUR, "active_at_night": False},
        ],
        users=users or [],
    )
    manager = IntrusionManager(bus, tags, project)
    return manager, tags, project


def _violate(tags, address):
    tags.update_tag(address, False)   # NC line opened


# --- night arming ------------------------------------------------------------

def test_a_full_arm_watches_everything():
    manager, tags, _ = _build()
    assert manager.arm_zone("Z1", actor="test").success is True

    _violate(tags, INTERIOR)

    assert manager.get_zone_state("Z1") == ZoneState.ALARM


def test_a_night_arm_ignores_the_lines_excluded_from_it():
    """The whole point: someone can walk through the hall without
    setting the alarm off, while the front door still watches."""
    manager, tags, _ = _build()
    assert manager.arm_zone("Z1", actor="test", mode=ArmMode.NIGHT).success is True
    assert manager.get_zone_arm_mode("Z1") == ArmMode.NIGHT

    _violate(tags, INTERIOR)
    assert manager.get_zone_state("Z1") == ZoneState.ARMED, "the excluded line must not alarm"

    _violate(tags, PERIMETER)
    assert manager.get_zone_state("Z1") == ZoneState.ALARM, "the perimeter still watches at night"


def test_a_24h_line_alarms_at_night_too():
    """A tamper does not care how the zone is armed - or whether it is."""
    manager, tags, _ = _build()
    manager.arm_zone("Z1", actor="test", mode=ArmMode.NIGHT)

    _violate(tags, ALWAYS)

    assert manager.get_zone_state("Z1") == ZoneState.ALARM


def test_an_excluded_line_does_not_block_a_night_arm():
    """Refusing a night arm because the motion detector sees the person
    doing the arming is exactly what night arming exists to avoid."""
    manager, tags, _ = _build()
    _violate(tags, INTERIOR)

    blocked = manager.arm_zone("Z1", actor="test")
    assert blocked.success is False and blocked.needs_confirmation is True

    assert manager.arm_zone("Z1", actor="test", mode=ArmMode.NIGHT).success is True


def test_disarming_puts_the_mode_back_so_the_next_arm_is_full():
    manager, _tags, _ = _build()
    manager.arm_zone("Z1", actor="test", mode=ArmMode.NIGHT)
    manager.disarm_zone("Z1", actor="test")

    assert manager.get_zone_arm_mode("Z1") == ArmMode.FULL


def test_an_unknown_mode_is_refused_rather_than_treated_as_full():
    manager, _tags, _ = _build()
    result = manager.arm_zone("Z1", actor="test", mode="SOMETHING_ELSE")
    assert result.success is False and "mode" in result.reason.lower()
    assert manager.get_zone_state("Z1") == ZoneState.DISARMED


def test_the_mode_survives_a_restart():
    """A zone armed at night must not come back from a power cut
    watching more than the person who armed it left watching - nor
    less."""
    manager, _tags, project = _build()
    manager.arm_zone("Z1", actor="test", mode=ArmMode.NIGHT)
    assert project.arm_modes == {"Z1": ArmMode.NIGHT}

    restarted, tags, _ = _build()
    restarted.project_manager.armed = list(project.armed)
    restarted.project_manager.arm_modes = dict(project.arm_modes)
    restarted._restore_operation_state([])

    assert restarted.get_zone_state("Z1") == ZoneState.ARMED
    assert restarted.get_zone_arm_mode("Z1") == ArmMode.NIGHT
    _violate(tags, INTERIOR)
    assert restarted.get_zone_state("Z1") == ZoneState.ARMED, "still a night arm after the restart"


def test_is_line_watching_answers_the_question_the_page_asks():
    manager, _tags, _ = _build()
    assert manager.is_line_watching("L1") is False, "nothing watches while disarmed"
    assert manager.is_line_watching("L3") is True, "except a 24H line"

    manager.arm_zone("Z1", actor="test", mode=ArmMode.NIGHT)
    assert manager.is_line_watching("L1") is True
    assert manager.is_line_watching("L2") is False
    assert manager.is_line_watching("L3") is True


def test_a_line_that_predates_the_flag_watches_at_night():
    """An existing installation armed at night protects exactly as much
    as a full arm until someone excludes something - never less."""
    manager, tags, _ = _build()
    manager._lines["L2"].pop("active_at_night", None)
    manager.arm_zone("Z1", actor="test", mode=ArmMode.NIGHT)

    _violate(tags, INTERIOR)

    assert manager.get_zone_state("Z1") == ZoneState.ALARM


# --- who may operate which zone ----------------------------------------------

USERS = [
    {"id": "U1", "name": "Kowalski", "level": "Operator", "zones": ["Z1"]},
    {"id": "U2", "name": "Nowak", "level": "Operator", "zones": ["Z2"]},
    {"id": "U3", "name": "Kierownik", "level": "Operator", "zones": []},
    {"id": "U4", "name": "Były pracownik", "level": "Operator", "zones": [], "enabled": False},
]


def test_only_the_user_allowed_on_a_zone_may_arm_and_disarm_it():
    manager, _tags, _ = _build(users=USERS)

    assert manager.arm_zone("Z1", actor="Nowak", user="U2").success is False
    assert manager.get_zone_state("Z1") == ZoneState.DISARMED

    assert manager.arm_zone("Z1", actor="Kowalski", user="U1").success is True
    assert manager.disarm_zone("Z1", actor="Nowak", user="U2") is False
    assert manager.get_zone_state("Z1") == ZoneState.ARMED, "a refused disarm changes nothing"
    assert manager.disarm_zone("Z1", actor="Kowalski", user="U1") is True


def test_a_user_with_no_zones_listed_may_operate_every_zone():
    manager, _tags, _ = _build(users=USERS)
    assert manager.arm_zone("Z1", actor="Kierownik", user="U3").success is True


def test_a_disabled_user_and_an_unknown_one_are_both_refused():
    manager, _tags, _ = _build(users=USERS)
    assert manager.arm_zone("Z1", actor="Były pracownik", user="U4").success is False
    assert manager.arm_zone("Z1", actor="?", user="U404").success is False


def test_no_user_at_all_leaves_the_level_gate_exactly_as_it_was():
    """An installation that configures no users notices nothing: the
    panel's own Operator-level path still arms and disarms."""
    manager, _tags, _ = _build(users=USERS)
    assert manager.arm_zone("Z1", actor="Operator", level=AccessLevel.OPERATOR).success is True
    assert manager.disarm_zone("Z1", actor="Operator", level=AccessLevel.OPERATOR) is True


def test_a_refusal_is_recorded_not_just_returned():
    """Somebody turned away at the keypad is exactly the kind of event
    the register has to carry."""
    recorded = []

    class Audit:
        def record(self, event_type, actor, detail, success=True):
            recorded.append((event_type, actor, detail, success))

    manager, _tags, _ = _build(users=USERS)
    manager.audit_logger = Audit()

    manager.disarm_zone("Z1", actor="Nowak", user="U2")

    assert recorded and recorded[0][0] == "INTRUSION_USER_REFUSED"
    assert "Nowak" in recorded[0][1] and recorded[0][3] is False


def test_the_event_names_the_person_who_armed_it():
    entries = []

    class Audit:
        def record(self, event_type, actor, detail, success=True):
            entries.append(detail)

    manager, _tags, _ = _build(users=USERS)
    manager.audit_logger = Audit()

    manager.arm_zone("Z1", actor="Kowalski", user="U1", mode=ArmMode.NIGHT)

    assert any("Kowalski" in detail and "NIGHT" in detail for detail in entries), entries


# --- signing in as a person ---------------------------------------------------

@pytest.fixture
def access(tmp_path):
    manager = AccessManager(EventBus(), config_path=str(tmp_path / "access.local.json"))
    manager.set_users(USERS)
    return manager


def test_a_personal_code_signs_the_person_in_with_their_own_level(access):
    assert access.set_user_pin("U1", "4711", level=AccessLevel.ENGINEER) is True

    assert access.attempt_user_login("0000") is None
    user = access.attempt_user_login("4711")

    assert user["name"] == "Kowalski"
    assert access.level == AccessLevel.OPERATOR
    assert access.current_user_id() == "U1"
    assert access.current_actor() == "Kowalski"


def test_a_disabled_user_cannot_sign_in_even_with_the_right_code(access):
    access.set_user_pin("U4", "1234", level=AccessLevel.ENGINEER)
    assert access.attempt_user_login("1234") is None
    assert access.level == AccessLevel.USER


def test_a_level_pin_is_nobody_in_particular(access):
    access.set_user_pin("U1", "4711", level=AccessLevel.ENGINEER)
    access.attempt_user_login("4711")
    assert access.current_user_id() == "U1"

    access.set_pin(AccessLevel.OPERATOR, "9999")
    access.attempt_login(AccessLevel.OPERATOR, "9999")

    assert access.current_user_id() is None
    assert access.current_actor() == AccessLevel.OPERATOR


def test_logging_out_ends_the_named_session(access):
    access.set_user_pin("U1", "4711", level=AccessLevel.ENGINEER)
    access.attempt_user_login("4711")
    access.logout()
    assert access.current_user_id() is None


def test_setting_a_code_is_engineer_only_and_only_for_a_real_user(access):
    assert access.set_user_pin("U1", "4711", level=AccessLevel.OPERATOR) is False
    assert access.set_user_pin("U404", "4711", level=AccessLevel.ENGINEER) is False
    assert access.attempt_user_login("4711") is None


def test_a_user_the_project_no_longer_has_loses_their_stored_code(access):
    access.set_user_pin("U1", "4711", level=AccessLevel.ENGINEER)
    access.set_users([u for u in USERS if u["id"] != "U1"])

    assert access.attempt_user_login("4711") is None
    assert [u["id"] for u in access.get_users()] == ["U2", "U3", "U4"]


def test_codes_never_reach_the_project(access):
    """The split the whole design rests on: identities travel in
    projekt.epw, codes stay on this controller."""
    access.set_user_pin("U1", "4711", level=AccessLevel.ENGINEER)
    listed = access.get_users()

    # has_pin (a bool: "is a code set on this panel") is the ONLY thing
    # said about codes - never the code, never its hash.
    assert all(set(user) == {"id", "name", "level", "zones", "enabled", "has_pin"} for user in listed)
    assert next(u for u in listed if u["id"] == "U1")["has_pin"] is True
    assert next(u for u in listed if u["id"] == "U2")["has_pin"] is False
