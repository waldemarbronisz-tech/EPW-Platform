// feat/room-plan: openings - doors, windows and gates that are IN a
// wall rather than stuck on top of one.
//
// Until now an opening was a symbol drawn over the wall body: the wall
// ran straight past behind it, so a door read as a sticker on a solid
// wall instead of a hole through it. This module is what turns it into
// a real opening: it works out which wall each opening belongs to and
// hands back the rectangle to CUT OUT of that wall's painted body
// (WallLayer clips it away), plus the jamb lines that close the cut.
//
// The match is GEOMETRIC, not a stored reference. An opening belongs to
// whichever wall it is sitting on, and it stops belonging the moment it
// is dragged off - no link to maintain, nothing to go stale when a wall
// is deleted, and moving the wall or the door needs no bookkeeping at
// all. The same reasoning NetResolver.ts uses for wires and terminals.
//
// Pure functions only, no store and no Konva.

import type { WallElement, WallPoint } from '../elements/WallElement';
import { clampWallThickness, distanceToWall, drawnWallHeight } from '../elements/WallElement';
import type { SynopticObject } from '../store';

/** Symbol types that cut an opening. Everything else placed on a wall stays on top of it, which is correct: a socket is mounted on a wall, it does not pierce it. */
export const OPENING_TYPES = new Set([
  'building.door',
  'building.window',
  'building.gate',
]);

export function isOpeningType(type: string): boolean {
  return OPENING_TYPES.has(type);
}

// How far from a wall's centre line an opening still counts as being
// "in" that wall. Half the thickness plus this, so an opening dropped
// roughly on a wall is taken, and one clearly beside it is not.
const ATTACH_MARGIN = 14;

export interface WallOpening {
  objectId: string;
  wallId: string;
  /** Centre of the opening, projected ONTO the wall's centre line - so the cut is centred in the wall even if the symbol sits slightly off it. */
  center: WallPoint;
  /** Clear width of the opening, along the wall. */
  width: number;
  /** The WALL's direction, in radians. The cut follows the wall, never the symbol's own rotation - a door dropped unrotated onto a diagonal wall still cuts a clean opening. */
  angle: number;
  wallThickness: number;
  /** The wall's PAINTED height. The cut has to clear the extruded body, not just the footprint - see openingCutPolygon. */
  wallDrawnHeight: number;
}

/**
 * The object's centre ON SCREEN, which is not x + w/2 once it is
 * rotated: Konva turns a Group about its own ORIGIN (its top-left), so
 * a rotated object's centre is its origin plus its half-size vector
 * rotated by the same angle.
 *
 * Ignoring that was a real bug, and a self-inflicted one. Seating an
 * opening into a wall that runs right-to-left gives it rotation 180;
 * the naive centre then landed a whole width and height away from the
 * wall, so the opening stopped being recognised as being IN that wall
 * the instant it was seated into it - and the wall was drawn unbroken
 * behind a door that had just been fitted to it. The effect was visible
 * only on walls drawn in one direction, which is exactly the kind of
 * thing that survives a casual look at the screen.
 *
 * This is the exact inverse of topLeftForCenter below; the two must
 * stay inverses, which is what the round-trip test pins.
 */
/** The object's size AS DRAWN: a resized symbol keeps its registered width/height and carries the change in scaleX/scaleY (ObjectNode's transformer end), so every geometric question about it must multiply them in - the first version of the openings did not, and a widened door cut a doorway of its original width (user, 2026-09-18). */
export function effectiveSize(obj: SynopticObject): { width: number; height: number } {
  return { width: obj.width * (obj.scaleX || 1), height: obj.height * (obj.scaleY || 1) };
}

export function objectCenter(obj: SynopticObject): WallPoint {
  const radians = ((obj.rotation || 0) * Math.PI) / 180;
  const cos = Math.cos(radians);
  const sin = Math.sin(radians);
  const { width, height } = effectiveSize(obj);
  const halfW = width / 2;
  const halfH = height / 2;
  return {
    x: obj.x + (halfW * cos - halfH * sin),
    y: obj.y + (halfW * sin + halfH * cos),
  };
}

/** An opening's side on its wall: the hinge/swing flipped to the other side (editor.opening_flipped) - explicit, not read off the angle, because a fresh door dropped on a wall drawn right to left (rotation 0, wall 180) must NOT count as flipped. */
export function isOpeningFlipped(obj: SynopticObject): boolean {
  return !!obj.editor?.opening_flipped;
}

/** True when a freely typed `rotation` is nearer the wall's direction turned by 180 than the direction itself. */
export function openingFlipped(rotation: number, wallAngleDegrees: number): boolean {
  const diff = (((rotation || 0) - wallAngleDegrees) % 360 + 540) % 360 - 180;   // -180..180
  return Math.abs(diff) > 90;
}

/** The wall's direction, or the direction turned by 180 (kept in 0..360) when flipped. */
export function openingRotation(wallAngleDegrees: number, flipped: boolean): number {
  return flipped ? ((wallAngleDegrees + 180) % 360 + 360) % 360 : wallAngleDegrees;
}

/** Projects a point onto a wall's centre line segment, clamped to its ends. */
function projectOntoWall(wall: WallElement, p: WallPoint): WallPoint {
  const dx = wall.to.x - wall.from.x;
  const dy = wall.to.y - wall.from.y;
  const lengthSquared = dx * dx + dy * dy;
  if (lengthSquared === 0) return { ...wall.from };
  let t = ((p.x - wall.from.x) * dx + (p.y - wall.from.y) * dy) / lengthSquared;
  t = Math.max(0, Math.min(1, t));
  return { x: wall.from.x + t * dx, y: wall.from.y + t * dy };
}

/** The wall an opening is sitting on, or null when it is not on one. Nearest wins, so an opening near a corner picks the wall it is actually closest to rather than whichever happened to be drawn first. */
export function wallForOpening(walls: WallElement[], obj: SynopticObject): WallElement | null {
  const center = objectCenter(obj);
  let best: WallElement | null = null;
  let bestDistance = Infinity;
  for (const wall of walls) {
    const distance = distanceToWall(wall, center.x, center.y);
    const reach = clampWallThickness(wall.thickness) / 2 + ATTACH_MARGIN;
    if (distance <= reach && distance < bestDistance) {
      best = wall;
      bestDistance = distance;
    }
  }
  return best;
}

/** Every opening currently seated in a wall. */
export function findWallOpenings(walls: WallElement[], objects: SynopticObject[]): WallOpening[] {
  const openings: WallOpening[] = [];
  for (const obj of objects) {
    if (!isOpeningType(obj.type)) continue;
    const wall = wallForOpening(walls, obj);
    if (!wall) continue;
    openings.push({
      objectId: obj.id,
      wallId: wall.id,
      center: projectOntoWall(wall, objectCenter(obj)),
      width: effectiveSize(obj).width,
      angle: Math.atan2(wall.to.y - wall.from.y, wall.to.x - wall.from.x),
      wallThickness: clampWallThickness(wall.thickness),
      wallDrawnHeight: drawnWallHeight(wall.height),
    });
  }
  return openings;
}

/**
 * Deliberately cut DEEPER than the wall is thick: a cut exactly as deep
 * as the wall leaves a hairline of wall paint on both faces from
 * antialiasing, which reads as a door with a pane of wall still across
 * it.
 */
const OVERCUT = 2;

/** The footprint of the cut - the hole as it would be on a flat plan. */
function footprintCut(opening: WallOpening): WallPoint[] {
  const halfWidth = opening.width / 2;
  const halfDepth = opening.wallThickness / 2 + OVERCUT;
  const cos = Math.cos(opening.angle);
  const sin = Math.sin(opening.angle);
  // Along the wall, and across it.
  const ax = cos * halfWidth;
  const ay = sin * halfWidth;
  const bx = -sin * halfDepth;
  const by = cos * halfDepth;
  const { x, y } = opening.center;
  return [
    { x: x - ax - bx, y: y - ay - by },
    { x: x + ax - bx, y: y + ay - by },
    { x: x + ax + bx, y: y + ay + by },
    { x: x - ax + bx, y: y - ay + by },
  ];
}

/** Andrew's monotone chain. Small and exact, which is all this needs. */
function convexHull(points: WallPoint[]): WallPoint[] {
  const sorted = [...points].sort((a, b) => (a.x - b.x) || (a.y - b.y));
  const cross = (o: WallPoint, a: WallPoint, b: WallPoint) =>
    (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);

  const build = (list: WallPoint[]) => {
    const stack: WallPoint[] = [];
    for (const p of list) {
      while (stack.length >= 2 && cross(stack[stack.length - 2], stack[stack.length - 1], p) <= 0) {
        stack.pop();
      }
      stack.push(p);
    }
    stack.pop();
    return stack;
  };

  return [...build(sorted), ...build([...sorted].reverse())];
}

/**
 * The polygon to cut out of the PAINTED wall body.
 *
 * Not just the footprint: the wall is drawn extruded straight up the
 * screen, so a hole the size of the footprint leaves the part of the
 * body that rises ABOVE it completely intact - and that leftover paint
 * sits directly over the opening. On a cut-away near wall the effect is
 * that a door reads as a door drawn ON a wall again, which is the very
 * thing the cut exists to fix.
 *
 * So the cut is the footprint swept upward by the wall's own painted
 * height: the convex hull of the footprint and the same footprint
 * lifted. For an axis-aligned wall that is a rectangle; for a diagonal
 * one it is a hexagon, and the hull gets both right without a special
 * case.
 */
export function openingCutPolygon(opening: WallOpening): WallPoint[] {
  const footprint = footprintCut(opening);
  if (opening.wallDrawnHeight <= 0) return footprint;
  const lifted = footprint.map(p => ({ x: p.x, y: p.y - opening.wallDrawnHeight }));
  return convexHull([...footprint, ...lifted]);
}

/**
 * The two jamb lines that close an opening's cut - the reveals at either
 * end, across the wall.
 *
 * Taken from the FOOTPRINT, not from the swept cut polygon: the jambs
 * mark where the wall stops on the plan, and the swept polygon's
 * corners are up in the air where the extrusion put them.
 */
export function openingJambs(opening: WallOpening): [WallPoint, WallPoint][] {
  const cut = footprintCut(opening);
  // cut[0]..cut[3] runs: start-near, end-near, end-far, start-far.
  return [
    [cut[0], cut[3]],
    [cut[1], cut[2]],
  ];
}

/**
 * Where an opening object must be placed to sit square in its wall:
 * centred on the wall's line and turned to the wall's own angle.
 *
 * Returned in the object's own x/y/rotation terms (top-left corner plus
 * degrees), so a caller can apply it straight to updateObject. Null when
 * the object is not on a wall at all - it is then left exactly where the
 * user put it, which is the right answer for a door being parked off to
 * one side while the plan is rearranged.
 */
export function seatOpeningInWall(
  walls: WallElement[],
  obj: SynopticObject
): { x: number; y: number; rotation: number } | null {
  const wall = wallForOpening(walls, obj);
  if (!wall) return null;
  const center = projectOntoWall(wall, objectCenter(obj));
  const wallAngle = (Math.atan2(wall.to.y - wall.from.y, wall.to.x - wall.from.x) * 180) / Math.PI;
  // Along the wall, one way or the other: a door keeps the side its
  // hinge/swing was flipped to (rotateSelected toggles editor.opening_flipped).
  const rotation = openingRotation(wallAngle, isOpeningFlipped(obj));
  const { width, height } = effectiveSize(obj);
  return {
    // Konva rotates a Group about its own origin (top-left), so the
    // top-left that puts the CENTRE on the wall is the centre minus
    // the half-size vector (at the DRAWN size), itself rotated by the
    // same angle.
    ...topLeftForCenter(center, width, height, rotation),
    rotation,
  };
}

/** The x/y an object needs so that its centre lands on `center` once rotated by `degrees` about its top-left. */
export function topLeftForCenter(
  center: WallPoint, width: number, height: number, degrees: number
): { x: number; y: number } {
  const radians = (degrees * Math.PI) / 180;
  const cos = Math.cos(radians);
  const sin = Math.sin(radians);
  const halfW = width / 2;
  const halfH = height / 2;
  return {
    x: center.x - (halfW * cos - halfH * sin),
    y: center.y - (halfW * sin + halfH * cos),
  };
}
