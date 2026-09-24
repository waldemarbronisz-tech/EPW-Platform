"""Internal bits IN/OUT in Logic Studio: the compiler refuses a writing
block on an IN bit, the exporter carries the direction and writer fields
to the controller, and the settings dialog keeps what Studio's Signals
department set."""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

_LOGIC = Path(__file__).resolve().parents[1]
if str(_LOGIC) not in sys.path:
    sys.path.insert(0, str(_LOGIC))
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from logic_studio.core.device_model import DeviceModel  # noqa: E402
from logic_studio.core.project import Project  # noqa: E402
from shared.logic.blocks import register_builtin_blocks  # noqa: E402
from shared.logic.blocks.registry import BlockRegistry  # noqa: E402


def _app():
    return QApplication.instance() or QApplication([])


def _project(entries):
    register_builtin_blocks()
    p = Project()
    DeviceModel.set_ela_devices(p, ["ELA01"])
    DeviceModel.set_ada_devices(p, ["ADA01"])
    p.settings["internal_bits"] = entries
    return p


def _block(project, type_id, bit, name):
    block = BlockRegistry.create_block(type_id)
    block.properties["Bit"] = bit
    block.display_name = name
    project.add_block(block)
    block.short_id = name          # what the validator names a block by
    return block


def _validate(project):
    from logic_studio.compiler.validator import Validator
    errors, warnings = [], []
    Validator(project).run(errors, warnings)
    return errors, warnings


def test_a_writing_block_on_an_in_bit_is_a_compile_error_a_reader_is_not():
    _app()
    p = _project([{"name": "START", "type": "BOOL", "retentive": False, "direction": "IN"},
                  {"name": "ZEZW", "type": "BOOL", "retentive": False, "direction": "OUT"}])
    _block(p, "virtual.input", "START", "READ_START")
    _block(p, "virtual.output", "ZEZW", "WRITE_ZEZW")
    errors, _ = _validate(p)
    assert not [e for e in errors if "IN bit" in e], errors
    _block(p, "virtual.output", "START", "WRITE_START")
    errors, _ = _validate(p)
    hits = [e for e in errors if "M.START" in e and "IN bit" in e]
    assert len(hits) == 1 and "WRITE_START" in hits[0], errors


def test_an_out_bit_without_a_direction_field_still_compiles_as_before():
    _app()
    p = _project([{"name": "DRUT", "type": "BOOL", "retentive": False}])
    _block(p, "virtual.output", "DRUT", "W")
    _block(p, "virtual.input", "DRUT", "R")
    errors, _ = _validate(p)
    assert errors == []


def test_the_export_carries_direction_and_writers_to_the_controller():
    _app()
    from logic_studio.compiler.core import Compiler
    from logic_studio.compiler.exporter import Exporter
    p = _project([{"name": "START", "type": "BOOL", "retentive": False, "direction": "IN", "panel_level": "Engineer",
                   "remote_write": True, "description": "Start z panelu"}])
    _block(p, "virtual.input", "START", "R")
    compiler = Compiler(p)
    result = compiler.compile()
    assert result is not None, compiler.errors
    payload = Exporter(p, result["program"].execution_order).export()
    entry = next(e for e in payload["internal_bits"] if e["name"] == "START")
    assert entry["direction"] == "IN" and entry["panel_level"] == "Engineer" and entry["remote_write"] is True
    assert entry["description"] == "Start z panelu"


def test_the_settings_dialog_shows_the_direction_and_keeps_the_writer_fields(monkeypatch):
    _app()
    from logic_studio.ui.dialogs import ProjectSettingsDialog
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    p = _project([{"name": "START", "type": "BOOL", "retentive": False, "direction": "IN", "panel_level": "User",
                   "remote_write": True, "category": "", "label": "", "description": "Start"}])
    dialog = ProjectSettingsDialog(p)
    assert dialog.signals_table.cellWidget(0, 3).currentText() == "IN"
    dialog.signals_table.cellWidget(0, 3).setCurrentText("OUT")
    dialog._on_accept()
    dialog.apply_to_project()
    entry = p.settings["internal_bits"][0]
    assert entry["direction"] == "OUT"
    assert entry["panel_level"] == "User" and entry["remote_write"] is True, "Studio's writer fields must survive the dialog"
    assert entry["description"] == "Start"
