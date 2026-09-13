"""feat/library-recent-and-search: the Device Explorer's search box.

The tree lists EVERY channel of every card - 64 rows per ELA before a
project has a single analog point - and had no way to narrow it at all.
What is pinned here is not that a box exists but that it behaves the way
the block library's own search already does: it hides what does not
match, it hides a branch only once nothing under it is left, and it
opens whatever still has results (results left inside a collapsed branch
look like no results), and it survives a rebuild of the tree.
"""
import pytest
from PySide6.QtWidgets import QApplication

from logic_studio.core.project import Project
from logic_studio.core.device_model import DeviceModel


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _panel():
    from logic_studio.ui.panels.device_explorer import DeviceExplorerPanel

    project = Project()
    DeviceModel.set_ela_devices(project, ["ELA01"])
    DeviceModel.set_ada_devices(project, ["ADA01"])
    return DeviceExplorerPanel(project=project), project


def _visible_leaves(panel):
    """Every leaf currently on show, by its label."""
    from logic_studio.ui.panels.device_explorer import TYPE_ID_ROLE

    found = []

    def walk(item):
        if item.isHidden():
            return
        if item.data(0, TYPE_ID_ROLE):
            found.append(item.text(0))
        for i in range(item.childCount()):
            walk(item.child(i))

    root = panel.tree.topLevelItem(0)
    if root is not None:
        walk(root)
    return found


def test_everything_is_visible_with_an_empty_search():
    _app()
    panel, _ = _panel()

    leaves = _visible_leaves(panel)
    assert len(leaves) > 1
    assert any("ELA01" in label for label in leaves)
    assert any("ADA01" in label for label in leaves)


def test_search_narrows_to_matching_channels_only():
    _app()
    panel, _ = _panel()

    panel.search_box.setText("DI.6")

    leaves = _visible_leaves(panel)
    assert leaves, "a real address must still be findable"
    assert all(label.endswith("DI.6") for label in leaves)


def test_punctuation_and_case_never_decide_whether_a_channel_is_found():
    """An address is read off a terminal label, not retyped from the
    format's own punctuation."""
    _app()
    panel, _ = _panel()

    panel.search_box.setText("ela01 di 6")
    spaced = _visible_leaves(panel)

    panel.search_box.setText("ELA01.DI.6")
    dotted = _visible_leaves(panel)

    assert spaced == dotted
    assert spaced


def test_a_branch_with_nothing_left_in_it_is_hidden_too():
    _app()
    panel, _ = _panel()

    panel.search_box.setText("ADA01")

    root = panel.tree.topLevelItem(0)
    branches = {root.child(i).text(0): root.child(i) for i in range(root.childCount())}
    ela = next(item for name, item in branches.items() if name.startswith("ELA01"))
    ada = next(item for name, item in branches.items() if name.startswith("ADA01"))

    assert ela.isHidden()
    assert not ada.isHidden()
    # ...and what is left is opened, so the results are actually on screen.
    assert ada.isExpanded()


def test_a_search_that_matches_nothing_leaves_no_leaves_showing():
    _app()
    panel, _ = _panel()

    panel.search_box.setText("zzzz-nie-ma-takiego")

    assert _visible_leaves(panel) == []


def test_a_rebuild_re_applies_whatever_is_typed():
    """Adding a card while a search is active must not silently show the
    whole tree back."""
    _app()
    panel, project = _panel()

    panel.search_box.setText("ADA01")
    before = _visible_leaves(panel)
    assert before

    DeviceModel.set_ela_devices(project, ["ELA01", "ELA02"])
    panel.set_project(project)

    after = _visible_leaves(panel)
    assert all("ADA01" in label for label in after)
