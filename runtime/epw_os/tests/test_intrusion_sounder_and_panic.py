"""Owner's instruction: "chce moc to swobodnie programowac ustawiajac bit
wewnetrzny alarm i pobudzenie danego DO ktory wyjdzie na syrene" - and,
for the missing line type, "dorob".

So EPW-OS drives NO siren. What it owns is the sounder's STATE - should
it be sounding, for how much longer, has somebody silenced it, is the
strobe still on - published as tags and as SEC.SYSTEM.SIREN_ACTIVE /
SIREN_TIME_LEFT / STROBE_ACTIVE / PANIC. Which output the siren hangs
on, through which interlocks, is a line of logic the engineer draws.

These tests pin that split, and the PANIC (napadowa) line type: alarms
in any zone state like a 24H line, but silent by default - the point of
a hold-up button is that the person standing over you does not learn you
pressed it.
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core.access_manager import AccessLevel
from epw_os.core.events import EventBus
from epw_os.core.intrusion_manager import ArmMode, IntrusionManager, LineType, ZoneState
from epw_os.core.tag_manager import TagManager, TagType

PERIMETER = "ELA1.DI.1"
HOLDUP = "ELA1.DI.2"
TAMPER = "ELA1.DI.3"


class FakeProjectManager:
    """Only what IntrusionManager reads, as in the other intrusion tests,
    plus the sounder settings."""

    def __init__(self, sounder=None, users=None):
        self.zones = [{"id": "Z1", "name": "Zone Z1", "exit_delay_seconds": 0.0, "entry_delay_seconds": 0.0},
                      {"id": "Z2", "name": "Zone Z2", "exit_delay_seconds": 0.0, "entry_delay_seconds": 0.0}]
        self.lines = [
            {"id": "L1", "name": "Front door", "zone_id": "Z1", "tag": PERIMETER,
             "normal_state": "NC", "line_type": LineType.INSTANT, "alarm_hold_seconds": 0.0},
            {"id": "L2", "name": "Hold-up button", "zone_id": "Z1", "tag": HOLDUP,
             "normal_state": "NC", "line_type": LineType.PANIC, "alarm_hold_seconds": 0.0},
            {"id": "L3", "name": "Tamper", "zone_id": "Z2", "tag": TAMPER,
             "normal_state": "NC", "line_type": LineType.TWENTY_FOUR_HOUR, "alarm_hold_seconds": 0.0},
        ]
        self.sounder = sounder or {}
        self.users = users or []
        self.armed, self.bypassed, self.arm_modes = [], [], {}
        self.alarm_memory = {}

    def get_intrusion_zones(self): return list(self.zones)
    def get_intrusion_lines(self): return list(self.lines)
    def get_intrusion_users(self): return list(self.users)
    def get_intrusion_sounder(self): return dict(self.sounder)
    def set_intrusion_zones(self, zones): self.zones = list(zones)
    def set_intrusion_lines(self, lines): self.lines = list(lines)
    def get_intrusion_line_supervision(self): return {}
    def get_intrusion_power_supervision(self): return {}
    def get_intrusion_alarm_memory(self): return dict(self.alarm_memory)
    def set_intrusion_alarm_memory(self, data): self.alarm_memory = dict(data)
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


def _build(sounder=None, users=None):
    bus = EventBus()
    tags = TagManager(bus)
    for address in (PERIMETER, HOLDUP, TAMPER):
        tags.add_tag(address, True, TagType.BOOL, description="test line")  # NC: True = secure
    project = FakeProjectManager(sounder=sounder, users=users)
    return IntrusionManager(bus, tags, project), tags, project


def _violate(tags, address):
    tags.update_tag(address, False)   # NC line opened


# --- the sounder is state, never an output ----------------------------------

def test_the_controller_publishes_the_sounder_instead_of_driving_it():
    """The tags below are the whole interface: this manager energizes no
    siren output, and is not supposed to."""
    manager, tags, _ = _build()
    manager.arm_zone("Z1", actor="test")

    _violate(tags, PERIMETER)

    assert manager.get_zone_state("Z1") == ZoneState.ALARM
    assert manager.siren_active() is True
    assert manager.strobe_active() is True
    assert tags.get_value("Security.System.SirenActive") is True
    assert tags.get_value("Security.System.StrobeActive") is True


def test_the_siren_stops_by_itself_while_the_alarm_carries_on():
    """A siren that never stops is against most local noise rules. The
    strobe is what keeps showing that something happened."""
    manager, tags, _ = _build(sounder={"siren_seconds": 60.0})
    manager.arm_zone("Z1", actor="test")
    _violate(tags, PERIMETER)
    assert manager.siren_active() is True
    assert 0 < manager.siren_time_left() <= 60.0

    manager._sounder_started_at -= 61.0   # 61 s later

    assert manager.siren_active() is False, "the noise is over"
    assert manager.siren_time_left() == 0.0
    assert manager.get_zone_state("Z1") == ZoneState.ALARM, "the alarm itself is not"
    assert manager.strobe_active() is True


def test_no_configured_limit_means_the_siren_sounds_until_somebody_acts():
    manager, tags, _ = _build(sounder={"siren_seconds": 0.0})
    manager.arm_zone("Z1", actor="test")
    _violate(tags, PERIMETER)

    manager._sounder_started_at -= 100000.0

    assert manager.siren_active() is True
    assert manager.siren_time_left() == 0.0, "no limit has no countdown to show"


# --- silencing ---------------------------------------------------------------

def test_silencing_stops_the_noise_and_nothing_else():
    manager, tags, _ = _build()
    manager.arm_zone("Z1", actor="test")
    _violate(tags, PERIMETER)

    assert manager.silence(actor="test") is True

    assert manager.siren_active() is False
    assert manager.get_zone_state("Z1") == ZoneState.ALARM, "the alarm stays"
    assert manager.strobe_active() is True, "and so does the light"
    assert manager.get_alarm_memory("Z1")["active"] is True


def test_a_second_break_in_sounds_again_after_a_silence():
    """Somebody silenced the PREVIOUS alarm; that decision does not
    cover a new one."""
    manager, tags, _ = _build()
    manager.arm_zone("Z1", actor="test")
    manager.arm_zone("Z2", actor="test")
    _violate(tags, PERIMETER)
    manager.silence(actor="test")
    assert manager.siren_active() is False

    _violate(tags, TAMPER)

    assert manager.siren_active() is True


def test_there_is_nothing_to_silence_without_an_alarm():
    manager, _, _ = _build()
    manager.arm_zone("Z1", actor="test")
    assert manager.silence(actor="test") is False


def test_silencing_is_refused_for_somebody_who_may_not_operate_that_zone():
    """The same rule as disarming: "tylko jakis jeden uzytkownik moze
    rozbroic dana strefe" would mean little if anyone could walk up and
    turn the noise off."""
    stranger = {"id": "U9", "name": "Stranger", "level": AccessLevel.OPERATOR, "zones": ["Z2"]}
    manager, tags, _ = _build(users=[stranger])
    manager.arm_zone("Z1", actor="test")
    _violate(tags, PERIMETER)

    assert manager.silence(actor="U9", user="U9") is False
    assert manager.siren_active() is True


# --- the sounder falls quiet when the alarm ends -----------------------------

def test_disarming_stops_the_sounder():
    manager, tags, _ = _build()
    manager.arm_zone("Z1", actor="test")
    _violate(tags, PERIMETER)

    manager.disarm_zone("Z1", actor="test")

    assert manager.siren_active() is False
    assert manager.strobe_active() is True, "the memory - and the light - outlive the disarm"


def test_clearing_the_alarm_memory_turns_the_strobe_off_too():
    manager, tags, _ = _build()
    manager.arm_zone("Z1", actor="test")
    _violate(tags, PERIMETER)
    manager.disarm_zone("Z1", actor="test")

    manager.clear_alarm_memory("Z1", actor="test", level=AccessLevel.OPERATOR)

    assert manager.strobe_active() is False
    assert manager.siren_active() is False


# --- PANIC (napadowa) --------------------------------------------------------

def test_a_hold_up_line_alarms_even_while_the_zone_is_disarmed():
    """Like a 24H line: a hold-up button that only worked while the
    building was armed would be worse than none."""
    manager, tags, _ = _build()
    assert manager.get_zone_state("Z1") == ZoneState.DISARMED

    _violate(tags, HOLDUP)

    assert manager.get_zone_state("Z1") == ZoneState.ALARM
    assert manager.panic_active() is True
    assert tags.get_value("Security.System.Panic") is True


def test_a_hold_up_line_is_silent_by_default():
    """The whole reason PANIC is its own type rather than a 24H line
    with a label."""
    manager, tags, _ = _build()

    _violate(tags, HOLDUP)

    assert manager.siren_active() is False, "the person standing over you must not hear it"
    assert manager.strobe_active() is True, "the alarm itself is entirely real"


def test_a_hold_up_line_can_be_made_audible_where_the_installation_wants_it():
    manager, tags, _ = _build(sounder={"panic_silent": False})

    _violate(tags, HOLDUP)

    assert manager.siren_active() is True


def test_a_break_in_elsewhere_during_a_silent_hold_up_alarm_still_sounds():
    """The silence belongs to the hold-up line, not to the site: an
    ordinary alarm in another zone sounds as it always would."""
    manager, tags, _ = _build()
    manager.arm_zone("Z2", actor="test")
    _violate(tags, HOLDUP)
    assert manager.siren_active() is False, "the hold-up alarm is silent"

    _violate(tags, TAMPER)

    assert manager.siren_active() is True


def test_the_panic_flag_is_cleared_with_the_alarm_not_by_disarming():
    """SEC.SYSTEM.PANIC means "somebody pressed it and nobody has
    acknowledged that yet", not a permanent property."""
    manager, tags, _ = _build()
    _violate(tags, HOLDUP)
    manager.disarm_zone("Z1", actor="test")
    assert manager.panic_active() is True

    manager.clear_alarm_memory("Z1", actor="test", level=AccessLevel.OPERATOR)

    assert manager.panic_active() is False


def test_a_panic_line_is_not_filtered_out_by_night_arming():
    manager, tags, _ = _build()
    manager.arm_zone("Z1", actor="test", mode=ArmMode.NIGHT)

    _violate(tags, HOLDUP)

    assert manager.get_zone_state("Z1") == ZoneState.ALARM
    assert manager.panic_active() is True
