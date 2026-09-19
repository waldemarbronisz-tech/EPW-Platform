"""SPEC-adjacent, task "co mamy do roboty" p. 1: Studio's controller panel
says what the controller is EXECUTING, not just whether it answers.

/api/v1/health only ever reports RUNNING/FAULT/DEGRADED for the whole
subsystem - which cannot tell "this project carries no logic" from "the
program was refused". The panel reads /api/v1/logic for that. Same fake
controller as the project-sync tests.
"""
from PySide6.QtWidgets import QApplication

from studio.shell.tests.test_controller_project_sync import (FakeController, _close, _quiet_boxes, _saved_project,
                                                             _window)


def _app():
    return QApplication.instance() or QApplication([])


RUNNING = {"configured": True, "loaded": True, "running": True, "block_count": 12, "cycle_time_ms": 100,
           "scan_count": 5000, "last_scan_ms": 0.9, "max_scan_ms": 2.4, "driven_outputs": ["ADA1.DO.1"],
           "last_error": ""}


def _panel_after_test(tmp_path, monkeypatch, logic):
    path = _saved_project(tmp_path, setting=25.0)
    controller = FakeController(path.read_bytes(), revision=1, logic=logic)
    win = _window(tmp_path, path, controller.url)
    _quiet_boxes(monkeypatch)
    panel = win._controller_panel
    panel._test_connection()
    return panel, win, controller


def test_a_running_program_is_reported_with_its_size_and_cycle(tmp_path, monkeypatch):
    _app()
    panel, win, controller = _panel_after_test(tmp_path, monkeypatch, RUNNING)
    try:
        text = panel.logic_label.text()
        assert "RUNNING" in text
        assert "12 block" in text and "100 ms" in text and "1 output" in text
    finally:
        _close(win)
        controller.close()


def test_a_refused_program_is_reported_with_its_reason(tmp_path, monkeypatch):
    _app()
    refused = dict(RUNNING, loaded=False, running=False, last_error="the checksum does not match")
    panel, win, controller = _panel_after_test(tmp_path, monkeypatch, refused)
    try:
        assert "NOT running" in panel.logic_label.text()
        assert "the checksum does not match" in panel.logic_label.text()
    finally:
        _close(win)
        controller.close()


def test_a_controller_without_logic_is_not_reported_as_broken(tmp_path, monkeypatch):
    _app()
    none_loaded = dict(RUNNING, configured=False, loaded=False, running=False)
    panel, win, controller = _panel_after_test(tmp_path, monkeypatch, none_loaded)
    try:
        assert "none" in panel.logic_label.text()
        assert "NOT running" not in panel.logic_label.text()
    finally:
        _close(win)
        controller.close()


def test_a_controller_too_old_to_answer_reports_unknown_not_an_error(tmp_path, monkeypatch):
    """An older EPW-OS has no /api/v1/logic at all. This panel's job is to
    say what it can see, not to fail over a missing extra."""
    _app()
    panel, win, controller = _panel_after_test(tmp_path, monkeypatch, None)
    try:
        assert "unknown" in panel.logic_label.text()
        # ...and the connection test itself still succeeded.
        assert "OK" in panel.status_label.text() or "ok" in panel.status_label.text().lower()
    finally:
        _close(win)
        controller.close()
