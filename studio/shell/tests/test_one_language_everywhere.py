"""One language for the whole application.

Owner's instruction: "jeżeli polski to wszędzie ma być polski zarówno w
logice synoptyce itp, poki co jezyk jest polski a np biblioteki po
angielsku".

Studio is four interfaces in one window - the shell, the Synoptic
editor (a web view), Logic Studio (its own Qt application, still
runnable standalone) and the block library (whose English lives in the
block classes, not in a locale file). Each one has its own translation
layer, for reasons that are good individually and add up to a product
that was half Polish:

* the shell's choice was never saved, so every restart went back to
  English;
* Logic Studio had no translation layer at all;
* the Synoptic editor takes its language from the address it was opened
  with, so it stayed in whatever it was opened in;
* the block library had no Polish.

These tests hold that together. They are about the WIRING - that one
setting reaches all four - not about any particular sentence.
"""
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from studio.shell.logic_path import ensure_importable

ensure_importable()

from logic_studio import i18n as logic_i18n
from shared.logic import i18n as block_i18n
from shared.logic.blocks import register_builtin_blocks

# The library is empty until the block modules have been imported for
# their registration side effect - the same call Logic Studio's own
# startup makes (logic_studio/app.py).
register_builtin_blocks()
from studio.shell import i18n as shell_i18n
from studio.shell.main_window import LANGUAGE_SETTING, StudioMainWindow


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _english_afterwards():
    """Every other test in this suite expects the platform language."""
    yield
    shell_i18n.set_language("en")
    logic_i18n.set_language("en")


def _window(tmp_path, app):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    window = StudioMainWindow(settings=settings)
    return window, settings


def _close(window):
    from PySide6.QtCore import QTimer
    for timer in window.findChildren(QTimer):
        timer.stop()
    window.hide()
    window.deleteLater()


# --- the setting reaches everything -------------------------------------------

def test_choosing_polish_switches_the_shell_and_logic_studio(tmp_path, app):
    window, _settings = _window(tmp_path, app)
    try:
        window._set_language("pl")

        assert shell_i18n.get_language() == "pl"
        assert logic_i18n.get_language() == "pl", "Logic Studio stayed in English"
        assert block_i18n.category_label("Logic gates", logic_i18n.block_language()) == "Bramki logiczne"
    finally:
        _close(window)


def test_the_choice_survives_a_restart(tmp_path, app):
    window, settings = _window(tmp_path, app)
    try:
        window._set_language("pl")
        assert settings.value(LANGUAGE_SETTING) == "pl"
    finally:
        _close(window)

    shell_i18n.set_language("en")
    logic_i18n.set_language("en")
    again, _ = _window(tmp_path, app)
    try:
        assert shell_i18n.get_language() == "pl", "the language was not restored"
        assert logic_i18n.get_language() == "pl"
    finally:
        _close(again)


def test_the_window_is_built_in_the_restored_language_not_translated_afterwards(tmp_path, app):
    """Every widget reads tr() at construction time, so restoring the
    language after building would leave the first window half
    translated until something rebuilt it."""
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    settings.setValue(LANGUAGE_SETTING, "pl")
    shell_i18n.set_language("en")

    window = StudioMainWindow(settings=settings)
    try:
        assert window.windowTitle() == shell_i18n.tr("app.title")
        labels = [window.tree.topLevelItem(i).text(0) for i in range(window.tree.topLevelItemCount())]
        assert labels, "the tree was not built"
    finally:
        _close(window)


def test_an_unknown_saved_language_falls_back_instead_of_breaking(tmp_path, app):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    settings.setValue(LANGUAGE_SETTING, "kl")

    window = StudioMainWindow(settings=settings)
    try:
        assert shell_i18n.get_language() in ("en", "pl")
    finally:
        _close(window)


def test_changing_language_reloads_the_screen_editor(tmp_path, app):
    """It is a web view opened with ?lang=... - the only way to change
    its language is to reload it."""
    window, _settings = _window(tmp_path, app)
    called = []
    try:
        window._reload_synoptic_language = lambda: called.append(True)
        window._set_language("pl")
        assert called == [True]
    finally:
        _close(window)


def test_the_reload_reaches_the_panel_that_is_open(tmp_path, app):
    window, _settings = _window(tmp_path, app)
    reloaded = []
    try:
        class _Panel:
            def reload_language(self):
                reloaded.append(True)

        window._synoptic_panel = _Panel()
        window._reload_synoptic_language()
        assert reloaded == [True]
    finally:
        _close(window)


class _Loads:
    """Records what the editor was asked to load."""

    def __init__(self):
        self.urls = []

    def load(self, url):
        self.urls.append(url.toString())


def _panel_without_a_browser(port):
    """The real SynopticPanel.reload_language(), without constructing a
    real panel.

    Every other test in this suite uses a fake SynopticPanel, and for a
    good reason: the real one builds a QWebEngineView, which needs a
    browser process and does not survive `offscreen` in a CI container.
    Two tests here once built the real thing and turned the whole Shell
    job red.

    So the METHOD is exercised - it is the code under test - on an
    instance that was never __init__'d, with only the two attributes it
    touches.
    """
    from studio.shell.synoptic_panel import SynopticPanel

    panel = SynopticPanel.__new__(SynopticPanel)
    panel._served_port = port
    panel._view = _Loads()
    return panel


def test_the_screen_editor_reloads_itself_in_the_current_language(app):
    """The editor reads ?lang= once, at load. Reloading is how its
    language changes - and it has to be the language chosen NOW."""
    panel = _panel_without_a_browser(port=3456)

    shell_i18n.set_language("pl")
    panel.reload_language()
    assert panel._view.urls[-1].endswith("?lang=pl"), panel._view.urls

    shell_i18n.set_language("en")
    panel.reload_language()
    assert panel._view.urls[-1].endswith("?lang=en"), panel._view.urls


def test_a_screen_editor_whose_build_failed_is_not_reloaded(app):
    """Nothing is being served, so there is nothing to reload - and the
    language change must not turn that into a second error."""
    panel = _panel_without_a_browser(port=None)

    panel.reload_language()

    assert panel._view.urls == [], "reloaded with nothing served"


def test_no_screen_editor_open_is_not_an_error(tmp_path, app):
    window, _settings = _window(tmp_path, app)
    try:
        window._synoptic_panel = None
        window._set_language("pl")  # must not raise
        assert shell_i18n.get_language() == "pl"
    finally:
        _close(window)


# --- the library, which is what the complaint was about -----------------------

def test_the_block_library_tree_is_polish_when_polish_is_chosen(app):
    from logic_studio.ui.panels.library import LibraryPanel

    logic_i18n.set_language("pl")
    panel = LibraryPanel()
    try:
        labels = [panel.tree.topLevelItem(i).text(0) for i in range(panel.tree.topLevelItemCount())]
        assert "Bramki logiczne" in labels, labels
        assert "Logic gates" not in labels
        assert "Ostatnio używane" in labels
    finally:
        panel.deleteLater()


def test_a_block_keeps_its_iec_mnemonic_but_gets_a_polish_description(app):
    from logic_studio.ui.panels.library import LibraryPanel

    logic_i18n.set_language("pl")
    panel = LibraryPanel()
    try:
        assert panel._display_name("logic.and") == "AND", "an IEC mnemonic must not be renamed"
        assert panel._description("logic.and").startswith("Iloczyn logiczny")
        # A block whose name is a word, not a mnemonic, is translated.
        assert panel._display_name("system.button") == "Przycisk"
    finally:
        panel.deleteLater()


def test_search_finds_a_block_by_its_polish_name_and_by_its_english_one(app):
    from logic_studio.ui.panels.library import LibraryPanel

    logic_i18n.set_language("pl")
    panel = LibraryPanel()
    try:
        assert panel._matches("logic.and", "and"), "the mnemonic must keep working"
        assert panel._matches("logic.and", "iloczyn"), "and so must the Polish description"
        assert panel._matches("system.button", "przycisk")
        assert not panel._matches("logic.and", "zawór")
    finally:
        panel.deleteLater()


# --- Qt's own words: OK / Cancel and the dialogs -----------------------------

def test_qts_own_buttons_follow_the_language(tmp_path, app):
    """OK/Cancel/Yes/No are drawn and translated by Qt itself, from the
    .qm files PySide6 ships - not from our locale. A Polish Studio with
    an English "Cancel" under every dialog was exactly this translator
    missing (logic_studio/qt_translation.py)."""
    from PySide6.QtWidgets import QDialogButtonBox
    from logic_studio.qt_translation import installed_qt_translators, remove_qt_translations

    cancel, ok = QDialogButtonBox.StandardButton.Cancel, QDialogButtonBox.StandardButton.Ok
    window = StudioMainWindow(settings=QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat))
    try:
        window._set_language("pl")
        assert len(installed_qt_translators()) == 2                   # qtbase_pl + qt_pl
        box = QDialogButtonBox(ok | cancel)
        assert box.button(cancel).text() == "Anuluj"
        assert box.button(ok).text() == "OK"                          # Qt's Polish keeps "OK"

        # The proof it is the translator: take it away and Qt is English again.
        remove_qt_translations(app)
        assert QDialogButtonBox(cancel).button(cancel).text() == "Cancel"

        # English is Qt's source language - no translator at all, no "qtbase_en".
        window._set_language("pl")
        window._set_language("en")
        assert installed_qt_translators() == []
        assert QDialogButtonBox(cancel).button(cancel).text() == "Cancel"
    finally:
        remove_qt_translations(app)
        window.hide()          # not close(): a closing window asks about unsaved work, modally


def test_a_missing_qt_translation_file_is_a_warning_not_a_crash(app, caplog):
    import logging
    from logic_studio.qt_translation import install_qt_translations, installed_qt_translators, qt_translations_path

    with caplog.at_level(logging.WARNING, logger="logic_studio.qt_translation"):
        assert install_qt_translations(app, "xx") == []
    assert installed_qt_translators() == []
    assert any("qtbase_xx.qm" in r.getMessage() for r in caplog.records)
    assert qt_translations_path() in caplog.records[0].getMessage()   # the path comes from Qt, not from us


def test_the_saved_language_is_what_studio_starts_qt_in(tmp_path):
    from studio.shell.main_window import saved_language

    settings = QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat)
    assert saved_language(settings) == shell_i18n.get_language()
    settings.setValue(LANGUAGE_SETTING, "pl")
    assert saved_language(settings) == "pl"
    settings.setValue(LANGUAGE_SETTING, "klingon")
    assert saved_language(settings) == shell_i18n.get_language()
