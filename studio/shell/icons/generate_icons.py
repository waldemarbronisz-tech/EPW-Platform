"""Generates every PNG in studio/shell/icons/ - task "zestaw ikon Studio
w manierze Windows 98". Run manually (`python generate_icons.py` from
this directory, or `python -m studio.shell.icons.generate_icons` from
the repo root) whenever an icon needs to change; the PNGs themselves are
committed (studio/shell/icons/__init__.py loads them from disk, it does
not regenerate them at runtime) so Studio never depends on this script
running, only a human editing it and re-running it does.

Technique, per the task's own spec:
  - 16x16, RGBA, transparent background.
  - Drawn pixel-by-pixel via QImage.setPixel()/a Bresenham line helper -
    not QPainter shape primitives (those anti-alias by default even
    with the render hint off, at the sub-pixel positions this style
    needs to avoid) - genuinely one placed pixel at a time.
  - No anti-aliasing anywhere - every edge is a hard pixel boundary.
  - A fixed 8-color palette (module-level constants below): black
    outline, white, two greys, yellow, navy, red, green - the same
    "epoch" palette for every icon, so recognizing one member of a
    group (the color) doesn't require reading the silhouette first.
  - A 1px darker-grey drop shadow along each icon's own bottom+right
    outer edge - the actual mechanism behind the "wypukłość" (bevel)
    look this whole task is chasing, applied per icon (not
    automatically to every sub-shape, which would look like noise on
    icons built from several small rectangles).

Every icon is its own function, name matching the PNG filename (and the
name callers pass to studio/shell/icons/__init__.py's icon()). Colors
are chosen for what they MEAN (task: "kolor niesie znaczenie") - yellow
folder, black diskette, blue water, yellow lightning - not decoration.
"""
import math
import os

from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

SIZE = 16
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

BLACK = QColor(0, 0, 0)
WHITE = QColor(255, 255, 255)
GREY_LIGHT = QColor(192, 192, 192)
GREY_DARK = QColor(128, 128, 128)
YELLOW = QColor(255, 204, 0)
NAVY = QColor(0, 0, 128)
RED = QColor(200, 0, 0)
GREEN = QColor(0, 140, 0)
# A ninth colour, added for one reason: VENTILATION is a medium in its
# own right everywhere else in this platform (ScadaTheme's
# VENTILATION_ACTIVE), and its icon sat in grey next to a yellow
# lightning bolt and a blue drop - so of the three media icons, two were
# identifiable at a glance and one was not. Colour carries meaning in
# this set; leaving one medium colourless broke that rule rather than
# following it.
ORANGE = QColor(200, 144, 0)
TRANSPARENT = QColor(0, 0, 0, 0)


def _new_image():
    img = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32)
    img.fill(TRANSPARENT)
    return img


def px(img, x, y, color):
    if 0 <= x < SIZE and 0 <= y < SIZE:
        img.setPixelColor(x, y, color)


def rect(img, x0, y0, x1, y1, color):
    """Fills the inclusive pixel range [x0..x1] x [y0..y1]."""
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            px(img, x, y, color)


def outline_rect(img, x0, y0, x1, y1, color):
    for x in range(x0, x1 + 1):
        px(img, x, y0, color)
        px(img, x, y1, color)
    for y in range(y0, y1 + 1):
        px(img, x0, y, color)
        px(img, x1, y, color)


def line(img, x0, y0, x1, y1, color):
    """Bresenham - the one genuinely pixel-by-pixel way to draw a
    diagonal with no anti-aliasing."""
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        px(img, x, y, color)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def drop_shadow(img, pixels, color=GREY_DARK):
    """Adds `color` one pixel below and one pixel right of every pixel
    in `pixels` (a set of (x, y) tuples already opaque in `img`) that
    isn't itself already opaque - the bevel-shadow convention, applied
    once per icon over its own outer silhouette, not per sub-rectangle."""
    shadow_px = set()
    for (x, y) in pixels:
        for dx, dy in ((1, 0), (0, 1), (1, 1)):
            nx, ny = x + dx, y + dy
            if (nx, ny) not in pixels and 0 <= nx < SIZE and 0 <= ny < SIZE:
                shadow_px.add((nx, ny))
    for (x, y) in shadow_px:
        if img.pixelColor(x, y).alpha() == 0:
            px(img, x, y, color)


def _opaque_pixels(img):
    return {(x, y) for y in range(SIZE) for x in range(SIZE) if img.pixelColor(x, y).alpha() > 0}


# ----------------------------------------------------------------------
# Fixed toolbar (7)
# ----------------------------------------------------------------------

def icon_new(img):
    # White page, folded top-right corner, a few text lines.
    rect(img, 3, 1, 11, 14, WHITE)
    outline_rect(img, 3, 1, 11, 14, BLACK)
    # folded corner (triangle of background showing through + diagonal)
    for i in range(4):
        for j in range(i + 1):
            px(img, 11 - i, 1 + j, TRANSPARENT)
    line(img, 8, 1, 11, 4, BLACK)
    line(img, 8, 1, 8, 4, GREY_LIGHT)
    line(img, 8, 4, 11, 4, GREY_LIGHT)
    for y in (7, 9, 11):
        line(img, 5, y, 9, y, GREY_DARK)


def icon_open(img):
    # A yellow folder, lid uchylona (open) - back panel + angled front flap.
    rect(img, 2, 4, 6, 6, YELLOW)
    outline_rect(img, 2, 4, 6, 6, BLACK)
    rect(img, 2, 6, 13, 12, YELLOW)
    outline_rect(img, 2, 6, 13, 12, BLACK)
    # the open flap, angled - a lighter yellow trapezoid drawn lower and
    # shifted, "uchylona klapa"
    for y in range(8, 13):
        x0 = 1 + (y - 8)
        x1 = 14 - (y - 8) // 2
        for x in range(x0, x1 + 1):
            px(img, x, y, QColor(255, 224, 102))
    outline_rect_poly = [(1, 12), (14, 12), (13, 8), (2, 8)]
    for i in range(len(outline_rect_poly)):
        x0, y0 = outline_rect_poly[i]
        x1, y1 = outline_rect_poly[(i + 1) % len(outline_rect_poly)]
        line(img, x0, y0, x1, y1, BLACK)


def icon_save(img):
    # Black 3.5" diskette: black body, white label near top, silver
    # shutter band.
    rect(img, 2, 2, 13, 13, BLACK)
    rect(img, 4, 2, 11, 5, GREY_LIGHT)  # metal shutter band at top
    rect(img, 5, 2, 8, 4, WHITE)
    rect(img, 3, 7, 12, 12, WHITE)  # paper label
    for y in (9, 11):
        line(img, 4, y, 11, y, GREY_DARK)
    outline_rect(img, 2, 2, 13, 13, BLACK)


def icon_save_as(img):
    icon_save(img)
    # a small yellow pencil badge over the bottom-right corner
    line(img, 11, 14, 15, 10, YELLOW)
    line(img, 12, 15, 15, 12, YELLOW)
    px(img, 15, 10, BLACK)
    px(img, 11, 14, BLACK)
    px(img, 12, 15, GREY_DARK)


def icon_undo(img):
    _arrow_arc(img, flip=False, color=YELLOW)


def icon_redo(img):
    _arrow_arc(img, flip=True, color=YELLOW)


def _arrow_arc(img, flip, color):
    cx = 8
    pts = []
    for deg in range(200, 520, 8):
        a = math.radians(deg if not flip else 360 - deg)
        x = cx + 5.5 * math.cos(a)
        y = 8 + 5.5 * math.sin(a)
        xi, yi = round(x), round(y)
        pts.append((xi, yi))
        px(img, xi, yi, color)
    tip = pts[-1]
    direction = -1 if not flip else 1
    tri = [
        (tip[0], tip[1]),
        (tip[0] + direction * 4, tip[1] - 3),
        (tip[0] + direction * 4, tip[1] + 3),
    ]
    _fill_triangle(img, tri, color)


def _fill_triangle(img, tri, color):
    xs = [p[0] for p in tri]
    ys = [p[1] for p in tri]
    for y in range(min(ys), max(ys) + 1):
        for x in range(min(xs), max(xs) + 1):
            if _point_in_triangle(x, y, *tri):
                px(img, x, y, color)


def _point_in_triangle(px_, py_, p0, p1, p2):
    def sign(a, b, c):
        return (a[0] - c[0]) * (b[1] - c[1]) - (b[0] - c[0]) * (a[1] - c[1])
    d1 = sign((px_, py_), p0, p1)
    d2 = sign((px_, py_), p1, p2)
    d3 = sign((px_, py_), p2, p0)
    has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (has_neg and has_pos)


def icon_help(img):
    # Blue circle, white question mark.
    _circle(img, 8, 8, 7, NAVY)
    for (x, y) in [(6, 5), (7, 4), (8, 4), (9, 5), (9, 6), (8, 7), (7, 8), (7, 9), (7, 11)]:
        px(img, x, y, WHITE)


def _circle(img, cx, cy, r, color):
    pts = set()
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                pts.add((x, y))
    for (x, y) in pts:
        px(img, x, y, color)
    return pts


# ----------------------------------------------------------------------
# Shared core (8)
# ----------------------------------------------------------------------

def icon_copy(img):
    rect(img, 2, 2, 10, 11, WHITE)
    outline_rect(img, 2, 2, 10, 11, GREY_DARK)
    rect(img, 5, 4, 13, 13, WHITE)
    outline_rect(img, 5, 4, 13, 13, BLACK)
    for y in (6, 8, 10):
        line(img, 7, y, 11, y, GREY_DARK)


def icon_paste(img):
    # Brown clipboard backing + white sheet on top + silver clip.
    rect(img, 2, 3, 13, 14, QColor(153, 102, 51))
    outline_rect(img, 2, 3, 13, 14, BLACK)
    rect(img, 4, 5, 11, 13, WHITE)
    outline_rect(img, 4, 5, 11, 13, BLACK)
    rect(img, 6, 1, 9, 4, GREY_LIGHT)
    outline_rect(img, 6, 1, 9, 4, BLACK)
    for y in (7, 9, 11):
        line(img, 5, y, 10, y, GREY_DARK)


def icon_cut(img):
    """Scissors (v4).

    v2's blades were single-pixel light-grey lines that vanished; v3
    thickened them but kept radius-2 finger rings, and a radius-2 ring
    rasterises to eight pixels in a diamond - which is precisely what
    the icon looked like. Radius 3 gives a ring that reads as round, and
    the blades get a black edge so they hold their shape against the
    toolbar's own grey.
    """
    pivot = (9, 8)

    # Blades: a grey core with a black edge, so they survive at size.
    for offset, color in ((0, BLACK), (1, GREY_LIGHT), (2, BLACK)):
        line(img, 5, 1 + offset, pivot[0], pivot[1] - 1 + offset, color)
        line(img, 5, 15 - offset, pivot[0], pivot[1] + 1 - offset, color)

    # Cutting tips past the pivot.
    for offset, color in ((0, BLACK), (1, GREY_LIGHT)):
        line(img, pivot[0], pivot[1] - 1 + offset, 15, 3 + offset, color)
        line(img, pivot[0], pivot[1] + 1 - offset, 15, 13 - offset, color)

    # Finger rings - rim only, radius 3, so they read as holes.
    for (bx, by) in ((3, 3), (3, 13)):
        for y in range(by - 3, by + 4):
            for x in range(bx - 3, bx + 4):
                d2 = (x - bx) ** 2 + (y - by) ** 2
                if 4 < d2 <= 9:
                    px(img, x, y, BLACK)

    px(img, pivot[0], pivot[1], BLACK)


def icon_delete(img):
    # Red X.
    for d in range(-1, 2):
        line(img, 3, 3 + d, 12, 12 + d, RED)
        line(img, 12, 3 + d, 3, 12 + d, RED)
    for d in range(-1, 2):
        px(img, 3 + d, 3, BLACK)


def icon_zoom_in(img):
    _magnifier(img)
    line(img, 5, 7, 9, 7, BLACK)
    line(img, 7, 5, 7, 9, BLACK)


def icon_zoom_out(img):
    _magnifier(img)
    line(img, 5, 7, 9, 7, BLACK)


def _magnifier(img):
    ring = _circle(img, 7, 7, 4, WHITE)
    for (x, y) in list(ring):
        if (x - 7) ** 2 + (y - 7) ** 2 >= 9:
            px(img, x, y, NAVY)
    line(img, 10, 10, 14, 14, BLACK)
    line(img, 11, 10, 14, 13, GREY_DARK)


def icon_grid(img):
    rect(img, 2, 2, 13, 13, WHITE)
    outline_rect(img, 2, 2, 13, 13, GREY_DARK)
    for x in (6, 9):
        line(img, x, 2, x, 13, GREY_DARK)
    for y in (6, 9):
        line(img, 2, y, 13, y, GREY_DARK)
    outline_rect(img, 2, 2, 13, 13, BLACK)


def icon_snap(img):
    icon_grid(img)
    _circle(img, 9, 9, 2, RED)


def icon_add_row(img):
    # Task "edytor DI/DO/AI" - a green plus, for adding a row (card,
    # location...) to one of the new table panels.
    rect(img, 1, 1, 14, 14, WHITE)
    outline_rect(img, 1, 1, 14, 14, GREY_DARK)
    rect(img, 6, 3, 9, 12, GREEN)
    rect(img, 3, 6, 12, 9, GREEN)


def icon_remove_row(img):
    # Same frame as icon_add_row, red minus - the deliberate visual
    # pair (add/remove), not reusing "delete"'s big red X so the two
    # concepts (delete a selected OBJECT vs. remove a TABLE ROW) stay
    # visually distinct in a panel where both might appear.
    rect(img, 1, 1, 14, 14, WHITE)
    outline_rect(img, 1, 1, 14, 14, GREY_DARK)
    rect(img, 3, 6, 12, 9, RED)


# ----------------------------------------------------------------------
# Synoptic tools (7 explicitly described)
# ----------------------------------------------------------------------

def icon_draw_wire(img):
    line(img, 2, 13, 7, 13, BLACK)
    line(img, 7, 13, 7, 5, BLACK)
    line(img, 7, 5, 13, 5, BLACK)
    for (x, y) in ((2, 13), (7, 13), (7, 5), (13, 5)):
        rect(img, x - 1, y - 1, x + 1, y + 1, NAVY)
    px(img, 7, 13, BLACK)
    px(img, 7, 5, BLACK)


def icon_draw_frame(img):
    for x in range(2, 14, 3):
        px(img, x, 2, BLACK)
        px(img, x, 13, BLACK)
    for y in range(2, 14, 3):
        px(img, 2, y, BLACK)
        px(img, 13, y, BLACK)
    px(img, 13, 2, BLACK)
    px(img, 13, 13, BLACK)
    px(img, 2, 2, BLACK)
    px(img, 2, 13, BLACK)


def icon_draw_building(img):
    # Redrawn (v2 - v1 self-sabotaged with a stray transparent-clearing
    # pass that erased the roof it had just drawn). Plain house: red
    # gable roof over a tan wall block, door + two windows.
    rect(img, 3, 9, 12, 14, QColor(224, 196, 140))
    outline_rect(img, 3, 9, 12, 14, BLACK)
    tri = [(1, 9), (14, 9), (7, 2)]
    _fill_triangle(img, tri, RED)
    _polygon_outline(img, tri, BLACK)
    line(img, 1, 9, 14, 9, BLACK)
    rect(img, 6, 11, 8, 14, QColor(102, 68, 34))  # door
    outline_rect(img, 6, 11, 8, 14, BLACK)
    rect(img, 4, 10, 5, 11, WHITE)
    outline_rect(img, 4, 10, 5, 11, BLACK)
    rect(img, 10, 10, 11, 11, WHITE)
    outline_rect(img, 10, 10, 11, 11, BLACK)


def icon_draw_wall(img):
    """Draw wall (ROOMS mode): a thick hatched wall segment with a pencil
    point at its free end - one wall, drawn corner to corner."""
    rect(img, 2, 9, 11, 12, GREY_DARK)
    outline_rect(img, 2, 9, 11, 12, BLACK)
    for x in range(3, 11, 2):
        px(img, x, 10, WHITE)
        px(img, x + 1, 11, WHITE)
    line(img, 12, 8, 14, 2, NAVY)
    line(img, 13, 8, 15, 2, NAVY)
    px(img, 12, 9, BLACK)


def icon_draw_room(img):
    """Draw room (ROOMS mode): a closed rectangle of thick walls - four
    walls at once - with a door gap in the bottom wall."""
    rect(img, 2, 2, 13, 13, GREY_DARK)
    rect(img, 4, 4, 11, 11, QColor(232, 228, 216))
    outline_rect(img, 2, 2, 13, 13, BLACK)
    outline_rect(img, 4, 4, 11, 11, BLACK)
    rect(img, 6, 12, 8, 13, QColor(232, 228, 216))
    line(img, 6, 11, 6, 13, BLACK)
    line(img, 8, 11, 8, 13, BLACK)


def _raised_tile(img, face):
    """The raised tile the two medium icons sit on - the classic SCADA
    look the user asked for: a light face, a white top-left edge and a
    dark bottom-right edge."""
    rect(img, 0, 0, 15, 15, face)
    rect(img, 0, 0, 15, 0, WHITE)
    rect(img, 0, 0, 0, 15, WHITE)
    rect(img, 0, 15, 15, 15, GREY_DARK)
    rect(img, 15, 0, 15, 15, GREY_DARK)


def _paint(img, cells):
    for x, y, w, h, color in cells:
        rect(img, x, y, x + w - 1, y + h - 1, color)


BOLT_RED = QColor(224, 0, 0)
BOLT_RIM = QColor(112, 0, 0)
TILE_PINK = QColor(222, 176, 176)
DROP_BLUE = QColor(40, 88, 224)
DROP_DARK = QColor(24, 56, 160)
DROP_LIGHT = QColor(160, 192, 255)


def icon_medium_electrical(img):
    """Power: a red lightning bolt on a raised pink tile (per the user's
    reference icon). Kept pixel-identical with the synoptic editor's own
    medium selector (src/components/icons/MediumPixelIcons.tsx), so the
    two toolbars show one picture for one medium."""
    _raised_tile(img, TILE_PINK)
    _paint(img, [
        (9, 2, 3, 1, BOLT_RIM),
        (8, 3, 3, 1, BOLT_RED), (11, 3, 1, 1, BOLT_RIM), (7, 3, 1, 1, BOLT_RIM),
        (7, 4, 3, 1, BOLT_RED), (10, 4, 1, 1, BOLT_RIM), (6, 4, 1, 1, BOLT_RIM),
        (6, 5, 3, 1, BOLT_RED), (9, 5, 1, 1, BOLT_RIM), (5, 5, 1, 1, BOLT_RIM),
        (5, 6, 6, 1, BOLT_RED), (4, 6, 1, 1, BOLT_RIM), (11, 6, 1, 1, BOLT_RIM),
        (4, 7, 6, 1, BOLT_RED), (10, 7, 1, 1, BOLT_RIM), (3, 7, 1, 1, BOLT_RIM),
        (7, 8, 2, 1, BOLT_RED), (6, 8, 1, 1, BOLT_RIM), (9, 8, 1, 1, BOLT_RIM), (3, 8, 3, 1, BOLT_RIM),
        (6, 9, 2, 1, BOLT_RED), (5, 9, 1, 1, BOLT_RIM), (8, 9, 1, 1, BOLT_RIM),
        (5, 10, 2, 1, BOLT_RED), (4, 10, 1, 1, BOLT_RIM), (7, 10, 1, 1, BOLT_RIM),
        (4, 11, 2, 1, BOLT_RED), (3, 11, 1, 1, BOLT_RIM), (6, 11, 1, 1, BOLT_RIM),
        (3, 12, 2, 1, BOLT_RED), (5, 12, 1, 1, BOLT_RIM), (2, 12, 1, 1, BOLT_RIM),
        (2, 13, 2, 1, BOLT_RIM),
    ])


def icon_medium_water(img):
    """Water: a tap with a falling blue drop on a raised grey tile (per the
    user's reference icon). Pixel-identical with the synoptic editor's
    medium selector, same reason as icon_medium_electrical."""
    _raised_tile(img, GREY_LIGHT)
    _paint(img, [
        (9, 2, 5, 1, BLACK),
        (11, 3, 1, 1, BLACK),
        (7, 4, 7, 1, BLACK), (7, 7, 7, 1, BLACK), (7, 4, 1, 4, BLACK), (13, 4, 1, 4, BLACK),
        (8, 5, 5, 2, GREY_DARK),
        (3, 5, 4, 1, BLACK), (3, 5, 1, 5, BLACK), (5, 7, 2, 1, BLACK), (5, 7, 1, 3, BLACK),
        (4, 6, 3, 1, GREY_DARK), (4, 7, 1, 2, GREY_DARK),
        (3, 9, 3, 1, BLACK),
        (4, 10, 1, 2, DROP_BLUE),
        (3, 12, 3, 2, DROP_BLUE),
        (3, 14, 3, 1, DROP_DARK),
        (3, 12, 1, 1, DROP_LIGHT),
    ])


def icon_medium_ventilation(img):
    """Ventilation: moving air (v4).

    v2 was a grille ring with paddles that merged into a blob; v3 was a
    four-blade pinwheel whose arms, bent all the same way at 16 px,
    landed on a shape nobody wants on a toolbar. This is the plain
    "moving air" glyph - three horizontal strokes with a turned-back end,
    the longest on top - which is what every icon set uses for air and
    which cannot be misread as anything else.

    ORANGE, matching this platform's own ventilation colour, so the
    three media icons are told apart by colour before shape: yellow
    lightning, blue drop, orange air.
    """
    # Same raised grey tile as the water icon (one icon look in Studio).
    _raised_tile(img, GREY_LIGHT)
    # Three air streams, each a bar with a hooked end, staggered in
    # length so they read as flow rather than as a hamburger menu.
    rect(img, 1, 3, 11, 4, ORANGE)
    rect(img, 11, 2, 12, 5, ORANGE)   # hook, curling back
    rect(img, 13, 2, 14, 3, ORANGE)

    rect(img, 1, 7, 13, 8, ORANGE)
    rect(img, 13, 6, 14, 9, ORANGE)

    rect(img, 1, 11, 9, 12, ORANGE)
    rect(img, 9, 10, 10, 13, ORANGE)
    rect(img, 11, 12, 12, 13, ORANGE)


def icon_wire_style_normal(img):
    rect(img, 2, 7, 13, 7, BLACK)
    rect(img, 2, 10, 13, 10, GREY_DARK)


def icon_wire_style_bus(img):
    rect(img, 2, 6, 13, 8, BLACK)
    rect(img, 2, 10, 13, 11, GREY_DARK)


def _fill_polygon(img, pts, color):
    ys = [p[1] for p in pts]
    for y in range(min(ys), max(ys) + 1):
        xs_at_y = []
        n = len(pts)
        for i in range(n):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            if y0 == y1:
                continue
            if min(y0, y1) <= y < max(y0, y1):
                t = (y - y0) / (y1 - y0)
                xs_at_y.append(x0 + t * (x1 - x0))
        xs_at_y.sort()
        for i in range(0, len(xs_at_y) - 1, 2):
            for x in range(round(xs_at_y[i]), round(xs_at_y[i + 1]) + 1):
                px(img, x, y, color)


def _polygon_outline(img, pts, color):
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        line(img, x0, y0, x1, y1, color)


def _opaque_pixels_subset(img, x0, y0, x1, y1):
    return {(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if img.pixelColor(x, y).alpha() > 0}


# ----------------------------------------------------------------------
# Remaining icons - chosen analogously, object-based per the task's own
# instruction ("wybierz analogicznie — realny obiekt albo jednoznaczny
# symbol, nigdy abstrakcję").
# ----------------------------------------------------------------------

def icon_reroute(img):
    line(img, 2, 13, 2, 8, BLACK)
    line(img, 2, 8, 9, 8, BLACK)
    line(img, 9, 8, 9, 3, BLACK)
    tri = [(9, 1), (6, 5), (12, 5)]
    _fill_triangle(img, tri, NAVY)


def icon_routing_direct(img):
    line(img, 2, 13, 12, 3, BLACK)
    tri = [(13, 2), (9, 3), (12, 6)]
    _fill_triangle(img, tri, BLACK)


def icon_routing_avoid(img):
    # Redrawn (v2 - v1's arc fragments didn't read as a continuous
    # path). A solid line detouring around a square obstacle, with an
    # arrowhead at the end - the obstacle drawn solid, not a dot.
    line(img, 2, 14, 5, 10, BLACK)
    for deg in range(200, 341, 10):
        a = math.radians(deg)
        x = round(8 + 4 * math.cos(a))
        y = round(10 + 4 * math.sin(a))
        px(img, x, y, BLACK)
        px(img, x, y - 1, BLACK)
    line(img, 11, 8, 14, 3, BLACK)
    tri = [(14, 2), (11, 4), (13, 6)]
    _fill_triangle(img, tri, BLACK)
    rect(img, 6, 8, 9, 11, RED)
    outline_rect(img, 6, 8, 9, 11, BLACK)


def icon_reset_zoom(img):
    _magnifier(img)
    px(img, 6, 6, BLACK)
    px(img, 6, 8, BLACK)
    px(img, 8, 7, BLACK)


def icon_align_left(img):
    line(img, 2, 1, 2, 14, BLACK)
    for y, w in ((3, 8), (7, 5), (11, 10)):
        rect(img, 4, y, 4 + w, y + 1, NAVY)


def icon_align_center(img):
    line(img, 8, 1, 8, 14, BLACK)
    for y, w in ((3, 8), (7, 4), (11, 10)):
        rect(img, 8 - w // 2, y, 8 - w // 2 + w, y + 1, NAVY)


def icon_align_right(img):
    line(img, 13, 1, 13, 14, BLACK)
    for y, w in ((3, 8), (7, 5), (11, 10)):
        rect(img, 13 - w, y, 13, y + 1, NAVY)


def icon_align_middle(img):
    line(img, 1, 8, 14, 8, BLACK)
    for x, h in ((3, 8), (7, 5), (11, 10)):
        rect(img, x, 8 - h // 2, x + 1, 8 - h // 2 + h, NAVY)


def icon_align_popup(img):
    tri = [(4, 6), (12, 6), (8, 11)]
    _fill_triangle(img, tri, BLACK)


def icon_distribute_h(img):
    for x in (2, 7, 12):
        rect(img, x, 5, x + 2, 11, NAVY)
        outline_rect(img, x, 5, x + 2, 11, BLACK)
    line(img, 1, 13, 14, 13, GREY_DARK)


def icon_distribute_v(img):
    for y in (2, 7, 12):
        rect(img, 5, y, 11, y + 2, NAVY)
        outline_rect(img, 5, y, 11, y + 2, BLACK)
    line(img, 13, 1, 13, 14, GREY_DARK)


def icon_bring_front(img):
    rect(img, 2, 5, 9, 12, GREY_LIGHT)
    outline_rect(img, 2, 5, 9, 12, GREY_DARK)
    rect(img, 6, 2, 13, 9, WHITE)
    outline_rect(img, 6, 2, 13, 9, BLACK)


def icon_send_back(img):
    rect(img, 6, 2, 13, 9, GREY_LIGHT)
    outline_rect(img, 6, 2, 13, 9, GREY_DARK)
    rect(img, 2, 5, 9, 12, WHITE)
    outline_rect(img, 2, 5, 9, 12, BLACK)


def icon_lock(img):
    rect(img, 4, 7, 11, 14, YELLOW)
    outline_rect(img, 4, 7, 11, 14, BLACK)
    for x in (5, 6, 9, 10):
        px(img, x, 5, BLACK)
    line(img, 5, 3, 5, 7, BLACK)
    line(img, 10, 3, 10, 7, BLACK)
    line(img, 5, 3, 10, 3, BLACK)
    _circle(img, 7, 10, 1, BLACK)


def icon_unlock(img):
    rect(img, 4, 7, 11, 14, YELLOW)
    outline_rect(img, 4, 7, 11, 14, BLACK)
    line(img, 5, 2, 5, 6, BLACK)
    line(img, 10, 2, 12, 2, BLACK)
    line(img, 12, 2, 12, 6, BLACK)
    line(img, 5, 2, 10, 2, BLACK)
    _circle(img, 7, 10, 1, BLACK)


def icon_rotate_left(img):
    _rotate_arc(img, flip=False)


def icon_rotate_right(img):
    _rotate_arc(img, flip=True)


def _rotate_arc(img, flip):
    """A rotation arrow (v4).

    v2's arc was a single faint grey pixel wide and vanished at toolbar
    size, leaving a bare square; v3 thickened it but wrapped it round a
    white workpiece, and at 16 px the two fought and read as one blue
    blob. The workpiece is gone: a three-quarter circular arrow IS the
    rotate glyph, and without something inside it there is room to draw
    it cleanly.

    NAVY rather than the undo/redo yellow, so a rotation is not mistaken
    for an undo at a glance.
    """
    # Three quarters of a ring, two pixels thick.
    for y in range(0, SIZE):
        for x in range(0, SIZE):
            d2 = (x - 8) ** 2 + (y - 8) ** 2
            if not (16 < d2 <= 36):
                continue
            # Leave a quadrant open - the gap the arrowhead closes.
            if flip:
                if x >= 8 and y <= 8:
                    continue
            else:
                if x <= 8 and y <= 8:
                    continue
            px(img, x, y, NAVY)

    # The head, closing the open quadrant.
    if flip:
        tri = [(8, 0), (8, 6), (14, 3)]
    else:
        tri = [(8, 0), (8, 6), (2, 3)]
    _fill_triangle(img, tri, NAVY)


def icon_add_meter(img):
    _circle(img, 8, 9, 6, WHITE)
    outline_rect(img, 2, 3, 14, 15, TRANSPARENT)
    for ang in range(200, 341, 35):
        a = math.radians(ang)
        px(img, round(8 + 5 * math.cos(a)), round(9 + 5 * math.sin(a)), BLACK)
    line(img, 8, 9, round(8 + 4 * math.cos(math.radians(250))), round(9 + 4 * math.sin(math.radians(250))), RED)
    px(img, 8, 9, BLACK)
    for x in range(2, 15):
        for y in range(3, 16):
            if (x - 8) ** 2 + (y - 9) ** 2 in (36, 35):
                px(img, x, y, BLACK)


def icon_add_signal_panel(img):
    rect(img, 2, 3, 13, 12, WHITE)
    outline_rect(img, 2, 3, 13, 12, BLACK)
    pts = [(3, 9), (5, 6), (7, 10), (9, 5), (11, 9), (12, 7)]
    for i in range(len(pts) - 1):
        line(img, *pts[i], *pts[i + 1], GREEN)


def icon_add_group_command(img):
    # Redrawn (v2 - v1's edge-to-edge tiling read as a checkerboard,
    # not "grouped items"). Three overlapping squares cascading
    # diagonally, like a stack of buttons grouped into one command.
    rect(img, 1, 1, 8, 8, WHITE)
    outline_rect(img, 1, 1, 8, 8, GREY_DARK)
    rect(img, 4, 4, 11, 11, YELLOW)
    outline_rect(img, 4, 4, 11, 11, GREY_DARK)
    rect(img, 7, 7, 14, 14, NAVY)
    outline_rect(img, 7, 7, 14, 14, BLACK)


def icon_add_setpoint_panel(img):
    rect(img, 2, 2, 13, 13, WHITE)
    outline_rect(img, 2, 2, 13, 13, BLACK)
    _circle(img, 8, 8, 4, RED)
    _circle(img, 8, 8, 2, WHITE)
    px(img, 8, 8, RED)


def icon_scada_preview(img):
    rect(img, 1, 2, 14, 10, NAVY)
    outline_rect(img, 1, 2, 14, 10, BLACK)
    rect(img, 3, 4, 12, 8, WHITE)
    pts = [(3, 7), (5, 5), (7, 7), (9, 4), (11, 6)]
    for i in range(len(pts) - 1):
        line(img, *pts[i], *pts[i + 1], GREEN)
    rect(img, 6, 11, 9, 12, GREY_DARK)
    rect(img, 4, 13, 11, 14, GREY_DARK)


def icon_project_registers(img):
    rect(img, 2, 2, 13, 13, WHITE)
    outline_rect(img, 2, 2, 13, 13, BLACK)
    for y in (5, 8, 11):
        line(img, 2, y, 13, y, GREY_DARK)
    line(img, 8, 2, 8, 13, GREY_DARK)


def icon_device_list(img):
    for y in (3, 7, 11):
        rect(img, 2, y, 4, y + 2, NAVY)
        line(img, 6, y + 1, 13, y + 1, BLACK)


def icon_background_color(img):
    # Redrawn (v2 - v1 read as a random blob). A paint can: grey body,
    # navy lid, a drip of the color it applies falling free of it - the
    # can/lid shape is the unambiguous part, the drip is what says
    # "color".
    rect(img, 3, 6, 10, 13, GREY_LIGHT)
    outline_rect(img, 3, 6, 10, 13, BLACK)
    rect(img, 2, 3, 11, 6, NAVY)
    outline_rect(img, 2, 3, 11, 6, BLACK)
    for y in (8, 10):
        line(img, 4, y, 9, y, GREY_DARK)
    _circle(img, 13, 12, 2, NAVY)
    px(img, 12, 9, NAVY)
    px(img, 13, 10, NAVY)


def icon_compare(img):
    # Redrawn (v2 - v1's thin connector read as a chain link, not
    # "compare"). Two documents with a two-headed arrow between them.
    rect(img, 0, 2, 5, 13, WHITE)
    outline_rect(img, 0, 2, 5, 13, BLACK)
    rect(img, 10, 2, 15, 13, WHITE)
    outline_rect(img, 10, 2, 15, 13, BLACK)
    line(img, 6, 7, 9, 7, NAVY)
    line(img, 6, 8, 9, 8, NAVY)
    tri_l = [(6, 6), (6, 9), (4, 7)]
    tri_r = [(9, 6), (9, 9), (11, 7)]
    _fill_triangle(img, tri_l, NAVY)
    _fill_triangle(img, tri_r, NAVY)


def icon_enable_selected(img):
    for d in range(2):
        line(img, 3, 8 + d, 6, 11 + d, GREEN)
        line(img, 6, 11 + d, 12, 3 + d, GREEN)


def icon_disable_selected(img):
    _circle(img, 8, 8, 6, WHITE)
    for x in range(2, 15):
        for y in range(2, 15):
            if (x - 8) ** 2 + (y - 8) ** 2 in (36, 35):
                px(img, x, y, RED)
    line(img, 4, 4, 12, 12, RED)


def icon_toolbar_style_icons(img):
    for x in (2, 7, 12):
        rect(img, x, 6, x + 3, 9, GREY_LIGHT)
        outline_rect(img, x, 6, x + 3, 9, BLACK)


def icon_toolbar_style_icons_text(img):
    for x in (2, 7, 12):
        rect(img, x, 2, x + 3, 5, GREY_LIGHT)
        outline_rect(img, x, 2, x + 3, 5, BLACK)
    for y in (9, 11, 13):
        line(img, 2, y, 13, y, GREY_DARK)


def icon_toolbar_style_text(img):
    for y in (3, 6, 9, 12):
        line(img, 2, y, 13, y, BLACK)


def icon_export(img):
    rect(img, 2, 7, 9, 14, GREY_LIGHT)
    outline_rect(img, 2, 7, 9, 14, BLACK)
    line(img, 10, 6, 14, 2, BLACK)
    tri = [(14, 2), (10, 3), (13, 6)]
    _fill_triangle(img, tri, BLACK)


def icon_help_catalog(img):
    rect(img, 2, 2, 13, 13, WHITE)
    outline_rect(img, 2, 2, 13, 13, BLACK)
    line(img, 7, 2, 7, 13, GREY_DARK)
    for y in (4, 6, 8, 10):
        line(img, 3, y, 6, y, GREY_DARK)
        line(img, 8, y, 12, y, GREY_DARK)


def icon_help_shortcuts(img):
    rect(img, 1, 5, 14, 12, GREY_LIGHT)
    outline_rect(img, 1, 5, 14, 12, BLACK)
    for row, y in enumerate((7, 10)):
        for col, x in enumerate(range(3, 13, 3)):
            rect(img, x, y, x + 1, y + 1, WHITE)
            outline_rect(img, x, y, x + 1, y + 1, GREY_DARK)


def icon_settings(img):
    """A gear, redrawn (v4).

    v2 laid EIGHT teeth of 3x3 pixels around a radius-6 circle; at 16 px
    the teeth were wider than the gaps and merged into a ring of noise.
    v3 fixed the teeth but outlined the body by re-colouring every pixel
    past a distance threshold, which on a rasterised circle picks a
    ragged, one-pixel-here-two-pixels-there rim. This draws the rim as
    an explicit ring - the outer radius minus the inner one - so it is
    uniform all the way round.
    """
    def ring(cx, cy, outer, inner, color):
        for y in range(cy - outer, cy + outer + 1):
            for x in range(cx - outer, cx + outer + 1):
                d2 = (x - cx) ** 2 + (y - cy) ** 2
                if inner * inner < d2 <= outer * outer:
                    px(img, x, y, color)

    # Teeth first, so the body draws over their inner ends.
    rect(img, 6, 1, 9, 3, GREY_DARK)     # N
    rect(img, 6, 12, 9, 14, GREY_DARK)   # S
    rect(img, 1, 6, 3, 9, GREY_DARK)     # W
    rect(img, 12, 6, 14, 9, GREY_DARK)   # E

    _circle(img, 8, 8, 5, GREY_LIGHT)
    ring(8, 8, 5, 4, BLACK)

    # The bore. A SQUARE hole, not a round one: a radius-2 ring
    # rasterises to eight pixels arranged in a diamond, which is what it
    # looked like. At this size a 4x4 outlined square reads as a hole
    # and a diamond does not.
    rect(img, 6, 6, 9, 9, BLACK)
    rect(img, 7, 7, 8, 8, WHITE)


def icon_about(img):
    _circle(img, 8, 8, 7, NAVY)
    for (x, y) in [(7, 4), (8, 4), (7, 6), (8, 6), (7, 7), (8, 7), (7, 8), (8, 8), (7, 9), (8, 9), (7, 10), (8, 10)]:
        px(img, x, y, WHITE)


def icon_compile(img):
    """Compile: a document with a green tick.

    v2 was the same unreadable gear as settings, plus a tick - two
    problems at once, and it was also nearly indistinguishable from
    settings itself at toolbar size. A sheet with a tick says "this was
    built and it checks out", is unmistakable next to a gear, and does
    not collide with sim_start's green triangle either.
    """
    # The sheet, with a folded corner.
    rect(img, 2, 1, 10, 13, WHITE)
    outline_rect(img, 2, 1, 10, 13, BLACK)
    rect(img, 8, 1, 10, 3, GREY_LIGHT)
    line(img, 8, 3, 10, 3, BLACK)
    line(img, 8, 1, 8, 3, BLACK)

    # Content lines - enough to read as a document, not so many that the
    # tick has nothing to sit on.
    for y in (5, 7, 9):
        rect(img, 4, y, 8, y, GREY_DARK)

    # The tick, deliberately breaking out past the sheet's own edge so it
    # reads as a verdict ON the document rather than as part of it.
    for d in range(2):
        line(img, 7, 10 + d, 9, 13 + d, GREEN)
        line(img, 9, 13 + d, 15, 5 + d, GREEN)


def icon_sim_start(img):
    tri = [(3, 2), (3, 14), (14, 8)]
    _fill_triangle(img, tri, GREEN)
    _polygon_outline(img, tri, BLACK)


def icon_sim_pause(img):
    rect(img, 3, 2, 6, 14, NAVY)
    outline_rect(img, 3, 2, 6, 14, BLACK)
    rect(img, 9, 2, 12, 14, NAVY)
    outline_rect(img, 9, 2, 12, 14, BLACK)


def icon_sim_stop(img):
    rect(img, 3, 3, 13, 13, RED)
    outline_rect(img, 3, 3, 13, 13, BLACK)


def icon_logic(img):
    """The Logika department. An AND gate: the one picture that says
    "logic" to anyone who has ever opened a control drawing.

    It replaces Qt's own SP_FileDialogDetailedView standard icon, which
    said "a list with details" and nothing whatever about logic - the
    reason the tree was reported as unreadable. Drawn as the IEC/ANSI
    D-shape with two inputs and one output, because that silhouette
    survives 16 px where a gate with a symbol inside it would not.
    """
    # The D: flat left edge, semicircular right. The arc is a hand-laid
    # pixel run rather than a computed circle - at this size a rounded
    # sqrt() lands on visibly lopsided pixels.
    right_edge = {3: 9, 4: 10, 5: 11, 6: 11, 7: 12, 8: 12, 9: 11, 10: 11, 11: 10, 12: 9}

    # Interior first, outline over it.
    for y in range(4, 12):
        rect(img, 5, y, right_edge[y] - 1, y, WHITE)

    for y in range(3, 13):
        px(img, 4, y, BLACK)
    for x in range(4, 10):
        px(img, x, 3, BLACK)
        px(img, x, 12, BLACK)
    for y, x_max in right_edge.items():
        px(img, x_max, y, BLACK)

    # Two inputs on the left, one output on the right - the part that
    # makes it a GATE rather than a rounded box.
    for x in range(1, 4):
        px(img, x, 5, BLACK)
        px(img, x, 10, BLACK)
    for x in range(13, 16):
        px(img, x, 8, BLACK)


def icon_synoptic(img):
    """The Schemat synoptyczny department. A fragment of a one-line
    diagram: a busbar with two outgoing ways, each through a device.

    It replaces Qt's own SP_DesktopIcon, which said "a computer
    desktop". What this department actually holds is a schematic, so
    that is what it shows. Navy for the busbar follows this set's own
    rule that colour carries meaning - navy is the schematic/electrical
    colour everywhere else in Studio.

    TWO ways, not three: at 16 px a third device leaves each box 3 px
    wide with a 1 px interior, and a box with a one-pixel hole in it
    reads as a slot rather than as an apparatus. Two boxes of 5 px have
    a real interior and the diagram still says "a bar feeding ways".
    """
    # Busbar, two pixels deep so it reads as a bar and not a hairline.
    rect(img, 2, 1, 13, 2, NAVY)

    # Two drops off it.
    for x in (5, 11):
        for y in range(3, 6):
            px(img, x, y, BLACK)

    # A device on each way - 5 px square, so the interior is a real 3 px
    # of white rather than a single pixel.
    for x0 in (3, 9):
        rect(img, x0, 6, x0 + 4, 10, WHITE)
        outline_rect(img, x0, 6, x0 + 4, 10, BLACK)

    # Outgoing tails, so the ways read as going somewhere.
    for x in (5, 11):
        for y in range(11, 15):
            px(img, x, y, BLACK)


# ----------------------------------------------------------------------
# Text formatting + preview (feat/text-formatting): used by the Word-style
# format bars in Synoptic and Logic Studio, and by Synoptic's preview mode.
# ----------------------------------------------------------------------

def _rects(img, cells, color):
    for x0, y0, x1, y1 in cells:
        rect(img, x0, y0, x1, y1, color)


def icon_text_bold(img):
    _rects(img, [(4, 3, 5, 12), (6, 3, 9, 4), (10, 4, 11, 6), (6, 7, 10, 7),
                 (10, 8, 11, 11), (6, 11, 9, 12)], BLACK)


def icon_text_italic(img):
    rect(img, 7, 3, 12, 3, BLACK)
    rect(img, 3, 12, 8, 12, BLACK)
    line(img, 10, 4, 6, 11, BLACK)
    line(img, 11, 4, 7, 11, BLACK)


def icon_text_underline(img):
    _rects(img, [(4, 3, 5, 9), (10, 3, 11, 9), (5, 10, 10, 10), (6, 11, 9, 11)], BLACK)
    rect(img, 3, 13, 12, 13, NAVY)


def icon_text_align_left(img):
    _rects(img, [(3, 3, 12, 3), (3, 6, 9, 6), (3, 9, 12, 9), (3, 12, 8, 12)], BLACK)


def icon_text_align_center(img):
    _rects(img, [(3, 3, 12, 3), (5, 6, 10, 6), (3, 9, 12, 9), (5, 12, 10, 12)], BLACK)


def icon_text_align_right(img):
    _rects(img, [(3, 3, 12, 3), (6, 6, 12, 6), (3, 9, 12, 9), (7, 12, 12, 12)], BLACK)


def icon_text_align_justify(img):
    _rects(img, [(3, 3, 12, 3), (3, 6, 12, 6), (3, 9, 12, 9), (3, 12, 12, 12)], BLACK)


def icon_text_box(img):
    for x in range(2, 14, 2):
        px(img, x, 2, NAVY)
        px(img, x, 13, NAVY)
    for y in range(2, 14, 2):
        px(img, 2, y, NAVY)
        px(img, 13, y, NAVY)
    rect(img, 5, 5, 10, 5, BLACK)
    rect(img, 7, 6, 8, 10, BLACK)


def icon_preview_mode(img):
    _circle(img, 8, 6, 3, YELLOW)
    for (x, y) in ((6, 3), (10, 3), (5, 6), (11, 6), (6, 9), (10, 9)):
        px(img, x, y, BLACK)
    rect(img, 7, 2, 9, 2, BLACK)
    rect(img, 6, 10, 10, 11, GREY_DARK)
    rect(img, 7, 12, 9, 12, BLACK)


NAME_TO_FUNC = {
    name[len("icon_"):]: func
    for name, func in list(globals().items())
    if name.startswith("icon_") and callable(func)
}


def generate_all(out_dir=OUT_DIR):
    # v2 (per live user correction): NO per-icon drop_shadow() bevel.
    # The first pass embossed every icon with its own raised-button
    # shadow, which on top of the toolbar's own button chrome read as
    # "too pixelarty" - two stacked 3D effects. These are flat
    # pictograms now, same idea as the Office-97-era reference the user
    # pointed at: a clean outlined glyph, not a tiny button of its own.
    # drop_shadow() itself stays defined (unused) in case a later,
    # single-source-of-bevel decision wants it back.
    for name, func in sorted(NAME_TO_FUNC.items()):
        img = _new_image()
        # One look everywhere in EPW Studio (user request, 2026-09-13): every
        # pictogram sits on the same raised tile as the electricity and
        # water icons. The medium icons draw their own coloured tile.
        if not name.startswith("medium_"):
            _raised_tile(img, GREY_LIGHT)
        func(img)
        path = os.path.join(out_dir, f"{name}.png")
        img.save(path, "PNG")
    return sorted(NAME_TO_FUNC.keys())


def export_synoptic_icon_data(names, out_dir=OUT_DIR):
    """Writes the same pixels for the Synoptic web editor
    (synoptic/src/components/icons/studioIconData.ts), so its toolbars show
    exactly the icons Studio's own toolbar does. Each icon is a list of
    horizontal runs "x,y,width,RRGGBB" separated by ";"."""
    target = os.path.normpath(os.path.join(out_dir, "..", "..", "synoptic", "src", "components", "icons", "studioIconData.ts"))
    lines = [
        "// GENERATED by studio/shell/icons/generate_icons.py - do not edit.",
        "// The shell's icon PNGs as pixel runs, drawn by StudioIcon.tsx.",
        "",
        "export const STUDIO_ICONS: Record<string, string> = {",
    ]
    for name in names:
        img = QImage(os.path.join(out_dir, f"{name}.png"))
        runs = []
        for y in range(img.height()):
            x = 0
            while x < img.width():
                c = img.pixelColor(x, y)
                if c.alpha() == 0:
                    x += 1
                    continue
                start = x
                key = (c.red(), c.green(), c.blue())
                while x < img.width():
                    d = img.pixelColor(x, y)
                    if d.alpha() == 0 or (d.red(), d.green(), d.blue()) != key:
                        break
                    x += 1
                runs.append(f"{start},{y},{x - start},{key[0]:02X}{key[1]:02X}{key[2]:02X}")
        lines.append(f"  {name}: '{';'.join(runs)}',")
    lines.append("};")
    lines.append("")
    with open(target, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    return target


def build_contact_sheet(names, out_path, cols=8, cell=64, scale=3):
    from PySide6.QtGui import QPainter, QFont, QPixmap
    rows = (len(names) + cols - 1) // cols
    sheet = QImage(cell * cols, cell * rows, QImage.Format.Format_ARGB32)
    sheet.fill(QColor(0xC0, 0xC0, 0xC0))
    painter = QPainter(sheet)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    painter.setFont(QFont("Tahoma", 7))
    for i, name in enumerate(names):
        col, row = i % cols, i // cols
        icon_path = os.path.join(OUT_DIR, f"{name}.png")
        pm = QPixmap(icon_path)
        big = pm.scaled(SIZE * scale, SIZE * scale)
        x = col * cell + (cell - big.width()) // 2
        y = row * cell + 4
        painter.drawPixmap(x, y, big)
        painter.drawText(col * cell + 2, row * cell + cell - 6, name[:12])
    painter.end()
    sheet.save(out_path, "PNG")


if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    all_names = generate_all()
    print(f"generated {len(all_names)} icons: {', '.join(all_names)}")
    sheet_path = os.path.join(OUT_DIR, "_contact_sheet.png")
    build_contact_sheet(all_names, sheet_path)
    print(f"contact sheet: {sheet_path}")
    ts_path = export_synoptic_icon_data(all_names)
    print(f"synoptic icon data: {ts_path}")
