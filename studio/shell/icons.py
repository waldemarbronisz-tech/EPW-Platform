"""Studio's own icon set - task "Studio: wyostrzenie stylu — wspólny
rdzeń", Problem 3/4: "Dziś pasek kontekstowy to szerokie przyciski
TEKSTOWE... ikony 16x16, tekst wyłącznie w podpowiedzi" and "zanim
narysujesz własne: sprawdź, co ma runtime/epw_os/gui/ i Logic Studio.
Jeśli tam są dobre — użyj ich."

Checked first, per that instruction: runtime/epw_os/gui/ has no
procedural icon module at all (its own custom-painted glyphs live
inline in nav_tree.py, for tree state, not editing commands) - nothing
to reuse from there. logic_studio.ui.icons.action_icon() DOES have a
real, already-integrated set - icon() below re-exports every name that
already exists there unchanged (new/open/save/save_as/copy/paste/cut/
delete/undo/redo/compile/start/pause/stop/zoom_in/zoom_out/grid/snap/
about/settings/help - the last four of those, copy/paste/cut/delete,
were ADDED to that module by this same task, not invented separately
here, so Logic Studio's own Edit menu also gained real icons instead of
plain text as a side effect).

Everything below _EXTRA_NAMES is new - Synoptic-domain tools
(draw wire/frame/building, medium, wire style, routing mode, align/
distribute, front/back, lock, rotate, the four screen elements) and a
few Logic-only actions that still had no icon (reset_zoom, the align
popup, enable/disable selected, toolbar display style, project/export
actions, the two extra Help entries) - none of it existed in either
runtime or Logic Studio to reuse, so it is drawn here, in the same hand
(QPainter, style.COLOR_OUTLINE-equivalent black, 1.4px pen, no fill
except where a shape needs one to read correctly)."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF

_OUTLINE = QColor(0, 0, 0)
_WHITE = QColor(255, 255, 255)

_cache = {}

# Names already drawn by logic_studio.ui.icons.action_icon() - re-exported
# as-is, not redrawn, so both editors' chrome shares literal pixels for
# these, not just a similar style.
_REEXPORTED = {
    "new", "open", "save", "save_as", "copy", "paste", "cut", "delete",
    "undo", "redo", "compile", "start", "pause", "stop", "zoom_in",
    "zoom_out", "grid", "snap", "about", "settings", "help",
}


def icon(name: str, size: int = 16) -> QIcon:
    if name in _REEXPORTED:
        from studio.shell.logic_panel import _ensure_logic_studio_importable
        _ensure_logic_studio_importable()
        from logic_studio.ui.icons import action_icon
        return action_icon(name, size=size)

    key = (name, size)
    if key in _cache:
        return _cache[key]

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(_OUTLINE, 1.4))
    painter.setBrush(Qt.BrushStyle.NoBrush)

    m = size * 0.16
    rect = QRectF(m, m, size - 2 * m, size - 2 * m)
    cx, cy = size / 2, size / 2
    w, h = rect.width(), rect.height()

    _draw(painter, name, rect, cx, cy, w, h)

    painter.end()
    result = QIcon(pixmap)
    _cache[key] = result
    return result


def _draw(p: QPainter, name: str, rect: QRectF, cx: float, cy: float, w: float, h: float):
    left, top, right, bottom = rect.left(), rect.top(), rect.right(), rect.bottom()

    if name == "reset_zoom":
        # A magnifying glass (same motif zoom_in/zoom_out already use in
        # logic_studio.ui.icons - circle + handle) with "1:1" inside
        # instead of a +/- sign - "back to 100%", not a rotation, so it
        # deliberately does NOT borrow the rotate_left/right glyph.
        glass = QRectF(rect.left(), rect.top(), w * 0.72, h * 0.72)
        p.drawEllipse(glass)
        p.drawLine(glass.bottomRight() - QPointF(2, 2), rect.bottomRight())
        f = p.font()
        f.setPixelSize(max(6, int(w * 0.32)))
        p.setFont(f)
        p.drawText(glass, Qt.AlignmentFlag.AlignCenter, "1:1")

    elif name == "reroute":
        # A zigzag with an arrowhead - "the wire's path changes", not a
        # straight line.
        pts = [QPointF(left, bottom), QPointF(left + w * 0.4, bottom),
               QPointF(left + w * 0.4, top + h * 0.3), QPointF(right, top + h * 0.3)]
        p.drawPolyline(QPolygonF(pts))
        _arrowhead(p, pts[-2], pts[-1])

    elif name == "draw_wire":
        p.drawLine(QPointF(left, bottom), QPointF(right, top))
        p.setBrush(_OUTLINE)
        p.drawEllipse(QPointF(left, bottom), 2, 2)
        p.drawEllipse(QPointF(right, top), 2, 2)

    elif name == "draw_frame":
        pen = p.pen()
        pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.drawRect(rect)

    elif name == "draw_building":
        base = QRectF(left, cy, w, h * 0.5)
        p.drawRect(base)
        roof = QPolygonF([QPointF(left, cy), QPointF(cx, top), QPointF(right, cy)])
        p.drawPolygon(roof)

    elif name == "medium_electrical":
        bolt = QPolygonF([
            QPointF(cx + w * 0.05, top), QPointF(left + w * 0.15, cy + h * 0.05),
            QPointF(cx, cy + h * 0.05), QPointF(cx - w * 0.05, bottom),
            QPointF(right - w * 0.15, cy - h * 0.05), QPointF(cx, cy - h * 0.05),
        ])
        p.setBrush(_OUTLINE)
        p.drawPolygon(bolt)

    elif name == "medium_water":
        # A real teardrop (a straight taper into a round bottom), not a
        # 4-point polygon - a diamond made of dead-straight edges reads
        # as a diamond, not a drop of water, at any size.
        path = QPainterPath(QPointF(cx, top))
        path.cubicTo(QPointF(right + w * 0.05, cy + h * 0.25), QPointF(right - w * 0.05, bottom),
                     QPointF(cx, bottom))
        path.cubicTo(QPointF(left + w * 0.05, bottom), QPointF(left - w * 0.05, cy + h * 0.25),
                     QPointF(cx, top))
        p.drawPath(path)

    elif name == "medium_ventilation":
        # Three short blades around the center - a stand-in fan glyph,
        # simpler than a literal fan at 16px.
        for i in range(3):
            a = math.radians(90 + i * 120)
            p.drawLine(QPointF(cx, cy), QPointF(cx + w * 0.42 * math.cos(a), cy + h * 0.42 * math.sin(a)))
        p.setBrush(_OUTLINE)
        p.drawEllipse(QPointF(cx, cy), 1.6, 1.6)

    elif name == "wire_style_normal":
        p.drawLine(QPointF(left, cy), QPointF(right, cy))

    elif name == "wire_style_bus":
        pen = p.pen()
        pen.setWidthF(3.2)
        p.setPen(pen)
        p.drawLine(QPointF(left, cy), QPointF(right, cy))

    elif name == "routing_direct":
        # A straight line WITH an arrowhead - "goes directly there" -
        # deliberately distinct from draw_wire's plain dotted line
        # above (same diagonal, different meaning: draw_wire is a
        # drawing TOOL, this is a routing MODE), and from
        # routing_avoid's zigzag below.
        p.drawLine(QPointF(left, bottom), QPointF(right, top))
        _arrowhead(p, QPointF(left, bottom), QPointF(right, top))

    elif name == "routing_avoid":
        pts = [QPointF(left, bottom), QPointF(left + w * 0.35, bottom),
               QPointF(left + w * 0.35, top), QPointF(left + w * 0.65, top),
               QPointF(left + w * 0.65, bottom), QPointF(right, bottom)]
        p.drawPolyline(QPolygonF(pts))

    elif name in ("distribute_h", "distribute_v"):
        bars = 3
        for i in range(bars):
            t = i / (bars - 1)
            if name == "distribute_h":
                x = left + t * w
                p.drawLine(QPointF(x, top), QPointF(x, bottom))
            else:
                y = top + t * h
                p.drawLine(QPointF(left, y), QPointF(right, y))

    elif name in ("align_left", "align_center", "align_right", "align_middle"):
        if name == "align_left":
            p.drawLine(QPointF(left, top), QPointF(left, bottom))
            xs = [left, left + w * 0.35, left + w * 0.6]
        elif name == "align_right":
            p.drawLine(QPointF(right, top), QPointF(right, bottom))
            xs = [right, right - w * 0.35, right - w * 0.6]
        elif name == "align_center":
            p.drawLine(QPointF(cx, top), QPointF(cx, bottom))
            xs = None
        else:
            p.drawLine(QPointF(left, cy), QPointF(right, cy))
            xs = None
        if xs is not None:
            for i, x in enumerate(xs):
                y0 = top + h * 0.15 * (i + 1)
                p.drawLine(QPointF(x, y0), QPointF(x + (w * 0.3 if name == "align_left" else -w * 0.3), y0))
        elif name == "align_center":
            for i in range(3):
                y0 = top + h * 0.22 * (i + 1)
                half = w * (0.32 - i * 0.06)
                p.drawLine(QPointF(cx - half, y0), QPointF(cx + half, y0))
        else:
            for i in range(3):
                x0 = left + w * 0.22 * (i + 1)
                half = h * (0.32 - i * 0.06)
                p.drawLine(QPointF(x0, cy - half), QPointF(x0, cy + half))

    elif name in ("bring_front", "send_back"):
        back = QRectF(left, top, w * 0.7, h * 0.7)
        front = QRectF(left + w * 0.3, top + h * 0.3, w * 0.7, h * 0.7)
        first, second = (back, front) if name == "send_back" else (front, back)
        p.setBrush(_WHITE)
        p.drawRect(second)
        pen = p.pen()
        pen.setWidthF(2.0)
        p.setPen(pen)
        p.drawRect(first)

    elif name in ("lock", "unlock"):
        body = QRectF(left, cy, w, h * 0.5)
        p.drawRect(body)
        shackle_rect = QRectF(cx - w * 0.22, top, w * 0.44, h * 0.55)
        if name == "lock":
            p.drawArc(shackle_rect, 0, 180 * 16)
        else:
            shackle_rect.moveLeft(shackle_rect.left() + w * 0.12)
            shackle_rect.moveTop(shackle_rect.top() - h * 0.05)
            p.drawArc(shackle_rect, 0, 180 * 16)

    elif name in ("rotate_left", "rotate_right"):
        flip = -1 if name == "rotate_right" else 1
        p.drawArc(rect, 30 * 16, 270 * 16 * flip)
        angle = math.radians(30 if flip == 1 else 300)
        tip = QPointF(cx + (w / 2) * math.cos(angle), cy + (h / 2) * math.sin(angle))
        tangent = angle + flip * math.pi / 2
        head = QPolygonF([
            tip,
            tip + QPointF(4 * math.cos(tangent + 2.4), 4 * math.sin(tangent + 2.4)),
            tip + QPointF(4 * math.cos(tangent - 2.4), 4 * math.sin(tangent - 2.4)),
        ])
        p.setBrush(_OUTLINE)
        p.drawPolygon(head)

    elif name == "add_meter":
        p.drawArc(QRectF(left, top, w, h * 1.3), 20 * 16, 140 * 16)
        p.drawLine(QPointF(cx, cy + h * 0.1), QPointF(cx + w * 0.28, cy - h * 0.18))
        p.setBrush(_OUTLINE)
        p.drawEllipse(QPointF(cx, cy + h * 0.1), 1.5, 1.5)

    elif name == "add_signal_panel":
        p.drawRect(rect)
        p.setBrush(_OUTLINE)
        p.drawEllipse(QPointF(cx, cy), h * 0.16, h * 0.16)

    elif name == "add_group_command":
        p.drawRoundedRect(rect, 3, 3)
        p.drawLine(QPointF(cx, top + h * 0.2), QPointF(cx, cy))
        p.drawArc(QRectF(cx - w * 0.25, cy - h * 0.05, w * 0.5, h * 0.45), -60 * 16, 300 * 16)

    elif name == "add_setpoint_panel":
        p.drawLine(QPointF(left, cy), QPointF(right, cy))
        marker = QPolygonF([
            QPointF(cx - w * 0.4, cy - h * 0.18), QPointF(cx - w * 0.25, cy),
            QPointF(cx - w * 0.4, cy + h * 0.18),
        ])
        p.setBrush(_OUTLINE)
        p.drawPolygon(marker)

    elif name == "scada_preview":
        p.drawRect(QRectF(left, top, w, h * 0.72))
        p.drawLine(QPointF(cx - w * 0.18, bottom - h * 0.02), QPointF(cx + w * 0.18, bottom - h * 0.02))
        p.drawLine(QPointF(cx, top + h * 0.72), QPointF(cx, bottom - h * 0.02))

    elif name in ("project_registers", "device_list"):
        p.drawRect(rect)
        rows = 3
        for i in range(1, rows):
            y = top + h * i / rows
            p.drawLine(QPointF(left, y), QPointF(right, y))
        if name == "device_list":
            p.drawLine(QPointF(cx, top), QPointF(cx, bottom))

    elif name == "background_color":
        p.drawRect(rect)
        p.setBrush(_OUTLINE)
        half = QPolygonF([QPointF(left, top), QPointF(right, top), QPointF(left, bottom)])
        p.drawPolygon(half)

    elif name == "compare":
        left_doc = QRectF(left, top + h * 0.1, w * 0.38, h * 0.8)
        right_doc = QRectF(right - w * 0.38, top + h * 0.1, w * 0.38, h * 0.8)
        p.drawRect(left_doc)
        p.drawRect(right_doc)
        p.drawLine(QPointF(left_doc.right() + 1, cy), QPointF(right_doc.left() - 1, cy))

    elif name == "align_popup":
        for i, y_frac in enumerate((0.15, 0.5, 0.85)):
            y = top + h * y_frac
            end = right if i != 1 else right - w * 0.25
            p.drawLine(QPointF(left, y), QPointF(end, y))

    elif name in ("enable_selected", "disable_selected"):
        p.drawEllipse(rect)
        if name == "disable_selected":
            p.drawLine(QPointF(left + w * 0.15, bottom - h * 0.15), QPointF(right - w * 0.15, top + h * 0.15))

    elif name == "toolbar_style_icons":
        for i in range(2):
            p.drawRect(QRectF(left + i * w * 0.55, top, w * 0.4, w * 0.4))

    elif name == "toolbar_style_icons_text":
        p.drawRect(QRectF(left, top, w * 0.32, w * 0.32))
        for i, y_frac in enumerate((0.15, 0.45)):
            y = top + h * 0.55 + h * y_frac * 0.4
            p.drawLine(QPointF(left, y), QPointF(right, y))

    elif name == "toolbar_style_text":
        for i, y_frac in enumerate((0.15, 0.45, 0.75)):
            y = top + h * y_frac
            p.drawLine(QPointF(left, y), QPointF(right, y))

    elif name == "export":
        body = QRectF(left, top + h * 0.3, w * 0.6, h * 0.7)
        p.drawRect(body)
        p.drawLine(QPointF(cx + w * 0.05, top + h * 0.35), QPointF(right, top))
        _arrowhead(p, QPointF(cx - w * 0.1, top + h * 0.15), QPointF(right, top))

    elif name == "help_catalog":
        # A book: a spine (the extra vertical line near the left edge)
        # plus ruled pages - NOT the two-overlapping-rects silhouette
        # "copy" already uses elsewhere in this same toolbar, and not
        # the plain ruled table project_registers/device_list use
        # (different context, never shown side by side, but still its
        # own distinct shape rather than a near-duplicate).
        p.drawRect(rect)
        p.drawLine(QPointF(left + w * 0.22, top), QPointF(left + w * 0.22, bottom))
        for i in range(1, 4):
            y = top + h * i / 4
            p.drawLine(QPointF(left + w * 0.34, y), QPointF(right - w * 0.1, y))

    elif name == "help_shortcuts":
        p.drawRoundedRect(rect, 2, 2)
        p.drawLine(QPointF(cx, top + h * 0.3), QPointF(cx, bottom - h * 0.3))

    else:
        p.drawRect(rect)


def _arrowhead(p: QPainter, from_pt: QPointF, to_pt: QPointF, size: float = 4.0):
    angle = math.atan2(to_pt.y() - from_pt.y(), to_pt.x() - from_pt.x())
    head = QPolygonF([
        to_pt,
        to_pt - QPointF(size * math.cos(angle - 0.5), size * math.sin(angle - 0.5)),
        to_pt - QPointF(size * math.cos(angle + 0.5), size * math.sin(angle + 0.5)),
    ])
    p.setBrush(_OUTLINE)
    p.drawPolygon(head)
