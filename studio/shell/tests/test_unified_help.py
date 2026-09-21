"""One help for the whole Studio (owner, 2026-09-21: "help jeden, spójny
i powiązany, nie ważne w którym miejscu stoję" - and the languages must
not mix). help/unified.py joins Studio's topics, the screen editor's
exported chapters and the logic editor's store into one tree in Studio's
language; F1 and "?" from every editor land in it."""
import os
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings, QUrl
from PySide6.QtWidgets import QApplication

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from studio.shell.help.unified import UnifiedHelp, key_from_url, split_key  # noqa: E402
from studio.shell.i18n import get_language, set_language  # noqa: E402
from studio.shell.project_panels import HelpPanel  # noqa: E402


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def language():
    before = get_language()
    yield
    set_language(before)


class _Window:
    pass


def test_the_tree_holds_studio_and_both_editors_in_one_language(language):
    for lang, synoptic_title, logic_title in (("pl", "Ekrany", "Logika"), ("en", "Screens", "Logic")):
        set_language(lang)
        help_ = UnifiedHelp(lang)
        tops = [node.title for node in help_.tree()]
        assert tops[-2].startswith(synoptic_title) and tops[-1].startswith(logic_title)
        keys = help_.keys()
        assert "points" in keys and "synoptic/intro-what" in keys and "logic/concept_labels" in keys
        assert "logic/block:logic.and" in keys and "logic/shortcuts" in keys
        assert any(k.startswith("logic/category:") for k in keys)
        assert len(set(keys)) == len(keys)                      # no key twice, whatever the source


def test_every_source_speaks_the_chosen_language(language):
    set_language("pl")
    pl = UnifiedHelp("pl")
    assert "Czym jest EPW-Synoptic-Editor" in pl.markdown("synoptic/intro-what")
    assert "Etykiety, znaczniki" in pl.markdown("logic/concept_labels")
    assert "Skróty" in pl.markdown("logic/shortcuts") or "Skroty" in pl.markdown("logic/shortcuts")
    assert "krok" in pl.markdown("workflow").lower()
    set_language("en")
    en = UnifiedHelp("en")
    assert "What EPW-Synoptic-Editor Is" in en.markdown("synoptic/intro-what")
    assert "Labels, markers" in en.markdown("logic/concept_labels")
    assert "Keyboard shortcuts" in en.markdown("logic/shortcuts")
    assert "step" in en.markdown("workflow").lower()


def test_the_logic_editors_block_catalog_is_in_the_help(language):
    set_language("pl")
    help_ = UnifiedHelp("pl")
    page = help_.markdown("logic/block:logic.and")
    assert "Unknown block type" not in page and "logic.and" in page
    category = next(k for k in help_.keys() if k.startswith("logic/category:"))
    index = help_.markdown(category)
    assert "- [" in index and "help://logic/block:" in index     # its blocks, linked the namespaced way
    assert "## Piny" in page and "| Nazwa |" in page               # the generated page speaks Polish too
    set_language("en")
    assert "## Pins" in UnifiedHelp("en").markdown("logic/block:logic.and")


def test_cross_references_of_every_source_resolve_to_namespaced_keys(language):
    set_language("pl")
    help_ = UnifiedHelp("pl")
    logic = help_.markdown("logic/concept_labels")
    assert "(help:concept_" not in logic and "help://logic/concept_scan_cycle" in logic
    synoptic = help_.markdown("synoptic/intro-what")
    assert "help://synoptic/intro-platform" in synoptic
    assert "help://synoptic/intro-what" in help_.markdown("welcome") and "help://logic/welcome" in help_.markdown("welcome")
    assert key_from_url(QUrl("help://logic/block:logic.and")) == "logic/block:logic.and"
    assert key_from_url(QUrl("help://points")) == "points"
    assert key_from_url(QUrl("help:concept_stubs")) == "concept_stubs"
    assert split_key("logic/category:Bramki") == ("logic", "category:Bramki")
    assert split_key("points") == ("", "points")
    # Every help:// link in every topic names a topic that exists.
    import re
    keys = set(help_.keys())
    for key in keys:
        for m in re.finditer(r"\]\(help://([^)\s]+)\)", help_.markdown(key)):
            assert m.group(1) in keys, f"{key} links to {m.group(1)}"


def test_search_finds_topics_across_the_sources_and_an_unknown_topic_is_named(language):
    set_language("pl")
    help_ = UnifiedHelp("pl")
    hits = help_.search("zaślepka")
    assert "logic/concept_stubs" in hits
    hits = help_.search("aparat SWITCHED")
    assert any(h.startswith("synoptic/") for h in hits)
    assert help_.search("") == help_.keys()
    assert "synoptic/nope" in help_.markdown("synoptic/nope")


def test_the_panel_navigates_across_the_sources_and_filters_by_search(app, language):
    set_language("pl")
    panel = HelpPanel(_Window())
    try:
        panel.select_topic("logic/block:logic.and")
        assert panel._current_key() == "logic/block:logic.and" and "logic.and" in panel.viewer.toPlainText()
        panel._on_anchor_clicked(QUrl("help://synoptic/dev-switched"))
        assert panel._current_key() == "synoptic/dev-switched"
        panel._on_anchor_clicked(QUrl("help://logic/concept_stubs"))
        assert panel._current_key() == "logic/concept_stubs"
        panel.search_edit.setText("zaślepka")
        panel._apply_search()
        assert "logic/concept_stubs" in panel._items and "points" not in panel._items
        # A link to a topic the search hid still opens it - the search is cleared.
        panel.select_topic("points")
        assert panel._current_key() == "points" and panel.search_edit.text() == ""
        assert len(panel._items) > 100
    finally:
        panel.deleteLater()


class _FakeLogicWindow:
    def __init__(self):
        self.topic = "block:logic.and"

    def _context_help_topic(self):
        return self.topic


class _FakeLogicPanel:
    def __init__(self):
        self._mw = _FakeLogicWindow()

    def main_window(self):
        return self._mw

    def is_dirty(self):
        return False


class _FakeSynopticPanel:
    def __init__(self):
        self.state = {"canUndo": False, "canRedo": False, "isDirty": False, "hasSelection": False,
                      "helpTopic": "elem-meter", "helpRequest": {"topicId": "", "nonce": 0}}

    def is_page_ready(self):
        return True

    def query_state(self, callback):
        callback(dict(self.state))

    def push_live_values(self, values):
        pass


def test_f1_from_either_editor_opens_the_one_help_on_the_editors_own_topic(app, language, tmp_path):
    from studio.shell.main_window import StudioMainWindow, _TREE_ITEM_HELP, _TREE_ITEM_LOGIC, _TREE_ITEM_SCREENS
    from studio.shell.project_format import new_project, save_project
    from studio.shell.tests.test_controller_project_sync import _close
    set_language("pl")
    win = StudioMainWindow(settings=QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat))
    path = tmp_path / "projekt.epw"
    save_project(new_project("Help", author="t"), path)
    win._load_project_from_path(str(path))
    try:
        win._logic_panel = _FakeLogicPanel()
        win._active = _TREE_ITEM_LOGIC
        win._open_contextual_help()
        assert win._active == _TREE_ITEM_HELP and win._help_panel._current_key() == "logic/block:logic.and"

        win._synoptic_panel = _FakeSynopticPanel()
        win._active = _TREE_ITEM_SCREENS
        win._help_topics()
        assert win._help_panel._current_key() == "synoptic/elem-meter"

        # F1 pressed inside the screen editor: its state carries the request once.
        win._active = _TREE_ITEM_SCREENS
        win._apply_synoptic_toolbar_state({"canUndo": False, "canRedo": False, "isDirty": False, "hasSelection": False,
                                           "helpRequest": {"topicId": "sch-drawing-wire", "nonce": 3}})
        assert win._help_panel._current_key() == "synoptic/sch-drawing-wire"
        win._active = _TREE_ITEM_SCREENS
        win._help_panel.select_topic("points")
        win._apply_synoptic_toolbar_state({"canUndo": False, "canRedo": False, "isDirty": False, "hasSelection": False,
                                           "helpRequest": {"topicId": "sch-drawing-wire", "nonce": 3}})
        assert win._help_panel._current_key() == "points"          # the same request is not replayed
    finally:
        _close(win)
