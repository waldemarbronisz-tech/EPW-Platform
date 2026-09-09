"""Tests for the MQTT integration (epw_os/core/mqtt_manager.py) -
headless, no Qt needed at all, and NEVER against a real broker or real
network socket (Task's own instruction: "Testy MQTT pisz WYLACZNIE na
atrapie brokera - nigdy na prawdziwym polaczeniu sieciowym. Test nie
moze wisiec w oczekiwaniu na siec.") - every test below injects
FakeMqttClient via MqttManager's own client_factory hook, so no test
here ever opens a socket.

Organized by the Task's own "DOWOD UKONCZENIA" checklist:
1. Program starts and runs normally with the integration DISABLED.
2. Program starts when the paho-mqtt LIBRARY isn't installed.
3. No broker does not block startup or ongoing operation.
4. A lost connection does not affect logic/alarms/control.
5. The outgoing queue is bounded and drops the OLDEST entry first.
6. An incoming Link.* signal with no update is marked STALE.
7. No MQTT message can ever trigger a command.
8. The broker password never reaches project.json.
Plus: topic/payload shape, retained-vs-event, analog deadband/interval,
Home Assistant discovery, and project_manager's own get/set round trip.
"""
import json
import time

import pytest

from epw_os.core.alarm_manager import AlarmManager
from epw_os.core.events import EventBus
from epw_os.core.mqtt_manager import MqttManager, MqttConnectionState, MQTT_LIB_AVAILABLE
from epw_os.core.project_manager import ProjectManager
from epw_os.core.tag_manager import TagManager, TagType, TagQuality


class FakeMqttClient:
    """Stands in for paho.mqtt.client.Client - implements only the
    subset of the real API MqttManager actually calls, and NEVER touches
    a real socket. Tests drive `on_connect`/`on_disconnect`/`on_message`
    themselves to simulate broker behavior."""

    def __init__(self, client_id):
        self.client_id = client_id
        self.published = []      # [(topic, payload, retain)]
        self.subscribed = []
        self.will = None
        self.username = None
        self.password = None
        self.tls = False
        self.connect_calls = []
        self.loop_started = False
        self.loop_stopped = False
        self.disconnected = False
        self.on_connect = None
        self.on_disconnect = None
        self.on_connect_fail = None
        self.on_message = None
        self.raise_on_connect_async = False

    def username_pw_set(self, username, password=None):
        self.username, self.password = username, password

    def tls_set(self, *a, **kw):
        self.tls = True

    def will_set(self, topic, payload=None, qos=0, retain=False):
        self.will = (topic, payload, retain)

    def reconnect_delay_set(self, min_delay=1, max_delay=120):
        pass

    def connect_async(self, host, port=1883, keepalive=60):
        if self.raise_on_connect_async:
            raise OSError("simulated network error")
        self.connect_calls.append((host, port))

    def loop_start(self):
        self.loop_started = True

    def loop_stop(self):
        self.loop_stopped = True

    def disconnect(self):
        self.disconnected = True

    def publish(self, topic, payload=None, qos=0, retain=False, properties=None):
        self.published.append((topic, payload, retain))

    def subscribe(self, topic, qos=0):
        self.subscribed.append(topic)


class FakeReasonCode:
    """Mimics just enough of paho's ReasonCode (v2 callback API) for
    _on_connect()'s failure/auth-error detection - see mqtt_manager.py's
    own _on_connect()."""
    def __init__(self, is_failure, name="Success"):
        self.is_failure = is_failure
        self._name = name

    def getName(self):
        return self._name


def _wait_until(condition, timeout=2.0, interval=0.005):
    """Polls an in-process condition (never the network - see module
    docstring) until true or timeout. Used only to let the background
    worker thread drain its queue against the FakeMqttClient."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(interval)
    return condition()


@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def tags(bus):
    tm = TagManager(bus)
    tm.add_tag("DI1", False, TagType.BOOL, source="HARDWARE")
    tm.add_tag("Meas.L1", 0.0, TagType.REAL, quality=TagQuality.SIMULATED, source="SIMULATION")
    return tm


@pytest.fixture
def project(tmp_path):
    return ProjectManager(project_file=str(tmp_path / "project.json"))


def make_manager(bus, tags, project, tmp_path, enabled=True, **cfg_overrides):
    project.load_project()
    cfg = project.get_mqtt_config()
    cfg.update({"enabled": enabled, "host": "broker.example.invalid", "port": 1883,
                "topic_prefix": "epw/TESTUNIT"})
    cfg.update(cfg_overrides)
    project.set_mqtt_config(cfg)
    project.save_project()

    created = []

    def factory(client_id):
        c = FakeMqttClient(client_id)
        created.append(c)
        return c

    manager = MqttManager(bus, tags, project, audit_logger=None,
                           secret_path=str(tmp_path / "mqtt.local.json"), client_factory=factory)
    manager.start()
    client = created[0] if created else None
    return manager, client


def connect(manager, client):
    """Simulates a successful CONNACK, exactly as _on_connect() would
    receive it from real paho."""
    client.on_connect(client, None, {}, FakeReasonCode(is_failure=False), None)


# --- DOWOD 1: disabled integration --------------------------------------

def test_disabled_integration_does_not_touch_the_network(bus, tags, project, tmp_path):
    manager, client = make_manager(bus, tags, project, tmp_path, enabled=False)
    assert manager.get_state() == MqttConnectionState.DISABLED
    assert client is None  # _client_factory was never even called
    # Tags still work completely normally.
    tags.update_tag("DI1", True)
    assert tags.get_value("DI1") is True
    manager.stop()


# --- DOWOD 2: library not installed -------------------------------------

def test_missing_library_is_a_graceful_no_op(bus, tags, project, tmp_path, monkeypatch):
    import epw_os.core.mqtt_manager as mm
    monkeypatch.setattr(mm, "MQTT_LIB_AVAILABLE", False)
    manager, client = make_manager(bus, tags, project, tmp_path, enabled=True)
    assert manager.get_state() == MqttConnectionState.UNAVAILABLE
    assert client is None
    # The rest of the program is unaffected.
    tags.update_tag("DI1", True)
    assert tags.get_value("DI1") is True
    manager.stop()


def test_paho_mqtt_really_is_importable_in_this_environment():
    """Not a mock - confirms the real optional dependency this task adds
    (see requirements.txt) actually resolves in a normal environment,
    so the graceful-fallback tests above are exercising the FALLBACK
    path deliberately, not the only path that happens to work."""
    assert MQTT_LIB_AVAILABLE is True


# --- DOWOD 3: no broker does not block startup or operation -------------

def test_unreachable_broker_does_not_block_start_or_shutdown(bus, tags, project, tmp_path):
    manager, client = make_manager(bus, tags, project, tmp_path, enabled=True)
    assert manager.get_state() == MqttConnectionState.CONNECTING
    # Program keeps running while "still trying to connect".
    tags.update_tag("DI1", True)
    assert tags.get_value("DI1") is True

    t0 = time.monotonic()
    manager.stop()
    assert (time.monotonic() - t0) < 1.0, "stop() must not block waiting on the (fake) network"


def test_connect_async_raising_does_not_crash_startup(bus, tags, project, tmp_path):
    """A network-level failure so immediate it raises synchronously
    (DNS resolution failure, etc.) - start() must catch it, not
    propagate, and the rest of the program must be unaffected."""
    project.load_project()
    cfg = project.get_mqtt_config()
    cfg.update({"enabled": True, "host": "nonexistent.invalid"})
    project.set_mqtt_config(cfg)
    project.save_project()

    created = []

    def factory(client_id):
        c = FakeMqttClient(client_id)
        c.raise_on_connect_async = True
        created.append(c)
        return c

    manager = MqttManager(bus, tags, project, secret_path=str(tmp_path / "mqtt.local.json"), client_factory=factory)
    manager.start()  # must not raise
    assert manager.get_state() == MqttConnectionState.ERROR
    tags.update_tag("DI1", True)
    assert tags.get_value("DI1") is True
    manager.stop()


# --- DOWOD 4: a lost connection does not affect logic/alarms/control ----

def test_disconnect_does_not_affect_tag_writes_or_alarms(bus, tags, project, tmp_path):
    alarms = AlarmManager(bus)
    manager, client = make_manager(bus, tags, project, tmp_path, enabled=True)
    connect(manager, client)
    assert manager.get_state() == MqttConnectionState.CONNECTED

    client.on_disconnect(client, None, {}, FakeReasonCode(is_failure=True, name="Unspecified error"), None)
    assert manager.get_state() == MqttConnectionState.DISCONNECTED

    # Completely unrelated systems keep working - a disconnect here must
    # never propagate into a tag write or an alarm failing.
    tags.update_tag("DI1", True)
    assert tags.get_value("DI1") is True
    alarms.trigger_alarm("TEST_ALARM", "test", source_tag="DI1", priority=2)
    assert alarms.get_active_alarms()
    manager.stop()


def test_auth_error_is_distinguished_from_a_plain_connection_error(bus, tags, project, tmp_path):
    manager, client = make_manager(bus, tags, project, tmp_path, enabled=True)
    client.on_connect(client, None, {}, FakeReasonCode(is_failure=True, name="Bad user name or password"), None)
    assert manager.get_state() == MqttConnectionState.AUTH_ERROR
    manager.stop()


def test_connect_fail_network_level_sets_error_state(bus, tags, project, tmp_path):
    manager, client = make_manager(bus, tags, project, tmp_path, enabled=True)
    client.on_connect_fail(client, None)
    assert manager.get_state() == MqttConnectionState.ERROR
    manager.stop()


# --- DOWOD 5: bounded queue, drops oldest first -------------------------

def test_outgoing_queue_is_bounded_and_drops_oldest(bus, tags, project, tmp_path):
    manager, client = make_manager(bus, tags, project, tmp_path, enabled=True, queue_max=3)
    # Never connect() - the worker thread only drains while _connected,
    # so the queue accumulates deterministically for this assertion.
    for i in range(10):
        tags.add_tag(f"Flag{i}", False, TagType.BOOL, source="SYSTEM") if tags.get_tag(f"Flag{i}") is None else None
        tags.update_tag(f"Flag{i}", True)
    assert len(manager._out_queue) == 3, "queue must never exceed its configured bound"
    assert manager.stats["dropped"] > 0
    # The newest entries survive, not the oldest - a reconnecting client
    # should see recent state, not stale leftovers.
    surviving_topics = [t for t, _p, _r in manager._out_queue]
    assert any("Flag9" in t for t in surviving_topics)
    assert not any("Flag0" in t for t in surviving_topics)
    manager.stop()


# --- DOWOD 6: incoming Link.* signal without updates goes STALE ---------

def test_link_in_tag_registered_with_configured_staleness_timeout(bus, tags, project, tmp_path):
    manager, client = make_manager(
        bus, tags, project, tmp_path, enabled=True,
        link_in=[{"topic": "site2/mains_ok", "tag": "Link.SITE2.InMainsOk", "type": "BOOL", "stale_after_s": 5}],
    )
    tag = tags.get_tag("Link.SITE2.InMainsOk")
    assert tag is not None
    assert tag.timeout == 5
    assert tag.quality != TagQuality.STALE  # freshly registered, not stale yet
    manager.stop()


def test_link_in_tag_goes_stale_with_no_update_and_recovers_on_update(bus, tags, project, tmp_path):
    manager, client = make_manager(
        bus, tags, project, tmp_path, enabled=True,
        link_in=[{"topic": "site2/mains_ok", "tag": "Link.SITE2.InMainsOk", "type": "BOOL", "stale_after_s": 0.05}],
    )
    time.sleep(0.08)
    tags.check_watchdogs()  # the exact, pre-existing, generic mechanism this module reuses - see its own docstring
    assert tags.get_tag("Link.SITE2.InMainsOk").quality == TagQuality.STALE

    # A fresh incoming message un-stales it, exactly like any other tag update.
    client.on_message(client, None, type("Msg", (), {"topic": "site2/mains_ok", "payload": b"true"})())
    tag = tags.get_tag("Link.SITE2.InMainsOk")
    assert tag.quality != TagQuality.STALE
    assert tag.value is True
    manager.stop()


def test_invalid_link_tag_name_is_rejected_not_registered(bus, tags, project, tmp_path, caplog):
    manager, client = make_manager(
        bus, tags, project, tmp_path, enabled=True,
        link_in=[{"topic": "x/y", "tag": "NotLinkNamespace.Foo", "type": "BOOL"}],
    )
    assert tags.get_tag("NotLinkNamespace.Foo") is None
    manager.stop()


# --- DOWOD 7: no MQTT message can ever trigger a command ----------------

def test_manager_holds_no_reference_to_any_command_path(bus, tags, project, tmp_path):
    manager, client = make_manager(bus, tags, project, tmp_path, enabled=True)
    for forbidden in ("command_manager", "safety_kernel", "driver_manager"):
        assert not hasattr(manager, forbidden)
    manager.stop()


def test_message_on_an_unmapped_topic_writes_nothing_and_raises_nothing(bus, tags, project, tmp_path):
    manager, client = make_manager(bus, tags, project, tmp_path, enabled=True)
    before = {t.name: t.value for t in tags.list_tags()}
    # An attacker/misconfigured peer publishing something that LOOKS
    # like a command topic - must be dropped silently, never acted on.
    msg = type("Msg", (), {"topic": "epw/TESTUNIT/cmd/arm", "payload": b"true"})()
    client.on_message(client, None, msg)
    after = {t.name: t.value for t in tags.list_tags()}
    assert before == after
    manager.stop()


def test_message_on_a_link_topic_only_ever_writes_that_ones_own_tag(bus, tags, project, tmp_path):
    manager, client = make_manager(
        bus, tags, project, tmp_path, enabled=True,
        link_in=[{"topic": "site2/mains_ok", "tag": "Link.SITE2.InMainsOk", "type": "BOOL"}],
    )
    before = {t.name: t.value for t in tags.list_tags() if t.name != "Link.SITE2.InMainsOk"}
    msg = type("Msg", (), {"topic": "site2/mains_ok", "payload": b"true"})()
    client.on_message(client, None, msg)
    after = {t.name: t.value for t in tags.list_tags() if t.name != "Link.SITE2.InMainsOk"}
    assert before == after, "an incoming Link.* message must never write any tag other than its own mapped one"
    assert tags.get_value("Link.SITE2.InMainsOk") is True
    manager.stop()


# --- DOWOD 8: the broker password never reaches project.json -----------

def test_password_never_written_to_project_json(bus, tags, project, tmp_path):
    project.load_project()
    secret_path = str(tmp_path / "mqtt.local.json")
    manager = MqttManager(bus, tags, project, secret_path=secret_path,
                           client_factory=lambda cid: FakeMqttClient(cid))
    result = manager.configure(
        {"enabled": True, "host": "broker.example.invalid", "port": 1883},
        password="s3cr3t-pw", actor="Engineer", level="Engineer",
    )
    assert result["success"] is True

    with open(project.project_file, "r", encoding="utf-8") as f:
        raw = json.load(f)
    assert "password" not in raw.get("mqtt", {})
    assert "s3cr3t-pw" not in json.dumps(raw)
    assert "password" not in project.get_mqtt_config()

    with open(secret_path, "r", encoding="utf-8") as f:
        secret = json.load(f)
    assert secret["password"] == "s3cr3t-pw"
    manager.stop()


def test_configure_below_engineer_is_refused(bus, tags, project, tmp_path):
    project.load_project()
    manager = MqttManager(bus, tags, project, secret_path=str(tmp_path / "mqtt.local.json"),
                           client_factory=lambda cid: FakeMqttClient(cid))
    result = manager.configure({"enabled": True, "host": "x"}, actor="Operator", level="Operator")
    assert result["success"] is False
    assert project.get_mqtt_config()["enabled"] is False  # unchanged
    manager.stop()


# --- Topic structure / retained-vs-event / payload shape ----------------

def test_tag_change_publishes_retained_state_and_quality(bus, tags, project, tmp_path):
    manager, client = make_manager(bus, tags, project, tmp_path, enabled=True)
    connect(manager, client)
    tags.update_tag("DI1", True)
    assert _wait_until(lambda: any(t == "epw/TESTUNIT/tag/DI1/state" for t, _p, _r in client.published))
    state_msgs = [(t, p, r) for t, p, r in client.published if t == "epw/TESTUNIT/tag/DI1/state"]
    assert state_msgs[-1] == ("epw/TESTUNIT/tag/DI1/state", "true", True)
    quality_msgs = [(t, p, r) for t, p, r in client.published if t == "epw/TESTUNIT/tag/DI1/quality"]
    assert quality_msgs[-1][1] == "GOOD"
    assert quality_msgs[-1][2] is True  # retained
    manager.stop()


def test_simulated_tag_is_recognizable_as_simulated_on_the_wire(bus, tags, project, tmp_path):
    manager, client = make_manager(bus, tags, project, tmp_path, enabled=True, publish_interval_s=0.0)
    connect(manager, client)
    tags.update_tag("Meas.L1", 42.0, TagQuality.SIMULATED)
    assert _wait_until(lambda: any(t == "epw/TESTUNIT/tag/Meas/L1/quality" for t, _p, _r in client.published))
    quality_msgs = [(t, p, r) for t, p, r in client.published if t == "epw/TESTUNIT/tag/Meas/L1/quality"]
    assert quality_msgs[-1][1] == "SIMULATED"
    manager.stop()


def test_online_status_retained_and_last_will_configured(bus, tags, project, tmp_path):
    manager, client = make_manager(bus, tags, project, tmp_path, enabled=True)
    assert client.will == ("epw/TESTUNIT/status/online", "false", True)
    connect(manager, client)
    assert _wait_until(lambda: ("epw/TESTUNIT/status/online", "true", True) in client.published)
    manager.stop()
    assert ("epw/TESTUNIT/status/online", "false", True) in client.published


def test_alarm_triggered_is_retained_state_plus_non_retained_event(bus, tags, project, tmp_path):
    alarms = AlarmManager(bus)
    manager, client = make_manager(bus, tags, project, tmp_path, enabled=True)
    connect(manager, client)
    alarms.trigger_alarm("A1", "Test alarm", source_tag="DI1", priority=3)
    assert _wait_until(lambda: any(t == "epw/TESTUNIT/alarm/A1/state" for t, _p, _r in client.published))
    state = [(t, p, r) for t, p, r in client.published if t == "epw/TESTUNIT/alarm/A1/state"][-1]
    assert state == ("epw/TESTUNIT/alarm/A1/state", "ACTIVE", True)
    event = [(t, p, r) for t, p, r in client.published if t == "epw/TESTUNIT/alarm/A1/event"][-1]
    assert event[2] is False  # events are never retained
    assert json.loads(event[1])["event"] == "TRIGGERED"
    manager.stop()


def test_intrusion_zone_state_change_emits_a_non_retained_event(bus, tags, project, tmp_path):
    tags.add_tag("Security.Zone.Z1.State", "DISARMED", TagType.STRING, source="SYSTEM")
    manager, client = make_manager(bus, tags, project, tmp_path, enabled=True)
    connect(manager, client)
    tags.update_tag("Security.Zone.Z1.State", "ARMED")
    assert _wait_until(lambda: any(t == "epw/TESTUNIT/event/intrusion" for t, _p, _r in client.published))
    ev = [(t, p, r) for t, p, r in client.published if t == "epw/TESTUNIT/event/intrusion"][-1]
    assert ev[2] is False
    payload = json.loads(ev[1])
    assert payload["event"] == "ARMED"
    assert payload["zone"] == "Z1"
    manager.stop()


# --- A3: analog publish interval + deadband ------------------------------

def test_analog_deadband_and_interval_suppress_noise(bus, tags, project, tmp_path):
    manager, client = make_manager(bus, tags, project, tmp_path, enabled=True,
                                    publish_interval_s=100.0, default_deadband=5.0)
    fake_time = [0.0]
    manager._clock = lambda: fake_time[0]
    connect(manager, client)

    assert manager._should_publish_analog("Meas.L1", 100.0) is True   # first value always publishes
    assert manager._should_publish_analog("Meas.L1", 101.0) is False  # interval not elapsed
    fake_time[0] += 200.0
    assert manager._should_publish_analog("Meas.L1", 101.0) is False  # interval elapsed, but under deadband
    assert manager._should_publish_analog("Meas.L1", 200.0) is True   # interval elapsed AND over deadband
    manager.stop()


def test_bool_tags_are_never_throttled_by_the_analog_filter(bus, tags, project, tmp_path):
    manager, client = make_manager(bus, tags, project, tmp_path, enabled=True, publish_interval_s=1000.0)
    connect(manager, client)
    for _ in range(3):
        tags.update_tag("DI1", not tags.get_value("DI1"))
    assert _wait_until(lambda: sum(1 for t, _p, _r in client.published if t == "epw/TESTUNIT/tag/DI1/state") >= 3)
    manager.stop()


# --- Home Assistant discovery (best-effort) ------------------------------

def test_home_assistant_discovery_published_once_per_tag(bus, tags, project, tmp_path):
    manager, client = make_manager(bus, tags, project, tmp_path, enabled=True)
    connect(manager, client)
    tags.update_tag("DI1", True)
    tags.update_tag("DI1", False)
    assert _wait_until(lambda: any(t.startswith("homeassistant/binary_sensor/") for t, _p, _r in client.published))
    discovery_msgs = [(t, p, r) for t, p, r in client.published if t.startswith("homeassistant/")]
    di1_msgs = [m for m in discovery_msgs if "DI1" in m[0]]
    assert len(di1_msgs) == 1, "discovery config must be published once per tag, not on every value change"
    assert di1_msgs[0][2] is True  # retained
    payload = json.loads(di1_msgs[0][1])
    assert payload["state_topic"] == "epw/TESTUNIT/tag/DI1/state"
    manager.stop()


# --- project_manager get/set round trip ----------------------------------

def test_project_manager_mqtt_config_defaults_and_round_trip(tmp_path):
    pm = ProjectManager(project_file=str(tmp_path / "project.json"))
    pm.load_project()
    cfg = pm.get_mqtt_config()
    assert cfg["enabled"] is False
    assert cfg["link_in"] == []

    cfg["enabled"] = True
    cfg["host"] = "192.168.1.10"
    cfg["link_in"] = [{"topic": "a/b", "tag": "Link.X.InY", "type": "BOOL", "stale_after_s": 10}]
    pm.set_mqtt_config(cfg)
    pm.save_project()

    pm2 = ProjectManager(project_file=pm.project_file)
    pm2.load_project()
    reloaded = pm2.get_mqtt_config()
    assert reloaded["enabled"] is True
    assert reloaded["host"] == "192.168.1.10"
    assert reloaded["link_in"] == [{"topic": "a/b", "tag": "Link.X.InY", "type": "BOOL", "stale_after_s": 10}]


def test_set_mqtt_config_defensively_strips_a_password_key(tmp_path):
    pm = ProjectManager(project_file=str(tmp_path / "project.json"))
    pm.load_project()
    pm.set_mqtt_config({"enabled": True, "password": "leaked"})
    pm.save_project()
    with open(pm.project_file, encoding="utf-8") as f:
        raw = json.load(f)
    assert "password" not in raw["mqtt"]
