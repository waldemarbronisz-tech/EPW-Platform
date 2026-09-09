"""Per-device service history (Task: historia serwisowa przypisana do
aparatu). Headless (no PyQt import), same rule as every other core/
module.

Complements epw_os/core/switching_counters.py (B3) rather than
duplicating it: counters say HOW MANY / HOW LONG (derived automatically
from tag changes); notes say WHAT HAPPENED (written by a person, by
hand). Together they're the object's history, not just its live state.

Deliberately NOT the audit log (epw_os/core/audit_logger.py): the audit
log is an automatic record of actions taken IN THE SYSTEM (logins, PIN
changes, setting changes) - it fires itself, from code, whenever a
gated action happens. A service note is the opposite: nothing in the
system ever writes one on its own, only a person deciding to record
something ("replaced contact set, visible pitting"). Mixing the two
would bury deliberate maintenance history inside a stream of routine
system bookkeeping, and vice versa (GRANICE: "nie mieszaj z dziennikiem
audytowym").

Entries are permanently immutable (Task: "NIEUSUWALNE i NIEEDYTOWALNE -
to dziennik, nie notatnik") - this module simply never exposes an edit
or delete method, for any level, including Engineer. A mistake is
corrected the way a paper logbook is: with another entry. get_notes()
also returns a deep copy, so nothing a caller does to the returned list
can reach back into the stored data either.
"""
import csv
import io
import time
from datetime import datetime
from typing import Optional

from epw_os.core.access_manager import AccessLevel
from epw_os.core.logging import log

PROJECT_KEY = "service_notes"

_LEVEL_ORDER = AccessLevel._ORDER  # ["User", "Operator", "Engineer"]


def _level_rank(level) -> int:
    try:
        return _LEVEL_ORDER.index(level)
    except ValueError:
        # Already deliberate/documented (fail-closed) - now also logged,
        # since `level` reaching here unrecognized is always a caller
        # bug, and silence is exactly the "polykane wyjatki" pattern
        # System.Mode had.
        log.warning(f"ServiceNoteManager._level_rank() got an unrecognized level {level!r} - denying.")
        return -1  # an unrecognized level string is always denied, not trusted


def format_timestamp(epoch_seconds) -> str:
    """Local date/time for a note's timestamp, or "N/A" for a missing
    one - same rendering every other timestamp in this app uses
    (%Y-%m-%d %H:%M:%S), never raises."""
    if epoch_seconds is None:
        return "N/A"
    try:
        return datetime.fromtimestamp(epoch_seconds).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OSError):
        # Deliberate, not logged: the "N/A" this returns IS already the
        # visible signal (shown directly in the notes table) - unlike
        # System.Mode, nothing here is hidden.
        return "N/A"


def _normalize_note(raw) -> Optional[dict]:
    """Defensive load - a corrupt/partial persisted entry is dropped
    rather than crashing startup (same stance as every other load_*()
    in this codebase), but unlike a corrupt counter record (replaced
    with a fresh zeroed one), a note has no sensible "fresh" fallback -
    if it can't be trusted, it's simply not shown."""
    if not isinstance(raw, dict):
        log.warning(f"Dropping a persisted service note: not a dict ({raw!r}).")
        return None
    text = raw.get("text")
    timestamp = raw.get("timestamp")
    author_level = raw.get("author_level")
    if not isinstance(text, str) or not text.strip():
        log.warning(f"Dropping a persisted service note: missing/blank text ({raw!r}).")
        return None
    try:
        timestamp = float(timestamp)
    except (TypeError, ValueError):
        log.warning(f"Dropping a persisted service note (text={text!r}): non-numeric timestamp {timestamp!r}.")
        return None
    if not isinstance(author_level, str):
        log.warning(f"Dropping a persisted service note (text={text!r}): invalid author_level {author_level!r}.")
        return None
    return {"text": text, "timestamp": timestamp, "author_level": author_level}


class ServiceNoteManager:
    def __init__(self, project_manager):
        self.project_manager = project_manager
        self._notes = {}  # tag_name -> list[note dict], append-only
        self._load_from_project()

    def _load_from_project(self):
        persisted = self.project_manager.get_service_notes()
        for tag_name, raw_notes in persisted.items():
            if not isinstance(raw_notes, list):
                continue
            normalized = [n for n in (_normalize_note(r) for r in raw_notes) if n is not None]
            if normalized:
                self._notes[tag_name] = normalized

    def _save(self):
        # Notes are added rarely (a person typing an entry, not a
        # per-tag-change event stream) and each one matters - unlike
        # switching_counters.py's buffered/periodic save, this writes
        # to disk immediately, every time, the same "never let a crash
        # between queued and flushed lose one" reasoning
        # epw_os/core/audit_logger.py's own docstring already applies
        # to its low-frequency, must-not-lose writes.
        snapshot = {tag: list(notes) for tag, notes in self._notes.items()}
        self.project_manager.set_service_notes(snapshot)
        self.project_manager.save_project()

    def add_note(self, tag_name: str, text: str, author_level: str, timestamp: float = None) -> Optional[dict]:
        """Task: "dodawanie wpisu: poziom Operator lub wyzszy" - enforced
        HERE too, not only by the GUI's Add control being
        disabled/hidden for User: the same defense-in-depth every
        other access-gated action in this app already uses. An
        unrecognized or below-Operator author_level is silently
        refused (returns None); the GUI is expected to have already
        denied the attempt through its own access_manager check before
        ever calling this - this is the last line of defense, not the
        first. An empty (or whitespace-only) note is refused too -
        there is nothing to record.

        Returns a copy of the stored note (or None if refused) - never
        the internal list itself."""
        if _level_rank(author_level) < _level_rank(AccessLevel.OPERATOR):
            log.warning(
                f"Refused to add a service note for {tag_name}: "
                f"author level {author_level!r} is below Operator."
            )
            return None
        text = (text or "").strip()
        if not text:
            return None
        note = {
            "text": text,
            "timestamp": timestamp if timestamp is not None else time.time(),
            "author_level": author_level,
        }
        self._notes.setdefault(tag_name, []).append(note)
        self._save()
        return dict(note)

    def get_notes(self, tag_name: str) -> list:
        """Task: "podglad: dla kazdego, bez ograniczen" - no access
        check here at all. Returns a fresh list of fresh dict copies -
        mutating the result can never reach the stored entries (part of
        the immutability guarantee, alongside simply never exposing an
        edit/delete method)."""
        return [dict(n) for n in self._notes.get(tag_name, [])]


def build_device_report_csv(properties: "dict[str, str]", notes: list) -> str:
    """One combined CSV (Task: "eksport notatek do CSV razem z reszta
    danych aparatu") - a Property/Value section (whatever the caller
    already has on screen: description, tag, counters, ...) followed by
    a blank separator row and a Timestamp/Access Level/Note table, oldest
    note first (a report reads naturally start to finish; the on-screen
    table shows newest-first instead, for at-a-glance monitoring - two
    different, equally reasonable orderings for two different purposes).

    Column headers are plain, untranslated English literals, matching
    every other CSV export in this app (Event Recorder, Historian
    export) - GRANICE only requires the note TEXT itself go untranslated
    (it's the operator's own words), but this project's established
    convention already keeps every CSV header language-independent too,
    so a file opened on a different workstation still makes sense."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Property", "Value"])
    for key, value in properties.items():
        writer.writerow([key, value])
    writer.writerow([])
    writer.writerow(["Timestamp", "Access Level", "Note"])
    for note in sorted(notes, key=lambda n: n["timestamp"]):
        writer.writerow([format_timestamp(note["timestamp"]), note["author_level"], note["text"]])
    return buf.getvalue()
