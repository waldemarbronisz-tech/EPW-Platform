"""Walls as the editor draws them - a port of project/WallGeometry.ts and
the passes of components/WallLayer.tsx (BandBody): walls joined at their
corners become one mitred band (a closed loop gets an outer and an
inner ring), the band is extruded up the screen by the wall's
foreshortened height, and the faces are lit from the upper left.
Openings: a door, window or gate seated in a wall (WallOpenings.ts -
the nearest wall within half its thickness plus a margin) cuts the band
and its extruded faces - the cut is the convex hull of the opening's
footprint and the same footprint lifted by the wall's drawn height, and
the two jambs are drawn as edges - so the room reads as one with a
doorway, not a wall with a door pasted on it.

All geometry is pure Python; drawing is draw_walls() at the bottom,
called by screen_widget.py in place of a flat band per wall.
"""
import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QPainterPath, QPen

from epw_os.gui.synoptic.rooms import DEFAULT_WALL_MATERIAL, WALL_MATERIALS, shade, wall_tones

JOIN_TOLERANCE = 1.5
MITRE_LIMIT = 4
PIXELS_PER_METRE = 80
WALL_MIN_THICKNESS, WALL_MAX_THICKNESS, WALL_DEFAULT_THICKNESS = 2, 16, 8
WALL_MIN_HEIGHT, WALL_MAX_HEIGHT, WALL_DEFAULT_HEIGHT = 0, 320, 200      # cm(400), cm(250) at 80 px/m
WALL_VIEW_FORESHORTENING = 0.2

EDGE_WIDTH = 1.25
NEAR_WALL_CUTAWAY = 0.3
LIGHT_X = -0.75
SHADE_RANGE = 0.22
FACE_BASE_SHADE = 0.78
CAP_SHADE = 1.06
ARRIS_COLOR, ARRIS_OPACITY = "#FFFFFF", 0.55
SKIRTING_COLOR, SKIRTING_OPACITY = "#000000", 0.22
GROUND_SHADOW_OFFSET, GROUND_SHADOW_OPACITY = 5, 0.18
COLOR_OUTLINE = "#000000"


def clamp_thickness(value) -> float:
    try:
        t = float(value)
    except (TypeError, ValueError):
        return WALL_DEFAULT_THICKNESS
    if not math.isfinite(t):
        return WALL_DEFAULT_THICKNESS
    return min(WALL_MAX_THICKNESS, max(WALL_MIN_THICKNESS, t))


def clamp_height(value) -> float:
    if value is None:
        return WALL_DEFAULT_HEIGHT
    try:
        h = float(value)
    except (TypeError, ValueError):
        return WALL_DEFAULT_HEIGHT
    if not math.isfinite(h):
        return WALL_DEFAULT_HEIGHT
    return min(WALL_MAX_HEIGHT, max(WALL_MIN_HEIGHT, h))


def drawn_height(value) -> float:
    return clamp_height(value) * WALL_VIEW_FORESHORTENING


def _pt(p):
    return float(p.get("x", 0)), float(p.get("y", 0))


def _key(point):
    return round(point[0] / JOIN_TOLERANCE), round(point[1] / JOIN_TOLERANCE)


# --- chains -------------------------------------------------------------------------------

def chains_from_walls(walls) -> list:
    """[{points, closed, wall_ids, thickness, height, material, mixed}] -
    closed loops first, then open runs from a free end, then every wall
    left over on its own (WallGeometry.chainsFromWalls)."""
    walls = [w for w in walls if isinstance(w, dict) and isinstance(w.get("from"), dict) and isinstance(w.get("to"), dict)]
    nodes = {}
    for wall in walls:
        a, b = _pt(wall["from"]), _pt(wall["to"])
        ka, kb = _key(a), _key(b)
        if ka == kb:
            continue
        nodes.setdefault(ka, {"point": a, "edges": []})["edges"].append((kb, wall))
        nodes.setdefault(kb, {"point": b, "edges": []})["edges"].append((ka, wall))

    def make(points, chain_walls, closed):
        thicknesses = {clamp_thickness(w.get("thickness")) for w in chain_walls}
        materials = {w.get("material") or "" for w in chain_walls}
        heights = {clamp_height(w.get("height")) for w in chain_walls}
        first = chain_walls[0]
        return {"points": points, "closed": closed, "wall_ids": [w.get("id") for w in chain_walls],
                "thickness": clamp_thickness(first.get("thickness")), "height": clamp_height(first.get("height")),
                "material": first.get("material"),
                "mixed": len(thicknesses) > 1 or len(materials) > 1 or len(heights) > 1}

    chains, used, visited = [], set(), set()
    for start in list(nodes):
        if start in visited:
            continue
        component, queue, seen = [], [start], {start}
        while queue:
            key = queue.pop(0)
            component.append(key)
            for to, _w in nodes[key]["edges"]:
                if to not in seen:
                    seen.add(to)
                    queue.append(to)
        visited.update(component)
        if len(component) < 3 or any(len(nodes[k]["edges"]) != 2 for k in component):
            continue
        points, chain_walls, current, previous = [], [], start, None
        for _ in range(len(component)):
            node = nodes[current]
            points.append(node["point"])
            step = next((e for e in node["edges"] if e[1] is not previous), None)
            if step is None:
                break
            chain_walls.append(step[1])
            previous, current = step[1], step[0]
        if len(points) == len(component):
            used.update(id(w) for w in chain_walls)
            chains.append(make(points, chain_walls, True))
    for key, node in nodes.items():
        if len(node["edges"]) != 1 or all(id(e[1]) in used for e in node["edges"]):
            continue
        points, chain_walls, current, previous = [node["point"]], [], key, None
        while True:
            here = nodes[current]
            step = None
            if len(here["edges"]) <= 2:
                step = next((e for e in here["edges"] if e[1] is not previous and id(e[1]) not in used), None)
            if step is None:
                break
            used.add(id(step[1]))
            chain_walls.append(step[1])
            previous, current = step[1], step[0]
            points.append(nodes[current]["point"])
            if current == key:
                break
        if chain_walls:
            chains.append(make(points, chain_walls, False))
    for wall in walls:
        if id(wall) in used or _key(_pt(wall["from"])) == _key(_pt(wall["to"])):
            continue
        used.add(id(wall))
        chains.append(make([_pt(wall["from"]), _pt(wall["to"])], [wall], False))
    return chains


# --- bands -------------------------------------------------------------------------------------

def _normalize(x, y):
    length = math.hypot(x, y)
    return (0.0, 0.0) if length == 0 else (x / length, y / length)


def _intersect(p1, d1, p2, d2):
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-9:
        return None
    t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
    return p1[0] + d1[0] * t, p1[1] + d1[1] * t


def offset_polyline(points, distance, closed) -> list:
    """WallGeometry.offsetPolyline(): the polyline moved sideways by
    `distance` (left normal), corners mitred up to MITRE_LIMIT."""
    count = len(points)
    if count < 2:
        return list(points)
    segments = count if closed else count - 1
    directions, offsets = [], []
    for i in range(segments):
        p, q = points[i], points[(i + 1) % count]
        d = _normalize(q[0] - p[0], q[1] - p[1])
        n = (-d[1] * distance, d[0] * distance)
        directions.append(d)
        offsets.append(((p[0] + n[0], p[1] + n[1]), (q[0] + n[0], q[1] + n[1])))
    result = []
    for i in range(count):
        incoming = (i - 1 + segments) % segments if closed else i - 1
        outgoing = i % segments if closed else i
        has_in = 0 <= incoming < segments
        has_out = 0 <= outgoing < segments
        if not has_in and has_out:
            result.append(offsets[outgoing][0])
            continue
        if has_in and not has_out:
            result.append(offsets[incoming][1])
            continue
        if not has_in and not has_out:
            result.append(points[i])
            continue
        meeting = _intersect(offsets[incoming][0], directions[incoming], offsets[outgoing][0], directions[outgoing])
        if meeting is None:
            result.append(offsets[outgoing][0])
            continue
        if math.hypot(meeting[0] - points[i][0], meeting[1] - points[i][1]) > abs(distance) * MITRE_LIMIT:
            result.append(offsets[incoming][1])
            continue
        result.append(meeting)
    return result


def signed_area(ring) -> float:
    total = 0.0
    for i, a in enumerate(ring):
        b = ring[(i + 1) % len(ring)]
        total += a[0] * b[1] - b[0] * a[1]
    return total


def band_from_chain(chain) -> dict:
    half = chain["thickness"] / 2.0
    if chain["closed"]:
        a = offset_polyline(chain["points"], half, True)
        b = offset_polyline(chain["points"], -half, True)
        outer, inner = (a, b) if abs(signed_area(a)) >= abs(signed_area(b)) else (b, a)
        return {"outer": outer, "inner": inner, "closed": True, "thickness": chain["thickness"],
                "height": chain["height"], "material": chain["material"], "wall_ids": chain["wall_ids"]}
    left = offset_polyline(chain["points"], half, False)
    right = offset_polyline(chain["points"], -half, False)
    return {"outer": left + list(reversed(right)), "inner": None, "closed": False, "thickness": chain["thickness"],
            "height": chain["height"], "material": chain["material"], "wall_ids": chain["wall_ids"]}


def bands_from_walls(walls) -> list:
    bands = []
    by_id = {w.get("id"): w for w in walls if isinstance(w, dict)}
    for chain in chains_from_walls(walls):
        if not chain["mixed"]:
            bands.append(band_from_chain(chain))
            continue
        for wall_id in chain["wall_ids"]:
            wall = by_id.get(wall_id)
            if wall is None:
                continue
            bands.append(band_from_chain({"points": [_pt(wall["from"]), _pt(wall["to"])], "closed": False,
                                          "wall_ids": [wall_id], "thickness": clamp_thickness(wall.get("thickness")),
                                          "height": clamp_height(wall.get("height")), "material": wall.get("material"),
                                          "mixed": False}))
    return bands


def extrude_band(band) -> list:
    """[{points: [(x, y) x4], depth, side, normal_x}] - the vertical faces
    a viewer above and in front sees: outer ring edges facing down the
    screen, and for a closed band the inner ring's edges facing up."""
    faces = []
    height = drawn_height(band["height"])
    if height <= 0:
        return faces
    ring = band["outer"]
    winding = 1 if signed_area(ring) >= 0 else -1
    for i, a in enumerate(ring):
        b = ring[(i + 1) % len(ring)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length == 0:
            continue
        nx, ny = dy * winding / length, -dx * winding / length
        if ny > 0:
            faces.append({"points": [a, b, (b[0], b[1] - height), (a[0], a[1] - height)],
                          "depth": max(a[1], b[1]), "side": "outer", "normal_x": nx})
        elif ny < 0 and band["inner"]:
            t = band["thickness"]
            ax, ay, bx, by = a[0] - nx * t, a[1] - ny * t, b[0] - nx * t, b[1] - ny * t
            faces.append({"points": [(ax, ay), (bx, by), (bx, by - height), (ax, ay - height)],
                          "depth": max(ay, by), "side": "inner", "normal_x": -nx})
    return faces


def shade_for_normal(normal_x: float) -> float:
    return 1 + normal_x * LIGHT_X * SHADE_RANGE


def cut_away(points) -> list:
    """The near face shown only 30 % high, so it never hides the room."""
    (ax, ay), (bx, by), (_bx, top_b), (_ax, top_a) = points
    return [(ax, ay), (bx, by), (bx, by - (by - top_b) * NEAR_WALL_CUTAWAY), (ax, ay - (ay - top_a) * NEAR_WALL_CUTAWAY)]


def cap_for_face(points, thickness) -> list:
    (_ax, _ay), (bx, _by), (_bx2, top_b), (ax, top_a) = points
    return [(ax, top_a), (bx, top_b), (bx, top_b - thickness), (ax, top_a - thickness)]


# --- drawing -------------------------------------------------------------------------------------

def _path(points, closed=True) -> QPainterPath:
    path = QPainterPath(QPointF(*points[0]))
    for x, y in points[1:]:
        path.lineTo(x, y)
    if closed:
        path.closeSubpath()
    return path


def _ring_path(outer, inner=None, lift=0.0) -> QPainterPath:
    path = _path([(x, y - lift) for x, y in outer])
    if inner:
        path.addPath(_path([(x, y - lift) for x, y in inner]))
    path.setFillRule(Qt.FillRule.OddEvenFill)
    return path


def _fill(painter, path, color, opacity=1.0):
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(color)))
    painter.setOpacity(opacity)
    painter.drawPath(path)
    painter.restore()


def _stroke(painter, path, color, width, opacity=1.0):
    painter.save()
    pen = QPen(QColor(color))
    pen.setWidthF(width)
    pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setOpacity(opacity)
    painter.drawPath(path)
    painter.restore()


def draw_band(painter, band):
    """WallLayer.tsx's BandBody, pass by pass."""
    tones = wall_tones(band["material"])
    material_base = WALL_MATERIALS.get(band["material"] or DEFAULT_WALL_MATERIAL, WALL_MATERIALS[DEFAULT_WALL_MATERIAL])
    thickness = band["thickness"]
    faces = sorted(extrude_band(band), key=lambda f: f["depth"])
    far = [f for f in faces if f["side"] == "inner"]
    near = [f for f in faces if f["side"] == "outer"]

    # 1. ground shadow: the footprint, offset down-right, the room punched out
    painter.save()
    painter.translate(GROUND_SHADOW_OFFSET, GROUND_SHADOW_OFFSET)
    _fill(painter, _ring_path(band["outer"], band["inner"]), "#000000", GROUND_SHADOW_OPACITY)
    painter.restore()
    # 2 + 3. the far wall: cap, face, cap outline, arris
    for face in far:
        cap = cap_for_face(face["points"], thickness)
        _fill(painter, _path(cap), shade(material_base, CAP_SHADE))
        _fill(painter, _path(face["points"]), shade(material_base, FACE_BASE_SHADE * shade_for_normal(face["normal_x"])))
        _stroke(painter, _path(cap), COLOR_OUTLINE, EDGE_WIDTH)
        (_a, _b, (bx, top_b), (ax, top_a)) = face["points"]
        _stroke(painter, _path([(ax, top_a), (bx, top_b)], closed=False), ARRIS_COLOR, 1.5, ARRIS_OPACITY)
    # 4. the top of the band (the wall's own footprint, lifted), the room punched out
    _fill(painter, _ring_path(band["outer"], band["inner"]), tones["top"])
    # 5. the near faces, cut away so they never hide the room
    for face in near:
        _fill(painter, _path(cut_away(face["points"])),
              shade(material_base, FACE_BASE_SHADE * shade_for_normal(face["normal_x"])))
    # 6. edges and skirting
    _stroke(painter, _path(band["outer"]), COLOR_OUTLINE, EDGE_WIDTH)
    if band["inner"]:
        _stroke(painter, _path(band["inner"]), COLOR_OUTLINE, EDGE_WIDTH)
        _stroke(painter, _path(band["inner"]), SKIRTING_COLOR, 3, SKIRTING_OPACITY)


# --- openings (a port of project/WallOpenings.ts) -----------------------------------------------

OPENING_TYPES = ("building.door", "building.window", "building.gate")
ATTACH_MARGIN = 14      # how far off a wall's centre line an opening may sit and still be seated in it
OVERCUT = 2             # the cut reaches a little past both faces so no sliver of wall is left


def object_center(obj: dict) -> tuple:
    """The object's centre ON SCREEN: Konva rotates a group about its
    top-left origin, so the centre is the origin plus the half-size
    vector turned by the same angle."""
    x, y = float(obj.get("x", 0)), float(obj.get("y", 0))
    w, h = float(obj.get("width", 0)) * float(obj.get("scaleX", 1) or 1), float(obj.get("height", 0)) * float(obj.get("scaleY", 1) or 1)
    angle = math.radians(float(obj.get("rotation", 0) or 0))
    cx, cy = w / 2, h / 2
    return (x + cx * math.cos(angle) - cy * math.sin(angle), y + cx * math.sin(angle) + cy * math.cos(angle))


def _wall_ends(wall):
    return _pt(wall["from"]), _pt(wall["to"])


def _project_onto_wall(wall, point) -> tuple:
    (x1, y1), (x2, y2) = _wall_ends(wall)
    dx, dy = x2 - x1, y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq <= 0:
        return (x1, y1)
    t = max(0.0, min(1.0, ((point[0] - x1) * dx + (point[1] - y1) * dy) / length_sq))
    return (x1 + t * dx, y1 + t * dy)


def _distance_to_wall(wall, point) -> float:
    px, py = _project_onto_wall(wall, point)
    return math.hypot(point[0] - px, point[1] - py)


def wall_for_opening(walls, obj: dict):
    """The wall an opening sits in: the nearest one within half its
    thickness plus ATTACH_MARGIN of the object's centre, or None."""
    center = object_center(obj)
    best, best_distance = None, float("inf")
    for wall in walls:
        distance = _distance_to_wall(wall, center)
        reach = clamp_thickness(wall.get("thickness")) / 2 + ATTACH_MARGIN
        if distance <= reach and distance < best_distance:
            best, best_distance = wall, distance
    return best


def find_wall_openings(walls, objects) -> list:
    """[{object_id, wall_id, center, width, angle, thickness, drawn_height}]
    for every door/window/gate seated in a wall."""
    openings = []
    for obj in objects or ():
        if obj.get("type") not in OPENING_TYPES:
            continue
        wall = wall_for_opening(walls, obj)
        if wall is None:
            continue
        (x1, y1), (x2, y2) = _wall_ends(wall)
        openings.append({
            "object_id": obj.get("id"), "wall_id": wall.get("id"),
            "center": _project_onto_wall(wall, object_center(obj)),
            "width": float(obj.get("width", 0)) * float(obj.get("scaleX", 1) or 1),
            "angle": math.atan2(y2 - y1, x2 - x1),
            "thickness": clamp_thickness(wall.get("thickness")),
            "drawn_height": drawn_height(wall.get("height")),
        })
    return openings


def _footprint_cut(opening) -> list:
    half_width = opening["width"] / 2
    half_depth = opening["thickness"] / 2 + OVERCUT
    cos, sin = math.cos(opening["angle"]), math.sin(opening["angle"])
    ax, ay = cos * half_width, sin * half_width
    bx, by = -sin * half_depth, cos * half_depth
    x, y = opening["center"]
    return [(x - ax - bx, y - ay - by), (x + ax - bx, y + ay - by), (x + ax + bx, y + ay + by), (x - ax + bx, y - ay + by)]


def convex_hull(points) -> list:
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def build(seq):
        stack = []
        for p in seq:
            while len(stack) >= 2 and cross(stack[-2], stack[-1], p) <= 0:
                stack.pop()
            stack.append(p)
        stack.pop()
        return stack
    return build(pts) + build(list(reversed(pts)))


def opening_cut_polygon(opening) -> list:
    """The footprint and the same footprint lifted by the wall's drawn
    height, hulled - what is cut out of the band AND its faces."""
    footprint = _footprint_cut(opening)
    if opening["drawn_height"] <= 0:
        return footprint
    lifted = [(x, y - opening["drawn_height"]) for x, y in footprint]
    return convex_hull(footprint + lifted)


def opening_jambs(opening) -> list:
    cut = _footprint_cut(opening)
    return [(cut[0], cut[3]), (cut[1], cut[2])]


def draw_walls(painter, walls, objects=()):
    openings = find_wall_openings(walls, objects)
    cuts = [opening_cut_polygon(o) for o in openings]
    painter.save()
    try:
        if cuts:
            clip = QPainterPath()
            clip.addRect(-100000.0, -100000.0, 200000.0, 200000.0)
            for cut in cuts:
                if len(cut) >= 3:
                    clip = clip.subtracted(_path(cut))
            painter.setClipPath(clip, Qt.ClipOperation.IntersectClip)
        for band in bands_from_walls(walls):
            if len(band["outer"]) >= 3:
                draw_band(painter, band)
    finally:
        painter.restore()
    for opening in openings:
        for (a, b) in opening_jambs(opening):
            _stroke(painter, _path([a, b], closed=False), COLOR_OUTLINE, EDGE_WIDTH)
