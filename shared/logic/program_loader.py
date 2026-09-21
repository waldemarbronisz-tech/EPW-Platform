"""Rebuilds a runnable CompiledProgram from an EPW_RUNTIME_LOGIC export.

Logic Studio compiles a project into a CompiledProgram in memory and, in
the same step, writes the EPW_RUNTIME_LOGIC payload (compiler/exporter.py)
that travels to the controller inside projekt.epw. The controller has the
payload but not the Project it came from - this module is the other half
of that trip: it turns the payload back into the very same CompiledProgram
the editor executed, block objects and all, using the one shared block
library (shared/logic/blocks/) both sides already run on.

What makes that faithful rather than approximate:
  * blocks are reconstructed through BlockRegistry/deserialize(), i.e. the
    identical code path the editor's own project loader uses;
  * pin UUIDs and connections come straight from the export, because
    execution_order and every wire in it are keyed by those UUIDs;
  * the three things Compiler.compile() resolves from the live Project (an
    AI block's range, a quality block's range, an internal signal's
    M./MR./MW./MWR. id) are re-resolved here from the data the exporter
    deliberately carries for exactly this purpose - the "_resolved_*"
    properties and the internal_bits registry copy.

It refuses, loudly, rather than running something subtly different from
what was compiled: a bad checksum, a newer schema, an unknown block type,
or a block whose pin count no longer matches this controller's own block
library all raise ProgramLoadError.

`cycle_delayed_reads` is deliberately NOT reconstructed: it is a
compile-time diagnostic the editor shows on its canvas (which internal
reads lag a scan behind their writer), the export does not carry it, and
ExecutionEngine never reads it.
"""
from shared.logic.blocks.pin import Pin
from shared.logic.blocks.registry import BlockRegistry
from shared.logic.engine.program import CompiledProgram
from shared.logic.internal_bits import internal_bit_id
from shared.logic.runtime_export import (
    FORMAT_MARKER,
    RUNTIME_SCHEMA_VERSION,
    verify_checksum,
)

# The block types whose "Bit" property names an entry in the internal-signal
# registry, and whose real id (M./MR./MW./MWR.<name>) therefore depends on
# that entry's type/retentive flag - never on the block itself. The same
# list Compiler.compile() resolves, for the same reason.
_INTERNAL_SIGNAL_TYPE_IDS = ("virtual.input", "virtual.output", "internal.reg_in", "internal.reg_out")

# The analog blocks whose range the compiler resolves from the project's
# own analog point list (see _resolve_analog_ranges below).
_RANGED_TYPE_IDS = ("input.ai", "analog.quality")

# Every data type a pin can carry. The exporter writes pin.data_type
# verbatim (a Pin.TYPE_* string), so a value outside this set means an
# export written by something that is not this contract's exporter - the
# constructed block's own pin type is kept instead of trusting it.
_KNOWN_PIN_TYPES = frozenset({
    Pin.TYPE_DIGITAL, Pin.TYPE_ANALOG, Pin.TYPE_INTEGER, Pin.TYPE_FLOAT,
    Pin.TYPE_BOOLEAN, Pin.TYPE_STRING, Pin.TYPE_ANY,
})


class ProgramLoadError(Exception):
    """The export cannot be turned into a program that is certainly
    equivalent to the one Logic Studio compiled. Never raised for a
    difference that is merely cosmetic - only for one that would change
    what the controller executes."""


def load_program(export: dict, verify: bool = True) -> CompiledProgram:
    """The CompiledProgram described by `export` (an EPW_RUNTIME_LOGIC
    payload, i.e. projekt.epw's "logic_runtime" section).

    `verify=False` skips ONLY the checksum comparison - every structural
    check still applies. It exists for tests that build a payload by hand;
    a controller always verifies.
    """
    if not isinstance(export, dict):
        raise ProgramLoadError("The logic export is not a JSON object.")

    fmt = export.get("format")
    if fmt != FORMAT_MARKER:
        raise ProgramLoadError(
            f"Not a logic export: expected format {FORMAT_MARKER!r}, found {fmt!r}."
        )

    schema_version = export.get("schema_version")
    if not isinstance(schema_version, int):
        raise ProgramLoadError(f"Missing or non-numeric schema_version: {schema_version!r}.")
    if schema_version > RUNTIME_SCHEMA_VERSION:
        raise ProgramLoadError(
            f"The logic was compiled against schema version {schema_version}, and this "
            f"controller understands at most {RUNTIME_SCHEMA_VERSION}. Update EPW-OS or "
            f"export the logic from a matching version of Logic Studio."
        )

    if verify and not verify_checksum(export):
        raise ProgramLoadError(
            "The logic export's checksum does not match its contents - the file was "
            "modified after it was compiled. Refusing to run it."
        )

    blocks_data = export.get("blocks")
    if not isinstance(blocks_data, dict):
        raise ProgramLoadError('The logic export has no "blocks" section.')

    execution_order = list(export.get("execution_order") or [])
    missing = [uuid for uuid in execution_order if uuid not in blocks_data]
    if missing:
        raise ProgramLoadError(
            "execution_order references blocks that are not in the export: "
            + ", ".join(missing)
        )

    blocks = [_rebuild_block(uuid, data) for uuid, data in blocks_data.items()]

    _resolve_analog_ranges(blocks)
    _resolve_internal_signal_ids(blocks, export.get("internal_bits") or [])

    return CompiledProgram(
        blocks=blocks,
        execution_order=execution_order,
        cycle_time_ms=export.get("cycle_time_ms", 100),
    )


def _rebuild_block(uuid: str, data: dict):
    if not isinstance(data, dict):
        raise ProgramLoadError(f"Block {uuid} is not a JSON object.")

    type_id = data.get("type_id")
    block_class = BlockRegistry.get_block_class(type_id)
    if block_class is None:
        raise ProgramLoadError(
            f"Block {data.get('short_id') or uuid} has type {type_id!r}, which this "
            f"controller's block library does not know. Refusing to run logic with a "
            f"block silently left out."
        )

    # The same entry point the editor's project loader uses - a block type
    # with its own deserialize() override (system.signal's pin-type sync,
    # for one) gets it here too, rather than this loader having to know
    # which types have one.
    block = block_class.deserialize({
        "uuid": uuid,
        "short_id": data.get("short_id", ""),
        "properties": data.get("properties") or {},
    })

    _restore_pins(block, block.inputs, data.get("inputs") or [], "input", uuid, type_id)
    _restore_pins(block, block.outputs, data.get("outputs") or [], "output", uuid, type_id)

    # The same last word the project loader gives a block over its own
    # intrinsic pin metadata after a restore (see base.py's
    # resync_derived_pin_metadata()).
    block.resync_derived_pin_metadata()
    return block


def _restore_pins(block, pins, pin_data_list, direction_label, uuid, type_id):
    """Pin UUIDs and connections ARE the graph: execution_order, every wire
    in it and the engine's own pin_map are all keyed by them, so they are
    restored verbatim from the export onto the pins the block class just
    constructed."""
    if len(pin_data_list) != len(pins):
        raise ProgramLoadError(
            f"Block {block.short_id or uuid} ({type_id}) was compiled with "
            f"{len(pin_data_list)} {direction_label} pin(s), but this controller's block "
            f"library builds {len(pins)}. The logic was compiled against a different "
            f"version of the block library - recompile it in Logic Studio."
        )

    for pin, pin_data in zip(pins, pin_data_list):
        pin.uuid = pin_data.get("pin_uuid", pin.uuid)
        pin.connections = list(pin_data.get("connections") or [])
        pin.disabled = bool(pin_data.get("disabled", False))
        # The exporter resolves a system-signal block's pin type against
        # the project's own catalog before writing it (see its comment on
        # system.signal) - that resolution, not a fresh block's default, is
        # what the compiled logic actually ran with.
        data_type = pin_data.get("type")
        if data_type in _KNOWN_PIN_TYPES:
            pin.data_type = data_type


def _resolve_analog_ranges(blocks):
    """The [min, max] an AI block checks its reading against, and the one a
    quality block uses when its range comes from the analog point rather
    than from its own properties. Compiler.compile() resolves both from the
    live Project; the exporter writes the result into the block's exported
    properties as "_resolved_range_min"/"_resolved_range_max" for exactly
    this, so here it is a lookup rather than a second resolution."""
    for block in blocks:
        if block.type_id not in _RANGED_TYPE_IDS or not hasattr(block, "set_range"):
            continue
        if block.type_id == "analog.quality" and \
                block.properties.get("Range Source", "Własny") != "Z punktu analogowego":
            continue
        if "_resolved_range_min" not in block.properties:
            continue
        block.set_range(
            block.properties.get("_resolved_range_min"),
            block.properties.get("_resolved_range_max"),
        )


def _resolve_internal_signal_ids(blocks, internal_bits):
    """A signal block's "Bit" property names either a registry entry or a
    signal of the fixed platform catalog (feat/signal-register §1.1), and
    the two are read/written through different IOProvider methods - so
    this resolves the KIND as well as the id.

    For a registry entry the id (M./MR./MW./MWR.<name>) is derived from
    that entry's type and retentive flag; the exporter carries a full copy
    of the registry for this - matched case-insensitively, the same rule
    DeviceModel.get_internal_bit() uses in the editor. For a catalog
    signal the id IS the name, and the catalog is part of EPW-OS itself,
    so nothing has to travel in the file for it.

    The catalog is consulted first, exactly as the compiler and the
    validator do: the resolution order is part of the contract, not an
    implementation detail each side may pick for itself."""
    from shared.logic import system_signals
    from shared.logic.blocks.virtual_io import resolve_signal_reference

    by_name = {}
    for entry in internal_bits:
        if isinstance(entry, dict):
            by_name.setdefault(entry.get("name", "").lower(), entry)

    for block in blocks:
        if block.type_id not in _INTERNAL_SIGNAL_TYPE_IDS or not hasattr(block, "set_signal_id"):
            continue
        name = block.properties.get("Bit", "") or ""
        signal_id, kind = resolve_signal_reference(
            name, by_name.get(name.lower()), system_signals.get_signal(name)
        )
        if signal_id:
            block.set_signal_id(signal_id, kind)
