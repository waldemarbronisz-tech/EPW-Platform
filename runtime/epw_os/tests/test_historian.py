import pytest
from epw_os.core.historian import Historian, HistorianException
from epw_os.db.database import SessionLocal, engine
from epw_os.db.models import TagHistory
from epw_os.core.events import EventBus

@pytest.fixture
def empty_db(db):
    db = SessionLocal()

    try:
        db.query(TagHistory).delete()
    except Exception:
        db.rollback()

    db.commit()
    db.close()

def test_single_write(empty_db):
    bus = EventBus()
    hist = Historian(bus)
    hist.start()

    bus.emit("tag_changed", "Tag.Single", 42, "GOOD")
    hist.flush()

    db = SessionLocal()
    records = db.query(TagHistory).filter(TagHistory.tag_name == "Tag.Single").all()
    assert len(records) == 1
    assert records[0].data_type == "INT"
    assert records[0].val_int == 42
    db.close()

    hist.stop()

def test_batch_write(empty_db):
    bus = EventBus()
    hist = Historian(bus)
    hist.start()

    for i in range(100):
        bus.emit("tag_changed", f"Tag.Batch.{i}", i, "GOOD")

    hist.flush()

    db = SessionLocal()
    records = db.query(TagHistory).filter(TagHistory.tag_name.like("Tag.Batch.%")).all()
    assert len(records) == 100
    db.close()

    hist.stop()

def test_shutdown_drain(empty_db):
    bus = EventBus()
    hist = Historian(bus)
    hist.start()

    for i in range(50):
        bus.emit("tag_changed", f"Tag.Drain.{i}", i, "GOOD")

    hist.stop()

    db = SessionLocal()
    records = db.query(TagHistory).filter(TagHistory.tag_name.like("Tag.Drain.%")).all()
    assert len(records) == 50
    db.close()

def test_worker_exception(empty_db):
    bus = EventBus()
    hist = Historian(bus)
    hist.start()

    original_persist = hist._persist_records
    def bad_persist(records):
        try:
            raise ValueError("Simulated DB Crash")
        finally:
            for _ in records:
                hist.queue.task_done()

    hist._persist_records = bad_persist

    bus.emit("tag_changed", "Tag.Fail", 1, "GOOD")

    with pytest.raises(HistorianException, match="Historian worker encountered a fatal error"):
        hist.flush()

    try:
        hist.stop()
    except HistorianException:
        pass

def test_restart_persistence(db):
    db = SessionLocal()

    try:
        db.query(TagHistory).delete()
    except Exception:
        db.rollback()

    db.commit()
    db.close()

    bus1 = EventBus()
    hist1 = Historian(bus1)
    hist1.start()
    bus1.emit("tag_changed", "Tag.Restart", "Hello", "GOOD")
    hist1.flush()
    hist1.stop()

    # Create entirely new historian instance mimicking restart
    bus2 = EventBus()
    hist2 = Historian(bus2)
    hist2.start()

    db = SessionLocal()
    records = db.query(TagHistory).filter(TagHistory.tag_name == "Tag.Restart").all()
    assert len(records) == 1
    assert records[0].val_string == "Hello"
    db.close()

    hist2.stop()

def test_alarm_persistence(db):
    from epw_os.db.database import SessionLocal
    from epw_os.core.historian import Historian
    from epw_os.core.events import EventBus

    db = SessionLocal()
    from epw_os.db.models import AlarmHistory
    try:
        db.query(AlarmHistory).delete()
    except Exception:
        db.rollback()
    db.commit()
    db.close()

    bus = EventBus()
    hist = Historian(bus)
    hist.start()

    import time
    bus.emit("alarm_transition", "ALM1", "Tag1", "Test Alarm", 1, "ACTIVE_UNACK", time.time())
    hist.flush()
    hist.stop()

    db = SessionLocal()
    records = db.query(AlarmHistory).filter(AlarmHistory.alarm_id == "ALM1").all()
    assert len(records) == 1
    assert records[0].state == "ACTIVE_UNACK"
    db.close()


def test_sqlite_uses_wal_journal_mode(empty_db):
    """Audit finding: the GUI thread, Historian's own worker thread, and
    (when up) the REST API's uvicorn thread all write this same SQLite
    file concurrently (connect_args={"check_same_thread": False} in
    database.py exists exactly because of that) - the default rollback
    journal serializes those writers with a file lock, which is the
    textbook cause of sporadic "database is locked" errors under load.
    WAL mode avoids that by letting readers and a writer proceed without
    blocking each other; database.py sets it via a connect-event pragma,
    so any fresh connection from `engine` must report it."""
    with engine.connect() as conn:
        mode = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
    assert mode.lower() == "wal"
