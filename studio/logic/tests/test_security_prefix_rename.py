"""feat/signal-register §3.1 — the alarm system's prefix is SEC.

Owner's decision (2026-09-21). The prompt described it as changing 23
signals "wg nazw z rejestru", and the register turned out not to offer a
straight swap: it reorganises the namespace. System-wide state moved to
SEC.SYSTEM.*, and the five commands left the state namespace entirely
for REQ.SEC.*, which is where the register's own standard sheet puts
every signal the logic REQUESTS and a manager then validates and
executes or refuses.

Eleven of the twenty-three have no row in the register at all - it has
no partial arming, no sounder, no panic line, and it is BOOL-only - so
they are named by the register's grammar and flagged `accepted` - the
owner reviewed and took them unchanged on 2026-09-21. These tests pin
which is which, so a name settled here cannot quietly become one the
register supplied.

The last group is the migration itself, which is deliberately NOT a
migration: a project naming a retired signal is reported, with the new
name, at both moments that matter (opening, and compiling), and is never
rewritten underneath the engineer.
"""
import pytest
from PySide6.QtWidgets import QApplication

from shared.logic import system_signals
from shared.logic.blocks import register_builtin_blocks
from shared.logic.blocks.registry import BlockRegistry
from shared.logic.signal_renames import (
    RENAMES, RETIRED_PREFIX, by_provenance, is_retired, new_name, retired_in,
)
from logic_studio.compiler.core import Compiler
from logic_studio.core.device_model import DeviceModel
from logic_studio.core.project import Project

register_builtin_blocks()


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def _project():
    p = Project()
    DeviceModel.set_ela_devices(p, ["ELA01"])
    DeviceModel.set_ada_devices(p, ["ADA01"])
    return p


def _block(type_id, **properties):
    block = BlockRegistry.create_block(type_id)
    for key, value in properties.items():
        block.properties[key] = value
    return block


CATALOG_IDS = {s["id"] for s in system_signals.get_all_signals()}


# --- the namespace is gone ---------------------------------------------------

def test_the_catalogue_has_no_signal_in_the_retired_namespace():
    assert not [i for i in CATALOG_IDS if i.startswith(RETIRED_PREFIX)], sorted(CATALOG_IDS)


def test_every_retired_name_maps_to_something_that_actually_exists():
    """A rename table pointing at a name no catalogue has would send an
    engineer from one missing signal to another."""
    for old_id, (new_id, _provenance) in RENAMES.items():
        assert new_id in CATALOG_IDS, f"{old_id} -> {new_id}, which is not in the catalogue"


def test_no_entry_renames_a_signal_to_itself():
    """The whole table was once destroyed by a careless project-wide
    substitution that rewrote its own keys - the result looked fine and
    silently stopped recognising every old project."""
    for old_id, (new_id, _p) in RENAMES.items():
        assert old_id != new_id


def test_all_twenty_three_are_covered():
    assert len(RENAMES) == 23


# --- state and requests are different things ---------------------------------

def test_system_wide_state_lives_under_sec_system():
    assert new_name(RETIRED_PREFIX + "ARMED") == "SEC.SYSTEM.ARMED"
    assert new_name(RETIRED_PREFIX + "ALARM_ACTIVE") == "SEC.SYSTEM.ALARM"


def test_the_commands_became_requests_not_states():
    """The register's own rule: the logic sets REQ.*, a manager validates
    and executes or refuses. Keeping them beside the states would have
    kept the one distinction this rename is for."""
    for old_suffix in ("CMD_ARM", "CMD_DISARM", "CMD_RESET", "CMD_SILENCE", "CMD_ARM_PARTIAL"):
        assert new_name(RETIRED_PREFIX + old_suffix).startswith("REQ.SEC."), old_suffix


def test_everything_the_logic_may_write_is_a_request_and_nothing_else_is():
    writable = {s["id"] for s in system_signals.get_all_signals() if s.get("source") == "logic"}

    assert writable, "the catalogue offers the logic nothing to write"
    assert all(i.startswith("REQ.") for i in writable), sorted(writable)
    assert not any(i.startswith("SEC.SYSTEM.") for i in writable)


# --- provenance is recorded, not assumed -------------------------------------

def test_the_register_backed_names_are_the_ones_the_register_has():
    from_register = dict(by_provenance("register"))

    assert len(from_register) == 12
    assert from_register[RETIRED_PREFIX + "ARMED"] == "SEC.SYSTEM.ARMED"
    assert from_register[RETIRED_PREFIX + "CMD_ARM"] == "REQ.SEC.ARM_ALL"


def test_the_ones_the_register_does_not_cover_say_so():
    """Eleven signals this controller really serves have no row in the
    register. Naming them by its grammar was a decision, and the owner
    accepted it on 2026-09-21; recording that it WAS a decision is what
    lets a later revision of the register correct them in one place."""
    settled_here = dict(by_provenance("accepted"))

    assert len(settled_here) == 11
    # The sounder, the panic line and partial arming - real, served, and
    # absent from a register that predates them.
    assert RETIRED_PREFIX + "PANIC" in settled_here
    assert RETIRED_PREFIX + "SIREN_ACTIVE" in settled_here
    assert RETIRED_PREFIX + "ARMED_PARTIAL" in settled_here


def test_nothing_is_left_flagged_as_awaiting_a_decision():
    """The owner accepted the eleven on 2026-09-21. A status page that
    still listed settled decisions as open teaches people to skip that
    section, which is how the next real question gets missed."""
    assert {p for _n, p in RENAMES.values()} == {"register", "accepted"}


def test_the_real_valued_signals_were_all_settled_here():
    """The register is BOOL-only, so nothing carrying a number could have
    come from it - each of these four was named here and accepted."""
    for suffix in ("DELAY_REMAINING", "LAST_TRIGGER", "ACTIVE_COUNT", "SIREN_TIME_LEFT"):
        old = RETIRED_PREFIX + suffix
        assert is_retired(old)
        assert dict(by_provenance("accepted")).get(old), suffix


# --- nothing is converted behind anybody's back ------------------------------

def test_an_old_project_is_reported_block_by_block(app):
    project = _project()
    a = _block("virtual.input", Bit=RETIRED_PREFIX + "ARMED")
    b = _block("system.signal", **{"Sygnał": RETIRED_PREFIX + "PANIC"})
    project.add_block(a)
    project.add_block(b)

    reported = retired_in(project.blocks)

    assert [(old, new) for _b, old, new in reported] == [
        (RETIRED_PREFIX + "ARMED", "SEC.SYSTEM.ARMED"),
        (RETIRED_PREFIX + "PANIC", "SEC.SYSTEM.PANIC"),
    ]


def test_the_report_looks_at_both_property_names(app):
    """"Bit" on the four signal blocks, "Sygnał" on the system ones.
    Reporting one would send somebody hunting for a correct block."""
    project = _project()
    project.add_block(_block("system.signal_out", **{"Sygnał": RETIRED_PREFIX + "CMD_ARM"}))

    assert len(retired_in(project.blocks)) == 1


def test_the_blocks_are_not_rewritten_by_looking_at_them(app):
    """A report, not a migration."""
    project = _project()
    block = _block("virtual.input", Bit=RETIRED_PREFIX + "ARMED")
    project.add_block(block)

    retired_in(project.blocks)

    assert block.properties["Bit"] == RETIRED_PREFIX + "ARMED"


def test_compiling_an_old_name_names_the_new_one_in_the_error(app):
    """Falling through to "exists in neither place" would be true and
    useless: the signal was renamed, not deleted."""
    project = _project()
    project.add_block(_block("virtual.input", Bit=RETIRED_PREFIX + "ARMED"))

    compiler = Compiler(project)
    compiler.compile()

    message = " ".join(compiler.errors)
    assert "SEC.SYSTEM.ARMED" in message, message
    assert "no longer exists" in message, message


def test_an_old_name_does_not_produce_a_runtime_file(app):
    """It must be an error, not a warning - a controller running a
    program whose commands silently do nothing is the worse outcome."""
    project = _project()
    source = _block("const.true")
    writer = _block("virtual.output", Bit=RETIRED_PREFIX + "CMD_ARM")
    source.outputs[0].connect(writer.inputs[0])
    project.add_block(source)
    project.add_block(writer)

    assert Compiler(project).compile() is None


def test_a_project_on_the_new_names_compiles_cleanly(app):
    project = _project()
    source = _block("const.true")
    writer = _block("virtual.output", Bit="REQ.SEC.ARM_ALL")
    source.outputs[0].connect(writer.inputs[0])
    project.add_block(source)
    project.add_block(writer)

    compiler = Compiler(project)

    assert compiler.compile() is not None, compiler.errors


# --- the version says what happened ------------------------------------------

def test_renaming_signals_bumped_the_major_version():
    """The catalogue's own rule: a new signal is MINOR, a rename or a
    removal is MAJOR, because a project compiled against the old names
    is no longer valid against these."""
    major = int(system_signals.get_catalog_version().split(".")[0])

    assert major >= 2, system_signals.get_catalog_version()
