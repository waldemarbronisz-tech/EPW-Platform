"""Commands arriving from outside (Home Assistant over MQTT).

WHY THIS IS ITS OWN MODULE, and not a few lines in mqtt_manager.py: that
module is a TRANSPORT and its own docstring promises it never touches a
control path. It still does not - it hands a raw message to a callback
and knows nothing about what happens next. Everything that decides
whether a command is real, who sent it, and whether they may do it lives
here, in one place that can be read start to finish.

THE LESSON THIS IS BUILT ON. The REST API once called CommandManager
directly, past every permission gate: anyone who could reach the port
could operate the plant with no PIN (see api_auth.py). The fix was not
"add a password" - it was making the SYSTEM decide the caller's rights
rather than believing what the request says about itself. Same rule
here, and two more that MQTT forces on top:

  * MQTT is a noticeboard, not a phone call. The broker does not tell
    the controller who pinned the note, so identity has to travel IN the
    message and be verified here against the controller's own registry.
  * A note STAYS pinned. A retained message is replayed to every client
    that connects - including this controller after a restart. A
    "disarm" published once would otherwise execute again at every power
    cut. Retained messages are refused outright, and that refusal is a
    security event, not a debug line.

WHAT A COMMAND MUST CARRY (JSON):

    {"id": "<unique per command>", "ts": <unix seconds>,
     "user": "<user id>", "token": "<that person's remote token>",
     "action": "intrusion|apparatus|setting", "what": "...",
     "zone"/"target"/"stage": "...", "values": {...}}

The values a SETTING writes live in their own `values` object, never at
the top level: a protection stage has fields called "setting" and
"action", and so does this envelope.

and what happens to it, in order: retained -> refused; malformed ->
refused; `ts` outside the freshness window -> refused; `id` already seen
-> IGNORED (a duplicate delivery is normal at QoS 1, not an attack - the
previous result is republished); unknown user or bad token -> refused
and reported; the person's own level/zones checked exactly as at the
panel -> refused if short; only then executed, through the very same
managers the panel calls.

Every outcome is published back on the result topic, so the automation
that sent the command learns whether it worked and why not - MQTT gives
no answer of its own.

WHAT IS DELIBERATELY NOT HERE: forcing (force_manager). A force is a
service engineer's tool, held alive by a heartbeat from someone standing
at the cabinet; there is no sense in which it can be driven from a phone
(owner's decision, see shared/docs/MQTT_STEROWANIE.md).
"""
import json
import time

from epw_os.core.access_manager import AccessLevel
from epw_os.core.logging import log

# How old a command may be and still be accepted. Long enough for a slow
# broker or a phone on a bad connection, short enough that a message
# captured off the wire is useless a minute later. The sender's clock
# has to be roughly right - Home Assistant's is.
FRESHNESS_WINDOW_S = 120.0

# How many recent command ids to remember for duplicate detection. QoS 1
# means "at least once", so the same command genuinely does arrive twice
# now and then; that must be harmless rather than a second arming.
SEEN_IDS_MAX = 512

# The alarm raised on anything that looks like an attempt to command
# this controller without the right to (owner's instruction: a silent
# alarm and a notification on the phone - EPW-OS has no siren of its
# own, and the alarm is published over MQTT, which is what Home
# Assistant turns into that notification).
SECURITY_ALARM_ID = "REMOTE_COMMAND_REFUSED"


class RemoteCommandGateway:
    """Verifies and executes one command at a time. Constructed by
    EPWCore, which owns everything it calls into."""

    def __init__(self, access_manager=None, intrusion_manager=None, command_manager=None,
                 project_manager=None, process_protection_manager=None, alarm_manager=None,
                 audit_logger=None, publish_result=None, clock=time.time, internal_bits=None):
        # Internal bits IN/OUT: the one door for a write from outside the
        # logic (core/internal_bit_gate.py) - per bit, only where the
        # project allows a remote writer.
        self.internal_bits = internal_bits
        self.access_manager = access_manager
        self.intrusion_manager = intrusion_manager
        self.command_manager = command_manager
        self.project_manager = project_manager
        self.process_protection_manager = process_protection_manager
        self.alarm_manager = alarm_manager
        self.audit_logger = audit_logger
        # Where an answer goes - set by whoever owns the transport.
        self.publish_result = publish_result
        self._clock = clock
        self._seen = {}      # command id -> the result already sent for it
        self._seen_order = []

    # --- the one entry point -------------------------------------------------

    def handle(self, topic: str, payload, retained: bool = False) -> dict:
        """Handles one inbound message. Always returns the result dict it
        also publishes - never raises, whatever arrives on the wire."""
        try:
            result = self._handle(topic, payload, retained)
        except Exception as e:  # noqa: BLE001 - a malformed message must never take the transport down
            log.error(f"Remote command from {topic!r} failed unexpectedly: {e}")
            result = {"accepted": False, "reason": "internal error"}
        self._publish(result)
        return result

    def _handle(self, topic: str, payload, retained: bool) -> dict:
        if retained:
            # The note that stayed pinned to the board. Never executed,
            # always reported: a retained command is either a mistake in
            # the automation that sent it or somebody trying to make this
            # controller replay something at every restart.
            return self._refuse("retained message", None, {"topic": topic}, security=True)

        try:
            body = json.loads(payload.decode("utf-8") if isinstance(payload, (bytes, bytearray)) else payload)
        except Exception:
            return self._refuse("payload is not JSON", None, {"topic": topic}, security=True)
        if not isinstance(body, dict):
            return self._refuse("payload is not an object", None, {"topic": topic}, security=True)

        command_id = str(body.get("id") or "").strip()
        if not command_id:
            return self._refuse("no command id", None, {"topic": topic}, security=True)
        if command_id in self._seen:
            # A duplicate delivery is ordinary MQTT, not an attack: the
            # answer already given is repeated, and nothing runs twice.
            log.info(f"Remote command {command_id} seen again - the previous result is republished.")
            return dict(self._seen[command_id], duplicate=True)

        age = abs(self._clock() - float(body.get("ts") or 0))
        if age > FRESHNESS_WINDOW_S:
            return self._refuse(f"stale command ({age:.0f}s old)", command_id, {"topic": topic}, security=True)

        user = self._resolve_user(body)
        if user is None:
            return self._refuse("unknown user or bad token", command_id, {"topic": topic}, security=True)

        action = str(body.get("action") or "").strip()
        handler = _ACTIONS.get(action)
        if handler is None:
            return self._refuse(f"unknown action {action!r}", command_id, {"user": user["name"]})

        return handler(self, body, user, command_id)

    # --- identity -------------------------------------------------------------

    def _resolve_user(self, body):
        """The person behind this message - their own record from the
        controller's registry, never anything the message claims about
        itself beyond the token it proves. A token that resolves to a
        DIFFERENT user than the message names is refused: saying "I am
        Kowalski" while holding Nowak's token is exactly the confusion
        this check exists to stop."""
        if self.access_manager is None:
            return None
        resolver = getattr(self.access_manager, "resolve_remote_token", None)
        if not callable(resolver):
            return None
        user = resolver(str(body.get("token") or ""))
        if user is None:
            return None
        claimed = str(body.get("user") or "").strip()
        if claimed and claimed != user["id"]:
            log.warning(f"Remote command claimed user {claimed!r} but the token belongs to {user['id']!r}.")
            return None
        return user

    def _has_level(self, user, required: str) -> bool:
        order = AccessLevel._ORDER
        try:
            return order.index(user["level"]) >= order.index(required)
        except ValueError:
            return False

    # --- answering -------------------------------------------------------------

    def _publish(self, result: dict):
        if callable(self.publish_result):
            try:
                self.publish_result(result)
            except Exception as e:  # noqa: BLE001 - a broker that went away must not break the command
                log.warning(f"Could not publish the remote command result: {e}")

    def _remember(self, command_id, result: dict) -> dict:
        if command_id:
            self._seen[command_id] = result
            self._seen_order.append(command_id)
            while len(self._seen_order) > SEEN_IDS_MAX:
                self._seen.pop(self._seen_order.pop(0), None)
        return result

    def _accept(self, command_id, user, detail: str, **extra) -> dict:
        log.info(f"Remote command accepted: {detail} ({user['name']})")
        if self.audit_logger is not None:
            self.audit_logger.record("REMOTE_COMMAND", f"MQTT:{user['name']}", detail, success=True)
        return self._remember(command_id, {"id": command_id, "accepted": True, "reason": "",
                                           "detail": detail, "user": user["id"], **extra})

    def _refuse(self, reason: str, command_id, context: dict = None, security: bool = False,
                user=None) -> dict:
        who = f"MQTT:{user['name']}" if user else "MQTT"
        detail = f"Remote command refused: {reason}"
        if context:
            detail += " (" + ", ".join(f"{k}={v}" for k, v in context.items()) + ")"
        log.warning(detail)
        if self.audit_logger is not None:
            self.audit_logger.record("REMOTE_COMMAND_REFUSED", who, detail, success=False)
        if security:
            # Owner's instruction: a quiet alarm and a push to the phone.
            # The alarm travels out over the same MQTT link, which is
            # what Home Assistant turns into the notification - so the
            # person finds out even though nothing sounds at the cabinet.
            self._raise_security_alarm(detail)
        return self._remember(command_id, {"id": command_id, "accepted": False, "reason": reason,
                                           "detail": detail})

    def _raise_security_alarm(self, detail: str):
        if self.alarm_manager is None:
            return
        try:
            self.alarm_manager.trigger_alarm(SECURITY_ALARM_ID, detail, source_tag="", priority=3)
        except Exception as e:  # noqa: BLE001 - never let the alarm path break the refusal itself
            log.error(f"Could not raise the remote-command security alarm: {e}")

    # --- what a command may actually do ----------------------------------------

    def _cmd_intrusion(self, body, user, command_id) -> dict:
        """arm / arm_night / disarm / reset / silence, on one zone or on
        all of them. Straight into IntrusionManager with `user=` - so the
        zones that person may operate, and the audit entry naming them,
        are exactly the same as if they had pressed the button at the
        cabinet."""
        from epw_os.core.intrusion_manager import ArmMode

        if self.intrusion_manager is None:
            return self._refuse("this controller has no alarm system", command_id, user=user)
        if not self._has_level(user, AccessLevel.OPERATOR):
            return self._refuse(f"{user['name']} is {user['level']}, Operator is required",
                                command_id, user=user)

        what = str(body.get("what") or "").strip()
        zone_ids = [zone["id"] for zone in self.intrusion_manager.get_zones()]
        target = str(body.get("zone") or "all").strip()
        if target != "all":
            if target not in zone_ids:
                return self._refuse(f"unknown zone {target!r}", command_id, user=user)
            zone_ids = [target]
        if not zone_ids:
            return self._refuse("this controller has no zones", command_id, user=user)

        # Silencing is not per zone - there is one sounder state - so it
        # is answered before the loop rather than run once per zone.
        if what == "silence":
            if self.intrusion_manager.silence(actor=f"MQTT:{user['name']}", user=user["id"]):
                return self._accept(command_id, user, "sounder silenced (the alarm itself is unchanged)")
            return self._refuse("nothing to silence, or not this person's zone", command_id, user=user)

        done, refused = [], []
        for zone_id in zone_ids:
            if what in ("arm", "arm_night"):
                mode = ArmMode.NIGHT if what == "arm_night" else ArmMode.FULL
                result = self.intrusion_manager.arm_zone(
                    zone_id, actor=f"MQTT:{user['name']}", mode=mode, user=user["id"],
                    force=bool(body.get("force", False)))
                (done if result.success else refused).append(
                    zone_id if result.success else f"{zone_id}: {result.reason}")
            elif what == "disarm":
                ok = self.intrusion_manager.disarm_zone(zone_id, actor=f"MQTT:{user['name']}", user=user["id"])
                (done if ok else refused).append(zone_id)
            elif what == "reset":
                ok = self.intrusion_manager.clear_alarm_memory(zone_id, actor=f"MQTT:{user['name']}")
                (done if ok else refused).append(zone_id)
            else:
                return self._refuse(f"unknown alarm action {what!r}", command_id, user=user)

        if not done:
            return self._refuse(f"{what} refused on every zone ({'; '.join(refused)})", command_id, user=user)
        return self._accept(command_id, user, f"{what} on {', '.join(done)}",
                            zones=done, refused=refused)

    def _cmd_apparatus(self, body, user, command_id) -> dict:
        """CLOSE/OPEN an apparatus, through CommandManager - the same
        entry point the panel uses, so the safety kernel, the logic
        interlocks, a force held on that output and Training Mode all
        apply unchanged. Nothing here reaches a driver."""
        if self.command_manager is None:
            return self._refuse("this controller cannot execute commands", command_id, user=user)
        if not self._has_level(user, AccessLevel.OPERATOR):
            return self._refuse(f"{user['name']} is {user['level']}, Operator is required",
                                command_id, user=user)
        target = str(body.get("target") or "").strip()
        what = str(body.get("what") or "").strip().upper()
        if not target or what not in ("CLOSE", "OPEN"):
            return self._refuse("a command needs target and what=CLOSE|OPEN", command_id, user=user)

        permitted, reasons = self.command_manager.request_command(target, what, user=f"MQTT:{user['name']}")
        if not permitted:
            return self._refuse(f"{target} {what}: {'; '.join(reasons) or 'refused'}", command_id, user=user)
        return self._accept(command_id, user, f"{target} {what}", target=target)

    def _cmd_bit(self, body, user, command_id) -> dict:
        """Sets an internal IN bit ({"action": "bit", "target": "M.X",
        "values": {"value": true}}) through the same gate the panel
        uses: the bit must be IN, the project must allow remote writes to
        it, and the person's own level must reach what the bit demands."""
        if self.internal_bits is None:
            return self._refuse("this controller has no internal bits", command_id, user=user)
        target = str(body.get("target") or "").strip()
        values = body.get("values") if isinstance(body.get("values"), dict) else {}
        if not target or "value" not in values:
            return self._refuse("a bit write needs target and values.value", command_id, user=user)
        ok, reason = self.internal_bits.write(target, values["value"], actor=user["name"], source="MQTT",
                                              level=user.get("level"))
        if not ok:
            return self._refuse(f"{target}: {reason}", command_id, user=user)
        return self._accept(command_id, user, f"{target} = {values['value']!r}", target=target)

    @staticmethod
    def _values(body, allowed) -> dict:
        """The setting values, read from their own `values` object rather
        than from the message's top level.

        Found by this module's own test: a protection stage has fields
        called "setting" and "action", and so does the command envelope
        ({"action": "setting"}) - read flat, the envelope's own words
        leaked into the values being written. Nesting them removes the
        class of collision rather than blacklisting the two names that
        happened to clash today.
        """
        values = body.get("values")
        if not isinstance(values, dict):
            return {}
        return {key: values[key] for key in allowed if key in values}

    def _cmd_setting(self, body, user, command_id) -> dict:
        """A setting value, Engineer level. Only the two families that
        have a real, gated setter behind them - a process protection's
        thresholds and an electrical protection stage. Everything else is
        refused by name rather than half-supported."""
        if not self._has_level(user, AccessLevel.ENGINEER):
            return self._refuse(f"{user['name']} is {user['level']}, Engineer is required",
                                command_id, user=user)
        what = str(body.get("what") or "").strip()

        if what == "process_protection":
            if self.process_protection_manager is None:
                return self._refuse("process protection is not part of this controller", command_id, user=user)
            fields = self._values(body, ("upper_threshold", "lower_threshold", "hysteresis",
                                          "delay_seconds", "enabled"))
            if not fields:
                return self._refuse("no setting given", command_id, user=user)
            ok = self.process_protection_manager.update_protection(
                str(body.get("target") or ""), level=AccessLevel.ENGINEER, **fields)
            if not ok:
                return self._refuse(f"process protection {body.get('target')!r} was not updated",
                                    command_id, user=user)
            return self._accept(command_id, user, f"process protection {body.get('target')}: {fields}")

        if what == "electrical_stage":
            setter = getattr(self.project_manager, "set_electrical_stage", None)
            if not callable(setter):
                return self._refuse("this controller cannot change protection stages", command_id, user=user)
            fields = self._values(body, ("enabled", "setting", "hysteresis", "delay_ms", "action"))
            if not fields:
                return self._refuse("no setting given", command_id, user=user)
            ok = setter(str(body.get("target") or ""), str(body.get("stage") or ""),
                        level=AccessLevel.ENGINEER, **fields)
            if not ok:
                return self._refuse(f"stage {body.get('target')}/{body.get('stage')} was not updated",
                                    command_id, user=user)
            return self._accept(command_id, user,
                                f"stage {body.get('target')}/{body.get('stage')}: {fields}")

        return self._refuse(f"unknown setting family {what!r}", command_id, user=user)


_ACTIONS = {
    "intrusion": RemoteCommandGateway._cmd_intrusion,
    "apparatus": RemoteCommandGateway._cmd_apparatus,
    "setting": RemoteCommandGateway._cmd_setting,
    "bit": RemoteCommandGateway._cmd_bit,
}
