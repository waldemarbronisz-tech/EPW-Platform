"""Owner 2026-09-24, "Nagłówki - robimy sprzątanie": the project settings
dialog's table headers come from the interface language, not from
English literals in the code."""
import os
import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from logic_studio import i18n  # noqa: E402
from logic_studio.core.device_model import DeviceModel  # noqa: E402
from logic_studio.core.project import Project  # noqa: E402
from logic_studio.ui import dialogs  # noqa: E402
from logic_studio.ui.dialogs import ProjectSettingsDialog  # noqa: E402
from shared.logic.blocks import register_builtin_blocks  # noqa: E402


@pytest.fixture(autouse=True)
def _restore_language():
    before = i18n.get_language()
    yield
    i18n.set_language(before)


def _dialog():
    QApplication.instance() or QApplication([])
    register_builtin_blocks()
    project = Project()
    DeviceModel.set_ela_devices(project, ["ELA01"])
    DeviceModel.set_ada_devices(project, ["ADA01"])
    project.settings["internal_bits"] = [{"name": "START", "type": "BOOL", "retentive": False, "direction": "IN",
                                          "panel_level": "User", "remote_write": False, "category": "",
                                          "label": "", "description": "Start"}]
    return ProjectSettingsDialog(project)


def _headers(table):
    return [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]


def test_the_headers_are_polish_in_polish():
    i18n.set_language("pl")
    dialog = _dialog()
    try:
        assert _headers(dialog.table) == ["Adres", "Nazwa", "Jednostka", "Min", "Max", "Kierunek"]
        assert _headers(dialog.signals_table) == ["Nazwa", "Typ", "Retencja", "Kierunek", "Kategoria", "Etykieta",
                                                  "Opis", "Użycia"]
        assert _headers(dialog.io_labels_table) == ["Adres", "Etykieta", "Użycia"]
    finally:
        dialog.close()


def test_the_headers_are_english_in_english():
    i18n.set_language("en")
    dialog = _dialog()
    try:
        assert _headers(dialog.table) == ["Address", "Name", "Unit", "Min", "Max", "Direction"]
        assert _headers(dialog.signals_table) == ["Name", "Type", "Retentive", "Direction", "Category", "Label",
                                                  "Description", "Uses"]
        assert _headers(dialog.io_labels_table) == ["Address", "Label", "Uses"]
    finally:
        dialog.close()


def test_every_header_key_exists_in_both_languages_and_no_literal_is_left_in_the_code():
    keys = (ProjectSettingsDialog.COLUMN_KEYS + ProjectSettingsDialog.SIGNAL_COLUMN_KEYS
            + ProjectSettingsDialog.IO_LABEL_COLUMN_KEYS)
    for language in ("pl", "en"):
        i18n.set_language(language)
        for key in keys:
            assert i18n.tr(f"settings.col_{key}") != f"settings.col_{key}", (language, key)
    text = Path(dialogs.__file__).read_text(encoding="utf-8")
    assert "setHorizontalHeaderLabels(self.COLUMNS)" in text
    assert '["Address", "Name"' not in text and '["Name", "Type", "Retentive"' not in text,         "no English header lists in the code"


def test_the_column_lists_keep_their_old_names_for_the_code_that_reads_them():
    i18n.set_language("pl")
    dialog = _dialog()
    try:
        assert dialog.COLUMNS == _headers(dialog.table)
        assert dialog.SIGNAL_COLUMNS == _headers(dialog.signals_table)
        assert dialog.IO_LABEL_COLUMNS == _headers(dialog.io_labels_table)
        assert len(dialog.COLUMNS) == dialog.table.columnCount()
    finally:
        dialog.close()
