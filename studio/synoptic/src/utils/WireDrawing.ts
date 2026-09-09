// Freehand orthogonal wire drawing - the pure geometry, kept Konva-free
// (safe to import from a Vitest test run under Node) so Canvas.tsx's
// mouse/keyboard handlers stay thin wrappers around this.

import type { WirePoint } from '../store';
import { GRID_SIZE } from '../theme/ScadaTheme';

export function snapPointToGrid(x: number, y: number): WirePoint {
  return { x: Math.round(x / GRID_SIZE) * GRID_SIZE, y: Math.round(y / GRID_SIZE) * GRID_SIZE };
}

/**
 * Appends a new (already grid-snapped) point to an in-progress wire.
 * Every segment must stay horizontal or vertical - if the new point
 * does not already share an x or a y with the wire's current last
 * point, one automatic right-angle bend is inserted first (horizontal
 * leg out of the last point, then vertical into the new point), so a
 * diagonal mouse movement always yields a clean two-segment corner
 * instead of ever recording a diagonal segment.
 */
export function appendWirePoint(points: WirePoint[], next: WirePoint): WirePoint[] {
  if (points.length === 0) return [next];
  const last = points[points.length - 1];
  if (last.x === next.x && last.y === next.y) return points; // no zero-length segment
  if (last.x === next.x || last.y === next.y) return [...points, next];
  const elbow: WirePoint = { x: next.x, y: last.y };
  return [...points, elbow, next];
}

/** Backspace while drawing: undo the last bend (or the whole in-progress point if it was the only one). */
export function removeLastWirePoint(points: WirePoint[]): WirePoint[] {
  return points.slice(0, -1);
}

/**
 * After dragging one point of an already-finished wire to a new
 * (grid-snapped) position, re-derive the one or two segments touching
 * it so the whole wire stays orthogonal - inserting an elbow on either
 * side if needed, the same way appendWirePoint does while drawing. Only
 * ever touches the moved point and its immediate neighbors.
 */
export function reorthogonalizeAfterMove(points: WirePoint[], movedIndex: number, newPos: WirePoint): WirePoint[] {
  const result = [...points];
  result[movedIndex] = newPos;

  const insertElbowBetween = (i: number, j: number): void => {
    const a = result[i];
    const b = result[j];
    if (a.x === b.x || a.y === b.y) return;
    result.splice(i + 1, 0, { x: b.x, y: a.y });
  };

  // Fix the segment AFTER the moved point first, so that insertion does
  // not shift the "before" segment's indices out from under it.
  if (movedIndex < result.length - 1) insertElbowBetween(movedIndex, movedIndex + 1);
  if (movedIndex > 0) insertElbowBetween(movedIndex - 1, movedIndex);
  return result;
}

/**
 * Collapses any run of three consecutive points that lie on one
 * straight line (all sharing an x, or all sharing a y) down to two -
 * the middle one adds nothing to the wire's own shape. fix/wiring-and-
 * library-groups commit 2: the actual fix for "przesuwanie symbolu
 * mnozy wezly" - see WireAnchoring.ts's own syncAnchoredConnections for
 * why repeatedly reorthogonalizing the SAME anchored point (once per
 * symbol move) otherwise leaves one stale elbow behind per move,
 * without ever removing it, even though every fresh elbow this
 * function's own caller inserts ends up exactly collinear with the one
 * before it once traced back to the same fixed reference point - this
 * is the general-purpose cleanup that collapses that whole chain back
 * down to just the one elbow actually needed right now, regardless of
 * how many times it has been moved before.
 *
 * Never drops an ANCHORED point even when it happens to be
 * geometrically redundant - it still carries meaning (which terminal
 * it follows) that a plain bend does not, and NetResolver's own
 * touching rule (pointOnSegment, not vertex membership) means removing
 * a genuinely redundant FREE point never breaks a net some other wire
 * happens to tap into at that same coordinate - the resulting single,
 * longer segment still passes exactly through it.
 */
export function simplifyCollinearPoints(points: WirePoint[]): WirePoint[] {
  if (points.length < 3) return points;
  const result: WirePoint[] = [points[0]];
  for (let i = 1; i < points.length - 1; i++) {
    const prev = result[result.length - 1];
    const curr = points[i];
    const next = points[i + 1];
    const collinear = (prev.x === curr.x && curr.x === next.x) || (prev.y === curr.y && curr.y === next.y);
    if (collinear && !curr.anchor) continue; // adds nothing to the shape - drop it
    result.push(curr);
  }
  result.push(points[points.length - 1]);
  return result;
}

/** Alt+click on a segment: insert a new bend point there. */
export function insertBendOnSegment(points: WirePoint[], segmentIndex: number, atPoint: WirePoint): WirePoint[] {
  if (segmentIndex < 0 || segmentIndex >= points.length - 1) return points;
  const result = [...points];
  result.splice(segmentIndex + 1, 0, atPoint);
  return result;
}

function clamp(v: number, lo: number, hi: number): number {
  return Math.min(Math.max(v, lo), hi);
}

/**
 * The nearest point ON one of a wire's own segments to an arbitrary
 * canvas position, snapped to the grid - what Alt+click on a wire uses
 * to place its new bend exactly on the segment that was clicked.
 */
export function nearestPointOnPolyline(points: WirePoint[], target: WirePoint): { segmentIndex: number; point: WirePoint } | null {
  if (points.length < 2) return null;

  let best: { segmentIndex: number; point: WirePoint; dist: number } | null = null;
  for (let i = 0; i < points.length - 1; i++) {
    const a = points[i];
    const b = points[i + 1];
    let px: number;
    let py: number;
    if (a.x === b.x) {
      px = a.x;
      py = clamp(target.y, Math.min(a.y, b.y), Math.max(a.y, b.y));
    } else {
      py = a.y;
      px = clamp(target.x, Math.min(a.x, b.x), Math.max(a.x, b.x));
    }
    const snapped = snapPointToGrid(px, py);
    const dist = Math.hypot(snapped.x - target.x, snapped.y - target.y);
    if (!best || dist < best.dist) best = { segmentIndex: i, point: snapped, dist };
  }
  return best ? { segmentIndex: best.segmentIndex, point: best.point } : null;
}
