"""ZADANIA p. 6, the room record on the runtime's side: the loader keeps
`rooms`, rooms.py finds closed wall loops the way the editor does and
names them from the record (or an old file's per-wall fields), and the
screen widget paints floors, material-coloured walls and the label."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor, QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from epw_os.core.epwsyn_loader import load_epwsyn_data  # noqa: E402
from epw_os.gui.synoptic import rooms as rm  # noqa: E402


def wall(id_, a, b, **extra):
    return {"id": id_, "from": {"x": a[0], "y": a[1]}, "to": {"x": b[0], "y": b[1]}, "thickness": 12, **extra}


def square(prefix, x, y, size=160, **extra):
    c = [(x, y), (x + size, y), (x + size, y + size), (x, y + size)]
    return [wall(f"{prefix}{i}", c[i], c[(i + 1) % 4], **extra) for i in range(4)]


def test_closed_rooms_finds_simple_loops_and_ignores_open_or_branching_chains():
    walls = square("a", 0, 0) + square("b", 400, 0)[:3] + [wall("t", (600, 0), (600, -80))]
    rooms = rm.closed_rooms(walls)
    assert len(rooms) == 1
    assert sorted(rooms[0]) == [(0.0, 0.0), (0.0, 160.0), (160.0, 0.0), (160.0, 160.0)]
    assert rm.polygon_area(rooms[0]) == 160 * 160
    # corners that nearly meet still join (JOIN_TOLERANCE), a zero-length wall is ignored
    nearly = square("n", 0, 0)
    nearly[3]["to"] = {"x": 0.6, "y": 0.4}
    assert len(rm.closed_rooms(nearly + [wall("z", (5, 5), (5, 5))])) == 1
    assert rm.closed_rooms([]) == []


def test_room_labels_read_the_record_then_the_old_per_wall_fields():
    walls = square("a", 0, 0, roomId="r1") + square("b", 400, 0, roomName="Garaz", roomLocation="GAR") + square("c", 800, 0)
    rooms = [{"id": "r1", "name": "Kotlownia", "location": "KOT"}]
    labels = rm.room_labels(walls, rooms)
    assert labels == [{"x": 80.0, "y": 80.0, "name": "Kotlownia", "location": "KOT"},
                      {"x": 480.0, "y": 80.0, "name": "Garaz", "location": "GAR"}]
    assert rm.connected_groups(walls) and len(rm.connected_groups(walls)) == 3


def test_materials_and_bands():
    assert rm.floor_color(None) == "#8C8C8C" and rm.floor_color("parkiet") == "#A9702F"
    assert rm.floor_color("no-such") == "#8C8C8C"
    tones = rm.wall_tones("cegla")
    assert tones["top"] == rm.shade("#9E5540", 1.06) and tones["side"] == rm.shade("#9E5540", 0.78)
    assert rm.shade("#808080", 0.5) == "#404040" and rm.shade("#ffffff", 2.0) == "#ffffff" and rm.shade("bad", 1) == "bad"
    band = rm.wall_band(wall("w", (0, 0), (100, 0)))
    assert band == [(0.0, 6.0), (100.0, 6.0), (100.0, -6.0), (0.0, -6.0)]


def test_loader_keeps_the_room_records():
    doc = {"format": "EPW_SYNOPTIC", "schema_version": 2, "project": {"name": "S"},
           "canvas": {"width": 800, "height": 600, "floorMaterial": "parkiet"},
           "objects": [], "devices": [], "walls": square("a", 0, 0, roomId="r1"),
           "rooms": [{"id": "r1", "name": "Kotlownia", "location": "KOT"}]}
    result = load_epwsyn_data(doc)
    assert result.ok and result.project.rooms == doc["rooms"] and len(result.project.walls) == 4
    assert load_epwsyn_data({**doc, "rooms": "x"}).project.rooms == []


def test_widget_paints_the_floor_in_the_material_and_the_walls_in_theirs():
    QApplication.instance() or QApplication([])
    from epw_os.gui.synoptic.screen_widget import SynopticScreenWidget
    widget = SynopticScreenWidget()
    widget.resize(800, 600)
    widget.set_screen({"format": "EPW_SYNOPTIC", "schema_version": 2, "project": {"name": "S"},
                       "canvas": {"width": 800, "height": 600, "background": "#00CFCF", "floorMaterial": "beton"},
                       "objects": [], "devices": [],
                       "walls": square("a", 100, 100, 300, roomId="r1", material="cegla"),
                       "rooms": [{"id": "r1", "name": "Kotlownia", "location": "KOT"}]})
    image = widget.grab().toImage()
    t = widget.view_transform()

    def color_at(x, y):
        p = t.map(x, y)
        return image.pixelColor(int(p[0]), int(p[1]))
    floor = color_at(150, 350)                               # inside the room, away from its label
    assert abs(floor.red() - 0xAB) <= 8 and abs(floor.green() - 0xAB) <= 8      # beton #ABABAB
    top = color_at(250, 100 + 3)                             # the lit face of the top wall (its shaded strip lies on the outer edge)
    expected_top = QColor(rm.wall_tones("cegla")["top"])
    assert abs(top.red() - expected_top.red()) <= 12 and abs(top.blue() - expected_top.blue()) <= 12
    # The panel fits what is drawn (the room, with a margin), so an empty
    # canvas point far from it lies off the widget - the canvas colour is
    # sampled in the widget's own corner, where the margin shows it.
    assert image.pixelColor(2, 2).name() == "#00cfcf"
    assert isinstance(image, QImage)
    widget.shutdown()
