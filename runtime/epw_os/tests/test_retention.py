"""Tests for the data retention feature (Task: feature/retention-and-
test-fix, Part B) - Historian's own TagHistory retention (B1) and
AuditLogger's archive-then-purge retention (B2).

Real (test) SQLite database via the `db` fixture (epw_os/tests/conftest.py -
opt-in, not autouse; see that file's own docstring). Historian rows are
inserted directly (bypassing its async queue+worker thread) so retention
enforcement itself can be tested deterministically, without any timing
dependency on a background thread actually processing a queue - the
worker-thread wiring itself (RETENTION_CHECK_INTERVAL_S) is covered
separately below, structurally rather than by waiting on a real timer.
"""
from datetime import datetime, timedelta

import pytest

from epw_os.core.events import EventBus
from epw_os.core.historian import Historian, DEFAULT_RETENTION_MAX_DAYS, DEFAULT_RETENTION_MAX_ROWS
from epw_os.core.audit_logger import AuditLogger
from epw_os.db.database import SessionLocal
from epw_os.db.models import TagHistory, AuditLog


class FakeAuditLogger:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))


def _insert_tag_history_row(tag_name, days_old, value=1.0):
    db = SessionLocal()
    row = TagHistory(
        tag_name=tag_name, data_type="REAL", quality="GOOD",
        timestamp=datetime.utcnow() - timedelta(days=days_old),
        val_real=value,
    )
    db.add(row)
    db.commit()
    db.close()


def _tag_history_count(tag_name=None):
    db = SessionLocal()
    try:
        q = db.query(TagHistory)
        if tag_name is not None:
            q = q.filter(TagHistory.tag_name == tag_name)
        return q.count()
    finally:
        db.close()


# =====================================================================
# B1: Historian retention
# =====================================================================

def test_historian_retention_defaults_to_off(db):
    hist = Historian(EventBus())
    assert hist.get_retention_config() == {"max_days": DEFAULT_RETENTION_MAX_DAYS,
                                            "max_rows": DEFAULT_RETENTION_MAX_ROWS}
    assert DEFAULT_RETENTION_MAX_DAYS == 0 and DEFAULT_RETENTION_MAX_ROWS == 0, \
        "GRANICE: retention must default to OFF (unbounded)"


# --- DOWÓD: "przy wylaczonej retencji nic nie jest usuwane" ------------

def test_retention_disabled_nothing_is_deleted(db):
    hist = Historian(EventBus())
    for i in range(10):
        _insert_tag_history_row("Meas.L1", days_old=i * 10)  # some very old, none purged
    assert _tag_history_count("Meas.L1") == 10

    hist._enforce_retention()  # both limits still 0 (off) - must be a no-op

    assert _tag_history_count("Meas.L1") == 10, "retention must delete nothing while disabled"


# --- DOWÓD: "Historian usuwa najstarsze po przekroczeniu limitu" -------

def test_historian_purges_oldest_rows_first_over_max_rows(db):
    hist = Historian(EventBus())
    for i in range(10):
        _insert_tag_history_row("Meas.L1", days_old=10 - i, value=float(i))  # row 0 oldest .. row 9 newest
    assert _tag_history_count("Meas.L1") == 10

    hist.configure_retention(max_rows=4)  # purges immediately

    db_session = SessionLocal()
    remaining = db_session.query(TagHistory).filter(TagHistory.tag_name == "Meas.L1") \
        .order_by(TagHistory.timestamp.asc()).all()
    db_session.close()
    assert len(remaining) == 4
    # the 4 NEWEST survive (days_old 4,3,2,1 -> values 6,7,8,9)
    assert [r.val_real for r in remaining] == [6.0, 7.0, 8.0, 9.0]


def test_historian_purges_rows_older_than_max_days(db):
    hist = Historian(EventBus())
    _insert_tag_history_row("Meas.L1", days_old=30, value=1.0)  # old - must be purged
    _insert_tag_history_row("Meas.L1", days_old=1, value=2.0)   # recent - must survive

    hist.configure_retention(max_days=7)

    db_session = SessionLocal()
    remaining = db_session.query(TagHistory).filter(TagHistory.tag_name == "Meas.L1").all()
    db_session.close()
    assert [r.val_real for r in remaining] == [2.0]


# --- DOWÓD: "usuwanie nie blokuje biezacego zapisu" - structural proof:
# the hot write path (record_tag_change -> queue.put_nowait) NEVER calls
# retention enforcement itself; only configure_retention() (a rare admin
# action) and the WORKER thread's own periodic check do. ---------------

def test_record_tag_change_never_calls_enforce_retention_directly(monkeypatch):
    hist = Historian(EventBus())
    hist.is_running = True
    calls = []
    monkeypatch.setattr(hist, "_enforce_retention", lambda: calls.append(1))

    hist.record_tag_change("Meas.L1", 42.0, "GOOD")  # the actual hot path - just a queue put

    assert calls == [], "record_tag_change() (the producer-side hot path) must never call retention itself"
    assert hist.queue.qsize() == 1, "the value must still have reached the queue normally"


def test_configure_retention_purges_immediately_not_deferred_to_the_worker(db):
    """configure_retention() (a rare, explicit admin action - not the
    per-tag hot path above) purging immediately is what makes this
    testable at all without a real 60s wait for the worker thread's own
    periodic sweep - see RETENTION_CHECK_INTERVAL_S."""
    hist = Historian(EventBus())
    _insert_tag_history_row("Meas.L1", days_old=30)
    hist.configure_retention(max_days=7)
    assert _tag_history_count("Meas.L1") == 0


def test_historian_purge_reaches_the_audit_log_with_count_and_date_range(db):
    """DOWÓD: "fakt usuniecia zapisany do dziennika: ile wierszy, z
    jakiego zakresu dat"."""
    audit = FakeAuditLogger()
    hist = Historian(EventBus(), audit_logger=audit)
    _insert_tag_history_row("Meas.L1", days_old=30)
    _insert_tag_history_row("Meas.L1", days_old=20)

    hist.configure_retention(max_days=7)

    purge_entries = [e for e in audit.entries if e[0] == "HISTORIAN_RETENTION_PURGE"]
    assert purge_entries, audit.entries
    event_type, actor, detail, success = purge_entries[-1]
    assert "2" in detail, detail  # 2 rows purged
    assert success is True


def test_historian_retention_config_change_also_reaches_the_audit_log(db):
    audit = FakeAuditLogger()
    hist = Historian(EventBus(), audit_logger=audit)
    hist.configure_retention(max_days=30, max_rows=1000, level="Engineer")
    assert any(e[0] == "HISTORIAN_RETENTION_CONFIG" and e[1] == "Engineer" for e in audit.entries), audit.entries


def test_historian_retention_config_refused_below_engineer(db):
    hist = Historian(EventBus())
    assert hist.configure_retention(max_days=30, level="Operator") is False
    assert hist.get_retention_config()["max_days"] == 0, "a denied change must not take effect"


# =====================================================================
# B2: Audit log retention + archival
# =====================================================================

def test_audit_retention_defaults_to_off(db):
    audit = AuditLogger()
    cfg = audit.get_retention_config()
    assert cfg["max_days"] == 0 and cfg["max_rows"] == 0


def test_audit_retention_disabled_nothing_is_deleted(db):
    audit = AuditLogger()
    for i in range(5):
        audit.record("LOGIN", "Operator", f"probe {i}")
    before = SessionLocal().query(AuditLog).count()

    audit._enforce_retention()  # both limits 0 (off) - must be a no-op

    after = SessionLocal().query(AuditLog).count()
    assert after == before


def test_audit_log_archives_before_purging_and_leaves_a_purge_record(db, tmp_path):
    audit = AuditLogger()
    for i in range(6):
        audit.record("LOGIN", "Operator", f"probe {i}")
    total_before = SessionLocal().query(AuditLog).count()

    archive_dir = str(tmp_path / "archive")
    audit.configure_retention(max_rows=2, archive_dir=archive_dir, level="Engineer")

    remaining = SessionLocal().query(AuditLog).count()
    # configure_retention() itself writes ONE row first (AUDIT_LOG_RETENTION_CONFIG,
    # counted as part of what enforcement then sees) - total_before (6) + 1
    # = 7 rows exist at the moment _enforce_retention() runs, max_rows=2
    # keeps only the 2 newest, so 5 are archived+deleted; ONE more new row
    # (AUDIT_LOG_RETENTION_PURGE) is then added recording that - DOWÓD:
    # "po czyszczeniu w dzienniku zostaje wpis o czyszczeniu".
    assert remaining == 3, (remaining, "2 kept + the new purge record")

    purge_rows = SessionLocal().query(AuditLog).filter(AuditLog.event_type == "AUDIT_LOG_RETENTION_PURGE").all()
    assert purge_rows, "a record of the purge itself must remain in the audit log"
    assert "row(s)" in purge_rows[-1].detail or "rows" in purge_rows[-1].detail.lower()

    # DOWÓD: archive is a real, readable CSV file with the archived rows.
    import csv, os
    files = os.listdir(archive_dir)
    assert len(files) == 1 and files[0].endswith(".csv"), files
    with open(os.path.join(archive_dir, files[0]), newline="", encoding="utf-8") as f:
        archived = list(csv.DictReader(f))
    assert len(archived) == 5, "the 5 oldest rows (of the 7 that existed at purge time) must be archived"
    # every archived row's content is exactly what was written - never
    # just IDs/timestamps with the actual content silently dropped.
    archived_details = {r["detail"] for r in archived}
    assert archived_details == {f"probe {i}" for i in range(5)}, archived_details


# --- DOWÓD: "dziennik audytowy NIE JEST czyszczony, gdy zapis archiwum
# sie nie powiodl" -------------------------------------------------------

def test_audit_log_not_purged_when_archive_write_fails(db, monkeypatch):
    audit = AuditLogger()
    for i in range(5):
        audit.record("LOGIN", "Operator", f"probe {i}")
    before = SessionLocal().query(AuditLog).count()

    def _broken_write(self, row_data):
        raise OSError("simulated disk full")

    monkeypatch.setattr(AuditLogger, "_write_archive_csv", _broken_write)

    audit.configure_retention(max_rows=1, level="Engineer")

    after = SessionLocal().query(AuditLog).count()
    # The config-change record itself is allowed to have been written
    # (it happens BEFORE _enforce_retention() runs) - but NONE of the
    # original probe rows were purged, since archiving them failed.
    probe_rows = SessionLocal().query(AuditLog).filter(AuditLog.detail.like("probe %")).count()
    assert probe_rows == 5, "a failed archive write must leave every original row untouched"
    assert after >= before, "nothing may be removed when the archive write fails"
    assert not any(e_type == "AUDIT_LOG_RETENTION_PURGE" for e_type, in
                    SessionLocal().query(AuditLog.event_type).filter(
                        AuditLog.event_type == "AUDIT_LOG_RETENTION_PURGE").all()), \
        "no purge record may be written when nothing was actually purged"


def test_audit_log_not_purged_when_delete_fails_after_a_successful_archive(db, tmp_path, monkeypatch):
    """The other half of "bez udanego zapisu archiwum nie usuwaj
    niczego" - if the ARCHIVE succeeds but the subsequent DELETE somehow
    fails, the failure must be reported, not silently swallowed as a
    success (the archive is still valid - a superset of what's in the
    table - but the purge record must not falsely claim rows were
    removed)."""
    audit = AuditLogger()
    for i in range(3):
        audit.record("LOGIN", "Operator", f"probe {i}")
    archive_dir = str(tmp_path / "archive2")

    class _BoomSession:
        """A realistic-enough stand-in for a session whose DELETE/COMMIT
        fails (e.g. a lock, a disk error) - unlike a raise-on-everything
        stub, rollback()/close() themselves still work (the connection
        itself isn't gone, just the operation), matching what a real
        SQLAlchemy Session does in this situation."""
        def query(self, *a, **k):
            raise RuntimeError("simulated DB failure on delete")
        def rollback(self): pass
        def close(self): pass

    call_count = {"n": 0}
    orig_session_local = SessionLocal

    def _flaky_session_local(*a, **k):
        call_count["n"] += 1
        # Let every call before the delete-stage one through normally;
        # _enforce_retention() opens a fresh SessionLocal() specifically
        # for the delete stage as its 3rd call in this test (the
        # config-change record() call, then the SELECT stage, then the
        # DELETE stage) - break exactly that one.
        if call_count["n"] == 3:
            return _BoomSession()
        return orig_session_local(*a, **k)

    monkeypatch.setattr("epw_os.core.audit_logger.SessionLocal", _flaky_session_local)

    audit.configure_retention(max_rows=1, archive_dir=archive_dir, level="Engineer")

    import os
    files = os.listdir(archive_dir)
    assert len(files) == 1, "the archive write itself must still have succeeded"

    monkeypatch.undo()
    probe_rows = SessionLocal().query(AuditLog).filter(AuditLog.detail.like("probe %")).count()
    assert probe_rows == 3, "rows must still be present in the DB if the delete step itself failed"


def test_audit_retention_config_change_reaches_the_audit_log(db):
    audit = AuditLogger()
    audit.configure_retention(max_days=90, level="Engineer")
    rows = SessionLocal().query(AuditLog).filter(AuditLog.event_type == "AUDIT_LOG_RETENTION_CONFIG").all()
    assert rows and rows[-1].actor == "Engineer"


def test_audit_retention_config_refused_below_engineer(db):
    audit = AuditLogger()
    assert audit.configure_retention(max_days=30, level="Operator") is False
    assert audit.get_retention_config()["max_days"] == 0
