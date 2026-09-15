"""Task "wyłącznik jednocewkowy bistabilny" (Waldek's schematic, arkusz
14/18: KP2 is an R15/3P impulse relay with ONE coil; DO3 "na załącz KM1"
via KA3, DO4 "na wyłącz KM1" via KA4 and the local push-buttons SB3/SB4
all put +24 V on that same coil, so EVERY pulse toggles; DI2 is the only
thing that knows KM1's state).

Two things the runtime could not do before this task, proven here:
  1. release a pulsed output - pulse_ms was carried in CommandDefinition
     but never acted on, every "pulsed" coil stayed energized forever;
  2. refuse to pulse an impulse relay already in the requested state -
     the pulse would have flipped it the wrong way.
Plus the definitions themselves: an apparatus had NO `<id>.CLOSE`/
`<id>.OPEN` of its own at all, only the raw per-DO defaults.
"""
import time

from epw_os.core.apparatus import Apparatus, apparatus_command_definitions
from epw_os.core.command_manager import CommandManager, CommandState
from epw_os.core.events import EventBus
from epw_os.core.tag_manager import TagManager, TagType


class _AllowAll:
    def validate_command_safety(self, target, action):
        return True, ""

    def validate_command(self, target, action):
        return True, []


class _Driver:
    def __init__(self):
        self.writes = []

    def route_command(self, driver_id, output_tag, value):
        self.writes.append((output_tag, value))
        return True


def _manager():
    bus = EventBus()
    tm = TagManager(bus)
    driver = _Driver()
    cm = CommandManager(tm, _AllowAll(), _AllowAll(), bus, driver_manager=driver)
    return cm, tm, driver


def _km1(style, command=("ADA1.DO.3", "ADA1.DO.4"), feedback=("ELA1.DI.2",), pulse_ms=100):
    return Apparatus(id="KOT_KM1", behavior="SWITCHED", feedback=list(feedback), command=list(command),
                     command_style=style, pulse_ms=pulse_ms)


# --- definitions -----------------------------------------------------------

def test_the_schematic_case_two_outputs_one_impulse_coil():
    defs = apparatus_command_definitions([_km1("PULSE_TOGGLE")])
    close, open_ = defs["KOT_KM1.CLOSE"], defs["KOT_KM1.OPEN"]
    assert (close["output_tag"], close["output_value"], close["pulse_ms"]) == ("ADA1.DO.3", True, 100)
    assert (open_["output_tag"], open_["output_value"], open_["pulse_ms"]) == ("ADA1.DO.4", True, 100)
    assert (close["feedback_tag"], close["feedback_value"]) == ("ELA1.DI.2", True)
    assert (open_["feedback_tag"], open_["feedback_value"]) == ("ELA1.DI.2", False)
    assert close["skip_when_feedback_matches"] and open_["skip_when_feedback_matches"]


def test_single_output_toggle_pulses_the_same_coil_both_ways():
    defs = apparatus_command_definitions([_km1("PULSE_TOGGLE", command=("ADA1.DO.3",))])
    assert defs["KOT_KM1.CLOSE"]["output_tag"] == "ADA1.DO.3"
    assert defs["KOT_KM1.OPEN"]["output_tag"] == "ADA1.DO.3"


def test_toggle_without_feedback_is_refused_not_guessed():
    assert apparatus_command_definitions([_km1("PULSE_TOGGLE", feedback=())]) == {}


def test_pulsed_style_without_pulse_time_is_refused():
    assert apparatus_command_definitions([_km1("PULSE", pulse_ms=0)]) == {}


def test_maintained_two_coils_release_the_opposite_one():
    defs = apparatus_command_definitions([_km1("MAINTAINED")])
    assert defs["KOT_KM1.CLOSE"]["also_reset_tag"] == "ADA1.DO.4"
    assert defs["KOT_KM1.OPEN"]["also_reset_tag"] == "ADA1.DO.3"
    assert "pulse_ms" not in defs["KOT_KM1.CLOSE"]


def test_maintained_one_coil_is_a_level():
    defs = apparatus_command_definitions([_km1("MAINTAINED", command=("ADA1.DO.3",))])
    assert (defs["KOT_KM1.CLOSE"]["output_value"], defs["KOT_KM1.OPEN"]["output_value"]) == (True, False)


def test_plain_pulse_with_one_output_commands_close_only():
    defs = apparatus_command_definitions([_km1("PULSE", command=("ADA1.DO.3",))])
    assert "KOT_KM1.CLOSE" in defs and "KOT_KM1.OPEN" not in defs


def test_non_switched_or_uncommanded_apparatus_gets_nothing():
    signal = Apparatus(id="KOT_S1", behavior="SIGNAL", feedback=["ELA1.DI.5"])
    no_output = Apparatus(id="KOT_X", behavior="SWITCHED", feedback=["ELA1.DI.6"])
    assert apparatus_command_definitions([signal, no_output]) == {}


# --- execution --------------------------------------------------------------

def _load(cm, tm, style="PULSE_TOGGLE"):
    tm.add_tag("ELA1.DI.2", False, TagType.BOOL)
    tm.add_tag("ADA1.DO.3", False, TagType.BOOL)
    tm.add_tag("ADA1.DO.4", False, TagType.BOOL)
    cm.load_definitions(apparatus_command_definitions([_km1(style, pulse_ms=30)]))


def test_pulse_is_released_after_pulse_ms():
    cm, tm, driver = _manager()
    _load(cm, tm)
    cm.request_command_ex("KOT_KM1", "CLOSE")
    assert driver.writes == [("ADA1.DO.3", True)]
    time.sleep(0.15)
    assert driver.writes == [("ADA1.DO.3", True), ("ADA1.DO.3", False)]


def test_close_on_an_already_closed_impulse_relay_does_not_pulse():
    cm, tm, driver = _manager()
    _load(cm, tm)
    tm.update_tag("ELA1.DI.2", True)  # KM1 already closed (DI2)
    record = cm.request_command_ex("KOT_KM1", "CLOSE")
    assert record.state == CommandState.SUCCESS
    assert "not pulsed" in record.reason
    assert driver.writes == []


def test_open_on_a_closed_impulse_relay_pulses_the_open_output():
    cm, tm, driver = _manager()
    _load(cm, tm)
    tm.update_tag("ELA1.DI.2", True)
    record = cm.request_command_ex("KOT_KM1", "OPEN")
    assert record.state == CommandState.FEEDBACK_PENDING
    assert driver.writes == [("ADA1.DO.4", True)]


def test_maintained_close_releases_the_open_coil_first():
    cm, tm, driver = _manager()
    _load(cm, tm, style="MAINTAINED")
    cm.request_command_ex("KOT_KM1", "CLOSE")
    assert driver.writes == [("ADA1.DO.4", False), ("ADA1.DO.3", True)]
    time.sleep(0.15)
    assert driver.writes == [("ADA1.DO.4", False), ("ADA1.DO.3", True)]  # a level is never released
