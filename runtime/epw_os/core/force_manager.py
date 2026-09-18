"""Forcing (SPEC_PROJEKT_EPW.md, "Wymuszanie stanów — dozwolone,
obwarowane"): Studio may pin an input or drive an output for
commissioning and tests, the way every PLC tool's force table does.
The three conditions the SPEC sets are all enforced HERE, not only in
Studio's own dialogs:

1. Off by default and deliberate: only an Engineer (the REST token's
   level) may force, and every force, release and expiry is an audit
   entry.
2. Visible on both sides: `forces_changed` is emitted on every change,
   the panel's status bar shows "WYMUSZENIA: n" (main_window.py) and a
   forced tag reads as forced in GET /api/v1/forces.
3. Gone in one move, and gone on its own: release_all() at any time,
   automatically when Studio's heartbeat stops (HEARTBEAT_TIMEOUT_S -
   a closed laptop must not leave a force behind) and at shutdown,
   which means a restart never inherits one (nothing is persisted).

What may NEVER be forced - protected_reason(): anything that is not a
point of the project (system, safety and device-status tags), and the
points of an apparatus on the protection path - a breaker/protection
apparatus by its kind or its Q designation (IEC 81346). ADA01's own
trip path is hardware and out of reach of any driver anyway; this rule
keeps runtime from pretending otherwise.

How a force works: TagManager pins the tag (every DRIVER/LOGIC/SYSTEM
update to it is dropped while forced - publish_forced() is the one
door), so logic and screens see the forced value exactly as they would
a real one. An OUTPUT force additionally writes the value through
DriverManager.route_command() - the same boundary a command uses, so
Training Mode cuts it off there just like a command - and
CommandManager refuses commands whose output is forced.
"""
import threading
import time
from typing import Optional

from epw_os.core.addressing import try_parse_address
from epw_os.core.logging import log
from epw_os.core.tag_manager import TagQuality

HEARTBEAT_TIMEOUT_S = 15.0
WATCH_INTERVAL_S = 2.0
INPUT_KINDS = ("DI", "AI")
OUTPUT_KINDS = ("DO", "AO")
# An apparatus whose kind names a breaker or a protection function, or
# whose designation is a Q (circuit breaker in IEC 81346), is on the
# protection path: its points are never forced.
PROTECTED_KIND_WORDS = ("BREAKER", "PROTECT", "TRIP", "WYLACZNIK", "WYŁĄCZNIK", "ZABEZP")


class ForceManager:
    def __init__(self, event_bus, tag_manager, driver_manager=None, audit_logger=None, apparatus_registry=None,
                 driver_for_tag=None, heartbeat_timeout_s: float = HEARTBEAT_TIMEOUT_S):
        self.event_bus = event_bus
        self.tag_manager = tag_manager
        self.driver_manager = driver_manager
        self.audit_logger = audit_logger
        self.apparatus_registry = apparatus_registry
        self._driver_for_tag = driver_for_tag
        self.heartbeat_timeout_s = float(heartbeat_timeout_s)
        self._forces = {}            # tag -> {"value", "kind", "actor", "since"}
        self._lock = threading.RLock()
        self._last_heartbeat = None
        self._watch_stop = threading.Event()
        self._watch_thread = None

    # --- rules --------------------------------------------------------------------------

    def protected_reason(self, tag_name: str) -> Optional[str]:
        """Why `tag_name` may not be forced, or None when it may."""
        parsed = try_parse_address(tag_name)
        if parsed is None:
            return "not a point of the project (system, safety and status tags are never forced)"
        if self.apparatus_registry is not None:
            for apparatus_id in self.apparatus_registry.list_ids():
                apparatus = self.apparatus_registry.get(apparatus_id)
                if apparatus is None:
                    continue
                if tag_name not in list(apparatus.feedback) + list(apparatus.command):
                    continue
                kind = (getattr(apparatus, "kind", "") or "").upper()
                designation = str(apparatus_id).split("_")[-1].upper()
                if any(word in kind for word in PROTECTED_KIND_WORDS) or designation.startswith("Q"):
                    return f"{tag_name} belongs to {apparatus_id} on the protection path - never forced"
        return None

    @staticmethod
    def kind_of(tag_name: str) -> Optional[str]:
        parsed = try_parse_address(tag_name)
        return parsed[1] if parsed else None

    # --- forcing ------------------------------------------------------------------------

    def force(self, tag_name: str, value, actor: str = "Engineer") -> tuple:
        """(True, "") or (False, reason). Pins the tag; an output is also
        written through the driver boundary."""
        reason = self.protected_reason(tag_name)
        if reason:
            self._audit("FORCE_REFUSED", actor, f"{tag_name} = {value!r}: {reason}", success=False)
            return False, reason
        if self.tag_manager.get_tag(tag_name) is None:
            reason = f"unknown tag {tag_name}"
            self._audit("FORCE_REFUSED", actor, f"{tag_name}: {reason}", success=False)
            return False, reason
        kind = self.kind_of(tag_name)
        with self._lock:
            self._forces[tag_name] = {"value": value, "kind": kind, "actor": actor, "since": time.time()}
            self._last_heartbeat = time.time()
            self.tag_manager.set_forced(tag_name, True)
        if kind in OUTPUT_KINDS and self.driver_manager is not None:
            driver_id = self._driver_for_tag(tag_name) if callable(self._driver_for_tag) else None
            if driver_id is not None:
                self.driver_manager.route_command(driver_id, tag_name, value)
        self.tag_manager.publish_forced(tag_name, value)
        self._audit("FORCE_SET", actor, f"{tag_name} = {value!r} ({kind})")
        log.warning(f"FORCE {tag_name} = {value!r} by {actor}")
        self._changed()
        self._ensure_watch()
        return True, ""

    def release(self, tag_name: str, actor: str = "Engineer", reason: str = "") -> bool:
        with self._lock:
            entry = self._forces.pop(tag_name, None)
            if entry is None:
                return False
            self.tag_manager.set_forced(tag_name, False)
        # An input's real value is not known until the driver's next poll:
        # say so, rather than keep showing the forced one as GOOD.
        if entry["kind"] in INPUT_KINDS:
            self.tag_manager.update_tag(tag_name, entry["value"], TagQuality.UNCERTAIN)
        detail = f"{tag_name} (was {entry['value']!r})" + (f" - {reason}" if reason else "")
        self._audit("FORCE_RELEASED", actor, detail)
        log.warning(f"FORCE released {tag_name} by {actor}{' - ' + reason if reason else ''}")
        self._changed()
        return True

    def release_all(self, actor: str = "Engineer", reason: str = "") -> int:
        with self._lock:
            tags = list(self._forces)
        for tag in tags:
            self.release(tag, actor, reason)
        if tags:
            self._audit("FORCE_RELEASED_ALL", actor, f"{len(tags)} force(s)" + (f" - {reason}" if reason else ""))
        return len(tags)

    def is_forced(self, tag_name: str) -> bool:
        with self._lock:
            return tag_name in self._forces

    def snapshot(self) -> list:
        with self._lock:
            return [{"tag": tag, **dict(entry)} for tag, entry in sorted(self._forces.items())]

    # --- the heartbeat: a force outlives nobody -----------------------------------------

    def heartbeat(self):
        with self._lock:
            self._last_heartbeat = time.time()

    def seconds_since_heartbeat(self) -> Optional[float]:
        with self._lock:
            return None if self._last_heartbeat is None else time.time() - self._last_heartbeat

    def check_expiry(self) -> int:
        """Releases everything when Studio's heartbeat stopped. Returns
        how many forces were released."""
        with self._lock:
            if not self._forces or self._last_heartbeat is None:
                return 0
            expired = time.time() - self._last_heartbeat > self.heartbeat_timeout_s
        if not expired:
            return 0
        return self.release_all("SYSTEM", f"heartbeat lost for more than {self.heartbeat_timeout_s:.0f} s")

    def _ensure_watch(self):
        if self._watch_thread is not None and self._watch_thread.is_alive():
            return
        self._watch_stop.clear()
        self._watch_thread = threading.Thread(target=self._watch_loop, name="ForceWatch", daemon=True)
        self._watch_thread.start()

    def _watch_loop(self):
        while not self._watch_stop.wait(WATCH_INTERVAL_S):
            try:
                self.check_expiry()
            except Exception as e:  # noqa: BLE001 - the watch must outlive one bad tick
                log.error(f"ForceManager watch: {e}")
            with self._lock:
                if not self._forces:
                    return

    def shutdown(self):
        """Every force goes with the process: a restart never inherits one."""
        self._watch_stop.set()
        self.release_all("SYSTEM", "shutdown")

    # --- plumbing -----------------------------------------------------------------------

    def _audit(self, event_type, actor, detail, success=True):
        if self.audit_logger is not None:
            self.audit_logger.record(event_type, actor, detail, success=success)

    def _changed(self):
        if self.event_bus is not None:
            self.event_bus.emit("forces_changed", len(self._forces))
