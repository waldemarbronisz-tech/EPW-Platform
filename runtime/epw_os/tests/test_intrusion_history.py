"""Tests for epw_os/core/intrusion_history.py - the dedicated intrusion
alarm event history (Task: "historia zdarzen alarmowych"), backed by the
real (test) SQLite database via the `db` fixture in conftest.py
(opt-in, not autouse - Task: refactor/test-db-fixture), requested by
this file's own autouse empty_history_table fixture below - same
pattern test_historian.py already uses for its own DB-backed tests."""
import pytest

from epw_os.core.intrusion_history import IntrusionAlarmHistoryLogger, DEFAULT_MAX_EVENTS, DEFAULT_MAX_DAYS
from epw_os.db.database import SessionLocal
from epw_os.db.models import IntrusionAlarmHistory


@pytest.fixture(autouse=True)
def empty_history_table(db):
    """Requests `db` so every test in this file gets the database
    (autouse - this whole file is DB-backed, see its own module
    docstring). The explicit delete below is now redundant with `db`'s
    own between-tests table cleanup (Task: refactor/test-db-fixture) -
    kept anyway as a harmless, explicit belt-and-suspenders for this
    table specifically, same pattern test_historian.py's own empty_db
    fixture already uses for TagHistory."""
    db = SessionLocal()
    try:
        db.query(IntrusionAlarmHistory).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


class FakeProjectManager:
    """Minimal stand-in for the retention config get/set methods only -
    same pattern test_intrusion_manager.py's own FakeProjectManager uses."""
    def __init__(self):
        self._retention = {}

    def get_intrusion_history_retention(self):
        return self._retention

    def set_intrusion_history_retention(self, data):
        self._retention = dict(data)

    def save_project(self):
        pass


def test_record_and_query_round_trip():
    logger = IntrusionAlarmHistoryLogger()
    logger.record("INTRUSION_ZONE_ARMED", "Operator", "Zone 'Perimeter' armed", zone_id="Z1", zone_name="Perimeter")
    logger.record("INTRUSION_ALARM", "SYSTEM", "Zone 'Perimeter': Instant line violated (line 'Front Door')",
                   zone_id="Z1", zone_name="Perimeter", line_id="L1", line_name="Front Door")

    rows = logger.query(limit=10)
    assert len(rows) == 2
    assert rows[0].event_type == "INTRUSION_ALARM"  # most recent first
    assert rows[1].event_type == "INTRUSION_ZONE_ARMED"
    assert rows[0].zone_id == "Z1"
    assert rows[0].line_id == "L1"


def test_query_filters_by_zone_and_event_type():
    logger = IntrusionAlarmHistoryLogger()
    logger.record("INTRUSION_ZONE_ARMED", "Operator", "Z1 armed", zone_id="Z1")
    logger.record("INTRUSION_ZONE_ARMED", "Operator", "Z2 armed", zone_id="Z2")
    logger.record("INTRUSION_ZONE_DISARMED", "Operator", "Z1 disarmed", zone_id="Z1")

    by_zone = logger.query(zone_id="Z1")
    assert {r.event_type for r in by_zone} == {"INTRUSION_ZONE_ARMED", "INTRUSION_ZONE_DISARMED"}

    by_type = logger.query(event_type="INTRUSION_ZONE_ARMED")
    assert {r.zone_id for r in by_type} == {"Z1", "Z2"}


def test_default_retention_matches_event_recorder_pattern():
    logger = IntrusionAlarmHistoryLogger()
    cfg = logger.get_retention_config()
    assert cfg == {"max_events": DEFAULT_MAX_EVENTS, "max_days": DEFAULT_MAX_DAYS}


def test_retention_by_event_count_evicts_oldest_first():
    """Task 5: "RETENCJA: konfigurowalna liczba zdarzen albo dni...
    Zastosuj ten sam wzorzec, co limit w Rejestrze Zdarzen" (cap + evict
    oldest, same principle page_event_recorder.py's own MAX_EVENT_ROWS
    already applies)."""
    logger = IntrusionAlarmHistoryLogger()
    logger.configure_retention(max_events=3, max_days=0)
    for i in range(5):
        logger.record("INTRUSION_LINE_VIOLATED", "SYSTEM", f"event {i}", zone_id="Z1")

    rows = logger.query(limit=100)
    assert len(rows) == 3
    # oldest (event 0, event 1) evicted - only the 3 most recent remain
    assert [r.detail for r in rows] == ["event 4", "event 3", "event 2"]


def test_retention_by_days_prunes_older_rows():
    from datetime import datetime, timedelta
    from epw_os.db.database import SessionLocal
    from epw_os.db.models import IntrusionAlarmHistory

    logger = IntrusionAlarmHistoryLogger()
    logger.configure_retention(max_events=0, max_days=7)

    # Insert one row directly with an old timestamp (bypassing record()'s
    # own datetime.utcnow(), which can't backdate) - then trigger
    # retention enforcement the same way record() itself would.
    db = SessionLocal()
    old_row = IntrusionAlarmHistory(
        timestamp=datetime.utcnow() - timedelta(days=30), event_type="INTRUSION_ZONE_ARMED",
        actor="Operator", detail="old event", zone_id="Z1",
    )
    db.add(old_row)
    db.commit()
    db.close()

    logger.record("INTRUSION_ZONE_DISARMED", "Operator", "recent event", zone_id="Z1")  # triggers _enforce_retention()

    rows = logger.query(limit=100)
    details = [r.detail for r in rows]
    assert "old event" not in details
    assert "recent event" in details


def test_retention_zero_on_both_axes_means_unbounded():
    logger = IntrusionAlarmHistoryLogger()
    logger.configure_retention(max_events=0, max_days=0)
    for i in range(10):
        logger.record("INTRUSION_LINE_VIOLATED", "SYSTEM", f"event {i}", zone_id="Z1")
    assert len(logger.query(limit=100)) == 10


def test_retention_config_persists_via_project_manager():
    pm = FakeProjectManager()
    logger1 = IntrusionAlarmHistoryLogger(project_manager=pm)
    logger1.configure_retention(max_events=42, max_days=14)

    logger2 = IntrusionAlarmHistoryLogger(project_manager=pm)  # "restart": same project data, fresh instance
    assert logger2.get_retention_config() == {"max_events": 42, "max_days": 14}


def test_distinct_event_types_reflects_whats_actually_recorded():
    logger = IntrusionAlarmHistoryLogger()
    logger.record("INTRUSION_ZONE_ARMED", "Operator", "a", zone_id="Z1")
    logger.record("INTRUSION_ALARM", "SYSTEM", "b", zone_id="Z1")
    logger.record("INTRUSION_ZONE_ARMED", "Operator", "c", zone_id="Z1")

    assert set(logger.distinct_event_types()) == {"INTRUSION_ZONE_ARMED", "INTRUSION_ALARM"}
