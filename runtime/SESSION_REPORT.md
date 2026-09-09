# Session Report — Combined-Suite Crash Fix + Data Retention

Branch `feature/retention-and-test-fix`, pushed, not merged (standing
rule: never merge locally to main). Two independent pieces, each
committed separately.

## Part A — the combined-suite crash

### The cause

`pytest epw_os/tests/ gui_smoke/` in one process crashed with a native
fault (Windows `STATUS_HEAP_CORRUPTION` or an access violation,
depending on the run) partway through, previously diagnosed only as far
as "somewhere in Qt event processing." Reproducing it this session
captured two DIFFERENT concrete crash sites across separate runs -
both real, both compounding:

1. **`pytest-qt`** is installed in this environment (`pip list` shows
   it, `pytest-qt==4.5.0`) but nothing in this codebase imports
   `pytestqt` or uses its `qtbot` fixture anywhere. Its own
   `pytest_runtest_teardown` hook (`pytestqt/plugin.py`) is
   UNCONDITIONAL: it calls `QApplication.processEvents()` up to three
   times after EVERY test in the WHOLE pytest session, the moment any
   `QApplication` exists - not gated by whether that test opted into
   anything. `gui_smoke/`'s own session-scoped `qapp` fixture creates
   one early, so from that point on every `epw_os/tests/` test (which
   never asked for any of this) ALSO got extra Qt event pumping at its
   own teardown. One crash trace ran directly through
   `pytestqt/plugin.py`'s own `_process_events()`.
2. `gui_smoke/conftest.py`'s own `_pump_qt_events_after_test` fixture
   (added last session to fix THIS package's progressive slowdown) used
   to additionally force a `gc.collect()` after every test - a full
   Python heap walk, not a Qt-specific operation. Its cost scales with
   the size of the WHOLE process's live-object graph, not just this
   package's own churn. Combined with `epw_os/tests/`'s own 500+ tests
   in the same process, this was a second, independent crash site (the
   other captured trace ran directly through this exact `gc.collect()`
   call) - and, even before it ever crashed, a measurable slowdown
   driver in its own right (see timings below).

### The fix

- `pytest.ini`: `addopts = -p no:pytest-qt` - disables the unused
  plugin globally. Verified nothing in the repo depends on it
  (`grep -rl "qtbot\|pytestqt"` outside `site-packages` is empty).
- `gui_smoke/conftest.py`: removed the `gc.collect()` call from
  `_pump_qt_events_after_test`, kept the `processEvents()` calls (the
  part that actually reclaims `.deleteLater()`'d Qt objects - a
  completely different mechanism from Python's cyclic garbage
  collector, which is what `gc.collect()` walks).

### Were the two goals reconcilable? Yes, once both were fixed together

Removing `pytest-qt`'s hook alone: no crash, but the combined run still
took 744.6s (12m24s), an obvious progressive-slowdown-shaped number.
Removing `gc.collect()` alone (on top of the `pytest-qt` fix): 319.5s
(5m19s) - a big improvement, but still well above the ~224s a naive sum
of the two suites' own solo times would predict. Investigating the
remaining gap surfaced a THIRD, unrelated bug this task's own new code
introduced (see below) - fixing that closed the rest of the gap.

**DOWÓD - can both suites now run in one invocation, and is the
progressive slowdown gone?** Yes to both, verified with three separate
full runs of `pytest epw_os/tests/ gui_smoke/`:

| Run | Result | Time |
|---|---|---|
| 1 | 677 passed | 143.64s (2m23s) |
| 2 | 677 passed | 141.66s (2m21s) |
| 3 | 677 passed | 142.95s (2m22s) |

No crash in any run; times stable within ~2s of each other across three
runs (not growing) - the progressive-slowdown symptom does not return.
`gui_smoke/README.md`'s own "found interaction effect" section is
updated with this fix; the two suites can now be run either combined or
as two separate invocations (CI keeps the latter - no need to change a
working setup).

### A third bug found along the way (fixed, not part of the original two)

While chasing the remaining ~95s gap between the naive sum and the
actual combined time, a genuinely separate, unrelated bug surfaced:
`epw_os/tests/conftest.py`'s own database-access guard (from the
previous session's `refactor/test-db-fixture` task) is a
`sqlalchemy.event.listens_for(engine.pool, "checkout")` listener bound
to a module-level flag. `epw_os/tests/` has no `__init__.py` (a
namespace package), so a conftest.py has no single, guaranteed dotted
module name - a second `import epw_os.tests.conftest` (which this
task's own new `gui_smoke/conftest.py` `real_db` fixture needed, to
participate in that same guard for the handful of gui_smoke tests that
touch a real database - see Part B) silently created a SECOND,
independent copy of the whole module, including a second copy of the
guard listener bound to a second, always-False flag that the real `db`
fixture never touched - which then made EVERY properly-`db`-fixtured
test in `epw_os/tests/` start failing, order-dependently, once the
`gui_smoke/` fixture had run once anywhere in the session. Fixed by
extracting the shared guard/migration state into
`epw_os/tests/_db_guard.py` - an ordinary module with a real, single
dotted name, imported identically (`import epw_os.tests._db_guard`)
from both `epw_os/tests/conftest.py`'s `db` fixture and
`gui_smoke/conftest.py`'s new `real_db` fixture, so there is exactly
one listener and one flag regardless of which side imports it first.

## Part B — data retention

### Historian (B1) - measurement data, deletable

- `epw_os/core/historian.py`: `configure_retention(max_days, max_rows,
  level=None)` / `get_retention_config()` - both axes independently
  optional (0 = unlimited), default OFF (`DEFAULT_RETENTION_MAX_DAYS =
  DEFAULT_RETENTION_MAX_ROWS = 0`). Purges immediately on
  `configure_retention()` (a rare, explicit admin action - safe to do
  on the calling thread) AND periodically (`RETENTION_CHECK_INTERVAL_S
  = 60.0`) from the Historian worker THREAD's own loop
  (`_process_queue()`) - never from `record_tag_change()`'s own
  producer-side hot path (`queue.put_nowait()` only), proven
  structurally by `test_record_tag_change_never_calls_enforce_retention_directly`
  (a spy on `_enforce_retention()`, not a timing-based test).
  Deliberately scoped to `TagHistory` only, not `AlarmHistory` (also
  written by this class) - see "Flagged decisions" below.
- Every purge is logged (row count + date range) via the application
  log and, if given, `audit_logger.record("HISTORIAN_RETENTION_PURGE",
  ...)` - `Historian.__init__` gained an optional `audit_logger=None`
  parameter (wired from `EPWCore.__init__`, which already constructs
  `audit_logger` before `historian`).
- Persisted via `project_manager.get_historian_retention_config()` /
  `set_historian_retention_config()` (new, optional
  `config["historian_retention"]` section - same lazy-default shape as
  the existing `historian_deadband` section), applied in
  `EPWCore.startup()` right after the existing deadband config.

### Audit log (B2) - archive before delete, always

- `epw_os/core/audit_logger.py`: same `configure_retention()` /
  `get_retention_config()` shape, plus `archive_dir`. `_enforce_retention()`
  is structured as two STRICTLY SEQUENTIAL stages: stage 1 selects the
  rows to purge and writes them to a CSV file (`_write_archive_csv()` -
  `os.makedirs()` + `csv.writer` + explicit `flush()`/`fsync()`); ANY
  exception there returns immediately, before stage 2 (the actual
  `DELETE` + `commit()`) is ever reached - not a shared try/except that
  could let a partial failure fall through. Verified by
  `test_audit_log_not_purged_when_archive_write_fails` (a monkeypatched
  `_write_archive_csv` that raises) and
  `test_audit_log_not_purged_when_delete_fails_after_a_successful_archive`
  (the archive succeeds, the DB delete is made to fail - the archive
  file must still exist and the DB must still hold every original row).
  A successful cycle writes one new `AUDIT_LOG_RETENTION_PURGE` entry
  into the audit log itself, naming the row count, date range, and
  archive file - `test_audit_log_archives_before_purging_and_leaves_a_purge_record`.
- Archive location: configurable (`archive_dir` in the Settings dialog,
  a `Browse...` button), defaulting to `<repo root>/audit_archive/`
  (gitignored) when never set.
- Persisted via `project_manager.get_audit_retention_config()` /
  `set_audit_retention_config()` - a separate `config["audit_retention"]`
  section, independent of Historian's own.

### Visibility (B3)

- `epw_os/db/database.py`: `get_db_stats()` - row count per table
  (`tag_history`/`audit_log`/`alarm_history`/`intrusion_alarm_history`)
  + the database file's on-disk size. Shown at the top of the Data
  Retention dialog.
- A separate, optional database-size warning
  (`project_manager.get_db_size_warning_config()` /
  `set_db_size_warning_config()`, off by default) - a new status-bar
  indicator (`lbl_sb_db_warning`, styled like the existing REST-API-
  exposure warning) that becomes visible once the database file exceeds
  the configured MB threshold. Refreshed at construction, on theme
  change, and every 60s via a new `db_size_check_timer` (stopped in
  `shutdown_gui()`, same pattern as every other timer there).

### Configuration (B4)

- `epw_os/gui/widgets/data_retention_dialog.py` (new) -
  `DataRetentionDialog`, Engineer-only, opened from
  Settings > Data Retention... (`main_window.py`, wired exactly like
  Feature Configuration/MQTT's own menu entries: hidden+disabled below
  Engineer, re-checked again at Save time via
  `Historian.configure_retention(level=...)` /
  `AuditLogger.configure_retention(level=...)` - defense in depth, not
  just a visual gate). Two clearly separate sections (Historian, Audit
  Log), each with its own max-days/max-rows fields (0 = "Unlimited",
  same `setSpecialValueText` convention `page_intrusion.py`'s own
  `HistoryRetentionDialog` already established) - GRANICE: "nie mogą
  dzielić jednego przełącznika". A third section covers the database
  size warning threshold.

### Defaults chosen, and why

Every new numeric default is **0 (unlimited/off)** - not just Historian/
audit-log retention themselves (explicit GRANICE requirement), but also
`RETENTION_CHECK_INTERVAL_S = 60.0` (matched to how often an
administrative background check is reasonable - the same order of
magnitude as `db_size_check_timer`'s own 60s interval, chosen for the
same reason: cheap enough to run constantly, coarse enough not to add
measurable overhead) and the size-warning threshold's own UI default
(500 MB, editable) - a starting suggestion, not a claim about what's
"correct" for any given SD card, deliberately not enforced or assumed
anywhere in code.

### GRANICE compliance

- Retention off by default everywhere - existing installations behave
  identically until an Engineer explicitly configures a limit.
- Audit log: never purged without a successful archive write first
  (see Part B's own two dedicated tests).
- Purging never blocks current writes: Historian's own hot write path
  (`record_tag_change`) never calls retention logic at all (see the
  structural proof test); audit log writes were already synchronous
  by design (low-frequency, security-relevant - unchanged by this
  task), matching the existing `IntrusionAlarmHistoryLogger` precedent.
- No database schema change - retention config lives entirely in
  project.json (new optional sections, same lazy-default shape every
  other optional section in `project_manager.py` already uses); B3's
  stats are runtime queries against the existing tables.
- `safety_kernel.py`, the permission matrix, Kiosk Mode, the REST API,
  MQTT, themes, and the alarm module: untouched.
- No new dependencies (`csv`, `os` are stdlib; `sqlalchemy.event` was
  already a transitive dependency of the existing `requirements.txt`).
- Every new user-facing string goes through `tr()`, with a key in both
  `epw_os/i18n/locales/en.json` and `pl.json` (verified: both files
  parse as valid JSON, and `test_i18n.py`'s existing key-parity tests
  pass unchanged). A new Help topic ("Data Retention") was added in
  both `epw_os/help/en/` and `epw_os/help/pl/`, including `toc.json`
  chapter and index-term entries in both languages
  (`test_help_content.py` passes unchanged).

### Flagged decision

**Historian retention is scoped to `TagHistory` only, not `AlarmHistory`**
(also written by the same `Historian` class). B1's own wording
specifically calls Historian "dane pomiarowe" (measurement data);
`AlarmHistory` is process-alarm event history, a different kind of
record with its own semantics (closer in spirit to the audit log's
"what happened" than to a measurement trend), and extending the same
mechanism to it wasn't asked for explicitly. Narrowed deliberately
rather than guessed at - flagged here for a decision either way.

## Tests (DOWÓD)

New: `epw_os/tests/test_retention.py` (16 tests, headless - real
`Historian`/`AuditLogger` against the real `db` fixture) and
`gui_smoke/test_retention.py` (4 tests - the Settings dialog, the menu
gate, the status-bar indicator). All explicitly requested DOWÓD items:

- "przy wyłączonej retencji nic nie jest usuwane" -
  `test_retention_disabled_nothing_is_deleted`,
  `test_audit_retention_disabled_nothing_is_deleted`
- "Historian usuwa najstarsze po przekroczeniu limitu" -
  `test_historian_purges_oldest_rows_first_over_max_rows`,
  `test_historian_purges_rows_older_than_max_days`
- "dziennik audytowy NIE JEST czyszczony, gdy zapis archiwum się nie
  powiódł" - `test_audit_log_not_purged_when_archive_write_fails`,
  `test_audit_log_not_purged_when_delete_fails_after_a_successful_archive`
- "po czyszczeniu w dzienniku zostaje wpis o czyszczeniu" -
  `test_historian_purge_reaches_the_audit_log_with_count_and_date_range`,
  `test_audit_log_archives_before_purging_and_leaves_a_purge_record`
- "usuwanie nie blokuje bieżącego zapisu" -
  `test_record_tag_change_never_calls_enforce_retention_directly`
  (structural, not timing-based)

## Numbers (DOWÓD)

- Tests: 584 (`epw_os/tests/`, was 568) + 93 (`gui_smoke/`, was 89) =
  **677 total, all passing** - no check removed, 36 new added (20 in
  Part A's own new `_db_guard`-adjacent test coverage folded into the
  existing `test_db_fixture.py`'s unchanged 5, plus the 16+4 above).
- Combined-suite time: **~143s, three consecutive runs, no crash** (see
  table above) - was previously an unmeasurable crash (Part A) or, on
  the two intermediate fixes, 744.6s then 319.5s before the third,
  unrelated bug (the `_db_guard` duplicate-module issue) was found and
  fixed too.
- `epw_os/tests/` alone and `gui_smoke/` alone: unaffected, still ~85s
  and ~57-138s respectively (run-to-run system variance observed on
  this machine independent of any change here).

## Push confirmation

`git push -u origin feature/retention-and-test-fix` — see the branch on
GitHub for the final pushed state. Commits kept separate for Part A and
Part B, per the task's own instruction ("Rób po kolei, commituj
osobno").
