"""What the panel shows of a screen: the editor's runtime frame
(canvas.viewport, View -> Runtime frame) when there is one, else
everything drawn with a margin, else the canvas - so a single room fills
the panel instead of sitting as a stamp in the middle of an empty
1920 x 1080 canvas. Also: a non-active screen's own canvas settings
(floorMaterial, viewport) reach the reader through screen_document()."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from epw_os.core.epwsyn_loader import load_epwsyn_data  # noqa: E402
from epw_os.core.screen_set import screen_document  # noqa: E402
from epw_os.gui.synoptic.screen_widget import SynopticScreenWidget, content_bounds  # noqa: E402
from epw_os.tests.test_synoptic_rooms import square  # noqa: E402


def _doc(**extra):
    doc = {"format": "EPW_SYNOPTIC", "schema_version": 2, "project": {"name": "S"},
           "canvas": {"width": 1920, "height": 1080, "background": "#00CFCF", "floorMaterial": "beton"},
           "objects": [], "devices": [],
           "walls": square("a", 300, 200, 480, roomId="r1", material="cegla"),
           "rooms": [{"id": "r1", "name": "Magazyn", "location": "MAG"}]}
    doc.update(extra)
    return doc


def _widget(doc):
    QApplication.instance() or QApplication([])
    widget = SynopticScreenWidget()
    widget.resize(800, 600)
    widget.set_screen(doc)
    assert widget.has_screen and widget.load_error is None
    return widget


def test_a_lone_room_fills_the_panel_instead_of_the_empty_canvas():
    widget = _widget(_doc())
    try:
        t = widget.view_transform()
        canvas_fit_scale = min((800 - 16) / 1920, (600 - 16) / 1080)
        assert t.m11() > 1.4 * canvas_fit_scale                     # the room, not the canvas, sets the scale
        # The room's centre lands at the widget's centre sideways and a
        # little below it (the walls' pseudo-3D faces rise above the plan
        # and count), and its floor is what is painted there.
        centre = t.map(QPointF(300 + 240, 200 + 240))
        assert abs(centre.x() - 400) < 2 and 300 < centre.y() < 340
        image = widget.grab().toImage()
        floor = image.pixelColor(400, 330)
        assert abs(floor.red() - 0xAB) <= 8 and abs(floor.green() - 0xAB) <= 8      # beton #ABABAB
        assert image.pixelColor(2, 2).name() == "#00cfcf"           # the canvas colour surrounds it
        # The room's corners stay inside the widget, with the margin around them.
        for x, y in ((300, 200), (780, 680)):
            p = t.map(QPointF(x, y))
            assert 8 < p.x() < 792 and 8 < p.y() < 592
        # Clicks still map back through the same transform.
        assert widget.object_at(t.map(QPointF(540, 440))) is None
    finally:
        widget.shutdown()


def test_the_runtime_frame_wins_over_the_content():
    widget = _widget(_doc(canvas={"width": 1920, "height": 1080, "background": "#00CFCF",
                                  "viewport": {"x": 200, "y": 100, "width": 800, "height": 600}}))
    try:
        t = widget.view_transform()
        top_left, bottom_right = t.map(QPointF(200, 100)), t.map(QPointF(1000, 700))
        # 800 x 600 into 784 x 584: the height decides, the frame's top and
        # bottom sit exactly on the widget's margin and it is centred sideways.
        assert abs(top_left.y() - 8) < 0.01 and abs(bottom_right.y() - 592) < 0.01
        assert abs((top_left.x() - 8) - (792 - bottom_right.x())) < 0.01 and top_left.x() > 8
        assert abs(t.m11() - 584 / 600) < 1e-6
    finally:
        widget.shutdown()


def test_an_empty_screen_shows_the_whole_canvas_and_a_bad_frame_is_ignored():
    empty = _widget(_doc(walls=[], rooms=[]))
    try:
        rect = empty.document.view_rect()
        assert (rect.x(), rect.y(), rect.width(), rect.height()) == (0, 0, 1920, 1080)
    finally:
        empty.shutdown()
    bad = load_epwsyn_data(_doc(canvas={"width": 1920, "height": 1080, "viewport": {"x": 0, "y": 0, "width": 0, "height": 5}}))
    assert bad.ok and bad.project.canvas["viewport"] is None
    good = load_epwsyn_data(_doc(canvas={"width": 1920, "height": 1080, "viewport": {"x": 1, "y": 2, "width": 3, "height": 4}}))
    assert good.project.canvas["viewport"] == {"x": 1.0, "y": 2.0, "width": 3.0, "height": 4.0}
    assert load_epwsyn_data(_doc(canvas={"width": 1920, "height": 1080, "viewport": "x"})).project.canvas["viewport"] is None


def test_content_bounds_take_every_drawn_thing_with_its_real_footprint():
    project = load_epwsyn_data(_doc(
        walls=[], rooms=[],
        objects=[{"id": "o", "type": "x", "x": 100, "y": 100, "width": 64, "height": 32, "rotation": 90, "scaleX": 2, "scaleY": 1}],
        meters=[{"id": "m", "x": 500, "y": 50, "width": 200, "fontSize": 13, "title": "T", "rows": [{"device": "", "label": "a"}]}],
        connections=[{"id": "c", "points": [{"x": 10, "y": 900}, {"x": 20, "y": 950}], "medium": "ELECTRICAL", "style": "NORMAL"}],
    )).project
    bounds = content_bounds(project)
    # The rotated, scaled symbol spans x[68,100] y[100,228]; the wire reaches (10, 950); the meter ends past x=700.
    assert bounds.left() == 10 and bounds.top() == 50
    assert bounds.right() == 700 and bounds.bottom() == 950


def test_a_non_active_screens_floor_and_frame_reach_its_canvas():
    document = _doc(screens=[{"id": "s1", "name": "A"}, {"id": "s2", "name": "B"}], activeScreenId="s1",
                    screenContents={"s2": {"objects": [], "connections": [], "meters": [], "signalPanels": [],
                                           "frames": [], "walls": [], "rooms": [], "groupCommands": [],
                                           "setpointPanels": [], "floorMaterial": "parkiet",
                                           "viewport": {"x": 5, "y": 6, "width": 70, "height": 80}}})
    second = screen_document(document, "s2")
    assert second["canvas"]["floorMaterial"] == "parkiet"
    assert second["canvas"]["viewport"] == {"x": 5, "y": 6, "width": 70, "height": 80}
    assert second["canvas"]["width"] == 1920 and document["canvas"].get("viewport") is None
    # Back on the active screen the document is untouched: beton, no frame.
    first = screen_document(document, "s1")
    assert first["canvas"]["floorMaterial"] == "beton" and "viewport" not in first["canvas"]
