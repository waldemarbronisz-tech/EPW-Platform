from logic_studio.blocks.base import BaseLogicBlock
from logic_studio.blocks.pin import Pin
from logic_studio.blocks.registry import BlockRegistry

class ConstantBase(BaseLogicBlock):
    PIN_DESCRIPTIONS = {"Out": "Constant value configured in the properties of this block."}

    def __init__(self, type_id, default_name, category, description, pin_type):
        super().__init__(type_id, default_name, category, description)
        self.color = "#555555" # Dark grey for constants
        self.width = 60
        self.height = 60
        self.outputs = [Pin("Out", Pin.DIR_OUTPUT, pin_type)]
        self.is_source = True

@BlockRegistry.register
class TrueConstant(ConstantBase):
    def __init__(self, type_id="const.true", default_name="TRUE", category="Other", description="Boolean constant TRUE."):
        super().__init__(type_id, default_name, category, description, Pin.TYPE_BOOLEAN)

    def evaluate(self, engine=None):
        self.outputs[0].value = True

@BlockRegistry.register
class FalseConstant(ConstantBase):
    def __init__(self, type_id="const.false", default_name="FALSE", category="Other", description="Boolean constant FALSE."):
        super().__init__(type_id, default_name, category, description, Pin.TYPE_BOOLEAN)

    def evaluate(self, engine=None):
        self.outputs[0].value = False

@BlockRegistry.register
class RealConstant(ConstantBase):
    PROPERTY_DESCRIPTIONS = {"Value": "Numeric (floating point) value put on the Out output."}

    def __init__(self, type_id="const.real", default_name="REAL", category="Other", description="Floating point constant — set in the Value property."):
        super().__init__(type_id, default_name, category, description, Pin.TYPE_FLOAT)
        self.properties["Value"] = 0.0

    def evaluate(self, engine=None):
        try:
            self.outputs[0].value = float(self.properties.get("Value", 0.0))
        except (TypeError, ValueError):
            # feat/const-property-validation: Validator now rejects this at
            # compile time (see compiler/validator.py) — caught here too so
            # a block evaluated outside that path (a stray script, a future
            # caller) degrades to the safe default instead of crashing the
            # scan on a bad property value.
            self.outputs[0].value = 0.0

@BlockRegistry.register
class IntConstant(ConstantBase):
    PROPERTY_DESCRIPTIONS = {"Value": "Numeric (integer) value put on the Out output."}

    def __init__(self, type_id="const.int", default_name="INT", category="Other", description="Integer constant — set in the Value property."):
        super().__init__(type_id, default_name, category, description, Pin.TYPE_INTEGER)
        self.properties["Value"] = 0

    def evaluate(self, engine=None):
        try:
            self.outputs[0].value = int(self.properties.get("Value", 0))
        except (TypeError, ValueError):
            self.outputs[0].value = 0

@BlockRegistry.register
class TimeConstant(ConstantBase):
    PROPERTY_DESCRIPTIONS = {"Time (ms)": "Time in milliseconds put on the Out output."}
    PROPERTY_UNITS = {"Time (ms)": "ms"}

    def __init__(self, type_id="const.time", default_name="TIME", category="Other", description="Time constant in milliseconds — set in the Time (ms) property."):
        super().__init__(type_id, default_name, category, description, Pin.TYPE_INTEGER)
        self.properties["Time (ms)"] = 1000

    def evaluate(self, engine=None):
        try:
            self.outputs[0].value = int(self.properties.get("Time (ms)", 1000))
        except (TypeError, ValueError):
            self.outputs[0].value = 1000

@BlockRegistry.register
class StringConstant(ConstantBase):
    PROPERTY_DESCRIPTIONS = {"Text": "Text put on the Out output."}

    def __init__(self, type_id="const.string", default_name="STRING", category="Other", description="Text constant — set in the Text property."):
        super().__init__(type_id, default_name, category, description, Pin.TYPE_STRING)
        self.properties["Text"] = ""

    def evaluate(self, engine=None):
        self.outputs[0].value = str(self.properties.get("Text", ""))
