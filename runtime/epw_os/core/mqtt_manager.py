"""MQTT integration (Task: "integracja MQTT") - publishes EPW-OS state
(tags, alarms, intrusion events, controller status) to a broker so Home
Assistant and other EPW controllers can consume it without polling the
REST API. Headless (no PyQt import), same rule every other core/ module
in this codebase follows.

GRANICE - enforced IN CODE here, not just by convention (Task's own
explicit warning: "jesli uznasz, ze sterowanie przez MQTT jest
niezbedne - ZATRZYMAJ SIE... nie implementuj"; see SESSION_REPORT.md for
the proposal to design MQTT control as its own, separate task):
  - This module never imports or calls CommandManager, SafetyKernel, or
    any other write path that could change the plant. The complete set
    of tag WRITES this file ever performs is TagManager.add_tag()/
    update_tag() against its own Link.<id>.In* namespace (A5's incoming
    mapping) - plain, read-only-to-everyone-else data tags, the same
    status as any analog input, never a command trigger.
  - _on_message() (the only inbound path at all) does exactly one thing:
    look up the incoming topic in the configured Link.* mapping table
    and write the ONE local tag that mapping names. An unmapped topic,
    or a topic that happens to collide with anything else, is dropped
    silently. There is no generic "topic -> tag" table beyond that
    mapping, and no "topic -> command" table anywhere in this file.
  - Accepting arm/disarm/setpoint/force commands over MQTT was
    deliberately NOT built - it needs its own authentication/
    authorization design (this codebase already learned that lesson
    once, the hard way - see api_auth.py's own docstring on the REST
    API command-bypass vulnerability it was built to close). Proposed
    as a separate future task in SESSION_REPORT.md, not implemented
    here.

Dependency (A2): paho-mqtt - see requirements.txt/SESSION_REPORT.md for
the license/maintenance/transitive-dependency justification. Imported
lazily and defensively: when the package isn't installed,
MQTT_LIB_AVAILABLE is False and every public method below becomes a
documented no-op - the program must start and run normally either way
(A2's own hard requirement, and A6's "brak biblioteki nie blokuje
uruchomienia").

Password handling: a broker password is NOT a PIN or an API token - this
program has to present it to a third party (the broker) on every
connection attempt, so it cannot be stored one-way-hashed the way
AccessManager/ApiAuth store PINs/tokens (those only ever need to compare
a hash, never reproduce the original secret - see access_manager.py's
own docstring). The STORAGE LOCATION convention is still the same one
those two modules already established: a dedicated, gitignored,
local-only JSON file - never project.json, never the repository. See
DEFAULT_SECRET_PATH below and .gitignore.

Resilience (A6): publishing is fully decoupled from tag_changed's
calling thread - _on_tag_changed() only appends to a bounded, in-memory
deque (O(1), no I/O, no network, cannot block whoever just wrote a tag);
a single background worker thread drains that queue against the actual
MQTT client. A lost broker connection therefore cannot slow down or
block logic, alarms, or control in any way - the worst case is the
queue itself filling up and silently dropping its OLDEST entries (never
raising, never blocking the writer) until the connection returns.
Reconnection (exponential backoff) is paho's own built-in
reconnect_delay_set() + automatic reconnect (loop_start()'s network
thread) - not reimplemented here.
"""
import json
import os
import re
import threading
import time
from collections import deque

from epw_os.core.logging import log
from epw_os.core.tag_manager import TagType, TagQuality
from epw_os.version import __version__ as EPW_OS_VERSION

try:
    import paho.mqtt.client as mqtt
    MQTT_LIB_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised by test_mqtt_manager.py
    # by forcing MQTT_LIB_AVAILABLE False directly, not by uninstalling
    # the real package from the test environment.
    mqtt = None
    MQTT_LIB_AVAILABLE = False


class MqttConnectionState:
    """Every value show_able in the config dialog's status line (A3:
    "Stan polaczenia z brokerem widoczny w interfejsie - polaczony,
    rozlaczony, blad uwierzytelnienia")."""
    UNAVAILABLE = "UNAVAILABLE"   # paho-mqtt is not installed
    DISABLED = "DISABLED"         # installed, but the integration switch is off
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    AUTH_ERROR = "AUTH_ERROR"
    ERROR = "ERROR"


# A local tag written from an incoming Link.* mapping must match this
# shape (A5: "mapowac je na wlasne tagi Link.<identyfikator>.In*") - a
# manually-typed config field the operator could get wrong, so it's
# validated rather than trusted blindly.
_LINK_TAG_RE = re.compile(r"^Link\.[^.]+\.In.+$")

# Read-only pattern match against tag NAMES/VALUES already flowing
# through tag_changed, used only to decide whether a SEPARATE,
# non-retained "event" message is also worth publishing on top of the
# generic per-tag state publish every tag already gets (A4: "zdarzenia
# systemu alarmowego: uzbrojenie, rozbrojenie, alarm, awaria linii").
# intrusion_manager.py is never imported, subscribed to directly, or
# modified for this - these are the exact tag names/values it already,
# independently, publishes (see its own module docstring) - GRANICE.
_ZONE_STATE_RE = re.compile(r"^Security\.Zone\.([^.]+)\.State$")
_LINE_FAULT_RE = re.compile(r"^Security\.Line\.([^.]+)\.Fault$")

_TYPE_NAME_TO_TAGTYPE = {
    "BOOL": TagType.BOOL, "INT": TagType.INT, "DINT": TagType.DINT,
    "REAL": TagType.REAL, "STRING": TagType.STRING,
}
_DEFAULT_VALUE_FOR_TYPE = {
    TagType.BOOL: False, TagType.INT: 0, TagType.DINT: 0,
    TagType.REAL: 0.0, TagType.STRING: "",
}


def _sanitize_for_id(text: str) -> str:
    """MQTT client ids / Home Assistant object ids are safest as
    [A-Za-z0-9_-] only - anything else (spaces, dots in a project id,
    non-ASCII) becomes "_"."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", text or "") or "epw_os"


def _tag_topic_path(tag_name: str) -> str:
    """"Security.Zone.Z1.State" -> "Security/Zone/Z1/State" - dots
    become the MQTT hierarchy separator so a subscriber can use a single
    wildcard subscription (e.g. "epw/<id>/tag/Security/Zone/+/State")
    instead of a flat namespace it has to filter client-side. See
    SESSION_REPORT.md's own "topic structure" section for the full
    rationale."""
    return tag_name.replace(".", "/")


def _payload_for_value(value) -> str:
    """One canonical text encoding, reused for the plain state topic AND
    as the Home Assistant discovery payload_on/off - never a second,
    differently-cased boolean spelling to keep track of."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


class MqttManager:
    # Same "anchored to this file's own location" reasoning as
    # AccessManager.DEFAULT_CONFIG_PATH/ApiAuth.DEFAULT_CONFIG_PATH - a
    # relative path here would silently create/read a different file
    # depending on the process's launch directory.
    DEFAULT_SECRET_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "mqtt.local.json"
    )

    def __init__(self, event_bus, tag_manager, project_manager, audit_logger=None,
                 secret_path: str = None, client_factory=None):
        self.event_bus = event_bus
        self.tag_manager = tag_manager
        self.project_manager = project_manager
        self.audit_logger = audit_logger
        self.secret_path = secret_path or self.DEFAULT_SECRET_PATH
        # Only ever overridden by tests, to inject a fake client instead
        # of a real paho one - see test_mqtt_manager.py's FakeMqttClient.
        self._client_factory = client_factory or self._default_client_factory

        self.cfg = self.project_manager.get_mqtt_config()
        self._client = None
        self._connected = False
        self._state = MqttConnectionState.UNAVAILABLE if not MQTT_LIB_AVAILABLE else MqttConnectionState.DISABLED
        self._prefix = ""
        self._device_id = ""

        self._out_queue = deque(maxlen=max(1, int(self.cfg.get("queue_max", 1000))))
        self._queue_lock = threading.Lock()
        self._new_item_event = threading.Event()
        self._stop_event = threading.Event()
        self._worker_thread = None

        # Analog throttling state (A3: publish interval + deadband) -
        # tag name -> (last_published_value, last_published_monotonic).
        self._analog_state = {}
        self._analog_lock = threading.Lock()

        # Home Assistant discovery (A4) - which tags already got a
        # (retained) discovery message published this session, so a
        # tag that changes value 1000 times doesn't republish its own
        # discovery config 1000 times. Cleared on every fresh CONNECT so
        # a broker that lost its retained messages (a fresh/different
        # broker) gets them republished.
        self._discovered_tags = set()

        # Link.* incoming mappings (A5) - topic -> mapping dict, built
        # once at start() from project_manager's persisted config.
        self._link_topic_index = {}

        self.stats = {"sent": 0, "received": 0, "errors": 0, "dropped": 0, "last_connect_time": None}

        # Injectable for tests - real code always uses time.monotonic.
        self._clock = time.monotonic

    # --- state / status (A3, A6: visible in the UI) ---------------------

    def get_state(self) -> str:
        return self._state

    def _set_state(self, state: str):
        if state != self._state:
            self._state = state
            self.event_bus.emit("mqtt_status_changed", state)

    def get_stats(self) -> dict:
        return dict(self.stats)

    # --- secret (password) storage --------------------------------------
    # Same "gitignored local file, separate from project.json" location
    # convention as access.local.json/api_tokens.local.json - see this
    # module's own docstring for why the CONTENT can't be a one-way hash
    # the way those two are.

    def _load_password(self) -> str:
        if not os.path.exists(self.secret_path):
            return ""
        try:
            with open(self.secret_path, "r", encoding="utf-8") as f:
                return json.load(f).get("password", "")
        except Exception as e:
            log.error(f"MQTT: failed to read {self.secret_path}: {e}")
            return ""

    def set_password(self, password: str):
        """Persists the broker password to the gitignored local file -
        called by the Settings > MQTT... dialog, never anything that
        also touches project.json."""
        try:
            os.makedirs(os.path.dirname(self.secret_path) or ".", exist_ok=True)
            with open(self.secret_path, "w", encoding="utf-8") as f:
                json.dump({"password": password}, f, indent=2)
        except OSError as e:
            log.error(f"MQTT: failed to write {self.secret_path}: {e}")

    # --- configuration ---------------------------------------------------

    def configure(self, config: dict, password: str = None, actor: str = "", level: str = None) -> dict:
        """The one entry point the Settings > MQTT... dialog calls to
        change configuration - Engineer-gated the same defense-in-depth
        way EPWCore.set_feature_enabled()/IntrusionManager's own
        Engineer-only setters already are (re-checked here regardless of
        whether the GUI itself already checked, so a direct call
        bypassing the dialog can't skip it either). Persists immediately
        (project.json for everything except the password, the gitignored
        local file for that) and restarts the connection live - no
        program restart needed. Returns {"success": bool, "reason": str}."""
        if level is not None:
            from epw_os.core.access_manager import AccessLevel
            order = AccessLevel._ORDER
            try:
                if order.index(level) < order.index(AccessLevel.ENGINEER):
                    return {"success": False, "reason": "Access denied - Engineer level required."}
            except ValueError:
                # `level` is caller-supplied; unrecognized -> denied (kept
                # unchanged), but worth a log line - same "polykane
                # wyjatki" pattern as System.Mode.
                log.warning(f"MqttManager.configure() refused: unrecognized level {level!r} - denying.")
                return {"success": False, "reason": "Access denied - Engineer level required."}

        clean = dict(self.project_manager.get_mqtt_config())
        clean.update(config)
        clean.pop("password", None)
        self.project_manager.set_mqtt_config(clean)
        self.project_manager.save_project()
        if password is not None:
            self.set_password(password)

        if self.audit_logger is not None:
            self.audit_logger.record(
                "MQTT_CONFIG_CHANGED", actor or "Engineer",
                f"MQTT integration {'enabled' if clean.get('enabled') else 'disabled'} "
                f"(broker {clean.get('host', '')}:{clean.get('port', '')})",
                success=True,
            )

        self.restart()
        return {"success": True, "reason": ""}

    def get_config(self) -> dict:
        return self.project_manager.get_mqtt_config()

    # --- lifecycle ---------------------------------------------------------

    def restart(self):
        self.stop()
        self.start()

    def start(self):
        self.cfg = self.project_manager.get_mqtt_config()
        self._out_queue = deque(maxlen=max(1, int(self.cfg.get("queue_max", 1000))))

        if not self.cfg.get("enabled"):
            self._set_state(MqttConnectionState.DISABLED)
            return
        if not MQTT_LIB_AVAILABLE:
            log.warning(
                "MQTT integration is enabled in configuration, but the 'paho-mqtt' package is not "
                "installed - the integration will stay inactive. Install it with `pip install paho-mqtt`."
            )
            self._set_state(MqttConnectionState.UNAVAILABLE)
            return
        if not self.cfg.get("host"):
            log.warning("MQTT integration is enabled but no broker host is configured - staying inactive.")
            self._set_state(MqttConnectionState.ERROR)
            return

        project_id = ""
        try:
            project_id = self.project_manager.config.get("project_id", "")
        except AttributeError:
            # Deliberate, not a swallowed problem: project_manager is a
            # minimal stand-in without a real .config in some tests/
            # isolated callers - project_id just stays "" and
            # _device_id below falls back to "epw_os" instead. Not
            # logged - it would fire routinely for every such caller,
            # not just a real one hitting an actual problem.
            pass
        self._device_id = _sanitize_for_id(self.cfg.get("client_id") or project_id or "epw_os")
        self._prefix = (self.cfg.get("topic_prefix") or f"epw/{self._device_id}").rstrip("/")

        self._client = self._client_factory(self._device_id)
        self._configure_client(self._client)

        self._register_link_in_tags()

        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="MqttWorker")
        self._worker_thread.start()

        self.event_bus.subscribe("tag_changed", self._on_tag_changed)
        self.event_bus.subscribe("alarm_triggered", self._on_alarm_triggered)
        self.event_bus.subscribe("alarm_cleared", self._on_alarm_cleared)
        self.event_bus.subscribe("alarm_acknowledged", self._on_alarm_acknowledged)
        self.event_bus.subscribe("mode_change_request", self._on_mode_change_request)

        self._set_state(MqttConnectionState.CONNECTING)
        try:
            self._client.connect_async(self.cfg["host"], int(self.cfg["port"]), keepalive=60)
            self._client.loop_start()
        except Exception as e:
            log.error(f"MQTT: could not start connection to {self.cfg['host']}:{self.cfg['port']}: {e}")
            self.stats["errors"] += 1
            self._set_state(MqttConnectionState.ERROR)

    def stop(self):
        self.event_bus.unsubscribe("tag_changed", self._on_tag_changed)
        self.event_bus.unsubscribe("alarm_triggered", self._on_alarm_triggered)
        self.event_bus.unsubscribe("alarm_cleared", self._on_alarm_cleared)
        self.event_bus.unsubscribe("alarm_acknowledged", self._on_alarm_acknowledged)
        self.event_bus.unsubscribe("mode_change_request", self._on_mode_change_request)

        self._stop_event.set()
        self._new_item_event.set()
        if self._worker_thread is not None and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
        self._worker_thread = None

        if self._client is not None:
            client = self._client
            try:
                # Publish a clean (non-LWT) "offline" before disconnecting,
                # so a graceful shutdown is distinguishable in principle
                # from a lost-connection LWT firing later - both end up
                # "false", but this one is retained immediately rather
                # than waiting on the broker's own keepalive timeout.
                client.publish(self._topic("status/online"), "false", qos=0, retain=True)
            except Exception:
                # Deliberate, not logged: shutdown cleanup, best-effort
                # only - the client may already be disconnected/broken at
                # this point (e.g. stop() called right after a failed
                # connect), and either way the program is tearing this
                # connection down regardless of whether this one last
                # publish succeeded. The Task's own explicit example of
                # "swiadome i uzasadnione... blad i tak nic nie zmienia".
                pass
            try:
                client.disconnect()
            except Exception:
                # Same "best-effort shutdown cleanup" reasoning as the
                # publish attempt just above - disconnect() failing here
                # changes nothing about the fact this connection is going
                # away either way.
                pass
            # loop_stop() joins paho's own background network thread,
            # which can be blocked mid-retry (its own reconnect backoff
            # sleep, or an in-progress connect attempt to an unreachable
            # broker) for up to that retry's own delay - measured up to
            # ~2s against an unreachable host in practice. disconnect()
            # above has already told the socket to close; running
            # loop_stop() itself on a short-lived daemon thread instead
            # of joining it here keeps shutdown()/stop() prompt (A6:
            # "publikacja nie moze blokowac... interfejsu") - safe to
            # abandon since it touches nothing but the now-orphaned
            # paho client object, not shared state.
            threading.Thread(target=client.loop_stop, daemon=True, name="MqttLoopStop").start()
        self._client = None
        self._connected = False
        self._link_topic_index = {}
        self._discovered_tags.clear()
        self._set_state(MqttConnectionState.UNAVAILABLE if not MQTT_LIB_AVAILABLE else MqttConnectionState.DISABLED)

    # --- client construction / callbacks -----------------------------------

    def _default_client_factory(self, client_id: str):
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, protocol=mqtt.MQTTv311)

    def _configure_client(self, client):
        username = self.cfg.get("username") or None
        password = self._load_password() or None
        if username:
            client.username_pw_set(username, password)
        if self.cfg.get("tls"):
            client.tls_set()
        # Last Will and Testament (A4): fires (retained) if this
        # connection is lost WITHOUT a clean disconnect - the broker
        # itself publishes it, so it works even if this process is
        # killed outright, not just on a graceful stop().
        client.will_set(self._topic("status/online"), "false", qos=0, retain=True)
        # A6: exponential backoff, capped - paho's own built-in
        # reconnect logic (used by loop_start()'s background network
        # thread), not reimplemented here.
        client.reconnect_delay_set(min_delay=1, max_delay=60)

        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_connect_fail = self._on_connect_fail
        client.on_message = self._on_message

    def _on_connect(self, client, userdata, connect_flags, reason_code, properties=None):
        is_failure = bool(getattr(reason_code, "is_failure", reason_code not in (0, None)))
        if not is_failure:
            self._connected = True
            self.stats["last_connect_time"] = time.time()
            self._set_state(MqttConnectionState.CONNECTED)
            self._discovered_tags.clear()  # re-publish HA discovery in case the broker doesn't remember it
            self._publish_controller_status()
            self._resubscribe_link_topics()
            return

        self.stats["errors"] += 1
        name = str(getattr(reason_code, "getName", lambda: reason_code)()).lower()
        if "password" in name or "authoriz" in name:
            self._set_state(MqttConnectionState.AUTH_ERROR)
        else:
            self._set_state(MqttConnectionState.ERROR)

    def _on_connect_fail(self, client, userdata):
        # Network-level failure (broker unreachable, DNS failure, ...) -
        # no CONNACK was ever received, so there is no reason_code to
        # inspect. Automatic retry (with backoff) is paho's own - see
        # reconnect_delay_set() above.
        self._connected = False
        self.stats["errors"] += 1
        self._set_state(MqttConnectionState.ERROR)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        self._connected = False
        if self._stop_event.is_set():
            return  # our own stop() already called disconnect() - not a fault
        self._set_state(MqttConnectionState.DISCONNECTED)

    def _on_message(self, client, userdata, message):
        """A5's ONLY inbound path - see this module's own GRANICE
        section at the top for the hard boundary this enforces."""
        self.stats["received"] += 1
        mapping = self._link_topic_index.get(message.topic)
        if mapping is None:
            return  # not a configured Link.* topic - dropped silently
        try:
            payload = message.payload.decode("utf-8") if isinstance(message.payload, (bytes, bytearray)) else str(message.payload)
        except UnicodeDecodeError:
            # A remote peer sending a non-UTF-8 payload on a configured
            # Link.* topic - dropped (kept unchanged), but silently would
            # leave the tag simply never updating with no clue why - the
            # same "polykane wyjatki" pattern as System.Mode.
            log.warning(f"MQTT: could not decode payload on Link.* topic {message.topic!r} as UTF-8 - dropped.")
            return
        self._apply_link_message(mapping, payload)

    # --- topic helpers -------------------------------------------------

    def _topic(self, suffix: str) -> str:
        return f"{self._prefix}/{suffix}"

    # --- publishing: queue + worker -----------------------------------
    # (A6: non-blocking, bounded, oldest-dropped-first)

    def _enqueue(self, topic: str, payload: str, retain: bool):
        with self._queue_lock:
            was_full = len(self._out_queue) >= self._out_queue.maxlen
            self._out_queue.append((topic, payload, retain))
            if was_full:
                self.stats["dropped"] += 1
        self._new_item_event.set()

    def _worker_loop(self):
        while not self._stop_event.is_set():
            item = None
            with self._queue_lock:
                if self._connected and self._out_queue:
                    item = self._out_queue.popleft()
                else:
                    self._new_item_event.clear()
            if item is None:
                # Staleness watchdog (A5) piggybacks on this same idle
                # tick - see the module docstring's own "Resilience"
                # section and TagManager.check_watchdogs()'s existing,
                # generic mechanism. Only run at all when there is
                # something to watch, so an MQTT setup with no Link.*
                # mappings configured doesn't change any tag's check
                # cadence versus not running this module at all.
                if self._link_topic_index:
                    try:
                        self.tag_manager.check_watchdogs()
                    except Exception:
                        log.error("MQTT: check_watchdogs() raised", exc_info=True)
                self._new_item_event.wait(timeout=0.5)
                continue
            topic, payload, retain = item
            try:
                self._client.publish(topic, payload, qos=0, retain=retain)
                self.stats["sent"] += 1
            except Exception:
                self.stats["errors"] += 1
                log.error(f"MQTT: publish to {topic} failed", exc_info=True)

    # --- A4: publishing tags / status ------------------------------------

    def _publish_controller_status(self):
        self._enqueue(self._topic("status/online"), "true", retain=True)
        self._enqueue(self._topic("status/version"), EPW_OS_VERSION, retain=True)
        self._enqueue(self._topic("status/mode"), self.tag_manager.mode, retain=True)
        # A retained snapshot of every currently-known tag, not just
        # future changes - so a client connecting after startup sees
        # the full current state immediately (A4: "wiadomosci
        # zatrzymane... zeby nowo podlaczony odbiorca od razu znal
        # stan"), not just what happens to change from here on.
        for tag in self.tag_manager.list_tags():
            self._publish_tag(tag.name, tag.value, tag.quality, force=True)

    def _on_mode_change_request(self, new_mode: str):
        self._enqueue(self._topic("status/mode"), new_mode, retain=True)

    def _on_tag_changed(self, tag_name, value, quality):
        q = TagQuality(quality) if isinstance(quality, str) else quality
        self._publish_tag(tag_name, value, q)
        self._maybe_emit_intrusion_event(tag_name, value)

    def _publish_tag(self, tag_name: str, value, quality: TagQuality, force: bool = False):
        if not force and isinstance(value, float):
            if not self._should_publish_analog(tag_name, value):
                return
        path = _tag_topic_path(tag_name)
        state_topic = self._topic(f"tag/{path}/state")
        self._enqueue(state_topic, _payload_for_value(value), retain=True)
        self._enqueue(self._topic(f"tag/{path}/quality"), quality.value, retain=True)
        self._maybe_publish_discovery(tag_name, value, state_topic)

    def _should_publish_analog(self, tag_name: str, value: float) -> bool:
        """A3: publish interval (rate limit) + deadband (minimum change)
        for analog (REAL) values only - mirrors historian.py's own
        deadband concept/vocabulary (configure_deadband()) for
        consistency, though this is a separate, independent filter (a
        tag can be deadbanded out of the historian and still publish to
        MQTT, or vice versa - two different consumers, two different
        acceptable-noise levels)."""
        now = self._clock()
        with self._analog_lock:
            prev = self._analog_state.get(tag_name)
            if prev is None:
                self._analog_state[tag_name] = (value, now)
                return True
            prev_value, prev_time = prev
            interval = float(self.cfg.get("publish_interval_s", 2.0))
            if (now - prev_time) < interval:
                return False
            threshold = float(self.cfg.get("deadband_per_tag", {}).get(tag_name, self.cfg.get("default_deadband", 0.0)))
            if abs(value - prev_value) < threshold:
                return False
            self._analog_state[tag_name] = (value, now)
            return True

    # --- A4: alarms --------------------------------------------------------

    def _on_alarm_triggered(self, alarm):
        self._enqueue(self._topic(f"alarm/{alarm.id}/state"), "ACTIVE", retain=True)
        self._enqueue(self._topic(f"alarm/{alarm.id}/event"),
                      json.dumps({"event": "TRIGGERED", "message": alarm.message, "priority": alarm.priority,
                                  "ts": alarm.activation_time}),
                      retain=False)

    def _on_alarm_cleared(self, alarm):
        self._enqueue(self._topic(f"alarm/{alarm.id}/state"), "CLEARED", retain=True)
        self._enqueue(self._topic(f"alarm/{alarm.id}/event"),
                      json.dumps({"event": "CLEARED", "message": alarm.message, "ts": alarm.clear_time}),
                      retain=False)

    def _on_alarm_acknowledged(self, alarm):
        self._enqueue(self._topic(f"alarm/{alarm.id}/event"),
                      json.dumps({"event": "ACKNOWLEDGED", "by": alarm.ack_user, "ts": alarm.ack_time}),
                      retain=False)

    # --- A4: intrusion events (read-only pattern match, see module
    # docstring's GRANICE section) --------------------------------------

    def _maybe_emit_intrusion_event(self, tag_name, value):
        m = _ZONE_STATE_RE.match(tag_name)
        if m and value in ("ARMED", "DISARMED", "ALARM"):
            zone_id = m.group(1)
            self._enqueue(self._topic("event/intrusion"),
                          json.dumps({"event": value, "zone": zone_id, "ts": time.time()}), retain=False)
            return
        m = _LINE_FAULT_RE.match(tag_name)
        if m and value is True:
            line_id = m.group(1)
            self._enqueue(self._topic("event/intrusion"),
                          json.dumps({"event": "LINE_FAULT", "line": line_id, "ts": time.time()}), retain=False)

    # --- A4: Home Assistant MQTT discovery (best-effort, retained) ------

    def _maybe_publish_discovery(self, tag_name: str, value, state_topic: str):
        if tag_name in self._discovered_tags:
            return
        self._discovered_tags.add(tag_name)
        tag = self.tag_manager.get_tag(tag_name)
        data_type = tag.data_type if tag is not None else None
        component = "binary_sensor" if data_type == TagType.BOOL or isinstance(value, bool) else "sensor"
        object_id = _sanitize_for_id(tag_name)
        payload = {
            "name": tag_name,
            "unique_id": f"{self._device_id}_{object_id}",
            "state_topic": state_topic,
            "availability_topic": self._topic("status/online"),
            "payload_available": "true",
            "payload_not_available": "false",
            "device": {
                "identifiers": [self._device_id],
                "name": f"EPW-OS ({self._device_id})",
                "manufacturer": "BroniszLabs",
                "model": "EPW-OS",
                "sw_version": EPW_OS_VERSION,
            },
        }
        if component == "binary_sensor":
            payload["payload_on"] = "true"
            payload["payload_off"] = "false"
        discovery_topic = f"homeassistant/{component}/{self._device_id}/{object_id}/config"
        self._enqueue(discovery_topic, json.dumps(payload), retain=True)

    # --- A5: Link.* incoming mappings -----------------------------------

    def _register_link_in_tags(self):
        self._link_topic_index = {}
        for entry in self.cfg.get("link_in", []):
            topic = entry.get("topic", "").strip()
            tag_name = entry.get("tag", "").strip()
            type_name = entry.get("type", "BOOL")
            stale_after_s = float(entry.get("stale_after_s", 30) or 30)
            if not topic or not _LINK_TAG_RE.match(tag_name):
                log.warning(f"MQTT: skipping invalid Link.* mapping (topic={topic!r}, tag={tag_name!r}) - "
                            f"tag must match Link.<identifier>.In<name>.")
                continue
            tag_type = _TYPE_NAME_TO_TAGTYPE.get(type_name, TagType.BOOL)
            if self.tag_manager.get_tag(tag_name) is None:
                self.tag_manager.add_tag(
                    tag_name, _DEFAULT_VALUE_FOR_TYPE[tag_type], tag_type,
                    description=f"Incoming Link data from MQTT topic '{topic}' - informational only, "
                                f"read by user logic, never treated as a command. Marked STALE if no update "
                                f"arrives for {stale_after_s:.0f}s.",
                    source="MQTT_LINK", timeout=stale_after_s,
                )
            self._link_topic_index[topic] = {"tag": tag_name, "type": tag_type}

    def _resubscribe_link_topics(self):
        if self._client is None:
            return
        for topic in self._link_topic_index:
            try:
                self._client.subscribe(topic)
            except Exception:
                log.error(f"MQTT: failed to subscribe to Link.* topic {topic!r}", exc_info=True)

    def _apply_link_message(self, mapping: dict, payload: str):
        tag_name = mapping["tag"]
        tag_type = mapping["type"]
        try:
            if tag_type == TagType.BOOL:
                value = payload.strip().lower() in ("1", "true", "on", "yes")
            elif tag_type in (TagType.INT, TagType.DINT):
                value = int(float(payload))
            elif tag_type == TagType.REAL:
                value = float(payload)
            else:
                value = payload
        except (ValueError, TypeError):
            log.warning(f"MQTT: could not parse incoming payload {payload!r} for {tag_name} as {tag_type.value}")
            return
        try:
            self.tag_manager.update_tag(tag_name, value)
        except ValueError:
            pass  # tag vanished (feature disabled/reconfigured mid-flight) - nothing to update
