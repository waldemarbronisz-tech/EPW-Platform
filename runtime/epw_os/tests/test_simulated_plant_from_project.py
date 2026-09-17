"""The simulated plant answers the project's own apparatuses (2026-09-17):
an output the simulator driver writes closes/opens the apparatus's
CLOSED contact a moment later, for every command style, so the command
loop confirms and the screens change without hardware."""
import time

from epw_os.core.events import EventBus
from epw_os.simulation.simulated_plant import SimulatedPlant, plant_mappings_from_apparatuses


def _records():
    return [
        {"id": "KOT_Q1", "behavior": "SWITCHED", "feedback": ["DI1.DI.1"], "command": ["DO1.DO.1"],
         "command_style": "MAINTAINED"},
        {"id": "KOT_KM1", "behavior": "SWITCHED", "feedback": ["DI1.DI.2"], "command": ["DO1.DO.2", "DO1.DO.3"],
         "command_style": "PULSE"},
        {"id": "KOT_KM2", "behavior": "SWITCHED", "feedback": ["DI1.DI.4"], "command": ["DO1.DO.4"],
         "command_style": "PULSE_TOGGLE"},
        {"id": "KOT_ALARM", "behavior": "SIGNAL", "feedback": ["DI1.DI.6"], "command": []},
        {"id": "KOT_BLIND", "behavior": "SWITCHED", "feedback": [], "command": ["DO1.DO.7"]},
    ]


def test_mappings_follow_the_command_convention():
    mappings = plant_mappings_from_apparatuses(_records(), delay_ms=0)
    assert mappings["DO1.DO.1"] == {"trigger_value": True, "delay_ms": 0, "feedback_tag": "DI1.DI.1", "feedback_value": True}
    release = mappings["DO1.DO.1\x00release"]
    assert (release["source_tag"], release["trigger_value"], release["feedback_value"]) == ("DO1.DO.1", False, False)
    assert mappings["DO1.DO.2"]["feedback_value"] is True and mappings["DO1.DO.3"]["feedback_value"] is False
    assert mappings["DO1.DO.4"] == {"trigger_value": True, "delay_ms": 0, "feedback_tag": "DI1.DI.4", "toggle": True}
    assert "DO1.DO.7" not in mappings                      # no contact to simulate
    assert not any(k.startswith("DI1.DI.6") for k in mappings)


class _Seen:
    def __init__(self, bus):
        self.updates = []
        bus.subscribe("driver_update", lambda tag, value, quality: self.updates.append((tag, value)))

    def feedback(self, tag):
        return [v for t, v in self.updates if t == tag]


def test_a_held_output_closes_and_opens_the_contact():
    bus = EventBus()
    plant = SimulatedPlant(bus, plant_mappings_from_apparatuses(_records(), delay_ms=0))
    seen = _Seen(bus)
    bus.emit("driver_update", "DO1.DO.1", True, "GOOD")
    bus.emit("driver_update", "DO1.DO.1", False, "GOOD")
    assert seen.feedback("DI1.DI.1") == [True, False]
    assert plant.mappings["DO1.DO.1"]["feedback_tag"] == "DI1.DI.1"


def test_two_pulsed_outputs_drive_the_contact_each_way_and_a_release_does_nothing():
    bus = EventBus()
    SimulatedPlant(bus, plant_mappings_from_apparatuses(_records(), delay_ms=0))
    seen = _Seen(bus)
    bus.emit("driver_update", "DO1.DO.2", True, "GOOD")
    bus.emit("driver_update", "DO1.DO.2", False, "GOOD")      # the pulse ends - nothing happens
    bus.emit("driver_update", "DO1.DO.3", True, "GOOD")
    assert seen.feedback("DI1.DI.2") == [True, False]


def test_a_single_toggle_output_flips_the_contact_every_pulse():
    bus = EventBus()
    SimulatedPlant(bus, plant_mappings_from_apparatuses(_records(), delay_ms=0))
    seen = _Seen(bus)
    for _ in range(3):
        bus.emit("driver_update", "DO1.DO.4", True, "GOOD")
        bus.emit("driver_update", "DO1.DO.4", False, "GOOD")
    assert seen.feedback("DI1.DI.4") == [True, False, True]


def test_a_delay_is_honoured_and_the_legacy_mappings_still_work():
    bus = EventBus()
    plant = SimulatedPlant(bus, {"ADA01.DO01": {"trigger_value": True, "delay_ms": 30, "feedback_tag": "ELA01.DI03",
                                                "feedback_value": True}})
    plant.add_mappings(plant_mappings_from_apparatuses(_records(), delay_ms=30))
    seen = _Seen(bus)
    bus.emit("driver_update", "ADA01.DO01", True, "GOOD")
    bus.emit("driver_update", "DO1.DO.1", True, "GOOD")
    assert seen.feedback("ELA01.DI03") == [] and seen.feedback("DI1.DI.1") == []
    deadline = time.time() + 2
    while time.time() < deadline and (not seen.feedback("ELA01.DI03") or not seen.feedback("DI1.DI.1")):
        time.sleep(0.01)
    assert seen.feedback("ELA01.DI03") == [True] and seen.feedback("DI1.DI.1") == [True]
