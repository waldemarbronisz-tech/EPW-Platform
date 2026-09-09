// feat/wire-routing-around-obstacles commit 1: a wire drawn between two
// apparatuses used to pass straight THROUGH anything standing in its
// way - on a real technological diagram a pipe/cable must go AROUND an
// obstacle, never through it. This file is the detection half: given a
// screen's own elements and a wire's own polyline, which of its
// segments actually crosses which obstacle. Pure functions only, no
// store dependency (this task's own spec) - the same Konva-free
// convention every other utils/project file in this codebase already
// follows, so this is safe to import from a plain Vitest run.
//
// A collision is a WARNING, never an error (GRANICE: never blocks
// drawing or saving) - see historySlice.ts for where it is turned into
// a one-time Messages notice, and Canvas.tsx/ConnectionLine.tsx for the
// dashed on-canvas marking.

import type { SynopticConnection, SynopticObject, WirePoint } from '../store';
import type { MeterElement } from '../meter/MeterElement';
import type { SignalPanelElement } from '../elements/SignalPanelElement';
import type { FrameElement } from '../elements/FrameElement';
import type { GroupCommandElement } from '../elements/GroupCommandElement';
import type { SetpointPanelElement } from '../elements/SetpointElement';
import { getSymbolDefinition } from '../symbols/SymbolRegistry';
import { describeObject } from '../utils/ObjectDisplay';
import { computePanelHeight } from '../elements/PanelLayout';
import { computeGroupCommandHeight } from '../elements/GroupCommandElement';
import { WIRE_OBSTACLE_MARGIN } from '../theme/ScadaTheme';

export interface Obstacle {
  id: string;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * Everything a wire's own route needs to avoid, gathered from one
 * screen's worth of elements. Every field but `objects` is optional -
 * a caller (a test, mostly) that has no meters/panels/frames on screen
 * simply omits them, exactly like ProjectSchema's own optional fields.
 */
export interface Screen {
  objects: SynopticObject[];
  meters?: MeterElement[];
  signalPanels?: SignalPanelElement[];
  frames?: FrameElement[];
  groupCommands?: GroupCommandElement[];
  setpointPanels?: SetpointPanelElement[];
}

interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

/** Shrinks a rectangle by `margin` on every side, never past zero size (centered, not just clamped from one corner). */
function shrinkRect(rect: Rect, margin: number): Rect {
  const width = Math.max(0, rect.width - margin * 2);
  const height = Math.max(0, rect.height - margin * 2);
  return {
    x: rect.x + (rect.width - width) / 2,
    y: rect.y + (rect.height - height) / 2,
    width,
    height
  };
}

/**
 * A symbol's own axis-aligned bounding box on screen, accounting for
 * rotation (rotating around its own top-left origin - the same pivot
 * Terminals.ts's getTerminalWorldPosition already documents) - not the
 * tightest possible rotated hit-test, but a correct, conservative
 * enclosing box, exactly what this task's own "wystarczy poprawna i
 * sensowna" (a correct, reasonable result, not necessarily optimal)
 * asks for.
 */
function objectBoundingBox(obj: SynopticObject): Rect {
  const w = obj.width * (obj.scaleX || 1);
  const h = obj.height * (obj.scaleY || 1);
  const rotation = obj.rotation || 0;
  if (!rotation) return { x: obj.x, y: obj.y, width: w, height: h };

  const radians = rotation * (Math.PI / 180);
  const corners: [number, number][] = [[0, 0], [w, 0], [0, h], [w, h]];
  const xs: number[] = [];
  const ys: number[] = [];
  corners.forEach(([lx, ly]) => {
    xs.push(obj.x + lx * Math.cos(radians) - ly * Math.sin(radians));
    ys.push(obj.y + lx * Math.sin(radians) + ly * Math.cos(radians));
  });
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  return { x: minX, y: minY, width: Math.max(...xs) - minX, height: Math.max(...ys) - minY };
}

/**
 * The obstacle rectangles a wire must avoid, right now, on this screen -
 * every library symbol (except the backdrop surfaces: trawa/droga
 * betonowa, which are never obstacles), plus meters, signal panels,
 * frames/buildings and command/setpoint panels. `excludeIds` drops the
 * symbol(s) this particular wire is itself anchored to - a wire ending
 * IN a valve's own terminal cannot treat that same valve as something
 * blocking it. Every returned rectangle is already shrunk by
 * WIRE_OBSTACLE_MARGIN, so a wire running right along an obstacle's own
 * edge is never flagged.
 */
export function getObstacles(screen: Screen, excludeIds: string[] = []): Obstacle[] {
  const excluded = new Set(excludeIds);
  const obstacles: Obstacle[] = [];

  const pushShrunk = (id: string, label: string, rect: Rect) => {
    const shrunk = shrinkRect(rect, WIRE_OBSTACLE_MARGIN);
    if (shrunk.width <= 0 || shrunk.height <= 0) return; // too small to ever collide with anything - not worth carrying
    obstacles.push({ id, label, ...shrunk });
  };

  screen.objects.forEach(obj => {
    if (excluded.has(obj.id)) return;
    const def = getSymbolDefinition(obj.type);
    // The backdrop/floor layer - grass, concrete road (and, were this
    // project's schema ever to grow a ROOM element, a room) - is never
    // an obstacle, per this task's own explicit list.
    if (def?.isSurface) return;
    pushShrunk(obj.id, describeObject(obj), objectBoundingBox(obj));
  });

  (screen.meters || []).forEach(m => {
    const height = computePanelHeight({ title: m.title, fontSize: m.fontSize, rowCount: m.rows.length });
    pushShrunk(`meter:${m.id}`, m.title || 'Miernik', { x: m.x, y: m.y, width: m.width, height });
  });

  (screen.signalPanels || []).forEach(p => {
    const height = computePanelHeight({ title: p.title, fontSize: p.fontSize, rowCount: p.rows.length });
    pushShrunk(`signalPanel:${p.id}`, p.title || 'Panel sygnalizacyjny', { x: p.x, y: p.y, width: p.width, height });
  });

  (screen.frames || []).forEach(f => {
    pushShrunk(`frame:${f.id}`, f.title || (f.variant === 'BUILDING' ? 'Budynek' : 'Rama'), { x: f.x, y: f.y, width: f.width, height: f.height });
  });

  (screen.groupCommands || []).forEach(g => {
    pushShrunk(`groupCommand:${g.id}`, g.label || 'Przycisk komend grupowych', { x: g.x, y: g.y, width: g.width, height: computeGroupCommandHeight() });
  });

  (screen.setpointPanels || []).forEach(p => {
    const height = computePanelHeight({ title: p.title, fontSize: p.fontSize, rowCount: p.rows.length });
    pushShrunk(`setpointPanel:${p.id}`, p.title || 'Panel nastaw', { x: p.x, y: p.y, width: p.width, height });
  });

  return obstacles;
}

/**
 * Whether the axis-aligned segment a-b (always horizontal or vertical -
 * this codebase's own wire model guarantees it) crosses the given
 * obstacle rectangle. Touching only the rectangle's own boundary does
 * not count as a crossing (strict inequalities throughout) - the
 * margin in getObstacles above is what actually keeps an edge-hugging
 * wire clear; this function does not need to duplicate that leniency.
 */
export function segmentHitsObstacle(a: WirePoint, b: WirePoint, obstacle: Obstacle): boolean {
  if (obstacle.width <= 0 || obstacle.height <= 0) return false;
  const left = obstacle.x;
  const right = obstacle.x + obstacle.width;
  const top = obstacle.y;
  const bottom = obstacle.y + obstacle.height;

  if (a.y === b.y) {
    if (a.y <= top || a.y >= bottom) return false;
    const lo = Math.min(a.x, b.x);
    const hi = Math.max(a.x, b.x);
    return hi > left && lo < right;
  }
  if (a.x === b.x) {
    if (a.x <= left || a.x >= right) return false;
    const lo = Math.min(a.y, b.y);
    const hi = Math.max(a.y, b.y);
    return hi > top && lo < bottom;
  }
  // A genuinely diagonal segment should never occur (every wire in this
  // model is orthogonal by construction) - fall back to a conservative
  // "does either endpoint sit strictly inside" check rather than
  // throwing on data this module was not built to expect.
  const inside = (p: WirePoint) => p.x > left && p.x < right && p.y > top && p.y < bottom;
  return inside(a) || inside(b);
}

export interface CollisionInfo {
  segmentIndex: number;
  obstacle: Obstacle;
}

/** Every (segment, obstacle) pair where the wire actually crosses that obstacle - at most one entry per pair, never duplicated. */
export function findCollisions(wire: SynopticConnection, obstacles: Obstacle[]): CollisionInfo[] {
  const collisions: CollisionInfo[] = [];
  const points = wire.points;
  for (let i = 0; i < points.length - 1; i++) {
    const a = points[i];
    const b = points[i + 1];
    for (const obstacle of obstacles) {
      if (segmentHitsObstacle(a, b, obstacle)) {
        collisions.push({ segmentIndex: i, obstacle });
      }
    }
  }
  return collisions;
}

/** Every symbol a wire is itself anchored to, anywhere along its points - never an obstacle for that same wire. */
function anchoredSymbolIds(wire: SynopticConnection): string[] {
  const ids = new Set<string>();
  wire.points.forEach(p => { if (p.anchor) ids.add(p.anchor.symbolId); });
  return [...ids];
}

export interface WireCollision {
  connectionId: string;
  segmentIndex: number;
  obstacle: Obstacle;
}

/**
 * Every collision across every wire on the screen, in one pass - each
 * wire's own obstacle list excludes whatever symbol(s) it is anchored
 * to, per getObstacles above. What both the on-canvas dashed marking
 * (Canvas.tsx) and the one-time Messages warning (historySlice.ts) call,
 * rather than each re-deriving the per-wire exclusion rule itself.
 */
export function findAllCollisions(connections: SynopticConnection[], screen: Screen): WireCollision[] {
  const out: WireCollision[] = [];
  connections.forEach(conn => {
    const obstacles = getObstacles(screen, anchoredSymbolIds(conn));
    findCollisions(conn, obstacles).forEach(c => out.push({ connectionId: conn.id, segmentIndex: c.segmentIndex, obstacle: c.obstacle }));
  });
  return out;
}
