"""Per-device switching (mechanical wear) counters (Task: liczba
przelaczen i czas w stanie zamknietym per aparat).

Headless (no PyQt import), same rule as every other core/ module -
subscribes directly to the core EventBus's "tag_changed" event, exactly
like epw_os/core/historian.py does, so counting works identically
whether or not a GUI is attached, and needs no polling.

WHAT IS COUNTED: every Digital Input tag (DIn) - "tag wejsciowy" per the
task - is the feedback/state tag for a switching device (see
epw_core.py's default command definitions: DO01-04's CLOSE/OPEN write
straight to DI1-4, and DO05-64 are self-contained). A tag's value True/1
means "closed" (matches the rest of the app's ON/CLOSED convention -
Lamp state==1, page_digital_inputs.py's state_on text, etc.).

DESIGN NOTES (GRANICE):

- "Zliczanie nie moze spowalniac przetwarzania zmian tagow": the
  tag_changed handler below is a handful of dict lookups/updates guarded
  by one short-held lock - no I/O, no disk access, O(1) per call.
- "Zapis na dysk nie przy kazdej zmianie stanu - buforuj i zapisuj
  okresowo": in-memory counters are the live source of truth while
  running; flush_to_project() (periodic background thread, see start()/
  stop()) is the only thing that touches disk, and only copies out the
  current snapshot - never called from the tag_changed path itself.
- Restart persistence: a currently-closed device's `closed_since`
  timestamp is itself persisted (not just the accumulated total) - so a
  device that is STILL closed across a restart keeps accruing its
  closed-time seamlessly (the interval spans the restart), rather than
  losing whatever fraction of the closed period fell in the previous
  run. See _on_tag_changed()'s docstring for exactly how a discrepancy
  between the persisted and newly-observed state is handled.
"""
import threading
import time
from typing import Optional

from epw_os.core.logging import log

PROJECT_KEY = "switching_counters"
DEFAULT_SAVE_INTERVAL_SECONDS = 60.0

_RECORD_KEYS = (
    "closes", "opens", "closed_seconds", "closed_since",
    "first_transition", "last_transition", "warning_threshold",
)


def new_record(warning_threshold: Optional[int] = None) -> dict:
    return {
        "closes": 0,
        "opens": 0,
        "closed_seconds": 0.0,
        "closed_since": None,       # epoch seconds while closed, else None
        "first_transition": None,   # epoch seconds of the first-ever recorded transition
        "last_transition": None,    # epoch seconds of the most recent recorded transition
        "warning_threshold": warning_threshold,
    }


def _normalize_record(raw, tag_name: str = None) -> dict:
    """Never raises - a corrupt/partial/old-format persisted record
    falls back to a fresh one, same defensive stance as every other
    load_*() in this codebase (e.g. window_state.py). `tag_name` is
    optional and used only for the log lines below - passing it costs
    the caller nothing when known, and its absence changes no behavior."""
    record = new_record()
    if not isinstance(raw, dict):
        return record
    for key in _RECORD_KEYS:
        if key in raw:
            record[key] = raw[key]
    try:
        record["closes"] = int(record["closes"])
        record["opens"] = int(record["opens"])
        record["closed_seconds"] = float(record["closed_seconds"])
    except (TypeError, ValueError):
        # A corrupt/incompatible persisted counter silently resetting a
        # device's mechanical-wear history to zero is real data loss with
        # no other trace - same "polykane wyjatki" pattern as
        # System.Mode. Kept fail-safe (fresh record, unchanged) - now
        # also logged.
        log.warning(f"Resetting corrupt switching-counter record for {tag_name!r}: {raw!r}")
        return new_record()
    if record["warning_threshold"] is not None:
        try:
            record["warning_threshold"] = int(record["warning_threshold"])
        except (TypeError, ValueError):
            log.warning(f"Ignoring malformed warning_threshold {record['warning_threshold']!r} "
                        f"for {tag_name!r}.")
            record["warning_threshold"] = None
    return record


def format_duration(seconds: float) -> str:
    """"3d 04:12:05"-style, dropping the day part when zero - compact
    enough for a table column, precise enough to be useful. Never
    raises; a negative/garbage input just renders as 0."""
    try:
        total = max(0, int(seconds))
    except (TypeError, ValueError):
        total = 0
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days:
        return f"{days}d {hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class SwitchingCounterManager:
    def __init__(self, event_bus, project_manager, save_interval_seconds: float = DEFAULT_SAVE_INTERVAL_SECONDS):
        self.event_bus = event_bus
        self.project_manager = project_manager
        self.save_interval_seconds = save_interval_seconds

        self._lock = threading.RLock()
        self._counters = {}       # tag_name -> record dict
        self._last_known_state = {}  # tag_name -> bool, to detect real transitions
        self._dirty = False

        self._stop_event = threading.Event()
        self._thread = None

        self._load_from_project()
        self.event_bus.subscribe("tag_changed", self._on_tag_changed)

    # --- loading / persistence ------------------------------------

    def _load_from_project(self):
        persisted = self.project_manager.get_switching_counters()
        for tag_name, raw in persisted.items():
            record = _normalize_record(raw, tag_name=tag_name)
            self._counters[tag_name] = record
            # Seed last-known state from what was persisted (not from
            # a live tag read - project_manager has no tag_manager
            # reference) - see _on_tag_changed()'s docstring for how a
            # later mismatch against the tag's real post-restart value
            # is reconciled.
            self._last_known_state[tag_name] = record["closed_since"] is not None

    def flush_to_project(self):
        """Copies the current snapshot into project_manager's config and
        saves - the only place that touches disk. Safe to call anytime
        (periodic thread, explicit reset, or shutdown); a no-op if
        nothing changed since the last flush."""
        with self._lock:
            if not self._dirty:
                return
            snapshot = {tag: dict(record) for tag, record in self._counters.items()}
            self._dirty = False
        self.project_manager.set_switching_counters(snapshot)
        self.project_manager.save_project()

    # --- lifecycle (periodic background save) -----------------------

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._periodic_save_loop, daemon=True, name="SwitchingCounterSaver"
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        self.flush_to_project()
        # Task (feature-configuration toggle: "wylaczona funkcja... nie
        # tworzy watkow"): this manager registers no tags of its own -
        # only the periodic-save thread above and this tag_changed
        # subscription need detaching for a genuinely clean live stop
        # (as opposed to a process-exit stop, where a dangling
        # subscription on an EventBus that's about to disappear anyway
        # was harmless and this line was never needed before).
        self.event_bus.unsubscribe("tag_changed", self._on_tag_changed)

    def _periodic_save_loop(self):
        # wait() returns True the instant stop() sets the event, so
        # shutdown doesn't block for a whole save_interval_seconds.
        while not self._stop_event.wait(self.save_interval_seconds):
            self.flush_to_project()

    # --- counting ------------------------------------------------------

    def _on_tag_changed(self, tag_name, value, quality):
        """Only Digital Input tags (DI<n>) are counted - see module
        docstring. Runs synchronously on whatever thread emitted the
        event (EventBus.emit() itself is synchronous) - kept
        deliberately cheap (dict lookups under one short lock, no I/O)
        so it never becomes the bottleneck for tag processing.

        A transition is only counted when `_last_known_state` already
        holds a PREVIOUS value for this tag that differs from the new
        one. The first time a tag is ever seen (no previous value at
        all - a brand-new tag, or the very first run) is never counted:
        there is nothing to call it a transition FROM. This same rule
        transparently handles the restart case too: _load_from_project()
        seeds `_last_known_state` from the PERSISTED state, so if the
        device is observed in that same state after restart (the common
        case - nothing changed while the program was down), it is
        correctly treated as "no transition" and the closed_since
        timestamp (already persisted) keeps accruing seamlessly across
        the restart. Only a genuine mismatch (the device's real state
        changed while the program was not running to see the edge) is
        treated as a transition happening now - which slightly
        overstates precisely when it happened, but never drops or
        double-counts it."""
        # Task "migracja adresacji": was `tag_name.startswith("DI") and
        # tag_name[2:].isdigit()` - never matched this codebase's own
        # multi-device tag shape at all (ADDRESSING_INVENTORY.md §3.2c),
        # so switching counters would have silently stopped being
        # tracked for any project with real ELA cards. addressing.
        # is_address() is the one shared grammar check every subsystem
        # now uses instead of its own opinion.
        from epw_os.core.addressing import is_address
        if not is_address(tag_name, "DI"):
            return
        if isinstance(value, bool):
            bool_value = value
        elif isinstance(value, int):
            bool_value = bool(value)
        else:
            return

        with self._lock:
            prev = self._last_known_state.get(tag_name)
            self._last_known_state[tag_name] = bool_value
            if prev is None or prev == bool_value:
                return

            now = time.time()
            record = self._counters.setdefault(tag_name, new_record())
            if record["first_transition"] is None:
                record["first_transition"] = now
            record["last_transition"] = now

            if bool_value:
                record["closes"] += 1
                record["closed_since"] = now
            else:
                record["opens"] += 1
                if record["closed_since"] is not None:
                    record["closed_seconds"] += now - record["closed_since"]
                    record["closed_since"] = None
            self._dirty = True

    # --- reading (GUI-facing) -------------------------------------------

    def get_snapshot(self, tag_name: str) -> dict:
        """A read-only copy with closed_seconds already including the
        CURRENTLY-open closed interval (if any) up to this exact moment -
        what a display should show right now, not just the total as of
        the last completed close->open cycle."""
        with self._lock:
            record = self._counters.get(tag_name)
            if record is None:
                return new_record()
            snapshot = dict(record)
        if snapshot["closed_since"] is not None:
            snapshot["closed_seconds"] += time.time() - snapshot["closed_since"]
        return snapshot

    def is_over_threshold(self, tag_name: str) -> bool:
        record = self._counters.get(tag_name)
        if not record or record.get("warning_threshold") is None:
            return False
        return record["closes"] >= record["warning_threshold"]

    def set_warning_threshold(self, tag_name: str, threshold):
        """`threshold` of None clears it (task: "opcjonalny")."""
        with self._lock:
            record = self._counters.setdefault(tag_name, new_record())
            record["warning_threshold"] = int(threshold) if threshold is not None else None
            self._dirty = True

    def restore_record(self, tag_name: str, record: dict):
        """Presentation Mode's own restore-on-stop path (Task: scenariusz
        5 - zuzycie mechaniczne - GRANICE: "liczniki NIE MOGA byc
        trwale zafalszowane... po zatrzymaniu wartosci maja wrocic do
        stanu sprzed uruchomienia"). Overwrites tag_name's counter
        record wholesale with a previously-captured snapshot (see
        get_snapshot()) - including warning_threshold, so a scenario
        that temporarily lowered it for a short demo (Task: scenariusz
        5's counter_threshold step) reverts that too - and re-derives
        _last_known_state from the restored record's own closed_since,
        so a real transition reported afterward is counted correctly
        against the restored state, not against whatever this
        function's own overwrite implies mid-flight. Does not touch
        _on_tag_changed()'s counting logic at all - purely an
        additional way to overwrite a record, the same shape
        reset_counter() above already establishes. Marks dirty so the
        reverted value is what the next periodic save (or shutdown
        flush) actually persists - never itself touches disk."""
        with self._lock:
            normalized = _normalize_record(record, tag_name=tag_name)
            self._counters[tag_name] = normalized
            self._last_known_state[tag_name] = normalized["closed_since"] is not None
            self._dirty = True

    def reset_counter(self, tag_name: str) -> dict:
        """Zeroes closes/opens/closed_seconds/timestamps for `tag_name`
        (Task: "do uzycia po wymianie aparatu") - the warning threshold
        is NOT cleared (a replaced device on the same site typically
        keeps the same maintenance interval). If the device is currently
        known to be closed, tracking continues seamlessly from now
        rather than being lost. Returns the OLD record (for an audit-log
        message showing what was reset) - the caller is responsible for
        actually writing to the audit log (this module has no
        audit_logger reference, staying framework-agnostic)."""
        with self._lock:
            old = self._counters.get(tag_name, new_record())
            was_closed = self._last_known_state.get(tag_name, False)
            fresh = new_record(warning_threshold=old.get("warning_threshold"))
            if was_closed:
                fresh["closed_since"] = time.time()
            self._counters[tag_name] = fresh
            self._dirty = True
            return dict(old)
