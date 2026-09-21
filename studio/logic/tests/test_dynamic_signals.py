"""feat/signal-register §3.3 — a pattern in the catalogue, real signals
in the dialog.

The register writes the alarm system's per-zone state as
SEC.ZONE.<zone_id>.ARMED. A fixed catalogue cannot hold those: how many
there are is a property of the installation. But the platform genuinely
does fix that every zone HAS an ARMED, what it means and what type it
is - only the list of zones belongs to the project.

So the catalogue holds the PATTERN and get_categories(project) turns it
into signals. What these tests are pointed at is the consequence an
engineer sees: the picker offers SEC.ZONE.PARTER.ARMED, by that name,
and never offers the pattern itself - a signal called
"SEC.ZONE.<zone_id>.ARMED" is not something anybody can bind a block to.
"""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from shared.logic import system_signals
from shared.logic.blocks import register_builtin_blocks
from logic_studio.core.device_model import DeviceModel
from logic_studio.core.project import Project
from logic_studio.ui.panels.property_grid import _SIGNAL_PICKER_TARGETS

register_builtin_blocks()


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def _installation(zones=(("PARTER", "Parter"), ("PIETRO", "Piętro")),
                  lines=(("L1", "Drzwi wejściowe"),)):
    project = Project()
    DeviceModel.set_ela_devices(project, ["ELA01"])
    project.external_zones = [{"id": i, "name": n} for i, n in zones]
    project.external_lines = [{"id": i, "name": n} for i, n in lines]
    return project


def _ids(project=None):
    return [s["id"] for s in system_signals.get_all_signals(project)]


def _picker_ids(project, type_id, key="Bit"):
    from logic_studio.ui.signal_picker import SignalPickerDialog

    target = _SIGNAL_PICKER_TARGETS[(type_id, key)]
    dialog = SignalPickerDialog(
        project, value_type=target[0], sections=target[1],
        system_source_filter=target[2] if len(target) > 2 else None,
    )
    out = []

    def walk(item):
        sid = item.data(0, Qt.UserRole)
        if sid is not None:
            out.append(sid)
        for i in range(item.childCount()):
            walk(item.child(i))

    for i in range(dialog.tree.topLevelItemCount()):
        walk(dialog.tree.topLevelItem(i))
    return out


# --- the pattern becomes signals ---------------------------------------------

def test_a_project_with_zones_gets_one_signal_per_zone():
    ids = _ids(_installation())

    assert "SEC.ZONE.PARTER.ARMED" in ids
    assert "SEC.ZONE.PIETRO.ARMED" in ids


def test_the_pattern_itself_is_never_offered():
    """Nobody can bind a block to "<zone_id>"."""
    for signal_id in _ids(_installation()):
        assert "<" not in signal_id, signal_id


def test_a_project_with_no_alarm_system_gets_no_zone_signals():
    """The correct answer for an installation without zones is none -
    not a placeholder, and not an error."""
    ids = _ids(_installation(zones=(), lines=()))

    assert not [i for i in ids if i.startswith("SEC.ZONE.")]
    assert not [i for i in ids if i.startswith("SEC.LINE.")]


def test_a_standalone_logic_studio_sees_only_the_fixed_catalogue():
    """No Studio host, so no zones were ever mirrored in."""
    fixed = _ids(None)

    assert "SYS.READY" in fixed
    assert not [i for i in fixed if i.startswith("SEC.ZONE.")]


def test_adding_a_zone_adds_its_whole_set_of_signals():
    one = set(_ids(_installation(zones=(("A", "A"),))))
    two = set(_ids(_installation(zones=(("A", "A"), ("B", "B")))))

    added = two - one
    assert added, "a second zone produced nothing"
    assert all(i.startswith(("SEC.ZONE.B.", "REQ.SEC.ZONE.B.")) for i in added), sorted(added)


# --- what the engineer actually reads ----------------------------------------

def test_the_description_names_the_zone_so_the_list_is_readable():
    signals = {s["id"]: s for s in system_signals.get_all_signals(_installation())}

    assert signals["SEC.ZONE.PARTER.ARMED"]["description"] == "Strefa uzbrojona - Parter"


def test_the_signal_remembers_which_pattern_it_came_from():
    """A panel or a report that wants to group "every zone's ARMED"
    should not have to parse the id back apart."""
    signals = {s["id"]: s for s in system_signals.get_all_signals(_installation())}

    assert signals["SEC.ZONE.PARTER.ARMED"]["instance_of"] == "SEC.ZONE.<zone_id>.ARMED"
    assert signals["SEC.ZONE.PARTER.ARMED"]["instance_id"] == "PARTER"


def test_the_id_follows_the_stable_id_not_the_display_name():
    """The register's own rule: "runtime wiąże się do stabilnego ID, nie
    display name". Renaming a zone in Studio must not break a schematic."""
    project = _installation(zones=(("PARTER", "Parter"),))
    before = _ids(project)

    project.external_zones = [{"id": "PARTER", "name": "Cała kondygnacja"}]

    assert _ids(project) == before


# --- the dialog ---------------------------------------------------------------

def test_the_bit_picker_offers_a_real_zone_signal(app):
    ids = _picker_ids(_installation(), "virtual.input")

    assert "SEC.ZONE.PARTER.ARMED" in ids
    assert "SEC.LINE.L1.VIOLATED" in ids


def test_the_output_picker_offers_the_per_zone_requests_only(app):
    """A per-zone STATE is the runtime's to write, a per-zone REQUEST is
    the logic's."""
    ids = _picker_ids(_installation(), "virtual.output")

    assert "REQ.SEC.ZONE.PARTER.ARM" in ids
    assert "SEC.ZONE.PARTER.ARMED" not in ids


def test_a_per_zone_signal_compiles_like_any_other(app):
    from logic_studio.compiler.core import Compiler
    from shared.logic.blocks.registry import BlockRegistry

    project = _installation()
    reader = BlockRegistry.create_block("virtual.input")
    reader.properties["Bit"] = "SEC.ZONE.PARTER.ARMED"
    project.add_block(reader)

    compiler = Compiler(project)

    assert compiler.compile() is not None, compiler.errors


def test_a_zone_that_does_not_exist_is_a_compile_error(app):
    """The zone list is part of the project, so a block naming a zone the
    project does not have is exactly as wrong as a misspelt signal."""
    from logic_studio.compiler.core import Compiler
    from shared.logic.blocks.registry import BlockRegistry

    project = _installation()
    reader = BlockRegistry.create_block("virtual.input")
    reader.properties["Bit"] = "SEC.ZONE.NIEMA.ARMED"
    project.add_block(reader)

    compiler = Compiler(project)
    compiler.compile()

    assert compiler.errors, "a signal for a zone that does not exist compiled cleanly"
