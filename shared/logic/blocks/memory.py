from shared.logic.blocks.base import BaseLogicBlock
from shared.logic.blocks.pin import Pin
from shared.logic.blocks.registry import BlockRegistry

class MemoryBase(BaseLogicBlock):
    PIN_DESCRIPTIONS = {"Q": "Current latch state."}

    def __init__(self, type_id, default_name, category, description):
        super().__init__(type_id, default_name, category, description)
        self.color = "#808000" # Classic Olive for memory
        self.width = 80
        self.height = 80

        self.outputs.append(Pin("Q", Pin.DIR_OUTPUT, Pin.TYPE_BOOLEAN))
        # Internal state memory
        self._memory = False
        self.is_stateful = True

    def reset_runtime_state(self):
        self._memory = False

@BlockRegistry.register
class SR(MemoryBase):
    PIN_DESCRIPTIONS = {
        "S1": "Set input — dominant: when S1 and R are active together, Set wins.",
        "R": "Reset input.",
    }

    def __init__(self, type_id="memory.sr", default_name="SR", category="Flip-flops", description="Set-dominant latch (Set wins over Reset)."):
        super().__init__(type_id, default_name, category, description)
        self.aliases = ["przerzutnik", "zatrzask", "pamięć"]
        self.inputs.append(Pin("S1", Pin.DIR_INPUT, Pin.TYPE_BOOLEAN))
        self.inputs.append(Pin("R", Pin.DIR_INPUT, Pin.TYPE_BOOLEAN))

    def evaluate(self, engine=None):
        s = bool(self.inputs[0].value)
        r = bool(self.inputs[1].value)

        if s: # Set dominant
            self._memory = True
        elif r:
            self._memory = False

        self.outputs[0].value = self._memory

@BlockRegistry.register
class RS(MemoryBase):
    PIN_DESCRIPTIONS = {
        "R1": "Reset input — dominant: when R1 and S are active together, Reset wins.",
        "S": "Set input.",
    }

    def __init__(self, type_id="memory.rs", default_name="RS", category="Flip-flops", description="Reset-dominant latch (Reset wins over Set)."):
        super().__init__(type_id, default_name, category, description)
        self.aliases = ["przerzutnik", "zatrzask", "pamięć"]
        self.inputs.append(Pin("R1", Pin.DIR_INPUT, Pin.TYPE_BOOLEAN))
        self.inputs.append(Pin("S", Pin.DIR_INPUT, Pin.TYPE_BOOLEAN))

    def evaluate(self, engine=None):
        r = bool(self.inputs[0].value)
        s = bool(self.inputs[1].value)

        if r: # Reset dominant
            self._memory = False
        elif s:
            self._memory = True

        self.outputs[0].value = self._memory
