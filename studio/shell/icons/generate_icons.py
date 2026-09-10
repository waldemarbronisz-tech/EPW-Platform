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
    # Scissors, redrawn (v2 - v1 read as an unreadable blob): two silver
    # blades converging on a pivot to a point on the right, black finger
    # rings on the left.
    pivot = (8, 8)
    line(img, 3, 3, *pivot, GREY_LIGHT)
    line(img, *pivot, 14, 6, GREY_LIGHT)
    line(img, 3, 13, *pivot, GREY_LIGHT)
    line(img, *pivot, 14, 10, GREY_LIGHT)
    for (bx, by) in ((3, 3), (3, 13)):
        ring = _circle(img, bx, by, 2, WHITE)
        for (x, y) in ring:
            if (x - bx) ** 2 + (y - by) ** 2 >= 2:
                px(img, x, y, BLACK)
    px(img, 8, 8, BLACK)
    tri1 = [(13, 5), (14, 6), (13, 7)]
    tri2 = [(13, 9), (14, 10), (13, 11)]
    _fill_triangle(img, tri1, GREY_DARK)
    _fill_triangle(img, tri2, GREY_DARK)


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


def icon_medium_electrical(img):
    pts = [(9, 1), (5, 8), (8, 8), (6, 15), (12, 6), (9, 6)]
    _fill_polygon(img, pts, YELLOW)
    _polygon_outline(img, pts, BLACK)


def icon_medium_water(img):
    # Blue droplet approximated as circle + tapered top, pixel-built.
    _circle(img, 8, 10, 4, NAVY)
    for row, half in enumerate((0, 1, 2, 3)):
        y = 6 - row
        for x in range(8 - half, 8 + half + 1):
            px(img, x, y, NAVY)
    for (x, y) in list(_opaque_pixels_subset(img, 3, 3, 13, 13)):
        pass
    px(img, 6, 9, QColor(150, 190, 255))  # highlight


def icon_medium_ventilation(img):
    # Redrawn (v2 - v1's blades were too thin/faint to read at 16px).
    # A fan grille ring with three fat paddle blades around a hub.
    ring = _circle(img, 8, 8, 7, TRANSPARENT)
    for x in range(1, 16):
        for y in range(1, 16):
            d2 = (x - 8) ** 2 + (y - 8) ** 2
            if 44 <= d2 <= 56:
                px(img, x, y, GREY_LIGHT)
    for ang in (90, 210, 330):
        a = math.radians(ang)
        tip = (8 + 5.5 * math.cos(a), 8 + 5.5 * math.sin(a))
        left = math.radians(ang + 110)
        right = math.radians(ang - 40)
        p1 = (8 + 2.5 * math.cos(left), 8 + 2.5 * math.sin(left))
        p2 = (8 + 2.5 * math.cos(right), 8 + 2.5 * math.sin(right))
        tri = [(8, 8), (round(p1[0]), round(p1[1])), (round(tip[0]), round(tip[1]))]
        _fill_triangle(img, tri, GREY_DARK)
        tri2 = [(8, 8), (round(tip[0]), round(tip[1])), (round(p2[0]), round(p2[1]))]
        _fill_triangle(img, tri2, GREY_DARK)
    _circle(img, 8, 8, 2, BLACK)


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
    rect(img, 6, 6, 10, 10, GREY_LIGHT)
    outline_rect(img, 6, 6, 10, 10, BLACK)
    cx = 8
    last = None
    for deg in range(200, 470, 10):
        a = math.radians(deg if not flip else 360 - deg)
        x = round(cx + 6 * math.cos(a))
        y = round(3 + 6 * math.sin(a))
        px(img, x, y, GREY_DARK)
        last = (x, y)
    d = -1 if not flip else 1
    tri = [(last[0], last[1]), (last[0] + d * 3, last[1] - 2), (last[0] + d * 3, last[1] + 2)]
    _fill_triangle(img, tri, GREY_DARK)


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
    _circle(img, 8, 8, 3, GREY_LIGHT)
    for ang in range(0, 360, 45):
        a = math.radians(ang)
        x = round(8 + 6 * math.cos(a))
        y = round(8 + 6 * math.sin(a))
        rect(img, x - 1, y - 1, x + 1, y + 1, GREY_DARK)
    _circle(img, 8, 8, 4, GREY_LIGHT)
    _circle(img, 8, 8, 1, WHITE)
    outline_rect(img, 7, 7, 9, 9, BLACK)


def icon_about(img):
    _circle(img, 8, 8, 7, NAVY)
    for (x, y) in [(7, 4), (8, 4), (7, 6), (8, 6), (7, 7), (8, 7), (7, 8), (8, 8), (7, 9), (8, 9), (7, 10), (8, 10)]:
        px(img, x, y, WHITE)


def icon_compile(img):
    _circle(img, 6, 6, 3, GREY_LIGHT)
    for ang in range(0, 360, 60):
        a = math.radians(ang)
        x = round(6 + 5 * math.cos(a))
        y = round(6 + 5 * math.sin(a))
        rect(img, x - 1, y - 1, x + 1, y + 1, GREY_DARK)
    for d in range(2):
        line(img, 9, 12 + d, 11, 14 + d, GREEN)
        line(img, 11, 14 + d, 15, 8 + d, GREEN)


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
        func(img)
        path = os.path.join(out_dir, f"{name}.png")
        img.save(path, "PNG")
    return sorted(NAME_TO_FUNC.keys())


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
