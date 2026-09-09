"""Independent audit trail for security/configuration-relevant actions:
logins, PIN changes, Protection Settings changes, language changes.

Deliberately separate from two other things that could be confused with
it:

* The operational Event Recorder (epw_os/gui/logger.py's ui_logger) is
  GUI-only, in-memory (never persisted to the DB), and about process/
  alarm events - "DO02 closed", "Protection ALARM active". It is not an
  audit trail and isn't a durable record.
* Historian (epw_os/core/historian.py) persists TagHistory/AlarmHistory -
  high-frequency operational process data, written asynchronously through
  a queue+worker-thread for throughput.

AuditLogger writes synchronously instead of through a queue: audit events
are low-frequency (logins, PIN/setting changes - not a 250ms tag stream)
and security-relevant, so the call site should know immediately whether
the record actually landed, and a crash between "queued" and "flushed"
should never be able to silently lose one.

RETENTION (Task: feature/retention-and-test-fix, B2) - deliberately NOT
the same "just delete the oldest rows" shape Historian/intrusion_history
use: "DZIENNIK AUDYTOWY to zapis, KTO CO ZROBIL... automatyczne kasowanie
takiego dziennika oznacza, ze po roku nie da sie ustalic, kto zmienil
nastawy zabezpieczen." A row may only ever be deleted AFTER it has been
written to a durable, human-readable archive file (CSV) - see
_enforce_retention() below for the exact ordering guarantee (archive
write must fully succeed, on disk, before any DELETE is even attempted).
Off by default, same as Historian's own retention (GRANICE).
"""
import csv
import os
from datetime import datetime, timedelta

from epw_os.db.database import SessionLocal
from epw_os.db.models import AuditLog
from epw_os.core.logging import log

# Both 0 = off (unbounded, today's behavior) - GRANICE: "Retencja
# domyslnie WYLACZONA".
DEFAULT_RETENTION_MAX_DAYS = 0
DEFAULT_RETENTION_MAX_ROWS = 0


def _default_archive_dir() -> str:
    """<repo root>/audit_archive/ - a sibling of epw_os.db/test_epw_os.db,
    not inside epw_os/ itself (this is generated runtime data, not
    source) and not inside epw_os/config/ (that directory is for small,
    single-file local settings like access.local.json - an
    ever-growing folder of dated CSV exports is a different shape of
    thing). Gitignored (see .gitignore) - never committed."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(repo_root, "audit_archive")


class AuditLogger:
    def __init__(self, event_bus=None):
        # Optional: if given, record() also emits "audit_log_recorded" so
        # a live-updating view (page_audit_log.py) can refresh without
        # polling the DB.
        self.event_bus = event_bus
        self._retention_max_days = DEFAULT_RETENTION_MAX_DAYS
        self._retention_max_rows = DEFAULT_RETENTION_MAX_ROWS
        self._archive_dir = None  # None -> _default_archive_dir() (lazy, so tests can override before it's ever needed)

    def record(self, event_type: str, actor: str, detail: str = "", success: bool = True):
        db = SessionLocal()
        try:
            entry = AuditLog(
                timestamp=datetime.utcnow(),
                event_type=event_type,
                actor=actor,
                detail=detail,
                success=success,
            )
            db.add(entry)
            db.commit()
        except Exception as e:
            db.rollback()
            log.error(f"AuditLogger failed to record {event_type} for {actor}: {e}")
            return
        finally:
            db.close()

        if self.event_bus:
            self.event_bus.emit("audit_log_recorded", event_type, actor, detail, success)

    def query(self, limit: int = 500):
        """Most recent entries first - used by the audit log view."""
        db = SessionLocal()
        try:
            return (
                db.query(AuditLog)
                .order_by(AuditLog.timestamp.desc())
                .limit(limit)
                .all()
            )
        finally:
            db.close()

    # --- Retention + archival (Task: feature/retention-and-test-fix, B2) -

    def get_retention_config(self) -> dict:
        return {
            "max_days": self._retention_max_days,
            "max_rows": self._retention_max_rows,
            "archive_dir": self._archive_dir or _default_archive_dir(),
        }

    def configure_retention(self, max_days: int = None, max_rows: int = None,
                             archive_dir: str = None, level: str = None):
        """Either numeric limit left None keeps it unchanged; 0 means "no
        limit" for that axis. `archive_dir` left None keeps the current
        directory (including the lazy built-in default, if never set).
        `level`, if given, is a defense-in-depth re-check (see
        historian.py's own configure_retention() for the identical
        reasoning) - refuses and returns False without changing anything
        if below Engineer. Purges immediately against the new limits."""
        if level is not None:
            from epw_os.core.access_manager import AccessLevel
            try:
                rank = AccessLevel._ORDER.index(level)
            except (ValueError, TypeError):
                rank = -1
            if rank < AccessLevel._ORDER.index(AccessLevel.ENGINEER):
                log.warning(f"Refused to configure audit log retention: level {level!r} is below Engineer.")
                return False
        changed = False
        if max_days is not None:
            self._retention_max_days = max(0, int(max_days))
            changed = True
        if max_rows is not None:
            self._retention_max_rows = max(0, int(max_rows))
            changed = True
        if archive_dir is not None and archive_dir != (self._archive_dir or ""):
            self._archive_dir = archive_dir
            changed = True
        if changed:
            cfg = self.get_retention_config()
            # Recorded like any other config change - written BEFORE
            # _enforce_retention() runs, so this row is never itself part
            # of whatever gets purged/archived a few lines down.
            self.record(
                "AUDIT_LOG_RETENTION_CONFIG", level or "SYSTEM",
                f"Audit log retention set to max_days={cfg['max_days'] or 'unlimited'}, "
                f"max_rows={cfg['max_rows'] or 'unlimited'}, archive_dir={cfg['archive_dir']!r}.",
            )
        self._enforce_retention()
        return True

    def _enforce_retention(self):
        """DOWÓD (B2): "przed usunieciem wpisy MUSZA zostac zapisane do
        pliku archiwalnego. Bez udanego zapisu archiwum nie usuwaj
        niczego." Structured as two separate, sequential stages on
        purpose - SELECT + write CSV (stage 1, may fail: disk full,
        permission denied, bad archive_dir) THEN, only if stage 1 fully
        succeeded, DELETE + commit (stage 2). A stage-1 failure returns
        immediately, before stage 2 is ever reached - not just
        "try/except around everything", which could still let a partial
        failure fall through to the delete."""
        if self._retention_max_days <= 0 and self._retention_max_rows <= 0:
            return

        db = SessionLocal()
        try:
            to_delete_ids = set()
            if self._retention_max_days > 0:
                cutoff = datetime.utcnow() - timedelta(days=self._retention_max_days)
                to_delete_ids.update(
                    r[0] for r in db.query(AuditLog.id).filter(AuditLog.timestamp < cutoff).all()
                )
            if self._retention_max_rows > 0:
                total = db.query(AuditLog).count()
                excess = total - self._retention_max_rows
                if excess > 0:
                    to_delete_ids.update(
                        r[0] for r in db.query(AuditLog.id)
                        .order_by(AuditLog.timestamp.asc()).limit(excess).all()
                    )
            if not to_delete_ids:
                return
            rows = (
                db.query(AuditLog)
                .filter(AuditLog.id.in_(to_delete_ids))
                .order_by(AuditLog.timestamp.asc())
                .all()
            )
            # Read every field off each row NOW, while the session (and
            # the rows) are still alive - avoids any risk of touching a
            # detached/expired ORM instance after db.close() below.
            row_data = [
                (r.id, r.timestamp, r.event_type, r.actor, r.detail, r.success) for r in rows
            ]
        except Exception as e:
            db.rollback()
            log.error(f"Audit log retention: could not determine rows to purge - nothing archived or deleted: {e}")
            return
        finally:
            db.close()

        # --- Stage 1: archive to CSV. Any failure here (bad directory,
        # disk full, permission denied) must leave the database
        # completely untouched - `return` here, not a shared try/except
        # with the delete below, is what guarantees that. ---------------
        try:
            archive_path = self._write_archive_csv(row_data)
        except Exception as e:
            log.error(f"Audit log retention: archive write failed ({e}) - nothing was purged.")
            return

        # --- Stage 2: only reached if the archive write above returned
        # normally (no exception) - delete exactly the rows just
        # archived, nothing else. ----------------------------------------
        db = SessionLocal()
        try:
            ids = [r[0] for r in row_data]
            db.query(AuditLog).filter(AuditLog.id.in_(ids)).delete(synchronize_session=False)
            db.commit()
        except Exception as e:
            db.rollback()
            log.error(f"Audit log retention: archive written to {archive_path} but the database delete failed "
                      f"({e}) - the archive is a superset of what's still in the table, not a mismatch.")
            return
        finally:
            db.close()

        oldest, newest = row_data[0][1], row_data[-1][1]
        count = len(row_data)
        log.info(f"Audit log retention: archived + purged {count} row(s), "
                 f"{oldest.isoformat()} .. {newest.isoformat()} -> {archive_path}.")
        # DOWÓD (B2): "po czyszczeniu w dzienniku zostaje wpis o
        # czyszczeniu" - a fresh record(), safe from being purged itself
        # (created strictly after the rows above were selected/deleted).
        self.record(
            "AUDIT_LOG_RETENTION_PURGE", "SYSTEM",
            f"Archived {count} row(s) dated {oldest.isoformat()} .. {newest.isoformat()} to "
            f"{archive_path}, then purged them from audit_log.",
        )

    def _write_archive_csv(self, row_data) -> str:
        """Writes `row_data` (id, timestamp, event_type, actor, detail,
        success tuples) as CSV to a new, uniquely-named file under the
        configured archive_dir (created if missing), and returns the
        path. Raises on any failure (caller decides what that means) -
        never silently returns a partial/empty file."""
        archive_dir = self._archive_dir or _default_archive_dir()
        os.makedirs(archive_dir, exist_ok=True)
        stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        filename = f"audit_log_archive_{stamp}.csv"
        path = os.path.join(archive_dir, filename)
        # A prior archive within the same wall-clock second (e.g. two
        # rapid manual purges, or a test) would otherwise silently
        # overwrite - append a numeric suffix instead of ever losing an
        # already-written archive.
        n = 1
        while os.path.exists(path):
            path = os.path.join(archive_dir, f"audit_log_archive_{stamp}_{n}.csv")
            n += 1
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "timestamp", "event_type", "actor", "detail", "success"])
            for row_id, timestamp, event_type, actor, detail, success in row_data:
                writer.writerow([row_id, timestamp.isoformat() if timestamp else "", event_type, actor,
                                  detail, success])
            f.flush()
            os.fsync(f.fileno())
        return path
