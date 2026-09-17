"""SVG path data -> QPainterPath, for the `path` primitive of
shared/symbols/geometry.json (Konva's Path draws exactly SVG path data).
Supports the whole basic grammar - M/L/H/V/C/S/Q/T/A/Z, absolute and
relative, implicit repeats, comma or space separators - because the
library uses M/L/Z/Q/C/A and relative variants (checked by grep before
this was written), not only the M/L/Z the spike handled.

The elliptical arc (A) is converted to cubic Beziers the standard way
(SVG implementation notes, section F.6) - QPainterPath.arcTo() takes a
bounding rectangle and angles, which is a different parametrisation.
"""
import math
import re

from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath

_TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}


class SvgPathError(ValueError):
    pass


def _tokens(data: str):
    out = []
    for tok in _TOKEN.findall(data.replace(",", " ")):
        out.append(tok if tok.isalpha() else float(tok))
    return out


def _arc_to_beziers(x1, y1, rx, ry, phi_deg, large_arc, sweep, x2, y2):
    """Center parametrisation of an SVG arc, then one cubic per <= 90 deg."""
    if rx == 0 or ry == 0:
        return [("L", x2, y2)]
    if x1 == x2 and y1 == y2:
        return []
    phi = math.radians(phi_deg % 360)
    cos_phi, sin_phi = math.cos(phi), math.sin(phi)
    dx, dy = (x1 - x2) / 2.0, (y1 - y2) / 2.0
    x1p = cos_phi * dx + sin_phi * dy
    y1p = -sin_phi * dx + cos_phi * dy
    rx, ry = abs(rx), abs(ry)
    lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    coef = 0.0 if den == 0 else math.sqrt(max(0.0, num / den))
    if large_arc == sweep:
        coef = -coef
    cxp = coef * (rx * y1p / ry)
    cyp = coef * -(ry * x1p / rx)
    cx = cos_phi * cxp - sin_phi * cyp + (x1 + x2) / 2.0
    cy = sin_phi * cxp + cos_phi * cyp + (y1 + y2) / 2.0

    def angle(ux, uy, vx, vy):
        dot = ux * vx + uy * vy
        length = math.hypot(ux, uy) * math.hypot(vx, vy)
        if length == 0:
            return 0.0
        a = math.acos(max(-1.0, min(1.0, dot / length)))
        return -a if ux * vy - uy * vx < 0 else a

    theta1 = angle(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dtheta = angle((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dtheta > 0:
        dtheta -= 2 * math.pi
    elif sweep and dtheta < 0:
        dtheta += 2 * math.pi

    segments = max(1, int(math.ceil(abs(dtheta) / (math.pi / 2) - 1e-9)))
    delta = dtheta / segments
    t = 4.0 / 3.0 * math.tan(delta / 4.0)
    out = []
    th = theta1
    for _ in range(segments):
        cos1, sin1 = math.cos(th), math.sin(th)
        cos2, sin2 = math.cos(th + delta), math.sin(th + delta)
        e1x, e1y = cos1 - t * sin1, sin1 + t * cos1
        e2x, e2y = cos2 + t * sin2, sin2 - t * cos2
        p1 = (cx + cos_phi * rx * e1x - sin_phi * ry * e1y, cy + sin_phi * rx * e1x + cos_phi * ry * e1y)
        p2 = (cx + cos_phi * rx * e2x - sin_phi * ry * e2y, cy + sin_phi * rx * e2x + cos_phi * ry * e2y)
        end = (cx + cos_phi * rx * cos2 - sin_phi * ry * sin2, cy + sin_phi * rx * cos2 + cos_phi * ry * sin2)
        out.append(("C", p1[0], p1[1], p2[0], p2[1], end[0], end[1]))
        th += delta
    return out


def parse_svg_path(data: str) -> QPainterPath:
    """Raises SvgPathError for data it cannot read (an unknown command,
    too few numbers) - the caller draws nothing for that primitive and
    reports it, rather than drawing something half right."""
    path = QPainterPath()
    if not isinstance(data, str) or not data.strip():
        return path
    toks = _tokens(data)
    i = 0
    cmd = None
    cx = cy = 0.0          # current point
    sx = sy = 0.0          # subpath start
    last_ctrl = None       # for S/T reflection
    last_cmd = None
    while i < len(toks):
        tok = toks[i]
        if isinstance(tok, str):
            cmd = tok
            i += 1
        elif cmd is None:
            raise SvgPathError(f"path data starts with a number: {data[:40]!r}")
        elif cmd in "Mm":
            cmd = "L" if cmd == "M" else "l"  # implicit lineto after moveto
        upper = cmd.upper()
        rel = cmd.islower()
        n = _ARGS[upper]
        if upper != "Z" and i + n > len(toks):
            raise SvgPathError(f"command {cmd} needs {n} numbers near token {i}")
        args = toks[i:i + n]
        if any(isinstance(a, str) for a in args):
            raise SvgPathError(f"command {cmd} needs {n} numbers near token {i}")
        i += n
        ox, oy = (cx, cy) if rel else (0.0, 0.0)
        if upper == "M":
            cx, cy = ox + args[0], oy + args[1]
            sx, sy = cx, cy
            path.moveTo(cx, cy)
            last_ctrl = None
        elif upper == "L":
            cx, cy = ox + args[0], oy + args[1]
            path.lineTo(cx, cy)
            last_ctrl = None
        elif upper == "H":
            cx = ox + args[0]
            path.lineTo(cx, cy)
            last_ctrl = None
        elif upper == "V":
            cy = oy + args[0]
            path.lineTo(cx, cy)
            last_ctrl = None
        elif upper == "C":
            c1 = (ox + args[0], oy + args[1])
            c2 = (ox + args[2], oy + args[3])
            cx, cy = ox + args[4], oy + args[5]
            path.cubicTo(QPointF(*c1), QPointF(*c2), QPointF(cx, cy))
            last_ctrl = c2
        elif upper == "S":
            if last_cmd in ("C", "S") and last_ctrl is not None:
                c1 = (2 * cx - last_ctrl[0], 2 * cy - last_ctrl[1])
            else:
                c1 = (cx, cy)
            c2 = (ox + args[0], oy + args[1])
            cx, cy = ox + args[2], oy + args[3]
            path.cubicTo(QPointF(*c1), QPointF(*c2), QPointF(cx, cy))
            last_ctrl = c2
        elif upper == "Q":
            c1 = (ox + args[0], oy + args[1])
            cx, cy = ox + args[2], oy + args[3]
            path.quadTo(QPointF(*c1), QPointF(cx, cy))
            last_ctrl = c1
        elif upper == "T":
            if last_cmd in ("Q", "T") and last_ctrl is not None:
                c1 = (2 * cx - last_ctrl[0], 2 * cy - last_ctrl[1])
            else:
                c1 = (cx, cy)
            cx, cy = ox + args[0], oy + args[1]
            path.quadTo(QPointF(*c1), QPointF(cx, cy))
            last_ctrl = c1
        elif upper == "A":
            x2, y2 = ox + args[5], oy + args[6]
            for seg in _arc_to_beziers(cx, cy, args[0], args[1], args[2], bool(args[3]), bool(args[4]), x2, y2):
                if seg[0] == "L":
                    path.lineTo(seg[1], seg[2])
                else:
                    path.cubicTo(QPointF(seg[1], seg[2]), QPointF(seg[3], seg[4]), QPointF(seg[5], seg[6]))
            cx, cy = x2, y2
            last_ctrl = None
        elif upper == "Z":
            path.closeSubpath()
            cx, cy = sx, sy
            last_ctrl = None
        last_cmd = upper
        if upper == "Z":
            cmd = None
    return path
