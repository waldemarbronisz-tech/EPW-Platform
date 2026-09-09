"""Dedicated event history for the intrusion (burglar) alarm module
(Task: "historia zdarzen alarmowych") - headless, no Qt import, same
rule every other core/ module follows.

DELIBERATELY SEPARATE from two other things (Task's own wording:
"Osobna od rejestru zdarzen procesowych i od dziennika audytowego"):
- The operational Event Recorder (epw_os/gui/logger.py's ui_logger) is
  GUI-only, in-memory, never persisted - process/alarm events across the
  WHOLE program, not specific to intrusion.
- AuditLogger (epw_os/core/audit_logger.py, table "audit_log") is the
  security/configuration trail for the WHOLE program (logins, PIN
  changes, settings) - IntrusionManager already writes to it for every
  alarm-system action, unchanged by this module. This one is instead the
  complete, INTRUSION-SPECIFIC narrative (arm/disarm, every violation,
  every alarm with its first-cause marking, faults, bypass, suspect
  lines, walk-test, alarm-memory clears) - Task: "Zapisuje WYLACZNIE
  zdarzenia systemu alarmowego."

Same DB (epw_os.db / test_epw_os.db under EPW_TESTING=1) and the same
synchronous-write stance AuditLogger already has (low-frequency-enough,
security/diagnostically-relevant events - not a 250ms tag stream, so no
async queue+worker is needed the way Historian's own TagHistory has).

RETENTION (Task: "konfigurowalna liczba zdarzen albo dni... Historia nie
moze rosnac w nieskonczonosc - docelowa platforma to Orange Pi z karta
SD"): enforced by DELETING the oldest rows immediately after every
write, whenever EITHER configured limit (max_events, max_days - either
may be 0/off) is exceeded - the same "cap + evict" principle
page_event_recorder.py's own MAX_EVENT_ROWS already applies, just
enforced in the database instead of an in-memory deque (this history
needs to survive a restart; an in-memory-only cap would not).
"""
from datetime import datetime, timedelta

from epw_os.db.database import SessionLocal
from epw_os.db.models import IntrusionAlarmHistory
from epw_os.core.logging import log

# 5000 matches page_event_recorder.py's own MAX_EVENT_ROWS default - the
# established "how many rows of history is reasonable on an SD card"
# figure elsewhere in this codebase. 0 = off (unbounded by count).
DEFAULT_MAX_EVENTS = 5000
# 0 = off (unbounded by age) - a pure count cap, same default posture
# Event Recorder's own limit already has (count-only, no day-based
# expiry), left configurable per Task's own "liczba zdarzen ALBO dni".
DEFAULT_MAX_DAYS = 0


class IntrusionAlarmHistoryLogger:
    def __init__(self, project_manager=None, event_bus=None):
        # project_manager: optional - if given, the retention config
        # persists (get/set_intrusion_history_retention()) and survives
        # a restart; without one this logger still works, just with the
        # in-memory defaults above for the lifetime of the process (same
        # "works fine standalone" stance every other optional collaborator
        # in this codebase has - e.g. IntrusionManager itself with no
        # audit_logger).
        self.project_manager = project_manager
        # Optional: mirrors AuditLogger's own event_bus param - lets a
        # live-updating view refresh without polling the DB.
        self.event_bus = event_bus
        self._max_events = DEFAULT_MAX_EVENTS
        self._max_days = DEFAULT_MAX_DAYS
        if project_manager is not None:
            cfg = project_manager.get_intrusion_history_retention()
            self._max_events = int(cfg.get("max_events", DEFAULT_MAX_EVENTS) or 0)
            self._max_days = int(cfg.get("max_days", DEFAULT_MAX_DAYS) or 0)

    def get_retention_config(self) -> dict:
        return {"max_events": self._max_events, "max_days": self._max_days}

    def configure_retention(self, max_events: int = None, max_days: int = None):
        """Either argument left None leaves that limit unchanged. 0 means
        "no limit" for that axis specifically - Task: "konfigurowalna
        liczba zdarzen ALBO dni" (both independently optional)."""
        if max_events is not None:
            self._max_events = max(0, int(max_events))
        if max_days is not None:
            self._max_days = max(0, int(max_days))
        if self.project_manager is not None:
            self.project_manager.set_intrusion_history_retention(self.get_retention_config())
            self.project_manager.save_project()
        self._enforce_retention()

    def record(self, event_type: str, actor: str, detail: str = "",
               zone_id: str = None, zone_name: str = None, line_id: str = None, line_name: str = None):
        db = SessionLocal()
        try:
            entry = IntrusionAlarmHistory(
                timestamp=datetime.utcnow(), event_type=event_type, actor=actor, detail=detail,
                zone_id=zone_id, zone_name=zone_name, line_id=line_id, line_name=line_name,
            )
            db.add(entry)
            db.commit()
        except Exception as e:
            db.rollback()
            log.error(f"IntrusionAlarmHistoryLogger failed to record {event_type}: {e}")
            return
        finally:
            db.close()
        if self.event_bus:
            self.event_bus.emit("intrusion_history_recorded", event_type, actor, detail, zone_id, line_id)
        self._enforce_retention()

    def _enforce_retention(self):
        """Deletes the oldest rows beyond max_events and/or older than
        max_days - called after every write (events are low-frequency
        enough that this is cheap; no periodic sweep needed)."""
        if self._max_events <= 0 and self._max_days <= 0:
            return
        db = SessionLocal()
        try:
            if self._max_days > 0:
                cutoff = datetime.utcnow() - timedelta(days=self._max_days)
                db.query(IntrusionAlarmHistory).filter(IntrusionAlarmHistory.timestamp < cutoff).delete(
                    synchronize_session=False)
            if self._max_events > 0:
                total = db.query(IntrusionAlarmHistory).count()
                excess = total - self._max_events
                if excess > 0:
                    # Oldest-first ids to delete - a plain LIMIT/OFFSET
                    # subquery, cheap even at thousands of rows (id is
                    # the primary key, already indexed).
                    stale_ids = [
                        row.id for row in
                        db.query(IntrusionAlarmHistory.id).order_by(IntrusionAlarmHistory.timestamp.asc()).limit(excess).all()
                    ]
                    if stale_ids:
                        db.query(IntrusionAlarmHistory).filter(IntrusionAlarmHistory.id.in_(stale_ids)).delete(
                            synchronize_session=False)
            db.commit()
        except Exception as e:
            db.rollback()
            log.error(f"IntrusionAlarmHistoryLogger failed to enforce retention: {e}")
        finally:
            db.close()

    def query(self, limit: int = 500, zone_id: str = None, event_type: str = None, start=None, end=None):
        """Most recent entries first - Task: "lista chronologiczna,
        filtrowanie po dacie, typie zdarzenia i strefie". `start`/`end`
        are datetime objects (inclusive), `zone_id`/`event_type` exact
        matches; any left None is simply not filtered on."""
        db = SessionLocal()
        try:
            q = db.query(IntrusionAlarmHistory)
            if zone_id:
                q = q.filter(IntrusionAlarmHistory.zone_id == zone_id)
            if event_type:
                q = q.filter(IntrusionAlarmHistory.event_type == event_type)
            if start is not None:
                q = q.filter(IntrusionAlarmHistory.timestamp >= start)
            if end is not None:
                q = q.filter(IntrusionAlarmHistory.timestamp <= end)
            return q.order_by(IntrusionAlarmHistory.timestamp.desc()).limit(limit).all()
        finally:
            db.close()

    def distinct_event_types(self) -> list:
        """GUI convenience - populates the History tab's "event type"
        filter dropdown from whatever actually exists in the table,
        rather than a hand-maintained list that could drift out of sync
        with the event_type strings this module and IntrusionManager
        actually use."""
        db = SessionLocal()
        try:
            rows = db.query(IntrusionAlarmHistory.event_type).distinct().order_by(IntrusionAlarmHistory.event_type).all()
            return [r[0] for r in rows if r[0]]
        finally:
            db.close()
