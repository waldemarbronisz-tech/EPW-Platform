"""SPIKE - generic PySide6 renderer prototype for Path C.

Reads shared/docs/spike/geometry_sample.json (produced by
spike/geometry_export/extract.mjs) and draws every symbol/state pair
with QPainter. Deliberately generic: this module has ZERO knowledge of
"a valve" or "a fan" - only of six primitive kinds (group/rect/circle/
line/arc/path/text) and how to denormalize+paint each one. That
genericness is the whole point of Path C: the same drawing code would
handle any new symbol the exporter was ever pointed at, with no new
Python written.

Not part of runtime/ - a standalone script, PySide6 only (already a
runtime dependency; nothing new added here), no wiring into EPW-OS.
"""

import json
import math
import os
import sys

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen, QBrush, QImage, QFont
from PySide6.QtWidgets import QApplication

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
GEOMETRY_JSON = os.path.join(REPO_ROOT, "shared", "docs", "spike", "geometry_sample.json")
OUT_DIR = os.path.join(REPO_ROOT, "shared", "docs", "spike")

SCALE = 4  # same upscale factor as render_editor_reference.mjs, for a like-for-like comparison
CELL_PAD = 44
LABEL_H = 22


def _color(value, default=Qt.GlobalColor.transparent):
    """Konva accepts CSS color strings ('green', '#7f8c8d', 'rgba(255,0,0,0.3)')
    and the bare string 'none' (meaning: don't paint this). QColor parses
    named colors and #hex natively; rgba(...)/none need a little help."""
    if value is None:
        return QColor(default)
    if value == "none":
        return QColor(0, 0, 0, 0)
    if isinstance(value, str) and value.startswith("rgba"):
        nums = value[value.index("(") + 1 : value.index(")")].split(",")
        r, g, b = (int(float(n)) for n in nums[:3])
        a = float(nums[3])
        return QColor(r, g, b, int(a * 255))
    c = QColor(value)
    return c if c.isValid() else QColor(default)


def _draw_group(painter: QPainter, node: dict, w: float, h: float):
    painter.save()
    x = node.get("x", 0) * w
    y = node.get("y", 0) * h
    painter.translate(x, y)
    if node.get("rotation_deg"):
        painter.rotate(node["rotation_deg"])
    for child in node.get("children", []):
        _draw_primitive(painter, child, w, h)
    painter.restore()


def _apply_style(painter: QPainter, node: dict):
    fill = node.get("fill")
    stroke = node.get("stroke")
    stroke_width = node.get("strokeWidth")
    opacity = node.get("opacity")

    painter.setOpacity(opacity if opacity is not None else 1.0)
    painter.setBrush(QBrush(_color(fill)) if fill is not None else QBrush(Qt.BrushStyle.NoBrush))
    if stroke is not None and stroke != "none":
        pen = QPen(_color(stroke))
        pen.setWidthF(stroke_width if stroke_width is not None else 1.0)
        # Canvas/Konva's default line cap is 'butt' (a dash segment ends
        # exactly at its own length, no extension). Qt's default is
        # SquareCap, which extends each dash by half the pen width at
        # BOTH ends - for a dash pattern whose gap is smaller than the
        # pen width (common: SYMBOL_STROKE=5 with dash=[4,2] here), that
        # extension is enough to visually merge adjacent dashes into
        # what looks like a solid line. FOUND via this exact comparison
        # (electrical.circuit_breaker's FAULT overlay renders solid
        # instead of dotted without this) - see the spike report's 1.4.
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        dash = node.get("dash")
        if dash:
            pen.setStyle(Qt.PenStyle.CustomDashLine)
            pen.setDashPattern([d / (stroke_width or 1.0) for d in dash])
        painter.setPen(pen)
    else:
        painter.setPen(Qt.PenStyle.NoPen)


def _draw_rect(painter: QPainter, node: dict, w: float, h: float):
    _apply_style(painter, node)
    rect = QRectF(node["x"] * w, node["y"] * h, node["width"] * w, node["height"] * h)
    painter.drawRect(rect)


def _draw_circle(painter: QPainter, node: dict, w: float, h: float):
    _apply_style(painter, node)
    cx, cy, r = node["x"] * w, node["y"] * h, node["radius"] * w
    painter.drawEllipse(QPointF(cx, cy), r, r)


def _draw_line(painter: QPainter, node: dict, w: float, h: float):
    _apply_style(painter, node)
    pts = node.get("points", [])
    poly = []
    for i in range(0, len(pts) - 1, 2):
        axis_w = w if i % 4 == 0 else w  # x is always even index
        poly.append(QPointF(pts[i] * w, pts[i + 1] * h))
    if len(poly) >= 2:
        for i in range(len(poly) - 1):
            painter.drawLine(poly[i], poly[i + 1])


def _draw_arc(painter: QPainter, node: dict, w: float, h: float):
    """Konva.Arc: x/y = center, innerRadius/outerRadius, angle = sweep
    (degrees), rotation = start angle - all measured CLOCKWISE from the
    3-o'clock direction (standard 2D-canvas convention, y-down). Qt's
    QPainterPath.arcTo takes plain degrees too, but COUNTERCLOCKWISE
    from 3-o'clock - hence the sign flip on both angles below."""
    _apply_style(painter, node)
    cx, cy = node["x"] * w, node["y"] * h
    outer_r = node["outer_radius"] * w
    inner_r = node.get("inner_radius", 0) * w
    start_deg = -node.get("rotation_deg", 0)
    sweep_deg = -node.get("angle_deg", 0)

    path = QPainterPath()
    outer_rect = QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)
    if inner_r <= 0:
        path.moveTo(cx, cy)
        path.arcTo(outer_rect, start_deg, sweep_deg)
        path.closeSubpath()
    else:
        inner_rect = QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)
        path.arcMoveTo(outer_rect, start_deg)
        path.arcTo(outer_rect, start_deg, sweep_deg)
        path.arcTo(inner_rect, start_deg + sweep_deg, -sweep_deg)
        path.closeSubpath()
    painter.drawPath(path)


def _draw_path(painter: QPainter, node: dict, w: float, h: float):
    """Parses the SAME normalized 'M x y L x y ... Z' grammar
    extract.mjs emits (absolute moveto/lineto/closepath only - see that
    script's own normalizePathData() for why nothing else is supported
    yet). Coordinates are already 0..1 fractions here; denormalized by
    (w, h) at draw time, same convention as every other primitive."""
    _apply_style(painter, node)
    data = node.get("data_normalized")
    if not data:
        return  # normalization_warning is set instead - nothing safe to draw
    tokens = data.replace(",", " ").split()
    path = QPainterPath()
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "M":
            path.moveTo(float(tokens[i + 1]) * w, float(tokens[i + 2]) * h)
            i += 3
        elif tok == "L":
            path.lineTo(float(tokens[i + 1]) * w, float(tokens[i + 2]) * h)
            i += 3
        elif tok == "Z":
            path.closeSubpath()
            i += 1
        else:
            i += 1
    painter.drawPath(path)


def _draw_text(painter: QPainter, node: dict, w: float, h: float):
    painter.save()
    _apply_style(painter, node)
    font = QFont()
    if node.get("font_size_px"):
        font.setPixelSize(int(node["font_size_px"]))
    painter.setFont(font)
    x, y = node.get("x", 0) * w, node.get("y", 0) * h
    tw = node.get("width") * w if node.get("width") else w
    th = node.get("height") * h if node.get("height") else h
    painter.drawText(QRectF(x, y, tw, th), Qt.AlignmentFlag.AlignCenter, node.get("text") or "")
    painter.restore()


_DRAWERS = {
    "group": _draw_group,
    "rect": _draw_rect,
    "circle": _draw_circle,
    "line": _draw_line,
    "arc": _draw_arc,
    "path": _draw_path,
    "text": _draw_text,
}


def _draw_primitive(painter: QPainter, node: dict, w: float, h: float):
    if node is None:
        return
    kind = node.get("primitive")
    drawer = _DRAWERS.get(kind)
    if drawer is None:
        # An unsupported/unrecognized primitive - drawn as a visible
        # magenta "unknown" marker rather than silently skipped, so a
        # real gap in this prototype shows up in the output image, not
        # just in a log nobody reads before shipping.
        painter.save()
        painter.setPen(QPen(QColor("magenta"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(0, 0, w, h))
        painter.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, f"?{kind}")
        painter.restore()
        return
    drawer(painter, node, w, h)


def render_state_to_image(state_tree: dict, ref_w: int, ref_h: int) -> QImage:
    cell_w, cell_h = ref_w * SCALE, ref_h * SCALE
    image = QImage(cell_w, cell_h, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    _draw_primitive(painter, state_tree, cell_w, cell_h)
    painter.end()
    return image


def main():
    app = QApplication.instance() or QApplication(sys.argv)

    with open(GEOMETRY_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    symbols = data["symbols"]
    col_count = max(len(s["allowed_states"]) for s in symbols.values())
    col_width = max(s["reference_width"] for s in symbols.values()) * SCALE + CELL_PAD
    row_heights = [s["reference_height"] * SCALE + LABEL_H + CELL_PAD for s in symbols.values()]

    total_w = CELL_PAD + col_count * col_width
    total_h = CELL_PAD + sum(row_heights)

    composite = QImage(total_w, total_h, QImage.Format.Format_ARGB32)
    composite.fill(Qt.GlobalColor.white)
    painter = QPainter(composite)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    label_font = QFont()
    label_font.setBold(True)
    label_font.setPixelSize(13)
    state_font = QFont()
    state_font.setPixelSize(11)

    y = CELL_PAD
    for symbol_type, symbol in symbols.items():
        ref_w, ref_h = symbol["reference_width"], symbol["reference_height"]
        painter.setFont(label_font)
        painter.setPen(QColor("black"))
        anim = symbol.get("animation")
        anim_note = f" [animation: {anim['type']}]" if anim else ""
        painter.drawText(
            QPointF(CELL_PAD, y - 4),
            f"{symbol_type}  ({ref_w}x{ref_h}, PySide6/QPainter, generic primitive renderer){anim_note}",
        )

        x = CELL_PAD
        for state in symbol["allowed_states"]:
            cell_w, cell_h = ref_w * SCALE, ref_h * SCALE
            painter.fillRect(QRectF(x, y + LABEL_H, cell_w, cell_h), QColor("#f0f0f0"))
            cell_image = render_state_to_image(symbol["states"][state], ref_w, ref_h)
            painter.drawImage(QPointF(x, y + LABEL_H), cell_image)
            painter.setPen(QColor("#cccccc"))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(x, y + LABEL_H, cell_w, cell_h))
            painter.setFont(state_font)
            painter.setPen(QColor("#333333"))
            painter.drawText(QPointF(x, y + LABEL_H + cell_h + 14), state)
            x += col_width
        y += ref_h * SCALE + LABEL_H + CELL_PAD

    painter.end()
    out_path = os.path.join(OUT_DIR, "pyside_prototype.png")
    composite.save(out_path, "PNG")
    print(f"Wrote {out_path} ({total_w}x{total_h})")


if __name__ == "__main__":
    main()
