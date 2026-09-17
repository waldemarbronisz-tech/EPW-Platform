"""Which wires and terminals form one net, and whether that net is live -
a port of the editor's project/NetResolver.ts (+ utils/Terminals.ts),
so a wire on the runtime's screen is coloured the way the editor colours
it: by the NET it belongs to, not by a per-wire flag.

Geometry only, no id references: two wires belong to one net when a
vertex of one lies on a segment of the other (a wire tapping a busbar
anywhere along its length joins it); a terminal joins the net whose
wire passes through its world position; terminals at the same point
join each other. A net is ACTIVE when it touches an active source
terminal - the editor's two rules, plus what the runtime knows that the
editor does not: a SWITCHED apparatus's OUT terminal is a source when
its LIVE feedback says it is closed (the editor uses the preview
state).

Terminal positions come from the symbol's registry spec (side TOP/
BOTTOM/LEFT/RIGHT of the object's own box, exported in
shared/symbols/geometry.json), except the boundary point, whose box
depends on its label text - the same estimate the editor uses.
"""
import math
from dataclasses import dataclass, field

GRID_SIZE = 16
FONT_SIZE_BASE = 13
FONT_SIZE_TITLE = 14
_LABEL_FRAME_PADDING_X = 14
_LABEL_FRAME_PADDING_Y = 10
_LABEL_FRAME_LINE_GAP = 4
_BOUNDARY_MIN_WIDTH = 96
_BOUNDARY_MAX_WIDTH = 220


@dataclass(frozen=True)
class WorldTerminal:
    obj_id: str
    terminal_id: str
    x: float
    y: float
    medium: str


@dataclass
class Net:
    id: str
    connection_ids: list
    terminals: list = field(default_factory=list)   # [(obj_id, terminal_id)]
    medium: str = None
    state: str = "INACTIVE"


def snap_to_grid(value: float) -> float:
    return round(value / GRID_SIZE) * GRID_SIZE


def _estimate_text_width(text: str, font_size: float) -> float:
    return len(text or "") * font_size * 0.62


def label_frame_size(title: str, description: str, font_size: float = FONT_SIZE_BASE):
    """LabelFrameSymbol.tsx's getLabelFrameSize()."""
    title_size = round(font_size * FONT_SIZE_TITLE / FONT_SIZE_BASE)
    width = max(_estimate_text_width(title, title_size), _estimate_text_width(description, font_size)) \
        + _LABEL_FRAME_PADDING_X * 2
    height = _LABEL_FRAME_PADDING_Y * 2 + title_size + _LABEL_FRAME_LINE_GAP + font_size
    return width, height


def _side_offset(side: str, width: float, height: float):
    return {"TOP": (width / 2, 0.0), "BOTTOM": (width / 2, height), "LEFT": (0.0, height / 2),
            "RIGHT": (width, height / 2)}.get(side, (width / 2, 0.0))


def object_terminals(obj: dict, geometry) -> list:
    """[(terminal_id, local_x, local_y, medium)] in the object's own frame."""
    if obj.get("type") == "scada.boundary_point":
        label = obj.get("designation") or obj.get("name") or "LABEL"
        sublabel = obj.get("description") or obj.get("text") or ""
        width, height = label_frame_size(label, sublabel)
        width = max(_BOUNDARY_MIN_WIDTH, min(_BOUNDARY_MAX_WIDTH, width))
        side = obj.get("boundaryPortSide") if obj.get("boundaryPortSide") in ("BOTTOM", "LEFT", "RIGHT") else "TOP"
        fx, fy = {"TOP": (0.5, 0.0), "BOTTOM": (0.5, 1.0), "LEFT": (0.0, 0.5), "RIGHT": (1.0, 0.5)}[side]
        medium = obj.get("boundaryMedium") if obj.get("boundaryMedium") in ("WATER", "VENTILATION") else "ELECTRICAL"
        return [("T1", snap_to_grid(fx * width), snap_to_grid(fy * height), medium)]
    record = geometry.symbol(obj.get("type") or "") if geometry is not None else None
    specs = (record or {}).get("terminals") or []
    width, height = float(obj.get("width") or 0), float(obj.get("height") or 0)
    out = []
    for spec in specs:
        x, y = _side_offset(spec.get("side"), width, height)
        out.append((spec.get("id"), x, y, spec.get("medium") or "ELECTRICAL"))
    return out


def terminal_world_position(obj: dict, local_x: float, local_y: float):
    """Terminals.ts's getTerminalWorldPosition(): scale, then rotate about
    the object's top-left, then translate."""
    rotation = float(obj.get("rotation") or 0)
    lx = local_x * float(obj.get("scaleX") or 1)
    ly = local_y * float(obj.get("scaleY") or 1)
    if rotation == 0:
        return float(obj.get("x") or 0) + lx, float(obj.get("y") or 0) + ly
    radians = math.radians(rotation)
    rx = lx * math.cos(radians) - ly * math.sin(radians)
    ry = lx * math.sin(radians) + ly * math.cos(radians)
    return float(obj.get("x") or 0) + rx, float(obj.get("y") or 0) + ry


def world_terminals(objects, geometry) -> list:
    out = []
    for obj in objects:
        for terminal_id, lx, ly, medium in object_terminals(obj, geometry):
            x, y = terminal_world_position(obj, lx, ly)
            out.append(WorldTerminal(obj.get("id"), terminal_id, x, y, medium))
    return out


# --- geometry helpers ----------------------------------------------------------------

def _point_on_segment(px, py, ax, ay, bx, by) -> bool:
    if ax == bx:
        return px == ax and min(ay, by) <= py <= max(ay, by)
    if ay == by:
        return py == ay and min(ax, bx) <= px <= max(ax, bx)
    return False


def _points(conn: dict):
    return [(float(p.get("x", 0)), float(p.get("y", 0))) for p in (conn.get("points") or []) if isinstance(p, dict)]


def _segments(points):
    return [(points[i], points[i + 1]) for i in range(len(points) - 1)]


def point_touches_connection(px, py, conn: dict) -> bool:
    return any(_point_on_segment(px, py, a[0], a[1], b[0], b[1]) for a, b in _segments(_points(conn)))


def _connections_touch(a: dict, b: dict) -> bool:
    return any(point_touches_connection(x, y, b) for x, y in _points(a)) or \
        any(point_touches_connection(x, y, a) for x, y in _points(b))


class _UnionFind:
    def __init__(self, size):
        self.parent = list(range(size))

    def find(self, i):
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


# --- the resolver ---------------------------------------------------------------------

def resolve_nets(connections, objects, geometry, is_active_source=None) -> list:
    """`is_active_source(obj, terminal_id) -> bool` decides which terminals
    feed a net (see runtime_source_rule()); None means no net is ever
    active. An empty connection list gives an empty net list."""
    connections = [c for c in connections if isinstance(c, dict) and len(_points(c)) >= 2]
    if not connections:
        return []
    terminals = world_terminals(objects, geometry)
    by_id = {o.get("id"): o for o in objects}
    n, m = len(connections), len(terminals)
    uf = _UnionFind(n + m)
    for i in range(n):
        for j in range(i + 1, n):
            if _connections_touch(connections[i], connections[j]):
                uf.union(i, j)
    for ti, terminal in enumerate(terminals):
        for ci, conn in enumerate(connections):
            if point_touches_connection(terminal.x, terminal.y, conn):
                uf.union(n + ti, ci)
    for a in range(m):
        for b in range(a + 1, m):
            if terminals[a].x == terminals[b].x and terminals[a].y == terminals[b].y:
                uf.union(n + a, n + b)
    groups = {}
    for i in range(n):
        groups.setdefault(uf.find(i), ([], []))[0].append(i)
    for ti in range(m):
        root = uf.find(n + ti)
        if root in groups:
            groups[root][1].append(ti)
    nets = []
    for counter, (conn_idx, term_idx) in enumerate(groups.values()):
        net_terminals = [(terminals[t].obj_id, terminals[t].terminal_id) for t in term_idx]
        active = bool(is_active_source) and any(
            is_active_source(by_id.get(obj_id), terminal_id) for obj_id, terminal_id in net_terminals
            if by_id.get(obj_id) is not None)
        nets.append(Net(id=f"net-{counter}", connection_ids=[connections[i].get("id") for i in conn_idx],
                        terminals=net_terminals, medium=connections[conn_idx[0]].get("medium"),
                        state="ACTIVE" if active else "INACTIVE"))
    return nets


def connection_states(nets) -> dict:
    return {conn_id: net.state for net in nets for conn_id in net.connection_ids}


def terminal_net_states(nets) -> dict:
    return {(obj_id, terminal_id): net.state for net in nets for obj_id, terminal_id in net.terminals}


def junction_points(connections, objects, geometry) -> list:
    """Every grid node where three or more branches meet - the editor
    draws a dot there (three wire segments, or two segments and a
    terminal; a plain bend of one wire is 1+1 and gets none)."""
    connections = [c for c in connections if isinstance(c, dict)]
    terminals = world_terminals(objects, geometry)
    candidates = {}
    for conn in connections:
        for x, y in _points(conn):
            candidates[(x, y)] = (x, y)
    for t in terminals:
        candidates[(t.x, t.y)] = (t.x, t.y)
    out = []
    for px, py in candidates.values():
        degree = 0
        for conn in connections:
            for a, b in _segments(_points(conn)):
                if _point_on_segment(px, py, a[0], a[1], b[0], b[1]):
                    degree += 1 if (px, py) in (a, b) else 2
        degree += sum(1 for t in terminals if t.x == px and t.y == py)
        if degree >= 3:
            out.append((px, py))
    return out


def runtime_source_rule(presentation_for):
    """The active-source rule with the runtime's own knowledge:
    `presentation_for(obj)` -> screen_state.ObjectPresentation (or None).
      - a boundary point drawn as SOURCE feeds its net;
      - a symbol's OUT terminal feeds it when the symbol is bound to a
        SWITCHED apparatus whose live feedback says closed (asserted);
      - the rainwater tank's outflow (ODPLYW) is live whenever the tank
        shows a level, as in the editor (every level state is > 0 %)."""
    from epw_os.gui.synoptic.screen_state import ASSERTED_STATES

    def is_source(obj, terminal_id):
        if obj is None:
            return False
        if obj.get("type") == "scada.boundary_point" and obj.get("boundaryDirection") == "SOURCE":
            return True
        if terminal_id == "OUT" and obj.get("deviceId"):
            presentation = presentation_for(obj)
            apparatus = getattr(presentation, "apparatus", None)
            if apparatus is not None and (apparatus.behavior or "").upper() == "SWITCHED":
                return bool(presentation.live) and presentation.state in ASSERTED_STATES
        if obj.get("type") == "site.rainwater_tank2" and terminal_id == "ODPLYW":
            return True
        return False
    return is_source
