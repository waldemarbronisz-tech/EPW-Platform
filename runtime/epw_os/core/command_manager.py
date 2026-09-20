from typing import Tuple, List, Optional, Dict
import uuid
import time
from epw_os.core.command_model import CommandDefinition, CommandRecord
from epw_os.core.tag_manager import TagType
from epw_os.core.logging import log

class CommandState:
    REQUESTED = "REQUESTED"
    VALIDATED = "VALIDATED"
    DISPATCHED = "DISPATCHED"
    FEEDBACK_PENDING = "FEEDBACK_PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    BLOCKED = "BLOCKED"

class CommandManager:
    def __init__(self, tag_manager, logic_engine, safety_kernel, event_bus, driver_manager=None, project_manager=None):
        self.tag_manager = tag_manager
        self.logic_engine = logic_engine
        self.safety_kernel = safety_kernel
        self.event_bus = event_bus
        self.driver_manager = driver_manager
        self.project_manager = project_manager
        self.force_manager = None       # set by EPWCore; a forced output refuses commands (force_manager.py)
        self._pending_commands: Dict[str, CommandRecord] = {}
        self._timeout_handles = {}

        self.event_bus.subscribe("tag_changed", self._on_tag_changed)

        # In a real engine, command mapping comes from project_manager
        self._definitions: Dict[str, CommandDefinition] = {}

        # Bug fix (Task: "warunki bezpieczenstwa przed testem zabezpieczenia
        # faktycznie dzialaja" - protection_verifier.py's own
        # check_safety_conditions() pre-flight gate reads this tag, but
        # nothing ever wrote to it). Registered HERE, in __init__ -
        # CommandManager is always constructed unconditionally in
        # EPWCore.__init__(), unlike ProtectionVerifier (only built when
        # the Engineer Mode PAGE is actually opened) - so this tag exists
        # and is kept correct from the very first command dispatch
        # onward, regardless of whether that page was ever opened (same
        # "register where the WRITER lives, unconditionally" lesson as
        # the System.Mode/Device.<id>.Status fixes in earlier sessions).
        # add_tag() is idempotent (a no-op if already registered), so
        # this coexists safely with protection_verifier.py's own
        # (now-redundant, but harmless) registration of the same tag.
        self.tag_manager.add_tag(
            "System.PendingCommand", False, TagType.BOOL,
            description="True while ANY command is between dispatch and resolution (feedback received, "
                        "denied, or timed out) - see CommandManager._sync_pending_command_tag().",
            source="SYSTEM",
        )

    def _sync_pending_command_tag(self):
        """System.PendingCommand - True while ANY command is pending,
        False the instant none are. Derived fresh from
        self._pending_commands (this class's own, already-authoritative
        "which commands are still waiting on feedback/timeout" registry)
        every time that dict changes, rather than toggled independently
        at each call site - so it can never drift out of sync with it,
        and correctly reflects any number of concurrent commands without
        extra bookkeeping (a second command still pending after a first
        one resolves simply leaves the dict non-empty). See
        SESSION_REPORT.md for why a boolean "is ANYTHING pending" flag -
        matching this tag's own BOOL type and singular name - was chosen
        over a separate counter tag."""
        self.tag_manager.update_tag("System.PendingCommand", bool(self._pending_commands))

    def clear_definitions(self):
        """Forgets every command definition, so a reloaded project's
        apparatuses can be loaded in place of the old ones rather than
        on top of them (EPWCore.reload_project()) - load_definitions()
        merges by key, which is right at startup and wrong here: an
        apparatus deleted in Studio would otherwise stay operable."""
        self._definitions.clear()

    def load_definitions(self, definitions_dict: dict):
        # Task "migracja adresacji": `target`/`action` are informational
        # (event_bus.emit("command_executed", definition.target,
        # definition.action, ...) below is the one real reader) - lookup
        # itself always goes by the verbatim key (`command_id`), never by
        # reassembling these two fields, so this split only ever needed
        # to get the SPLIT POINT right, not the segment count. The old
        # `split(".")[0] + "." + split(".")[1]` assumed the key had
        # EXACTLY 3 dot-separated segments (device.tag.ACTION) - already
        # silently wrong for a 2-segment key (`"DO05.CLOSE"` -> target
        # "DO05.CLOSE" instead of "DO05", swallowing the action into the
        # emitted target), and wrong again, differently, once a real tag
        # itself contains two dots (`"ADA1.DO.1.CLOSE"` -> target
        # "ADA1.DO" instead of "ADA1.DO.1", losing the channel number).
        # rsplit(".", 1) is correct for any number of segments - action
        # is always everything after the LAST dot, target everything
        # before it.
        for k, v in definitions_dict.items():
            self._definitions[k] = CommandDefinition(
                command_id=k,
                target=k.rsplit(".", 1)[0] if "." in k else k,
                action=k.rsplit(".", 1)[1] if "." in k else "EXECUTE",
                driver_id=v.get("driver_id", "SIM_DRIVER"),
                output_tag=v["output_tag"],
                output_value=v["output_value"],
                pulse_ms=v.get("pulse_ms"),
                feedback_tag=v.get("feedback_tag"),
                feedback_value=v.get("feedback_value"),
                timeout_ms=v.get("timeout_ms", 1500),
                skip_when_feedback_matches=bool(v.get("skip_when_feedback_matches", False)),
                also_reset_tag=v.get("also_reset_tag"),
            )

    def _feedback_already_satisfied(self, definition) -> bool:
        """Task "wyłącznik jednocewkowy bistabilny": a single-coil impulse
        relay toggles on EVERY pulse, so a CLOSE on an already-closed
        apparatus must not pulse at all. Only consulted when the
        definition asks for it (skip_when_feedback_matches); a missing or
        non-GOOD feedback tag never counts as "already there" - the pulse
        is then sent and the normal feedback/timeout path judges it."""
        if not definition.skip_when_feedback_matches or not definition.feedback_tag:
            return False
        tag = self.tag_manager.get_tag(definition.feedback_tag)
        if tag is None or getattr(tag, "quality", None) not in (None, "GOOD", getattr(tag, "quality", None)):
            return False
        quality = getattr(tag, "quality", "GOOD")
        if str(getattr(quality, "value", quality)) != "GOOD":
            return False
        return tag.value == definition.feedback_value

    def _release_pulse(self, definition):
        """The second half of a PULSE-style output: `pulse_ms` after the
        coil was energized, de-energize it again through the very same
        driver boundary (route_command - Training Mode's cut applies to
        the release exactly as it did to the pulse). Before this, pulse_ms
        was carried in the definition but never acted on - every "pulsed"
        output stayed energized forever."""
        if self.driver_manager is not None:
            self.driver_manager.route_command(definition.driver_id, definition.output_tag, False)

    def _on_tag_changed(self, tag_name, value, quality):
        if quality != "GOOD":
            return
            
        for command_id, record in list(self._pending_commands.items()):
            definition = record.definition
            if definition.feedback_tag != tag_name:
                continue
            if value != definition.feedback_value:
                continue
                
            record.state = CommandState.SUCCESS
            record.completed_at = time.time()
            record.reason = ""
            
            # self._cancel_timeout(command_id) # Using simple thread timers for now, ignore cancel
            del self._pending_commands[command_id]
            self._sync_pending_command_tag()

            self.event_bus.emit("command_status", command_id, CommandState.SUCCESS, "Expected feedback received")
            self.event_bus.emit("command_executed", definition.target, definition.action, record.user)

    def _on_timeout(self, command_id):
        record = self._pending_commands.pop(command_id, None)
        if record is None:
            return
        # Bug fix (Task: System.PendingCommand): a lost/missing feedback
        # must never leave this tag stuck True forever - the timeout path
        # is exactly what guarantees that, same as every other removal
        # from _pending_commands.
        self._sync_pending_command_tag()

        record.state = CommandState.TIMEOUT
        record.completed_at = time.time()
        record.reason = "Expected feedback not received"
        self.event_bus.emit("command_status", command_id, CommandState.TIMEOUT, record.reason)

    def set_driver_manager(self, driver_manager):
        self.driver_manager = driver_manager
        
    def request_command(self, device_tag: str, command: str, user: str = "Operator", validate_only: bool = False) -> Tuple[bool, List[str]]:
        return self._legacy_request_command(device_tag, command, user, validate_only)
        
    def request_command_ex(self, target: str, action: str, user="Operator", source="GUI") -> CommandRecord:
        cmd_id = str(uuid.uuid4())
        key = f"{target}.{action}"
        
        # 1. Definition check
        definition = self._definitions.get(key)
        if not definition:
            record = CommandRecord(cmd_id, None, CommandState.BLOCKED, time.time(), user=user, source=source, reason="Unknown command definition")
            self.event_bus.emit("command_status", cmd_id, CommandState.BLOCKED, "Unknown command definition")
            return record
            
        record = CommandRecord(cmd_id, definition, CommandState.REQUESTED, time.time(), user=user, source=source)
        self.event_bus.emit("command_status", cmd_id, CommandState.REQUESTED, "Command requested")
        
        # 2. Safety Kernel
        safe, kernel_reason = self.safety_kernel.validate_command_safety(target, action)
        if not safe:
            record.state = CommandState.BLOCKED
            record.reason = f"Platform Safety: {kernel_reason}"
            self.event_bus.emit("command_status", cmd_id, CommandState.BLOCKED, record.reason)
            return record
            
        # 2b. A forced output belongs to the person forcing it, not to logic
        # or an operator (SPEC "Wymuszanie stanów"): refused, audibly.
        if self.force_manager is not None:
            forced_def = self._definitions.get(f"{target}.{action}")
            forced_tag = getattr(forced_def, "output_tag", None) if forced_def is not None else None
            if forced_tag and self.force_manager.is_forced(forced_tag):
                record.state = CommandState.BLOCKED
                record.reason = f"Output {forced_tag} is forced from Studio - release the force first"
                self.event_bus.emit("command_status", cmd_id, CommandState.BLOCKED, record.reason)
                return record

        # 3. Logic Runtime Interlock
        permitted, reasons = self.logic_engine.validate_command(target, action)
        if not permitted:
            record.state = CommandState.BLOCKED
            record.reason = ", ".join(reasons)
            self.event_bus.emit("command_status", cmd_id, CommandState.BLOCKED, record.reason)
            return record
            
        record.state = CommandState.VALIDATED
        self.event_bus.emit("command_status", cmd_id, CommandState.VALIDATED, "Command validated")

        # Task "wyłącznik jednocewkowy bistabilny": after every safety/
        # logic check above (a blocked command stays blocked), before
        # anything reaches a driver - an impulse relay already in the
        # requested state must NOT be pulsed, see _feedback_already_
        # satisfied(). Resolved as SUCCESS: the requested state IS the
        # actual state, which is all a command ever promises.
        if self._feedback_already_satisfied(definition):
            record.state = CommandState.SUCCESS
            record.completed_at = time.time()
            record.reason = "Already in requested state - impulse relay not pulsed"
            self.event_bus.emit("command_status", cmd_id, CommandState.SUCCESS, record.reason)
            self.event_bus.emit("command_executed", target, action, user)
            return record

        # 4. Dispatch
        if self.driver_manager:
            # Task: presentation-mode scenarios "normal operation, manual
            # control" / "command never confirmed" (discovered while
            # building them, not specific to either one) - register this
            # command as pending, and its feedback_tag on record, BEFORE
            # calling route_command(), not after. Under Training Mode's
            # cutoff (driver_manager.py) - the only way a command's
            # driver call ever runs while Presentation Mode is active,
            # but also reachable any time Training Mode is simply
            # switched on - a self-referential definition's output_tag ==
            # feedback_tag is written SYNCHRONOUSLY, inside
            # route_command() itself, via the driver_update ->
            # driver_to_tag -> TagManager.update_tag() bridge. That fires
            # tag_changed, which _on_tag_changed() below needs to already
            # know this cmd_id to resolve it to SUCCESS. With the
            # registration happening only after route_command() returned
            # (the original ordering), that synchronous, same-call-stack
            # feedback was invisibly missed every single time, and the
            # command sat at FEEDBACK_PENDING until an unnecessary
            # timeout fired instead - regardless of the real value having
            # already matched immediately.
            pending_armed = False
            if definition.feedback_tag:
                record.state = CommandState.FEEDBACK_PENDING
                self._pending_commands[cmd_id] = record
                pending_armed = True
                self._sync_pending_command_tag()

            if definition.also_reset_tag:
                # Two maintained coils: release the opposite one first,
                # so both are never energized at once.
                self.driver_manager.route_command(definition.driver_id, definition.also_reset_tag, False)
            success = self.driver_manager.route_command(definition.driver_id, definition.output_tag, definition.output_value)
            if success and definition.pulse_ms:
                # A PULSE-style output: energize now, release after
                # pulse_ms - see _release_pulse().
                import threading
                release = threading.Timer(definition.pulse_ms / 1000.0, lambda: self._release_pulse(definition))
                release.daemon = True
                release.start()

            if success:
                record.dispatched_at = time.time()
                if pending_armed and record.state == CommandState.SUCCESS:
                    pass  # _on_tag_changed() already resolved it, synchronously, above - nothing left to do
                else:
                    record.state = CommandState.DISPATCHED
                    self.event_bus.emit("command_status", cmd_id, CommandState.DISPATCHED, "Command sent to driver")
                    if definition.feedback_tag:
                        record.state = CommandState.FEEDBACK_PENDING
                        self.event_bus.emit("command_status", cmd_id, CommandState.FEEDBACK_PENDING, "Waiting for feedback")

                        import threading
                        timer = threading.Timer(definition.timeout_ms / 1000.0, lambda: self._on_timeout(cmd_id))
                        timer.daemon = True
                        timer.start()
                        self._timeout_handles[cmd_id] = timer
                    else:
                        record.state = CommandState.SUCCESS
                        record.completed_at = time.time()
                        self.event_bus.emit("command_status", cmd_id, CommandState.SUCCESS, "Command dispatched with no feedback required")
                        self.event_bus.emit("command_executed", target, action, user)
            else:
                if pending_armed:
                    self._pending_commands.pop(cmd_id, None)
                    self._sync_pending_command_tag()
                record.state = CommandState.FAILED
                record.reason = "Driver routing failed"
                self.event_bus.emit("command_status", cmd_id, CommandState.FAILED, "Driver routing failed")
        else:
            record.state = CommandState.FAILED
            record.reason = "Driver manager missing"
            self.event_bus.emit("command_status", cmd_id, CommandState.FAILED, "Driver manager missing")
            
        return record

    def _legacy_request_command(self, device_tag: str, command: str, user: str = "Operator", validate_only: bool = False) -> Tuple[bool, List[str]]:
        # Map to EX mapping if we have it, else fallback for GUI
        key = f"{device_tag}.{command}"
        if key in self._definitions:
            if validate_only:
                safe, kr = self.safety_kernel.validate_command_safety(device_tag, command)
                if not safe: return False, [kr]
                return self.logic_engine.validate_command(device_tag, command)
            rec = self.request_command_ex(device_tag, command, user=user)
            if rec.state in [CommandState.BLOCKED, CommandState.FAILED]:
                return False, [rec.reason]
            return True, []
            
        cmd_id = str(uuid.uuid4())
        safe, kernel_reason = self.safety_kernel.validate_command_safety(device_tag, command)
        if not safe:
            self.event_bus.emit("command_status", cmd_id, CommandState.BLOCKED, f"Safety Kernel: {kernel_reason}")
            return False, [f"Platform Safety: {kernel_reason}"]

        permitted, reasons = self.logic_engine.validate_command(device_tag, command)
        if permitted:
            if validate_only: return True, []
            self.event_bus.emit("command_status", cmd_id, CommandState.DISPATCHED, "Command dispatched")
            self.event_bus.emit("command_executed", device_tag, command, user)
            return True, []
        else:
            self.event_bus.emit("command_status", cmd_id, CommandState.BLOCKED, ", ".join(reasons))
            return False, reasons
