"""feat/signal-register §1.1 — a system signal picked from a BIT block is
not a facade.

Offering a signal in a dialog is the easy half. The prompt's own words:
"jesli dzis umie to tylko blok system.signal, zbuduj to, nie ukrywaj
sygnalu". Before this the validator answered a system signal in a
virtual.input's "Bit" with a flat compile error - "does not exist in the
project registry" - so widening the dialog alone would have turned a
useful choice into a project that no longer builds.

What is pinned here is the whole path: the compiler resolves the name
into the right ADDRESS SPACE, the block reads/writes through the
matching IOProvider method, the runtime loader re-derives the same
answer from the exported file with no live Project to ask, and the
validator still refuses the two things that were never legal.

The distinction that makes all of this necessary: an internal marker
lives in read_internal()/write_internal(), a catalog signal in
read_system_signal()/write_system_signal(). Reading a catalog id through
read_internal() does not crash - it silently returns the default for
ever, which is the failure mode worth a test.
"""
import pytest
from PySide6.QtWidgets import QApplication

from shared.logic.blocks import register_builtin_blocks
from shared.logic.blocks.registry import BlockRegistry
from shared.logic.engine.execution import ExecutionEngine
from shared.logic.engine.io_provider import SimulationIOProvider
from shared.logic.engine.time_provider import SimulationTimeProvider
from logic_studio.compiler.core import Compiler
from logic_studio.core.device_model import DeviceModel
from logic_studio.core.project import Project

register_builtin_blocks()


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def _project(bits=()):
    p = Project()
    DeviceModel.set_ela_devices(p, ["ELA01"])
    DeviceModel.set_ada_devices(p, ["ADA01"])
    p.settings["internal_bits"] = [dict(b) for b in bits]
    return p


def _bit(name, type_="BOOL", **over):
    entry = {"name": name, "type": type_, "retentive": False,
             "description": "", "label": "", "category": ""}
    entry.update(over)
    return entry


def _block(type_id, **properties):
    block = BlockRegistry.create_block(type_id)
    for key, value in properties.items():
        block.properties[key] = value
    return block


def _run(project, io=None):
    """Compiles and runs one scan. Returns (io, compiled)."""
    compiler = Compiler(project)
    compiled = compiler.compile()
    assert compiled is not None, compiler.errors
    io = io or SimulationIOProvider()
    engine = ExecutionEngine(compiled["program"], io, SimulationTimeProvider())
    engine.start()
    engine.step()
    return io, compiled


# --- reading -----------------------------------------------------------------

def test_a_bit_input_pointed_at_a_system_signal_reads_its_real_value(app):
    project = _project()
    reader = _block("virtual.input", Bit="SYS.READY")
    sink = _block("virtual.output", Bit="ECHO")
    project.settings["internal_bits"] = [_bit("ECHO")]
    reader.outputs[0].connect(sink.inputs[0])
    project.add_block(reader)
    project.add_block(sink)

    io = SimulationIOProvider()
    io.write_system_signal("SYS.READY", True)
    _run(project, io)

    assert io.read_internal("M.ECHO", False) is True, "the catalog value never arrived"


def test_the_same_block_still_reads_an_ordinary_marker(app):
    """The second address space is an addition, not a replacement."""
    project = _project([_bit("SRC"), _bit("DST")])
    reader = _block("virtual.input", Bit="SRC")
    sink = _block("virtual.output", Bit="DST")
    reader.outputs[0].connect(sink.inputs[0])
    project.add_block(reader)
    project.add_block(sink)

    io = SimulationIOProvider()
    io.write_internal("M.SRC", True)
    _run(project, io)

    assert io.read_internal("M.DST", False) is True


def test_a_register_input_reads_a_real_system_signal(app):
    project = _project([_bit("SCAN", "REAL")])
    reader = _block("internal.reg_in", Bit="SYS.SCAN_TIME")
    sink = _block("internal.reg_out", Bit="SCAN")
    reader.outputs[0].connect(sink.inputs[0])
    project.add_block(reader)
    project.add_block(sink)

    io = SimulationIOProvider()
    io.scan_time_ms = 42.0
    _run(project, io)

    assert io.read_internal("MW.SCAN", 0.0) == 42.0


# --- writing -----------------------------------------------------------------

def test_a_bit_output_pointed_at_a_command_writes_the_system_signal(app):
    """And writes it into the SYSTEM image, not into the internal one -
    a value in the wrong image is a value the runtime never acts on."""
    project = _project()
    source = _block("const.true")
    writer = _block("virtual.output", Bit="REQ.SEC.ARM_ALL")
    source.outputs[0].connect(writer.inputs[0])
    project.add_block(source)
    project.add_block(writer)

    io, _ = _run(project)

    assert io.read_system_signal("REQ.SEC.ARM_ALL") is True
    assert "REQ.SEC.ARM_ALL" not in io.internal_image, "written into the wrong address space"


# --- the validator still refuses what was never legal ------------------------

def test_writing_a_signal_the_runtime_owns_is_a_compile_error(app):
    project = _project()
    source = _block("const.true")
    writer = _block("virtual.output", Bit="SEC.SYSTEM.ARMED")   # source == "runtime"
    source.outputs[0].connect(writer.inputs[0])
    project.add_block(source)
    project.add_block(writer)

    compiler = Compiler(project)

    assert compiler.compile() is None
    assert any("cannot be written from the logic" in e for e in compiler.errors), compiler.errors


def test_a_name_in_neither_place_still_names_both_places_in_the_error(app):
    """The old message said "project registry" only. A typo in a catalog
    id would send the engineer looking in the wrong window."""
    project = _project()
    reader = _block("virtual.input", Bit="SYS.NIE_MA")
    project.add_block(reader)

    compiler = Compiler(project)
    compiler.compile()

    message = " ".join(compiler.errors)
    assert "project registry" in message and "system signal catalog" in message, message


def test_a_type_mismatch_against_the_catalog_is_caught(app):
    """SYS.SCAN_TIME is REAL; a BOOL block must not silently take it."""
    project = _project()
    reader = _block("virtual.input", Bit="SYS.SCAN_TIME")
    project.add_block(reader)

    compiler = Compiler(project)
    compiler.compile()

    assert any("SYS.SCAN_TIME" in e and "BOOL" in e for e in compiler.errors), compiler.errors


def test_two_blocks_writing_the_same_command_is_an_error(app):
    """The single-writer rule the registry already had - a command with
    two owners is the same defect, and was unguarded for catalog ids."""
    project = _project()
    for index in range(2):
        source = _block("const.true")
        writer = _block("virtual.output", Bit="REQ.SEC.DISARM_ALL")
        source.outputs[0].connect(writer.inputs[0])
        project.add_block(source)
        project.add_block(writer)

    compiler = Compiler(project)
    compiler.compile()

    assert any("more than one writing block" in e and "REQ.SEC.DISARM_ALL" in e
               for e in compiler.errors), compiler.errors


def test_a_marker_named_after_a_catalog_signal_is_rejected_not_shadowed(app):
    """Resolution gives the catalog priority, so such a marker can never
    be reached. Silently is the wrong way to tell somebody that."""
    project = _project([_bit("SYS.READY")])
    project.add_block(_block("const.true"))

    compiler = Compiler(project)
    compiler.compile()

    assert any("same name as a system signal" in e for e in compiler.errors), compiler.errors


# --- the runtime reaches the same answer with no editor present --------------

def test_the_exported_file_resolves_to_the_same_two_address_spaces(app):
    """EPW-OS has no Project and no DeviceModel. It re-derives the kind
    from the exported file plus its own copy of the catalog - if that
    disagreed with the compiler, the controller would run a different
    program than the one that was verified."""
    from shared.logic.program_loader import load_program

    project = _project([_bit("MARKER")])
    from_system = _block("virtual.input", Bit="SYS.READY")
    to_marker = _block("virtual.output", Bit="MARKER")
    from_system.outputs[0].connect(to_marker.inputs[0])
    project.add_block(from_system)
    project.add_block(to_marker)

    compiler = Compiler(project)
    assert compiler.compile() is not None, compiler.errors
    from logic_studio.compiler.exporter import Exporter
    payload = Exporter(project, compiler.last_execution_order).export()

    program = load_program(payload)
    by_bit = {b.properties.get("Bit"): b for b in program.blocks
              if b.type_id in ("virtual.input", "virtual.output")}

    assert by_bit["SYS.READY"]._signal_reference() == ("SYS.READY", "system")
    assert by_bit["MARKER"]._signal_reference() == ("M.MARKER", "internal")


def test_the_loaded_program_actually_reads_the_system_signal(app):
    """The end of the whole chain: run what the controller would run."""
    from shared.logic.program_loader import load_program
    from logic_studio.compiler.exporter import Exporter

    project = _project([_bit("ECHO")])
    reader = _block("virtual.input", Bit="SYS.READY")
    sink = _block("virtual.output", Bit="ECHO")
    reader.outputs[0].connect(sink.inputs[0])
    project.add_block(reader)
    project.add_block(sink)

    compiler = Compiler(project)
    assert compiler.compile() is not None, compiler.errors
    program = load_program(Exporter(project, compiler.last_execution_order).export())

    io = SimulationIOProvider()
    io.write_system_signal("SYS.READY", True)
    engine = ExecutionEngine(program, io, SimulationTimeProvider())
    engine.start()
    engine.step()

    assert io.read_internal("M.ECHO", False) is True


# --- the blocks that left the library still work -----------------------------

def test_a_project_saved_with_the_old_system_signal_block_still_runs(app):
    """Owner's correction to 1.4: system.signal is no longer OFFERED, but
    projects already contain it. Hidden is not deleted - it must open,
    compile and behave exactly as before, and nothing may rewrite it into
    a virtual.input behind the engineer's back."""
    project = _project([_bit("ECHO")])
    reader = _block("system.signal", **{"Sygnał": "SYS.READY"})
    sink = _block("virtual.output", Bit="ECHO")
    reader.outputs[0].connect(sink.inputs[0])
    project.add_block(reader)
    project.add_block(sink)

    io = SimulationIOProvider()
    io.write_system_signal("SYS.READY", True)
    _run(project, io)

    assert io.read_internal("M.ECHO", False) is True
    assert reader.type_id == "system.signal", "the block was silently converted"


def test_the_old_output_block_still_issues_its_command(app):
    project = _project()
    source = _block("const.true")
    writer = _block("system.signal_out", **{"Sygnał": "REQ.SEC.ARM_ALL"})
    source.outputs[0].connect(writer.inputs[0])
    project.add_block(source)
    project.add_block(writer)

    io, _ = _run(project)

    assert io.read_system_signal("REQ.SEC.ARM_ALL") is True


def test_the_four_blocks_that_replaced_them_are_the_ones_offered():
    """The point of hiding them: one way to reach a signal, not two."""
    from shared.logic.blocks.system_signals import LEGACY_LIBRARY_HIDDEN
    from logic_studio.ui.panels.property_grid import _SIGNAL_PICKER_TARGETS

    replacements = {type_id for type_id, _key in _SIGNAL_PICKER_TARGETS}

    assert {"virtual.input", "virtual.output",
            "internal.reg_in", "internal.reg_out"} <= replacements
    assert LEGACY_LIBRARY_HIDDEN <= replacements, (
        "the hidden blocks lost their picker too - an old project could no "
        "longer even be edited")
