"""Task „runtime czyta projekt.epw", punkt 2, on the panel: the project's
analog outputs are visible on the Control Outputs page and an Engineer can
set one - in engineering units, never the raw register number.
"""
from PySide6.QtWidgets import QPushButton

from gui_smoke._mocks import (MockAuditLogger, MockCommandManager, MockControllableAccessManager, MockProjectManager,
                              MockTagManager)

_VALVE = {"tag": "ADA1.AO.1", "description": "Zawór mieszający", "technical_note": "",
          "signal_type": "4-20mA", "raw_min": 4.0, "raw_max": 20.0, "eng_min": 0.0, "eng_max": 100.0,
          "unit": "%", "decimals": 0}
_SETPOINT = {"tag": "ADA1.AO.2", "description": "Zadana temperatura", "technical_note": "",
             "signal_type": "4-20mA", "raw_min": 4.0, "raw_max": 20.0, "eng_min": 0.0, "eng_max": 120.0,
             "unit": "°C", "decimals": 1}


class _TagsWithAnalogOutputs(MockTagManager):
    """MockTagManager plus what the analog-output section reads: the
    project's AO points, their live raw values, and the write path."""

    def __init__(self, points=(_VALVE, _SETPOINT), values=None):
        super().__init__()
        self._points = [dict(p) for p in points]
        self._values = dict(values or {})
        self.written = []
        self.result = {"success": True, "reason": "", "raw": None}

    def get_analog_output_points(self):
        return [dict(p) for p in self._points]

    def get_value(self, name):
        return self._values.get(name)

    def write_analog_output(self, tag_name, value, actor="", level=None):
        self.written.append((tag_name, value, actor, level))
        return dict(self.result)


def _access(level):
    access = MockControllableAccessManager()
    if level != "User":
        assert access.attempt_login(level, MockControllableAccessManager.CORRECT_PIN)
    return access


def _page(make_window, tag_manager, level="Engineer", audit=None):
    window = make_window(tag_manager, MockCommandManager(), _access(level), MockProjectManager(),
                         audit or MockAuditLogger())
    return window, window.page_do


def _set_buttons(page):
    return [page.analog_table.cellWidget(row, 4).findChild(QPushButton)
            for row in range(page.analog_table.rowCount())]


def test_the_page_lists_the_projects_analog_outputs_with_their_descriptions(make_window):
    tags = _TagsWithAnalogOutputs(values={"ADA1.AO.1": 12.0})  # 12 mA on a 4-20 mA / 0-100 % output
    _window, page = _page(make_window, tags)

    assert page.analog_table.isVisibleTo(page) and page.analog_title.isVisibleTo(page)
    assert [page.analog_table.item(r, 0).text() for r in range(page.analog_table.rowCount())] == [
        "ADA1.AO.1", "ADA1.AO.2"]
    assert page.analog_table.item(0, 1).text() == "Zawór mieszający"
    assert page.analog_table.item(0, 2).text() == "50 %"   # the raw value read in engineering units
    assert page.analog_table.item(1, 2).text() == "-"       # never written yet


def test_a_project_without_analog_outputs_shows_no_section_at_all(make_window):
    _window, page = _page(make_window, _TagsWithAnalogOutputs(points=()))

    assert page.analog_table.rowCount() == 0
    assert not page.analog_table.isVisibleTo(page)
    assert not page.analog_title.isVisibleTo(page)


def test_the_set_button_exists_only_at_engineer(make_window):
    for level, expected in (("User", False), ("Operator", False), ("Engineer", True)):
        _window, page = _page(make_window, _TagsWithAnalogOutputs(), level=level)
        assert all(bool(button) == expected for button in _set_buttons(page)), level


def test_setting_a_value_sends_it_in_engineering_units_and_refreshes_the_row(make_window, monkeypatch):
    from epw_os.gui.pages import page_control_outputs as module

    tags = _TagsWithAnalogOutputs(values={"ADA1.AO.1": 4.0})
    _window, page = _page(make_window, tags)

    monkeypatch.setattr(module.AnalogOutputDialog, "exec", lambda self: 1)
    monkeypatch.setattr(module.AnalogOutputDialog, "result_value", lambda self: 65.0)
    tags._values["ADA1.AO.1"] = 14.4  # what the driver reports back for 65 %

    assert page.set_analog_output(0) is True
    assert tags.written == [("ADA1.AO.1", 65.0, "Engineer", "Engineer")]
    assert page.analog_table.item(0, 2).text() == "65 %"


def test_below_engineer_nothing_is_written_and_the_denial_is_audited(make_window, monkeypatch):
    from epw_os.gui.pages import page_control_outputs as module

    tags = _TagsWithAnalogOutputs()
    audit = MockAuditLogger()
    _window, page = _page(make_window, tags, level="Operator", audit=audit)

    monkeypatch.setattr(module.AnalogOutputDialog, "exec", lambda self: 1)
    assert page.set_analog_output(0) is False
    assert tags.written == []
    assert any(entry[0] == "ACCESS_DENIED" and "analog output" in entry[2].lower() for entry in audit.entries), \
        audit.entries


def test_a_refused_write_is_reported_and_leaves_the_row_alone(make_window, monkeypatch):
    from epw_os.gui.pages import page_control_outputs as module
    from PySide6.QtWidgets import QMessageBox

    tags = _TagsWithAnalogOutputs(values={"ADA1.AO.1": 12.0})
    tags.result = {"success": False, "reason": "Driver MODBUS did not write ADA1.AO.1.", "raw": None}
    _window, page = _page(make_window, tags)

    monkeypatch.setattr(module.AnalogOutputDialog, "exec", lambda self: 1)
    monkeypatch.setattr(module.AnalogOutputDialog, "result_value", lambda self: 80.0)
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *args, **kwargs: warnings.append(args)))

    assert page.set_analog_output(0) is False
    assert warnings and "did not write" in warnings[0][2]
    assert page.analog_table.item(0, 2).text() == "50 %"  # unchanged
