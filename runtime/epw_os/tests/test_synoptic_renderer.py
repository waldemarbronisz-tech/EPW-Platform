"""Punkt 2 / luka 5: the runtime renders the screen Studio embedded in
projekt.epw (epw_os/gui/synoptic/). Checks, from the bottom up:
  - shared/symbols/geometry.json is present, well-formed, and covers the
    editor's whole library (every registry type, every allowed state);
  - the SVG path parser handles the grammar the library uses;
  - screen_state.py picks the right symbol state from feedback tags and
    the apparatus register;
  - the painter draws every symbol/state without an exception and with
    ink on the canvas;
  - the widget draws a real screen, maps a click back to the object under
    it, and the page constructs, reports problems, and sends a command.
"""
import json
import os
import re
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from epw_os.core.apparatus import Apparatus, ApparatusRegistry  # noqa: E402
from epw_os.core.tag_manager import TagManager, TagQuality, TagType  # noqa: E402
from epw_os.gui.synoptic import screen_state  # noqa: E402
from epw_os.gui.synoptic.geometry import (DEFAULT_GEOMETRY_PATH, is_template, load_geometry, resolve_template,
                                          shared_geometry)  # noqa: E402
from epw_os.gui.synoptic.painter import PrimitivePainter, blink_state, mark_dash_march, parse_color  # noqa: E402
from epw_os.gui.synoptic.svg_path import SvgPathError, parse_svg_path  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
REGISTRY_DIR = REPO / "studio" / "synoptic" / "src" / "symbols" / "registry"
EXAMPLES = REPO / "studio" / "synoptic" / "examples"


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def geometry():
    result = load_geometry()
    assert result.ok, result.problem
    return result.geometry


def _registry_types():
    """Every `'<cat>.<name>': {` key in the editor's registry files."""
    types = set()
    for path in REGISTRY_DIR.glob("*.ts"):
        text = path.read_text(encoding="utf-8")
        types.update(re.findall(r"^\s*'([a-z_]+\.[a-z0-9_]+)':\s*\{", text, re.M))
    return types


# --- the geometry file ---------------------------------------------------------------

def test_geometry_file_exists_and_covers_the_whole_library(geometry):
    assert DEFAULT_GEOMETRY_PATH.exists()
    registry = _registry_types()
    assert len(registry) >= 85
    missing = registry - set(geometry.types())
    assert missing == set(), f"re-run studio/synoptic/tools/geometry_export: {sorted(missing)}"
    for symbol_type in geometry.types():
        rec = geometry.symbol(symbol_type)
        if rec.get("generic"):
            continue
        assert not rec.get("export_error"), (symbol_type, rec.get("export_error"))
        for state in rec["allowed_states"] or [rec["default_state"]]:
            assert rec["states"].get(state), (symbol_type, state)


def test_geometry_lookup_falls_back_to_the_default_state_and_reports_generic(geometry):
    assert geometry.state_tree("electrical.circuit_breaker", "CLOSED")
    assert geometry.state_tree("electrical.circuit_breaker", "NO_SUCH_STATE") == geometry.state_tree(
        "electrical.circuit_breaker", geometry.default_state("electrical.circuit_breaker"))
    assert geometry.state_tree("graphics.rectangle", "NORMAL") is None
    assert geometry.state_tree("no.such_symbol", "NORMAL") is None
    assert geometry.reference_size("electrical.circuit_breaker") == (64.0, 64.0)


def test_missing_geometry_file_is_reported_not_fatal(tmp_path):
    result = load_geometry(tmp_path / "nope.json")
    assert not result.ok and "not found" in result.problem
    assert result.geometry.types() == []
    (tmp_path / "bad.json").write_text("{\"format\": \"OTHER\"}", encoding="utf-8")
    assert "EPW_SYMBOL_GEOMETRY" in load_geometry(tmp_path / "bad.json").problem


def test_templates_substitute_object_fields_and_keep_the_symbols_own_default():
    tpl = {"$template": "{{value}} {{unit}}", "$default": "--- "}
    assert resolve_template(tpl, {"value": "12.3", "unit": "°C"}) == "12.3 °C"
    assert resolve_template(tpl, {"value": "", "unit": ""}) == "--- "
    assert resolve_template({"$template": "{{fill}}", "$default": "#c0c0c0"}, {"fill": ""}) == "#c0c0c0"
    assert resolve_template({"$template": "{{fill}}", "$default": "#c0c0c0"}, {"fill": "red"}) == "red"
    size = {"$template": "{{fontSize}}", "$scale": 2.0, "$default": 26}
    assert resolve_template(size, {"fontSize": 0}) == 26
    assert resolve_template(size, {"fontSize": 20}) == 40.0
    assert resolve_template("plain", {}) == "plain"
    assert is_template(tpl) and not is_template("x")


# --- SVG paths -------------------------------------------------------------------------

def test_svg_path_grammar_absolute_relative_curves_and_arcs():
    path = parse_svg_path("M 0 0 L 10 0 l 0 10 H 0 V 0 Z")
    assert path.boundingRect() == QRectF(0, 0, 10, 10)
    curved = parse_svg_path("M0,0 Q10,20 20,0 C 25 -10 35 -10 40 0 S 60 10 60 0 T 80 0 A 5 5 0 0 1 90 0 z")
    assert curved.elementCount() > 6
    assert curved.boundingRect().right() >= 89
    arc = parse_svg_path("M 10 0 A 10 10 0 1 1 -10 0")   # half circle, radius 10
    br = arc.boundingRect()
    assert abs(br.width() - 20) < 0.5 and 9.5 < br.height() < 10.5
    with pytest.raises(SvgPathError):
        parse_svg_path("M 1 2 L 3")
    with pytest.raises(SvgPathError):
        parse_svg_path("10 10 L 0 0")
    assert parse_svg_path("").isEmpty()


def test_every_exported_path_parses(geometry):
    def walk(nodes):
        for node in nodes or []:
            if node.get("primitive") == "path" and isinstance(node.get("data"), str):
                parse_svg_path(node["data"])
            walk(node.get("children"))
    for symbol_type in geometry.types():
        for tree in (geometry.symbol(symbol_type).get("states") or {}).values():
            walk(tree)


# --- screen_state ------------------------------------------------------------------------

class _Tags:
    def __init__(self, values):
        self.values = values

    def get_tag(self, name):
        if name not in self.values:
            return None
        value, quality = self.values[name]

        class _T:
            pass
        t = _T()
        t.value, t.quality = value, TagQuality(quality)
        return t


def _registry_with(*apparatuses):
    registry = ApparatusRegistry()
    registry.set_apparatuses(list(apparatuses))
    return registry


def test_pick_state_uses_each_symbols_own_vocabulary():
    assert screen_state.pick_state("electrical.circuit_breaker", ["OPEN", "CLOSED", "TRIPPED", "FAULT"], True) == "CLOSED"
    assert screen_state.pick_state("electrical.circuit_breaker", ["OPEN", "CLOSED", "TRIPPED", "FAULT"], False) == "OPEN"
    assert screen_state.pick_state("electrical.contactor", ["OFF", "ON", "FAULT"], True) == "ON"
    assert screen_state.pick_state("hvac.fan", ["OFF", "RUNNING", "FAULT"], True) == "RUNNING"
    # A valve's energized contact opens it.
    assert screen_state.pick_state("water.ball_valve", ["CLOSED", "OPENING", "OPEN", "CLOSING", "FAULT"], True) == "OPEN"
    assert screen_state.pick_state("water.ball_valve", ["CLOSED", "OPENING", "OPEN", "CLOSING", "FAULT"], False) == "CLOSED"
    assert screen_state.pick_state("x.y", [], True, "NORMAL") == "NORMAL"
    assert screen_state.pick_state("x.y", ["A", "B"], True, "B") == "B"


def test_present_object_reads_feedback_measured_and_selector(geometry):
    tags = _Tags({"DI1.DI.1": (True, "GOOD"), "DI1.DI.2": (False, "GOOD"), "DI1.DI.3": (True, "COMM_FAILURE"),
                  "AI1.AI.1": (21.456, "GOOD"), "DI1.DI.5": (True, "GOOD")})
    registry = _registry_with(
        Apparatus(id="KOT_Q1", behavior="SWITCHED", feedback=["DI1.DI.1"], command=["DO1.DO.1"]),
        Apparatus(id="KOT_KM1", behavior="SWITCHED", feedback=["DI1.DI.2"], command=["DO1.DO.2"]),
        Apparatus(id="KOT_KM2", behavior="SWITCHED", feedback=["DI1.DI.3"], command=["DO1.DO.3"]),
        Apparatus(id="KOT_ALARM", behavior="SIGNAL", feedback=["DI1.DI.1"]),
        Apparatus(id="MH_T1", behavior="MEASURED", feedback=["AI1.AI.1"]),
        Apparatus(id="KOT_S1", behavior="SELECTOR", feedback=["DI1.DI.2", "DI1.DI.5", "DI1.DI.9"]),
    )
    reader = screen_state.TagReader(tags)

    def obj(t, device):
        return {"id": "o", "type": t, "deviceId": device}

    q1 = screen_state.present_object(obj("electrical.circuit_breaker", "KOT_Q1"), geometry, registry, reader)
    assert (q1.state, q1.commandable, q1.live, q1.bound) == ("CLOSED", True, True, True)
    km1 = screen_state.present_object(obj("electrical.contactor", "KOT_KM1"), geometry, registry, reader)
    assert km1.state == "OFF"
    km2 = screen_state.present_object(obj("electrical.contactor", "KOT_KM2"), geometry, registry, reader)
    assert (km2.state, km2.live) == ("FAULT", False)          # feedback not GOOD
    lamp = screen_state.present_object(obj("electrical.indicator_lamp", "KOT_ALARM"), geometry, registry, reader)
    assert (lamp.state, lamp.commandable) == ("ON", False)
    t1 = screen_state.present_object(obj("measurements.temperature_display", "MH_T1"), geometry, registry, reader,
                                     analog_units={"AI1.AI.1": "°C"})
    assert (t1.fields["value"], t1.fields["unit"], t1.fields["tag"]) == ("21.5", "°C", "AI1.AI.1")
    s1 = screen_state.present_object(obj("electrical.selector_switch", "KOT_S1"), geometry, registry, reader)
    assert s1.state == "CENTER"
    unbound = screen_state.present_object({"id": "o", "type": "electrical.circuit_breaker",
                                           "editor": {"preview_state": "TRIPPED"}}, geometry, registry, reader)
    assert (unbound.state, unbound.bound, unbound.commandable) == ("TRIPPED", False, False)
    stale = screen_state.present_object(obj("electrical.circuit_breaker", "GONE"), geometry, registry, reader)
    assert (stale.state, stale.bound) == (geometry.default_state("electrical.circuit_breaker"), True)


def test_command_for_toggle_follows_the_closed_contact():
    reader = screen_state.TagReader(_Tags({"DI1.DI.1": (True, "GOOD"), "DI1.DI.2": (False, "GOOD"),
                                           "DI1.DI.3": (True, "BAD")}))
    closed = Apparatus(id="A", behavior="SWITCHED", feedback=["DI1.DI.1"], command=["DO1.DO.1"])
    opened = Apparatus(id="B", behavior="SWITCHED", feedback=["DI1.DI.2"], command=["DO1.DO.2"])
    unknown = Apparatus(id="C", behavior="SWITCHED", feedback=["DI1.DI.3"], command=["DO1.DO.3"])
    blind = Apparatus(id="D", behavior="SWITCHED", feedback=[], command=["DO1.DO.4"])
    assert screen_state.command_for_toggle(closed, reader) == "OPEN"
    assert screen_state.command_for_toggle(opened, reader) == "CLOSE"
    assert screen_state.command_for_toggle(unknown, reader) is None
    assert screen_state.command_for_toggle(blind, reader) == "CLOSE"
    assert screen_state.command_for_toggle(Apparatus(id="E", behavior="SIGNAL", feedback=["DI1.DI.1"]), reader) is None


# --- painter ---------------------------------------------------------------------------

def _ink(image: QImage) -> int:
    """1 when anything at all was painted (a byte-wise comparison with a
    blank image of the same size - a 1 px line must count too)."""
    blank = QImage(image.size(), image.format())
    blank.fill(QColor(0, 0, 0, 0))
    if image == blank:
        return 0
    opaque = QImage(image.size(), image.format())
    opaque.fill(QColor("#303030"))
    return 1 if image != opaque else 0


def test_painter_draws_every_symbol_and_state_with_ink(app, geometry):
    fields = {"text": "T", "designation": "-Q1", "name": "N", "tag": "ELA1.DI.1", "value": "1.0", "unit": "V"}
    for symbol_type in geometry.types():
        rec = geometry.symbol(symbol_type)
        if rec.get("generic"):
            continue
        w, h = geometry.reference_size(symbol_type)
        for state, tree in rec["states"].items():
            image = QImage(int(w) + 64, int(h) + 64, QImage.Format.Format_ARGB32)
            image.fill(QColor(0, 0, 0, 0))
            painter = QPainter(image)
            painter.translate(32, 32)
            pp = PrimitivePainter(painter, fields=fields)
            pp.draw_tree(tree)
            painter.end()
            assert pp.warnings == [], (symbol_type, state, pp.warnings)
            assert _ink(image) > 0, (symbol_type, state)


def test_painter_primitives_and_colours():
    assert parse_color("rgba(255, 0, 0, 0.5)").alpha() == 128
    assert parse_color("transparent").alpha() == 0
    assert parse_color("#2c3e50").name() == "#2c3e50"
    assert parse_color("no-such-colour", "#000000").name() == "#000000"
    assert parse_color(None) is None
    image = QImage(100, 100, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    pp = PrimitivePainter(painter, fields={"fill": "", "text": "Hi"})
    pp.draw_tree([
        {"primitive": "group", "x": 10, "y": 10, "rotation": 45, "children": [
            {"primitive": "rect", "width": 20, "height": 20, "fill": {"$template": "{{fill}}", "$default": "#00ff00"},
             "cornerRadius": 3},
            {"primitive": "ellipse", "x": 50, "y": 50, "radiusX": 10, "radiusY": 5, "stroke": "black", "dash": [4, 2]},
            {"primitive": "wedge", "x": 70, "y": 20, "radius": 10, "angle": 90, "fill": "blue"},
            {"primitive": "arc", "x": 70, "y": 60, "innerRadius": 5, "outerRadius": 10, "angle": 180, "stroke": "red"},
            {"primitive": "line", "points": [0, 80, 80, 80, 80, 90], "closed": True, "fill": "gray"},
            {"primitive": "text", "text": {"$template": "{{text}}", "$default": ""}, "fontSize": 12, "align": "center",
             "width": 60, "verticalAlign": "middle", "height": 20, "fontStyle": "bold italic", "textDecoration": "underline"},
            {"primitive": "path", "data": "M 0 0 L 5 5 Q 10 0 15 5 Z", "fill": "pink"},
            {"primitive": "hologram"},
        ]},
    ])
    painter.end()
    assert _ink(image) > 0
    assert pp.warnings == ["unsupported primitive 'hologram'"]


def test_blink_and_dash_march_directives():
    blink = {"type": "blink", "trigger_state": "BLINK", "half_period_ms": 500}
    assert blink_state(blink, "BLINK", 0) == "ON"
    assert blink_state(blink, "BLINK", 600) == "OFF"
    assert blink_state(blink, "ON", 600) == "ON"
    assert blink_state(None, "BLINK", 600) == "BLINK"
    march = {"type": "dash_march", "trigger_state": "LIVE", "rate_px_per_sec": 30}
    tree = [{"primitive": "group", "children": [{"primitive": "line", "points": [0, 0, 1, 1], "dash": [4, 2]}]}]
    tagged = mark_dash_march(tree, march, "LIVE")
    assert tagged[0]["children"][0]["_dash_march"] == 30
    assert "_dash_march" not in tree[0]["children"][0]
    assert mark_dash_march(tree, march, "DEAD") is tree


# --- widget + page ---------------------------------------------------------------------

def _screen(objects, devices=(), **extra):
    doc = {"format": "EPW_SYNOPTIC", "schema_version": 2, "project": {"name": "S"},
           "canvas": {"width": 800, "height": 600, "background": "#00CFCF"},
           "objects": objects, "devices": list(devices)}
    doc.update(extra)
    return doc


def _obj(id_, type_, x, y, **kw):
    base = {"id": id_, "type": type_, "category": "X", "x": x, "y": y, "rotation": 0, "scaleX": 1, "scaleY": 1,
            "visible": True, "locked": False, "layer": 1, "tag": "", "description": "", "color": "", "fill": "",
            "border": "", "text": "", "font": "", "fontSize": 13, "tooltip": "", "width": 64, "height": 64,
            "customProperties": {}}
    base.update(kw)
    return base


def _live_tag_manager():
    from epw_os.core.events import EventBus
    tm = TagManager(EventBus())
    tm.add_tag("DI1.DI.1", True, TagType.BOOL, source="HARDWARE")
    tm.add_tag("AI1.AI.1", 42.0, TagType.REAL, source="HARDWARE")
    return tm


def test_widget_renders_a_screen_and_maps_clicks_to_objects(app):
    from epw_os.gui.synoptic.screen_widget import SynopticScreenWidget
    registry = _registry_with(Apparatus(id="KOT_Q1", behavior="SWITCHED", feedback=["DI1.DI.1"], command=["DO1.DO.1"]),
                              Apparatus(id="MH_T1", behavior="MEASURED", feedback=["AI1.AI.1"]))
    widget = SynopticScreenWidget()
    widget.resize(800, 600)
    widget.set_sources(_live_tag_manager(), registry, {"AI1.AI.1": "°C"})
    widget.set_screen(_screen(
        [_obj("q1", "electrical.circuit_breaker", 100, 100, deviceId="KOT_Q1", designation="-Q1", name="Main"),
         _obj("rot", "electrical.contactor", 400, 100, rotation=90, scaleX=2, scaleY=2),
         _obj("t1", "measurements.temperature_display", 100, 300, deviceId="MH_T1", width=120, height=40),
         _obj("box", "graphics.rectangle", 300, 300, fill="#ff0000", text="Hello"),
         _obj("stale", "old.symbol", 500, 400)],
        devices=[{"id": "KOT_Q1", "designation": "-Q1", "name": "Main", "behavior": "SWITCHED", "kind": "breaker"},
                 {"id": "MH_T1", "designation": "-T1", "name": "Temp", "behavior": "MEASURED", "kind": "sensor"}],
        connections=[{"id": "w", "points": [{"x": 0, "y": 500}, {"x": 800, "y": 500}], "medium": "ELECTRICAL",
                      "style": "BUS", "state": "LIVE"}],
        frames=[{"id": "f", "x": 20, "y": 20, "width": 300, "height": 200, "title": "Kotlownia",
                 "titlePosition": "TOP_LEFT", "variant": "BUILDING"}],
        walls=[{"id": "wl", "from": {"x": 600, "y": 20}, "to": {"x": 780, "y": 20}, "thickness": 12}],
        meters=[{"id": "m", "x": 500, "y": 200, "width": 200, "fontSize": 13, "title": "Pomiary",
                 "rows": [{"device": "MH_T1", "label": "", "manualValue": "", "manualUnit": ""},
                          {"device": "", "label": "Manual", "manualValue": "7", "manualUnit": "bar"}]}],
        signalPanels=[{"id": "sp", "x": 500, "y": 350, "width": 150, "fontSize": 13, "title": "",
                       "rows": [{"device": "KOT_Q1", "label": "", "manualState": "OFF"},
                                {"device": "", "label": "Fixed", "manualState": "ALARM"}]}],
        groupCommands=[{"id": "g", "x": 20, "y": 520, "width": 160, "label": "Start", "command": "CLOSE", "deviceIds": []}],
        setpointPanels=[{"id": "s", "x": 200, "y": 520, "width": 160, "fontSize": 13, "rows": [{"device": "MH_T1", "label": "Sp"}]}],
    ))
    assert widget.has_screen and widget.load_error is None
    assert widget.document.warnings == []
    image = widget.grab().toImage()
    assert image.width() == 800
    assert _ink(image) > 0
    # The canvas fills the widget's width: a canvas pixel must be the canvas colour.
    t = widget.view_transform()
    canvas_pt = t.map(QPointF(700, 550))
    assert image.pixelColor(int(canvas_pt.x()), int(canvas_pt.y())).name() == "#00cfcf"

    # Click mapping through the same transform, including a rotated+scaled object.
    assert widget.object_at(t.map(QPointF(132, 132)))["id"] == "q1"
    assert widget.object_at(t.map(QPointF(101, 101)))["id"] == "q1"
    assert widget.object_at(t.map(QPointF(90, 90))) is None        # outside q1, inside the frame only
    assert widget.object_at(t.map(QPointF(400 - 64, 100 + 64)))["id"] == "rot"   # rotated 90deg, scaled 2x: spans x[272,400] y[100,228]
    assert widget.object_at(t.map(QPointF(410, 110))) is None
    pres = widget.presentation_for(widget.object_at(t.map(QPointF(132, 132))))
    assert pres.state == "CLOSED" and pres.commandable
    widget.shutdown()


def test_widget_reports_a_refused_document_and_an_empty_project(app):
    from epw_os.gui.synoptic.screen_widget import SynopticScreenWidget
    widget = SynopticScreenWidget()
    widget.set_screen({"format": "WRONG"})
    assert not widget.has_screen and "EPW Synoptic" in widget.load_error
    widget.set_screen({})
    assert not widget.has_screen and widget.load_error is None
    assert widget.object_at(QPointF(1, 1)) is None
    widget.grab()  # paints the "no screen" background without a document
    widget.shutdown()


@pytest.mark.parametrize("name", ["GOSPODARKA_WODNA", "ENTRY_GATE_LIBRARY_TEST", "STATEFUL_SYMBOLS", "LIBRARY_TEST"])
def test_widget_renders_the_editors_example_screens(app, name):
    from epw_os.gui.synoptic.screen_widget import SynopticScreenWidget
    doc = json.loads((EXAMPLES / f"{name}.epwsyn").read_text(encoding="utf-8"))
    widget = SynopticScreenWidget()
    widget.resize(1000, 700)
    widget.set_screen(doc)
    assert widget.has_screen, widget.load_error
    assert _ink(widget.grab().toImage()) > 0
    widget.shutdown()


class _ProjectManager:
    def __init__(self, screens):
        self._screens = screens

    def get_embedded_screens(self):
        return dict(self._screens)

    def get_analog_points(self):
        return [{"tag": "AI1.AI.1", "unit": "°C"}]


class _Access:
    def __init__(self, allowed=True):
        self.allowed = allowed

    def has_access(self, level):
        return self.allowed


class _Commands:
    def __init__(self, permitted=True):
        self.permitted = permitted
        self.calls = []

    def request_command(self, target, action, user="Operator"):
        self.calls.append((target, action))
        return (True, []) if self.permitted else (False, ["interlock"])


def test_page_shows_why_when_there_is_nothing_to_draw(app):
    from epw_os.gui.synoptic.page_synoptic import PageSynoptic
    page = PageSynoptic(_live_tag_manager(), project_manager=_ProjectManager({}), access_manager=_Access())
    assert page.status_label.isVisibleTo(page) and page.status_label.text()
    page.shutdown()
    page = PageSynoptic(_live_tag_manager(), project_manager=_ProjectManager({"format": "WRONG"}), access_manager=_Access())
    assert "EPW Synoptic" in page.status_label.text()
    page.shutdown()
    page = PageSynoptic(_live_tag_manager(), project_manager=_ProjectManager(_screen([])), access_manager=_Access())
    assert page.status_label.text() == "" and not page.status_label.isVisibleTo(page)
    page.shutdown()


def test_page_sends_a_command_for_a_clicked_switched_symbol(app, monkeypatch):
    from epw_os.gui.synoptic.page_synoptic import PageSynoptic
    registry = _registry_with(Apparatus(id="KOT_Q1", behavior="SWITCHED", feedback=["DI1.DI.1"], command=["DO1.DO.1"]))
    commands = _Commands()
    screens = _screen([_obj("q1", "electrical.circuit_breaker", 100, 100, deviceId="KOT_Q1")],
                      devices=[{"id": "KOT_Q1", "designation": "-Q1", "name": "Q1", "behavior": "SWITCHED", "kind": "b"}])
    page = PageSynoptic(_live_tag_manager(), project_manager=_ProjectManager(screens), apparatus_registry=registry,
                        access_manager=_Access(True), command_manager=commands)
    confirmations = []
    monkeypatch.setattr(page, "confirm_command", lambda apparatus, action, pos=None: confirmations.append(action) or True)
    obj = page.screen.document.project.objects[0]
    page._on_object_clicked(obj, page.screen.presentation_for(obj), None)
    assert confirmations == ["OPEN"]                 # DI1.DI.1 is True -> it is closed -> the click opens it
    assert commands.calls == [("KOT_Q1", "OPEN")]

    # Without Operator access nothing is sent.
    page.access_manager = _Access(False)
    page._on_object_clicked(obj, page.screen.presentation_for(obj), None)
    assert commands.calls == [("KOT_Q1", "OPEN")]

    # A rejected command is reported, not raised.
    page.access_manager = _Access(True)
    commands.permitted = False
    warned = []
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warned.append(a[2]) or QMessageBox.StandardButton.Ok)
    page._on_object_clicked(obj, page.screen.presentation_for(obj), None)
    assert warned and "interlock" in warned[0]
    page.shutdown()


# --- nets on the widget (port of NetResolver.ts) --------------------------------------

def test_widget_colours_wires_by_net_and_draws_junctions(app):
    from epw_os.gui.synoptic.screen_widget import (COLOR_DE_ENERGIZED, COLOR_ENERGIZED, SynopticScreenWidget,
                                                   wire_color)
    registry = _registry_with(Apparatus(id="KOT_Q1", behavior="SWITCHED", feedback=["DI1.DI.1"], command=["DO1.DO.1"]))
    tm = _live_tag_manager()                                   # DI1.DI.1 is True -> Q1 closed
    widget = SynopticScreenWidget()
    widget.resize(800, 600)
    widget.set_sources(tm, registry)
    source = {"id": "BP", "type": "scada.boundary_point", "x": 96, "y": 0, "designation": "SIEC", "category": "X",
              "boundaryDirection": "SOURCE", "boundaryPortSide": "BOTTOM", "width": 96, "height": 51}
    q1 = _obj("q1", "electrical.circuit_breaker", 96, 160, deviceId="KOT_Q1")   # IN (128,160) OUT (128,224)
    doc = _screen(
        [source, q1],
        devices=[{"id": "KOT_Q1", "designation": "-Q1", "name": "Q1", "behavior": "SWITCHED", "kind": "b"}],
        connections=[{"id": "FEED", "points": [{"x": 144, "y": 48}, {"x": 144, "y": 96}, {"x": 128, "y": 96},
                                                {"x": 128, "y": 160}], "medium": "ELECTRICAL", "style": "NORMAL"},
                     {"id": "LOAD", "points": [{"x": 128, "y": 224}, {"x": 128, "y": 400}], "medium": "ELECTRICAL",
                      "style": "NORMAL"},
                     {"id": "TAP", "points": [{"x": 128, "y": 300}, {"x": 300, "y": 300}], "medium": "ELECTRICAL",
                      "style": "NORMAL"},
                     {"id": "ALONE", "points": [{"x": 600, "y": 500}, {"x": 700, "y": 500}], "medium": "WATER",
                      "style": "NORMAL"}])
    widget.set_screen(doc)
    from epw_os.gui.synoptic import net_resolver as nr
    [bp_terminal] = nr.world_terminals([source], widget._geometry_result.geometry)
    assert (bp_terminal.x, bp_terminal.y) == (144.0, 48.0)     # the fixture's FEED starts on it
    widget.resolve_now()                                       # what a paint does first
    assert widget.connection_state("FEED") == "ACTIVE"
    assert widget.connection_state("LOAD") == "ACTIVE"        # Q1 is closed: its OUT feeds the load
    assert widget.connection_state("TAP") == "ACTIVE"         # taps the load wire mid-segment
    assert widget.connection_state("ALONE") == "INACTIVE"
    assert widget.object_on_live_net(q1) is True
    assert (128, 300) in widget._junctions                    # TAP meets LOAD: three branches
    assert wire_color("ELECTRICAL", True) == COLOR_ENERGIZED and wire_color("ELECTRICAL", False) == COLOR_DE_ENERGIZED

    # Open the breaker: the load side goes dead, the feed stays live.
    tm.update_tag("DI1.DI.1", False)
    widget.grab()
    assert widget.connection_state("FEED") == "ACTIVE" and widget.connection_state("LOAD") == "INACTIVE"
    assert widget.connection_state("TAP") == "INACTIVE"
    widget.shutdown()


def test_water_symbols_have_a_live_net_variant_and_the_fan_rotates(geometry):
    from epw_os.gui.synoptic.painter import animation_rotation
    inactive = geometry.state_tree("water.ball_valve", "OPEN")
    active = geometry.state_tree("water.ball_valve", "OPEN", net_active=True)
    assert inactive and active and json.dumps(inactive) != json.dumps(active)
    assert geometry.state_tree("electrical.circuit_breaker", "CLOSED", net_active=True) == \
        geometry.state_tree("electrical.circuit_breaker", "CLOSED")
    fan = geometry.symbol("hvac.fan")
    assert fan["animation"]["type"] == "rotate"

    def rotating(nodes):
        for n in nodes or []:
            if n.get("$animate_rotation") or rotating(n.get("children")):
                return True
        return False
    assert rotating(fan["states"]["RUNNING"]) and not rotating(fan["states"]["OFF"])
    assert animation_rotation(fan["animation"], "RUNNING", 500) == 90.0 or animation_rotation(fan["animation"], "RUNNING", 500) > 0
    assert animation_rotation(fan["animation"], "OFF", 500) == 0.0
    assert all(t.get("side") in ("TOP", "BOTTOM", "LEFT", "RIGHT") for t in geometry.symbol("electrical.contactor")["terminals"])
