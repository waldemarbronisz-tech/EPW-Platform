"""feat/signal-register §2 — the "Sygnały" department.

Owner: "Waldek chce móc dodawać bity z jednego miejsca, jak rejestr
punktów", and the warning that came with it: "Dwa rejestry tych samych
bitów to błąd, który ten projekt przerabiał osiem razy."

So the single most important thing these tests check is not what the
panel displays - it is WHAT IT EDITS. The markers live in the logic
project's own settings["internal_bits"], and every assertion below that
touches the registry reads it back from THAT object rather than from the
panel, so a panel that quietly kept a copy of its own would fail here
even while looking perfectly correct on screen.

The rest is the behaviour the prompt asked for by name: the derived
identifier (M./MR./MW./MWR., which is what "retention" actually means),
the "used by" column, a rename that re-points the blocks instead of
orphaning them, a delete that names what it is about to break, and a
system tab that is a contract rather than a list somebody may extend.
"""
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from studio.shell.logic_path import ensure_importable

ensure_importable()

from studio.shell import i18n as shell_i18n
from studio.shell.main_window import StudioMainWindow, _TREE_ITEM_SIGNALS


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def english():
    shell_i18n.set_language("en")
    yield
    shell_i18n.set_language("en")


@pytest.fixture
def window(tmp_path, app):
    w = StudioMainWindow(settings=QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat))
    yield w
    for timer in w.findChildren(QTimer):
        timer.stop()
    w.hide()
    w.deleteLater()


@pytest.fixture
def panel(window):
    """The department as a click on the tree opens it."""
    window._open_signals()
    return window._signals_panel


def _registry(window):
    """The registry AS THE LOGIC PROJECT HOLDS IT - never through the
    panel, which is the thing under test."""
    return window._logic_panel.main_window().project.settings["internal_bits"]


def _logic_project(window):
    return window._logic_panel.main_window().project


def _bit(name, type_="BOOL", **over):
    entry = {"name": name, "type": type_, "retentive": False,
             "description": "", "label": "", "category": ""}
    entry.update(over)
    return entry


def _block(project, type_id, bit):
    from shared.logic.blocks import register_builtin_blocks
    from shared.logic.blocks.registry import BlockRegistry

    register_builtin_blocks()
    block = BlockRegistry.create_block(type_id)
    block.properties["Bit"] = bit
    project.add_block(block)
    return block


def _cell(table, row, col):
    item = table.item(row, col)
    return item.text() if item is not None else None


def _column(table, col):
    return [_cell(table, row, col) for row in range(table.rowCount())]


# --- the department exists and is reachable ----------------------------------

def test_the_tree_has_a_signals_branch(window):
    labels = []

    def walk(item):
        labels.append(item.text(0))
        for i in range(item.childCount()):
            walk(item.child(i))

    for i in range(window.tree.topLevelItemCount()):
        walk(window.tree.topLevelItem(i))

    assert "Signals" in labels


def test_the_branch_comes_before_the_logic_editor(window):
    """The order the tree keeps: a department after the ones it needs.
    Bits are named, then wired."""
    config = window._item_signals.parent()
    order = [config.child(i) for i in range(config.childCount())]

    assert order.index(window._item_signals) < order.index(window._item_logic)


def test_opening_it_shows_the_two_tabs(panel):
    assert [panel.tabs.tabText(i) for i in range(panel.tabs.count())] == ["Internal", "System"]


def test_the_tabs_are_named_in_the_interface_language(window):
    shell_i18n.set_language("pl")
    window._open_signals()
    panel = window._signals_panel

    assert [panel.tabs.tabText(i) for i in range(panel.tabs.count())] == ["Wewnętrzne", "Systemowe"]


# --- ONE registry, not two ---------------------------------------------------

def test_the_panel_edits_the_logic_projects_own_registry(window, panel):
    """The whole point. Add through the panel, read back from the logic
    project - a panel keeping a copy of its own fails right here."""
    panel.internal_tab.add_signal()

    assert len(_registry(window)) == 1
    assert _registry(window)[0]["name"] == "NEW_SIGNAL"


def test_it_shows_markers_that_were_already_there(window, panel):
    _registry(window).append(_bit("BLOKADA_ZS", description="Blokada załączenia"))
    panel.internal_tab.refresh()

    table = panel.internal_tab.table
    assert _column(table, panel.internal_tab.COL_NAME) == ["BLOKADA_ZS"]
    assert _column(table, panel.internal_tab.COL_DESCRIPTION) == ["Blokada załączenia"]


def test_an_edited_description_lands_in_the_registry(window, panel):
    _registry(window).append(_bit("BLOKADA_ZS"))
    panel.internal_tab.refresh()
    table = panel.internal_tab.table

    table.item(0, panel.internal_tab.COL_DESCRIPTION).setText("Opis z panelu")

    assert _registry(window)[0]["description"] == "Opis z panelu"


def test_a_second_added_signal_does_not_reuse_the_first_name(window, panel):
    panel.internal_tab.add_signal()
    panel.internal_tab.add_signal()

    names = [entry["name"] for entry in _registry(window)]
    assert len(set(names)) == 2, names


# --- the identifier is derived, and that is what retention means -------------

def test_the_identifier_column_shows_what_type_and_retention_produce(window, panel):
    _registry(window).extend([
        _bit("A"), _bit("B", retentive=True),
        _bit("C", "REAL"), _bit("D", "REAL", retentive=True),
    ])
    panel.internal_tab.refresh()

    assert _column(panel.internal_tab.table, panel.internal_tab.COL_ID) == [
        "M.A", "MR.B", "MW.C", "MWR.D",
    ]


def test_ticking_retention_changes_the_identifier(window, panel):
    _registry(window).append(_bit("PAMIEC"))
    panel.internal_tab.refresh()
    tab = panel.internal_tab

    tab.table.cellWidget(0, tab.COL_RETENTIVE).setChecked(True)

    assert _registry(window)[0]["retentive"] is True
    assert _cell(tab.table, 0, tab.COL_ID) == "MR.PAMIEC"


def test_the_identifier_cannot_be_typed_over(window, panel):
    """It is derived. An editable cell would invite somebody to set it to
    something the program would then ignore."""
    _registry(window).append(_bit("A"))
    panel.internal_tab.refresh()

    item = panel.internal_tab.table.item(0, panel.internal_tab.COL_ID)
    assert not (item.flags() & Qt.ItemFlag.ItemIsEditable)


# --- "used by" ---------------------------------------------------------------

def test_the_used_by_column_names_the_blocks(window, panel):
    _registry(window).append(_bit("BLOKADA_ZS"))
    block = _block(_logic_project(window), "virtual.input", "BLOKADA_ZS")
    panel.internal_tab.refresh()

    used = _cell(panel.internal_tab.table, 0, panel.internal_tab.COL_USED)
    assert block.short_id in used


def test_a_marker_nothing_reads_says_so(window, panel):
    _registry(window).append(_bit("NIEUZYWANY"))
    panel.internal_tab.refresh()

    assert _cell(panel.internal_tab.table, 0, panel.internal_tab.COL_USED) == "not used"


# --- renaming ----------------------------------------------------------------

def test_renaming_re_points_every_block_that_used_the_old_name(window, panel):
    _registry(window).append(_bit("STARA"))
    project = _logic_project(window)
    reader = _block(project, "virtual.input", "STARA")
    writer = _block(project, "virtual.output", "STARA")
    panel.internal_tab.refresh()

    panel.internal_tab.table.item(0, panel.internal_tab.COL_NAME).setText("NOWA")

    assert _registry(window)[0]["name"] == "NOWA"
    assert reader.properties["Bit"] == "NOWA"
    assert writer.properties["Bit"] == "NOWA", "a block left pointing at a name that no longer exists"


def test_a_duplicate_name_is_refused_and_nothing_changes(window, panel, monkeypatch):
    shown = []
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: shown.append(a[1:3])))
    _registry(window).extend([_bit("PIERWSZY"), _bit("DRUGI")])
    panel.internal_tab.refresh()

    panel.internal_tab.table.item(1, panel.internal_tab.COL_NAME).setText("PIERWSZY")

    assert [e["name"] for e in _registry(window)] == ["PIERWSZY", "DRUGI"]
    assert shown, "the clash was accepted silently"


def test_a_name_the_registry_could_never_store_is_refused(window, panel, monkeypatch):
    """Spaces and Polish diacritics cannot go into an M.<name> id."""
    shown = []
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: shown.append(a[1:3])))
    _registry(window).append(_bit("DOBRA"))
    panel.internal_tab.refresh()

    panel.internal_tab.table.item(0, panel.internal_tab.COL_NAME).setText("zła nazwa")

    assert _registry(window)[0]["name"] == "DOBRA"
    assert shown


# --- deleting ----------------------------------------------------------------

def test_deleting_a_used_marker_warns_and_names_what_breaks(window, panel, monkeypatch):
    asked = {}

    def _warn(parent, title, text, *args, **kwargs):
        asked["title"] = title
        asked["text"] = text
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "warning", staticmethod(_warn))
    _registry(window).append(_bit("UZYWANY"))
    block = _block(_logic_project(window), "virtual.input", "UZYWANY")
    panel.internal_tab.refresh()
    panel.internal_tab.table.selectRow(0)

    panel.internal_tab.delete_selected()

    assert "UZYWANY" in asked["text"]
    assert block.short_id in asked["text"], "the warning did not say WHERE it is used"
    assert len(_registry(window)) == 1, "answering No still deleted it"


def test_confirming_the_warning_does_delete_it(window, panel, monkeypatch):
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    _registry(window).append(_bit("UZYWANY"))
    _block(_logic_project(window), "virtual.input", "UZYWANY")
    panel.internal_tab.refresh()
    panel.internal_tab.table.selectRow(0)

    panel.internal_tab.delete_selected()

    assert _registry(window) == []


def test_deleting_an_unused_marker_asks_nothing(window, panel, monkeypatch):
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: pytest.fail("asked about an unused signal")))
    _registry(window).append(_bit("NIEUZYWANY"))
    panel.internal_tab.refresh()
    panel.internal_tab.table.selectRow(0)

    panel.internal_tab.delete_selected()

    assert _registry(window) == []


# --- the system tab is a contract --------------------------------------------

def test_the_system_tab_lists_the_platform_catalogue(panel):
    tab = panel.system_tab
    ids = _column(tab.table, tab.COL_ID)

    assert "SYS.READY" in ids
    assert "REQ.SEC.ARM_ALL" in ids
    assert len(ids) >= 40


def test_nothing_in_the_system_tab_can_be_edited(panel):
    from PySide6.QtWidgets import QAbstractItemView

    assert panel.system_tab.table.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
    assert not hasattr(panel.system_tab, "add_button")


def test_the_system_tab_says_in_words_that_nothing_is_added_here(panel):
    from PySide6.QtWidgets import QLabel

    texts = " ".join(label.text() for label in panel.system_tab.findChildren(QLabel))
    assert "NOTHING IS ADDED HERE" in texts
    assert "contract" in texts


def test_the_direction_column_separates_reading_from_commanding(panel):
    tab = panel.system_tab
    rows = {_cell(tab.table, r, tab.COL_ID): _cell(tab.table, r, tab.COL_DIRECTION)
            for r in range(tab.table.rowCount())}

    assert rows["SYS.READY"] == "read"
    assert rows["REQ.SEC.ARM_ALL"] == "write from logic"


def test_the_runtime_column_says_whether_the_controller_answers(panel):
    tab = panel.system_tab
    rows = {_cell(tab.table, r, tab.COL_ID): _cell(tab.table, r, tab.COL_RUNTIME)
            for r in range(tab.table.rowCount())}

    assert rows["SYS.READY"] == "supported"


def test_the_search_box_filters_on_content_not_only_on_the_identifier(panel):
    tab = panel.system_tab

    tab.search_edit.setText("dozór")
    visible = [_cell(tab.table, r, tab.COL_ID) for r in range(tab.table.rowCount())
               if not tab.table.isRowHidden(r)]

    assert visible, "a Polish description in the catalogue found nothing"
    # "dozór" appears only in the alarm system's own descriptions, and
    # that subsystem now spans two namespaces: its STATE under
    # SEC.SYSTEM.*, and the requests the logic issues under REQ.SEC.*.
    assert all(v.startswith(("SEC.", "REQ.SEC.")) for v in visible), visible
    assert any(v.startswith("REQ.SEC.") for v in visible), (
        "the request half of the alarm system was not searched at all")


def test_clearing_the_search_brings_everything_back(panel):
    tab = panel.system_tab
    total = tab.table.rowCount()

    tab.search_edit.setText("SYS.READY")
    tab.search_edit.setText("")

    assert sum(1 for r in range(total) if not tab.table.isRowHidden(r)) == total
