"""Etap 1 of the signal register: SYS lifecycle/configuration, RT.LOGIC,
RT.SYNOPTIC, MODE and REQ.MODE served from the controller's own state
(core/runtime_state_signals.py, core/operating_mode.py,
core/synoptic_status.py). Every bit is checked to CHANGE with its
source - a bit that never moves is a facade (rule Z1)."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core import operating_mode as modes  # noqa: E402
from epw_os.core.access_manager import AccessLevel  # noqa: E402
from epw_os.core.events import EventBus  # noqa: E402
from epw_os.core.health_manager import HealthManager, SubsystemState  # noqa: E402
from epw_os.core.logic_engine import LogicEngine  # noqa: E402
from epw_os.core.logic_runtime import SystemSignalSource, TagIOProvider  # noqa: E402
from epw_os.core.operating_mode import OperatingModeManager  # noqa: E402
from epw_os.core.runtime_state_signals import RuntimeStateSignals  # noqa: E402
from epw_os.core.synoptic_status import evaluate_screens  # noqa: E402
from epw_os.core.tag_manager import TagManager  # noqa: E402
from epw_os.tests import _logic_program  # noqa: E402
from shared.logic.engine.io_provider import pulse_signal_value  # noqa: E402


class _Audit:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))

    def types(self):
        return [e[0] for e in self.entries]


class _Access:
    def __init__(self, level=AccessLevel.OPERATOR):
        self.level = level

    def has_access(self, required):
        return AccessLevel._ORDER.index(self.level) >= AccessLevel._ORDER.index(required)


def _core(**over):
    bus = EventBus()
    core = SimpleNamespace(lifecycle="STARTING", health_manager=HealthManager(bus),
                           project_manager=SimpleNamespace(is_epw_project=lambda: True, load_error=None, rolled_back=None),
                           logic_engine=None, synoptic_status={}, operating_mode=None,
                           training_mode=SimpleNamespace(active=False), tag_manager=None,
                           time_sync_monitor=SimpleNamespace(status="SYNCED"))
    for key, value in over.items():
        setattr(core, key, value)
    return core


def _source(core):
    signals = RuntimeStateSignals(core)
    SystemSignalSource(sources=[signals])       # attaches the scan flags
    return signals


# --- SYS: the lifecycle, the health, the project ------------------------------

def test_the_lifecycle_bits_follow_startup_and_shutdown():
    core = _core()
    s = _source(core)
    assert (s.read("SYS.STARTING"), s.read("SYS.RUNNING"), s.read("SYS.STOPPING")) == (True, False, False)
    core.lifecycle = "RUNNING"
    assert (s.read("SYS.STARTING"), s.read("SYS.RUNNING"), s.read("SYS.STOPPING")) == (False, True, False)
    core.lifecycle = "STOPPING"
    assert (s.read("SYS.STARTING"), s.read("SYS.RUNNING"), s.read("SYS.STOPPING")) == (False, False, True)


def test_degraded_and_fail_come_from_the_subsystem_health():
    core = _core()
    s = _source(core)
    assert s.read("SYS.DEGRADED") is False and s.read("SYS.FAIL") is False and s.read("MODE.DEGRADED") is False
    core.health_manager.update_subsystem("DRIVERS", SubsystemState.DEGRADED)
    assert s.read("SYS.DEGRADED") is True and s.read("MODE.DEGRADED") is True and s.read("SYS.FAIL") is False
    core.health_manager.update_subsystem("LOGIC_RUNTIME", SubsystemState.FAULT)
    assert s.read("SYS.FAIL") is True
    core.health_manager.update_subsystem("DRIVERS", SubsystemState.RUNNING)
    core.health_manager.update_subsystem("LOGIC_RUNTIME", SubsystemState.RUNNING)
    assert s.read("SYS.DEGRADED") is False and s.read("SYS.FAIL") is False


def test_config_ok_and_fault_come_from_the_project_load_result():
    core = _core()
    s = _source(core)
    assert s.read("SYS.CONFIG_OK") is True and s.read("SYS.CONFIG_FAULT") is False
    core.project_manager.load_error = {"key": "startup.project_refused", "text": "bad", "params": {}}
    assert s.read("SYS.CONFIG_OK") is False and s.read("SYS.CONFIG_FAULT") is True
    core.project_manager.load_error = None
    core.project_manager.rolled_back = {"path": "p"}
    assert s.read("SYS.CONFIG_FAULT") is True
    core.project_manager = SimpleNamespace(is_epw_project=lambda: False, load_error=None, rolled_back=None)
    assert s.read("SYS.CONFIG_OK") is False and s.read("SYS.CONFIG_FAULT") is False   # no project: neither
    core.time_sync_monitor.status = "UNSYNCED"
    assert s.read("SYS.TIME_SYNC_FAULT") is True
    core.time_sync_monitor.status = "SYNCED"
    assert s.read("SYS.TIME_SYNC_FAULT") is False


def test_the_clocks_and_the_heartbeat_are_square_waves_of_the_named_period():
    for signal, period in (("SYS.CLOCK_100MS", 100), ("SYS.CLOCK_1S", 1000), ("SYS.CLOCK_10S", 10000),
                           ("SYS.CLOCK_1MIN", 60000), ("SYS.HEARTBEAT", 2000)):
        assert pulse_signal_value(signal, 0) is True
        assert pulse_signal_value(signal, period // 2 - 1) is True
        assert pulse_signal_value(signal, period // 2) is False
        assert pulse_signal_value(signal, period - 1) is False
        assert pulse_signal_value(signal, period) is True
    # The same table the controller reads through its system source.
    assert SystemSignalSource().read("SYS.CLOCK_10S", now_ms=4999) is True
    assert SystemSignalSource().read("SYS.CLOCK_10S", now_ms=5001) is False


# --- RT.LOGIC: a real engine ----------------------------------------------------

def test_rt_logic_follows_a_real_engine_from_empty_to_running_to_broken():
    engine = LogicEngine(TagManager(EventBus()))
    core = _core(logic_engine=engine)
    s = _source(core)
    assert not any(s.read(k) for k in ("RT.LOGIC.READY", "RT.LOGIC.RUNNING", "RT.LOGIC.FAIL",
                                       "RT.LOGIC.PROJECT_OK", "RT.LOGIC.PROJECT_FAULT"))
    assert engine.load_program_data(_logic_program.di_to_do()) is True
    assert s.read("RT.LOGIC.READY") is True and s.read("RT.LOGIC.PROJECT_OK") is True
    assert s.read("RT.LOGIC.RUNNING") is False and s.read("RT.LOGIC.FAIL") is False

    engine.attach_io(TagIOProvider(engine.tag_manager))
    engine.tag_manager.add_tag("ELA01.DI.1", False, __import__("epw_os.core.tag_manager", fromlist=["TagType"]).TagType.BOOL)
    engine.tag_manager.add_tag("ADA01.DO.1", False, __import__("epw_os.core.tag_manager", fromlist=["TagType"]).TagType.BOOL)
    assert engine.start() is True
    assert s.read("RT.LOGIC.RUNNING") is True
    engine.stop()
    assert s.read("RT.LOGIC.RUNNING") is False

    assert engine.load_program_data({"format": "EPW_RUNTIME_LOGIC", "blocks": [{"id": "b"}]}) is False
    assert s.read("RT.LOGIC.FAIL") is True and s.read("RT.LOGIC.PROJECT_FAULT") is True
    assert s.read("RT.LOGIC.READY") is False and s.read("RT.LOGIC.PROJECT_OK") is False


def test_overrun_is_the_scan_loops_own_flag():
    core = _core()
    signals = RuntimeStateSignals(core)
    system = SystemSignalSource(sources=[signals])
    assert system.read("RT.LOGIC.OVERRUN") is False
    system.scan_overrun = True
    assert system.read("RT.LOGIC.OVERRUN") is True and system.read("SYS.SCAN_OVERRUN") is True


# --- RT.SYNOPTIC: the screens verdict ------------------------------------------

def _screens(objects=(), devices=(), **extra):
    doc = {"format": "EPW_SYNOPTIC", "schema_version": 2, "project": {"name": "S"},
           "canvas": {"width": 800, "height": 600}, "objects": list(objects), "devices": list(devices)}
    doc.update(extra)
    return doc


def test_the_screens_verdict_ready_binding_fault_and_fail():
    assert evaluate_screens(None) == {"present": False, "ready": False, "fail": False, "binding_fault": False, "problems": []}
    ok = evaluate_screens(_screens([{"id": "o1", "type": "x", "deviceId": "KOT_Q1"}], [{"id": "KOT_Q1", "behavior": "SWITCHED"}]),
                          apparatus_ids=["KOT_Q1"])
    assert ok["ready"] and not ok["fail"] and not ok["binding_fault"]
    dangling = evaluate_screens(_screens([{"id": "o1", "type": "x", "deviceId": "KOT_Q9"}], [{"id": "KOT_Q1", "behavior": "SWITCHED"}]),
                                apparatus_ids=["KOT_Q1"])
    assert dangling["ready"] and dangling["binding_fault"] and "KOT_Q9" in dangling["problems"][0]
    broken = evaluate_screens({"format": "EPW_SYNOPTIC", "schema_version": 2, "project": {"name": "S"}, "objects": []})
    assert broken["fail"] and not broken["ready"] and "canvas" in broken["problems"][0].lower()

    core = _core(synoptic_status=dangling)
    s = _source(core)
    assert s.read("RT.SYNOPTIC.READY") is True and s.read("RT.SYNOPTIC.BINDING_FAULT") is True and s.read("RT.SYNOPTIC.FAIL") is False


# --- MODE / REQ.MODE ------------------------------------------------------------

def test_the_operating_mode_is_one_at_a_time_persisted_and_gated_by_level():
    audit = _Audit()
    saved = []
    manager = OperatingModeManager(EventBus(), audit, load=lambda: "MANUAL", save=saved.append)
    assert manager.mode == "MANUAL"                                # restored from the state file
    core = _core(operating_mode=manager, tag_manager=SimpleNamespace(mode="LIVE MODE"))
    s = _source(core)
    assert s.read("MODE.MANUAL") is True and s.read("MODE.NORMAL") is False and s.read("MODE.SERVICE") is False

    assert manager.set_mode("SERVICE", actor="API:Operator", level=AccessLevel.OPERATOR) == (
        False, "SERVICE requires Engineer, API:Operator is Operator")
    assert manager.mode == "MANUAL" and audit.types()[-1] == "OPERATING_MODE_REFUSED"
    assert manager.set_mode("SERVICE", actor="API:Engineer", level=AccessLevel.ENGINEER) == (True, "")
    assert saved == ["SERVICE"] and audit.entries[-1][2] == "MANUAL -> SERVICE"
    assert s.read("MODE.SERVICE") is True and s.read("MODE.MANUAL") is False
    assert manager.set_mode("SPACE", actor="x")[0] is False
    core.training_mode.active = True
    core.tag_manager.mode = "SIMULATION MODE"
    assert s.read("MODE.TRAINING") is True and s.read("MODE.SIMULATION") is True


def test_a_logic_request_changes_the_mode_at_the_panels_level_and_a_refusal_is_audited():
    audit = _Audit()
    manager = OperatingModeManager(EventBus(), audit)
    access = _Access(AccessLevel.OPERATOR)
    core = _core(operating_mode=manager)
    signals = RuntimeStateSignals(core)
    io = TagIOProvider(TagManager(EventBus()), access_manager=access, audit_logger=audit,
                       system_signals=SystemSignalSource(access_manager=access, sources=[signals]))
    io.command_levels = {"REQ.MODE.MANUAL": "Brak", "REQ.MODE.SERVICE": "Brak"}

    io.write_system_signal("REQ.MODE.MANUAL", True)                # rising edge: executed
    assert manager.mode == "MANUAL" and io.read_system_signal("MODE.MANUAL") is True
    io.write_system_signal("REQ.MODE.MANUAL", True)                # held: not re-issued
    io.write_system_signal("REQ.MODE.MANUAL", False)

    io.write_system_signal("REQ.MODE.SERVICE", True)               # the block asked for nothing, the mode asks Engineer
    assert manager.mode == "MANUAL"
    refused = [e for e in audit.entries if e[0] == "LOGIC_REQUEST_REFUSED"]
    assert refused and "REQ.MODE.SERVICE" in refused[-1][2] and "Engineer" in refused[-1][2] and refused[-1][3] is False

    access.level = AccessLevel.ENGINEER
    io.write_system_signal("REQ.MODE.SERVICE", False)
    io.write_system_signal("REQ.MODE.SERVICE", True)
    assert manager.mode == "SERVICE"

    io.write_system_signal("REQ.MODE.NOWHERE", True)               # not a request anyone serves
    assert any("REQ.MODE.NOWHERE" in e[2] for e in audit.entries if e[0] == "LOGIC_REQUEST_REFUSED")


# --- the catalogue and the register ---------------------------------------------

def test_every_new_signal_is_in_the_catalogue_with_the_right_direction_and_served():
    from shared.logic import system_signals
    ids = {s["id"]: s for s in system_signals.raw_signals()}
    reads = ["SYS.STARTING", "SYS.RUNNING", "SYS.STOPPING", "SYS.DEGRADED", "SYS.FAIL", "SYS.CONFIG_OK", "SYS.CONFIG_FAULT",
             "SYS.TIME_SYNC_FAULT", "SYS.HEARTBEAT", "SYS.CLOCK_100MS", "SYS.CLOCK_1S", "SYS.CLOCK_10S", "SYS.CLOCK_1MIN",
             "RT.LOGIC.READY", "RT.LOGIC.RUNNING", "RT.LOGIC.FAIL", "RT.LOGIC.OVERRUN", "RT.LOGIC.PROJECT_OK",
             "RT.LOGIC.PROJECT_FAULT", "RT.SYNOPTIC.READY", "RT.SYNOPTIC.FAIL", "RT.SYNOPTIC.BINDING_FAULT"]
    reads += [f"MODE.{m}" for m in modes.MODES] + ["MODE.TRAINING", "MODE.SIMULATION", "MODE.DEGRADED"]
    for signal_id in reads:
        assert ids[signal_id]["source"] == "runtime" and ids[signal_id]["runtime"] == "served", signal_id
    for mode in modes.MODES:
        assert ids[f"REQ.MODE.{mode}"]["source"] == "logic"
    assert "MODE.LOCAL" not in ids and "MODE.REMOTE" not in ids     # no source here - not faked
    assert tuple(int(x) for x in system_signals.get_catalog_version().split(".")) >= (2, 2, 0)

    # Everything the catalogue says is served, the controller's source really answers.
    signals = RuntimeStateSignals(_core(operating_mode=OperatingModeManager()))
    for signal_id in reads:
        if not signal_id.startswith("SYS.CLOCK") and signal_id != "SYS.HEARTBEAT":
            assert signals.serves(signal_id), signal_id


def test_the_register_status_now_counts_these_rows_as_served():
    from shared.docs import generate_signal_register_status as gen
    from shared.logic import system_signals
    catalog = {gen._normalise(s["id"]): s for s in system_signals.raw_signals()}
    for row in ("SYS.RUNNING", "SYS.CLOCK_1MIN", "RT.LOGIC.OVERRUN", "RT.SYNOPTIC.BINDING_FAULT", "MODE.MAINTENANCE",
                "REQ.MODE.EMERGENCY"):
        assert gen.classify({"ID / Wzorzec": row, "Grupa": "X"}, catalog, {})[0] == "w katalogu i obsłużony", row
    assert gen.classify({"ID / Wzorzec": "MODE.LOCAL", "Grupa": "MODES"}, catalog, {})[0] == "do zrobienia"


# --- the panel's side: REST, the same table -------------------------------------

def test_rest_changes_the_mode_at_the_level_the_mode_demands(tmp_path):
    import hashlib
    import json
    import secrets
    from fastapi.testclient import TestClient
    from epw_os.backend.api import app
    from epw_os.core.api_auth import ApiAuth

    audit = _Audit()
    tokens = {"Operator": secrets.token_hex(16), "Engineer": secrets.token_hex(16)}
    config = tmp_path / "api_tokens.local.json"
    config.write_text(json.dumps({"token_hashes": {
        level: hashlib.sha256(t.encode("utf-8")).hexdigest() for level, t in tokens.items()}}))
    core = SimpleNamespace(operating_mode=OperatingModeManager(EventBus(), audit), audit_logger=audit,
                           api_auth=ApiAuth(config_path=str(config)))
    app.state.core = core
    http = TestClient(app)

    listing = http.get("/api/v1/mode").json()
    assert listing["mode"] == "NORMAL" and listing["required_level"]["SERVICE"] == "Engineer" and "MANUAL" in listing["modes"]
    assert http.post("/api/v1/mode", json={"mode": "MANUAL"}).status_code == 401           # no token
    operator = {"Authorization": f"Bearer {tokens['Operator']}"}
    assert http.post("/api/v1/mode", json={"mode": "MANUAL"}, headers=operator).json() == {"mode": "MANUAL"}
    assert http.post("/api/v1/mode", json={"mode": "SERVICE"}, headers=operator).status_code == 401
    assert core.operating_mode.mode == "MANUAL"
    engineer = {"Authorization": f"Bearer {tokens['Engineer']}"}
    assert http.post("/api/v1/mode", json={"mode": "SERVICE"}, headers=engineer).json() == {"mode": "SERVICE"}
    assert http.post("/api/v1/mode", json={"mode": "WARP"}, headers=engineer).status_code == 400
    assert "OPERATING_MODE_CHANGED" in audit.types() and "API_AUTH_FAILED" in audit.types()
