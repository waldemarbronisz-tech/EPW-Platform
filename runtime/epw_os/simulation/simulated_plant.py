"""The simulated plant: turns an output the simulator driver "wrote" into
the feedback a real apparatus would report a moment later, so the whole
command loop (CommandManager -> driver -> plant -> feedback tag ->
confirmation, symbol state on the screen) runs without hardware.

Mappings (`{output tag: {trigger_value, delay_ms, feedback_tag,
feedback_value | toggle}}`) come from two places: the four legacy
cabinet outputs EPWCore wires by hand, and - since 2026-09-17 - the
project's own apparatus register (plant_mappings_from_apparatuses()):
every SWITCHED apparatus with an output and a CLOSED contact gets its
close output driving the contact closed, its open output (when it has
one) driving it open, a single MAINTAINED output following its level,
and a single PULSE_TOGGLE output toggling the contact - the same
convention apparatus.py's command definitions use (feedback[0] = the
CLOSED contact, command[0] = CLOSE, command[1] = OPEN).
"""
import threading

from epw_os.core.logging import log


class SimulatedPlant:
    def __init__(self, event_bus, mappings=None):
        self.event_bus = event_bus
        self.mappings = dict(mappings or {})
        self._feedback_state = {}   # feedback tag -> last value this plant emitted (for toggles)
        self.event_bus.subscribe("driver_update", self._on_driver_update)

    def set_mappings(self, mappings: dict):
        """Replaces the whole mapping table (EPWCore.startup(), once the
        project's apparatuses are known)."""
        self.mappings = dict(mappings or {})

    def add_mappings(self, mappings: dict):
        self.mappings.update(mappings or {})

    def _on_driver_update(self, tag_name, value, quality):
        if tag_name in self._feedback_state or any(m.get("feedback_tag") == tag_name for m in self.mappings.values()):
            self._feedback_state[tag_name] = value
        # A mapping reacts to its own key, or to `source_tag` when one
        # output has more than one entry (a held output's True and False
        # edges - see plant_mappings_from_apparatuses()).
        for key, mapping in list(self.mappings.items()):
            if mapping.get("source_tag", key) != tag_name:
                continue
            if value != mapping.get("trigger_value", True):
                continue
            self._schedule(mapping)

    def _schedule(self, mapping):
        delay = mapping.get("delay_ms", 0)

        def publish():
            feedback_tag = mapping["feedback_tag"]
            if mapping.get("toggle"):
                new_value = not bool(self._feedback_state.get(feedback_tag, False))
            else:
                new_value = mapping.get("feedback_value", True)
            self._feedback_state[feedback_tag] = new_value
            self.event_bus.emit("driver_update", feedback_tag, new_value, "GOOD")

        if delay > 0:
            timer = threading.Timer(delay / 1000.0, publish)
            timer.daemon = True
            timer.start()
        else:
            publish()


def plant_mappings_from_apparatuses(records, delay_ms: int = 50) -> dict:
    """[{id, behavior, feedback, command, command_style}] (ProjectManager.
    get_apparatuses()) -> SimulatedPlant mappings. An apparatus without
    an output or without a CLOSED contact has nothing to simulate."""
    mappings = {}
    for record in records:
        if (record.get("behavior") or "").upper() != "SWITCHED":
            continue
        command = [c for c in (record.get("command") or []) if c]
        feedback = [f for f in (record.get("feedback") or []) if f]
        if not command or not feedback:
            continue
        style = (record.get("command_style") or "MAINTAINED").upper()
        closed_contact = feedback[0]
        close_out = command[0]
        open_out = command[1] if len(command) > 1 else None
        if style == "PULSE_TOGGLE" and open_out is None:
            mappings[close_out] = {"trigger_value": True, "delay_ms": delay_ms, "feedback_tag": closed_contact,
                                   "toggle": True}
            continue
        mappings[close_out] = {"trigger_value": True, "delay_ms": delay_ms, "feedback_tag": closed_contact,
                               "feedback_value": True}
        if open_out is not None:
            mappings[open_out] = {"trigger_value": True, "delay_ms": delay_ms, "feedback_tag": closed_contact,
                                  "feedback_value": False}
        elif style == "MAINTAINED":
            # One held output: releasing it opens the apparatus. A second
            # mapping keyed by the same tag would clash, so the level's
            # False edge is expressed as a separate entry under a marker.
            mappings[close_out + "\x00release"] = {"source_tag": close_out, "trigger_value": False,
                                                   "delay_ms": delay_ms, "feedback_tag": closed_contact,
                                                   "feedback_value": False}
        if len(feedback) > 1:
            log.debug(f"Simulated plant: {record.get('id')} has a second (OPEN) contact - not simulated.")
    return mappings
