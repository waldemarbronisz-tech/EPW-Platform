// feat/editing-and-signal-panel commit 3: rubber-band selection
// containment checks. Pure, Konva-free (same convention as GridSnap.ts/
// Terminals.ts/WireDrawing.ts) - an element is selected only if it lies
// ENTIRELY within the box, never on a partial overlap: an element
// poking out past the box's edge is left unselected, on purpose.

export interface Box {
  x: number;
  y: number;
  width: number;
  height: number;
}

export function isObjectFullyInBox(obj: { x: number; y: number; width: number; height: number; scaleX?: number; scaleY?: number }, box: Box): boolean {
  const w = obj.width * (obj.scaleX || 1);
  const h = obj.height * (obj.scaleY || 1);
  return obj.x >= box.x && obj.y >= box.y && obj.x + w <= box.x + box.width && obj.y + h <= box.y + box.height;
}

/** height is the meter's own COMPUTED height (MeterElement.ts's computeMeterHeight) - a meter carries no height field of its own to read here. */
export function isMeterFullyInBox(meter: { x: number; y: number; width: number }, height: number, box: Box): boolean {
  return meter.x >= box.x && meter.y >= box.y && meter.x + meter.width <= box.x + box.width && meter.y + height <= box.y + box.height;
}

export function isConnectionFullyInBox(conn: { points: { x: number; y: number }[] }, box: Box): boolean {
  if (conn.points.length === 0) return false;
  return conn.points.every(p => p.x >= box.x && p.y >= box.y && p.x <= box.x + box.width && p.y <= box.y + box.height);
}

export interface MixedSelection {
  objectIds: string[];
  connectionIds: string[];
  meterIds: string[];
  signalPanelIds: string[];
  frameIds: string[];
  groupCommandIds: string[];
  setpointPanelIds: string[];
  // feat/cad-marquee: walls were never part of a rubber-band selection,
  // which made a room impossible to select as a whole. Optional, so a
  // caller written before walls could be selected still merges instead
  // of throwing - an older call site is a missing KIND, not a bug.
  wallIds?: string[];
}

/**
 * feat/appearance-selection-frames commit 2d: what a Shift+drag rubber-
 * band adds to an existing selection - every id newly found inside the
 * box, unioned into whatever was already selected, per kind,
 * duplicate-free. Extracted out of Canvas.tsx's own handleMouseUp (the
 * same reason every other pure piece of rubber-band logic in this file
 * already lives here, not inline in the component) so this specific
 * "Shift adds instead of replacing" rule is directly testable without
 * a Konva rendering harness.
 */
export function mergeSelectionAdditive(existing: MixedSelection, found: Partial<MixedSelection>): MixedSelection {
  return {
    objectIds: [...new Set([...existing.objectIds, ...(found.objectIds || [])])],
    connectionIds: [...new Set([...existing.connectionIds, ...(found.connectionIds || [])])],
    meterIds: [...new Set([...existing.meterIds, ...(found.meterIds || [])])],
    signalPanelIds: [...new Set([...existing.signalPanelIds, ...(found.signalPanelIds || [])])],
    frameIds: [...new Set([...existing.frameIds, ...(found.frameIds || [])])],
    groupCommandIds: [...new Set([...existing.groupCommandIds, ...(found.groupCommandIds || [])])],
    setpointPanelIds: [...new Set([...existing.setpointPanelIds, ...(found.setpointPanelIds || [])])],
    wallIds: [...new Set([...(existing.wallIds || []), ...(found.wallIds || [])])]
  };
}

// ---------------------------------------------------------------------
// feat/cad-marquee: window and crossing selection, as every CAD has done
// it for thirty years.
//
// Dragging LEFT to RIGHT is a WINDOW: only what lies entirely inside is
// caught. Dragging RIGHT to LEFT is a CROSSING: touching is enough. The
// distinction is not a preference, it is the whole reason a marquee is
// usable on a crowded drawing - a window picks the one symbol standing
// clear, a crossing sweeps up a wall run you cannot possibly enclose
// without also enclosing the room's whole contents.
//
// The direction is read from the drag itself rather than from a
// modifier, because that is the gesture people already have in their
// hands, and because a modifier would need teaching.

/** WINDOW - fully inside; CROSSING - touching is enough. */
export type MarqueeMode = 'WINDOW' | 'CROSSING';

/** Which kind of marquee a drag from `startX` to `currentX` is. A drag with no horizontal movement at all is a window: it catches less, and catching too much is the error that is harder to notice. */
export function marqueeMode(startX: number, currentX: number): MarqueeMode {
  return currentX < startX ? 'CROSSING' : 'WINDOW';
}

/** Whether two axis-aligned rectangles touch at all. Edge contact counts - a symbol exactly on the marquee's edge was dragged over, and refusing it would feel like a miss. */
export function rectsOverlap(a: Box, b: Box): boolean {
  return a.x <= b.x + b.width && a.x + a.width >= b.x
    && a.y <= b.y + b.height && a.y + a.height >= b.y;
}

/** Whether a segment touches a box: either end inside, or the segment crossing any of the four edges. */
export function segmentTouchesBox(
  p1: { x: number; y: number },
  p2: { x: number; y: number },
  box: Box
): boolean {
  const inside = (p: { x: number; y: number }) =>
    p.x >= box.x && p.x <= box.x + box.width && p.y >= box.y && p.y <= box.y + box.height;
  if (inside(p1) || inside(p2)) return true;

  const corners = [
    { x: box.x, y: box.y },
    { x: box.x + box.width, y: box.y },
    { x: box.x + box.width, y: box.y + box.height },
    { x: box.x, y: box.y + box.height },
  ];
  for (let i = 0; i < 4; i++) {
    if (segmentsIntersect(p1, p2, corners[i], corners[(i + 1) % 4])) return true;
  }
  return false;
}

type Point = { x: number; y: number };

function cross(o: Point, a: Point, b: Point): number {
  return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
}

/** Proper segment intersection, including the collinear-overlap case - a wall lying exactly along the marquee's edge is touching it. */
function segmentsIntersect(a1: Point, a2: Point, b1: Point, b2: Point): boolean {
  const d1 = cross(b1, b2, a1);
  const d2 = cross(b1, b2, a2);
  const d3 = cross(a1, a2, b1);
  const d4 = cross(a1, a2, b2);
  if (((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) && ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0))) return true;
  const onSegment = (p: Point, q: Point, r: Point) =>
    Math.min(p.x, r.x) <= q.x && q.x <= Math.max(p.x, r.x)
    && Math.min(p.y, r.y) <= q.y && q.y <= Math.max(p.y, r.y);
  if (d1 === 0 && onSegment(b1, a1, b2)) return true;
  if (d2 === 0 && onSegment(b1, a2, b2)) return true;
  if (d3 === 0 && onSegment(a1, b1, a2)) return true;
  if (d4 === 0 && onSegment(a1, b2, a2)) return true;
  return false;
}

/** An object's own bounding box, scale included. */
function objectBox(obj: { x: number; y: number; width: number; height: number; scaleX?: number; scaleY?: number }): Box {
  return {
    x: obj.x,
    y: obj.y,
    width: obj.width * (obj.scaleX || 1),
    height: obj.height * (obj.scaleY || 1),
  };
}

export function isObjectInBox(
  obj: { x: number; y: number; width: number; height: number; scaleX?: number; scaleY?: number },
  box: Box,
  mode: MarqueeMode
): boolean {
  return mode === 'WINDOW' ? isObjectFullyInBox(obj, box) : rectsOverlap(objectBox(obj), box);
}

export function isMeterInBox(
  meter: { x: number; y: number; width: number },
  height: number,
  box: Box,
  mode: MarqueeMode
): boolean {
  return mode === 'WINDOW'
    ? isMeterFullyInBox(meter, height, box)
    : rectsOverlap({ x: meter.x, y: meter.y, width: meter.width, height }, box);
}

export function isConnectionInBox(
  conn: { points: { x: number; y: number }[] },
  box: Box,
  mode: MarqueeMode
): boolean {
  if (mode === 'WINDOW') return isConnectionFullyInBox(conn, box);
  if (conn.points.length === 0) return false;
  if (conn.points.length === 1) {
    const p = conn.points[0];
    return p.x >= box.x && p.x <= box.x + box.width && p.y >= box.y && p.y <= box.y + box.height;
  }
  for (let i = 0; i < conn.points.length - 1; i++) {
    if (segmentTouchesBox(conn.points[i], conn.points[i + 1], box)) return true;
  }
  return false;
}

/**
 * Whether a wall is caught by the marquee.
 *
 * Walls were never part of rubber-band selection at all before this,
 * which made a room impossible to select as a whole - you could only
 * click its walls one at a time. A wall is a SEGMENT, not a box, so it
 * gets its own test rather than being approximated by its bounding
 * rectangle: a long diagonal wall's bounding box covers most of a room,
 * and selecting it by dragging anywhere near that box would be wrong in
 * a way nobody could predict.
 */
export function isWallInBox(
  wall: { from: { x: number; y: number }; to: { x: number; y: number } },
  box: Box,
  mode: MarqueeMode
): boolean {
  if (mode === 'WINDOW') {
    const inside = (p: { x: number; y: number }) =>
      p.x >= box.x && p.x <= box.x + box.width && p.y >= box.y && p.y <= box.y + box.height;
    return inside(wall.from) && inside(wall.to);
  }
  return segmentTouchesBox(wall.from, wall.to, box);
}
