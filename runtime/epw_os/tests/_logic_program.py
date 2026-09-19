"""Builds REAL EPW_RUNTIME_LOGIC payloads for the runtime suites.

The old tests here used a stand-in dict ({"format": "EPW_RUNTIME_LOGIC",
"blocks": [{"id": "b"}]}) because the runtime only ever checked the
format marker. Now that the controller actually executes the program,
such a document is correctly refused - so these helpers assemble a
payload out of the SAME block classes Logic Studio compiles (shared/
logic/blocks/) and sign it with the SAME checksum function the exporter
uses (shared/logic/runtime_export.py). Nothing here re-implements a
block, the graph or the checksum rule.

The other direction - a payload produced by Logic Studio's own Exporter,
executed by the controller's loader - is covered end to end in
shared/tests/test_logic_execution_contract.py.
"""
import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parents[3])
if _REPO_ROOT not in sys.path:
    sys.path.append(_REPO_ROOT)

from shared.logic.blocks import register_builtin_blocks
from shared.logic.blocks.registry import BlockRegistry
from shared.logic.runtime_export import FORMAT_MARKER, RUNTIME_SCHEMA_VERSION, compute_checksum

register_builtin_blocks()


def make_block(type_id: str, **properties):
    """A live block object of `type_id` with `properties` applied - the
    same object the controller will rebuild from the payload."""
    block = BlockRegistry.create_block(type_id)
    assert block is not None, f"unknown block type {type_id!r}"
    for key, value in properties.items():
        block.properties[key] = value
    return block


def connect(source_block, dest_block, source_index: int = 0, dest_index: int = 0):
    """Wires an output pin to an input pin through Pin.connect() itself,
    so the uuid bookkeeping is the library's, not this helper's."""
    assert source_block.outputs[source_index].connect(dest_block.inputs[dest_index])


def export(blocks, execution_order=None, cycle_time_ms: int = 20, **overrides) -> dict:
    """The payload. `execution_order` defaults to the order `blocks` are
    given in, which is what a linear source -> logic -> output chain
    compiles to anyway."""
    payload = {
        "format": FORMAT_MARKER,
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "source_version": "1.0",
        "cycle_time_ms": cycle_time_ms,
        "execution_order": [b.uuid for b in blocks] if execution_order is None else execution_order,
        "blocks": {b.uuid: _block_entry(b) for b in blocks},
        "generated_at": "2026-01-01T00:00:00+00:00",
        "generated_by": "runtime test helper",
        "project_name": "runtime test",
        "block_count": len(blocks),
        "contains_forced_io": False,
        "contains_disabled_blocks": False,
        "analog_points": [],
        "internal_bits": [],
        "system_catalog_version": "1.1.0",
        "io_labels": {},
    }
    payload.update(overrides)
    payload["checksum"] = compute_checksum(payload)
    return payload


def _block_entry(block) -> dict:
    return {
        "type_id": block.type_id,
        "short_id": block.short_id,
        "category": block.category,
        "inputs": [_pin(p, with_disabled=True) for p in block.inputs],
        "outputs": [_pin(p) for p in block.outputs],
        "properties": dict(block.properties),
    }


def _pin(pin, with_disabled: bool = False) -> dict:
    entry = {"pin_uuid": pin.uuid, "name": pin.name, "type": pin.data_type,
             "connections": list(pin.connections)}
    if with_disabled:
        entry["disabled"] = pin.disabled
    return entry


def di_to_do(di_address: str = "ELA01.DI.1", do_address: str = "ADA01.DO.1",
             cycle_time_ms: int = 20) -> dict:
    """The smallest real program: one digital input wired straight to one
    digital output."""
    di = make_block("input.di", Address=di_address)
    do = make_block("output.do", Address=do_address)
    connect(di, do)
    return export([di, do], cycle_time_ms=cycle_time_ms)


def ai_to_ao(ai_address: str = "ELA01.AI.1", ao_address: str = "ADA01.AO.1",
             cycle_time_ms: int = 20, range_min=0.0, range_max=100.0) -> dict:
    """The analog counterpart, with the analog point range resolved into
    the AI block's properties exactly as the exporter resolves it."""
    ai = make_block("input.ai", Address=ai_address)
    ai.properties["_resolved_range_min"] = range_min
    ai.properties["_resolved_range_max"] = range_max
    ao = make_block("output.ao", Address=ao_address)
    connect(ai, ao)
    return export([ai, ao], cycle_time_ms=cycle_time_ms,
                  analog_points=[{"tag": ai_address, "min": range_min, "max": range_max, "unit": "%"}])


class AllowAllLogicEngine:
    """The stand-in seven tests used to declare for themselves, one copy
    each: a logic engine that permits every command, so a test about the
    safety kernel/Training Mode/command routing is not also a test of
    whatever the logic happens to say.

    One shared copy because it has to mirror the REAL LogicEngine surface
    EPWCore and CommandManager use - all seven private copies broke at
    once the day the engine gained a lifecycle (EPWCore.shutdown() calls
    stop()), which is exactly what a single definition prevents next
    time.
    """

    is_running = False
    last_error = ""

    def validate_command(self, target, action):
        return True, []

    def is_configured(self) -> bool:
        return False

    def attach_io(self, io_provider):
        pass

    def load_program(self, filepath) -> bool:
        return True

    def load_program_data(self, data) -> bool:
        return True

    def driven_outputs(self):
        return frozenset()

    def start(self) -> bool:
        return True

    def stop(self):
        pass
