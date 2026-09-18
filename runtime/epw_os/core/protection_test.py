"""The "internal Omicron" (SPEC_PROJEKT_EPW.md, "Wymuszanie stanów -
Powiązanie"): a protection test is a forced state, a measured response
time and a report - on the same ForceManager the commissioning forces
use, so it is Engineer-only, audited, visible at the cabinet and
released on its own if Studio disappears.

Two kinds, both headless (no Qt - unlike gui's ProtectionVerifier, the
panel's own ramp test, which stays as it is):

  process   - a PROCESS protection (process_protection_manager.py,
              evaluated in software): its analog point is forced past
              the upper threshold, the time until Process.<id>.Exceeded
              latches is measured against the configured delay, then
              the point is forced back inside the band and the time
              until the latch clears is measured; the force is released.
  apparatus - a SWITCHED apparatus with a command and a feedback point:
              the command that changes its state (OPEN when it reads
              closed, CLOSE otherwise) goes through CommandManager - the
              real path, with every interlock and safety check - and the
              time until the feedback follows is measured; then the
              opposite command restores it and that time is measured
              too.

Electrical protection stages are ADA01's own (hardware); this runner
does not pretend to test them - the panel's ProtectionVerifier ramps a
measurement for that, at the cabinet.

Reports are kept in memory and appended to protection_test_reports.json
next to the runtime (evidence, not project data); every start and
result is an audit entry (PROTECTION_TEST_*). One test at a time.
"""
import json
import os
import threading
import time
import uuid
from datetime import datetime

from epw_os.core.logging import log

REPORTS_FILE_NAME = "protection_test_reports.json"
MAX_REPORTS = 500
FEEDBACK_TIMEOUT_S = 5.0        # after a command, how long the feedback may take (the panel's own verifier used 5 s)
RESET_TIMEOUT_S = 5.0           # how long the latch may take to clear once the value is back in band
TRIP_GRACE_S = 3.0              # on top of the configured delay


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class ProtectionTestRunner:
    def __init__(self, core, reports_file=None):
        self.core = core
        self.reports_file = reports_file or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", REPORTS_FILE_NAME)
        self.reports = []
        self._lock = threading.RLock()
        self._running = None       # the report of the test in progress, or None
        self._thread = None
        self._load()

    # --- reports --------------------------------------------------------------------------

    def _load(self):
        try:
            with open(self.reports_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self.reports = [r for r in data if isinstance(r, dict)][-MAX_REPORTS:]
        except (OSError, ValueError):
            self.reports = []

    def _save(self):
        try:
            from epw_os.core.local_json import atomic_write_json
            atomic_write_json(self.reports_file, self.reports[-MAX_REPORTS:])
        except OSError as e:
            log.error(f"Protection test reports not written to {self.reports_file}: {e}")

    def list_reports(self) -> list:
        with self._lock:
            return [dict(r) for r in self.reports]

    def running(self):
        with self._lock:
            return dict(self._running) if self._running else None

    def get(self, test_id: str):
        with self._lock:
            if self._running and self._running["id"] == test_id:
                return dict(self._running)
            for report in self.reports:
                if report["id"] == test_id:
                    return dict(report)
        return None

    def candidates(self) -> dict:
        """What can be tested on this controller right now."""
        process = []
        ppm = getattr(self.core, "process_protection_manager", None)
        if ppm is not None:
            for p in ppm.get_protections():
                process.append({"id": p["id"], "name": p.get("name", ""), "analog_tag": p.get("analog_tag"),
                                "upper_threshold": p.get("upper_threshold"), "lower_threshold": p.get("lower_threshold"),
                                "delay_seconds": p.get("delay_seconds"), "enabled": bool(p.get("enabled", True)),
                                "exceeded": ppm.is_exceeded(p["id"])})
        apparatus = []
        registry = getattr(self.core, "apparatus_registry", None)
        if registry is not None:
            for apparatus_id in registry.list_ids():
                a = registry.get(apparatus_id)
                if a is None or a.behavior != "SWITCHED" or not a.command or not a.feedback:
                    continue
                apparatus.append({"id": a.id, "kind": getattr(a, "kind", ""), "feedback": list(a.feedback),
                                  "command": list(a.command), "command_style": a.command_style})
        return {"process": process, "apparatus": apparatus}

    # --- starting ------------------------------------------------------------------------

    def _new_report(self, kind, subject, name, actor):
        return {"id": uuid.uuid4().hex[:12], "kind": kind, "subject": subject, "name": name, "actor": actor,
                "started_at": _now_iso(), "finished_at": None, "result": "RUNNING", "reason": "",
                "configured": {}, "measured": {}, "steps": []}

    def _blocked(self, report, reason):
        report["result"] = "BLOCKED"
        report["reason"] = reason
        report["finished_at"] = _now_iso()
        self._finish(report)
        return report

    def _finish(self, report):
        with self._lock:
            if self._running is not None and self._running["id"] == report["id"]:
                self._running = None
            self.reports.append(report)
            self._save()
        audit = getattr(self.core, "audit_logger", None)
        if audit is not None:
            audit.record(f"PROTECTION_TEST_{report['result']}", report["actor"],
                         f"{report['kind']} {report['subject']}: {report['reason'] or report['measured']}",
                         success=report["result"] == "PASS")
        bus = getattr(self.core, "event_bus", None)
        if bus is not None:
            bus.emit("protection_test_finished", report["id"], report["result"])

    def _begin(self, report, target):
        with self._lock:
            if self._running is not None:
                return self._blocked(report, f"another test is running ({self._running['id']})")
            self._running = report
        audit = getattr(self.core, "audit_logger", None)
        if audit is not None:
            audit.record("PROTECTION_TEST_STARTED", report["actor"], f"{report['kind']} {report['subject']}")
        self._thread = threading.Thread(target=self._guarded, args=(target, report), name="ProtectionTest", daemon=True)
        self._thread.start()
        return dict(report)

    def _guarded(self, target, report):
        try:
            target(report)
        except Exception as e:  # noqa: BLE001 - a test must always end in a report
            log.error(f"Protection test {report['id']} failed: {e}")
            report["result"] = "FAIL"
            report["reason"] = f"error: {e}"
        report["finished_at"] = _now_iso()
        self._finish(report)

    def wait(self, timeout: float = 30.0) -> bool:
        thread = self._thread
        if thread is None:
            return True
        thread.join(timeout)
        return not thread.is_alive()

    # --- a process protection --------------------------------------------------------------

    def start_process_test(self, protection_id: str, actor: str = "Engineer"):
        ppm = getattr(self.core, "process_protection_manager", None)
        protection = ppm.get_protection(protection_id) if ppm is not None else None
        report = self._new_report("process", protection_id, (protection or {}).get("name", protection_id), actor)
        if protection is None:
            return self._blocked(report, f"no process protection {protection_id}")
        if not protection.get("enabled", True):
            return self._blocked(report, "the protection is disabled")
        if ppm.is_exceeded(protection_id):
            return self._blocked(report, "the protection is already exceeded - clear it first")
        force = getattr(self.core, "force_manager", None)
        if force is None:
            return self._blocked(report, "forcing is not available on this controller")
        reason = force.protected_reason(protection["analog_tag"])
        if reason:
            return self._blocked(report, reason)
        if self.core.tag_manager.get_tag(protection["analog_tag"]) is None:
            return self._blocked(report, f"unknown tag {protection['analog_tag']}")
        report["configured"] = {"analog_tag": protection["analog_tag"], "upper_threshold": protection["upper_threshold"],
                                "lower_threshold": protection["lower_threshold"], "hysteresis": protection["hysteresis"],
                                "delay_seconds": protection["delay_seconds"],
                                "exceeded_tag": f"Process.{protection_id}.Exceeded"}
        return self._begin(report, lambda r: self._run_process_test(r, protection))

    def _run_process_test(self, report, protection):
        tags = self.core.tag_manager
        force = self.core.force_manager
        ppm = self.core.process_protection_manager
        tag = protection["analog_tag"]
        pid = report["subject"]
        delay = float(protection["delay_seconds"] or 0.0)
        upper, lower, hyst = float(protection["upper_threshold"]), float(protection["lower_threshold"]), float(protection["hysteresis"] or 0)
        beyond = upper + max(hyst, 1.0) + abs(upper) * 0.05
        inside = (upper + lower) / 2.0
        steps = report["steps"]

        original = tags.get_value(tag)
        steps.append(f"{_now_iso()} force {tag} = {beyond} (above {upper})")
        ok, reason = force.force(tag, beyond, actor=report["actor"])
        if not ok:
            report["result"] = "BLOCKED"
            report["reason"] = reason
            return
        t0 = time.monotonic()
        tripped_at = None
        while time.monotonic() - t0 < delay + TRIP_GRACE_S:
            if ppm.is_exceeded(pid):
                tripped_at = time.monotonic()
                break
            time.sleep(0.02)
        trip_s = (tripped_at - t0) if tripped_at is not None else None
        steps.append(f"{_now_iso()} exceeded after {trip_s:.3f} s" if trip_s is not None else f"{_now_iso()} NO trip within {delay + TRIP_GRACE_S:.1f} s")

        steps.append(f"{_now_iso()} force {tag} = {inside} (back in band)")
        force.force(tag, inside, actor=report["actor"])
        t1 = time.monotonic()
        reset_s = None
        if trip_s is not None:
            while time.monotonic() - t1 < RESET_TIMEOUT_S:
                if not ppm.is_exceeded(pid):
                    reset_s = time.monotonic() - t1
                    break
                time.sleep(0.02)
            steps.append(f"{_now_iso()} cleared after {reset_s:.3f} s" if reset_s is not None else f"{_now_iso()} latch did NOT clear")
        force.release(tag, actor=report["actor"], reason="protection test finished")
        steps.append(f"{_now_iso()} force released (was {original!r})")

        tolerance = max(0.5, 0.25 * delay)
        report["measured"] = {"forced_value": beyond, "trip_seconds": trip_s, "reset_seconds": reset_s,
                              "tolerance_seconds": tolerance}
        if trip_s is None:
            report["result"], report["reason"] = "FAIL", "the protection did not trip"
        elif trip_s < delay - 0.05:
            report["result"], report["reason"] = "FAIL", f"tripped after {trip_s:.2f} s, before the configured delay {delay:.2f} s"
        elif trip_s > delay + tolerance:
            report["result"], report["reason"] = "FAIL", f"tripped after {trip_s:.2f} s, later than {delay:.2f} s + {tolerance:.2f} s"
        elif reset_s is None:
            report["result"], report["reason"] = "FAIL", "the latch did not clear once the value was back in band"
        else:
            report["result"], report["reason"] = "PASS", f"trip {trip_s:.2f} s (delay {delay:.2f} s), reset {reset_s:.2f} s"

    # --- an apparatus ---------------------------------------------------------------------

    def start_apparatus_test(self, device_id: str, actor: str = "Engineer"):
        registry = getattr(self.core, "apparatus_registry", None)
        apparatus = registry.get(device_id) if registry is not None else None
        report = self._new_report("apparatus", device_id, device_id, actor)
        if apparatus is None:
            return self._blocked(report, f"no apparatus {device_id}")
        if apparatus.behavior != "SWITCHED" or not apparatus.command or not apparatus.feedback:
            return self._blocked(report, "the apparatus has no command output and feedback point to test")
        commands = getattr(self.core, "command_manager", None)
        if commands is None or f"{device_id}.OPEN" not in commands._definitions and f"{device_id}.CLOSE" not in commands._definitions:
            return self._blocked(report, "the apparatus is not commandable on this controller")
        feedback_tag = apparatus.feedback[0]
        closed = bool(self.core.tag_manager.get_value(feedback_tag))
        first = "OPEN" if closed else "CLOSE"
        if f"{device_id}.{first}" not in commands._definitions:
            return self._blocked(report, f"the apparatus has no {first} command")
        report["configured"] = {"feedback_tag": feedback_tag, "initially_closed": closed, "first_command": first,
                                "restore_command": "CLOSE" if first == "OPEN" else "OPEN",
                                "feedback_timeout_s": FEEDBACK_TIMEOUT_S}
        return self._begin(report, lambda r: self._run_apparatus_test(r, apparatus, feedback_tag, first))

    def _run_apparatus_test(self, report, apparatus, feedback_tag, first):
        tags = self.core.tag_manager
        commands = self.core.command_manager
        steps = report["steps"]
        device_id = apparatus.id

        def issue(action):
            record = commands.request_command_ex(device_id, action, user=report["actor"], source="TEST")
            steps.append(f"{_now_iso()} {device_id}.{action} -> {record.state}" + (f" ({record.reason})" if record.reason else ""))
            return record

        def wait_feedback(expected: bool):
            t0 = time.monotonic()
            while time.monotonic() - t0 < FEEDBACK_TIMEOUT_S:
                if bool(tags.get_value(feedback_tag)) == expected:
                    return time.monotonic() - t0
                time.sleep(0.02)
            return None

        record = issue(first)
        if record.state in ("BLOCKED", "FAILED"):
            report["result"], report["reason"] = "BLOCKED", f"{first} refused: {record.reason}"
            return
        expected_after_first = first == "CLOSE"
        first_s = wait_feedback(expected_after_first)
        steps.append(f"{_now_iso()} feedback {'followed' if first_s is not None else 'MISSING'}"
                     + (f" after {first_s:.3f} s" if first_s is not None else ""))
        restore = "CLOSE" if first == "OPEN" else "OPEN"
        restore_s = None
        if f"{device_id}.{restore}" in commands._definitions:
            record = issue(restore)
            if record.state not in ("BLOCKED", "FAILED"):
                restore_s = wait_feedback(not expected_after_first)
                steps.append(f"{_now_iso()} restored{f' after {restore_s:.3f} s' if restore_s is not None else ': feedback MISSING'}")
        report["measured"] = {"first_command": first, "first_seconds": first_s, "restore_seconds": restore_s}
        if first_s is None:
            report["result"], report["reason"] = "FAIL", f"no feedback within {FEEDBACK_TIMEOUT_S:.0f} s after {first}"
        elif restore_s is None and f"{device_id}.{restore}" in commands._definitions:
            report["result"], report["reason"] = "FAIL", f"{first} took {first_s:.2f} s but the apparatus did not come back"
        else:
            report["result"], report["reason"] = "PASS", f"{first} {first_s:.2f} s" + (f", {restore} {restore_s:.2f} s" if restore_s is not None else "")
