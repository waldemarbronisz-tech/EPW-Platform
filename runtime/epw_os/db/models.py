from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from epw_os.db.database import Base
from datetime import datetime

class TagHistory(Base):
    """
    Persists tag changes with strongly typed columns to preserve data integrity.
    Only the column matching the 'data_type' string is populated.
    """
    __tablename__ = "tag_history"

    id = Column(Integer, primary_key=True, index=True)
    tag_name = Column(String, index=True)
    data_type = Column(String, nullable=True)  # BOOL, INT, REAL, STRING, etc.
    quality = Column(String, nullable=True)    # GOOD, BAD, etc.
    
    val_bool = Column(Boolean, nullable=True)
    val_int = Column(Integer, nullable=True)
    val_real = Column(Float, nullable=True)
    val_string = Column(String, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class AuditLog(Base):
    """Independent security/configuration audit trail - logins, PIN
    changes, Protection Settings changes, language changes. Deliberately
    separate from TagHistory/AlarmHistory above (operational process
    data) and from the GUI-only ui_logger Event Recorder feed
    (epw_os/gui/logger.py, in-memory only, never persisted here) - see
    epw_os/core/audit_logger.py and SESSION_REPORT.md for the reasoning.
    """
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String, index=True)  # LOGIN, PIN_CHANGE, SETTING_CHANGE, LANGUAGE_CHANGE
    actor = Column(String, nullable=True)     # access level or identity acting (e.g. "Engineer")
    detail = Column(String, nullable=True)    # human-readable description
    success = Column(Boolean, default=True)   # e.g. False for a failed login attempt


class AlarmHistory(Base):
    __tablename__ = "alarm_history"

    id = Column(Integer, primary_key=True, index=True)
    alarm_id = Column(String, index=True)
    source_tag = Column(String, nullable=True)
    message = Column(String)
    priority = Column(Integer)
    state = Column(String) # NORMAL, ACTIVE_UNACK, etc.
    activation_time = Column(DateTime, nullable=True)
    clear_time = Column(DateTime, nullable=True)
    ack_time = Column(DateTime, nullable=True)


class IntrusionAlarmHistory(Base):
    """Task ("historia zdarzen alarmowych"): a dedicated event history
    for the intrusion (burglar) alarm module ONLY - deliberately
    separate from AlarmHistory above (process alarms, a different
    domain entirely - see intrusion_manager.py's own module docstring
    on why the two managers are never merged) and from AuditLog (every
    security/config action across the whole program, not just this
    module). Written by epw_os/core/intrusion_history.py's
    IntrusionAlarmHistoryLogger, which also enforces the configurable
    retention this table needs (Task: "Historia nie moze rosnac w
    nieskoncznosc - docelowa platforma to Orange Pi z karta SD") -
    nothing here caps growth on its own; the logger prunes old rows
    after every write.
    """
    __tablename__ = "intrusion_alarm_history"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String, index=True)   # INTRUSION_ZONE_ARMED, INTRUSION_ALARM, INTRUSION_LINE_VIOLATED, ...
    actor = Column(String, nullable=True)
    detail = Column(String, nullable=True)
    zone_id = Column(String, index=True, nullable=True)
    zone_name = Column(String, nullable=True)
    line_id = Column(String, nullable=True)
    line_name = Column(String, nullable=True)
