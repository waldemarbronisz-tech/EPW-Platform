import queue
import threading
import time
from typing import Dict, Any, List
from epw_os.db.database import get_db, SessionLocal
from epw_os.db.models import TagHistory, AlarmHistory
from epw_os.core.logging import log
from datetime import datetime, timedelta

class HistorianException(Exception):
    pass


# Deadband (Task: karta SD o ograniczonej trwalosci zapisu - nie kazda
# zmiana wartosci REAL/INT ma trafiac do bazy, tylko zmiana wieksza niz
# prog, plus wymuszony okresowy zapis zeby stabilna wartosc nie zostawiala
# dziury w historii). Sensible generic defaults - tunable per-tag and
# overall via ProjectManager's new, optional "historian_deadband" section
# (see project_manager.py's get_deadband_config()/set_deadband_config(),
# and EPWCore.startup(), which applies it to this module's Historian
# instance before start()). Deliberately module-level constants, not
# buried magic numbers, so both this file and the report can point at one
# definition.
DEFAULT_DEADBAND_THRESHOLD = 0.5      # absolute value change required (REAL/INT tags only)
DEFAULT_FORCED_WRITE_SECONDS = 300.0  # write anyway after this long, even if unchanged

# Retention (Task: feature/retention-and-test-fix, "Historian to dane
# pomiarowe - starsze niz jakis czas przestaja byc potrzebne, mozna je
# usuwac"). Scoped to TagHistory only (the actual measurement table) -
# AlarmHistory (also written by this class) is process-alarm history,
# not "dane pomiarowe" in the task's own wording, and is deliberately
# left untouched by this feature - see SESSION_REPORT.md's flagged-
# decision section. GRANICE: "Retencja domyslnie WYLACZONA" - both 0
# (off) by default, existing installations behave identically to today
# until an Engineer explicitly configures a limit.
DEFAULT_RETENTION_MAX_DAYS = 0   # 0 = unbounded (off)
DEFAULT_RETENTION_MAX_ROWS = 0   # 0 = unbounded (off)
# How often the background worker thread re-checks retention on its own,
# between explicit configure_retention() calls (which also purge
# immediately - see below). Not on the hot write path either way -
# record_tag_change() only ever touches self.queue.put_nowait().
RETENTION_CHECK_INTERVAL_S = 60.0


def tag_history_value(row: TagHistory):
    """The one populated val_* column for a TagHistory row, by its own
    data_type - same rule Historian._persist_records() used to decide
    which column to write into. Shared here so the export dialog and any
    future consumer read history back the same way it was written."""
    if row.data_type == "BOOL":
        return row.val_bool
    if row.data_type == "INT":
        return row.val_int
    if row.data_type == "REAL":
        return row.val_real
    return row.val_string

class Historian:
    def __init__(self, event_bus, audit_logger=None):
        self.event_bus = event_bus
        # Optional (Task: retention) - if given, both a retention CONFIG
        # CHANGE and every actual retention PURGE are recorded to it (see
        # configure_retention()/_enforce_retention() below). None in
        # isolated tests/older call sites that never cared about
        # retention - configure_retention()/the periodic sweep still work
        # fully, they just have nowhere to record the fact.
        self.audit_logger = audit_logger
        self.queue = queue.Queue()
        self.is_running = False
        self._thread = None
        self._stop_event = threading.Event()
        self._worker_exception = None

        self.event_bus.subscribe("tag_changed", self.record_tag_change)
        self.event_bus.subscribe("alarm_transition", self.record_alarm_transition)

        # Deadband state - see configure_deadband()/_should_write() below.
        # record_tag_change() runs on whichever thread emitted tag_changed
        # (GUI thread, SimulatorDriver's own thread, ...), so this needs
        # its own lock independent of TagManager's.
        self._deadband_lock = threading.RLock()
        self._deadband_default = DEFAULT_DEADBAND_THRESHOLD
        self._deadband_per_tag: Dict[str, float] = {}
        self._forced_write_seconds = DEFAULT_FORCED_WRITE_SECONDS
        self._last_written: Dict[str, tuple] = {}  # tag_name -> (value, quality, monotonic_time)

        # Retention state - see configure_retention()/_enforce_retention()
        # below. Its own lock (independent of the deadband one above):
        # configure_retention() can be called from the GUI thread while
        # the worker thread's periodic sweep reads these same fields.
        self._retention_lock = threading.RLock()
        self._retention_max_days = DEFAULT_RETENTION_MAX_DAYS
        self._retention_max_rows = DEFAULT_RETENTION_MAX_ROWS
        self._last_retention_check = 0.0

    def configure_deadband(self, config: dict):
        """Applies ProjectManager's persisted historian_deadband section
        (or any dict with the same shape) - called once from
        EPWCore.startup(), before start(). Missing/malformed keys keep
        this Historian's current values (the __init__ defaults, if never
        called at all), same defensive stance as ProjectManager's own
        get_deadband_config()."""
        with self._deadband_lock:
            try:
                self._deadband_default = float(config.get("default_threshold", self._deadband_default))
            except (TypeError, ValueError):
                # A malformed persisted value (bad hand-edit, legacy
                # format) silently keeping the previous default is the
                # right fail-safe behavior (kept unchanged), but it's
                # worth logging - an operator who thinks they configured
                # a threshold that quietly didn't apply is exactly the
                # "polykane wyjatki" pattern System.Mode had.
                log.warning(f"Ignoring malformed historian_deadband.default_threshold "
                            f"{config.get('default_threshold')!r} - keeping {self._deadband_default}.")
            try:
                self._forced_write_seconds = float(config.get("forced_write_seconds", self._forced_write_seconds))
            except (TypeError, ValueError):
                log.warning(f"Ignoring malformed historian_deadband.forced_write_seconds "
                            f"{config.get('forced_write_seconds')!r} - keeping {self._forced_write_seconds}.")
            per_tag = config.get("per_tag") or {}
            if isinstance(per_tag, dict):
                clean = {}
                for k, v in per_tag.items():
                    try:
                        clean[k] = float(v)
                    except (TypeError, ValueError):
                        log.warning(f"Ignoring malformed historian_deadband.per_tag[{k!r}] = {v!r}.")
                        continue
                self._deadband_per_tag = clean

    def set_tag_deadband(self, tag_name: str, threshold: float):
        """Per-tag override, settable independently of configure_deadband()
        (e.g. from a future Settings UI) - the default from
        configure_deadband()/DEFAULT_DEADBAND_THRESHOLD still applies to
        every tag with no entry here."""
        with self._deadband_lock:
            self._deadband_per_tag[tag_name] = float(threshold)

    def _should_write(self, tag_name, value, quality) -> bool:
        """True if this tag_changed event should actually reach the
        database. BOOL and STRING values (relay/logic/status signals -
        "kazda zmiana ma znaczenie", GRANICE explicit requirement) always
        return True - the deadband applies only to REAL/INT-shaped numeric
        values. A quality change (e.g. GOOD -> STALE) always counts as
        "changed enough" too, regardless of the numeric deadband - going
        stale/bad is operationally significant on its own and must not be
        silently swallowed just because the last numeric value happens to
        still be within threshold."""
        # isinstance(True, int) is True in Python - bool must be checked
        # before the int/float branch below, or every boolean tag would
        # incorrectly fall into the deadband-filtered path.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return True

        now = time.monotonic()
        with self._deadband_lock:
            prev = self._last_written.get(tag_name)
            if prev is None:
                self._last_written[tag_name] = (value, quality, now)
                return True
            prev_value, prev_quality, prev_time = prev
            threshold = self._deadband_per_tag.get(tag_name, self._deadband_default)
            changed_enough = abs(value - prev_value) >= threshold
            quality_changed = quality != prev_quality
            stale = (now - prev_time) >= self._forced_write_seconds
            if changed_enough or quality_changed or stale:
                self._last_written[tag_name] = (value, quality, now)
                return True
            return False

    # --- Retention (Task: feature/retention-and-test-fix, B1) -----------

    def get_retention_config(self) -> dict:
        with self._retention_lock:
            return {"max_days": self._retention_max_days, "max_rows": self._retention_max_rows}

    def configure_retention(self, max_days: int = None, max_rows: int = None, level: str = None):
        """Either argument left None leaves that limit unchanged; 0 means
        "no limit" for that axis (both independently optional, same
        "liczba dni albo liczba wierszy" shape as intrusion_history.py's
        own precedent). `level`, if given, is a defense-in-depth re-check
        (the GUI dialog that calls this is already Engineer-gated
        visually - this catches a level lost between opening the dialog
        and clicking OK, same belt-and-suspenders pattern
        IntrusionManager.configure_history_retention() already uses) -
        refuses and returns False without changing anything if below
        Engineer. Purges immediately against the NEW limits (not on the
        hot write path - this is a rare, explicit admin action, not
        record_tag_change()'s own producer-side queue.put_nowait())."""
        if level is not None:
            from epw_os.core.access_manager import AccessLevel
            try:
                rank = AccessLevel._ORDER.index(level)
            except (ValueError, TypeError):
                rank = -1  # unrecognized level - same fail-closed stance as intrusion_manager.py's own _level_rank()
            if rank < AccessLevel._ORDER.index(AccessLevel.ENGINEER):
                log.warning(f"Refused to configure Historian retention: level {level!r} is below Engineer.")
                return False
        changed = False
        with self._retention_lock:
            if max_days is not None:
                self._retention_max_days = max(0, int(max_days))
                changed = True
            if max_rows is not None:
                self._retention_max_rows = max(0, int(max_rows))
                changed = True
            cfg = self.get_retention_config()
        if changed and self.audit_logger is not None:
            self.audit_logger.record(
                "HISTORIAN_RETENTION_CONFIG", level or "SYSTEM",
                f"Historian retention set to max_days={cfg['max_days'] or 'unlimited'}, "
                f"max_rows={cfg['max_rows'] or 'unlimited'}.",
            )
        self._enforce_retention()
        return True

    def _enforce_retention(self):
        """Deletes the oldest TagHistory rows beyond max_rows and/or
        older than max_days, in ONE query each (no row-by-row loop) -
        called both immediately from configure_retention() and
        periodically from the worker thread's own loop (see
        _process_queue() below), never from record_tag_change()'s
        producer-side hot path."""
        with self._retention_lock:
            max_days, max_rows = self._retention_max_days, self._retention_max_rows
        if max_days <= 0 and max_rows <= 0:
            return
        db = SessionLocal()
        try:
            to_delete_ids = set()
            if max_days > 0:
                cutoff = datetime.utcnow() - timedelta(days=max_days)
                to_delete_ids.update(
                    r[0] for r in db.query(TagHistory.id).filter(TagHistory.timestamp < cutoff).all()
                )
            if max_rows > 0:
                total = db.query(TagHistory).count()
                excess = total - max_rows
                if excess > 0:
                    to_delete_ids.update(
                        r[0] for r in db.query(TagHistory.id)
                        .order_by(TagHistory.timestamp.asc()).limit(excess).all()
                    )
            if not to_delete_ids:
                return
            timestamps = [r[0] for r in db.query(TagHistory.timestamp)
                          .filter(TagHistory.id.in_(to_delete_ids)).all()]
            oldest, newest = min(timestamps), max(timestamps)
            count = len(to_delete_ids)
            db.query(TagHistory).filter(TagHistory.id.in_(to_delete_ids)).delete(synchronize_session=False)
            db.commit()
        except Exception as e:
            db.rollback()
            log.error(f"Historian retention purge failed: {e}")
            return
        finally:
            db.close()
        # DOWÓD (B1): "fakt usuniecia zapisany do dziennika: ile wierszy,
        # z jakiego zakresu dat" - both the plain application log (this
        # module's own existing logging convention) and, if available,
        # the audit trail (a durable, queryable record - the same
        # collaborator the CONFIG change above is recorded to).
        log.info(f"Historian retention: purged {count} tag_history row(s), "
                 f"{oldest.isoformat()} .. {newest.isoformat()}.")
        if self.audit_logger is not None:
            self.audit_logger.record(
                "HISTORIAN_RETENTION_PURGE", "SYSTEM",
                f"Purged {count} tag_history row(s) dated {oldest.isoformat()} .. {newest.isoformat()}.",
            )

    def start(self):
        self.is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="HistorianWorker")
        self._thread.start()
        log.info("Historian service started.")

    def stop(self):
        log.info("Stopping Historian service... draining queue.")
        self.is_running = False
        self._stop_event.set()
        if self._thread:
            self.queue.put(None)
            self._thread.join(timeout=5.0)
        log.info("Historian service stopped.")
        self.check_worker_errors()

    def flush(self):
        if self.queue.unfinished_tasks > 0:
            self.queue.join()
        self.check_worker_errors()

    def check_worker_errors(self):
        if self._worker_exception:
            raise HistorianException("Historian worker encountered a fatal error") from self._worker_exception

    def record_alarm_transition(self, alarm_id, source_tag, message, priority, state, activation_time):
        if not self.is_running:
            return
        try:
            self.queue.put_nowait({
                "type": "alarm",
                "alarm_id": alarm_id,
                "source_tag": source_tag,
                "message": message,
                "priority": priority,
                "state": state,
                "activation_time": activation_time,
                "timestamp": datetime.utcnow()
            })
        except Exception as e:
            log.error(f"Historian queue full or error: {e}")

    def record_tag_change(self, tag_name, value, quality):
        if not self.is_running:
            return
        if not self._should_write(tag_name, value, quality):
            return

        record = {
            "type": "tag",
            "tag_name": tag_name,
            "data_type": "STRING",
            "quality": str(quality),
            "timestamp": datetime.utcnow(),
            "val_bool": None,
            "val_int": None,
            "val_real": None,
            "val_string": None
        }
        
        if isinstance(value, bool):
            record["data_type"] = "BOOL"
            record["val_bool"] = value
        elif isinstance(value, int):
            record["data_type"] = "INT"
            record["val_int"] = value
        elif isinstance(value, float):
            record["data_type"] = "REAL"
            record["val_real"] = value
        else:
            record["data_type"] = "STRING"
            record["val_string"] = str(value)
            
        try:
            self.queue.put_nowait(record)
        except Exception as e:
            log.error(f"Historian queue full or error: {e}")

    def _run_loop(self):
        try:
            self._process_queue()
        except Exception as e:
            self._worker_exception = e
            log.error(f"Historian worker fatal error: {e}")

    def _process_queue(self):
        while True:
            records = []
            # _persist_records() always calls task_done() for every item in
            # `records` itself (success or failure - see its finally block),
            # so once we've handed records off to it we must NOT also call
            # task_done() for them here on the except path below, or every
            # item gets marked done twice ("task_done() called too many
            # times"). Only items that never made it to _persist_records
            # (e.g. queue.get()/get_nowait() itself raising) are this loop's
            # responsibility to finish.
            handed_off_to_persist = False
            try:
                item = self.queue.get(timeout=0.1)
                if item is None:
                    self.queue.task_done()
                    if self._stop_event.is_set():
                        break
                    continue
                records.append(item)

                while not self.queue.empty() and len(records) < 100:
                    try:
                        next_item = self.queue.get_nowait()
                        if next_item is None:
                            self.queue.task_done()
                            continue
                        records.append(next_item)
                    except queue.Empty:
                        # Deliberate, routine control flow, not an error:
                        # this inner drain loop's own exit condition once
                        # the queue empties out - not logged, it fires on
                        # every single batch (would flood the log).
                        break

                if records:
                    handed_off_to_persist = True
                    self._persist_records(records)
            except queue.Empty:
                # Deliberate, routine control flow (this outer get()'s own
                # 0.1s poll timeout firing with nothing queued) - the
                # normal idle state of this loop, not logged for the same
                # "would flood the log" reason as the inner one above.
                if self._stop_event.is_set() and self.queue.empty():
                    break
            except Exception as e:
                self._worker_exception = e
                log.error(f"Historian batch processing error: {e}")
                if not handed_off_to_persist:
                    for _ in records:
                        self.queue.task_done()
                break

            # Retention (Task B1: "usuwanie w tle, nie w goracej sciezce
            # zapisu") - checked here, on the WORKER thread, at most once
            # every RETENTION_CHECK_INTERVAL_S, regardless of how busy
            # the queue is. Never on record_tag_change()'s own producer-
            # side path (queue.put_nowait(), a different thread entirely).
            now = time.monotonic()
            if now - self._last_retention_check >= RETENTION_CHECK_INTERVAL_S:
                self._last_retention_check = now
                self._enforce_retention()

    def _persist_records(self, records: List[Dict[str, Any]]):
        db = SessionLocal()
        try:
            for rec in records:
                if rec.get("type") == "alarm":
                    activation_time = None
                    if isinstance(rec["activation_time"], float):
                        activation_time = datetime.fromtimestamp(rec["activation_time"])
                        
                    ah = AlarmHistory(
                        alarm_id=rec["alarm_id"],
                        source_tag=rec["source_tag"],
                        message=rec["message"],
                        priority=rec["priority"],
                        state=rec["state"],
                        activation_time=activation_time,
                        clear_time=rec["timestamp"] if rec["state"] in ["NORMAL", "CLEARED_UNACK"] else None,
                        ack_time=rec["timestamp"] if rec["state"] in ["ACTIVE_ACK"] else None
                    )
                    db.add(ah)
                else:
                    th = TagHistory(
                        tag_name=rec["tag_name"],
                        data_type=rec["data_type"],
                        quality=rec["quality"],
                        timestamp=rec["timestamp"],
                        val_bool=rec["val_bool"],
                        val_int=rec["val_int"],
                        val_real=rec["val_real"],
                        val_string=rec["val_string"]
                    )
                    db.add(th)
            db.commit()
        except Exception as db_err:
            db.rollback()
            log.error(f"Historian DB insertion error: {db_err}")
            raise db_err
        finally:
            db.close()
            for _ in records:
                self.queue.task_done()

    # --- read side: general historical export, not tied to Event
    # Recorder's own CSV export (that one exports the operational event
    # log table; this is tag_history - raw trend data) ------------------

    def get_distinct_tag_names(self) -> List[str]:
        """Every tag that actually has recorded history - not the full
        (150+ entry) static tag list, most of which may never have been
        written, so the export dialog's tag picker only offers tags
        worth exporting."""
        db = SessionLocal()
        try:
            rows = db.query(TagHistory.tag_name).distinct().all()
            return sorted(r[0] for r in rows if r[0])
        finally:
            db.close()

    def query_tag_history(self, start_dt: datetime, end_dt: datetime,
                          tag_names: List[str] = None, limit: int = 200000) -> List[TagHistory]:
        """Rows in [start_dt, end_dt], oldest first, optionally restricted
        to tag_names (None/empty = all tags). `limit` is a hard safety cap
        - a huge unbounded query from the GUI thread could otherwise hang
        the app on a long-running installation's history."""
        db = SessionLocal()
        try:
            q = db.query(TagHistory).filter(
                TagHistory.timestamp >= start_dt, TagHistory.timestamp <= end_dt
            )
            if tag_names:
                q = q.filter(TagHistory.tag_name.in_(tag_names))
            q = q.order_by(TagHistory.timestamp.asc()).limit(limit)
            return q.all()
        finally:
            db.close()
