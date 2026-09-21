from shared.logic.blocks.base import BaseLogicBlock
from shared.logic.blocks.pin import Pin
from shared.logic.blocks.registry import BlockRegistry
from shared.logic.internal_bits import internal_bit_id

# The two address spaces a "Bit" property can name. Kept as constants
# rather than bare strings because the compiler, the runtime loader and
# the validator all have to agree on the spelling.
SIGNAL_KIND_INTERNAL = "internal"
SIGNAL_KIND_SYSTEM = "system"


def resolve_signal_reference(name: str, registry_entry, catalog_entry):
    """Which address space `name` belongs to, and the id to use.

    The PLATFORM CATALOG WINS. A system signal's id is a fixed contract
    every project shares; a project-defined marker is not allowed to
    shadow one, or the same name would mean different things in two
    projects. (The validator reports such a collision so the engineer
    sees it rather than silently losing their marker - it does not
    depend on this order being noticed.)

    Returns (signal_id, kind), or ("", None) when the name resolves to
    nothing at all.
    """
    if not name:
        return "", None
    if catalog_entry is not None:
        return catalog_entry.get("id", name), SIGNAL_KIND_SYSTEM
    if registry_entry is not None:
        return internal_bit_id(registry_entry), SIGNAL_KIND_INTERNAL
    return "", None


class _InternalSignalMixin:
    """Shared compile-time id resolution for the four signal blocks below
    (feat/internal-bits §2). A block's "Bit" property only NAMES a signal;
    what it names is resolved once, at compile time, because the
    ExecutionEngine/CompiledProgram deliberately never holds a live
    Project reference (AUDIT_REPORT.md §2.1) - exactly like
    AnalogInputBlock's set_range().

    Two address spaces (feat/signal-register §1.1). Originally a "Bit"
    could only name an entry of the project's own internal registry,
    whose type and retentive flag together give the M./MR./MW./MWR.<name>
    id. It may now equally name a signal from the fixed platform catalog
    (SYS.*, SEC.*, ...) - the same catalog the separate "System signal"
    block reads. The two are read and written through DIFFERENT
    IOProvider methods, so the block has to remember WHICH it resolved,
    not just the resolved string: read_internal() on a catalog id returns
    the default for ever and nothing ever says why.

    A block that was never compiled (constructed directly in a test, or
    placed on the canvas and evaluated ad hoc) falls back to resolving the
    name itself against the catalog first, then to the registry id
    computed from the block's OWN default type/retentive=False - correct
    for the common case, but not authoritative once a real registry entry
    with a non-default retentive flag exists; that is what set_signal_id()
    is for.
    """
    _SIGNAL_TYPE = "BOOL"  # overridden by the REAL-typed register blocks

    def set_signal_id(self, resolved_id: str, kind: str = SIGNAL_KIND_INTERNAL):
        """Called by the compiler (and by the runtime program loader) with
        the id AND the address space it came from. `kind` defaults to
        "internal" so every existing caller - and every .epwlogic runtime
        file written before this - keeps its previous meaning exactly."""
        self._resolved_signal_id = resolved_id
        self._resolved_signal_kind = kind

    def _signal_reference(self):
        """(id, kind) for this block right now."""
        resolved = getattr(self, "_resolved_signal_id", None)
        if resolved:
            return resolved, getattr(self, "_resolved_signal_kind", SIGNAL_KIND_INTERNAL)

        name = self.properties.get("Bit", "")
        if not name:
            return "", None
        # Uncompiled fallback: ask the catalog directly (it needs no
        # project for a fixed entry), otherwise assume the registry.
        from shared.logic import system_signals
        catalog_entry = system_signals.get_signal(name)
        if catalog_entry is not None:
            return catalog_entry["id"], SIGNAL_KIND_SYSTEM
        return internal_bit_id({"name": name, "type": self._SIGNAL_TYPE, "retentive": False}), SIGNAL_KIND_INTERNAL

    def _signal_id(self) -> str:
        """Back-compatible accessor - the id alone, kind discarded."""
        return self._signal_reference()[0]

    def _read_signal(self, engine, default):
        """Reads through whichever IOProvider method matches the address
        space this block's name resolved into."""
        signal_id, kind = self._signal_reference()
        if not signal_id or engine is None:
            return None
        io = getattr(engine, "io", None)
        if io is None:
            return None
        if kind == SIGNAL_KIND_SYSTEM:
            now_ms = engine.time.current_time_ms() if getattr(engine, "time", None) else 0
            return io.read_system_signal(signal_id, now_ms)
        return io.read_internal(signal_id, default)

    def _write_signal(self, engine, value) -> None:
        """Queues a write on the matching address space. Both queues are
        flushed atomically at end-of-scan by the engine; a system-signal
        write additionally has to be a source == "logic" catalog entry,
        which compiler/validator.py rejects at compile time rather than
        here - a block that reaches evaluate() has already been cleared."""
        signal_id, kind = self._signal_reference()
        if not signal_id or engine is None:
            return
        if kind == SIGNAL_KIND_SYSTEM:
            if hasattr(engine, "queue_system_signal_write"):
                engine.queue_system_signal_write(signal_id, value)
        elif hasattr(engine, "queue_internal_write"):
            engine.queue_internal_write(signal_id, value)


@BlockRegistry.register
class VirtualInputBlock(_InternalSignalMixin, BaseLogicBlock):
    """feat/internal-bits §2.1: reads a project-registered BOOL internal
    signal (project.settings["internal_bits"]) — its "Bit" property names
    the registry entry, picked via SignalPickerDialog (ui/signal_picker.py)
    rather than typed freehand like the old "Tag" property. type_id is
    unchanged for file back-compat; the "Tag"->"Bit" property rename is
    handled by Project's v2->v3 migration (core/project.py)."""

    PIN_DESCRIPTIONS = {"State": "Current state of the internal logic bit."}
    PROPERTY_DESCRIPTIONS = {"Bit": "Name of an internal bit (M./MR.) from the project registry, or of a readable system signal from the platform catalog."}

    def __init__(self, type_id="virtual.input", default_name="Bit input (internal)", category="Inputs / Outputs", description="Reads a BOOL signal - an internal bit (M./MR.) or a system signal from the platform catalog."):
        super().__init__(type_id, default_name, category, description)
        # Purple family, distinct from physical DI's green/DO's red/AI's
        # amber/AO's steel blue — an engineer must tell an internal signal
        # apart from a physical terminal at a glance (§2.4).
        self.color = "#663399"
        self.width = 100
        self.height = 60
        del self.properties["Tag"]  # replaced by "Bit" (§2.1) — see below
        self.properties["Bit"] = ""
        self.is_source = True

        self.outputs = [Pin("State", Pin.DIR_OUTPUT, Pin.TYPE_BOOLEAN)]

    def evaluate(self, engine=None):
        # Force is runtime-only, see AUDIT_REPORT.md §5.1 — never persisted in `properties`.
        force_state = self.simulation_state.get("force_state", "NO FORCE")

        if force_state == "FORCE TRUE":
            self.outputs[0].value = True
        elif force_state == "FORCE FALSE":
            self.outputs[0].value = False
        else:
            value = self._read_signal(engine, False)
            if value is not None:
                self.outputs[0].value = bool(value)
            elif "sim_value" in self.simulation_state:
                self.outputs[0].value = self.simulation_state["sim_value"]
            else:
                self.outputs[0].value = False


@BlockRegistry.register
class VirtualOutputBlock(_InternalSignalMixin, BaseLogicBlock):
    """feat/internal-bits §2.1: writes a project-registered BOOL internal
    signal — "Bit" property, picked via SignalPickerDialog. See
    VirtualInputBlock for the type_id/migration note."""

    PIN_DESCRIPTIONS = {"Cmd": "Value written to the internal logic bit."}
    PROPERTY_DESCRIPTIONS = {"Bit": "Name of an internal bit (M./MR.) from the project registry, or of a system signal the logic may write (source == \"logic\")."}

    def __init__(self, type_id="virtual.output", default_name="Bit output (internal)", category="Inputs / Outputs", description="Writes a BOOL signal - an internal bit (M./MR.) or a writable system signal."):
        super().__init__(type_id, default_name, category, description)
        self.color = "#4B0082"  # Purple family — see VirtualInputBlock
        self.width = 100
        self.height = 60
        del self.properties["Tag"]
        self.properties["Bit"] = ""

        self.inputs = [Pin("Cmd", Pin.DIR_INPUT, Pin.TYPE_BOOLEAN)]

    def evaluate(self, engine=None):
        v = self.inputs[0].value
        val = v if v is not None else False
        self.simulation_state["sim_value"] = val
        self._write_signal(engine, val)


@BlockRegistry.register
class InternalRegisterInputBlock(_InternalSignalMixin, BaseLogicBlock):
    """feat/internal-bits §2.2: reads a project-registered REAL internal
    signal ("register") — the analog counterpart of VirtualInputBlock."""
    _SIGNAL_TYPE = "REAL"

    PIN_DESCRIPTIONS = {"Value": "Current value of the internal analog register."}
    PROPERTY_DESCRIPTIONS = {"Bit": "Name of an internal register (MW./MWR.) from the project registry, or of a readable REAL system signal."}

    def __init__(self, type_id="internal.reg_in", default_name="Register input (internal)", category="Inputs / Outputs", description="Reads an internal analog register (an MW./MWR. signal, not tied to physical I/O)."):
        super().__init__(type_id, default_name, category, description)
        self.color = "#8A2BE2"  # Purple family — see VirtualInputBlock
        self.width = 100
        self.height = 60
        del self.properties["Tag"]
        self.properties["Bit"] = ""
        self.is_source = True

        self.outputs = [Pin("Value", Pin.DIR_OUTPUT, Pin.TYPE_FLOAT)]

    def evaluate(self, engine=None):
        value = self._read_signal(engine, 0.0)
        if value is not None:
            self.outputs[0].value = float(value)
        else:
            self.outputs[0].value = self.simulation_state.get("sim_value", 0.0)
        self.simulation_state["sim_value"] = self.outputs[0].value


@BlockRegistry.register
class InternalRegisterOutputBlock(_InternalSignalMixin, BaseLogicBlock):
    """feat/internal-bits §2.2: writes a project-registered REAL internal
    signal — the analog counterpart of VirtualOutputBlock."""
    _SIGNAL_TYPE = "REAL"

    PIN_DESCRIPTIONS = {"Value": "Value written to the internal analog register."}
    PROPERTY_DESCRIPTIONS = {"Bit": "Name of an internal register (MW./MWR.) from the project registry, or of a REAL system signal the logic may write."}

    def __init__(self, type_id="internal.reg_out", default_name="Register output (internal)", category="Inputs / Outputs", description="Writes an internal analog register (an MW./MWR. signal, not tied to physical I/O)."):
        super().__init__(type_id, default_name, category, description)
        self.color = "#6A5ACD"  # Purple family — see VirtualInputBlock
        self.width = 100
        self.height = 60
        del self.properties["Tag"]
        self.properties["Bit"] = ""

        self.inputs = [Pin("Value", Pin.DIR_INPUT, Pin.TYPE_FLOAT)]

    def evaluate(self, engine=None):
        v = self.inputs[0].value
        val = float(v) if v is not None else 0.0
        self.simulation_state["sim_value"] = val
        self._write_signal(engine, val)
