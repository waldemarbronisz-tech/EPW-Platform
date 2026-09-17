"""epw_os/gui/synoptic/net_resolver.py - the runtime's port of the editor's
NetResolver.ts: the editor's own test cases (net-resolver.test.ts), the
terminal placement rules, and the runtime's live-feedback source rule."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from epw_os.core.apparatus import Apparatus  # noqa: E402
from epw_os.gui.synoptic import net_resolver as nr  # noqa: E402
from epw_os.gui.synoptic.geometry import load_geometry  # noqa: E402
from epw_os.gui.synoptic.screen_state import ObjectPresentation  # noqa: E402

GEOMETRY = load_geometry().geometry


def wire(id_, points, **over):
    conn = {"id": id_, "points": [{"x": x, "y": y} for x, y in points], "medium": "ELECTRICAL", "style": "NORMAL"}
    conn.update(over)
    return conn


def device(id_, x, y, **over):
    obj = {"id": id_, "type": "electrical.circuit_breaker", "x": x, "y": y, "rotation": 0, "scaleX": 1, "scaleY": 1,
           "width": 40, "height": 40}
    obj.update(over)
    return obj


def ids(net):
    return sorted(net.connection_ids)


# --- the editor's own cases ---------------------------------------------------------

def test_two_wires_sharing_an_endpoint_form_one_net():
    nets = nr.resolve_nets([wire("A", [(0, 0), (32, 0)]), wire("B", [(32, 0), (32, 32)])], [], GEOMETRY)
    assert len(nets) == 1 and ids(nets[0]) == ["A", "B"]


def test_two_wires_with_no_shared_point_form_two_nets():
    nets = nr.resolve_nets([wire("A", [(0, 0), (32, 0)]), wire("B", [(192, 192), (224, 192)])], [], GEOMETRY)
    assert len(nets) == 2


def test_a_wire_ending_on_the_middle_of_a_busbar_joins_it():
    nets = nr.resolve_nets([wire("BUS", [(0, 0), (320, 0)], style="BUS"), wire("TAP", [(160, 0), (160, 64)])], [], GEOMETRY)
    assert len(nets) == 1 and ids(nets[0]) == ["BUS", "TAP"]


def test_five_taps_on_one_busbar_are_one_net_and_a_b_c_join_transitively():
    bus = wire("BUS", [(0, 0), (320, 0)], style="BUS")
    taps = [wire(f"T{i}", [(64 * i, 0), (64 * i, 48)]) for i in range(5)]
    nets = nr.resolve_nets([bus] + taps, [], GEOMETRY)
    assert len(nets) == 1 and len(nets[0].connection_ids) == 6
    chain = [wire("A", [(0, 0), (32, 0)]), wire("B", [(32, 0), (64, 0)]), wire("C", [(64, 0), (96, 0)])]
    assert ids(nr.resolve_nets(chain, [], GEOMETRY)[0]) == ["A", "B", "C"]


def test_an_empty_connection_list_gives_no_nets_even_with_terminals():
    assert nr.resolve_nets([], [device("Q1", 0, 0)], GEOMETRY) == []


def test_junction_dots_where_three_branches_meet_but_not_at_a_bend():
    tee = [wire("A", [(0, 0), (64, 0)]), wire("B", [(32, 0), (32, 48)])]
    assert nr.junction_points(tee, [], GEOMETRY) == [(32, 0)]
    bend = [wire("A", [(0, 0), (32, 0), (32, 32)])]
    assert nr.junction_points(bend, [], GEOMETRY) == []
    # two segments plus a terminal at the same node
    q1 = device("Q1", 12, 0)            # IN terminal at (12 + 20, 0) = (32, 0)
    assert nr.junction_points([wire("A", [(0, 0), (64, 0)])], [q1], GEOMETRY) == [(32, 0)]


# --- terminals -----------------------------------------------------------------------

def test_terminals_sit_on_the_side_the_registry_says_scaled_and_rotated_with_the_object():
    q1 = device("Q1", 100, 200)
    terminals = {t.terminal_id: (t.x, t.y, t.medium) for t in nr.world_terminals([q1], GEOMETRY)}
    assert terminals == {"IN": (120.0, 200.0, "ELECTRICAL"), "OUT": (120.0, 240.0, "ELECTRICAL")}
    scaled = device("Q1", 100, 200, scaleX=2, scaleY=2)
    assert {t.terminal_id: (t.x, t.y) for t in nr.world_terminals([scaled], GEOMETRY)}["OUT"] == (140.0, 280.0)
    rotated = device("Q1", 100, 200, rotation=90)
    out = {t.terminal_id: (round(t.x), round(t.y)) for t in nr.world_terminals([rotated], GEOMETRY)}["OUT"]
    assert out == (60, 220)                                   # (20, 40) rotated 90deg -> (-40, 20)
    valve = device("V1", 0, 0, type="water.ball_valve", width=64, height=64)
    assert {t.medium for t in nr.world_terminals([valve], GEOMETRY)} == {"WATER"}
    assert nr.world_terminals([device("X", 0, 0, type="graphics.rectangle")], GEOMETRY) == []


def test_boundary_point_terminal_follows_its_label_size_and_port_side():
    bp = {"id": "BP", "type": "scada.boundary_point", "x": 0, "y": 0, "designation": "ZASILANIE",
          "boundaryDirection": "SOURCE", "boundaryPortSide": "BOTTOM", "boundaryMedium": "ELECTRICAL"}
    [t] = nr.world_terminals([bp], GEOMETRY)
    width, height = nr.label_frame_size("ZASILANIE", "")
    assert t.terminal_id == "T1" and t.medium == "ELECTRICAL"
    assert t.x == nr.snap_to_grid(0.5 * max(96, min(220, width))) and t.y == nr.snap_to_grid(height)
    assert t.x % 16 == 0 and t.y % 16 == 0
    water = dict(bp, boundaryMedium="WATER", boundaryPortSide="LEFT")
    [t] = nr.world_terminals([water], GEOMETRY)
    assert t.medium == "WATER" and t.x == 0


# --- live state ------------------------------------------------------------------------

def _presentations(closed_ids):
    def presentation_for(obj):
        apparatus = Apparatus(id=obj.get("deviceId"), behavior="SWITCHED", feedback=["DI1.DI.1"], command=["DO1.DO.1"])
        closed = obj.get("deviceId") in closed_ids
        return ObjectPresentation("CLOSED" if closed else "OPEN", {}, apparatus, commandable=True, bound=True,
                                  live=True)
    return presentation_for


def test_a_net_is_active_from_a_source_boundary_point_or_a_closed_breakers_out_terminal():
    source = {"id": "BP", "type": "scada.boundary_point", "x": 0, "y": 0, "designation": "SIEC",
              "boundaryDirection": "SOURCE", "boundaryPortSide": "BOTTOM"}
    [bp_terminal] = nr.world_terminals([source], GEOMETRY)
    q1 = device("Q1", 100, 100, deviceId="KOT_Q1")          # IN (120,100), OUT (120,140)
    feed = wire("FEED", [(bp_terminal.x, bp_terminal.y), (bp_terminal.x, 100), (120, 100)])
    load = wire("LOAD", [(120, 140), (120, 200)])
    objects = [source, q1]

    open_rule = nr.runtime_source_rule(_presentations(closed_ids=set()))
    states = nr.connection_states(nr.resolve_nets([feed, load], objects, GEOMETRY, open_rule))
    assert states == {"FEED": "ACTIVE", "LOAD": "INACTIVE"}

    closed_rule = nr.runtime_source_rule(_presentations(closed_ids={"KOT_Q1"}))
    nets = nr.resolve_nets([feed, load], objects, GEOMETRY, closed_rule)
    assert nr.connection_states(nets) == {"FEED": "ACTIVE", "LOAD": "ACTIVE"}
    assert nr.terminal_net_states(nets)[("Q1", "OUT")] == "ACTIVE"
    assert nr.terminal_net_states(nets)[("Q1", "IN")] == "ACTIVE"

    # Without a rule nothing is ever active; a wire touching nothing is a net of its own.
    plain = nr.resolve_nets([feed, load, wire("ALONE", [(400, 400), (432, 400)])], objects, GEOMETRY)
    assert sorted(n.state for n in plain) == ["INACTIVE", "INACTIVE", "INACTIVE"]


def test_the_runtime_rule_needs_live_feedback_and_ignores_a_sink_boundary_point():
    rule = nr.runtime_source_rule(lambda obj: ObjectPresentation("CLOSED", {}, Apparatus(id="X", behavior="SWITCHED",
                                                                                        command=["DO1.DO.1"]),
                                                                 commandable=True, bound=True, live=False))
    assert rule(device("Q1", 0, 0, deviceId="X"), "OUT") is False          # not live
    assert rule(device("Q1", 0, 0, deviceId="X"), "IN") is False
    assert rule({"id": "S", "type": "scada.boundary_point", "boundaryDirection": "SINK"}, "T1") is False
    assert rule({"id": "T", "type": "site.rainwater_tank2"}, "ODPLYW") is True
    assert rule(None, "OUT") is False
