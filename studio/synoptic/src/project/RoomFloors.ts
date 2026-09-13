// feat/room-plan: floors. Pure functions only, no store dependency -
// takes a plain walls array, returns plain polygons, the same shape
// NetResolver.ts and CircuitResolver.ts next door already follow.
//
// There is no "floor element" the user draws. A floor is DERIVED: when
// walls happen to enclose an area, that area gets a floor. Drawing the
// room is the only act; the floor follows from it, and moving a wall
// re-derives it with no second thing to keep in sync.
//
// SCOPE, stated up front because the limit is deliberate and visible:
// only a SIMPLE closed loop is filled - a group of walls where every
// endpoint joins exactly two walls. That is a room outline: four walls
// round a rectangle, six round an L. A group with a T-junction, a
// dangling stub, or a shared internal wall has more than one possible
// interpretation of "the room", so it gets NO floor rather than a
// guessed one. An unfilled room is a user looking at their drawing and
// seeing a gap they can close; a wrongly filled one is a user
// wondering what the editor thinks it is looking at.

import type { WallElement, WallPoint } from '../elements/WallElement';

// Endpoints that land within this many units of each other are the
// same corner. Walls are drawn chained and grid-snapped, so in practice
// they match exactly - this only absorbs float drift from a drag.
const JOIN_TOLERANCE = 1.5;

function pointKey(p: WallPoint): string {
  // Quantize to the tolerance so two corners that should be one always
  // produce one key. Rounding (not truncating) keeps the cell centered
  // on the actual coordinate.
  const q = (v: number) => Math.round(v / JOIN_TOLERANCE);
  return `${q(p.x)}:${q(p.y)}`;
}

interface Node {
  point: WallPoint;
  edges: { to: string; wallId: string }[];
}

/**
 * Every simple closed loop the given walls form, as a polygon of its
 * corner points in traversal order. Returns an empty array when the
 * walls enclose nothing - the normal state while a room is still being
 * drawn, never an error.
 */
export function findClosedRooms(walls: WallElement[]): WallPoint[][] {
  const nodes = new Map<string, Node>();

  for (const wall of walls) {
    const fromKey = pointKey(wall.from);
    const toKey = pointKey(wall.to);
    // A zero-length wall would make a self-loop that no traversal can
    // resolve - it is not part of any room outline.
    if (fromKey === toKey) continue;

    if (!nodes.has(fromKey)) nodes.set(fromKey, { point: wall.from, edges: [] });
    if (!nodes.has(toKey)) nodes.set(toKey, { point: wall.to, edges: [] });
    nodes.get(fromKey)!.edges.push({ to: toKey, wallId: wall.id });
    nodes.get(toKey)!.edges.push({ to: fromKey, wallId: wall.id });
  }

  const rooms: WallPoint[][] = [];
  const visited = new Set<string>();

  for (const startKey of nodes.keys()) {
    if (visited.has(startKey)) continue;

    // Walk this whole connected component first, so a component that
    // fails the every-node-has-degree-2 test is rejected as a WHOLE
    // rather than partly walked and left half-marked.
    const component: string[] = [];
    const queue = [startKey];
    const seen = new Set<string>([startKey]);
    while (queue.length > 0) {
      const key = queue.shift()!;
      component.push(key);
      for (const edge of nodes.get(key)!.edges) {
        if (!seen.has(edge.to)) {
          seen.add(edge.to);
          queue.push(edge.to);
        }
      }
    }
    component.forEach(k => visited.add(k));

    // A simple cycle, and nothing else, has every node joining exactly
    // two walls. Anything else is ambiguous - see this file's header.
    const isSimpleLoop = component.length >= 3
      && component.every(k => nodes.get(k)!.edges.length === 2);
    if (!isSimpleLoop) continue;

    // Walk the cycle in order, never stepping back along the wall just
    // used (each node has exactly two, so "the other one" is always
    // well defined).
    const polygon: WallPoint[] = [];
    let currentKey = startKey;
    let previousWallId: string | null = null;
    for (let i = 0; i < component.length; i++) {
      const node = nodes.get(currentKey)!;
      polygon.push(node.point);
      const next = node.edges.find(e => e.wallId !== previousWallId);
      // Cannot happen for a degree-2 component, but a malformed input
      // must stop the walk rather than loop forever.
      if (!next) break;
      previousWallId = next.wallId;
      currentKey = next.to;
    }

    if (polygon.length === component.length) rooms.push(polygon);
  }

  return rooms;
}

/** One room polygon as the flat [x0,y0,x1,y1,...] array Konva's Line wants. */
export function roomToPoints(room: WallPoint[]): number[] {
  return room.flatMap(p => [p.x, p.y]);
}
