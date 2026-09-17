"""The whole embedded screen as one QWidget: canvas, frames, walls, wires,
symbols with their labels, meters, signal panels - drawn from the
EPW_SYNOPTIC document Studio embeds in projekt.epw (Project.screens),
with every symbol's state and value taken from the live tags through
screen_state.py.

Layout follows the editor's own Canvas.tsx pass order (surfaces and
frames first, then walls, wires, symbols, labels, panels on top) and its
placement rules: an object's (x, y) is its top-left corner, rotation
pivots there, scaleX/scaleY apply after rotation, the symbol is drawn in
its reference size scaled to the object's width/height. The canvas
(canvas.width x canvas.height) is fitted into the widget with its aspect
ratio kept; the same transform maps a click back to an object.

Wires are coloured by the NET they belong to (net_resolver.py, the
editor's own algorithm): a net fed by a SOURCE boundary point or by the
OUT terminal of a closed apparatus is live, in the medium's live colour;
junction dots are drawn where three branches meet; a water symbol on a
live net draws its live variant; a rotating symbol turns at its
directive's rate. Rooms: a closed loop of walls gets a floor in the
screen's floor material with the editor's contact shadow along the
walls, and a room record's name and location are written on the floor. Walls
are the editor's own extruded bands (walls3d.py: mitred outer/inner
rings, far faces with caps, the near face cut away, lit from the
upper left) - door and window openings are not cut yet.
"""
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import QWidget

from epw_os.core.epwsyn_loader import load_epwsyn_data
from epw_os.core.logging import log
from epw_os.gui.synoptic.geometry import shared_geometry
from epw_os.gui.synoptic.net_resolver import (connection_states, junction_points, resolve_nets, runtime_source_rule,
                                               terminal_net_states)
from epw_os.gui.synoptic.painter import (PrimitivePainter, animation_rotation, blink_state, mark_dash_march,
                                         parse_color)
from epw_os.gui.synoptic.rooms import closed_rooms, floor_color, room_labels, shade
from epw_os.gui.synoptic.walls3d import draw_walls
from epw_os.gui.synoptic.screen_state import (GOOD_QUALITIES, ObjectPresentation, TagReader, format_value,
                                              present_object)

# The editor's ScadaTheme.ts, verbatim.
COLOR_CANVAS_BACKGROUND = "#00CFCF"
COLOR_OUTLINE = "#000000"
COLOR_PANEL = "#C6C6C6"
COLOR_VALUE_FIELD = "#F2F2F2"
COLOR_ENERGIZED = "#E01000"
COLOR_DE_ENERGIZED = "#909090"
COLOR_WATER = "#2848D8"
COLOR_WATER_INACTIVE = "#C0C0C0"
VENTILATION_ACTIVE = "#C89000"
VENTILATION_INACTIVE = "#8A7A50"
COLOR_ALARM = "#D80000"
CONDUCTOR_WIDTH = 8
BUSBAR_HEIGHT = 16
OUTLINE_WIDTH = 5
FONT_UI = "Tahoma"
FONT_VALUE = "Consolas"
FONT_SIZE_BASE = 13
FONT_SIZE_SMALL = 11
FONT_SIZE_TITLE = 14
PANEL_PADDING_X = 10
PANEL_PADDING_Y = 10
PANEL_ROW_HEIGHT_FACTOR = 2
PANEL_TITLE_HEIGHT_FACTOR = 1.5
PANEL_TITLE_DIVIDER_GAP = 6
PANEL_OUTLINE_WIDTH = 4
DIODE_RADIUS_LARGE = 7
DIODE_ON, DIODE_OFF, DIODE_ALARM, DIODE_QUALITY = "#00E838", "#3C4048", "#FF2020", "#FFD000"
LABEL_MAX_WIDTH = 220
LABEL_MIN_FONT_SIZE = 8


def wire_color(medium, live: bool) -> str:
    if medium == "WATER":
        return COLOR_WATER if live else COLOR_WATER_INACTIVE
    if medium == "VENTILATION":
        return VENTILATION_ACTIVE if live else VENTILATION_INACTIVE
    return COLOR_ENERGIZED if live else COLOR_DE_ENERGIZED


def panel_layout(font_size, has_title):
    size = font_size or FONT_SIZE_BASE
    row_height = size * PANEL_ROW_HEIGHT_FACTOR
    title_block = FONT_SIZE_TITLE * PANEL_TITLE_HEIGHT_FACTOR + PANEL_TITLE_DIVIDER_GAP if has_title else 0
    return row_height, title_block


def panel_height(title, font_size, row_count):
    row_height, title_block = panel_layout(font_size, bool(title))
    return PANEL_PADDING_Y * 2 + title_block + max(0, row_count) * row_height


class ScreenDocument:
    """The parsed screen plus what the widget derives from it once."""

    def __init__(self, project, warnings):
        self.project = project
        self.warnings = list(warnings)
        self.devices = {d.id: d for d in project.devices.all()} if project is not None else {}

    @property
    def canvas_size(self):
        canvas = self.project.canvas if self.project is not None else {}
        return float(canvas.get("width") or 1920), float(canvas.get("height") or 1080)


class SynopticScreenWidget(QWidget):
    """set_screen(dict) with the embedded document, set_sources() with the
    live objects; the widget repaints itself on a timer while visible.
    object_clicked(obj_dict, presentation, global_pos) fires for a click
    on a symbol bound to an apparatus."""

    object_clicked = Signal(dict, object, object)

    def __init__(self, parent=None, refresh_ms: int = 250):
        super().__init__(parent)
        self.setMinimumSize(320, 200)
        self.setMouseTracking(False)
        self._document = None
        self._load_error = None
        self._tag_reader = TagReader(None)
        self._apparatus_registry = None
        self._analog_units = {}
        self._geometry_result = shared_geometry()
        self._presentations = {}
        self._net_states = {}         # connection id -> ACTIVE/INACTIVE, per paint
        self._terminal_states = {}    # (object id, terminal id) -> ACTIVE/INACTIVE, per paint
        self._junctions = []
        self._transform = QTransform()
        self._t0 = time.monotonic()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.setInterval(max(50, int(refresh_ms)))
        self._timer.start()

    # -- inputs ----------------------------------------------------------------------

    def set_sources(self, tag_manager=None, apparatus_registry=None, analog_units=None):
        self._tag_reader = TagReader(tag_manager)
        self._apparatus_registry = apparatus_registry
        self._analog_units = dict(analog_units or {})
        self.update()

    def set_screen(self, screens: dict):
        """`screens`: ProjectManager.get_embedded_screens() - {} means no
        screen in the project."""
        self._document = None
        self._load_error = None
        if screens:
            result = load_epwsyn_data(screens)
            if result.ok:
                self._document = ScreenDocument(result.project, result.warnings)
            else:
                self._load_error = str(result.error)
        self.update()

    @property
    def has_screen(self) -> bool:
        return self._document is not None

    @property
    def load_error(self):
        return self._load_error

    @property
    def geometry_problem(self):
        return self._geometry_result.problem

    @property
    def document(self):
        return self._document

    def shutdown(self):
        self._timer.stop()

    # -- geometry of the view ----------------------------------------------------------

    def _phase_ms(self) -> float:
        return (time.monotonic() - self._t0) * 1000.0

    def _tick(self):
        if self.isVisible() and self._document is not None:
            self.update()

    def view_transform(self) -> QTransform:
        """Canvas -> widget pixels: fitted, centred, aspect kept."""
        if self._document is None:
            return QTransform()
        cw, ch = self._document.canvas_size
        margin = 8.0
        avail_w = max(1.0, self.width() - 2 * margin)
        avail_h = max(1.0, self.height() - 2 * margin)
        scale = min(avail_w / cw, avail_h / ch)
        ox = margin + (avail_w - cw * scale) / 2.0
        oy = margin + (avail_h - ch * scale) / 2.0
        transform = QTransform()
        transform.translate(ox, oy)
        transform.scale(scale, scale)
        return transform

    @staticmethod
    def object_transform(obj: dict) -> QTransform:
        """The editor's own Group transform: top-left origin, rotation
        about it, then scale."""
        t = QTransform()
        t.translate(float(obj.get("x") or 0), float(obj.get("y") or 0))
        rotation = float(obj.get("rotation") or 0)
        if rotation:
            t.rotate(rotation)
        sx, sy = float(obj.get("scaleX") or 1), float(obj.get("scaleY") or 1)
        if sx != 1 or sy != 1:
            t.scale(sx, sy)
        return t

    def object_at(self, widget_pos):
        """Topmost screen object under a widget point, or None."""
        if self._document is None:
            return None
        inverse, ok = self._transform.inverted()
        if not ok:
            return None
        canvas_pt = inverse.map(QPointF(widget_pos))
        for obj in reversed(self._ordered_objects()):
            if obj.get("visible") is False:
                continue
            local_inverse, ok = self.object_transform(obj).inverted()
            if not ok:
                continue
            local = local_inverse.map(canvas_pt)
            w, h = float(obj.get("width") or 0), float(obj.get("height") or 0)
            if 0 <= local.x() <= w and 0 <= local.y() <= h:
                return obj
        return None

    def presentation_for(self, obj: dict) -> ObjectPresentation:
        return present_object(obj, self._geometry_result.geometry, self._apparatus_registry, self._tag_reader,
                              self._analog_units)

    def _ordered_objects(self):
        objects = list(self._document.project.objects) if self._document is not None else []
        return sorted(objects, key=lambda o: (0 if self._is_surface(o) else 1, float(o.get("zIndex") or 0)))

    def _is_surface(self, obj):
        rec = self._geometry_result.geometry.symbol(obj.get("type") or "")
        return bool(rec and rec.get("is_surface"))

    # -- mouse -------------------------------------------------------------------------

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            obj = self.object_at(event.position())
            if obj is not None and obj.get("deviceId"):
                self.object_clicked.emit(obj, self.presentation_for(obj), event.globalPosition().toPoint())
        super().mouseReleaseEvent(event)

    # -- painting ------------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.fillRect(self.rect(), QColor("#303030"))
        if self._document is None:
            painter.end()
            return
        self._transform = self.view_transform()
        painter.setTransform(self._transform)
        project = self._document.project
        cw, ch = self._document.canvas_size
        painter.fillRect(QRectF(0, 0, cw, ch), parse_color(project.canvas.get("background"), COLOR_CANVAS_BACKGROUND))
        painter.setClipRect(QRectF(0, 0, cw, ch))
        phase = self._phase_ms()

        objects = self._ordered_objects()
        self._resolve_nets(objects, project.connections)
        self._draw_floors(painter, project)
        for obj in objects:
            if self._is_surface(obj):
                self._draw_object(painter, obj, phase)
        for frame in project.frames:
            self._draw_frame(painter, frame)
        draw_walls(painter, project.walls)
        self._draw_room_labels(painter, project)
        for conn in project.connections:
            self._draw_connection(painter, conn)
        for obj in objects:
            if not self._is_surface(obj):
                self._draw_object(painter, obj, phase)
        for x, y in self._junctions:
            self._draw_junction(painter, x, y, phase)
        for obj in objects:
            self._draw_label(painter, obj)
        for meter in project.meters:
            self._draw_meter(painter, meter)
        for panel in project.signal_panels:
            self._draw_signal_panel(painter, panel)
        for command in project.group_commands:
            self._draw_group_command(painter, command)
        for panel in project.setpoint_panels:
            self._draw_setpoint_panel(painter, panel)
        painter.end()

    def _resolve_nets(self, objects, connections):
        """One net resolution per paint: every object's presentation is
        read once (the source rule needs the live state), then wires,
        terminals and junctions are known for the rest of the pass."""
        geometry = self._geometry_result.geometry
        self._presentations = {obj.get("id"): self.presentation_for(obj) for obj in objects}
        rule = runtime_source_rule(lambda obj: self._presentations.get(obj.get("id")) or self.presentation_for(obj))
        try:
            nets = resolve_nets(connections, objects, geometry, rule)
            self._net_states = connection_states(nets)
            self._terminal_states = terminal_net_states(nets)
            self._junctions = junction_points(connections, objects, geometry)
        except Exception as exc:  # noqa: BLE001 - a malformed wire must not blank the screen
            log.debug(f"Net resolution skipped: {exc}")
            self._net_states, self._terminal_states, self._junctions = {}, {}, []

    def resolve_now(self):
        """Resolves presentations, nets and junctions without a paint -
        for callers (tests, a status query) that need connection_state()
        / object_on_live_net() before the widget has ever been painted
        (a child widget that is not shown yet has no size to paint)."""
        if self._document is None:
            return
        self._resolve_nets(self._ordered_objects(), self._document.project.connections)

    def connection_state(self, connection_id) -> str:
        return self._net_states.get(connection_id, "INACTIVE")

    def object_on_live_net(self, obj: dict) -> bool:
        obj_id = obj.get("id")
        return any(state == "ACTIVE" for (o, _t), state in self._terminal_states.items() if o == obj_id)

    def _draw_junction(self, painter: QPainter, x: float, y: float, phase: float):
        """The editor's WireNodeSymbol (scada.wire_node) centred on the
        node - the same dot it draws."""
        geometry = self._geometry_result.geometry
        tree = geometry.state_tree("scada.wire_node", geometry.default_state("scada.wire_node"))
        if not tree:
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(COLOR_OUTLINE)))
            painter.drawEllipse(QPointF(x, y), 6, 6)
            painter.restore()
            return
        w, h = geometry.reference_size("scada.wire_node", (150.0, 150.0))
        painter.save()
        painter.translate(x - w / 2, y - h / 2)
        PrimitivePainter(painter, fields={}, phase_ms=phase).draw_tree(tree)
        painter.restore()

    def _draw_object(self, painter: QPainter, obj: dict, phase: float):
        if obj.get("visible") is False:
            return
        geometry = self._geometry_result.geometry
        symbol_type = obj.get("type") or ""
        presentation = self._presentations.get(obj.get("id")) or self.presentation_for(obj)
        self._presentations[obj.get("id")] = presentation
        painter.save()
        painter.setTransform(self.object_transform(obj), combine=True)
        w, h = float(obj.get("width") or 64), float(obj.get("height") or 64)
        rec = geometry.symbol(symbol_type)
        if rec is None or rec.get("generic"):
            self._draw_generic(painter, obj, w, h, known=rec is not None)
            painter.restore()
            return
        ref_w, ref_h = geometry.reference_size(symbol_type)
        state = blink_state(rec.get("animation"), presentation.state, phase)
        tree = geometry.state_tree(symbol_type, state, net_active=self.object_on_live_net(obj))
        tree = mark_dash_march(tree, rec.get("animation"), state)
        rotation = animation_rotation(rec.get("animation"), presentation.state, phase)
        if ref_w and ref_h and (w != ref_w or h != ref_h):
            painter.scale(w / ref_w, h / ref_h)
        PrimitivePainter(painter, fields=presentation.fields, phase_ms=phase, rotation_deg=rotation).draw_tree(tree)
        painter.restore()

    def _draw_generic(self, painter: QPainter, obj: dict, w: float, h: float, known: bool):
        """The editor's GenericSymbol: a box or circle in the object's own
        fill/border with its text; an unknown type gets a magenta frame
        so a stale screen is visible, never silently blank."""
        symbol_type = obj.get("type") or ""
        fill = parse_color(obj.get("fill"), "#c0c0c0")
        border = parse_color(obj.get("border"), "#000000")
        painter.setBrush(QBrush(fill))
        pen = QPen(border if known else QColor("magenta"))
        pen.setWidthF(1.0 if known else 2.0)
        if not known:
            pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        is_circle = symbol_type == "graphics.circle"
        if is_circle:
            painter.drawEllipse(QPointF(w / 2, h / 2), w / 2, h / 2)
        else:
            painter.drawRect(QRectF(0, 0, w, h))
        text = obj.get("text") or (symbol_type if not known or symbol_type == "graphics.text" else "")
        if symbol_type == "graphics.text" and not obj.get("text"):
            text = ""
        if text:
            font = QFont(obj.get("font") or FONT_UI)
            font.setPixelSize(int(obj.get("fontSize") or FONT_SIZE_BASE))
            painter.setFont(font)
            painter.setPen(QPen(parse_color(obj.get("textColor"), "#000000")))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)

    def _draw_label(self, painter: QPainter, obj: dict):
        """ObjectLabelRenderer.tsx's placement, in the object's own frame."""
        if obj.get("visible") is False:
            return
        if obj.get("showDesignation") is False and obj.get("showName") is False:
            return
        primary = obj.get("designation") or "" if obj.get("showDesignation") is not False else ""
        secondary = obj.get("name") or "" if obj.get("showName") is not False else ""
        if not primary and not secondary:
            return
        geometry = self._geometry_result.geometry
        ref_w, ref_h = geometry.reference_size(obj.get("type") or "", (80.0, 80.0))
        w, h = ref_w or 80.0, ref_h or 80.0
        margin = 10
        pos = obj.get("labelPosition") or "BOTTOM"
        box_width = 80 if pos in ("LEFT", "RIGHT") else min(w * 2, LABEL_MAX_WIDTH)
        if pos == "TOP":
            base_x, base_y, align = -box_width / 2, -h / 2 - margin - 20, Qt.AlignmentFlag.AlignHCenter
        elif pos == "LEFT":
            base_x, base_y, align = -w - box_width - margin, -10, Qt.AlignmentFlag.AlignRight
        elif pos == "RIGHT":
            base_x, base_y, align = w / 2 + margin, -10, Qt.AlignmentFlag.AlignLeft
        else:
            base_x, base_y, align = -box_width / 2, h / 2 + margin, Qt.AlignmentFlag.AlignHCenter
        x = float(obj["labelOffsetX"]) if obj.get("labelOffsetX") is not None else base_x
        y = float(obj["labelOffsetY"]) if obj.get("labelOffsetY") is not None else base_y

        primary_size = int(obj.get("fontSize") or FONT_SIZE_BASE)
        secondary_size = max(LABEL_MIN_FONT_SIZE, round(primary_size * FONT_SIZE_SMALL / FONT_SIZE_BASE))
        family = (obj.get("font") or FONT_UI).split(",")[0].strip().strip("'\"")
        font_primary = QFont(family)
        font_primary.setPixelSize(primary_size)
        font_primary.setBold(bool(obj.get("fontBold")))
        font_secondary = QFont(family)
        font_secondary.setPixelSize(secondary_size)
        pad_x, pad_y, gap = 4, 2, 1
        m1, m2 = QFontMetricsF(font_primary), QFontMetricsF(font_secondary)
        max_text = box_width - 2 * pad_x
        w1 = min(m1.horizontalAdvance(primary), max_text) if primary else 0
        w2 = min(m2.horizontalAdvance(secondary), max_text) if secondary else 0
        h1 = primary_size * 1.2 * (2 if primary and m1.horizontalAdvance(primary) > max_text else 1) if primary else 0
        h2 = secondary_size * 1.2 * (2 if secondary and m2.horizontalAdvance(secondary) > max_text else 1) if secondary else 0
        bg_w = min(box_width, max(w1, w2) + 2 * pad_x)
        bg_h = pad_y * 2 + h1 + (gap if primary and secondary else 0) + h2
        if align == Qt.AlignmentFlag.AlignRight:
            bg_x = box_width - bg_w
        elif align == Qt.AlignmentFlag.AlignHCenter:
            bg_x = (box_width - bg_w) / 2
        else:
            bg_x = 0

        painter.save()
        painter.setTransform(self.object_transform(obj), combine=True)
        painter.translate(x, y)
        painter.rotate(-float(obj.get("rotation") or 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 235)))
        painter.drawRect(QRectF(bg_x, 0, bg_w, bg_h))
        painter.setPen(QPen(parse_color(obj.get("textColor"), COLOR_OUTLINE)))
        flags = align | Qt.TextFlag.TextWordWrap
        if primary:
            painter.setFont(font_primary)
            painter.drawText(QRectF(bg_x + pad_x, pad_y, bg_w - 2 * pad_x, h1), flags, primary)
        if secondary:
            painter.setFont(font_secondary)
            painter.drawText(QRectF(bg_x + pad_x, pad_y + h1 + (gap if primary else 0), bg_w - 2 * pad_x, h2), flags,
                             secondary)
        painter.restore()

    def _draw_connection(self, painter: QPainter, conn: dict):
        points = conn.get("points") or []
        if len(points) < 2:
            return
        live = self.connection_state(conn.get("id")) == "ACTIVE"
        width = BUSBAR_HEIGHT if conn.get("style") == "BUS" else CONDUCTOR_WIDTH
        pen = QPen(QColor(wire_color(conn.get("medium"), live)))
        pen.setWidthF(width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        path = QPainterPath(QPointF(float(points[0].get("x", 0)), float(points[0].get("y", 0))))
        for pt in points[1:]:
            path.lineTo(float(pt.get("x", 0)), float(pt.get("y", 0)))
        painter.save()
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        painter.restore()

    def _draw_floors(self, painter: QPainter, project):
        """RoomFloorLayer.tsx: the floor of every closed wall loop in the
        screen's floor material, outlined a shade darker, with a wide,
        faint black stroke along the walls as the contact shadow."""
        material = floor_color((project.canvas or {}).get("floorMaterial"))
        for polygon in closed_rooms(project.walls):
            path = QPainterPath(QPointF(*polygon[0]))
            for x, y in polygon[1:]:
                path.lineTo(x, y)
            path.closeSubpath()
            painter.save()
            painter.setBrush(QBrush(QColor(material)))
            outline = QPen(QColor(shade(material, 0.75)))
            outline.setWidthF(1.0)
            painter.setPen(outline)
            painter.drawPath(path)
            shadow = QPen(QColor(0, 0, 0))
            shadow.setWidthF(14.0)
            painter.setPen(shadow)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setOpacity(0.13)
            painter.drawPath(path)
            painter.restore()

    def _draw_room_labels(self, painter: QPainter, project):
        """Canvas.tsx: "name - location" on the floor, bold title size."""
        font = QFont(FONT_UI)
        font.setPixelSize(FONT_SIZE_TITLE)
        font.setBold(True)
        for label in room_labels(project.walls, project.rooms):
            text = " - ".join(part for part in (label["name"], label["location"]) if part)
            painter.save()
            painter.setFont(font)
            painter.setPen(QPen(QColor(COLOR_OUTLINE)))
            painter.drawText(QRectF(label["x"] - 160, label["y"] - 9, 320, FONT_SIZE_TITLE * 1.4),
                             Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, text)
            painter.restore()

    def _draw_frame(self, painter: QPainter, frame: dict):
        x, y = float(frame.get("x") or 0), float(frame.get("y") or 0)
        w, h = float(frame.get("width") or 0), float(frame.get("height") or 0)
        title = frame.get("title") or ""
        painter.save()
        painter.translate(x, y)
        pen = QPen(QColor(COLOR_OUTLINE))
        pen.setWidthF(OUTLINE_WIDTH)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        font = QFont(FONT_UI)
        font.setPixelSize(FONT_SIZE_TITLE)
        font.setBold(True)
        gap_start = gap_end = 0.0
        if title:
            text_w = QFontMetricsF(font).horizontalAdvance(title) + 12
            gap_start = max(0.0, (w - text_w) / 2) if frame.get("titlePosition") == "TOP_CENTER" else 12.0
            gap_end = min(w, gap_start + text_w)
            painter.drawLine(QPointF(0, 0), QPointF(gap_start, 0))
            painter.drawLine(QPointF(gap_end, 0), QPointF(w, 0))
        else:
            painter.drawLine(QPointF(0, 0), QPointF(w, 0))
        painter.drawLine(QPointF(w, 0), QPointF(w, h))
        painter.drawLine(QPointF(w, h), QPointF(0, h))
        painter.drawLine(QPointF(0, h), QPointF(0, 0))
        if frame.get("variant") == "BUILDING":
            roof = h * 0.25
            hatch = QPen(QColor(COLOR_OUTLINE))
            hatch.setWidthF(1.0)
            painter.setPen(hatch)
            painter.setOpacity(0.35)
            yy = 6.0
            while yy < roof:
                painter.drawLine(QPointF(0, yy), QPointF(w, yy))
                yy += 6.0
            painter.setOpacity(1.0)
        if title:
            painter.setPen(QPen(QColor(COLOR_OUTLINE)))
            painter.setFont(font)
            painter.drawText(QRectF(gap_start + 6, -FONT_SIZE_TITLE / 2, gap_end - gap_start - 12, FONT_SIZE_TITLE * 1.3),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)
        painter.restore()

    def _draw_panel_chrome(self, painter: QPainter, width: float, height: float, title: str, font_size: float):
        pen = QPen(QColor(COLOR_OUTLINE))
        pen.setWidthF(PANEL_OUTLINE_WIDTH)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(COLOR_PANEL)))
        painter.drawRect(QRectF(0, 0, width, height))
        row_height, title_block = panel_layout(font_size, bool(title))
        if title:
            font = QFont(FONT_UI)
            font.setPixelSize(FONT_SIZE_TITLE)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QPen(QColor(COLOR_OUTLINE)))
            painter.drawText(QRectF(PANEL_PADDING_X, PANEL_PADDING_Y, width - 2 * PANEL_PADDING_X, FONT_SIZE_TITLE * 1.3),
                             Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, title)
            divider = QPen(QColor(COLOR_OUTLINE))
            divider.setWidthF(1.0)
            painter.setPen(divider)
            yy = PANEL_PADDING_Y + title_block - PANEL_TITLE_DIVIDER_GAP / 2
            painter.drawLine(QPointF(0, yy), QPointF(width, yy))
        return row_height, title_block

    def _device_value(self, device_id):
        """(value_text, unit, ok) for a MEASURED/MODULATED apparatus."""
        apparatus = self._apparatus_registry.get(device_id) if (self._apparatus_registry and device_id) else None
        if apparatus is None:
            return "---", "", False
        tag_name = apparatus.feedback[0] if apparatus.feedback else None
        value, quality = self._tag_reader.read(tag_name)
        if value is None or quality not in GOOD_QUALITIES:
            return "---", self._analog_units.get(tag_name, ""), False
        return format_value(value), self._analog_units.get(tag_name, ""), True

    def _device_asserted(self, device_id):
        """None (unknown), True/False for a SWITCHED/SIGNAL apparatus."""
        apparatus = self._apparatus_registry.get(device_id) if (self._apparatus_registry and device_id) else None
        if apparatus is None or not apparatus.feedback:
            return None
        value, quality = self._tag_reader.read(apparatus.feedback[0])
        if value is None or quality not in GOOD_QUALITIES:
            return None
        return bool(value)

    def _device_label(self, device_id) -> str:
        device = self._document.devices.get(device_id) if self._document else None
        return (device.designation or device.name) if device is not None else (device_id or "")

    def _draw_meter(self, painter: QPainter, meter: dict):
        rows = meter.get("rows") or []
        font_size = float(meter.get("fontSize") or FONT_SIZE_BASE)
        width = float(meter.get("width") or 200)
        height = panel_height(meter.get("title"), font_size, len(rows))
        painter.save()
        painter.translate(float(meter.get("x") or 0), float(meter.get("y") or 0))
        row_height, title_block = self._draw_panel_chrome(painter, width, height, meter.get("title") or "", font_size)
        value_w = width * 0.42
        value_x = width - PANEL_PADDING_X - value_w
        label_font = QFont(FONT_UI)
        label_font.setPixelSize(int(font_size))
        value_font = QFont(FONT_VALUE)
        value_font.setPixelSize(int(font_size))
        for i, row in enumerate(rows):
            row_y = PANEL_PADDING_Y + title_block + i * row_height
            device_id = row.get("device") or ""
            if device_id:
                value, unit, ok = self._device_value(device_id)
                label = row.get("label") or self._device_label(device_id)
                color = QColor(COLOR_OUTLINE) if ok else QColor(COLOR_DE_ENERGIZED)
            else:
                value, unit, ok = str(row.get("manualValue") or ""), str(row.get("manualUnit") or ""), True
                label = row.get("label") or ""
                color = QColor(COLOR_OUTLINE)
            painter.setFont(label_font)
            painter.setPen(QPen(QColor(COLOR_OUTLINE)))
            painter.drawText(QRectF(PANEL_PADDING_X, row_y, value_x - PANEL_PADDING_X, row_height),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
            field_pen = QPen(QColor(COLOR_OUTLINE))
            field_pen.setWidthF(2)
            painter.setPen(field_pen)
            painter.setBrush(QBrush(QColor(COLOR_VALUE_FIELD)))
            painter.drawRect(QRectF(value_x, row_y + 3, value_w, row_height - 6))
            painter.setFont(value_font)
            painter.setPen(QPen(color))
            painter.drawText(QRectF(value_x, row_y, value_w - 6, row_height),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{value} {unit}".strip())
        painter.restore()

    def _draw_signal_panel(self, painter: QPainter, panel: dict):
        rows = panel.get("rows") or []
        font_size = float(panel.get("fontSize") or FONT_SIZE_BASE)
        width = float(panel.get("width") or 200)
        height = panel_height(panel.get("title"), font_size, len(rows))
        painter.save()
        painter.translate(float(panel.get("x") or 0), float(panel.get("y") or 0))
        row_height, title_block = self._draw_panel_chrome(painter, width, height, panel.get("title") or "", font_size)
        diode_x = width - PANEL_PADDING_X - DIODE_RADIUS_LARGE
        label_font = QFont(FONT_UI)
        label_font.setPixelSize(int(font_size))
        for i, row in enumerate(rows):
            row_y = PANEL_PADDING_Y + title_block + i * row_height
            device_id = row.get("device") or ""
            if device_id:
                asserted = self._device_asserted(device_id)
                state = "OFF" if asserted is None else ("ON" if asserted else "OFF")
                label = row.get("label") or self._device_label(device_id)
                opacity = 0.5 if asserted is None else 1.0
            else:
                state = row.get("manualState") or "OFF"
                label = row.get("label") or ""
                opacity = 1.0
            painter.setFont(label_font)
            painter.setPen(QPen(QColor(COLOR_OUTLINE)))
            painter.drawText(QRectF(PANEL_PADDING_X, row_y, diode_x - PANEL_PADDING_X - DIODE_RADIUS_LARGE, row_height),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
            fill = {"ON": DIODE_ON, "ALARM": DIODE_ALARM, "QUALITY": DIODE_QUALITY}.get(state, DIODE_OFF)
            outline = QPen(QColor(COLOR_OUTLINE))
            outline.setWidthF(3.5)
            painter.setPen(outline)
            painter.setBrush(QBrush(QColor(fill)))
            painter.setOpacity(opacity)
            painter.drawEllipse(QPointF(diode_x, row_y + row_height / 2), DIODE_RADIUS_LARGE, DIODE_RADIUS_LARGE)
            painter.setOpacity(1.0)
        painter.restore()

    def _draw_group_command(self, painter: QPainter, command: dict):
        width = float(command.get("width") or 160)
        painter.save()
        painter.translate(float(command.get("x") or 0), float(command.get("y") or 0))
        pen = QPen(QColor(COLOR_OUTLINE))
        pen.setWidthF(PANEL_OUTLINE_WIDTH)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(COLOR_PANEL)))
        painter.drawRect(QRectF(0, 0, width, 36))
        font = QFont(FONT_UI)
        font.setPixelSize(FONT_SIZE_BASE)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(0, 0, width, 36), Qt.AlignmentFlag.AlignCenter, command.get("label") or "")
        painter.restore()

    def _draw_setpoint_panel(self, painter: QPainter, panel: dict):
        rows = panel.get("rows") or []
        font_size = float(panel.get("fontSize") or FONT_SIZE_BASE)
        width = float(panel.get("width") or 200)
        height = panel_height(panel.get("title"), font_size, len(rows))
        painter.save()
        painter.translate(float(panel.get("x") or 0), float(panel.get("y") or 0))
        row_height, title_block = self._draw_panel_chrome(painter, width, height, panel.get("title") or "", font_size)
        font = QFont(FONT_UI)
        font.setPixelSize(int(font_size))
        painter.setFont(font)
        for i, row in enumerate(rows):
            row_y = PANEL_PADDING_Y + title_block + i * row_height
            painter.setPen(QPen(QColor(COLOR_OUTLINE)))
            painter.drawText(QRectF(PANEL_PADDING_X, row_y, width - 2 * PANEL_PADDING_X, row_height),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                             str(row.get("label") or row.get("device") or ""))
        painter.restore()
