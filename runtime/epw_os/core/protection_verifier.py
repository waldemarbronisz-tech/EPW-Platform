import json
import os
import time
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, Any
from PySide6.QtCore import QObject, QTimer, Signal
from epw_os.core.access_manager import AccessLevel
from epw_os.core.logging import log
from epw_os.core.tag_manager import TagType

# Absolute, anchored to the repo root - see project_manager.DEFAULT_PROJECT_FILE
# for why a relative path here is a real bug, not just a style nit.
REPORTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "protection_reports.json")

@dataclass
class VerificationReport:
    date: str
    time: str
    protection: str
    operator: str
    sw_version: str
    fw_version: str
    conf_pickup: str
    meas_pickup: str
    conf_delay: str
    meas_delay: str
    output: str
    feedback: str
    result: str

class ProtectionVerifier(QObject):
    log_msg = Signal(str)
    test_finished = Signal(object)

    def __init__(self, tag_manager, protection_manager, access_manager, audit_logger=None):
        super().__init__()
        self.tag_manager = tag_manager
        self.protection_manager = protection_manager
        self.access_manager = access_manager
        # Task (System.PendingCommand/System.ActiveTrip requirement #4:
        # "odmowa zapisywana do dziennika audytowego") - optional, same
        # tolerance every other core module's audit_logger parameter
        # already has (None in isolated widget tests). Threaded through
        # from PageEngineerMode -> MainWindow.audit_logger, the same
        # AuditLogger every other Engineer-gated action in this program
        # already writes to.
        self.audit_logger = audit_logger
        self.reports = []
        self.load_reports()

        # Bug fix, part 1 - registration (Task: "ten sam wzorzec w
        # protection_verifier.py", a previous session's tag-registry
        # audit): the two pre-flight checks in check_safety_conditions()
        # below read these tags, but neither was ever registered
        # anywhere in this codebase - get_value() on an unregistered tag
        # returns None, and None == True is False, so both conditions
        # were permanently, silently inert (the exact "polykane bez
        # sladu" shape the System.Mode bug had). Registered here - this
        # class's own constructor, the same "the module that reads a tag
        # registers it" pattern IntrusionManager/SafetyKernel already
        # use - default False, the safe "nothing pending, nothing
        # tripped" resting state, so an already-passing verification
        # pre-flight stays unaffected (confirmed by test) until this
        # SESSION's own fix (part 2 below) makes them start reflecting
        # something real. add_tag() is idempotent - safe even though
        # CommandManager (this session's own fix, part 1 for
        # System.PendingCommand specifically) may have already
        # registered the first one.
        self.tag_manager.add_tag(
            "System.PendingCommand", False, TagType.BOOL,
            description="True while ANY command is between dispatch and resolution (feedback received, "
                        "denied, or timed out) - blocks starting a protection verification test in "
                        "Engineer Mode. Written by CommandManager - see its own "
                        "_sync_pending_command_tag().",
            source="SYSTEM",
        )
        self.tag_manager.add_tag(
            "System.ActiveTrip", False, TagType.BOOL,
            description="True while any PROCESS protection currently reads Exceeded (Process.<id>.Exceeded) "
                        "- blocks starting a protection verification test in Engineer Mode. Momentary, not "
                        "a latch - clears the instant no process protection is exceeded anymore, mirroring "
                        "Process.<id>.Exceeded's own polarity. Electrical protections are NOT included: "
                        "they have no live trip evaluation anywhere in this codebase to observe (see "
                        "SESSION_REPORT.md). Written by this class's own _on_process_tag_changed().",
            source="SYSTEM",
        )

        # Bug fix, part 2 - System.ActiveTrip's actual write side (Task:
        # "podlacz zapis do rzeczywistego zadzialania zabezpieczenia").
        # A plain, read-only pattern match against tag_changed - the same
        # established, zero-coupling technique mqtt_manager.py's own
        # _maybe_emit_intrusion_event() already uses to observe
        # Security.Zone.<id>.State without importing or modifying
        # intrusion_manager.py - process_protection_manager.py is never
        # imported or touched here either. Self-contained: unlike
        # System.PendingCommand (whose only consumer, this precondition
        # check, could be reached from other code too, so it's written
        # by the always-constructed CommandManager instead),
        # System.ActiveTrip has no consumer beyond THIS object's own
        # check_safety_conditions() below, so keeping its write side
        # entirely inside this same class - constructed and subscribed
        # in the same breath - cannot leave a "stale until some page
        # happens to be open" gap the way Device.<id>.Status once did.
        self._exceeded_process_protections = set()
        for tag in self.tag_manager.list_tags():
            if self._is_process_exceeded_tag(tag.name) and tag.value:
                self._exceeded_process_protections.add(tag.name)
        if self._exceeded_process_protections:
            self.tag_manager.update_tag("System.ActiveTrip", True)
        self.tag_manager.tag_changed.connect(self._on_process_tag_changed)

        self.timer = QTimer()
        self.timer.timeout.connect(self.test_tick)
        
        self.state = "IDLE"
        self.test_ctx = {}
        
    def load_reports(self):
        try:
            if os.path.exists(REPORTS_FILE):
                with open(REPORTS_FILE, "r") as f:
                    data = json.load(f)
                    self.reports = [VerificationReport(**d) for d in data]
        except Exception as e:
            # A corrupt/incompatible REPORTS_FILE silently discarding
            # every previously saved verification report is real data
            # loss with zero other trace - same "polykane wyjatki"
            # pattern as System.Mode. Kept fail-safe (empty list, program
            # keeps starting) - now also logged.
            log.warning(f"Could not load {REPORTS_FILE} - starting with no verification history: {e}")
            self.reports = []

    def save_reports(self):
        with open(REPORTS_FILE, "w") as f:
            json.dump([asdict(r) for r in self.reports], f, indent=4)
            
    def _di_label(self, tag_name: str) -> str:
        """Human-readable label for a DI tag in verification messages -
        the operator-editable tag description if one is set (same
        description DigitalInputs' page shows/lets you rename), falling
        back to the bare tag name. No project-specific device name
        hardcoded here - see SESSION_REPORT.md. The safety-relevant part
        (which DI tag gets checked, and against what value) is unchanged
        - only the label shown to the operator is generic now."""
        tag = self.tag_manager.get_tag(tag_name)
        if tag is not None and getattr(tag, "description", None):
            return tag.description
        return tag_name

    @staticmethod
    def _is_process_exceeded_tag(tag_name: str) -> bool:
        """Matches exactly the shape process_protection_manager.py's own
        _exceeded_tag() produces (f"{TAG_PREFIX}.{protection_id}.Exceeded",
        TAG_PREFIX == "Process") - precise enough that nothing else in
        this codebase's tag namespace can collide with it."""
        return tag_name.startswith("Process.") and tag_name.endswith(".Exceeded")

    def _on_process_tag_changed(self, tag_name, value, quality):
        if not self._is_process_exceeded_tag(tag_name):
            return
        if value:
            self._exceeded_process_protections.add(tag_name)
        else:
            self._exceeded_process_protections.discard(tag_name)
        # bool(...) - "any currently exceeded", not a count - matches
        # System.ActiveTrip's own BOOL type/singular name, the same
        # "flag, not a counter" choice made for System.PendingCommand
        # (see command_manager.py's own _sync_pending_command_tag()).
        self.tag_manager.update_tag("System.ActiveTrip", bool(self._exceeded_process_protections))

    def _record_precondition_denial(self, tag_name: str, reason: str):
        """Task requirement #4 ("odmowa zapisywana do dziennika
        audytowego") - scoped to exactly the two preconditions this task
        touches (System.PendingCommand/System.ActiveTrip), not every
        existing check_safety_conditions() gate (GRANICE: "zmieniasz
        WYLACZNIE zapis tych dwoch tagow i to, co z nich wynika" - the
        other five pre-existing gates already worked before this task
        and are out of its scope). `reason` is the same multi-line
        string already shown to the operator in the terminal - collapsed
        to one line for the audit record, which (unlike the terminal)
        has no line-wrapping of its own."""
        if self.audit_logger is not None:
            actor = getattr(self.access_manager, "level", "")
            detail = f"{tag_name}: " + reason.replace("\n", " ")
            self.audit_logger.record("PROTECTION_VERIFICATION_BLOCKED", actor, detail, success=False)

    def check_safety_conditions(self) -> (bool, str):
        if not self.access_manager.has_access(AccessLevel.ENGINEER):
            return False, "Engineer access is NOT ACTIVE.\nVerification requires Engineer access."

        val_l1 = self.tag_manager.get_value("Meas.L1")
        if val_l1 is None or val_l1 < 10:
            return False, "Incoming voltage not detected.\nProtection verification requires\nenergized busbars."

        if self.tag_manager.get_value("DI2") != 1:
            return False, f"{self._di_label('DI2')} is OPEN.\nVerification requires this feeder active."

        if self.tag_manager.get_value("DI3") == 1:
            return False, f"{self._di_label('DI3')} is CLOSED.\nProtection testing could disconnect\nthis feeder.\nOpen it before starting the test."

        if self.tag_manager.get_value("DI4") == 1:
            return False, f"{self._di_label('DI4')} is CLOSED.\nOpen it before protection testing."
            
        if self.tag_manager.get_value("System.PendingCommand") == True:
            reason = "Pending switching command detected.\nWait until switching operation\nhas finished."
            self._record_precondition_denial("System.PendingCommand", reason)
            return False, reason

        if self.tag_manager.get_value("System.ActiveTrip") == True:
            reason = "Active TRIP detected.\nClear all trips before starting test."
            self._record_precondition_denial("System.ActiveTrip", reason)
            return False, reason

        # Device.Modbus.Status starts OFFLINE and flips to ONLINE once the
        # simulated driver reports its first live comm heartbeat.
        if self.tag_manager.get_value("Device.Modbus.Status") != "ONLINE":
            return False, "Communication failure.\nModbus is offline."
            
        return True, "PASS"
        
    def start_verification(self, prot_name):
        # Format "27 Under Voltage - Stage 1"
        parts = prot_name.split(" - ")
        if len(parts) != 2:
            self.log_msg.emit("TEST BLOCKED\nReason:\nInvalid protection format.")
            return

        pid = parts[0]
        stage_name = parts[1]
        
        prot = self.protection_manager.protections.get(pid)
        if not prot:
            self.log_msg.emit("TEST BLOCKED\nReason:\nProtection not found.")
            return
            
        stage = next((s for s in prot.stages if s.name == stage_name), None)
        if not stage:
            self.log_msg.emit("TEST BLOCKED\nReason:\nStage not found.")
            return

        # Safety conditions already checked by UI before operator confirmation
        if not stage.enabled:
            self.log_msg.emit("TEST BLOCKED\nReason:\nProtection stage is disabled.")
            return

        self.log_msg.emit("■ Running Test")

        # Context setup
        self.test_ctx = {
            "prot_name": prot_name,
            "pid": pid,
            "stage": stage,
            "prot": prot,
            "start_val": 0,
            "current_val": 0,
            "step": 0,
            "target_tag": "",
            "ramp_direction": 1, # 1 for up, -1 for down
            "unit": prot.unit,
            
            "pickup_val": None,
            "pickup_time": 0,
            "trip_time": 0,
            
            "initial_state": self.tag_manager.get_value("DI2") if self.tag_manager.get_value("DI2") is not None else 0
        }

        # Map protection to tag and ramp logic
        if "Under Voltage" in pid:
            self.test_ctx["target_tag"] = "Meas.L1"
            self.test_ctx["start_val"] = 230.0
            self.test_ctx["current_val"] = 230.0
            self.test_ctx["step"] = -1.0
            self.test_ctx["ramp_direction"] = -1
        elif "Over Voltage" in pid:
            self.test_ctx["target_tag"] = "Meas.L1"
            self.test_ctx["start_val"] = 230.0
            self.test_ctx["current_val"] = 230.0
            self.test_ctx["step"] = 1.0
            self.test_ctx["ramp_direction"] = 1
        elif "Frequency" in pid:
            self.test_ctx["target_tag"] = "Meas.Freq"
            self.test_ctx["start_val"] = 50.0
            self.test_ctx["current_val"] = 50.0
            self.test_ctx["step"] = 0.1 if "Over" in pid else -0.1
            self.test_ctx["ramp_direction"] = 1 if "Over" in pid else -1
        elif "Overcurrent" in pid:
            self.test_ctx["target_tag"] = "Meas.I1"
            self.test_ctx["start_val"] = 0.0
            self.test_ctx["current_val"] = 0.0
            self.test_ctx["step"] = 5.0
            self.test_ctx["ramp_direction"] = 1
        else:
            # Generic
            self.test_ctx["target_tag"] = "Sim.TestValue"
            self.test_ctx["start_val"] = 0.0
            self.test_ctx["current_val"] = 0.0
            self.test_ctx["step"] = 1.0
            self.test_ctx["ramp_direction"] = 1

        self.state = "RAMPING"
        self.timer.start(100) # Fast 100ms cycle

    def test_tick(self):
        ctx = self.test_ctx
        
        if self.state == "RAMPING":
            ctx["current_val"] += ctx["step"]
            self.tag_manager.update_tag(ctx["target_tag"], ctx["current_val"])
            
            # Check if threshold crossed
            crossed = False
            if ctx["ramp_direction"] == 1 and ctx["current_val"] >= ctx["stage"].setting: crossed = True
            if ctx["ramp_direction"] == -1 and ctx["current_val"] <= ctx["stage"].setting: crossed = True
            
            if crossed:
                ctx["pickup_val"] = ctx["current_val"]
                ctx["pickup_time"] = time.time()
                self.log_msg.emit(f"■ Waiting For Protection (Pickup at {ctx['pickup_val']:.1f} {ctx['unit']})")
                self.state = "WAITING_TRIP"
                
        elif self.state == "WAITING_TRIP":
            # Wait for DI2 feedback to drop, simulating real external trip output
            current_di = self.tag_manager.get_value("DI2")
            if current_di is None: current_di = 0
            
            elapsed = (time.time() - ctx["pickup_time"]) * 1000 # ms
            
            if current_di == 0 and ctx["initial_state"] == 1:
                ctx["trip_time"] = time.time()
                self.state = "MEASURING"
                self.log_msg.emit("■ Output Feedback Detected")
                
            if elapsed > ctx["stage"].delay_ms + 5000: # 5 sec timeout awaiting external feedback
                ctx["trip_time"] = 0
                self.state = "MEASURING"
                self.log_msg.emit("■ Output Feedback TIMEOUT")
                
        elif self.state == "MEASURING":
            self.log_msg.emit("■ Creating Report")
            self.finish_test()

    def finish_test(self):
        self.timer.stop()
        self.log_msg.emit("POST TEST CHECK\nPASS")
        
        ctx = self.test_ctx
        stage = ctx["stage"]
        
        meas_p = f"{ctx['pickup_val']:.1f} {ctx['unit']}" if ctx['pickup_val'] is not None else "N/A"
        conf_p = f"{stage.setting} {ctx['unit']}"
        
        if ctx["trip_time"] > 0:
            meas_d = f"{(ctx['trip_time'] - ctx['pickup_time']) * 1000:.0f} ms"
            feedback = "Received"
            result = "PASS"
        else:
            meas_d = "TIMEOUT"
            feedback = "Missing"
            result = "FAIL"
            
        conf_d = f"{stage.delay_ms} ms"

        rep = self.create_report(
            ctx["prot_name"],
            conf_p, meas_p,
            conf_d, meas_d,
            self._di_label("DI2"), feedback, result
        )

        # Reset simulation values
        self.tag_manager.update_tag(ctx["target_tag"], ctx["start_val"])
        self.tag_manager.update_tag("DI2", ctx["initial_state"]) # Restore feeder to its prior state
        
        self.test_finished.emit(rep)
        self.state = "IDLE"

    def create_report(self, prot_name, conf_p, meas_p, conf_d, meas_d, out, fdbk, res):
        now = datetime.now()
        report = VerificationReport(
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
            protection=prot_name,
            operator="Engineer",
            sw_version="EPW OS v1.0",
            fw_version="1.0.3",
            conf_pickup=conf_p,
            meas_pickup=meas_p,
            conf_delay=conf_d,
            meas_delay=meas_d,
            output=out,
            feedback=fdbk,
            result=res
        )
        self.reports.append(report)
        self.save_reports()
        return report
