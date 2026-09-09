"""Proves the `db` fixture's own two guarantees directly (Task:
refactor/test-db-fixture - "database migration is no longer done for
every test regardless of need").

1. A test that touches the database WITHOUT requesting `db` fails
   clearly, immediately, at the point of connecting - not by silently
   reading/writing whatever test_epw_os.db happens to contain.
2. Two tests that both request `db` never see each other's data,
   regardless of which one pytest happens to run first (verified here,
   and by running the whole epw_os/tests/ suite under pytest-randomly -
   see SESSION_REPORT.md for the multi-seed results).

Neither of these needs the real database to already contain anything -
they exist to prove the FIXTURE mechanism itself, not any particular
table's data.
"""
import pytest

from epw_os.db.database import SessionLocal
from epw_os.db.models import AuditLog


# --- DOWÓD 1: a test that touches the database without requesting `db`
# fails clearly - not silently, not on leftover data from a previous
# test. This test itself deliberately does NOT take `db` as a
# parameter - that omission IS the point being proven. -------------------

def test_touching_the_database_without_requesting_db_fails_clearly():
    session = SessionLocal()
    try:
        with pytest.raises(RuntimeError, match="db.*fixture"):
            session.query(AuditLog).count()
    finally:
        session.close()


def test_the_same_guard_also_fires_for_a_write_attempt():
    # Not just reads - the guard is on the connection pool's checkout
    # event, which fires before ANY operation (read or write) ever
    # reaches the database.
    session = SessionLocal()
    try:
        with pytest.raises(RuntimeError, match="db.*fixture"):
            session.add(AuditLog(event_type="SHOULD_NEVER_BE_WRITTEN", actor="test", success=True))
            session.commit()
    finally:
        session.rollback()
        session.close()


# --- DOWÓD 2: two tests, each requesting `db`, never see each other's
# data - independent of which one runs first. Both assert the table is
# empty at the very start of the test (proving no leftover row from
# whichever test - inside or outside this file - happened to run
# earlier this session), then each leaves exactly one row of its own. --

def test_isolation_probe_a_starts_clean_and_leaves_its_own_row(db):
    session = SessionLocal()
    try:
        assert session.query(AuditLog).filter(AuditLog.event_type == "ISOLATION_PROBE").count() == 0, \
            "must start clean - a leftover ISOLATION_PROBE row means another db-using test's data leaked in"
        session.add(AuditLog(event_type="ISOLATION_PROBE", actor="probe_a", success=True))
        session.commit()
        assert session.query(AuditLog).filter(AuditLog.event_type == "ISOLATION_PROBE").count() == 1
    finally:
        session.close()


def test_isolation_probe_b_starts_clean_and_leaves_its_own_row(db):
    session = SessionLocal()
    try:
        assert session.query(AuditLog).filter(AuditLog.event_type == "ISOLATION_PROBE").count() == 0, \
            "must start clean - a leftover ISOLATION_PROBE row means another db-using test's data leaked in " \
            "(in particular, probe_a's own row, if it ran first and this fixture's between-tests cleanup " \
            "didn't actually run)"
        session.add(AuditLog(event_type="ISOLATION_PROBE", actor="probe_b", success=True))
        session.commit()
        assert session.query(AuditLog).filter(AuditLog.event_type == "ISOLATION_PROBE").count() == 1
    finally:
        session.close()


def test_db_fixture_is_usable_again_right_after_the_guard_tests_above(db):
    # DOWÓD: the guard only blocks a test that never requested `db` -
    # it must not leave the engine/pool in some broken state for the
    # NEXT test that legitimately requests it, even one that runs
    # immediately after a test that deliberately triggered the guard
    # (as the two tests above do, every time this file runs in order).
    session = SessionLocal()
    try:
        session.query(AuditLog).count()  # must not raise
    finally:
        session.close()
