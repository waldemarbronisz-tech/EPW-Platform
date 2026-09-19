"""THE proof that the controller runs what Logic Studio compiled.

Logic Studio compiles a project into a CompiledProgram it simulates on
the canvas, and writes an EPW_RUNTIME_LOGIC export that travels to the
controller inside projekt.epw. The controller rebuilds a CompiledProgram
from that export alone (shared/logic/program_loader.py) - it never sees
the Project.

Two programs, built by two different paths, are only "the same program"
if they behave the same. This test does not compare their structure and
call that good enough: it RUNS both, scan for scan, against the same
inputs, and asserts every output matches - the editor's own program and
the one the controller reconstructed, on the same real example project
(studio/logic/examples/*.epwlogic).

The rest of the file covers what the loader must REFUSE, because
refusing is the whole reason the export carries a checksum: a controller
that runs a program subtly different from the compiled one is worse than
a controller that runs nothing and says why.
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _extra_root in (_REPO_ROOT / "studio" / "logic",):
    _extra_root_str = str(_extra_root)
    if _extra_root_str not in sys.path:
        sys.path.insert(0, _extra_root_str)

import pytest

from shared.logic.blocks import register_builtin_blocks
from shared.logic.engine.execution import ExecutionEngine
from shared.logic.engine.io_provider import SimulationIOProvider
from shared.logic.engine.time_provider import SimulationTimeProvider
from shared.logic.internal_bits import internal_bit_id
from shared.logic.program_loader import ProgramLoadError, load_program
from shared.logic.runtime_export import compute_checksum

EXAMPLES = _REPO_ROOT / "studio" / "logic" / "examples"

register_builtin_blocks()


def _compile(path: Path):
    """(export payload, the editor's own CompiledProgram) for a real
    example project, through Logic Studio's own compiler - not a
    hand-built stand-in."""
    from logic_studio.compiler.core import Compiler
    from logic_studio.core.project import Project

    project = Project.load_from_file(str(path))
    compiler = Compiler(project)
    compiled = compiler.compile()
    assert compiled is not None, f"{path.name} did not compile: {compiler.errors}"
    # compile() attaches the live CompiledProgram and a diagnostic list on
    # top of the export payload; the controller only ever gets the rest.
    export = {k: v for k, v in compiled.items() if k not in ("program", "cycle_delayed_reads")}
    return export, compiled["program"]


def _run(program, digital_inputs, scans: int = 5):
    io = SimulationIOProvider()
    for address, value in digital_inputs.items():
        io.set_digital_input(address, value)
    engine = ExecutionEngine(program, io, SimulationTimeProvider())
    engine.start()
    for _ in range(scans):
        engine.step()
    return io.output_image


@pytest.mark.parametrize("example", sorted(p.name for p in EXAMPLES.glob("*.epwlogic")))
@pytest.mark.parametrize("di_state", [False, True])
def test_the_controller_reproduces_the_editors_own_run(example, di_state):
    export, editor_program = _compile(EXAMPLES / example)
    controller_program = load_program(export)

    # Every digital input address the program reads, driven together -
    # enough to make a gate switch in either direction on the examples,
    # without this test needing to know what each one does.
    addresses = {
        block.properties.get("Address", "")
        for block in controller_program.blocks
        if block.type_id == "input.di" and block.properties.get("Address")
    }
    inputs = {address: di_state for address in addresses}

    editor_outputs = _run(editor_program, inputs)
    controller_outputs = _run(controller_program, inputs)
    assert controller_outputs == editor_outputs


def test_the_controller_rebuilds_the_same_graph():
    export, editor_program = _compile(EXAMPLES / "EPW_LOGIC_FINAL_UI_TEST.epwlogic")
    program = load_program(export)

    assert program.execution_order == editor_program.execution_order
    assert program.cycle_time_ms == editor_program.cycle_time_ms
    assert sorted(program.block_map) == sorted(editor_program.block_map)
    # The pin UUIDs ARE the wiring: the engine resolves every connection
    # through them, so a rebuilt program whose pin map does not match is
    # a different circuit however similar it looks.
    assert sorted(program.pin_map) == sorted(editor_program.pin_map)
    for uuid, block in program.block_map.items():
        original = editor_program.block_map[uuid]
        assert block.type_id == original.type_id
        assert [p.connections for p in block.inputs] == [p.connections for p in original.inputs]


# --- what the loader must refuse ---------------------------------------------

def _minimal_export(**overrides):
    from shared.logic.blocks.registry import BlockRegistry
    di = BlockRegistry.create_block("input.di")
    di.properties["Address"] = "ELA01.DI.1"
    do = BlockRegistry.create_block("output.do")
    do.properties["Address"] = "ADA01.DO.1"
    di.outputs[0].connect(do.inputs[0])

    def entry(block):
        return {
            "type_id": block.type_id, "short_id": block.short_id, "category": block.category,
            "inputs": [{"pin_uuid": p.uuid, "name": p.name, "type": p.data_type,
                        "connections": list(p.connections), "disabled": p.disabled} for p in block.inputs],
            "outputs": [{"pin_uuid": p.uuid, "name": p.name, "type": p.data_type,
                         "connections": list(p.connections)} for p in block.outputs],
            "properties": dict(block.properties),
        }

    payload = {
        "format": "EPW_RUNTIME_LOGIC", "schema_version": 4, "source_version": "1.0",
        "cycle_time_ms": 100, "execution_order": [di.uuid, do.uuid],
        "blocks": {di.uuid: entry(di), do.uuid: entry(do)},
        "generated_at": "2026-01-01T00:00:00+00:00", "generated_by": "test", "project_name": "test",
        "block_count": 2, "contains_forced_io": False, "contains_disabled_blocks": False,
        "analog_points": [], "internal_bits": [], "system_catalog_version": "1.1.0", "io_labels": {},
    }
    payload.update(overrides)
    payload["checksum"] = compute_checksum(payload)
    return payload


def test_a_payload_altered_after_compilation_is_refused():
    export = _minimal_export()
    export["cycle_time_ms"] = 10  # checksum no longer matches
    with pytest.raises(ProgramLoadError, match="checksum"):
        load_program(export)
    # Structural checks still apply with verification off - what the flag
    # skips is the checksum comparison alone.
    assert load_program(export, verify=False).cycle_time_ms == 10


def test_a_newer_schema_is_refused_rather_than_guessed_at():
    with pytest.raises(ProgramLoadError, match="schema version"):
        load_program(_minimal_export(schema_version=99))
    with pytest.raises(ProgramLoadError, match="format"):
        load_program({"format": "EPW_LOGIC", "schema_version": 4})


def test_an_unknown_block_type_is_refused_not_skipped():
    export = _minimal_export()
    uuid = export["execution_order"][0]
    export["blocks"][uuid]["type_id"] = "input.invented_later"
    export["checksum"] = compute_checksum(export)
    with pytest.raises(ProgramLoadError, match="block library does not know"):
        load_program(export)


def test_a_block_whose_pins_no_longer_match_the_library_is_refused():
    """A block type that gained or lost a pin since the export was made
    would leave a connection pointing at nothing - the graph silently
    changes shape. Refused instead."""
    export = _minimal_export()
    uuid = export["execution_order"][1]
    export["blocks"][uuid]["inputs"].append(dict(export["blocks"][uuid]["inputs"][0]))
    export["checksum"] = compute_checksum(export)
    with pytest.raises(ProgramLoadError, match="pin"):
        load_program(export)


def test_an_internal_signals_real_id_is_resolved_from_the_exported_registry():
    """A block's "Bit" property only NAMES a registry entry; the id it
    reads/writes (M./MR./MW./MWR.<name>) depends on that entry's type and
    retentive flag, which live in the registry the exporter carries."""
    from shared.logic.blocks.registry import BlockRegistry
    reader = BlockRegistry.create_block("virtual.input")
    reader.properties["Bit"] = "blokada_zs"  # case-insensitive, like the editor

    export = _minimal_export(internal_bits=[{"name": "BLOKADA_ZS", "type": "BOOL", "retentive": True}])
    export["blocks"][reader.uuid] = {
        "type_id": "virtual.input", "short_id": "v1", "category": reader.category,
        "inputs": [], "outputs": [{"pin_uuid": reader.outputs[0].uuid, "name": reader.outputs[0].name,
                                   "type": reader.outputs[0].data_type, "connections": []}],
        "properties": dict(reader.properties),
    }
    export["execution_order"].append(reader.uuid)
    export["checksum"] = compute_checksum(export)

    program = load_program(export)
    rebuilt = program.get_block(reader.uuid)
    assert rebuilt._signal_id() == internal_bit_id({"name": "BLOKADA_ZS", "type": "BOOL", "retentive": True})
    assert rebuilt._signal_id() == "MR.BLOKADA_ZS"


def test_an_analog_inputs_range_survives_the_trip():
    """The compiler resolves an AI block's [min, max] from the project's
    analog point list; the controller has no project, so the exporter
    writes the resolved values into the block's properties."""
    from shared.logic.blocks.registry import BlockRegistry
    ai = BlockRegistry.create_block("input.ai")
    ai.properties["Address"] = "ELA01.AI.1"
    ai.properties["_resolved_range_min"] = -10.0
    ai.properties["_resolved_range_max"] = 110.0

    export = _minimal_export()
    export["blocks"][ai.uuid] = {
        "type_id": "input.ai", "short_id": "a1", "category": ai.category,
        "inputs": [], "outputs": [{"pin_uuid": p.uuid, "name": p.name, "type": p.data_type,
                                   "connections": []} for p in ai.outputs],
        "properties": dict(ai.properties),
    }
    export["execution_order"].append(ai.uuid)
    export["checksum"] = compute_checksum(export)

    rebuilt = load_program(export).get_block(ai.uuid)
    assert (rebuilt._range_min, rebuilt._range_max) == (-10.0, 110.0)
