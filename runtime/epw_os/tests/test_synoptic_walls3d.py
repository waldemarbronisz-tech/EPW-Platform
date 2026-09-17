"""Walls as the editor draws them (walls3d.py, a port of WallGeometry.ts
and WallLayer.tsx's passes) and the tanks' level clip (a Konva clipFunc
recorded by the exporter, honoured by the painter)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from epw_os.gui.synoptic import walls3d as w3  # noqa: E402
from epw_os.gui.synoptic.geometry import load_geometry  # noqa: E402
from epw_os.gui.synoptic.painter import PrimitivePainter  # noqa: E402


def wall(id_, a, b, **extra):
    return {"id": id_, "from": {"x": a[0], "y": a[1]}, "to": {"x": b[0], "y": b[1]}, "thickness": 8, **extra}


def square(prefix, x, y, size=160, **extra):
    c = [(x, y), (x + size, y), (x + size, y + size), (x, y + size)]
    return [wall(f"{prefix}{i}", c[i], c[(i + 1) % 4], **extra) for i in range(4)]


# --- geometry ------------------------------------------------------------------------

def test_chains_closed_open_and_single():
    walls = square("a", 0, 0) + [wall("o1", (400, 0), (500, 0)), wall("o2", (500, 0), (500, 100)),
                                 wall("s", (700, 700), (760, 700)), wall("z", (9, 9), (9, 9))]
    chains = w3.chains_from_walls(walls)
    kinds = [(c["closed"], len(c["wall_ids"])) for c in chains]
    assert kinds == [(True, 4), (False, 2), (False, 1)]
    assert chains[0]["thickness"] == 8 and chains[0]["height"] == w3.WALL_DEFAULT_HEIGHT and not chains[0]["mixed"]
    mixed = w3.chains_from_walls(square("m", 0, 0) [:2] + [dict(w, thickness=12) for w in square("m", 0, 0)[2:]])
    assert mixed[0]["mixed"] is True


def test_offset_polyline_mitres_corners_and_the_closed_band_has_two_rings():
    ring = [(0, 0), (100, 0), (100, 100), (0, 100)]
    outward = w3.offset_polyline(ring, -4, True)     # left normal of a clockwise-on-screen square points out
    inward = w3.offset_polyline(ring, 4, True)
    assert outward[0] == (-4.0, -4.0) and inward[0] == (4.0, 4.0)
    assert abs(w3.signed_area(outward)) > abs(w3.signed_area(inward))
    band = w3.band_from_chain(w3.chains_from_walls(square("a", 0, 0, 100))[0])
    assert band["closed"] and band["inner"] is not None
    assert abs(w3.signed_area(band["outer"])) > abs(w3.signed_area(band["inner"]))
    open_band = w3.band_from_chain(w3.chains_from_walls([wall("o", (0, 0), (100, 0))])[0])
    assert open_band["inner"] is None and len(open_band["outer"]) == 4
    assert w3.offset_polyline([(0, 0)], 3, False) == [(0, 0)]


def test_extrusion_gives_outer_faces_facing_down_and_inner_faces_facing_up():
    band = w3.band_from_chain(w3.chains_from_walls(square("a", 0, 0, 100))[0])
    faces = w3.extrude_band(band)
    sides = sorted(f["side"] for f in faces)
    assert sides == ["inner", "outer"]
    outer = next(f for f in faces if f["side"] == "outer")
    (ax, ay), (bx, by), (_bx, top_b), (_ax, top_a) = outer["points"]
    assert ay == by == 104.0 and top_a == top_b == 104.0 - w3.drawn_height(None)   # the bottom edge, extruded up
    assert w3.drawn_height(None) == 40.0 and w3.drawn_height(0) == 0.0 and w3.drawn_height("x") == 40.0
    flat = w3.band_from_chain(dict(w3.chains_from_walls(square("a", 0, 0, 100))[0], height=0))
    assert w3.extrude_band(flat) == []
    assert w3.cut_away(outer["points"])[2][1] == by - (by - top_b) * w3.NEAR_WALL_CUTAWAY
    assert w3.cap_for_face(outer["points"], 8)[2] == (bx, top_b - 8)
    assert w3.shade_for_normal(1.0) < 1 < w3.shade_for_normal(-1.0)


def test_bands_split_a_mixed_chain_per_wall():
    walls = square("m", 0, 0)[:2] + [dict(w, material="cegla") for w in square("m", 0, 0)[2:]]
    bands = w3.bands_from_walls(walls)
    assert len(bands) == 4 and all(not b["closed"] for b in bands)
    assert w3.bands_from_walls([]) == []


# --- drawing ---------------------------------------------------------------------------

def _ink(image):
    blank = QImage(image.size(), image.format())
    blank.fill(QColor(0, 0, 0, 0))
    return image != blank


def test_draw_walls_paints_a_room_with_a_darker_face_below_the_top(app=None):
    QApplication.instance() or QApplication([])
    image = QImage(400, 400, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    w3.draw_walls(painter, square("a", 100, 100, 200, material="tynk"))
    painter.end()
    assert _ink(image)
    top = image.pixelColor(200, 300)          # on the bottom wall's own footprint (the lit top)
    face = image.pixelColor(200, 300 + 3)     # just below it: the near face, cut away, shaded
    assert top.alpha() == 255 and face.alpha() == 255
    assert face.red() < top.red()
    inside = image.pixelColor(200, 200)       # the room stays clear (the ground shadow is punched out)
    assert inside.alpha() == 0 or inside.alpha() < 60


def test_the_tanks_carry_a_clip_and_the_painter_honours_it():
    QApplication.instance() or QApplication([])
    geometry = load_geometry().geometry

    def clips(nodes):
        for n in nodes or []:
            if n.get("clip"):
                yield n["clip"]
            yield from clips(n.get("children"))
    rain = list(clips(geometry.state_tree("site.rain_tank", "ON")))
    tank2 = list(clips(geometry.state_tree("site.rainwater_tank2", "HIGH")))
    assert rain and rain[0][0]["kind"] == "arc" and rain[0][0]["radius"] == 33
    assert tank2 and tank2[0][0]["kind"] == "rect"
    assert not any("clipFunc" in w for w in geometry.symbol("site.rain_tank")["warnings"])

    # A clipped group: a full-size rect painted inside a small rect clip covers only the clip.
    image = QImage(100, 100, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    PrimitivePainter(painter).draw_tree([
        {"primitive": "group", "clip": [{"kind": "rect", "x": 10, "y": 10, "width": 20, "height": 20}], "children": [
            {"primitive": "rect", "width": 100, "height": 100, "fill": "#0000ff"}]},
        {"primitive": "group", "clip": [{"kind": "arc", "x": 70, "y": 70, "radius": 10, "start_rad": 0, "end_rad": 6.283185307179586}],
         "children": [{"primitive": "rect", "width": 100, "height": 100, "fill": "#ff0000"}]},
    ])
    painter.end()
    assert image.pixelColor(15, 15).blue() == 255 and image.pixelColor(50, 50).alpha() == 0
    assert image.pixelColor(70, 70).red() == 255 and image.pixelColor(85, 85).alpha() == 0
