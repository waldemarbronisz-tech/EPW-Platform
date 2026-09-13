// feat/room-plan: wall geometry - what turns a pile of separate wall
// segments into ONE continuous body.
//
// THE PROBLEM THIS SOLVES. Each wall used to be painted on its own as
// a thick rectangle. Four of them round a room therefore OVERLAPPED at
// every corner, each drawing its own outline straight through the
// neighbour it met - the corners showed notches, doubled edges and
// little dark steps. It read as four planks laid on top of each other,
// which is exactly what it was.
//
// A real wall drawing has MITRED corners: the two faces of one wall
// continue into the two faces of the next, meeting at a single point on
// the bisector. That cannot be computed from one wall alone - it needs
// the whole chain. So this module works on chains, not on segments:
// it groups connected walls, walks each chain in order, and offsets the
// resulting polyline outwards and inwards by half the thickness. The
// result is a single closed ring (or a pair of rings for a closed
// room) that is filled and outlined ONCE.
//
// Pure functions only, no store and no Konva - the same contract
// NetResolver.ts, CircuitResolver.ts and RoomFloors.ts next door keep.

import type { WallElement, WallPoint } from '../elements/WallElement';
import { clampWallHeight, clampWallThickness, drawnWallHeight } from '../elements/WallElement';

// Endpoints closer than this are the same corner. Walls are drawn
// chained and grid-snapped so they normally match exactly; this only
// absorbs float drift from a drag.
const JOIN_TOLERANCE = 1.5;

// A mitre at a very sharp angle runs away to infinity. Past this
// multiple of the wall's half-thickness the joint is cut off flat
// instead - the same limit every stroke renderer applies, and for the
// same reason.
const MITRE_LIMIT = 4;

export function pointKey(p: WallPoint): string {
  const q = (v: number) => Math.round(v / JOIN_TOLERANCE);
  return `${q(p.x)}:${q(p.y)}`;
}

export interface WallChain {
  /** The chain's corners in traversal order. For a closed chain the first point is NOT repeated at the end. */
  points: WallPoint[];
  closed: boolean;
  wallIds: string[];
  /** Thickness/height/material taken from the chain's own walls - see chainsFromWalls for what happens when they disagree. */
  thickness: number;
  height: number;
  material: string | undefined;
  /** True when the chain's walls do NOT all share one thickness/material, so it cannot be drawn as one body. */
  mixed: boolean;
}

interface GraphNode {
  point: WallPoint;
  edges: { to: string; wall: WallElement }[];
}

function buildGraph(walls: WallElement[]): Map<string, GraphNode> {
  const nodes = new Map<string, GraphNode>();
  for (const wall of walls) {
    const a = pointKey(wall.from);
    const b = pointKey(wall.to);
    if (a === b) continue; // zero-length: not part of any chain
    if (!nodes.has(a)) nodes.set(a, { point: wall.from, edges: [] });
    if (!nodes.has(b)) nodes.set(b, { point: wall.to, edges: [] });
    nodes.get(a)!.edges.push({ to: b, wall });
    nodes.get(b)!.edges.push({ to: a, wall });
  }
  return nodes;
}

/**
 * Groups walls into chains: maximal runs of walls joined end to end.
 *
 * Only chains where every corner joins exactly two walls (a closed
 * loop) or where the ends join one and the middles two (an open run)
 * can be drawn as one mitred body. Anything with a junction - three
 * walls meeting at a point - has no single "the wall continues this
 * way", so those walls come back as one-segment chains and are drawn
 * individually, exactly as before. A T-junction looking slightly
 * blockier than a corner is a far smaller problem than a mitre
 * computed from an arbitrary choice of which branch to follow.
 */
export function chainsFromWalls(walls: WallElement[]): WallChain[] {
  const nodes = buildGraph(walls);
  const chains: WallChain[] = [];
  const usedWallIds = new Set<string>();

  const makeChain = (points: WallPoint[], chainWalls: WallElement[], closed: boolean): WallChain => {
    const thicknesses = new Set(chainWalls.map(w => clampWallThickness(w.thickness)));
    const materials = new Set(chainWalls.map(w => w.material ?? ''));
    const heights = new Set(chainWalls.map(w => clampWallHeight(w.height)));
    return {
      points,
      closed,
      wallIds: chainWalls.map(w => w.id),
      thickness: clampWallThickness(chainWalls[0].thickness),
      height: clampWallHeight(chainWalls[0].height),
      material: chainWalls[0].material,
      // One body can only have one thickness, one height and one
      // material. When the chain's walls disagree, the caller falls
      // back to drawing them separately rather than silently painting
      // three of them with the fourth one's brick.
      mixed: thicknesses.size > 1 || materials.size > 1 || heights.size > 1,
    };
  };

  // --- closed loops first: every node degree 2 in its component ---
  const visited = new Set<string>();
  for (const startKey of nodes.keys()) {
    if (visited.has(startKey)) continue;
    const component: string[] = [];
    const queue = [startKey];
    const seen = new Set<string>([startKey]);
    while (queue.length > 0) {
      const key = queue.shift()!;
      component.push(key);
      for (const edge of nodes.get(key)!.edges) {
        if (!seen.has(edge.to)) { seen.add(edge.to); queue.push(edge.to); }
      }
    }
    component.forEach(k => visited.add(k));

    const allDegreeTwo = component.length >= 3 && component.every(k => nodes.get(k)!.edges.length === 2);
    if (!allDegreeTwo) continue;

    const points: WallPoint[] = [];
    const chainWalls: WallElement[] = [];
    let current = startKey;
    let previousWall: WallElement | null = null;
    for (let i = 0; i < component.length; i++) {
      const node = nodes.get(current)!;
      points.push(node.point);
      const next = node.edges.find(e => e.wall.id !== previousWall?.id);
      if (!next) break;
      chainWalls.push(next.wall);
      previousWall = next.wall;
      current = next.to;
    }
    if (points.length === component.length) {
      chainWalls.forEach(w => usedWallIds.add(w.id));
      chains.push(makeChain(points, chainWalls, true));
    }
  }

  // --- open runs: start at an endpoint (degree 1) and walk ---
  for (const [key, node] of nodes) {
    if (node.edges.length !== 1) continue;
    if (node.edges.every(e => usedWallIds.has(e.wall.id))) continue;

    const points: WallPoint[] = [node.point];
    const chainWalls: WallElement[] = [];
    let current = key;
    let previousWall: WallElement | null = null;
    for (;;) {
      const here = nodes.get(current)!;
      // Degree > 2 is a junction - the run stops there rather than
      // guessing which branch continues it.
      const next = here.edges.length <= 2
        ? here.edges.find(e => e.wall.id !== previousWall?.id && !usedWallIds.has(e.wall.id))
        : undefined;
      if (!next) break;
      usedWallIds.add(next.wall.id);
      chainWalls.push(next.wall);
      previousWall = next.wall;
      current = next.to;
      points.push(nodes.get(current)!.point);
      if (current === key) break; // safety: never loop forever
    }
    if (chainWalls.length > 0) chains.push(makeChain(points, chainWalls, false));
  }

  // --- anything left (junction walls, leftovers) as its own chain ---
  for (const wall of walls) {
    if (usedWallIds.has(wall.id)) continue;
    if (pointKey(wall.from) === pointKey(wall.to)) continue;
    usedWallIds.add(wall.id);
    chains.push(makeChain([wall.from, wall.to], [wall], false));
  }

  return chains;
}

// ---- mitre offsetting -----------------------------------------------------

interface Vec { x: number; y: number }

function sub(a: Vec, b: Vec): Vec { return { x: a.x - b.x, y: a.y - b.y }; }
function add(a: Vec, b: Vec): Vec { return { x: a.x + b.x, y: a.y + b.y }; }
function scale(a: Vec, k: number): Vec { return { x: a.x * k, y: a.y * k }; }

function normalize(v: Vec): Vec {
  const length = Math.hypot(v.x, v.y);
  return length === 0 ? { x: 0, y: 0 } : { x: v.x / length, y: v.y / length };
}

/** Left-hand normal of a direction - (x,y) -> (-y,x). */
function leftNormal(v: Vec): Vec { return { x: -v.y, y: v.x }; }

/**
 * Where two offset edges meet. Returns null when they are (near)
 * parallel, which is a straight-through vertex needing no mitre at
 * all - the caller just keeps the offset point itself.
 */
function intersectLines(p1: Vec, d1: Vec, p2: Vec, d2: Vec): Vec | null {
  const denominator = d1.x * d2.y - d1.y * d2.x;
  if (Math.abs(denominator) < 1e-9) return null;
  const t = ((p2.x - p1.x) * d2.y - (p2.y - p1.y) * d2.x) / denominator;
  return add(p1, scale(d1, t));
}

/**
 * Offsets a polyline sideways by `distance` (positive = to the left of
 * travel), mitring every interior vertex. `closed` wraps the first and
 * last vertices so a ring has no seam.
 *
 * This is what makes the corners continuous: the outgoing face of one
 * wall and the incoming face of the next are extended until they
 * actually meet, instead of each stopping at its own end cap and
 * leaving the overlap visible.
 */
export function offsetPolyline(points: WallPoint[], distance: number, closed: boolean): WallPoint[] {
  const count = points.length;
  if (count < 2) return points.slice();

  const segmentCount = closed ? count : count - 1;
  const directions: Vec[] = [];
  const offsets: { a: Vec; b: Vec }[] = [];
  for (let i = 0; i < segmentCount; i++) {
    const p = points[i];
    const q = points[(i + 1) % count];
    const direction = normalize(sub(q, p));
    directions.push(direction);
    const n = scale(leftNormal(direction), distance);
    offsets.push({ a: add(p, n), b: add(q, n) });
  }

  const result: WallPoint[] = [];
  for (let i = 0; i < count; i++) {
    const incoming = closed ? (i - 1 + segmentCount) % segmentCount : i - 1;
    const outgoing = closed ? i % segmentCount : i;

    const hasIncoming = incoming >= 0 && incoming < segmentCount;
    const hasOutgoing = outgoing >= 0 && outgoing < segmentCount;

    if (!hasIncoming && hasOutgoing) { result.push(offsets[outgoing].a); continue; }
    if (hasIncoming && !hasOutgoing) { result.push(offsets[incoming].b); continue; }
    if (!hasIncoming && !hasOutgoing) { result.push(points[i]); continue; }

    const meeting = intersectLines(offsets[incoming].a, directions[incoming], offsets[outgoing].a, directions[outgoing]);
    if (!meeting) { result.push(offsets[outgoing].a); continue; }

    // Runaway spike guard: past the mitre limit, cut the corner flat.
    if (Math.hypot(meeting.x - points[i].x, meeting.y - points[i].y) > Math.abs(distance) * MITRE_LIMIT) {
      result.push(offsets[incoming].b);
      continue;
    }
    result.push(meeting);
  }
  return result;
}

/** Twice the signed area of a ring. Positive and negative simply mean the two winding directions; only the SIGN is ever used here. */
export function signedArea(ring: WallPoint[]): number {
  let total = 0;
  for (let i = 0; i < ring.length; i++) {
    const a = ring[i];
    const b = ring[(i + 1) % ring.length];
    total += a.x * b.y - b.x * a.y;
  }
  return total;
}

export interface WallBand {
  /** The outer boundary of the wall body. Always present. */
  outer: WallPoint[];
  /** The inner boundary - the room side. Only for a closed chain; an open run has one ring that goes out along one face and back along the other. */
  inner: WallPoint[] | null;
  closed: boolean;
  thickness: number;
  height: number;
  material: string | undefined;
  wallIds: string[];
}

/**
 * The wall body for one chain: one ring for an open run, two
 * (outer + inner) for a closed room.
 *
 * Winding is normalised first, so "outer" really is the outside
 * whichever way round the user happened to draw the room - drawing a
 * room clockwise and anticlockwise must produce the same wall, and
 * without this it produces one wall inside out.
 */
export function bandFromChain(chain: WallChain): WallBand {
  const half = chain.thickness / 2;

  if (chain.closed) {
    // Which sign of the offset goes OUTWARD depends on the ring's
    // winding, and the winding depends on which way round the user
    // happened to click the corners. Rather than reasoning about the
    // sign - screen y points down, so the usual intuition is inverted
    // and the first version of this got it exactly backwards, handing
    // back an "outer" ring smaller than the inner one - both offsets
    // are computed and the one enclosing MORE area is the outer one.
    // That is true by definition, in any coordinate convention.
    const a = offsetPolyline(chain.points, half, true);
    const b = offsetPolyline(chain.points, -half, true);
    const [outer, inner] = Math.abs(signedArea(a)) >= Math.abs(signedArea(b)) ? [a, b] : [b, a];
    return {
      outer,
      inner,
      closed: true,
      thickness: chain.thickness,
      height: chain.height,
      material: chain.material,
      wallIds: chain.wallIds,
    };
  }

  // An open run becomes one ring: out along the left face, back along
  // the right. Butt ends, matching how the walls themselves are drawn.
  const left = offsetPolyline(chain.points, half, false);
  const right = offsetPolyline(chain.points, -half, false);
  return {
    outer: [...left, ...right.reverse()],
    inner: null,
    closed: false,
    thickness: chain.thickness,
    height: chain.height,
    material: chain.material,
    wallIds: chain.wallIds,
  };
}

/**
 * Every wall body on the screen, ready to paint.
 *
 * A chain whose walls disagree about thickness, height or material
 * cannot be ONE body - one body has one of each. It is split back into
 * one band PER WALL so each keeps its own look; the corners between
 * differing walls are butt joints rather than mitres, which is the
 * honest result of asking for two different walls meeting.
 *
 * Splitting rather than DROPPING such a chain matters: the first
 * version returned nothing for a mixed chain, so changing one wall's
 * material made every wall of that room disappear off the drawing.
 */
export function bandsFromWalls(walls: WallElement[]): WallBand[] {
  const bands: WallBand[] = [];
  for (const chain of chainsFromWalls(walls)) {
    if (!chain.mixed) {
      bands.push(bandFromChain(chain));
      continue;
    }
    for (const id of chain.wallIds) {
      const wall = walls.find(w => w.id === id);
      if (!wall) continue;
      bands.push(bandFromChain({
        points: [wall.from, wall.to],
        closed: false,
        wallIds: [wall.id],
        thickness: clampWallThickness(wall.thickness),
        height: clampWallHeight(wall.height),
        material: wall.material,
        mixed: false,
      }));
    }
  }
  return bands;
}

/** The walls of any chain that could NOT be merged - the caller draws these one by one. */
export function unmergedWalls(walls: WallElement[]): WallElement[] {
  const merged = new Set<string>();
  for (const chain of chainsFromWalls(walls)) {
    if (!chain.mixed) chain.wallIds.forEach(id => merged.add(id));
  }
  return walls.filter(w => !merged.has(w.id));
}

// ---- extrusion ------------------------------------------------------------

export interface WallFace {
  points: number[];
  /** Sort key for painter's algorithm - larger is nearer the viewer. */
  depth: number;
  /**
   * Which side of the wall body this face belongs to.
   *
   * 'outer' is the face of the wall NEAREST the viewer, seen from
   * outside the room - the one that would stand between you and the
   * room's contents. 'inner' is the FAR wall's inside face, which is
   * what you actually want to see in a cut-away view.
   *
   * The renderer treats them completely differently: inner faces are
   * drawn at full height, outer ones are cut down to a stub, which is
   * what turns a closed box into a dolls-house view you can see into.
   */
  side: 'outer' | 'inner';
  /** Unit outward normal, for flat shading. Only x is ever interesting - see shadeForNormal in WallLayer. */
  normalX: number;
}

/**
 * The vertical faces of one wall body: for every boundary edge whose
 * outward direction points toward the viewer (down the screen), a quad
 * from the footprint up to the lifted top.
 *
 * Only viewer-facing edges get a face. Drawing all of them would paint
 * the far side of the wall over its own top surface - and cost four
 * times the polygons for three quarters of them to be hidden.
 */
export function extrudeBand(band: WallBand): WallFace[] {
  const faces: WallFace[] = [];
  // The PAINTED height - band.height is the wall's real height.
  const height = drawnWallHeight(band.height);
  if (height <= 0) return faces;

  // EVERY face is generated from the OUTER ring, including the far
  // wall's inner face, which is simply that ring's far edge pushed in
  // by the wall's thickness.
  //
  // Taking the inner face from the inner RING instead - the obvious
  // reading, and the first version here - is subtly wrong: the inner
  // ring is inset by half the thickness, so at every mitred corner it
  // stops short of where the wall body actually reaches, and the face
  // built from it left a notch of bare background above each corner.
  // Patching that with an "extend the ends a bit" fudge only moved the
  // error around, because how much a mitre takes away depends on the
  // corner's angle. Derived from one ring, both faces span exactly the
  // same corners as the body they belong to, at any angle.
  const ring = band.outer;
  const winding = signedArea(ring) >= 0 ? 1 : -1;

  for (let i = 0; i < ring.length; i++) {
    const a = ring[i];
    const b = ring[(i + 1) % ring.length];
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const length = Math.hypot(dx, dy);
    if (length === 0) continue;

    // Unit outward normal of this edge of the outer ring.
    const nx = (dy * winding) / length;
    const ny = (-dx * winding) / length;

    // An edge whose outside points down the screen is a NEAR face: the
    // wall's own outer surface, between the viewer and the room.
    if (ny > 0) {
      faces.push({
        points: [a.x, a.y, b.x, b.y, b.x, b.y - height, a.x, a.y - height],
        depth: Math.max(a.y, b.y),
        side: 'outer',
        normalX: nx,
      });
      continue;
    }

    // An edge pointing away is the FAR wall. What faces the viewer
    // there is its INSIDE, one thickness in - and only for a closed
    // body, since an open run has no inside.
    if (ny < 0 && band.inner) {
      // INWARD is minus the outward normal. Adding it instead pushes
      // the face further out of the building, which left a gap of bare
      // background exactly one thickness deep between the face and the
      // wall body below it.
      const ax = a.x - nx * band.thickness;
      const ay = a.y - ny * band.thickness;
      const bx = b.x - nx * band.thickness;
      const by = b.y - ny * band.thickness;
      faces.push({
        points: [ax, ay, bx, by, bx, by - height, ax, ay - height],
        depth: Math.max(ay, by),
        side: 'inner',
        // It faces back toward the viewer, so its normal is the
        // opposite of the edge's own.
        normalX: -nx,
      });
    }
  }

  return faces;
}

/** One ring as the flat [x0,y0,...] array Konva's Line wants. */
export function ringToPoints(ring: WallPoint[], lift = 0): number[] {
  return ring.flatMap(p => [p.x, p.y - lift]);
}

/** Every endpoint that is not shared with a second wall - i.e. the ends of an unfinished room. */
export function openEndPoints(walls: WallElement[]): { x: number; y: number }[] {
  const counts = new Map<string, { point: { x: number; y: number }; count: number }>();
  for (const wall of walls) {
    for (const p of [wall.from, wall.to]) {
      const key = pointKey(p);
      const entry = counts.get(key);
      if (entry) entry.count += 1;
      else counts.set(key, { point: p, count: 1 });
    }
  }
  return [...counts.values()].filter(e => e.count !== 2).map(e => e.point);
}
