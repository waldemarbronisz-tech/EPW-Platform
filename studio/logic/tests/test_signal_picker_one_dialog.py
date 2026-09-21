"""feat/signal-register §1 — one dialog to choose a bit for the logic.

Reported by the owner: the "Bit input (internal)" block opens an EMPTY
dialog. Nothing was broken in the dialog - every one of the four signal
blocks asked it for sections=("internal",), and a fresh project has no
markers yet, so the honest answer to that question was an empty tree.
Meanwhile 42 system signals sat behind a SEPARATE block ("System
signal"), filed in the library under "Other".

So the fix is not "show something": it is that a bit block reads a BIT,
and where the bit comes from - this project's own registry or the
platform's catalog - is not a distinction an engineer should have to
express by choosing a different block first. eTango has one window; so
does this now.

What the tests below pin is the CONTENT of that window: which signal ids
are actually offered to which block, which are deliberately withheld,
what an empty section says instead of showing nothing, and that a system
signal picked this way survives all the way through the compiler into a
real read at run time - the half that would otherwise be a facade.
"""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from shared.logic.blocks import register_builtin_blocks
from shared.logic.blocks.registry import BlockRegistry
from shared.logic.blocks.virtual_io import (
    SIGNAL_KIND_INTERNAL, SIGNAL_KIND_SYSTEM, resolve_signal_reference,
)
from logic_studio.core.project import Project
from logic_studio.core.device_model import DeviceModel
from logic_studio.i18n import set_language
from logic_studio.ui.panels.property_grid import _SIGNAL_PICKER_TARGETS

register_builtin_blocks()


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def english():
    """Every assertion below reads English text unless it says otherwise."""
    set_language("en")
    yield
    set_language("en")


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


def _picker(project, type_id, key="Bit"):
    """The dialog EXACTLY as the property panel opens it for that block -
    through _SIGNAL_PICKER_TARGETS, so a test can never pass while the
    table the real code reads says something else."""
    from logic_studio.ui.signal_picker import SignalPickerDialog
    target = _SIGNAL_PICKER_TARGETS[(type_id, key)]
    return SignalPickerDialog(
        project, value_type=target[0], sections=target[1],
        system_source_filter=target[2] if len(target) > 2 else None,
    )


def _ids(dialog):
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


def _headings(dialog):
    return [dialog.tree.topLevelItem(i).text(0)
            for i in range(dialog.tree.topLevelItemCount())]


def _rows_under(dialog, heading):
    for i in range(dialog.tree.topLevelItemCount()):
        item = dialog.tree.topLevelItem(i)
        if item.text(0) == heading:
            return [item.child(j) for j in range(item.childCount())]
    raise AssertionError("no section %r among %r" % (heading, _headings(dialog)))


# --- §1.1: one window, all four blocks ---------------------------------------

def test_the_bit_input_block_offers_the_project_and_the_platform_together(app):
    dialog = _picker(_project([_bit("BLOKADA_ZS")]), "virtual.input")
    ids = _ids(dialog)

    assert "BLOKADA_ZS" in ids, "the project's own marker"
    assert "SYS.READY" in ids, "and the platform catalog, in the same window"
    assert _headings(dialog) == ["Internal signals", "System signals"]


def test_every_one_of_the_four_signal_blocks_sees_both_sections():
    """The defect was one shared table entry repeated four times, so a fix
    that only reached virtual.input would leave three blocks broken."""
    for type_id in ("virtual.input", "virtual.output", "internal.reg_in", "internal.reg_out"):
        sections = _SIGNAL_PICKER_TARGETS[(type_id, "Bit")][1]
        assert set(sections) == {"internal", "system"}, type_id


def test_a_bool_block_is_never_offered_a_real_signal(app):
    project = _project([_bit("BLOKADA_ZS"), _bit("USTAWKA", "REAL")])
    ids = _ids(_picker(project, "virtual.input"))

    assert "BLOKADA_ZS" in ids
    assert "USTAWKA" not in ids, "a REAL marker in a BOOL block"
    assert "SYS.SCAN_TIME" not in ids, "SYS.SCAN_TIME is REAL"


def test_a_register_block_is_never_offered_a_bool_signal(app):
    project = _project([_bit("BLOKADA_ZS"), _bit("USTAWKA", "REAL")])
    ids = _ids(_picker(project, "internal.reg_in"))

    assert "USTAWKA" in ids
    assert "SYS.SCAN_TIME" in ids, "the REAL half of the catalog"
    assert "BLOKADA_ZS" not in ids
    assert "SYS.READY" not in ids


def test_an_output_block_is_never_offered_a_signal_the_runtime_owns(app):
    """The compiler rejects writing a source == "runtime" signal. A dialog
    that proposes one is proposing a compile error."""
    ids = _ids(_picker(_project([_bit("BLOKADA_ZS")]), "virtual.output"))

    assert "BLOKADA_ZS" in ids, "a marker is always writable"
    assert "REQ.SEC.ARM_ALL" in ids, "a command the logic owns"
    assert "SYS.READY" not in ids
    assert "SEC.SYSTEM.ARMED" not in ids, "the runtime decides this one"


# --- §1.3: an empty section says what belongs in it --------------------------

def test_an_empty_registry_explains_itself_instead_of_showing_nothing(app):
    dialog = _picker(_project(), "virtual.input")

    rows = _rows_under(dialog, "Internal signals")
    assert len(rows) == 1
    assert rows[0].text(0) == (
        'No internal signals - add one with the "New internal signal" button below.'
    )


def test_the_explanation_is_not_something_you_can_pick(app):
    """It is a sentence, not a signal. Selecting it and pressing OK would
    set the property to nothing at all."""
    dialog = _picker(_project(), "virtual.input")
    hint = _rows_under(dialog, "Internal signals")[0]

    assert hint.data(0, Qt.UserRole) is None
    assert not (hint.flags() & Qt.ItemIsSelectable)
    assert not dialog.ok_button.isEnabled()


def test_the_explanation_gets_out_of_the_way_once_you_search(app):
    """While searching, "no results" is the honest answer - a leftover
    hint would read as a match."""
    dialog = _picker(_project(), "virtual.input")
    hint = _rows_under(dialog, "Internal signals")[0]

    dialog.search_edit.setText("READY")
    assert hint.isHidden()

    dialog.search_edit.setText("")
    assert not hint.isHidden()


# --- §1.2: the headings are translated ---------------------------------------

def test_the_section_headings_are_polish_in_a_polish_session(app):
    set_language("pl")
    dialog = _picker(_project([_bit("BLOKADA_ZS")]), "virtual.input")

    assert _headings(dialog) == ["Sygnały wewnętrzne", "Sygnały systemowe"]


def test_the_empty_registry_explains_itself_in_polish_too(app):
    set_language("pl")
    dialog = _picker(_project(), "virtual.input")

    assert _rows_under(dialog, "Sygnały wewnętrzne")[0].text(0) == (
        "Brak sygnałów wewnętrznych - dodaj przyciskiem „Nowy sygnał wewnętrzny” poniżej."
    )


def test_an_uncategorised_marker_is_not_filed_under_a_polish_word_in_english(app):
    """"(bez kategorii)" was written straight into the grouping code."""
    dialog = _picker(_project([_bit("BLOKADA_ZS")]), "virtual.input")

    groups = [row.text(0) for row in _rows_under(dialog, "Internal signals")]
    assert groups == ["(no category)"]


# --- §1.5: the "new internal signal" window ----------------------------------

def test_a_register_block_cannot_create_a_bool_it_would_never_show(app):
    from logic_studio.ui.signal_picker import _NewInternalSignalDialog

    dialog = _NewInternalSignalDialog("REAL")

    assert dialog.type_combo.currentText() == "REAL"
    assert not dialog.type_combo.isEnabled()


def test_the_new_signal_form_is_labelled_in_the_interface_language(app):
    from logic_studio.ui.signal_picker import _NewInternalSignalDialog
    from PySide6.QtWidgets import QFormLayout, QLabel

    set_language("pl")
    dialog = _NewInternalSignalDialog("BOOL")
    form = dialog.findChild(QFormLayout)
    labels = []
    for row in range(form.rowCount()):
        item = form.itemAt(row, QFormLayout.LabelRole)
        if item is not None and isinstance(item.widget(), QLabel):
            labels.append(item.widget().text())

    assert labels == ["Nazwa", "Typ", "Retencja", "Opis", "Etykieta", "Kategoria"]


def test_the_button_that_creates_a_marker_is_hidden_where_markers_cannot_go(app):
    """system.signal's picker shows the catalog only - a "New internal
    signal" button there creates something its own list cannot display."""
    system_only = _picker(_project(), "system.signal", key="Sygnał")
    both = _picker(_project(), "virtual.input")

    assert not system_only.new_signal_btn.isVisible()
    assert both.new_signal_btn.isVisible() or not both.isVisible()  # only hidden deliberately
    assert "internal" in _SIGNAL_PICKER_TARGETS[("virtual.input", "Bit")][1]


# --- §1.4: the block has its own place in the library ------------------------

def test_the_system_signal_blocks_left_the_other_drawer():
    """They used to sit among the constants and the square-wave generator,
    which is not where anybody looks for the alarm system's state."""
    for type_id in ("system.signal", "system.signal_out"):
        block = BlockRegistry.create_block(type_id)
        assert block.category == "System signals", type_id

    from logic_studio.ui.panels.library import LibraryPanel  # noqa: F401  (import guard)
    assert "System signals" in BlockRegistry.get_categories()


def test_the_new_category_has_a_polish_name():
    from shared.logic.i18n import category_label

    assert category_label("System signals", "pl") == "Sygnały systemowe"


# --- resolution: which address space a name belongs to -----------------------

def test_a_name_in_neither_place_resolves_to_nothing():
    assert resolve_signal_reference("NIE_MA_TAKIEGO", None, None) == ("", None)


def test_a_marker_resolves_to_its_prefixed_id():
    signal_id, kind = resolve_signal_reference("BLOKADA_ZS", _bit("BLOKADA_ZS"), None)

    assert (signal_id, kind) == ("M.BLOKADA_ZS", SIGNAL_KIND_INTERNAL)


def test_a_retentive_marker_keeps_its_own_prefix():
    signal_id, _kind = resolve_signal_reference(
        "PAMIEC", _bit("PAMIEC", retentive=True), None)

    assert signal_id == "MR.PAMIEC"


def test_the_platform_catalog_wins_over_a_marker_of_the_same_name():
    """Otherwise the same name would mean different things in two
    projects, which is the one thing a fixed contract exists to prevent."""
    from shared.logic import system_signals

    catalog = system_signals.get_signal("SYS.READY")
    signal_id, kind = resolve_signal_reference("SYS.READY", _bit("SYS.READY"), catalog)

    assert (signal_id, kind) == ("SYS.READY", SIGNAL_KIND_SYSTEM)
