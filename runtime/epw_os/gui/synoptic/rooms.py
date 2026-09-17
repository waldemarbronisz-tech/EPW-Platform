"""Rooms on the runtime's screen - the editor's floor plan rules, ported:
which walls close a room (project/RoomFloors.ts's findClosedRooms), what
the room is called (the room record, elements/RoomElement.ts, that every
wall points at through roomId; an older file's per-wall roomName/
roomLocation as the fallback), and the material palette the editor
paints floors and walls with (theme/Materials.ts - base colours only,
the runtime does not tile textures).
"""
import math

JOIN_TOLERANCE = 1.5

FLOOR_MATERIALS = {"osb": "#C9A063", "parkiet": "#A9702F", "wykladzina": "#8C8C8C", "beton": "#ABABAB"}
WALL_MATERIALS = {"tynk": "#EDEDED", "beton": "#ABABAB", "cegla": "#9E5540", "osb": "#C9A063"}
DEFAULT_FLOOR_MATERIAL = "wykladzina"
DEFAULT_WALL_MATERIAL = "tynk"


def shade(hex_color: str, factor: float) -> str:
    """Materials.ts's shade(): every channel multiplied by `factor`, clamped."""
    text = (hex_color or "").strip().lstrip("#")
    if len(text) != 6:
        return hex_color
    try:
        value = int(text, 16)
    except ValueError:
        return hex_color
    channels = [((value >> shift) & 0xFF) for shift in (16, 8, 0)]
    clamped = [max(0, min(255, round(c * factor))) for c in channels]
    return "#{:02x}{:02x}{:02x}".format(*clamped)


def floor_color(material_id) -> str:
    return FLOOR_MATERIALS.get(material_id or DEFAULT_FLOOR_MATERIAL, FLOOR_MATERIALS[DEFAULT_FLOOR_MATERIAL])


def wall_tones(material_id) -> dict:
    """Materials.ts's wallFaceTones(): the lit top, the shaded side, the base."""
    base = WALL_MATERIALS.get(material_id or DEFAULT_WALL_MATERIAL, WALL_MATERIALS[DEFAULT_WALL_MATERIAL])
    return {"top": shade(base, 1.06), "side": shade(base, 0.78), "base": shade(base, 0.5)}


def _point(p):
    return float(p.get("x", 0)), float(p.get("y", 0))


def _key(point):
    return round(point[0] / JOIN_TOLERANCE), round(point[1] / JOIN_TOLERANCE)


def closed_rooms(walls) -> list:
    """[[(x, y), ...], ...] - one polygon per simple loop of walls: a
    connected group in which every corner joins exactly two walls."""
    nodes = {}
    for wall in walls:
        if not isinstance(wall, dict) or not isinstance(wall.get("from"), dict) or not isinstance(wall.get("to"), dict):
            continue
        a, b = _point(wall["from"]), _point(wall["to"])
        ka, kb = _key(a), _key(b)
        if ka == kb:
            continue
        nodes.setdefault(ka, {"point": a, "edges": []})["edges"].append((kb, wall.get("id")))
        nodes.setdefault(kb, {"point": b, "edges": []})["edges"].append((ka, wall.get("id")))
    rooms = []
    visited = set()
    for start in list(nodes):
        if start in visited:
            continue
        component, queue, seen = [], [start], {start}
        while queue:
            key = queue.pop(0)
            component.append(key)
            for to, _wall in nodes[key]["edges"]:
                if to not in seen:
                    seen.add(to)
                    queue.append(to)
        visited.update(component)
        if len(component) < 3 or any(len(nodes[k]["edges"]) != 2 for k in component):
            continue
        polygon, current, previous_wall = [], start, None
        for _ in range(len(component)):
            node = nodes[current]
            polygon.append(node["point"])
            step = next((e for e in node["edges"] if e[1] != previous_wall), None)
            if step is None:
                break
            previous_wall, current = step[1], step[0]
        if len(polygon) == len(component):
            rooms.append(polygon)
    return rooms


def connected_groups(walls) -> list:
    """Walls sharing corners, grouped: [[wall, ...], ...] - the editor's
    connectedWallIds() over every wall."""
    walls = [w for w in walls if isinstance(w, dict)]
    remaining = list(walls)
    groups = []
    while remaining:
        first = remaining.pop(0)
        group, corners = [first], {_key(_point(first.get("from", {}))), _key(_point(first.get("to", {})))}
        grew = True
        while grew:
            grew = False
            for wall in list(remaining):
                ka, kb = _key(_point(wall.get("from", {}))), _key(_point(wall.get("to", {})))
                if ka in corners or kb in corners:
                    group.append(wall)
                    corners.update((ka, kb))
                    remaining.remove(wall)
                    grew = True
        groups.append(group)
    return groups


def room_labels(walls, rooms) -> list:
    """[{x, y, name, location}] - one per wall group with a name or a
    location: the record first (roomId), the old per-wall fields for a
    file saved before the record existed."""
    by_id = {r.get("id"): r for r in rooms if isinstance(r, dict) and r.get("id")}
    labels = []
    for group in connected_groups(walls):
        record = next((by_id[w["roomId"]] for w in group if w.get("roomId") in by_id), None)
        name = (record or {}).get("name") or next((w.get("roomName") for w in group if w.get("roomName")), "")
        location = (record or {}).get("location") or next((w.get("roomLocation") for w in group if w.get("roomLocation")), "")
        if not name and not location:
            continue
        xs = [c for w in group for c in (_point(w["from"])[0], _point(w["to"])[0])]
        ys = [c for w in group for c in (_point(w["from"])[1], _point(w["to"])[1])]
        labels.append({"x": (min(xs) + max(xs)) / 2, "y": (min(ys) + max(ys)) / 2, "name": name or "",
                       "location": location or ""})
    return labels


def polygon_area(points) -> float:
    total = 0.0
    for i, (x1, y1) in enumerate(points):
        x2, y2 = points[(i + 1) % len(points)]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def wall_band(wall) -> list:
    """The four corners of a wall's footprint (its thickness around the
    centre line), for a filled band."""
    (x1, y1), (x2, y2) = _point(wall.get("from", {})), _point(wall.get("to", {}))
    half = float(wall.get("thickness") or 8) / 2.0
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / length * half, dx / length * half
    return [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)]
