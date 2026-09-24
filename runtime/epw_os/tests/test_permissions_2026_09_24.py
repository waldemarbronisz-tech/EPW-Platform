"""The owner's decisions of 2026-09-24 on permissions, each one exercised
against the real controller:

  * "wymuszamy bity - ma być zezwolenie": an OUT bit may be forced only
    where the project's registry entry says so (`force_allowed`); an IN
    bit stays forceable as before;
  * "niech mają zezwolenie": a DO point commanded on its own (no
    apparatus over it) carries its own permission bit, and the same
    hard gate refuses switching it ON with the reason naming the bit.
"""
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

os.environ["EPW_TESTING"] = "1"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core import project_format as pf  # noqa: E402
from epw_os.core.apparatus import ApparatusRegistry  # noqa: E402
from epw_os.core.command_manager import CommandState  # noqa: E402
from epw_os.core.events import EventBus  # noqa: E402
from epw_os.core.force_manager import ForceManager  # noqa: E402
from epw_os.core.internal_bit_gate import InternalBitGate  # noqa: E402
from epw_os.core.logic_engine import LogicEngine  # noqa: E402
from epw_os.core.logic_runtime import TagIOProvider  # noqa: E402
from epw_os.core.tag_manager import TagManager  # noqa: E402
from epw_os.tests import _logic_program  # noqa: E402
from shared.logic import internal_bits as bits  # noqa: E402

START = {"name": "START", "type": "BOOL", "retentive": False, "direction": "IN", "panel_level": "Operator",
         "remote_write": False, "description": "Zezwolenie z panelu", "label": "", "category": ""}
ZEZW = {"name": "KMG1_ZEZW", "type": "BOOL", "retentive": False, "direction": "OUT",
        "description": "Blokada od Q1 otwartego", "label": "", "category": ""}
PROBNY = {"name": "PROBNY", "type": "BOOL", "retentive": False, "direction": "OUT", "force_allowed": True,
          "description": "Bit do prób", "label": "", "category": ""}


class _Audit:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))


def _wait(predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def _program():
    start = _logic_program.make_block("virtual.input", Bit="START")
    zezw = _logic_program.make_block("virtual.output", Bit="KMG1_ZEZW")
    probny = _logic_program.make_block("virtual.output", Bit="PROBNY")
    _logic_program.connect(start, zezw)
    _logic_program.connect(start, probny)
    return [start, zezw, probny]


def _engine():
    bus = EventBus()
    tags = TagManager(bus)
    engine = LogicEngine(tags)
    engine.attach_io(TagIOProvider(tags))
    assert engine.load_program_data(_logic_program.export(_program(), internal_bits=[START, ZEZW, PROBNY]))
    return bus, tags, engine


# --- forcing with permission ------------------------------------------------------------------------

def test_the_shared_rule_an_in_bit_always_an_out_bit_only_where_the_designer_said():
    assert bits.force_allowed(START) is True, "an IN bit stays forceable - the owner's rule of 2026-09-22"
    assert bits.force_allowed(ZEZW) is False, "an OUT bit is not forceable by default"
    assert bits.force_allowed(PROBNY) is True
    assert bits.normalize_entry(dict(ZEZW))["force_allowed"] is False
    assert bits.normalize_entry(dict(PROBNY))["force_allowed"] is True
    # the flag is a documented registry field, not a magic string
    assert "force_allowed" in bits.normalize_entry({"name": "X"})


def test_a_force_on_an_out_bit_follows_the_projects_flag_and_the_refusal_says_where_to_allow_it():
    bus, tags, engine = _engine()
    audit = _Audit()
    core = SimpleNamespace(logic_engine=engine, tag_manager=tags, audit_logger=audit,
                           access_manager=SimpleNamespace(level=None), force_manager=None)
    gate = InternalBitGate(core)
    forces = ForceManager(bus, tags, None, audit, ApparatusRegistry(), heartbeat_timeout_s=5.0,
                          internal_bit_direction=engine._io.internal_bit_direction)
    forces._internal_bit_force_allowed = gate.force_allowed
    assert gate.force_allowed("M.PROBNY") is True and gate.force_allowed("M.KMG1_ZEZW") is False
    assert gate.force_allowed("M.START") is True and gate.force_allowed("M.NIE_MA") is False
    # the OUT bit without the flag: refused, and the reason names the Studio column
    ok, reason = forces.force("M.KMG1_ZEZW", True, actor="Engineer")
    assert ok is False
    assert reason == "M.KMG1_ZEZW is an OUT bit and the project does not allow forcing it (Wymuszanie in Studio)"
    assert not forces.is_forced("M.KMG1_ZEZW")
    assert audit.entries[-1][0] == "FORCE_REFUSED" and "M.KMG1_ZEZW" in audit.entries[-1][2]
    # the OUT bit with the flag: pinned, and the scan cannot move it while the force holds
    assert forces.force("M.PROBNY", True, actor="Engineer") == (True, "")
    assert forces.is_forced("M.PROBNY") and forces.kind_of("M.PROBNY") == "BIT"
    assert engine.start()
    try:
        assert _wait(lambda: engine.get_status()["scan_count"] > 3)
        assert tags.get_value("M.PROBNY") is True, "the force owns the bit, START is FALSE"
        assert tags.get_value("M.KMG1_ZEZW") is False, "the unforced OUT bit still follows the logic"
        forces.release("M.PROBNY", actor="Engineer")
        assert _wait(lambda: tags.get_value("M.PROBNY") is False), "released: the logic writes it again"
    finally:
        engine.stop()
    # and the IN bit as before
    assert forces.force("M.START", True, actor="Engineer") == (True, "")


# --- a DO point's own permission --------------------------------------------------------------------

def test_a_do_point_without_an_apparatus_is_gated_by_its_own_permission_bit(tmp_path, db):
    from epw_os.core.epw_core import EPWCore
    from epw_os.i18n import set_language
    directory = tmp_path / "site"
    directory.mkdir()
    project = pf.new_project("Zezwolenie DO")
    project.cards = [pf.Card(id="ADA1", model="ADA01", channel_kinds={"DO": 2}, modbus_unit_id=2)]
    project.points = [pf.Point(address="ADA1.DO.1", permission_bit="M.KMG1_ZEZW"), pf.Point(address="ADA1.DO.2")]
    project.logic_runtime = _logic_program.export(_program(), internal_bits=[START, ZEZW, PROBNY])
    path = directory / "projekt.epw"
    pf.save_project(project, path)
    assert pf.load_project(path).points[0].permission_bit == "M.KMG1_ZEZW", "the file keeps the permission"
    core = EPWCore()
    core.project_manager.project_file = str(path)
    core.startup()
    try:
        set_language("pl")
        assert core.logic_engine.is_running
        assert _wait(lambda: core.logic_engine.get_status()["scan_count"] > 2)
        registry = {p["address"]: p for p in core.project_manager.get_point_registry()}
        assert registry["ADA1.DO.1"]["permission_bit"] == "M.KMG1_ZEZW"
        assert registry["ADA1.DO.2"]["permission_bit"] == ""
        assert core._permission_bit_for("ADA1.DO.1") == ("M.KMG1_ZEZW", "Blokada od Q1 otwartego")
        assert core._permission_bit_for("ADA1.DO.2") is None
        # switching ON is refused with the reason naming the bit ...
        record = core.command_manager.request_command_ex("ADA1.DO.1", "CLOSE", user="Operator")
        assert record.state == CommandState.BLOCKED
        assert record.reason == "ZAMKNIJ ADA1.DO.1 odrzucone: brak zezwolenia M.KMG1_ZEZW (Blokada od Q1 otwartego)"
        # ... switching OFF never is, and the point without a bit is not gated at all
        assert core.command_manager.request_command_ex("ADA1.DO.1", "OPEN", user="Operator").state != CommandState.BLOCKED
        assert core.command_manager.request_command_ex("ADA1.DO.2", "CLOSE", user="Operator").state != CommandState.BLOCKED
        # the logic grants it: START -> KMG1_ZEZW -> ON accepted
        from epw_os.core.access_manager import AccessLevel
        core.access_manager.level = AccessLevel.OPERATOR
        assert core.internal_bits.write("M.START", True, "Operator", "PANEL") == (True, "")
        assert _wait(lambda: core.tag_manager.get_value("M.KMG1_ZEZW") is True)
        record = core.command_manager.request_command_ex("ADA1.DO.1", "CLOSE", user="Operator")
        assert record.state != CommandState.BLOCKED, record.reason
    finally:
        core.shutdown()
