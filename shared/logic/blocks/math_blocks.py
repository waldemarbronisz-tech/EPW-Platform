from shared.logic.blocks.base import BaseLogicBlock
from shared.logic.blocks.pin import Pin
from shared.logic.blocks.registry import BlockRegistry

class MathBase(BaseLogicBlock):
    PIN_DESCRIPTIONS = {
        "In1": "First operand.",
        "In2": "Second operand.",
        "Out": "Result.",
    }

    def __init__(self, type_id, default_name, category, description):
        super().__init__(type_id, default_name, category, description)
        self.color = "#800080" # Classic Purple for math
        self.width = 80
        self.height = 80

        self.inputs.append(Pin("In1", Pin.DIR_INPUT, Pin.TYPE_FLOAT))
        self.inputs.append(Pin("In2", Pin.DIR_INPUT, Pin.TYPE_FLOAT))
        self.outputs.append(Pin("Out", Pin.DIR_OUTPUT, Pin.TYPE_FLOAT))

    def _get_vals(self):
        v1 = float(self.inputs[0].value) if self.inputs[0].value is not None else 0.0
        v2 = float(self.inputs[1].value) if self.inputs[1].value is not None else 0.0
        return v1, v2

@BlockRegistry.register
class AddBlock(MathBase):
    def __init__(self, type_id="math.add", default_name="ADD", category="Analog", description="Addition — Out = In1 + In2."):
        super().__init__(type_id, default_name, category, description)

    def evaluate(self, engine=None):
        v1, v2 = self._get_vals()
        self.outputs[0].value = v1 + v2

@BlockRegistry.register
class SubBlock(MathBase):
    def __init__(self, type_id="math.sub", default_name="SUB", category="Analog", description="Subtraction — Out = In1 - In2."):
        super().__init__(type_id, default_name, category, description)

    def evaluate(self, engine=None):
        v1, v2 = self._get_vals()
        self.outputs[0].value = v1 - v2

@BlockRegistry.register
class MulBlock(MathBase):
    def __init__(self, type_id="math.mul", default_name="MUL", category="Analog", description="Multiplication — Out = In1 * In2."):
        super().__init__(type_id, default_name, category, description)

    def evaluate(self, engine=None):
        v1, v2 = self._get_vals()
        self.outputs[0].value = v1 * v2

@BlockRegistry.register
class DivBlock(MathBase):
    def __init__(self, type_id="math.div", default_name="DIV", category="Analog", description="Division — Out = In1 / In2 (when In2 = 0 the output is 0, no exception)."):
        super().__init__(type_id, default_name, category, description)

    def evaluate(self, engine=None):
        v1, v2 = self._get_vals()
        if v2 != 0:
            self.outputs[0].value = v1 / v2
        else:
            # Deterministic safe value on div/0
            self.outputs[0].value = 0.0

@BlockRegistry.register
class AbsBlock(MathBase):
    def __init__(self, type_id="math.abs", default_name="ABS", category="Analog", description="Absolute value — Out = |In1|."):
        # only "In1"/"Out" ever exist on this block (see below, In2 removed) -
        # inherited PIN_DESCRIPTIONS still has an unused "In2" entry, harmless
        # since the catalog only ever looks up pins a block ACTUALLY has.
        super().__init__(type_id, default_name, category, description)
        self.inputs.pop() # Only 1 input

    def evaluate(self, engine=None):
        v1 = float(self.inputs[0].value) if self.inputs[0].value is not None else 0.0
        self.outputs[0].value = abs(v1)

@BlockRegistry.register
class MinBlock(MathBase):
    def __init__(self, type_id="math.min", default_name="MIN", category="Analog", description="Smaller of two values — Out = min(In1, In2)."):
        super().__init__(type_id, default_name, category, description)

    def evaluate(self, engine=None):
        v1, v2 = self._get_vals()
        self.outputs[0].value = min(v1, v2)

@BlockRegistry.register
class MaxBlock(MathBase):
    def __init__(self, type_id="math.max", default_name="MAX", category="Analog", description="Larger of two values — Out = max(In1, In2)."):
        super().__init__(type_id, default_name, category, description)

    def evaluate(self, engine=None):
        v1, v2 = self._get_vals()
        self.outputs[0].value = max(v1, v2)
