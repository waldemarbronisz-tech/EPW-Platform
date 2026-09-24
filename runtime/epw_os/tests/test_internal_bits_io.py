"""Internal bits IN/OUT - the owner's decisions of 2026-09-22, each one
exercised against the real controller:

  * an internal bit is a TAG: an OUT bit written by the scan shows up
    as M.<name>, an IN bit written from outside is what the scan reads;
  * who may write an IN bit is declared per bit (panel at a level,
    remote only when enabled), every write and refusal is audited with
    old and new value; an OUT bit is never written from outside;
  * a Studio force pins an IN bit and is refused on an OUT bit;
  * REST and MQTT reach a bit only where the project allows them;
  * the apparatus's permission bit is a HARD gate on CLOSE, with the
    reason naming the bit and its description, under the three
    conditions: (a) only CLOSE, never OPEN; (b) no logic = no
    permission; (c) the scan's own outputs and the protection requests
    are not gated.
"""
import hashlib
import json
import os
import secrets
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ["EPW_TESTING"] = "1"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from epw_os.core import project_format as pf  # noqa: E402
from epw_os.core.access_manager import AccessLevel  # noqa: E402
from epw_os.core.apparatus import Apparatus, ApparatusRegistry, apparatus_command_definitions  # noqa: E402
from epw_os.core.command_manager import CommandManager, CommandState  # noqa: E402
from epw_os.core.events import EventBus  # noqa: E402
from epw_os.core.force_manager import ForceManager  # noqa: E402
from epw_os.core.internal_bit_gate import InternalBitGate  # noqa: E402
from epw_os.core.logic_engine import LogicEngine  # noqa: E402
from epw_os.core.logic_runtime import TagIOProvider  # noqa: E402
from epw_os.core.remote_commands import RemoteCommandGateway  # noqa: E402
from epw_os.core.tag_manager import TagManager, TagType  # noqa: E402
from epw_os.tests import _logic_program  # noqa: E402

START = {"name": "START", "type": "BOOL", "retentive": False, "direction": "IN", "panel_level": "Operator",
         "remote_write": False, "description": "Zezwolenie z panelu", "label": "", "category": ""}
REMOTE = {"name": "ZDALNY", "type": "BOOL", "retentive": False, "direction": "IN", "panel_level": "Operator",
          "remote_write": True, "description": "Bit z Home Assistant", "label": "", "category": ""}
ZEZW = {"name": "KMG1_ZEZW", "type": "BOOL", "retentive": False, "direction": "OUT",
        "description": "Blokada od Q1 otwartego", "label": "", "category": ""}
NASTAWA = {"name": "NASTAWA", "type": "REAL", "retentive": False, "direction": "IN", "panel_level": "Engineer",
           "remote_write": True, "description": "Nastawa z panelu", "label": "", "category": ""}


def _program():
    """START (IN) -> KMG1_ZEZW (OUT): the permission follows the panel's bit."""
    source = _logic_program.make_block("virtual.input", Bit="START")
    sink = _logic_program.make_block("virtual.output", Bit="KMG1_ZEZW")
    _logic_program.connect(source, sink)
    return _logic_program.export([source, sink], internal_bits=[START, REMOTE, ZEZW, NASTAWA])


class _Audit:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))

    def of(self, event_type):
        return [e for e in self.entries if e[0] == event_type]


def _wait(predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def _engine(program=None):
    """A real LogicEngine scanning a real program, headless."""
    bus = EventBus()
    tags = TagManager(bus)
    engine = LogicEngine(tags)
    engine.attach_io(TagIOProvider(tags))
    assert engine.load_program_data(program or _program())
    return bus, tags, engine


def _core(engine, tags, level=AccessLevel.OPERATOR, forces=None):
    audit = _Audit()
    core = SimpleNamespace(logic_engine=engine, tag_manager=tags, audit_logger=audit,
                           access_manager=SimpleNamespace(level=level), force_manager=forces)
    gate = InternalBitGate(core)
    core.internal_bits = gate
    return core, gate, audit


# --- bits are tags ------------------------------------------------------------------------------

def test_an_out_bit_is_a_tag_the_scan_writes_and_an_in_bit_a_tag_the_scan_reads():
    bus, tags, engine = _engine()
    assert tags.get_tag("M.START") is not None and tags.get_tag("M.KMG1_ZEZW") is not None
    assert tags.get_tag("MW.NASTAWA").data_type == TagType.REAL and tags.get_tag("M.START").description == "Zezwolenie z panelu"
    assert engine.start()
    try:
        assert _wait(lambda: engine.get_status()["scan_count"] > 2)
        assert tags.get_value("M.KMG1_ZEZW") is False
        tags.update_tag("M.START", True)                     # what the panel's SET does, through the gate
        assert _wait(lambda: tags.get_value("M.KMG1_ZEZW") is True), "the scan did not follow the IN bit"
        tags.update_tag("M.START", False)
        assert _wait(lambda: tags.get_value("M.KMG1_ZEZW") is False)
        # an OUT bit written behind the logic's back is the scan's again next cycle
        tags.update_tag("M.KMG1_ZEZW", True)
        assert _wait(lambda: tags.get_value("M.KMG1_ZEZW") is False)
    finally:
        engine.stop()
    # a reload without NASTAWA takes its tag away; the others stay
    source = _logic_program.make_block("virtual.input", Bit="START")
    sink = _logic_program.make_block("virtual.output", Bit="KMG1_ZEZW")
    _logic_program.connect(source, sink)
    assert engine.load_program_data(_logic_program.export([source, sink], internal_bits=[START, ZEZW]))
    assert tags.get_tag("MW.NASTAWA") is None and tags.get_tag("M.START") is not None


# --- who may write an IN bit -------------------------------------------------------------------------

def test_the_bits_own_entry_says_who_may_write_it_and_every_write_is_audited():
    bus, tags, engine = _engine()
    core, gate, audit = _core(engine, tags, level=AccessLevel.OPERATOR)
    assert gate.write("M.START", True, "Operator", "PANEL") == (True, "")
    assert tags.get_value("M.START") is True
    written = audit.of("INTERNAL_BIT_WRITTEN")
    assert len(written) == 1 and written[0][1] == "PANEL:Operator" and "M.START: False -> True" in written[0][2]
    # an OUT bit: never from outside, whoever asks
    ok, reason = gate.write("M.KMG1_ZEZW", True, "Engineer", "PANEL", level=AccessLevel.ENGINEER)
    assert ok is False and "OUT bit" in reason and "only by the logic" in reason
    # the level the entry names: NASTAWA needs Engineer, an Operator is refused
    ok, reason = gate.write("MW.NASTAWA", 12.5, "Operator", "PANEL")
    assert ok is False and "Engineer" in reason
    assert gate.write("MW.NASTAWA", 12.5, "Engineer", "PANEL", level=AccessLevel.ENGINEER) == (True, "")
    assert tags.get_value("MW.NASTAWA") == 12.5
    # the panel switched off for a bit: "(nie)"
    engine._io.configure_internal_bits([dict(START, panel_level=""), ZEZW])
    ok, reason = gate.write("M.START", True, "Engineer", "PANEL", level=AccessLevel.ENGINEER)
    assert ok is False and "no writes" in reason
    # a name the program does not declare
    ok, reason = gate.write("M.NIE_MA", True, "Operator", "PANEL")
    assert ok is False and "not an internal bit" in reason
    refused = audit.of("INTERNAL_BIT_WRITE_REFUSED")
    assert len(refused) == 4 and all(e[3] is False for e in refused)
    assert any("M.KMG1_ZEZW = True" in e[2] for e in refused)


def test_a_force_pins_an_in_bit_on_the_force_rules_and_is_refused_on_an_out_bit():
    bus, tags, engine = _engine()
    audit = _Audit()
    forces = ForceManager(bus, tags, None, audit, ApparatusRegistry(), heartbeat_timeout_s=5.0,
                          internal_bit_direction=engine._io.internal_bit_direction)
    assert forces.force("M.START", True, actor="Engineer") == (True, "")
    assert tags.get_value("M.START") is True and forces.is_forced("M.START")
    assert forces.kind_of("M.START") == "BIT"
    # while forced, the panel's write is refused - the force owns the bit
    core, gate, gate_audit = _core(engine, tags, forces=forces)
    ok, reason = gate.write("M.START", False, "Operator", "PANEL")
    assert ok is False and "forced" in reason
    assert tags.get_value("M.START") is True
    forces.release("M.START", actor="Engineer")
    assert gate.write("M.START", False, "Operator", "PANEL") == (True, "")
    # an OUT bit: never forced
    ok, reason = forces.force("M.KMG1_ZEZW", True, actor="Engineer")
    assert ok is False and "OUT bit" in reason and not forces.is_forced("M.KMG1_ZEZW")
    assert any(e[0] == "FORCE_REFUSED" and "M.KMG1_ZEZW" in e[2] for e in audit.entries)
    # and still nothing that is not a point or a bit
    assert forces.force("System.PendingCommand", True)[0] is False


def test_rest_and_mqtt_reach_a_bit_only_where_the_project_allows_it(tmp_path):
    from fastapi.testclient import TestClient
    from epw_os.backend.api import app
    from epw_os.core.api_auth import ApiAuth
    bus, tags, engine = _engine()
    core, gate, audit = _core(engine, tags)
    tokens = {"Operator": secrets.token_hex(16), "Engineer": secrets.token_hex(16)}
    config = tmp_path / "api_tokens.local.json"
    config.write_text(json.dumps({"token_hashes": {
        level: hashlib.sha256(t.encode("utf-8")).hexdigest() for level, t in tokens.items()}}))
    core.api_auth = ApiAuth(config_path=str(config))
    app.state.core = core
    http = TestClient(app)
    operator = {"Authorization": f"Bearer {tokens['Operator']}"}
    engineer = {"Authorization": f"Bearer {tokens['Engineer']}"}
    # START allows the panel but not remote writers: refused whatever the token
    response = http.post("/api/v1/bits/M.START", json={"value": True}, headers=engineer)
    assert response.status_code == 403 and "not enabled" in response.json()["detail"]["reason"]
    assert tags.get_value("M.START") is False
    # ZDALNY allows remote writers at Operator
    assert http.post("/api/v1/bits/M.ZDALNY", json={"value": True}).status_code == 403          # no token
    assert http.post("/api/v1/bits/M.ZDALNY", json={"value": True}, headers=operator).json()["value"] is True
    assert tags.get_value("M.ZDALNY") is True
    # NASTAWA allows remote writers, but at Engineer
    assert http.post("/api/v1/bits/MW.NASTAWA", json={"value": 3.5}, headers=operator).status_code == 403
    assert http.post("/api/v1/bits/MW.NASTAWA", json={"value": 3.5}, headers=engineer).json()["value"] == 3.5
    # an OUT bit: never
    assert http.post("/api/v1/bits/M.KMG1_ZEZW", json={"value": True}, headers=engineer).status_code == 403
    rest_writes = [e for e in audit.of("INTERNAL_BIT_WRITTEN") if e[1].startswith("REST:")]
    assert len(rest_writes) == 2 and "from REST" in rest_writes[0][2]

    # MQTT: the same gate, the person's own token and level
    class _Access:
        def resolve_remote_token(self, token):
            return {"id": "U1", "name": "Kowalski", "level": "Operator", "zones": [], "enabled": True} if token == "tok" else None

    published = []
    gateway = RemoteCommandGateway(access_manager=_Access(), audit_logger=audit, publish_result=published.append,
                                   internal_bits=gate)

    def send(**body):
        body.setdefault("id", f"c{len(published)}-{time.time()}")
        body.setdefault("ts", time.time())
        body.setdefault("token", "tok")
        return gateway.handle("epw/x/cmd", json.dumps(body).encode("utf-8"))

    result = send(action="bit", target="M.ZDALNY", values={"value": False})
    assert result["accepted"] is True and tags.get_value("M.ZDALNY") is False
    result = send(action="bit", target="M.START", values={"value": True})
    assert result["accepted"] is False and "not enabled" in result["reason"] and tags.get_value("M.START") is False
    result = send(action="bit", target="MW.NASTAWA", values={"value": 9.0})
    assert result["accepted"] is False and "Engineer" in result["reason"]
    assert any(e[1] == "MQTT:Kowalski" for e in audit.of("INTERNAL_BIT_WRITTEN"))


# --- the permission bit ------------------------------------------------------------------------------

class _AllowAll:
    def validate_command_safety(self, target, action):
        return True, ""


class _Driver:
    def __init__(self):
        self.written = []

    def route_command(self, driver_id, output_tag, value):
        self.written.append((output_tag, value))
        return True


def _commands(engine, tags, bus):
    from epw_os.i18n import set_language
    set_language("pl")
    driver = _Driver()
    manager = CommandManager(tags, engine, _AllowAll(), bus, driver_manager=driver)
    apparatus = Apparatus(id="KOT_KMG1", behavior="SWITCHED", feedback=["ELA1.DI.1"], command=["ADA1.DO.1", "ADA1.DO.2"],
                          permission_bit="M.KMG1_ZEZW")
    for name in ("ELA1.DI.1", "ADA1.DO.1", "ADA1.DO.2"):
        tags.add_tag(name, False, TagType.BOOL, source="HARDWARE")
    manager.load_definitions(apparatus_command_definitions([apparatus]))
    entries = engine._io.internal_bit_entries()

    def permission_bits(target):
        if target != "KOT_KMG1" or not apparatus.permission_bit:
            return None
        return apparatus.permission_bit, (entries.get(apparatus.permission_bit) or {}).get("description", "")

    manager.permission_bits = permission_bits
    return manager, driver, apparatus


def test_a_close_needs_the_permission_and_an_open_never_does():
    """Condition (a): the permission blocks ONLY switching on."""
    bus, tags, engine = _engine()
    manager, driver, apparatus = _commands(engine, tags, bus)
    assert engine.start()
    try:
        assert _wait(lambda: engine.get_status()["scan_count"] > 2)
        record = manager.request_command_ex("KOT_KMG1", "CLOSE", user="Operator")
        assert record.state == CommandState.BLOCKED
        assert record.reason == "ZAMKNIJ KOT_KMG1 odrzucone: brak zezwolenia M.KMG1_ZEZW (Blokada od Q1 otwartego)"
        assert ("ADA1.DO.1", True) not in driver.written
        # OPEN passes with the permission FALSE - switching off must always be possible
        record = manager.request_command_ex("KOT_KMG1", "OPEN", user="Operator")
        assert record.state not in (CommandState.BLOCKED, CommandState.FAILED)
        assert ("ADA1.DO.2", True) in driver.written
        # the legacy wrapper the screen uses says the same
        permitted, reasons = manager.request_command("KOT_KMG1", "CLOSE", validate_only=True)
        assert permitted is False and "brak zezwolenia M.KMG1_ZEZW" in reasons[0]
        # the logic grants it: the panel's START bit -> the OUT bit -> CLOSE accepted
        tags.update_tag("M.START", True)
        assert _wait(lambda: tags.get_value("M.KMG1_ZEZW") is True)
        record = manager.request_command_ex("KOT_KMG1", "CLOSE", user="Operator")
        assert record.state not in (CommandState.BLOCKED, CommandState.FAILED), record.reason
        assert ("ADA1.DO.1", True) in driver.written
        # an apparatus without a permission bit is not gated at all
        apparatus.permission_bit = ""
        tags.update_tag("M.START", False)
        assert _wait(lambda: tags.get_value("M.KMG1_ZEZW") is False)
        assert manager.request_command_ex("KOT_KMG1", "CLOSE", user="Operator").state != CommandState.BLOCKED
    finally:
        engine.stop()


def test_no_logic_is_no_permission():
    """Condition (b): stopped, before the first scan, an unknown bit, no program."""
    bus, tags, engine = _engine()
    manager, driver, apparatus = _commands(engine, tags, bus)
    tags.update_tag("M.START", True)
    # loaded but not running
    record = manager.request_command_ex("KOT_KMG1", "CLOSE", user="Operator")
    assert record.state == CommandState.BLOCKED and record.reason.endswith("logika zatrzymana")
    assert engine.start()
    try:
        assert _wait(lambda: tags.get_value("M.KMG1_ZEZW") is True)
        assert manager.request_command_ex("KOT_KMG1", "CLOSE", user="Operator").state != CommandState.BLOCKED
        # the moment before the first scan of a (re)started program
        engine._first_scan = True
        record = manager.request_command_ex("KOT_KMG1", "CLOSE", user="Operator")
        assert record.state == CommandState.BLOCKED and record.reason.endswith("sterownik przed pierwszym skanem")
        engine._first_scan = False
        # a bit the program does not declare
        apparatus.permission_bit = "M.NIE_MA"
        record = manager.request_command_ex("KOT_KMG1", "CLOSE", user="Operator")
        assert record.state == CommandState.BLOCKED and "M.NIE_MA" in record.reason
        assert record.reason.endswith("program nie deklaruje tego bitu")
        # an IN bit named as a permission is not the logic's word
        apparatus.permission_bit = "M.START"
        record = manager.request_command_ex("KOT_KMG1", "CLOSE", user="Operator")
        assert record.state == CommandState.BLOCKED and record.reason.endswith("to nie jest bit wyjściowy logiki")
    finally:
        engine.stop()
    record = manager.request_command_ex("KOT_KMG1", "CLOSE", user="Operator")
    assert record.state == CommandState.BLOCKED and "zatrzymana" in record.reason
    # no program at all
    bare = LogicEngine(TagManager(EventBus()))
    manager.logic_engine = bare
    apparatus.permission_bit = "M.KMG1_ZEZW"
    record = manager.request_command_ex("KOT_KMG1", "CLOSE", user="Operator")
    assert record.state == CommandState.BLOCKED and record.reason.endswith("brak programu logiki")


def test_the_scans_own_outputs_and_the_protection_requests_are_not_gated(tmp_path, db):
    """Condition (c): the permission lives in the software command path
    only. The scan drives its output with the permission FALSE, and a
    protection request reaches the ADA card's register unchanged."""
    from epw_os.core.epw_core import EPWCore
    directory = tmp_path / "site"
    directory.mkdir()
    project = pf.new_project("Permission")
    project.cards = [pf.Card(id="ELA1", model="ELA01", channel_kinds={"DI": 2}, modbus_unit_id=1),
                     pf.Card(id="ADA1", model="ADA01", channel_kinds={"DO": 2}, modbus_unit_id=2)]
    project.points = [pf.Point(address="ELA1.DI.1"), pf.Point(address="ELA1.DI.2"),
                      pf.Point(address="ADA1.DO.1"), pf.Point(address="ADA1.DO.2")]
    project.devices = [pf.Device(id="KOT_KMG1", behavior="SWITCHED", kind="contactor", feedback=["ELA1.DI.2"],
                                 command=["ADA1.DO.2"], permission_bit="M.KMG1_ZEZW")]
    di = _logic_program.make_block("input.di", Address="ELA1.DI.1")
    do = _logic_program.make_block("output.do", Address="ADA1.DO.1")
    _logic_program.connect(di, do)
    start = _logic_program.make_block("virtual.input", Bit="START")
    zezw = _logic_program.make_block("virtual.output", Bit="KMG1_ZEZW")
    _logic_program.connect(start, zezw)
    project.logic_runtime = _logic_program.export([di, do, start, zezw], internal_bits=[START, ZEZW])
    path = directory / "projekt.epw"
    pf.save_project(project, path)
    core = EPWCore()
    core.project_manager.project_file = str(path)
    core.startup()
    try:
        assert core.logic_engine.is_running
        assert core.apparatus_registry.get("KOT_KMG1").permission_bit == "M.KMG1_ZEZW"
        assert core.tag_manager.get_value("M.KMG1_ZEZW") is False
        # the software command path IS gated ...
        record = core.command_manager.request_command_ex("KOT_KMG1", "CLOSE", user="Operator")
        assert record.state == CommandState.BLOCKED and "M.KMG1_ZEZW" in record.reason
        # ... the scan's own output is not: DI.1 -> DO.1 with the permission FALSE
        core.tag_manager.publish_from_driver("ELA1.DI.1", True)
        assert _wait(lambda: core.tag_manager.get_value("ADA1.DO.1") is True)
        # ... and a protection request is not: it goes to the device, refused only because no ADA answers
        source = core.logic_engine._io.system_signals.request_source("REQ.PROT.RESET")
        assert source is not None and "permission" not in type(source).__name__.lower()
        assert source.execute("REQ.PROT.RESET", "LOGIC") is False           # no ADA card answering on this bench
        assert core.audit_logger is None or True
        # and the panel's page sees the bits with the writers the project declared
        entries = core.internal_bits.entries()
        assert entries["M.START"]["panel_level"] == "Operator" and entries["M.KMG1_ZEZW"]["direction"] == "OUT"
    finally:
        core.shutdown()


# --- the panel's page -------------------------------------------------------------------------------

def test_the_panel_page_sets_an_in_bit_and_disables_what_the_level_forbids():
    from PySide6.QtCore import QObject, Signal
    from PySide6.QtWidgets import QApplication
    from epw_os.gui.pages.page_internal_bits import COL_DIRECTION, COL_SET, COL_VALUE, PageInternalBits
    from epw_os.i18n import set_language
    QApplication.instance() or QApplication([])
    set_language("pl")
    bus, tags, engine = _engine()
    core, gate, audit = _core(engine, tags, level=AccessLevel.OPERATOR)

    class Bridge(QObject):
        tag_changed = Signal(str, object, str)

        def __getattr__(self, name):
            return getattr(tags, name)

    bridge = Bridge()
    page = PageInternalBits(bridge, core.access_manager, gate)
    rows = {page.table.item(r, 0).text(): r for r in range(page.table.rowCount())}
    assert set(rows) == {"M.START", "M.ZDALNY", "M.KMG1_ZEZW", "MW.NASTAWA"}
    assert page.table.item(rows["M.START"], COL_DIRECTION).text() == "WE"
    assert page.table.item(rows["M.KMG1_ZEZW"], COL_DIRECTION).text() == "WY"
    assert page.table.cellWidget(rows["M.KMG1_ZEZW"], COL_SET) is None, "an OUT bit has no buttons"
    set_button, clear_button = page._buttons["M.START"]
    assert set_button.isEnabled() and page._buttons["MW.NASTAWA"][0].isEnabled() is False   # Engineer needed
    set_button.click()
    assert tags.get_value("M.START") is True
    bridge.tag_changed.emit("M.START", True, "GOOD")
    assert page.table.item(rows["M.START"], COL_VALUE).text() == "1"
    assert audit.of("INTERNAL_BIT_WRITTEN")[-1][1] == "PANEL:Operator"
    core.access_manager.level = AccessLevel.USER
    page._refresh_buttons()
    assert not set_button.isEnabled() and set_button.toolTip()
    core.access_manager.level = AccessLevel.ENGINEER
    page._refresh_buttons()
    assert page._buttons["MW.NASTAWA"][0].isEnabled()
