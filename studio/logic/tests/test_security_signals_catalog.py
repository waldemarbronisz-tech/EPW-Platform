"""feat/security-signals — the EPW-OS alarm/intrusion subsystem's fixed
part: catalog 1.1.0 (SEC.STATE/ALARM/OUT/CMD), the first source=="logic"
system signals, system.signal_out (the write direction), the compiler
validation around it, and the "Minimalny poziom dostępu" access-level gate
on safety_relevant writes. See ARCHITECTURE.md "System alarmowy".
"""
import re

import pytest
from PySide6.QtWidgets import QApplication

from shared.logic.blocks import register_builtin_blocks
from shared.logic.blocks.registry import BlockRegistry
from shared.logic.blocks.pin import Pin
from logic_studio.core.project import Project
from shared.logic import system_signals
from logic_studio.compiler.core import Compiler
from logic_studio.compiler.exporter import Exporter, verify_checksum

register_builtin_blocks()


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ---- §4.1: catalog correctness (guards future entries too) -----------------

def test_the_catalog_declares_a_version():
    """EPW-OS refuses logic compiled against a catalog newer than it
    understands, so the version has to exist and be comparable - a
    literal pinned here would only mean "somebody edited this test"."""
    import re
    version = system_signals.get_catalog_version()
    assert re.fullmatch(r"\d+\.\d+\.\d+", version or ""), version

def test_every_catalog_entry_has_the_required_fields():
    required = {"id", "description", "label", "type", "source", "safety_relevant",
                # feat/signal-register 2.2: whether this controller really
                # answers for the signal - Studio shows it, and the
                # runtime's own suite checks the claim.
                "runtime"}
    for sig in system_signals.get_all_signals():
        missing = required - set(sig.keys())
        assert not missing, f"{sig.get('id', '?')} missing fields: {missing}"

def test_catalog_ids_are_unique():
    ids = [s["id"] for s in system_signals.get_all_signals()]
    assert len(ids) == len(set(ids)), "duplicate id(s) in the catalog"

def test_catalog_types_are_from_the_allowed_set():
    allowed = {"BOOL", "REAL"}
    for sig in system_signals.get_all_signals():
        assert sig["type"] in allowed, f"{sig['id']}: unexpected type {sig['type']!r}"

def test_catalog_sources_are_from_the_allowed_set():
    allowed = {"runtime", "logic"}
    for sig in system_signals.get_all_signals():
        assert sig["source"] in allowed, f"{sig['id']}: unexpected source {sig['source']!r}"

def test_catalog_version_is_valid_semver():
    assert re.match(r"^\d+\.\d+\.\d+$", system_signals.get_catalog_version())

def test_requests_are_the_only_logic_sourced_signals():
    """The invariant behind the direction rule (register Z2): a signal
    the logic may WRITE is a request - REQ.* - and every request is
    such a signal. A source flipped on an unrelated signal, or a request
    filed under source == "runtime", breaks one half or the other."""
    signals = system_signals.get_all_signals()
    logic_sourced = {s["id"] for s in signals if s["source"] == "logic"}
    requests = {s["id"] for s in signals if s["id"].startswith("REQ.")}
    assert logic_sourced == requests
    assert {"REQ.SEC.ARM_ALL", "REQ.SEC.ARM_ALL_PARTIAL", "REQ.SEC.DISARM_ALL",
            "REQ.SEC.CLEAR_ALARM_MEMORY", "REQ.SEC.SILENCE"} <= logic_sourced


# ---- §4.2: write direction ---------------------------------------------------

def _out_block(signal_id, access_level=None):
    b = BlockRegistry.create_block("system.signal_out")
    b.update_property("Sygnał", signal_id)
    if access_level is not None:
        b.update_property("Minimalny poziom dostępu", access_level)
    return b

def _in_block(signal_id):
    b = BlockRegistry.create_block("system.signal")
    b.update_property("Sygnał", signal_id)
    return b

def test_writing_a_runtime_sourced_signal_is_a_compile_error():
    p = Project()
    p.add_block(_out_block("SEC.SYSTEM.ARMED"))  # source == "runtime"

    res = Compiler(p).compile()

    assert res is None

def test_writing_a_logic_sourced_signal_compiles():
    p = Project()
    p.add_block(_out_block("REQ.SEC.ARM_ALL"))

    c = Compiler(p)
    res = c.compile()

    assert res is not None, f"Compile failed: {c.errors}"

def test_reading_a_request_is_a_compile_error():
    """Owner's correction: a request is not a state.

    This test used to assert the opposite - that echoing REQ.SEC.ARM_ALL
    onto an indicator was legal. It reads plausibly and it is wrong: the
    controller does not maintain a value for a request, so a schematic
    built on reading one waits for a bit that only ever moves when that
    same program writes it, one scan late, and never at all after a
    restart. The dialog no longer offers it either."""
    p = Project()
    p.add_block(_in_block("REQ.SEC.ARM_ALL"))

    c = Compiler(p)

    assert c.compile() is None
    assert any("REQ.SEC.ARM_ALL" in e and "cannot be read" in e for e in c.errors), c.errors


def test_the_refusal_is_decided_by_the_source_field_not_by_the_name():
    """"REQ." is a naming convention; `source` is the fact. A future
    logic-owned signal called something else has to be refused too.

    Runs over the catalogue EXPANDED against a project with a zone, so
    the per-zone requests are covered as the concrete ids an engineer
    would actually write - a raw pattern is not a signal any project
    contains, and feeding one in tests the unrecognised-id path instead
    of the direction rule."""
    from shared.logic import system_signals

    installation = Project()
    installation.external_zones = [{"id": "PARTER", "name": "Parter"}]
    logic_owned = [s for s in system_signals.get_all_signals(installation)
                   if s.get("source") == "logic"]
    assert len(logic_owned) > 5, "the catalogue offers the logic almost nothing to write"

    for signal in logic_owned:
        p = Project()
        p.external_zones = [{"id": "PARTER", "name": "Parter"}]
        p.add_block(_in_block(signal["id"]))
        c = Compiler(p)
        assert c.compile() is None, signal["id"]


def test_a_runtime_state_is_still_perfectly_readable():
    """The correction must not have closed the door on the normal case."""
    p = Project()
    p.add_block(_in_block("SEC.SYSTEM.ARMED"))

    c = Compiler(p)

    assert c.compile() is not None, c.errors

def test_a_request_is_flushed_to_the_io_provider_at_the_end_of_the_scan():
    """The buffering half of what used to be a round-trip test.

    Its other half - reading the request back with a block on the next
    scan - is gone with the owner's correction, and the test says so
    rather than quietly shrinking: nothing may read a request any more,
    so there is no block to read it with. What still matters, and is
    still checked, is that the write does not reach the IOProvider
    mid-scan: every write lands together, at the end, so two blocks
    reading the world in one scan never see a half-applied picture."""
    from shared.logic.engine.execution import ExecutionEngine
    from shared.logic.engine.io_provider import SimulationIOProvider
    from shared.logic.engine.time_provider import SystemTimeProvider

    p = Project()
    out = _out_block("REQ.SEC.ARM_ALL")
    p.add_block(out)

    c = Compiler(p)
    res = c.compile()
    assert res is not None, f"Compile failed: {c.errors}"

    eng = ExecutionEngine(res["program"], SimulationIOProvider(), SystemTimeProvider())
    eng.start()
    out_clone = res["program"].block_map[out.uuid]
    out_clone.inputs[0].value = True

    assert eng.io.system_signal_overrides.get("REQ.SEC.ARM_ALL") is None
    eng.step()
    assert eng.io.system_signal_overrides.get("REQ.SEC.ARM_ALL") is True

def test_writing_an_unrecognized_system_signal_is_a_compile_error():
    p = Project()
    b = BlockRegistry.create_block("system.signal_out")
    b.properties["Sygnał"] = "SEC.NOT_A_REAL_SIGNAL"  # bypass update_property's own resync, matches a corrupted file
    p.add_block(b)

    res = Compiler(p).compile()

    assert res is None

def test_unconfigured_output_block_does_not_error():
    """An output block with no signal picked yet — mid-edit — must not
    fail the compile the way an addressless DI/DO block does not either."""
    p = Project()
    p.add_block(BlockRegistry.create_block("system.signal_out"))

    c = Compiler(p)
    res = c.compile()

    assert res is not None, f"Compile failed: {c.errors}"

def test_unused_logic_signal_is_a_warning_not_an_error():
    p = Project()
    p.add_block(_out_block("REQ.SEC.ARM_ALL"))  # every OTHER CMD_* signal is unused

    c = Compiler(p)
    res = c.compile()

    assert res is not None, f"Compile failed: {c.errors}"
    assert any("REQ.SEC.CLEAR_ALARM_MEMORY" in w and "is not used" in w for w in c.warnings)

def test_the_unused_warning_does_not_confuse_one_request_with_another():
    """This test used to say that a request only ever READ still counts
    as used. Reading one is a compile error now (owner's correction), so
    that premise is gone - but the half worth keeping is not: one
    request's id is a PREFIX of another's, and a substring check would
    silently mark REQ.SEC.ARM_ALL_PARTIAL as used the moment anything
    wrote REQ.SEC.ARM_ALL."""
    p = Project()
    p.add_block(_out_block("REQ.SEC.ARM_ALL"))

    c = Compiler(p)
    res = c.compile()

    assert res is not None, f"Compile failed: {c.errors}"
    assert not any("'REQ.SEC.ARM_ALL'" in w and "is not used" in w for w in c.warnings)
    assert any("'REQ.SEC.ARM_ALL_PARTIAL'" in w and "is not used" in w for w in c.warnings), c.warnings


# ---- §4.3: two writers ------------------------------------------------------

def test_two_writers_for_the_same_command_is_a_compile_error_naming_both():
    p = Project()
    o1 = _out_block("REQ.SEC.ARM_ALL")
    o2 = _out_block("REQ.SEC.ARM_ALL")
    p.add_block(o1)
    p.add_block(o2)

    c = Compiler(p)
    res = c.compile()

    assert res is None
    matching = [e for e in c.errors if "REQ.SEC.ARM_ALL" in e and "more than one" in e]
    assert len(matching) == 1
    assert o1.short_id in matching[0]
    assert o2.short_id in matching[0]


# ---- §4.4: access level ------------------------------------------------------

def test_safety_relevant_write_with_no_access_level_warns():
    p = Project()
    p.add_block(_out_block("REQ.SEC.DISARM_ALL", access_level="Brak"))

    c = Compiler(p)
    res = c.compile()

    assert res is not None, f"Compile failed: {c.errors}"
    assert any("critical signal" in w and "REQ.SEC.DISARM_ALL" in w for w in c.warnings)

def test_safety_relevant_write_with_engineer_level_does_not_warn():
    p = Project()
    p.add_block(_out_block("REQ.SEC.DISARM_ALL", access_level="Engineer"))

    c = Compiler(p)
    res = c.compile()

    assert res is not None, f"Compile failed: {c.errors}"
    assert not any("critical signal" in w for w in c.warnings)

def test_non_safety_write_with_no_access_level_does_not_warn():
    p = Project()
    p.add_block(_out_block("REQ.SEC.ARM_ALL", access_level="Brak"))

    c = Compiler(p)
    res = c.compile()

    assert res is not None, f"Compile failed: {c.errors}"
    assert not any("critical signal" in w for w in c.warnings)

def test_access_level_defaults_to_engineer_for_a_safety_relevant_signal():
    b = BlockRegistry.create_block("system.signal_out")
    b.update_property("Sygnał", "REQ.SEC.DISARM_ALL")
    assert b.properties["Minimalny poziom dostępu"] == "Engineer"

def test_access_level_defaults_to_brak_for_a_non_safety_signal():
    b = BlockRegistry.create_block("system.signal_out")
    b.update_property("Sygnał", "REQ.SEC.ARM_ALL")
    assert b.properties["Minimalny poziom dostępu"] == "Brak"

def test_manual_access_level_override_survives_reselecting_the_same_signal():
    """§3.1's default only applies when "Sygnał" actually CHANGES value —
    reassigning the same value it already has must not clobber a manual
    override (update_property() itself is a no-op path many callers use
    defensively; the property grid's own §5.4 already skips the commit
    when old==new, but the block-level guarantee should hold regardless)."""
    b = BlockRegistry.create_block("system.signal_out")
    b.update_property("Sygnał", "REQ.SEC.DISARM_ALL")
    assert b.properties["Minimalny poziom dostępu"] == "Engineer"
    b.update_property("Minimalny poziom dostępu", "User")
    assert b.properties["Minimalny poziom dostępu"] == "User"


# ---- §4.5: export --------------------------------------------------------

def test_export_carries_the_version_the_catalog_actually_declares():
    """The real contract: not a particular number, but the SAME number -
    a runtime file claiming a version the catalog never had is how the
    controller's compatibility check reaches the wrong conclusion."""
    p = Project()
    c = Compiler(p)
    res = c.compile()
    data = Exporter(p, res["program"].execution_order).export()
    assert data["system_catalog_version"] == system_signals.get_catalog_version()

def test_export_checksum_covers_the_catalog_version_field():
    p = Project()
    c = Compiler(p)
    res = c.compile()
    data = Exporter(p, res["program"].execution_order).export()
    assert verify_checksum(data) is True

    tampered = dict(data)
    tampered["system_catalog_version"] = "9.9.9"
    assert verify_checksum(tampered) is False

def test_export_carries_the_access_level_property():
    p = Project()
    o = _out_block("REQ.SEC.DISARM_ALL")
    p.add_block(o)
    c = Compiler(p)
    res = c.compile()
    data = Exporter(p, res["program"].execution_order).export()
    assert data["blocks"][o.uuid]["properties"]["Minimalny poziom dostępu"] == "Engineer"


# ---- §4.6: backward compatibility -------------------------------------------

def test_a_project_using_only_pre_1_1_0_signals_loads_and_compiles_cleanly():
    """A project built against catalog 1.0.0 (before SEC existed)
    references only signals that are STILL in 1.1.0, unchanged — nothing
    was renamed or removed, only added. Must load/compile with no
    "unrecognized signal" warning."""
    p = Project()
    p.add_block(_in_block("SYS.READY"))

    c = Compiler(p)
    res = c.compile()

    assert res is not None, f"Compile failed: {c.errors}"
    assert not any("Nierozpoznany" in w for w in c.warnings)

def test_serialized_pre_1_1_0_project_round_trips():
    p = Project()
    p.add_block(_in_block("SYS.READY"))
    data = p.serialize()

    reloaded = Project.deserialize(data)

    c = Compiler(reloaded)
    res = c.compile()
    assert res is not None, f"Compile failed: {c.errors}"
    assert not any("Nierozpoznany" in w for w in c.warnings)


# ---- signal picker filtering (§2.4) -----------------------------------------

def test_output_block_signal_picker_shows_only_logic_sourced_signals():
    _app()
    from logic_studio.ui.signal_picker import SignalPickerDialog
    p = Project()
    dlg = SignalPickerDialog(p, value_type=None, sections=("system",), system_source_filter="logic")
    sys_root = dlg.tree.topLevelItem(0)
    cats = {sys_root.child(i).text(0) for i in range(sys_root.childCount())}
    # Exactly the request categories - every one of them, nothing else.
    request_categories = {c["name"] for c in system_signals.get_categories()
                          if any(s["source"] == "logic" for s in c["signals"])}
    assert cats == request_categories
    assert "Żądania - alarmówka" in cats and "Stan dozoru" not in cats

def test_input_block_signal_picker_shows_every_category():
    _app()
    from logic_studio.ui.signal_picker import SignalPickerDialog
    p = Project()
    dlg = SignalPickerDialog(p, value_type=None, sections=("system",))
    sys_root = dlg.tree.topLevelItem(0)
    cats = {sys_root.child(i).text(0) for i in range(sys_root.childCount())}
    assert "Żądania - alarmówka" in cats
    assert "Stan dozoru" in cats
    assert "Alarmy" in cats


# ---- signals panel "Zapisuje" column (§2.5) ---------------------------------

def test_signals_panel_shows_writer_block_for_a_logic_sourced_signal():
    _app()
    from logic_studio.ui.panels.signals import SignalsPanel
    from logic_studio.core.crossref import build_crossref

    p = Project()
    out = _out_block("REQ.SEC.ARM_ALL")
    p.add_block(out)

    panel = SignalsPanel()
    panel.project = p
    usage = build_crossref(p)["REQ.SEC.ARM_ALL"]

    text, tooltip = panel._writers_text("REQ.SEC.ARM_ALL", usage)
    assert text == out.short_id

def test_signals_panel_still_shows_urzadzenie_for_a_runtime_sourced_signal():
    _app()
    from logic_studio.ui.panels.signals import SignalsPanel
    from logic_studio.core.crossref import build_crossref

    p = Project()
    p.add_block(_in_block("SYS.READY"))

    panel = SignalsPanel()
    panel.project = p
    usage = build_crossref(p)["SYS.READY"]

    text, _tooltip = panel._writers_text("SYS.READY", usage)
    assert text == "device"

def test_signals_panel_shows_dash_for_an_unwritten_logic_signal():
    _app()
    from logic_studio.ui.panels.signals import SignalsPanel
    from logic_studio.core.crossref import SignalUsage, KIND_SYSTEM

    p = Project()
    panel = SignalsPanel()
    panel.project = p
    usage = SignalUsage(signal_id="REQ.SEC.CLEAR_ALARM_MEMORY", kind=KIND_SYSTEM, data_type="BOOL")

    text, _tooltip = panel._writers_text("REQ.SEC.CLEAR_ALARM_MEMORY", usage)
    assert text == "—"
