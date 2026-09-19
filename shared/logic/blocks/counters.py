from shared.logic.blocks.base import BaseLogicBlock
from shared.logic.blocks.pin import Pin
from shared.logic.blocks.registry import BlockRegistry

class CounterBase(BaseLogicBlock):
    PROPERTY_DESCRIPTIONS = {
        "Preset": "Target/initial counter value, used when the PV input is not connected.",
    }

    def __init__(self, type_id, default_name, category, description):
        super().__init__(type_id, default_name, category, description)
        self.color = "#008080" # Classic Teal (similar to Timers)
        self.width = 100
        self.height = 120
        self.properties["Preset"] = 10
        self._count = 0
        self._last_cu = False
        self._last_cd = False
        self.is_stateful = True

    def reset_runtime_state(self):
        self._count = 0
        self._last_cu = False
        self._last_cd = False
        self.simulation_state["count"] = 0

    def get_preset(self):
        return int(self.properties.get("Preset", 10))

    def _publish_count(self):
        """Mirror the authoritative count into simulation_state for read-only UI display."""
        self.simulation_state["count"] = self._count

@BlockRegistry.register
class CTU(CounterBase):
    PIN_DESCRIPTIONS = {
        "CU": "A rising edge on this input increments the counter by 1.",
        "R": "Resets the counter to zero (overrides CU).",
        "PV": "Target value — when connected, overrides the Preset property.",
        "Q": "True when CV has reached or exceeded the target value.",
        "CV": "Current counter value.",
    }

    def __init__(self, type_id="counter.ctu", default_name="CTU", category="Counters", description="Counter counting up to the target value."):
        super().__init__(type_id, default_name, category, description)
        self.aliases = ["licznik"]
        self.inputs.append(Pin("CU", Pin.DIR_INPUT, Pin.TYPE_BOOLEAN))
        self.inputs.append(Pin("R", Pin.DIR_INPUT, Pin.TYPE_BOOLEAN))
        self.inputs.append(Pin("PV", Pin.DIR_INPUT, Pin.TYPE_INTEGER))

        self.outputs.append(Pin("Q", Pin.DIR_OUTPUT, Pin.TYPE_BOOLEAN))
        self.outputs.append(Pin("CV", Pin.DIR_OUTPUT, Pin.TYPE_INTEGER))

    def evaluate(self, engine=None):
        cu = bool(self.inputs[0].value)
        r = bool(self.inputs[1].value)
        pv = int(self.inputs[2].value) if self.inputs[2].value is not None else self.get_preset()

        if r:
            self._count = 0
        elif cu and not self._last_cu:
            self._count += 1

        self._last_cu = cu
        self._publish_count()

        cv = self._count
        self.outputs[1].value = cv
        self.outputs[0].value = (cv >= pv)

@BlockRegistry.register
class CTD(CounterBase):
    PIN_DESCRIPTIONS = {
        "CD": "A rising edge on this input decrements the counter by 1.",
        "LD": "Loads the counter with PV (overrides CD).",
        "PV": "Value loaded by LD — when connected, overrides the Preset property.",
        "Q": "True when CV has reached or dropped below zero.",
        "CV": "Current counter value.",
    }

    def __init__(self, type_id="counter.ctd", default_name="CTD", category="Counters", description="Counter counting down from the initial value."):
        super().__init__(type_id, default_name, category, description)
        self.aliases = ["licznik"]
        self.inputs.append(Pin("CD", Pin.DIR_INPUT, Pin.TYPE_BOOLEAN))
        self.inputs.append(Pin("LD", Pin.DIR_INPUT, Pin.TYPE_BOOLEAN))
        self.inputs.append(Pin("PV", Pin.DIR_INPUT, Pin.TYPE_INTEGER))

        self.outputs.append(Pin("Q", Pin.DIR_OUTPUT, Pin.TYPE_BOOLEAN))
        self.outputs.append(Pin("CV", Pin.DIR_OUTPUT, Pin.TYPE_INTEGER))

    def evaluate(self, engine=None):
        cd = bool(self.inputs[0].value)
        ld = bool(self.inputs[1].value)
        pv = int(self.inputs[2].value) if self.inputs[2].value is not None else self.get_preset()

        if ld:
            self._count = pv
        elif cd and not self._last_cd:
            self._count -= 1

        self._last_cd = cd
        self._publish_count()

        cv = self._count
        self.outputs[1].value = cv
        self.outputs[0].value = (cv <= 0)

@BlockRegistry.register
class CTUD(CounterBase):
    PIN_DESCRIPTIONS = {
        "CU": "A rising edge on this input increments the counter by 1.",
        "CD": "A rising edge on this input decrements the counter by 1.",
        "R": "Resets the counter to zero (overrides CU/CD/LD).",
        "LD": "Loads the counter with PV (overrides CU/CD, overridden by R).",
        "PV": "Value loaded by LD and the threshold for QU — when connected, overrides the Preset property.",
        "QU": "True when CV has reached or exceeded PV.",
        "QD": "True when CV has reached or dropped below zero.",
        "CV": "Current counter value.",
    }

    def __init__(self, type_id="counter.ctud", default_name="CTUD", category="Counters", description="Up/down counter."):
        super().__init__(type_id, default_name, category, description)
        self.aliases = ["licznik"]
        self.height = 140
        self.inputs.append(Pin("CU", Pin.DIR_INPUT, Pin.TYPE_BOOLEAN))
        self.inputs.append(Pin("CD", Pin.DIR_INPUT, Pin.TYPE_BOOLEAN))
        self.inputs.append(Pin("R", Pin.DIR_INPUT, Pin.TYPE_BOOLEAN))
        self.inputs.append(Pin("LD", Pin.DIR_INPUT, Pin.TYPE_BOOLEAN))
        self.inputs.append(Pin("PV", Pin.DIR_INPUT, Pin.TYPE_INTEGER))

        self.outputs.append(Pin("QU", Pin.DIR_OUTPUT, Pin.TYPE_BOOLEAN))
        self.outputs.append(Pin("QD", Pin.DIR_OUTPUT, Pin.TYPE_BOOLEAN))
        self.outputs.append(Pin("CV", Pin.DIR_OUTPUT, Pin.TYPE_INTEGER))

    def evaluate(self, engine=None):
        cu = bool(self.inputs[0].value)
        cd = bool(self.inputs[1].value)
        r = bool(self.inputs[2].value)
        ld = bool(self.inputs[3].value)
        pv = int(self.inputs[4].value) if self.inputs[4].value is not None else self.get_preset()

        if r:
            self._count = 0
        elif ld:
            self._count = pv
        else:
            if cu and not self._last_cu:
                self._count += 1
            if cd and not self._last_cd:
                self._count -= 1

        self._last_cu = cu
        self._last_cd = cd
        self._publish_count()

        cv = self._count
        self.outputs[2].value = cv
        self.outputs[0].value = (cv >= pv)
        self.outputs[1].value = (cv <= 0)
