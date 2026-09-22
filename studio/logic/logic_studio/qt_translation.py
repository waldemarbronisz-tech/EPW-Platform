"""Qt's own words in the interface's language.

OK / Cancel / Yes / No, the file dialogs, the colour picker, the
context menu of a text field - none of that comes from our locale files:
Qt draws those widgets and translates them itself, from the .qm files
PySide6 ships (Qt/translations/qtbase_<lang>.qm and qt_<lang>.qm). With
no translator installed Qt speaks its source language, English - which
is how a Polish Studio ended up with an English "Cancel" under every
Polish dialog.

One translator set per application, installed at start (studio/main.py,
studio/logic/main.py) and replaced when the language changes
(StudioMainWindow._set_language). English means NO translator - Qt's
source language is English, there is no qtbase_en.qm and asking for one
would only produce a warning. The path comes from Qt itself
(QLibraryInfo), never from a hard-coded install location; a missing
file is logged and the application starts anyway, in English there.
"""
import logging

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QTranslator

log = logging.getLogger(__name__)

# qtbase: the widgets (buttons, dialogs, menus); qt: the compatibility
# catalogue that loads the rest of the module set.
QT_TRANSLATION_FILES = ("qtbase", "qt")
QT_SOURCE_LANGUAGE = "en"

_installed = []


def qt_translations_path() -> str:
    return QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)


def installed_qt_translators() -> list:
    return list(_installed)


def remove_qt_translations(app=None) -> int:
    app = app or QCoreApplication.instance()
    removed = 0
    for translator in _installed:
        if app is not None and app.removeTranslator(translator):
            removed += 1
    _installed.clear()
    return removed


def install_qt_translations(app, language: str) -> list:
    """Replaces whatever this module installed before with Qt's
    translations for `language`; returns the translators now installed
    (none for English, none when the files are missing)."""
    remove_qt_translations(app)
    if not language or language == QT_SOURCE_LANGUAGE:
        return []
    path = qt_translations_path()
    for name in QT_TRANSLATION_FILES:
        translator = QTranslator(app)
        if translator.load(f"{name}_{language}", path) and app.installTranslator(translator):
            _installed.append(translator)
        else:
            log.warning("Qt translation %s_%s.qm not found in %s - Qt's own buttons and dialogs stay English",
                        name, language, path)
    return list(_installed)
