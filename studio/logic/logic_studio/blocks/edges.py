from logic_studio.blocks.base import BaseLogicBlock
from logic_studio.blocks.pin import Pin
from logic_studio.blocks.registry import BlockRegistry

class EdgeBase(BaseLogicBlock):
    PIN_DESCRIPTIONS = {
        "In": "Signal watched for a change of state.",
        "Out": "One-scan pulse when an edge/change is detected.",
    }

    def __init__(self, type_id, default_name, category, description):
        super().__init__(type_id, default_name, category, description)
        self.color = "#8A2BE2" # BlueViolet for edge processing
        self.width = 60
        self.height = 60

        self.inputs = [Pin("In", Pin.DIR_INPUT, Pin.TYPE_BOOLEAN)]
        self.outputs = [Pin("Out", Pin.DIR_OUTPUT, Pin.TYPE_BOOLEAN)]

        self._last_in = False
        self.is_stateful = True

    def reset_runtime_state(self):
        self._last_in = False

@BlockRegistry.register
class RTrigBlock(EdgeBase):
    def __init__(self, type_id="edge.rtrig", default_name="R_TRIG", category="Edge detection", description="Detects a rising edge (0→1) on the input — a one-scan pulse."):
        super().__init__(type_id, default_name, category, description)
        self.aliases = ["zbocze narastające"]

    def evaluate(self, engine=None):
        current = bool(self.inputs[0].value)
        self.outputs[0].value = (current and not self._last_in)
        self._last_in = current

@BlockRegistry.register
class FTrigBlock(EdgeBase):
    def __init__(self, type_id="edge.ftrig", default_name="F_TRIG", category="Edge detection", description="Detects a falling edge (1→0) on the input — a one-scan pulse."):
        super().__init__(type_id, default_name, category, description)
        self.aliases = ["zbocze opadające"]
        self._last_in = True # Assume stable high if evaluating

    def reset_runtime_state(self):
        self._last_in = True

    def evaluate(self, engine=None):
        current = bool(self.inputs[0].value)
        self.outputs[0].value = (not current and self._last_in)
        self._last_in = current

@BlockRegistry.register
class ChangeBlock(EdgeBase):
    def __init__(self, type_id="edge.change", default_name="CHANGE", category="Edge detection", description="Detects any change of the input state (0→1 or 1→0) — a one-scan pulse."):
        super().__init__(type_id, default_name, category, description)

    def evaluate(self, engine=None):
        # Trigger on either edge
        current = bool(self.inputs[0].value)
        self.outputs[0].value = (current != self._last_in)
        self._last_in = current
