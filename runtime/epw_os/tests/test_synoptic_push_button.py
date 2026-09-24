"""The synoptic push button on the controller (owner 2026-09-24:
"Przycisk robimy - robota synoptyki, ale w logice też chcę bity"): a
screen object with no apparatus that writes one of the logic's IN bits
through InternalBitGate - TOGGLE flips it, PULSE sets it and clears it
after pulse_ms - and whose cap follows the bit's value. The geometry
file carries the symbol, the widget maps a click on it, the page writes
the bit with the gate's rules (level, audit, a forced bit refuses)."""
import os
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

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from epw_os.core.access_manager import AccessLevel  # noqa: E402
from epw_os.core.apparatus import ApparatusRegistry  # noqa: E402
from epw_os.core.events import EventBus  # noqa: E402
from epw_os.core.force_manager import ForceManager  # noqa: E402
from epw_os.core.internal_bit_gate import InternalBitGate  # noqa: E402
from epw_os.core.logic_engine import LogicEngine  # noqa: E402
from epw_os.core.logic_runtime import TagIOProvider  # noqa: E402
from epw_os.core.tag_manager import TagManager  # noqa: E402
from epw_os.gui.synoptic import screen_state  # noqa: E402
from epw_os.gui.synoptic.geometry import load_geometry  # noqa: E402
from epw_os.tests import _logic_program  # noqa: E402

START = {"name": "START", "type": "BOOL", "retentive": False, "direction": "IN", "panel_level": "Operator",
         "remote_write": False, "description": "Start z panelu", "label": "", "category": ""}
KMG1_ZEZW = {"name": "KMG1_ZEZW", "type": "BOOL", "retentive": False, "direction": "OUT",
             "description": "Blokada od Q1 otwartego", "label": "", "category": ""}


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class _Audit:
    def __init__(self):
        self.entries = []

    def record(self, event_type, actor, detail="", success=True):
        self.entries.append((event_type, actor, detail, success))


def _wait(predicate, timeout=3.0, app=None):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if app is not None:
            app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def _engine():
    """START (IN) -> KMG1_ZEZW (OUT): the logic reads what the button writes."""
    bus = EventBus()
    tags = TagManager(bus)
    engine = LogicEngine(tags)
    engine.attach_io(TagIOProvider(tags))
    source = _logic_program.make_block("virtual.input", Bit="START")
    sink = _logic_program.make_block("virtual.output", Bit="KMG1_ZEZW")
    _logic_program.connect(source, sink)
    assert engine.load_program_data(_logic_program.export([source, sink], internal_bits=[START, KMG1_ZEZW]))
    return bus, tags, engine


def _button(id_="b1", bit="M.START", mode="TOGGLE", pulse_ms=None, x=100, y=100, text="START"):
    obj = {"id": id_, "type": "scada.push_button", "category": "SCADA", "x": x, "y": y, "rotation": 0, "scaleX": 1,
           "scaleY": 1, "visible": True, "locked": False, "layer": 1, "tag": "", "description": "", "color": "",
           "fill": "", "border": "", "text": text, "font": "", "fontSize": 13, "tooltip": "", "width": 150,
           "height": 150, "customProperties": {}, "editor": {"button_mode": mode},
           "bindings": {"command": {"tag": bit}} if bit else {}}
    if pulse_ms is not None:
        obj["editor"]["pulse_ms"] = pulse_ms
    return obj


def _screen(objects):
    return {"format": "EPW_SYNOPTIC", "schema_version": 2, "project": {"name": "S"},
            "canvas": {"width": 800, "height": 600, "background": "#00CFCF"}, "objects": objects, "devices": []}


class _ProjectManager:
    def __init__(self, screens):
        self._screens = screens

    def get_embedded_screens(self):
        return dict(self._screens)

    def get_analog_points(self):
        return []


def _page(tags, engine, level=AccessLevel.OPERATOR, forces=None, objects=None):
    from epw_os.gui.synoptic.page_synoptic import PageSynoptic
    audit = _Audit()
    core = SimpleNamespace(logic_engine=engine, tag_manager=tags, audit_logger=audit,
                           access_manager=SimpleNamespace(level=level, has_access=lambda lvl: True),
                           force_manager=forces)
    gate = InternalBitGate(core)
    page = PageSynoptic(tags, project_manager=_ProjectManager(_screen(objects or [_button()])),
                        apparatus_registry=ApparatusRegistry(), access_manager=core.access_manager,
                        command_manager=None, internal_bits=gate)
    return page, gate, audit


# --- the symbol and its state ------------------------------------------------------------------------

def test_the_geometry_file_carries_the_button_with_both_states_and_a_label_template():
    result = load_geometry()
    assert result.ok, result.problem
    rec = result.geometry.symbol("scada.push_button")
    assert rec and rec["allowed_states"] == ["RELEASED", "PRESSED"] and rec["default_state"] == "RELEASED"
    assert not rec.get("generic") and not rec.get("export_error"), rec.get("warnings")
    for state in ("RELEASED", "PRESSED"):
        assert rec["states"].get(state), state
    texts = [n for n in _walk(rec["states"]["PRESSED"]) if n.get("primitive") == "text"]
    assert texts and any(isinstance(t.get("text"), dict) and "{{text}}" in str(t["text"].get("$template"))
                         for t in texts), "the label under the cap is the object's own text"
    pressed_fills = {n.get("fill") for n in _walk(rec["states"]["PRESSED"]) if n.get("primitive") == "circle"}
    released_fills = {n.get("fill") for n in _walk(rec["states"]["RELEASED"]) if n.get("primitive") == "circle"}
    assert "#00A800" in pressed_fills and "#00A800" not in released_fills, "a pressed cap is the theme's green"


def _walk(node):
    if isinstance(node, dict):
        yield node
        for child in node.get("children") or []:
            yield from _walk(child)
    elif isinstance(node, list):
        for child in node:
            yield from _walk(child)


def test_present_object_reads_the_buttons_bit_and_offers_the_click_even_when_the_bit_is_unreadable():
    result = load_geometry()
    bus, tags, engine = _engine()
    reader = screen_state.TagReader(tags)
    assert screen_state.push_button_bit(_button()) == "M.START"
    assert screen_state.push_button_bit(_button(bit="")) == ""
    assert screen_state.push_button_bit({"type": "electrical.circuit_breaker", "bindings": {"command": {"tag": "M.X"}}}) == ""
    assert screen_state.push_button_mode(_button()) == ("TOGGLE", 0)
    assert screen_state.push_button_mode(_button(mode="PULSE")) == ("PULSE", 500)
    assert screen_state.push_button_mode(_button(mode="PULSE", pulse_ms=80)) == ("PULSE", 80)
    assert screen_state.push_button_mode(_button(mode="PULSE", pulse_ms="oops")) == ("PULSE", 500)
    released = screen_state.present_object(_button(), result.geometry, ApparatusRegistry(), reader)
    assert (released.state, released.commandable, released.bound, released.live, released.bit) == (
        "RELEASED", True, True, True, "M.START")
    tags.update_tag("M.START", True)
    pressed = screen_state.present_object(_button(), result.geometry, ApparatusRegistry(), reader)
    assert (pressed.state, pressed.live) == ("PRESSED", True)
    unknown = screen_state.present_object(_button(bit="M.NIE_MA"), result.geometry, ApparatusRegistry(), reader)
    assert (unknown.state, unknown.commandable, unknown.live, unknown.bit) == ("RELEASED", True, False, "M.NIE_MA")
    plain = screen_state.present_object(_button(bit=""), result.geometry, ApparatusRegistry(), reader)
    assert (plain.commandable, plain.bound, plain.bit) == (False, False, "")
    assert plain.fields["text"] == "START"


# --- the click -----------------------------------------------------------------------------------------

def test_the_widget_maps_a_click_on_a_button_to_the_page(app):
    from epw_os.gui.synoptic.screen_widget import SynopticScreenWidget
    bus, tags, engine = _engine()
    widget = SynopticScreenWidget()
    widget.resize(800, 600)
    widget.set_sources(tags, ApparatusRegistry(), {})
    widget.set_screen(_screen([_button(x=100, y=100), _button(id_="plain", bit="", x=500, y=100)]))
    widget.show()
    app.processEvents()
    clicks = []
    widget.object_clicked.connect(lambda obj, presentation, pos: clicks.append((obj["id"], presentation.bit)))
    obj = widget.document.project.objects[0]
    centre = widget._transform.map(QPoint(100 + 75, 100 + 75))
    assert widget.object_at(centre)["id"] == "b1"
    QTest.mouseClick(widget, Qt.MouseButton.LeftButton, pos=centre)
    assert clicks == [("b1", "M.START")]
    # a button without a bit is not a command
    plain_centre = widget._transform.map(QPoint(500 + 75, 100 + 75))
    assert widget.object_at(plain_centre)["id"] == "plain"
    QTest.mouseClick(widget, Qt.MouseButton.LeftButton, pos=plain_centre)
    assert clicks == [("b1", "M.START")]
    assert obj["id"] == "b1"
    widget.shutdown()


def test_toggle_flips_the_bit_through_the_gate_and_the_logic_reads_it(app):
    bus, tags, engine = _engine()
    page, gate, audit = _page(tags, engine)
    assert engine.start()
    try:
        button = page.screen.document.project.objects[0]
        assert page.screen.presentation_for(button).state == "RELEASED"
        page._on_object_clicked(button, page.screen.presentation_for(button), None)
        assert tags.get_value("M.START") is True
        assert _wait(lambda: tags.get_value("M.KMG1_ZEZW") is True), "the logic read the bit the button wrote"
        assert page.screen.presentation_for(button).state == "PRESSED"
        assert [e[0] for e in audit.entries] == ["INTERNAL_BIT_WRITTEN"]
        assert audit.entries[0][1] == "PANEL:Operator" and "M.START" in audit.entries[0][2]
        page._on_object_clicked(button, page.screen.presentation_for(button), None)
        assert tags.get_value("M.START") is False
        assert _wait(lambda: tags.get_value("M.KMG1_ZEZW") is False)
    finally:
        engine.stop()
        page.shutdown()


def test_pulse_sets_the_bit_and_clears_it_after_its_time(app):
    bus, tags, engine = _engine()
    page, gate, audit = _page(tags, engine, objects=[_button(mode="PULSE", pulse_ms=60)])
    try:
        button = page.screen.document.project.objects[0]
        assert page.press_button(button, "M.START") is True
        assert tags.get_value("M.START") is True
        assert _wait(lambda: tags.get_value("M.START") is False, timeout=2.0, app=app), "cleared after pulse_ms"
        writes = [e for e in audit.entries if e[0] == "INTERNAL_BIT_WRITTEN"]
        assert len(writes) == 2 and "True" in writes[0][2] and "False" in writes[1][2]
    finally:
        page.shutdown()


def test_the_gates_rules_hold_for_the_button_level_forced_bit_out_bit(app, monkeypatch):
    bus, tags, engine = _engine()
    warned = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: warned.append(a[2]) or QMessageBox.StandardButton.Ok))
    # a User at the panel: START needs Operator
    page, gate, audit = _page(tags, engine, level=AccessLevel.USER)
    try:
        button = page.screen.document.project.objects[0]
        assert page.press_button(button, "M.START") is False
        assert tags.get_value("M.START") is False
        assert warned and "M.START" in warned[-1] and "Operator" in warned[-1]
        assert audit.entries[-1][0] == "INTERNAL_BIT_WRITE_REFUSED"
    finally:
        page.shutdown()
    # a forced bit belongs to the force
    forces = ForceManager(bus, tags, None, _Audit(), ApparatusRegistry(), heartbeat_timeout_s=5.0,
                          internal_bit_direction=engine._io.internal_bit_direction)
    assert forces.force("M.START", False, actor="Engineer") == (True, "")
    page, gate, audit = _page(tags, engine, forces=forces)
    try:
        button = page.screen.document.project.objects[0]
        assert page.press_button(button, "M.START") is False and "forced" in warned[-1]
        assert tags.get_value("M.START") is False
    finally:
        page.shutdown()
    forces.release("M.START", actor="Engineer")
    # an OUT bit is never written from outside, a button naming it is refused by the gate
    page, gate, audit = _page(tags, engine, objects=[_button(bit="M.KMG1_ZEZW")])
    try:
        button = page.screen.document.project.objects[0]
        assert page.press_button(button, "M.KMG1_ZEZW") is False
        assert "OUT" in warned[-1] or "not an IN bit" in warned[-1] or "M.KMG1_ZEZW" in warned[-1]
        assert audit.entries[-1][0] == "INTERNAL_BIT_WRITE_REFUSED"
    finally:
        page.shutdown()
    # no gate at all: nothing is written, nothing raised
    from epw_os.gui.synoptic.page_synoptic import PageSynoptic
    page = PageSynoptic(tags, project_manager=_ProjectManager(_screen([_button()])), apparatus_registry=ApparatusRegistry(),
                        access_manager=SimpleNamespace(level=AccessLevel.OPERATOR, has_access=lambda lvl: True))
    try:
        assert page.press_button(page.screen.document.project.objects[0], "M.START") is False
        assert tags.get_value("M.START") is False
    finally:
        page.shutdown()


def test_the_panel_texts_exist_in_both_languages():
    from epw_os.i18n import set_language, tr
    set_language("pl")
    assert tr("pages.synoptic.button_refused_title") == "Przycisk odrzucony"
    assert "M.X" in tr("pages.synoptic.button_refused_text", bit="M.X", reason="r")
    set_language("en")
    assert tr("pages.synoptic.button_refused_title") == "Push button refused"
    assert "M.X" in tr("pages.synoptic.button_refused_text", bit="M.X", reason="r")
    for language in ("pl", "en"):
        text = (_REPO_ROOT / "runtime" / "epw_os" / "help" / language / "mv_synoptic.md").read_text(encoding="utf-8")
        assert "dio_internal_bits" in text and "M.START" in text
