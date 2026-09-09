from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

import os
# Use absolute path to bypass test runner dir-hopping issues which causes RO locking
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "epw_os.db"))
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

# In testing we can use an in-memory or fully permissive file
if os.environ.get("EPW_TESTING") == "1":
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "test_epw_os.db"))
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}?timeout=10"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, pool_pre_ping=True
)


# Audit finding: check_same_thread=False is there because this one SQLite
# file is genuinely written from multiple threads at once - the GUI
# (main thread), Historian's own background worker, and (when the REST
# API is up) uvicorn's thread, all against the same epw_os.db. SQLite's
# default rollback-journal mode serializes writers with a file lock, so
# concurrent writers can surface as "database is locked" under load.
# WAL mode lets readers and a single writer proceed without blocking each
# other - set per-connection (SQLite has no server process to configure
# once), so every connection this engine ever opens gets it.
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_stats() -> dict:
    """Row count per table + the on-disk database file size in bytes
    (Task: feature/retention-and-test-fix, B3 - "rozmiar bazy i liczba
    wierszy w kazdej tabeli widoczne w interfejsie"). Models imported
    lazily (not at module level) to avoid the circular import
    epw_os.db.models -> epw_os.db.database -> epw_os.db.models would
    otherwise create."""
    from epw_os.db.models import TagHistory, AuditLog, AlarmHistory, IntrusionAlarmHistory

    db = SessionLocal()
    try:
        row_counts = {
            "tag_history": db.query(TagHistory).count(),
            "audit_log": db.query(AuditLog).count(),
            "alarm_history": db.query(AlarmHistory).count(),
            "intrusion_alarm_history": db.query(IntrusionAlarmHistory).count(),
        }
    finally:
        db.close()
    file_size_bytes = os.path.getsize(db_path) if os.path.exists(db_path) else 0
    return {"row_counts": row_counts, "file_size_bytes": file_size_bytes, "file_path": db_path}


def run_migrations():
    """Apply all pending Alembic migrations against the active database
    (SQLALCHEMY_DATABASE_URL above - production epw_os.db, or test_epw_os.db
    under EPW_TESTING=1) so the schema actually exists before anything
    tries to use it. Nothing previously called this outside of tests: on a
    fresh checkout with no committed *.db file (they're gitignored), the
    Historian worker would hit "no such table: tag_history" within moments
    of startup. Idempotent - safe to call even if already at head.
    """
    from alembic.config import Config
    from alembic import command as alembic_command

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    alembic_cfg = Config(os.path.join(repo_root, "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(repo_root, "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)
    alembic_command.upgrade(alembic_cfg, "head")
