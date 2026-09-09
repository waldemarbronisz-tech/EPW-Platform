"""Shared, single-listener database-access guard for the whole test
suite (Task: refactor/test-db-fixture, extended by
feature/retention-and-test-fix's own Part A finding).

Deliberately NOT inside conftest.py. A conftest.py has no guaranteed,
ordinarily-importable dotted module name - pytest loads it through its
own rootdir-relative mechanism, not a plain `import`, and
epw_os/tests/ has no __init__.py (a namespace package). A second,
ordinary `import epw_os.tests.conftest` (e.g. from gui_smoke/conftest.py,
a SIBLING package whose own tests sometimes also touch the real,
shared, process-wide database - see gui_smoke/conftest.py's own
`real_db` fixture) creates a SEPARATE module object with its OWN
separate globals - including a SECOND, independent copy of the guard
listener below, bound to a second, independent "is a db fixture
active" flag that never gets set from the first copy's side.

This was found exactly this way, as a real combined-run (epw_os/tests/
+ gui_smoke/) failure: every properly `db`-fixtured test in
epw_os/tests/ started failing once gui_smoke/'s own `real_db` fixture
had run once anywhere earlier in the session - that first run's plain
`import epw_os.tests.conftest` re-executed conftest.py's top-level code
from scratch (a fresh module, a fresh SQLAlchemy `event.listens_for`
registration on the same shared `engine.pool`), installing a rogue
second listener that stayed active, checking its own always-False flag,
for the rest of the session.

This module has one real, ordinary dotted name, reachable identically
by a plain `import epw_os.tests._db_guard` from anywhere - unlike
conftest.py, it is never pytest-loaded as a plugin, so there is exactly
ONE way to reach it, ONE cached module in sys.modules, ONE listener, ONE
flag - regardless of which directory's fixtures import it first.
"""
import os
import time

from sqlalchemy import event

from epw_os.db.database import Base, engine

_active = False
_migrated_this_session = False
_listener_installed = False


def _install_listener():
    global _listener_installed
    if _listener_installed:
        return

    @event.listens_for(engine.pool, "checkout")
    def _guard_unrequested_db_access(dbapi_connection, connection_record, connection_proxy):
        if not _active:
            raise RuntimeError(
                "A test opened a real database connection without requesting the `db` "
                "fixture (epw_os/tests/conftest.py) or `real_db` (gui_smoke/conftest.py). "
                "Add one as a parameter to this test - e.g. `def test_foo(db): ...` - if "
                "it genuinely needs the database; if it doesn't, something it calls does, "
                "and that's worth tracking down rather than silently reading/writing "
                "whatever test_epw_os.db happens to contain at this point in the run."
            )

    _listener_installed = True


_install_listener()


def activate():
    global _active
    _active = True


def deactivate():
    global _active
    _active = False


def clean_all_tables():
    """Deletes every ROW from every table this project's models define -
    not the schema, and not test_epw_os.db's own `alembic_version` table
    (Alembic's own tracking table, outside Base.metadata)."""
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


def ensure_migrated_and_clean():
    """Idempotent within a session: the FIRST call this session deletes
    any stale test_epw_os.db and runs the real Alembic migration once;
    every call after that only clears table data (for isolation between
    tests), never re-migrates. Callers must have already called
    activate() (or be inside its context) - this itself opens real DB
    connections."""
    global _migrated_this_session
    if not _migrated_this_session:
        from alembic import command
        from alembic.config import Config

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        db_path = os.path.join(repo_root, "test_epw_os.db")
        for _ in range(5):
            try:
                if os.path.exists(db_path):
                    os.remove(db_path)
                break
            except Exception:
                time.sleep(0.1)

        alembic_cfg = Config(os.path.join(repo_root, "alembic.ini"))
        alembic_cfg.set_main_option("script_location", os.path.join(repo_root, "alembic"))
        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}?timeout=10")
        command.upgrade(alembic_cfg, "head")
        engine.dispose()
        _migrated_this_session = True
    else:
        clean_all_tables()
