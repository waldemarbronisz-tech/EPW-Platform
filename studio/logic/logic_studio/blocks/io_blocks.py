from logic_studio.blocks.base import BaseLogicBlock
from logic_studio.blocks.pin import Pin
from logic_studio.blocks.registry import BlockRegistry

@BlockRegistry.register
class DigitalInputBlock(BaseLogicBlock):
    PIN_DESCRIPTIONS = {"State": "Aktualny stan fizycznego wejścia cyfrowego."}
    PROPERTY_DESCRIPTIONS = {
        "Address": "Adres fizycznego wejścia cyfrowego (moduł ELA), np. \"ELA01.DI.1\".",
    }

    def __init__(self, type_id="input.di", default_name="DI", category="Wejścia / Wyjścia", description="Fizyczne wejście cyfrowe (moduł ELA)."):
        super().__init__(type_id, default_name, category, description)
        self.color = "#008000" # Classic dark green
        self.width = 100
        self.height = 60
        # Task "jedno źródło listy kart": no more a hardcoded default
        # address (was "ELA01.DI.1") - a fresh block dropped from the
        # Library (not dragged from Device Explorer with a real address
        # already attached) has no way to know whether ANY "ELA01" card
        # even exists in this project. Empty here means block_item.py's
        # own "???" missing-config warning (§1) fires immediately -
        # honest, not a plausible-looking guess the user has to notice
        # is wrong. Dragging from Device Explorer still sets a real
        # address explicitly (LogicView.dropEvent's own mime payload),
        # unaffected by this default.
        self.properties["Address"] = ""
        self.is_source = True

        out1 = Pin("State", Pin.DIR_OUTPUT, Pin.TYPE_BOOLEAN)
        self.outputs = [out1]

    def evaluate(self, engine=None):
        addr = self.properties.get("Address", "")
        # Force is a runtime-only override (see AUDIT_REPORT.md §5.1): it must never be
        # persisted in `properties`, or a workshop force would ride along into a saved
        # project / exported runtime and end up driving the real object.
        force_state = self.simulation_state.get("force_state", "NO FORCE")

        if force_state == "FORCE TRUE":
            self.outputs[0].value = True
        elif force_state == "FORCE FALSE":
            self.outputs[0].value = False
        else:
            if engine and hasattr(engine, 'io') and engine.io is not None:
                val = engine.io.read_digital_input(addr)
                self.outputs[0].value = val
            else:
                self.outputs[0].value = False

        self.simulation_state["sim_value"] = self.outputs[0].value

@BlockRegistry.register
class DigitalOutputBlock(BaseLogicBlock):
    PIN_DESCRIPTIONS = {"Cmd": "Stan wysyłany na fizyczne wyjście cyfrowe."}
    PROPERTY_DESCRIPTIONS = {
        "Address": "Adres fizycznego wyjścia cyfrowego (moduł ADA), np. \"ADA01.DO.1\".",
    }

    def __init__(self, type_id="output.do", default_name="DO", category="Wejścia / Wyjścia", description="Fizyczne wyjście cyfrowe (moduł ADA)."):
        super().__init__(type_id, default_name, category, description)
        self.color = "#800000" # Classic dark red
        self.width = 100
        self.height = 60
        # Task "jedno źródło listy kart": see DigitalInputBlock's own
        # comment above - no more a hardcoded default (was "ADA01.DO.1").
        self.properties["Address"] = ""

        in1 = Pin("Cmd", Pin.DIR_INPUT, Pin.TYPE_BOOLEAN)
        self.inputs = [in1]

    def evaluate(self, engine=None):
        v = self.inputs[0].value
        val = v if v is not None else False

        # Buffered by the engine and pushed to the IOProvider atomically at the
        # end of the scan (AUDIT_REPORT.md §4.2) — never written here directly.
        if engine and hasattr(engine, 'queue_digital_output'):
            addr = self.properties.get("Address", "")
            engine.queue_digital_output(addr, val)

        self.simulation_state["sim_value"] = val
