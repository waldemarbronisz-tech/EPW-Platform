"""Data Retention Settings dialog + status-bar DB size warning (Task:
feature/retention-and-test-fix, B3+B4) - GUI-level checks. The retention
MECHANISM itself (purge logic, archive-before-delete, audit trail) is
covered headlessly in epw_os/tests/test_retention.py; this file is only
about the Settings menu entry's access gate, the dialog reading/applying
real Historian/AuditLogger config, and the status bar indicator.

Real (headless) Historian/AuditLogger/EventBus, not mocks - both are
Qt-free (see their own module docstrings), so there is nothing a mock
would save here versus just constructing the real thing, and a real
object cannot drift from itself (see gui_smoke/_mocks.py's own
docstring on when this project prefers that over a mock).

Three of the four tests below request `real_db` (gui_smoke/conftest.py) -
they pass a real Historian into MainWindow, and PageTrends
unconditionally queries it (get_distinct_tag_names()) at construction
whenever historian is not None, so these genuinely touch the database,
unlike every other gui_smoke test."""
from epw_os.core.events import EventBus
from epw_os.core.historian import Historian
from epw_os.core.audit_logger import AuditLogger

from gui_smoke._mocks import MockCommandManager, MockControllableAccessManager, MockProjectManager, MockTagManager


def _access_at(level):
    am = MockControllableAccessManager()
    if level != "User":
        assert am.attempt_login(level, MockControllableAccessManager.CORRECT_PIN)
    return am


def test_data_retention_menu_entry_is_engineer_only(make_window, real_db):
    for level, visible in (("User", False), ("Operator", False), ("Engineer", True)):
        access = _access_at(level)
        w = make_window(MockTagManager(), MockCommandManager(), access, MockProjectManager(),
                         audit_logger=AuditLogger(), historian=Historian(EventBus()))
        assert w._act_data_retention.isVisible() is visible, level
        assert w._act_data_retention.isEnabled() is visible, level


def test_dialog_shows_real_stats_and_applies_config_to_both_collaborators(make_window, tmp_path, real_db):
    access = _access_at("Engineer")
    audit_logger = AuditLogger()
    historian = Historian(EventBus())
    pm = MockProjectManager()
    w = make_window(MockTagManager(), MockCommandManager(), access, pm,
                     audit_logger=audit_logger, historian=historian)

    from epw_os.gui.widgets.data_retention_dialog import DataRetentionDialog
    dlg = DataRetentionDialog(historian, audit_logger, access, w)

    # DOWÓD (B3): real row counts/size shown, not a placeholder.
    assert "tag_history" in dlg.lbl_stats.text()

    dlg.spin_hist_days.setValue(30)
    dlg.spin_hist_rows.setValue(10000)
    dlg.spin_audit_days.setValue(180)
    archive_dir = str(tmp_path / "archive")
    dlg.edit_archive_dir.setText(archive_dir)
    dlg.chk_size_warning.setChecked(True)
    dlg.spin_size_threshold.setValue(250)
    dlg._save()

    assert historian.get_retention_config() == {"max_days": 30, "max_rows": 10000}
    audit_cfg = audit_logger.get_retention_config()
    assert audit_cfg["max_days"] == 180
    assert audit_cfg["archive_dir"] == archive_dir

    # DOWÓD (B4): persisted, survives a restart (a fresh read from the
    # same project_manager already IS "as if the app restarted" - same
    # reasoning every other project_manager-backed setting in this test
    # suite already uses).
    assert pm.get_historian_retention_config() == {"max_days": 30, "max_rows": 10000}
    assert pm.get_audit_retention_config()["max_days"] == 180
    assert pm.get_audit_retention_config()["archive_dir"] == archive_dir
    assert pm.get_db_size_warning_config() == {"enabled": True, "threshold_mb": 250}

    w.shutdown_gui()


def test_dialog_save_denied_below_engineer_even_calling_it_directly(make_window, real_db):
    """Defense in depth (same pattern every other Engineer-gated action
    in this app already has): even if something bypassed the menu's own
    hidden+disabled gate, the dialog's Save re-checks the level itself
    via Historian/AuditLogger.configure_retention(level=...)."""
    access = _access_at("Operator")
    audit_logger = AuditLogger()
    historian = Historian(EventBus())
    w = make_window(MockTagManager(), MockCommandManager(), access, MockProjectManager(),
                     audit_logger=audit_logger, historian=historian)

    from epw_os.gui.widgets.data_retention_dialog import DataRetentionDialog
    from PySide6.QtWidgets import QMessageBox
    dlg = DataRetentionDialog(historian, audit_logger, access, w)
    dlg.spin_hist_days.setValue(30)
    # The denied path pops a real QMessageBox.warning() - stubbed the
    # same way every other modal warning/confirmation popup in this test
    # suite already is (a real .exec() would block forever under the
    # offscreen QPA platform, waiting for a click that can never come).
    orig_warning = QMessageBox.warning
    QMessageBox.warning = staticmethod(lambda *a, **k: None)
    try:
        dlg._save()
    finally:
        QMessageBox.warning = orig_warning

    assert historian.get_retention_config()["max_days"] == 0, \
        "an Operator-level Save must not actually change Historian's retention"
    w.shutdown_gui()


def test_db_size_warning_indicator_hidden_by_default_and_shown_once_configured(make_window, monkeypatch):
    access = _access_at("Engineer")
    pm = MockProjectManager()
    w = make_window(MockTagManager(), MockCommandManager(), access, pm)
    assert w.lbl_sb_db_warning.isHidden(), "off by default (GRANICE) - no warning until explicitly configured"

    # A fixed, artificially large reported size (monkeypatched, not a
    # real multi-hundred-MB database) - deterministic regardless of
    # whatever this test's own (test) database file actually happens to
    # be sized at. _refresh_db_size_warning_indicator() re-imports
    # get_db_stats from its source module on every call (a lazy import,
    # not a module-level one in main_window.py), so patching it there is
    # what actually takes effect.
    import epw_os.db.database as _db_module
    monkeypatch.setattr(_db_module, "get_db_stats", lambda: {"file_size_bytes": 999 * 1024 * 1024})

    pm.set_db_size_warning_config(enabled=True, threshold_mb=500)
    w._refresh_db_size_warning_indicator()
    assert not w.lbl_sb_db_warning.isHidden(), \
        "must become visible once the database exceeds the configured threshold"
    assert "999" in w.lbl_sb_db_warning.text()
    w.shutdown_gui()
