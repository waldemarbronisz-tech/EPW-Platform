"""Backup and restore at the cabinet.

This is the interface that must not need a laptop, a network or Studio:
somebody is standing in front of a spare controller with the dead one's
backup on a memory stick.

Two things matter here and neither is about the bundle itself (that is
proved in runtime/epw_os/tests/): that a restore shows what it is about
to overwrite BEFORE it does it, and that afterwards it hands over the
list of secrets nobody can restore - because a controller that comes
back silently missing every PIN is worse than one that says so.
"""
import gzip
import json

import pytest
from PySide6.QtWidgets import QFileDialog, QMessageBox

from gui_smoke._mocks import (MockAccessManager, MockCommandManager,
                              MockControllableAccessManager, MockProjectManager, MockTagManager)


class _Core:
    """Only what the panel calls on EPWCore."""

    def __init__(self, bundle=b"bundle-bytes", result=None):
        self.bundle = bundle
        self.result = result or {"success": True, "reason": "", "checklist": []}
        self.backups, self.restores = [], []

    def backup_bundle(self, actor="", level=None):
        self.backups.append((actor, level))
        return self.bundle

    def restore_from_backup(self, data, actor="", level=None, restore_audit=False):
        self.restores.append((data, actor, level))
        return self.result


CHECKLIST = [
    {"kind": "level_pins", "detail": "Operator, Engineer"},
    {"kind": "user", "id": "U1", "detail": "Kowalski", "needs": ["code", "token"]},
    {"kind": "mqtt_password", "detail": "homeassistant.local"},
]


def _window(make_window, core, level="Engineer"):
    access = MockControllableAccessManager()
    access.level = level
    window = make_window(MockTagManager(), MockCommandManager(), access, MockProjectManager(),
                         controller_backup_core=core)
    window.window().request_access = lambda required: True
    return window


def _fake_bundle(tmp_path, summary=None):
    """A file the panel can read with the real reader."""
    from epw_os.core import controller_backup

    payload = {
        "format": controller_backup.BACKUP_FORMAT,
        "schema_version": controller_backup.BACKUP_SCHEMA_VERSION,
        "meta": {"project_name": "Kotłownia", "project_revision": 7,
                 "created_at": 0, "created_by": "Panel:Engineer"},
        "project": None,
        "state": {"switching_counters": {"ADA1.DO.1": {}},
                  "intrusion_state": {"armed_zones": ["Z1"]}},
        "local": {}, "audit": [],
        "secrets": {"users": [{"id": "U1", "name": "Kowalski", "had_code": True,
                               "had_remote_token": True}],
                    "level_pins_set": ["Operator", "Engineer"],
                    "api_tokens_set": False, "mqtt_password_set": True,
                    "mqtt_broker": "homeassistant.local"},
    }
    payload["checksum"] = controller_backup._checksum(payload)
    path = tmp_path / "from-the-dead-one.epwbak"
    path.write_bytes(gzip.compress(json.dumps(payload).encode("utf-8")))
    return path


# --- taking one ---------------------------------------------------------------

def test_a_backup_is_written_where_the_engineer_asked(make_window, monkeypatch, tmp_path):
    core = _Core(bundle=b"the-bundle")
    window = _window(make_window, core)
    target = tmp_path / "saved.epwbak"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(target), "")))

    window._save_controller_backup()

    assert target.read_bytes() == b"the-bundle"
    assert core.backups == [("Panel:Engineer", "Engineer")]


def test_backing_up_is_engineer_only(make_window, monkeypatch, tmp_path):
    core = _Core()
    window = _window(make_window, core, level="Operator")
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: pytest.fail("asked for a file below Engineer")))

    window._save_controller_backup()

    assert core.backups == []


def test_a_panel_with_no_controller_behind_it_says_so(make_window, monkeypatch):
    window = _window(make_window, None)
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: pytest.fail("asked for a file with no core")))

    window._save_controller_backup()  # must not raise


def test_cancelling_the_file_dialog_takes_no_backup(make_window, monkeypatch):
    core = _Core()
    window = _window(make_window, core)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: ("", "")))

    window._save_controller_backup()

    assert core.backups == []


# --- putting one back ----------------------------------------------------------

def test_a_restore_shows_what_it_will_overwrite_before_it_does(make_window, monkeypatch, tmp_path):
    """A restore overwrites a running controller. Somebody has to be
    able to look first."""
    core = _Core(result={"success": True, "reason": "", "checklist": CHECKLIST})
    window = _window(make_window, core)
    path = _fake_bundle(tmp_path)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(path), "")))
    asked = []
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: asked.append(a[2]) or QMessageBox.Yes))

    window._restore_controller_backup()

    assert asked, "nothing was shown before overwriting a running controller"
    assert "Kotłownia" in asked[0], asked[0]
    assert "Z1" in asked[0], "and which zones were armed at the time"
    assert core.restores, "the restore did not happen after the confirmation"


def test_saying_no_restores_nothing(make_window, monkeypatch, tmp_path):
    core = _Core()
    window = _window(make_window, core)
    path = _fake_bundle(tmp_path)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(path), "")))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.No))

    window._restore_controller_backup()

    assert core.restores == []


def test_a_file_that_is_not_a_backup_never_reaches_the_controller(make_window, monkeypatch, tmp_path):
    core = _Core()
    window = _window(make_window, core)
    junk = tmp_path / "holiday-photo.epwbak"
    junk.write_bytes(b"not a backup at all")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(junk), "")))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: pytest.fail("asked about an unreadable file")))

    window._restore_controller_backup()

    assert core.restores == []


def test_restoring_is_engineer_only(make_window, monkeypatch, tmp_path):
    core = _Core()
    window = _window(make_window, core, level="Operator")
    monkeypatch.setattr(QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: pytest.fail("asked for a file below Engineer")))

    window._restore_controller_backup()

    assert core.restores == []


# --- the checklist, which is the point of the whole design ---------------------

def test_the_checklist_is_rendered_as_something_a_person_can_work_through():
    from epw_os.gui.main_window import _checklist_lines

    lines = _checklist_lines(CHECKLIST)

    assert len(lines) == 3
    assert any("Operator, Engineer" in line for line in lines), "which PINs"
    assert any("Kowalski" in line for line in lines), "and who"
    assert any("homeassistant.local" in line for line in lines), "and which broker"


def test_an_empty_checklist_renders_to_nothing_rather_than_to_a_heading():
    from epw_os.gui.main_window import _checklist_lines

    assert _checklist_lines([]) == []
