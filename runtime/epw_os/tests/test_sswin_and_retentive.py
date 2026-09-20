"""The two gaps the logic-execution task deliberately left open (task "co
mamy do roboty", p. 2):

  * SSWIN.* - the catalog names the intrusion system as ONE alarm panel,
    this controller's model is per ZONE. core/sswin_signals.py is where
    that translation is decided; these tests pin the decisions.
  * retentive internal signals (MR./MWR.) - Logic Studio only ever stored
    and exported the flag, saying outright that making the value survive
    a restart is EPW-OS's job. Now it does.
"""
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core import project_format as pf
from epw_os.core.access_manager import AccessLevel
from epw_os.core.epw_core import EPWCore
from epw_os.core.logic_runtime import SystemSignalSource, TagIOProvider
from epw_os.core.sswin_signals import UNSERVED_SIGNALS, SswinSignalSource
from epw_os.tests import _logic_program


# --- a stand-in intrusion system --------------------------------------------

class FakeIntrusion:
    """Only what SswinSignalSource reads: zones with states, lines with
    violated/fault/state flags, alarm memory, countdowns."""

    def __init__(self, zones=None, lines=None, modes=None):
        self.zones = zones or {}          # zone_id -> state
        self.modes = modes or {}          # zone_id -> ArmMode.*, default FULL
        self.lines = lines or {}          # line_id -> {"violated", "fault", "state"}
        self.memory = {}                  # zone_id -> {"active", "first_cause_line_id"}
        self.countdowns = {}              # zone_id -> seconds
        self.calls = []                   # (command, zone_id, actor)
        self.arm_succeeds = True

    def get_zones(self):
        return [{"id": zone_id} for zone_id in self.zones]

    def get_zone_state(self, zone_id):
        return self.zones.get(zone_id)

    def get_lines(self):
        return [{"id": line_id} for line_id in self.lines]

    def is_line_violated_now(self, line_id):
        return bool(self.lines.get(line_id, {}).get("violated"))

    def is_line_fault(self, line_id):
        return bool(self.lines.get(line_id, {}).get("fault"))

    def get_line_state(self, line_id):
        return self.lines.get(line_id, {}).get("state", "SECURE")

    def get_alarm_memory(self, zone_id):
        return dict(self.memory.get(zone_id, {"active": False, "first_cause_line_id": None}))

    def get_countdown_remaining(self, zone_id):
        return self.countdowns.get(zone_id, 0)

    class _ArmResult:
        def __init__(self, success):
            self.success = success
            self.reason = "" if success else "a line is violated"

    def get_zone_arm_mode(self, zone_id):
        return self.modes.get(zone_id, "FULL")

    def arm_zone(self, zone_id, actor, level=None, mode="FULL", user=None):
        self.calls.append(("arm", zone_id, actor) if mode == "FULL" else ("arm_night", zone_id, actor))
        if self.arm_succeeds:
            self.modes[zone_id] = mode
        return self._ArmResult(self.arm_succeeds)

    def disarm_zone(self, zone_id, actor, level=None, user=None):
        self.calls.append(("disarm", zone_id, actor))
        return True

    def clear_alarm_memory(self, zone_id, actor, level=None, user=None):
        self.calls.append(("reset", zone_id, actor))
        return True


def _source(**kwargs):
    return SswinSignalSource(FakeIntrusion(**kwargs))


# --- what "the system is armed" means ---------------------------------------

def test_armed_means_every_zone_armed_not_merely_one():
    """Deliberately stricter than the status indicator's own aggregate: a
    schematic that runs "while the building is armed" must not see ARMED
    while half the building is open."""
    all_armed = _source(zones={"Z1": "ARMED", "Z2": "ARMED"})
    assert all_armed.read("SSWIN.ARMED") is True
    assert all_armed.read("SSWIN.ARMED_PARTIAL") is False

    half = _source(zones={"Z1": "ARMED", "Z2": "DISARMED"})
    assert half.read("SSWIN.ARMED") is False
    assert half.read("SSWIN.ARMED_PARTIAL") is True
    assert half.read("SSWIN.DISARMED") is False


def test_a_site_with_no_zones_is_neither_armed_nor_disarmed():
    empty = _source(zones={})
    assert empty.read("SSWIN.ARMED") is False
    assert empty.read("SSWIN.DISARMED") is False
    assert empty.read("SSWIN.READY_TO_ARM") is False


def test_one_zone_in_alarm_is_the_system_in_alarm():
    source = _source(zones={"Z1": "DISARMED", "Z2": "ALARM"})
    assert source.read("SSWIN.ALARM_ACTIVE") is True
    assert source.read("SSWIN.ARMED") is False


def test_a_countdown_reports_the_longest_one_running():
    source = SswinSignalSource(FakeIntrusion(zones={"Z1": "EXIT_DELAY", "Z2": "ARMED"}))
    source.intrusion_manager.countdowns = {"Z1": 17, "Z2": 0}
    assert source.read("SSWIN.EXIT_DELAY") is True
    assert source.read("SSWIN.ENTRY_DELAY") is False
    assert source.read("SSWIN.DELAY_REMAINING") == 17.0


def test_readiness_counts_every_line_that_would_block_an_arm():
    ready = _source(zones={"Z1": "DISARMED"}, lines={"L1": {}})
    assert ready.read("SSWIN.READY_TO_ARM") is True

    violated = _source(zones={"Z1": "DISARMED"}, lines={"L1": {"violated": True}})
    assert violated.read("SSWIN.READY_TO_ARM") is False

    faulty = _source(zones={"Z1": "DISARMED"}, lines={"L1": {"fault": True}})
    assert faulty.read("SSWIN.READY_TO_ARM") is False


def test_tamper_is_sabotage_only_not_every_line_fault():
    """The catalog's own wording: case, wire, short. An open circuit is a
    line FAULT, which is its own signal."""
    shorted = _source(zones={"Z1": "ARMED"}, lines={"L1": {"state": "SHORT", "fault": True}})
    assert shorted.read("SSWIN.TAMPER") is True
    assert shorted.read("SSWIN.FAULT") is True

    broken = _source(zones={"Z1": "ARMED"}, lines={"L1": {"state": "FAULT_OPEN", "fault": True}})
    assert broken.read("SSWIN.TAMPER") is False
    assert broken.read("SSWIN.FAULT") is True


def test_the_latch_outlives_the_alarm_it_came_from():
    source = SswinSignalSource(FakeIntrusion(zones={"Z1": "ALARM"}))
    source.intrusion_manager.memory = {"Z1": {"active": True, "first_cause_line_id": "L7"}}
    # While the alarm is still on, ALARM_ACTIVE is what says so.
    assert source.read("SSWIN.ALARM_ACTIVE") is True
    assert source.read("SSWIN.ALARM_LATCHED") is False
    assert source.read("SSWIN.ALARM_MEMORY") is True

    source.intrusion_manager.zones["Z1"] = "DISARMED"
    assert source.read("SSWIN.ALARM_ACTIVE") is False
    assert source.read("SSWIN.ALARM_LATCHED") is True
    assert source.read("SSWIN.LAST_TRIGGER") == 7.0


def test_the_violated_line_count_is_a_number_logic_can_compare():
    source = _source(zones={"Z1": "ARMED"},
                     lines={"L1": {"violated": True}, "L2": {"violated": True}, "L3": {}})
    assert source.read("SSWIN.ACTIVE_COUNT") == 2.0


def test_what_this_controller_does_not_have_is_not_invented():
    source = _source(zones={"Z1": "ARMED"})
    for signal in UNSERVED_SIGNALS:
        assert source.read(signal) is None, signal
        assert source.serves(signal) is False


def test_a_controller_without_the_intrusion_module_reads_safe_values():
    source = SswinSignalSource(None)
    assert source.read("SSWIN.ARMED") is False
    assert source.read("SSWIN.ALARM_ACTIVE") is False
    assert source.read("SSWIN.DELAY_REMAINING") == 0.0
    assert source.execute("SSWIN.CMD_ARM", actor="LOGIC") is False


def test_the_module_can_be_switched_on_while_the_controller_runs():
    """EPWCore passes a callable, because feature configuration replaces
    the manager object without a restart."""
    holder = {"manager": None}
    source = SswinSignalSource(lambda: holder["manager"])
    assert source.read("SSWIN.ARMED") is False

    holder["manager"] = FakeIntrusion(zones={"Z1": "ARMED"})
    assert source.read("SSWIN.ARMED") is True


# --- commands ----------------------------------------------------------------

def test_a_command_applies_to_every_zone():
    source = _source(zones={"Z1": "DISARMED", "Z2": "DISARMED"})
    assert source.execute("SSWIN.CMD_ARM", actor="LOGIC") is True
    assert source.intrusion_manager.calls == [("arm", "Z1", "LOGIC"), ("arm", "Z2", "LOGIC")]


def test_a_refused_arm_is_reported_not_swallowed():
    source = _source(zones={"Z1": "DISARMED"})
    source.intrusion_manager.arm_succeeds = False
    assert source.execute("SSWIN.CMD_ARM", actor="LOGIC") is False


# --- the write path: rising edge and the block's own access level ------------

def _provider(intrusion, access_manager=None, levels=None):
    io = TagIOProvider(tag_manager=None, access_manager=access_manager,
                       system_signals=SystemSignalSource(sswin=SswinSignalSource(intrusion)))
    io.command_levels = levels or {}
    return io


class FakeAccess:
    def __init__(self, level):
        self.level = level

    def has_access(self, required):
        order = AccessLevel._ORDER
        return order.index(self.level) >= order.index(required)


def test_a_command_fires_once_per_rising_edge_not_every_scan():
    intrusion = FakeIntrusion(zones={"Z1": "DISARMED"})
    io = _provider(intrusion)

    for _ in range(5):                       # a block holding it true
        io.write_system_signal("SSWIN.CMD_ARM", True)
    assert len(intrusion.calls) == 1

    io.write_system_signal("SSWIN.CMD_ARM", False)
    io.write_system_signal("SSWIN.CMD_ARM", True)
    assert len(intrusion.calls) == 2


def test_a_command_block_demanding_a_level_is_refused_without_it():
    intrusion = FakeIntrusion(zones={"Z1": "ARMED"})
    io = _provider(intrusion, access_manager=FakeAccess(AccessLevel.USER),
                   levels={"SSWIN.CMD_DISARM": "Engineer"})

    io.write_system_signal("SSWIN.CMD_DISARM", True)
    assert intrusion.calls == []


def test_the_same_command_runs_once_the_level_is_held():
    intrusion = FakeIntrusion(zones={"Z1": "ARMED"})
    access = FakeAccess(AccessLevel.USER)
    io = _provider(intrusion, access_manager=access, levels={"SSWIN.CMD_DISARM": "Engineer"})

    io.write_system_signal("SSWIN.CMD_DISARM", True)
    io.write_system_signal("SSWIN.CMD_DISARM", False)
    access.level = AccessLevel.ENGINEER
    io.write_system_signal("SSWIN.CMD_DISARM", True)

    assert intrusion.calls == [("disarm", "Z1", "LOGIC")]


def test_a_gated_command_on_a_controller_that_cannot_tell_who_is_present_is_refused():
    intrusion = FakeIntrusion(zones={"Z1": "ARMED"})
    io = _provider(intrusion, access_manager=None, levels={"SSWIN.CMD_DISARM": "Operator"})
    io.write_system_signal("SSWIN.CMD_DISARM", True)
    assert intrusion.calls == []


# --- retentive internal signals ----------------------------------------------

def _retentive_program(names_retentive=(("KEEP", True), ("PLAIN", False))):
    """A program whose internal-signal REGISTRY declares the given
    signals, with a plain DI -> DO chain as its logic.

    Deliberately no virtual.output writing them: a block driving a signal
    would overwrite it on the very first scan after a restart, which is
    correct behaviour but would hide the thing under test here - whether
    the stored value is put back BEFORE that first scan. Which signals
    are retentive is a fact about the registry (shared/logic/
    internal_bits.py), not about which blocks happen to use them."""
    source = _logic_program.make_block("input.di", Address="ELA1.DI.1")
    sink = _logic_program.make_block("output.do", Address="ADA1.DO.1")
    _logic_program.connect(source, sink)
    internal_bits = [{"name": name, "type": "BOOL", "retentive": retentive}
                     for name, retentive in names_retentive]
    return _logic_program.export([source, sink], internal_bits=internal_bits)


def _project(directory: Path, logic_runtime) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    project = pf.new_project("Retentive")
    project.modules = ["intrusion"]
    project.cards = [pf.Card(id="ELA1", model="ELA", channel_kinds={"DI": 2}, modbus_unit_id=1),
                     pf.Card(id="ADA1", model="ADA", channel_kinds={"DO": 2}, modbus_unit_id=2)]
    project.points = [pf.Point(address="ELA1.DI.1"), pf.Point(address="ELA1.DI.2"),
                      pf.Point(address="ADA1.DO.1")]
    project.logic_runtime = logic_runtime
    path = directory / "projekt.epw"
    pf.save_project(project, path)
    return path


@pytest.fixture
def started(tmp_path, db):
    cores = []

    def _start(logic_runtime, subdir="site"):
        instance = EPWCore()
        instance.project_manager.project_file = str(_project(tmp_path / subdir, logic_runtime))
        instance.startup()
        cores.append(instance)
        return instance

    yield _start
    for instance in cores:
        if instance.is_running:
            instance.shutdown()


def test_only_the_signals_the_program_calls_retentive_are_kept(started):
    core = started(_retentive_program())
    assert core.logic_engine.retentive_ids() == frozenset({"MR.KEEP"})


def test_a_retentive_signal_comes_back_after_a_restart(started, tmp_path):
    core = started(_retentive_program())
    core.logic_engine._io.write_internal("MR.KEEP", True)
    core.logic_engine._io.write_internal("M.PLAIN", True)
    core.shutdown()                      # an orderly stop flushes them

    stored = core.project_manager.get_retentive_signals()
    assert stored == {"MR.KEEP": True}, stored

    restarted = started(_retentive_program(), subdir="site")   # same project directory
    assert restarted.logic_engine._io.read_internal("MR.KEEP") is True
    # A non-retentive signal starts from its own default, as always.
    assert restarted.logic_engine._io.read_internal("M.PLAIN", None) is None


def test_a_value_left_by_a_program_that_no_longer_declares_it_is_not_resurrected(started, tmp_path):
    core = started(_retentive_program())
    core.logic_engine._io.write_internal("MR.KEEP", True)
    core.shutdown()
    assert core.project_manager.get_retentive_signals() == {"MR.KEEP": True}

    # The engineer clears the retentive flag and reinstalls.
    restarted = started(_retentive_program((("KEEP", False),)), subdir="site")
    assert restarted.logic_engine.retentive_ids() == frozenset()
    assert restarted.logic_engine._io.read_internal("M.KEEP", None) is None
