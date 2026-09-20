"""The help section, after the owner's instruction "rozbuduj dzial pomoc
bo jest strasznie ubogi, rozpisz wszystkie funkcje jak sie programuje
krok po kroku".

Help rots quietly: a topic renamed in one language and not the other, a
cross-reference to a topic that was merged away, a new panel whose F1
lands nowhere. None of that shows up when you open the panel and it
looks fine. These tests are what notices.
"""
import re
import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from studio.shell.help._manifest import CHAPTERS, TOPICS
from studio.shell.project_panels import HelpPanel, load_help_topic_markdown

_KEYS = [entry[0] for entry in TOPICS]
_HELP_DIR = Path(__file__).resolve().parents[1] / "help"


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def _body(key, lang="pl"):
    return load_help_topic_markdown(key, lang)


# --- the manifest and the files agree ----------------------------------------

def test_every_topic_has_a_file_in_both_languages():
    for key in _KEYS:
        for lang in ("pl", "en"):
            text = _body(key, lang)
            assert "brak pliku pomocy" not in text, f"{key}/{lang}"
            assert text.lstrip().startswith("#"), f"{key}/{lang} has no heading"


def test_no_orphan_files_left_behind_by_a_renamed_topic():
    """A topic removed from the manifest leaves its .md file on disk,
    where nothing reaches it and nothing notices it is stale."""
    for lang in ("pl", "en"):
        on_disk = {path.stem for path in (_HELP_DIR / lang).glob("*.md")}
        assert on_disk == set(_KEYS), f"{lang}: {on_disk ^ set(_KEYS)}"


def test_both_languages_carry_the_same_topics_in_the_same_order():
    """The generator exists precisely so a topic cannot be added to one
    language and forgotten in the other."""
    for key, title_pl, title_en, chapter in TOPICS:
        assert title_pl and title_en, key
        assert chapter in dict((c[0], c) for c in CHAPTERS), f"{key}: unknown chapter {chapter}"


def test_every_chapter_has_at_least_one_topic():
    used = {entry[3] for entry in TOPICS}
    for chapter_key, _pl, _en in CHAPTERS:
        assert chapter_key in used, f"empty chapter: {chapter_key}"


# --- cross-references --------------------------------------------------------

_LINK = re.compile(r"\]\(help://([a-z0-9_]+)\)")


def test_every_cross_reference_points_at_a_topic_that_exists():
    for key in _KEYS:
        for lang in ("pl", "en"):
            for target in _LINK.findall(_body(key, lang)):
                assert target in _KEYS, f"{key}/{lang} links to a missing topic: {target}"


def test_the_step_by_step_topic_really_walks_the_whole_tree():
    """The owner asked for "jak sie programuje krok po kroku" - the
    walkthrough is worth nothing if it skips a department, so this pins
    that it reaches every one of them."""
    for lang in ("pl", "en"):
        linked = set(_LINK.findall(_body("workflow", lang)))
        for key in ("info", "devices", "locations", "io_cards", "points", "apparatus",
                    "screens", "logic", "zones", "lines", "intrusion_users",
                    "protection_electrical", "protection_process", "validation", "controller"):
            assert key in linked, f"workflow/{lang} never sends you to {key}"


def test_no_topic_is_a_dead_end_stub():
    """"Strasznie ubogi" was the complaint. A topic shorter than this is
    a title with a sentence under it, which is what was there before."""
    for key in _KEYS:
        for lang in ("pl", "en"):
            assert len(_body(key, lang)) > 700, f"{key}/{lang} is still a stub"


# --- F1 reaches something for every branch of the tree -----------------------

def test_every_tree_branch_has_a_help_topic():
    """F1 maps a tree branch to a topic key by hand; a branch added
    without its topic silently opens nothing. That is exactly what had
    happened to the alarm system's users."""
    from studio.shell.main_window import _HELP_TOPIC_BY_TREE_KEY

    for tree_key, topic_key in _HELP_TOPIC_BY_TREE_KEY.items():
        assert topic_key in _KEYS, f"F1 on '{tree_key}' opens a topic that does not exist: {topic_key}"


# --- the panel itself --------------------------------------------------------

class _Window:
    pass


def test_the_panel_shows_chapters_with_their_topics_under_them(app):
    panel = HelpPanel(_Window())
    try:
        tree = panel.topic_tree
        assert tree.topLevelItemCount() == len(CHAPTERS)
        leaves = sum(tree.topLevelItem(i).childCount() for i in range(tree.topLevelItemCount()))
        assert leaves == len(TOPICS)
        # A chapter is a heading: selecting one must not be possible,
        # because there is nothing to show for it.
        from PySide6.QtCore import Qt
        assert not (tree.topLevelItem(0).flags() & Qt.ItemFlag.ItemIsSelectable)
    finally:
        panel.deleteLater()


def test_selecting_a_topic_renders_it(app):
    panel = HelpPanel(_Window())
    try:
        panel.select_topic("workflow")
        assert "krok" in panel.viewer.toPlainText().lower() or "step" in panel.viewer.toPlainText().lower()
    finally:
        panel.deleteLater()


def test_a_cross_reference_navigates_instead_of_opening_a_browser(app):
    """The whole reason the links are written as help:// - this help is
    offline and has no business reaching the network."""
    from PySide6.QtCore import QUrl

    panel = HelpPanel(_Window())
    try:
        panel.select_topic("workflow")
        panel._on_anchor_clicked(QUrl("help://points"))
        assert panel._current_key() == "points"
        assert panel.viewer.openExternalLinks() is False
    finally:
        panel.deleteLater()


def test_an_unknown_topic_key_is_a_no_op_not_a_crash(app):
    panel = HelpPanel(_Window())
    try:
        panel.select_topic("there_is_no_such_topic")
        assert panel._current_key() in _KEYS
    finally:
        panel.deleteLater()
