// feat/room-plan: the wall element - a straight architectural wall
// segment, drawn end to end, used to outline a room on a floor plan.
// Pure data model + pure math only; Konva rendering lives in
// WallElementNode.tsx, the same split FrameElement/MeterElement already
// use.
//
// A wall is NOT a symbol: no terminals, no state, no aparat link, never
// in SymbolRegistry.ts. It is a project-level element like the frame -
// its own array in the store, its own selection kind.
//
// SHAPE: from/to points, matching project/ProjectV2Schema.ts's own
// WallElement exactly, so the eventual v1 -> v2 migration has nothing
// to translate for this element. The ONE addition is `thickness`, which
// V2's own comment explicitly says it left out. That divergence is
// deliberate and was asked for: a plan wall drawn as a hairline reads
// as a wire, not a wall. A v2 writer would simply drop the field.
//
// Walls are chained, not free-floating: the drawing tool starts each
// new segment at the previous one's end point (Canvas.tsx), so a room
// is four clicks around its corners rather than four separate drags.

import { GRID_SIZE } from '../theme/ScadaTheme';
import type { WallMaterialId } from '../theme/Materials';
import { cm } from '../theme/Scale';

export interface WallPoint {
  x: number;
  y: number;
}

export interface WallElement {
  id: string;
  from: WallPoint;
  to: WallPoint;
  thickness: number;
  // The wall's REAL height, on the same scale as every other dimension
  // in the BUDYNEK department (theme/Scale.ts) - 250 means 2.5 m, not
  // 250 px of paint. What actually gets painted is drawnWallHeight()
  // below, which foreshortens it; see the note there for why, and why
  // that is a projection rather than a fudge.
  //
  // The extrusion is a paint pass ONLY. from/to stay plain plan
  // coordinates and every hit test, drag and snap works on the flat
  // footprint - this is explicitly NOT a revival of the isometric PLAN
  // screen kind that chore/remove-isometric-plan-mode deleted, which
  // changed the whole screen's projection and editing model.
  //
  // Optional so a wall saved before this field existed still loads -
  // callers fall back to WALL_DEFAULT_HEIGHT.
  height?: number;
  // Which material this wall is painted with (theme/Materials.ts).
  // Per-wall rather than per-screen on purpose: one room genuinely can
  // have a brick feature wall and plaster everywhere else, and a wall
  // is the thing you click to change it. Optional and additive -
  // absent falls back to DEFAULT_WALL_MATERIAL.
  material?: WallMaterialId;
}

// A wall thinner than this stops reading as a wall at normal zoom; one
// thicker than a grid cell starts swallowing the fixtures placed on it.
export const WALL_MIN_THICKNESS = 2;
export const WALL_MAX_THICKNESS = GRID_SIZE;
export const WALL_DEFAULT_THICKNESS = 8;

// A drag shorter than this is a mis-click, not a wall - see
// isDegenerateWall below for what the caller does with that.
export const WALL_MIN_LENGTH = GRID_SIZE;

/** Clamps a thickness into the supported range. Never returns NaN: a non-finite input falls back to the default rather than propagating into the rendered geometry. */
export function clampWallThickness(thickness: number): number {
  if (!Number.isFinite(thickness)) return WALL_DEFAULT_THICKNESS;
  return Math.min(WALL_MAX_THICKNESS, Math.max(WALL_MIN_THICKNESS, thickness));
}

/** The wall's length in canvas units. */
export function wallLength(wall: Pick<WallElement, 'from' | 'to'>): number {
  const dx = wall.to.x - wall.from.x;
  const dy = wall.to.y - wall.from.y;
  return Math.hypot(dx, dy);
}

/**
 * Whether these two points are too close together to be a real wall.
 * The caller (Canvas.tsx) uses this to DISCARD such a gesture rather
 * than clamping it to a minimum length the way a frame does: a frame
 * has a position to keep even when the drag was tiny, but a wall
 * clamped to a minimum would point in an arbitrary direction the user
 * never indicated. Dropping it is the honest outcome.
 */
export function isDegenerateWall(from: WallPoint, to: WallPoint): boolean {
  return wallLength({ from, to }) < WALL_MIN_LENGTH;
}

/**
 * The wall's axis-aligned bounding box, widened by half the thickness
 * on every side so it covers what is actually drawn (a thick wall
 * extends past the bare centre line). Used for rubber-band selection
 * and hit testing, exactly like a frame's own rect is.
 */
export function wallBounds(wall: WallElement): { x: number; y: number; width: number; height: number } {
  const half = clampWallThickness(wall.thickness) / 2;
  const x = Math.min(wall.from.x, wall.to.x) - half;
  const y = Math.min(wall.from.y, wall.to.y) - half;
  const width = Math.abs(wall.to.x - wall.from.x) + half * 2;
  const height = Math.abs(wall.to.y - wall.from.y) + half * 2;
  return { x, y, width, height };
}

/**
 * Shortest distance from a point to the wall's centre line (a real
 * segment distance, not an infinite-line one - a point far beyond an
 * end cap must not count as near the wall). Used for click hit testing,
 * where a bounding box alone would make every diagonal wall grab
 * clicks across the whole rectangle it spans.
 */
export function distanceToWall(wall: Pick<WallElement, 'from' | 'to'>, px: number, py: number): number {
  const { from, to } = wall;
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const lengthSquared = dx * dx + dy * dy;
  if (lengthSquared === 0) return Math.hypot(px - from.x, py - from.y);
  // Projection of the point onto the segment, clamped to [0,1] so it
  // never runs off either end.
  let t = ((px - from.x) * dx + (py - from.y) * dy) / lengthSquared;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(px - (from.x + t * dx), py - (from.y + t * dy));
}

/** Moves a whole wall by a delta - both ends together, so it never deforms. The shape every drag/arrow-key/paste path needs. */
export function moveWall(wall: WallElement, dx: number, dy: number): Pick<WallElement, 'from' | 'to'> {
  return {
    from: { x: wall.from.x + dx, y: wall.from.y + dy },
    to: { x: wall.to.x + dx, y: wall.to.y + dy },
  };
}

// ---- 2.5D extrusion ------------------------------------------------------
// Pure geometry for the low-poly look. Lives here, beside the model,
// rather than inside the Konva component: it is ordinary maths with
// exact expected outputs, so it can be unit-tested without mounting a
// canvas - the same split every other element file already uses.

// Wall height is a REAL DIMENSION now, on the same scale as everything
// else in the BUDYNEK department (theme/Scale.ts): the default is a
// 2.5 m storey, and the range runs from a flat plan up to 4 m.
//
// It is not DRAWN at that size, and that is not a fudge - it is what
// every 3D view does. A 2.5 m wall drawn at its full 200 px would bury
// the 4 m room it encloses, because this projection has no perspective
// to foreshorten it. WALL_VIEW_FORESHORTENING is that foreshortening,
// applied once, in drawnWallHeight() - so the stored number stays a
// real height (and can be scheduled, listed and costed as one) while
// the picture stays readable.
export const WALL_DEFAULT_HEIGHT = cm(250);
export const WALL_MIN_HEIGHT = 0;   // 0 = flat plan, the pre-3D look, still supported
export const WALL_MAX_HEIGHT = cm(400);

/**
 * How much of a wall's real height is actually drawn.
 *
 * Tuned by looking, not derived: at 0.34 a 2.5 m wall draws 68 px and
 * the far wall's inside face stops reading as a wall at all - it
 * becomes a grey slab sitting above the room, because this projection
 * has no perspective to make it recede. At 0.2 the same wall draws
 * 40 px, which is what the room looked right at. The stored height
 * stays fully real either way - it is what the schedule counts and
 * what a future perspective view would use.
 */
export const WALL_VIEW_FORESHORTENING = 0.2;

/** Clamps a wall height into the supported range, falling back to the default for a missing or non-finite value. */
export function clampWallHeight(height: number | undefined): number {
  if (height === undefined || !Number.isFinite(height)) return WALL_DEFAULT_HEIGHT;
  return Math.min(WALL_MAX_HEIGHT, Math.max(WALL_MIN_HEIGHT, height));
}

/** The height a wall is PAINTED at - its real height, foreshortened. Every renderer and every hit test must use this, never the raw value, or the picture and the mouse disagree. */
export function drawnWallHeight(height: number | undefined): number {
  return clampWallHeight(height) * WALL_VIEW_FORESHORTENING;
}

/** A flat polygon, as the flat [x0,y0,x1,y1,...] array Konva's Line wants. */
export type FacePoints = number[];

export interface WallFaces {
  /** The wall's footprint on the floor - the flat plan rectangle. Drawn first, as the shadow/base. */
  base: FacePoints;
  /** The top surface of the wall: the footprint lifted by `height`. Lightest face. */
  top: FacePoints;
  /** The face turned toward the viewer (the long side with the greater y). Mid tone. Empty when height is 0. */
  side: FacePoints;
}

/**
 * The three flat-shaded faces that make one extruded wall.
 *
 * The projection is the cheapest one that reads as 3D and keeps
 * editing honest: "up" is straight negative y on screen, so a wall's
 * FOOTPRINT never moves and plan coordinates stay plan coordinates.
 * Only the painted body leans upward. A true isometric projection
 * would move every footprint, which is precisely the thing the removed
 * PLAN mode did and which this must not reintroduce.
 *
 * Face choice: of the footprint's two long edges, the one with the
 * greater average y is nearer the viewer in a top-down-ish view, so
 * that is the side actually visible. Drawing both would z-fight and
 * paint a face that should be hidden behind the wall.
 */
export function computeWallFaces(wall: Pick<WallElement, 'from' | 'to' | 'thickness' | 'height'>): WallFaces {
  const thickness = clampWallThickness(wall.thickness);
  // Painted height, not the real one - see drawnWallHeight.
  const height = drawnWallHeight(wall.height);

  const dx = wall.to.x - wall.from.x;
  const dy = wall.to.y - wall.from.y;
  const length = Math.hypot(dx, dy);
  // A degenerate wall has no direction to take a normal from - hand
  // back empty faces rather than dividing by zero and painting NaNs.
  if (length === 0) return { base: [], top: [], side: [] };

  // Unit normal to the wall, scaled to half its thickness.
  const nx = (-dy / length) * (thickness / 2);
  const ny = (dx / length) * (thickness / 2);

  const a1 = { x: wall.from.x + nx, y: wall.from.y + ny };
  const b1 = { x: wall.to.x + nx, y: wall.to.y + ny };
  const a2 = { x: wall.from.x - nx, y: wall.from.y - ny };
  const b2 = { x: wall.to.x - nx, y: wall.to.y - ny };

  const base: FacePoints = [a1.x, a1.y, b1.x, b1.y, b2.x, b2.y, a2.x, a2.y];
  const top: FacePoints = [
    a1.x, a1.y - height, b1.x, b1.y - height,
    b2.x, b2.y - height, a2.x, a2.y - height,
  ];

  if (height <= 0) return { base, top, side: [] };

  // Whichever long edge sits lower on screen is the one facing us.
  const edge = (a1.y + b1.y) / 2 >= (a2.y + b2.y) / 2 ? [a1, b1] : [a2, b2];
  const side: FacePoints = [
    edge[0].x, edge[0].y,
    edge[1].x, edge[1].y,
    edge[1].x, edge[1].y - height,
    edge[0].x, edge[0].y - height,
  ];

  return { base, top, side };
}
