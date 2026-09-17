"""Draws a primitive tree from shared/symbols/geometry.json with
QPainter. Generic on purpose: this module knows nine primitive kinds
(group, rect, circle, ellipse, line, path, text, arc, wedge) and how
Konva positions and styles each one - it knows no symbol by name, so a
new symbol in the editor's library needs a re-export, never new Python.

Konva conventions reproduced here (all checked against the editor's
own rendering in the spike comparison, shared/docs/spike):
  - a node's transform is translate(x, y) . rotate(rotation) .
    scale(scaleX, scaleY) . translate(-offsetX, -offsetY); children of a
    group live inside their parent's transform;
  - rect/text: (0,0) is the top-left corner after the transform;
    circle/ellipse/arc/wedge: (0,0) is the centre; a line's points are
    absolute inside its own transform;
  - stroke width does not scale with the node (Konva strokeScaleEnabled
    defaults to true, actually - so it does; kept);
  - line cap defaults to butt, join to miter, opacity multiplies down
    the tree, dash is in pixels, cornerRadius rounds a rect;
  - text: fontSize 12 / Arial / normal by default, `width` fixes the box
    (with align), `height` with verticalAlign; without width the text
    is as wide as it measures.

Animation: geometry carries the base pose. Two directives are applied
here from a monotonic phase (ms): blink (the BLINK state alternates
between the ON and OFF trees every half period) and dash_march (dashed
strokes scroll). A rotating symbol keeps its base pose - which part
rotates is not in the export.
"""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen

from epw_os.gui.synoptic.geometry import resolve_template
from epw_os.gui.synoptic.svg_path import SvgPathError, parse_svg_path

_CAPS = {"butt": Qt.PenCapStyle.FlatCap, "round": Qt.PenCapStyle.RoundCap, "square": Qt.PenCapStyle.SquareCap}
_JOINS = {"miter": Qt.PenJoinStyle.MiterJoin, "round": Qt.PenJoinStyle.RoundJoin, "bevel": Qt.PenJoinStyle.BevelJoin}
_ALIGN = {"left": Qt.AlignmentFlag.AlignLeft, "center": Qt.AlignmentFlag.AlignHCenter, "right": Qt.AlignmentFlag.AlignRight,
          "justify": Qt.AlignmentFlag.AlignJustify}
_VALIGN = {"top": Qt.AlignmentFlag.AlignTop, "middle": Qt.AlignmentFlag.AlignVCenter, "bottom": Qt.AlignmentFlag.AlignBottom}
_NAMED = {"transparent": QColor(0, 0, 0, 0), "none": QColor(0, 0, 0, 0)}


def parse_color(value, default=None):
    """CSS colour string (named, #hex, rgb()/rgba()) -> QColor; None or
    'transparent'/'none' -> fully transparent."""
    if value is None or value == "":
        return QColor(default) if default is not None else None
    if isinstance(value, QColor):
        return value
    text = str(value).strip()
    lowered = text.lower()
    if lowered in _NAMED:
        return QColor(_NAMED[lowered])
    if lowered.startswith("rgb"):
        try:
            nums = [p.strip() for p in text[text.index("(") + 1:text.index(")")].replace("/", ",").split(",") if p.strip()]
            r, g, b = (int(float(n)) for n in nums[:3])
            a = float(nums[3]) if len(nums) > 3 else 1.0
            if a > 1:
                a = a / 255.0
            return QColor(r, g, b, int(round(a * 255)))
        except (ValueError, IndexError):
            return QColor(default) if default is not None else None
    color = QColor(text)
    if color.isValid():
        return color
    return QColor(default) if default is not None else None


class PrimitivePainter:
    """One instance per paint pass. `fields` are the current object's
    per-instance values for templates; `phase_ms` drives animation."""

    def __init__(self, painter: QPainter, fields=None, phase_ms: float = 0.0, warnings=None):
        self.painter = painter
        self.fields = fields or {}
        self.phase_ms = phase_ms
        self.warnings = warnings if warnings is not None else []

    # -- entry -----------------------------------------------------------------------

    def draw_tree(self, nodes, opacity: float = 1.0):
        for node in nodes or []:
            self.draw_node(node, opacity)

    def draw_node(self, node, opacity: float = 1.0):
        if not isinstance(node, dict):
            return
        kind = node.get("primitive")
        if node.get("unsupported") or kind not in _DRAWERS:
            self._unknown(node)
            return
        if self._prop(node, "visible", True) is False:
            return
        node_opacity = opacity * float(self._prop(node, "opacity", 1.0) or 0.0)
        p = self.painter
        p.save()
        try:
            self._apply_transform(node)
            _DRAWERS[kind](self, node, node_opacity)
        finally:
            p.restore()

    # -- helpers -------------------------------------------------------------------------

    def _prop(self, node, key, default=None):
        value = node.get(key, default)
        value = resolve_template(value, self.fields)
        return default if value is None else value

    def _num(self, node, key, default=0.0) -> float:
        value = self._prop(node, key, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    def _apply_transform(self, node):
        p = self.painter
        x, y = self._num(node, "x"), self._num(node, "y")
        if x or y:
            p.translate(x, y)
        rotation = self._num(node, "rotation")
        if rotation:
            p.rotate(rotation)
        sx, sy = self._num(node, "scaleX", 1.0), self._num(node, "scaleY", 1.0)
        if sx != 1.0 or sy != 1.0:
            p.scale(sx, sy)
        ox, oy = self._num(node, "offsetX"), self._num(node, "offsetY")
        if ox or oy:
            p.translate(-ox, -oy)

    def _style(self, node, opacity: float):
        p = self.painter
        p.setOpacity(max(0.0, min(1.0, opacity)))
        fill = parse_color(self._prop(node, "fill"))
        p.setBrush(QBrush(fill) if fill is not None else QBrush(Qt.BrushStyle.NoBrush))
        stroke = parse_color(self._prop(node, "stroke"))
        if stroke is None or stroke.alpha() == 0 and self._prop(node, "stroke") in ("transparent", "none"):
            p.setPen(Qt.PenStyle.NoPen)
            return
        width = self._num(node, "strokeWidth", 2.0)
        pen = QPen(stroke)
        pen.setWidthF(width)
        pen.setCapStyle(_CAPS.get(str(self._prop(node, "lineCap", "butt")).lower(), Qt.PenCapStyle.FlatCap))
        pen.setJoinStyle(_JOINS.get(str(self._prop(node, "lineJoin", "miter")).lower(), Qt.PenJoinStyle.MiterJoin))
        dash = self._prop(node, "dash")
        if isinstance(dash, (list, tuple)) and dash and width > 0:
            pattern = [max(0.01, float(d) / width) for d in dash]
            if len(pattern) % 2:
                pattern = pattern * 2
            pen.setStyle(Qt.PenStyle.CustomDashLine)
            pen.setDashPattern(pattern)
            if node.get("_dash_march"):
                pen.setDashOffset((self.phase_ms / 1000.0 * float(node["_dash_march"])) / width)
        p.setPen(pen)

    def _unknown(self, node):
        self.warnings.append(f"unsupported primitive {node.get('primitive')!r}")
        p = self.painter
        p.save()
        p.setPen(QPen(QColor("magenta"), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(0, 0, 8, 8))
        p.restore()

    # -- primitives ----------------------------------------------------------------------

    def _group(self, node, opacity):
        for child in node.get("children") or []:
            self.draw_node(child, opacity)

    def _rect(self, node, opacity):
        self._style(node, opacity)
        rect = QRectF(0, 0, self._num(node, "width"), self._num(node, "height"))
        radius = self._prop(node, "cornerRadius")
        if isinstance(radius, (list, tuple)):
            radius = max(radius) if radius else 0
        try:
            radius = float(radius or 0)
        except (TypeError, ValueError):
            radius = 0.0
        if radius > 0:
            self.painter.drawRoundedRect(rect, radius, radius)
        else:
            self.painter.drawRect(rect)

    def _circle(self, node, opacity):
        self._style(node, opacity)
        r = self._num(node, "radius")
        self.painter.drawEllipse(QPointF(0, 0), r, r)

    def _ellipse(self, node, opacity):
        self._style(node, opacity)
        rx, ry = self._num(node, "radiusX"), self._num(node, "radiusY")
        self.painter.drawEllipse(QPointF(0, 0), rx, ry)

    def _line(self, node, opacity):
        self._style(node, opacity)
        pts = self._prop(node, "points") or []
        points = [QPointF(float(pts[i]), float(pts[i + 1])) for i in range(0, len(pts) - 1, 2)]
        if len(points) < 2:
            return
        path = QPainterPath(points[0])
        for pt in points[1:]:
            path.lineTo(pt)
        if self._prop(node, "closed", False):
            path.closeSubpath()
            self.painter.drawPath(path)
        else:
            self.painter.save()
            self.painter.setBrush(Qt.BrushStyle.NoBrush)
            self.painter.drawPath(path)
            self.painter.restore()

    def _path(self, node, opacity):
        self._style(node, opacity)
        data = self._prop(node, "data")
        try:
            path = parse_svg_path(data)
        except SvgPathError as e:
            self.warnings.append(f"path data: {e}")
            return
        self.painter.drawPath(path)

    def _arc(self, node, opacity, wedge=False):
        """Konva Arc/Wedge: angle = sweep, rotation already applied as the
        node transform (Konva rotates the node, the arc starts at
        3 o'clock), clockwise in a y-down canvas - Qt's arcTo counts
        counter-clockwise, hence the sign flips."""
        self._style(node, opacity)
        outer = self._num(node, "outerRadius") if not wedge else self._num(node, "radius")
        inner = 0.0 if wedge else self._num(node, "innerRadius")
        sweep = -self._num(node, "angle")
        clockwise = self._prop(node, "clockwise", False)
        if clockwise:
            sweep = -sweep
        path = QPainterPath()
        outer_rect = QRectF(-outer, -outer, 2 * outer, 2 * outer)
        if inner <= 0:
            path.moveTo(0, 0)
            path.arcTo(outer_rect, 0, sweep)
            path.closeSubpath()
        else:
            inner_rect = QRectF(-inner, -inner, 2 * inner, 2 * inner)
            path.arcMoveTo(outer_rect, 0)
            path.arcTo(outer_rect, 0, sweep)
            path.arcTo(inner_rect, sweep, -sweep)
            path.closeSubpath()
        self.painter.drawPath(path)

    def _wedge(self, node, opacity):
        self._arc(node, opacity, wedge=True)

    def _text(self, node, opacity):
        p = self.painter
        p.setOpacity(max(0.0, min(1.0, opacity)))
        text = self._prop(node, "text", "")
        text = "" if text is None else str(text)
        if not text:
            return
        size = self._num(node, "fontSize", 12.0)
        font = QFont()
        family = str(self._prop(node, "fontFamily", "Arial") or "Arial").split(",")[0].strip().strip("'\"")
        font.setFamily(family or "Arial")
        font.setPixelSize(max(1, int(round(size))))
        style = str(self._prop(node, "fontStyle", "normal") or "normal").lower()
        font.setBold("bold" in style)
        font.setItalic("italic" in style)
        decoration = str(self._prop(node, "textDecoration", "") or "").lower()
        font.setUnderline("underline" in decoration)
        p.setFont(font)
        color = parse_color(self._prop(node, "fill"), "#000000")
        p.setPen(QPen(color))
        p.setBrush(Qt.BrushStyle.NoBrush)
        metrics = QFontMetricsF(font)
        line_height = float(self._prop(node, "lineHeight", 1.0) or 1.0)
        padding = self._num(node, "padding", 0.0)
        width = self._prop(node, "width")
        height = self._prop(node, "height")
        wrap = str(self._prop(node, "wrap", "word") or "word").lower()
        flags = _ALIGN.get(str(self._prop(node, "align", "left") or "left").lower(), Qt.AlignmentFlag.AlignLeft)
        flags |= _VALIGN.get(str(self._prop(node, "verticalAlign", "top") or "top").lower(), Qt.AlignmentFlag.AlignTop)
        if wrap != "none":
            flags |= Qt.TextFlag.TextWordWrap
        lines = text.split("\n")
        natural_w = max(metrics.horizontalAdvance(line) for line in lines) + 2 * padding
        natural_h = len(lines) * size * line_height + 2 * padding
        try:
            box_w = float(width) if width not in (None, "", "auto") else natural_w
        except (TypeError, ValueError):
            box_w = natural_w
        try:
            box_h = float(height) if height not in (None, "", "auto") else natural_h
        except (TypeError, ValueError):
            box_h = natural_h
        rect = QRectF(padding, padding, max(1.0, box_w - 2 * padding), max(1.0, box_h - 2 * padding))
        if self._prop(node, "ellipsis", False) and wrap == "none":
            text = metrics.elidedText(text, Qt.TextElideMode.ElideRight, rect.width())
        p.drawText(rect, flags, text)


_DRAWERS = {
    "group": PrimitivePainter._group,
    "rect": PrimitivePainter._rect,
    "circle": PrimitivePainter._circle,
    "ellipse": PrimitivePainter._ellipse,
    "line": PrimitivePainter._line,
    "path": PrimitivePainter._path,
    "text": PrimitivePainter._text,
    "arc": PrimitivePainter._arc,
    "wedge": PrimitivePainter._wedge,
}


def blink_state(animation, state, phase_ms: float):
    """For a symbol whose animation directive is `blink` and whose state
    is the trigger: the state to draw at `phase_ms` (ON/OFF alternate
    every half period). Any other case: the state itself."""
    if not animation or animation.get("type") != "blink" or state != animation.get("trigger_state", "BLINK"):
        return state
    half = float(animation.get("half_period_ms") or 500)
    return "ON" if int(phase_ms // half) % 2 == 0 else "OFF"


def mark_dash_march(tree, animation, state, rate_px_per_sec=None):
    """Tags the dashed strokes of a `dash_march` symbol in its trigger
    state so the painter scrolls them (a private `_dash_march` prop the
    export never writes)."""
    if not animation or animation.get("type") != "dash_march" or state != animation.get("trigger_state"):
        return tree
    rate = float(rate_px_per_sec or animation.get("rate_px_per_sec") or 30)

    def tag(nodes):
        out = []
        for node in nodes or []:
            copy = dict(node)
            if copy.get("dash"):
                copy["_dash_march"] = rate
            if "children" in copy:
                copy["children"] = tag(copy["children"])
            out.append(copy)
        return out
    return tag(tree)


def symbol_bounds(tree, reference_w: float, reference_h: float) -> QRectF:
    """The reference box - the editor's own hit/selection box for a
    symbol is exactly its width x height, not its ink."""
    return QRectF(0, 0, reference_w, reference_h)


def deg_to_rad(deg: float) -> float:
    return math.radians(deg)
