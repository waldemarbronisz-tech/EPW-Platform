"""Shared fixtures for epw_os/tests/.

Task (refactor/test-db-fixture): the database used to be migrated
(a full Alembic `upgrade head` pass, deleting and recreating
test_epw_os.db first) before EVERY test collected in this directory,
via an autouse fixture - regardless of whether that test touched the
database at all. See SESSION_REPORT.md for the measurement that led to
this change: removing the fixture's cost entirely saved ~60s out of a
~146s full run, but it was NOT simply "the fixture is too slow" - most
of that saving is startup-time overhead (a fresh SQLite file, WAL mode
setup, engine.dispose()) paid 563 times, not the ~39ms of raw Alembic
work each call actually needs, and it is NOT the single dominant cost
of the full suite's own historical "~20 minutes" (that remains
unexplained beyond this file - see SESSION_REPORT.md).

Only 5 files (out of 30) touch the database at all - migrations are now
scoped to exactly those, via one explicit, opt-in `db` fixture (see
below), rather than the autouse fixture guessing nothing and doing it
for everyone.

Migration itself is no longer repeated per-test: it happens ONCE for
the whole pytest session (the first time any test requests `db`), and
every further `db` request just deletes each table's ROWS (not the
schema) so tests stay isolated from each other's data without paying
Alembic's cost again. This assumes a single pytest process (already
true in this project - no pytest-xdist/parallel workers; GRANICE:
no new dependencies).

**Enforcement, not just convention**: a `pool.checkout` listener on the
real SQLAlchemy engine (see epw_os/tests/_db_guard.py) fires on every
real connection attempt, from ANY test, at ANY point in the session -
including one that runs long after some earlier, unrelated test already
migrated the schema. A test that touches the database without adding
`db` as one of its parameters gets a clear, immediate RuntimeError
naming exactly what happened, never a silent read/write against
whatever the database happens to contain at that moment. See
test_db_fixture.py for a test that exercises this directly (a
deliberate, unguarded DB touch, wrapped in `pytest.raises`) plus a test
that two `db`-using tests never see each other's data, regardless of
run order.

The guard/migration/cleanup machinery itself lives in the separate,
ordinarily-importable epw_os/tests/_db_guard.py, not here - see that
module's own docstring for why (gui_smoke/'s own `real_db` fixture,
feature/retention-and-test-fix, needs the exact same mechanism from a
sibling package, and a second `import` of THIS file - a conftest.py,
with no guaranteed dotted module name of its own - would silently
create a second, independent copy of it instead of sharing one)."""
import os

import pytest

# Set testing environment BEFORE importing db modules
os.environ["EPW_TESTING"] = "1"

from epw_os.tests import _db_guard


@pytest.fixture
def db():
    """Opt-in: request this fixture (`def test_foo(db): ...`) for any
    test that touches the database, directly (SessionLocal/engine) or
    indirectly (e.g. constructing a real EPWCore and calling
    `.startup()`, which runs its own real migration as part of normal
    production startup - see epw_os/core/epw_core.py - redundant but
    harmless the first time this fixture also migrates; a no-op after).

    First call this session: deletes any stale test_epw_os.db and runs
    the real Alembic migration once (same technique as the old
    per-test fixture, just no longer repeated). Every call after that:
    only clears table data, for isolation between tests - not a
    migration re-run (see this module's own docstring for why once is
    enough)."""
    _db_guard.activate()
    try:
        _db_guard.ensure_migrated_and_clean()
        yield
    finally:
        _db_guard.deactivate()
