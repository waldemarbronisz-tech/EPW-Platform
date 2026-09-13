// feat/cad-marquee: resizing a whole selection - above all, a whole
// room.
//
// Selecting four walls and dragging a corner has to do what a plan
// drawing expects, which is NOT what a graphics program would do. A
// graphics program scales everything: the room grows and so does every
// chair in it. A plan is dimensioned, and everything on it is a real
// object at a real size (theme/Scale.ts: 1 m = 80 px) - a 45 cm chair is
// 45 cm whatever the room around it measures.
//
// So the rule here is: GEOMETRY SCALES, OBJECTS MOVE.
//
//   - A wall's endpoints scale, so the room takes the new shape and
//     stays a closed chain. Its THICKNESS does not: a 12 cm partition
//     does not become 18 cm because the room got wider.
//   - A fixture, a chair, a door keeps its own size and is carried to
//     the same relative place in the room. Six luminaires spread evenly
//     across a hall stay spread evenly across the bigger hall.
//
// The one exception is deliberate: an opening (door, gate, window) is
// re-seated into its wall by the caller afterwards, because a door's
// position along a wall is only meaningful relative to that wall.
//
// Pure: plain data in, plain updates out. No store, no Konva.

import type { WallElement } from '../elements/WallElement';
import type { SynopticObject } from '../store/types';

export interface ScaleBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

/** A box narrower or shorter than this cannot be dragged to. Below roughly one grid cell a room stops being a room and the scaling factors blow up. */
export const MIN_SCALE_EXTENT = 16;

/** Which handle is being dragged. The corners scale both axes; the edges scale one and leave the other exactly as it was. */
export type ResizeAnchor = 'nw' | 'n' | 'ne' | 'e' | 'se' | 's' | 'sw' | 'w';

export const RESIZE_ANCHORS: ResizeAnchor[] = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'];

/** Where a handle sits on a box, in world coordinates. */
export function anchorPoint(box: ScaleBox, anchor: ResizeAnchor): { x: number; y: number } {
  const left = box.x;
  const middle = box.x + box.width / 2;
  const right = box.x + box.width;
  const top = box.y;
  const centre = box.y + box.height / 2;
  const bottom = box.y + box.height;
  switch (anchor) {
    case 'nw': return { x: left, y: top };
    case 'n': return { x: middle, y: top };
    case 'ne': return { x: right, y: top };
    case 'e': return { x: right, y: centre };
    case 'se': return { x: right, y: bottom };
    case 's': return { x: middle, y: bottom };
    case 'sw': return { x: left, y: bottom };
    case 'w': return { x: left, y: centre };
  }
}

/** The cursor a handle should show. Wrong cursors on resize handles make a control feel broken even when it works. */
export function anchorCursor(anchor: ResizeAnchor): string {
  switch (anchor) {
    case 'nw': case 'se': return 'nwse-resize';
    case 'ne': case 'sw': return 'nesw-resize';
    case 'n': case 's': return 'ns-resize';
    case 'e': case 'w': return 'ew-resize';
  }
}

/**
 * The box that results from dragging one handle of `box` to `point`.
 *
 * The opposite edge stays put - that is what makes a resize feel like a
 * resize rather than a move. Dragging a handle past its opposite edge
 * clamps instead of flipping the box inside out: a mirrored room is
 * never what the drag meant, and it would silently reverse every wall.
 */
export function resizeBox(box: ScaleBox, anchor: ResizeAnchor, point: { x: number; y: number }): ScaleBox {
  let left = box.x;
  let top = box.y;
  let right = box.x + box.width;
  let bottom = box.y + box.height;

  if (anchor.includes('w')) left = Math.min(point.x, right - MIN_SCALE_EXTENT);
  if (anchor.includes('e')) right = Math.max(point.x, left + MIN_SCALE_EXTENT);
  if (anchor.includes('n')) top = Math.min(point.y, bottom - MIN_SCALE_EXTENT);
  if (anchor.includes('s')) bottom = Math.max(point.y, top + MIN_SCALE_EXTENT);

  return { x: left, y: top, width: right - left, height: bottom - top };
}

/** Maps a point from `before` into the same relative place in `after`. A degenerate source axis maps to the new origin rather than to NaN. */
export function mapPoint(
  point: { x: number; y: number },
  before: ScaleBox,
  after: ScaleBox
): { x: number; y: number } {
  const fx = before.width > 0 ? (point.x - before.x) / before.width : 0;
  const fy = before.height > 0 ? (point.y - before.y) / before.height : 0;
  return {
    x: after.x + fx * after.width,
    y: after.y + fy * after.height,
  };
}

/** The wall updates that take a selection from `before` to `after`. Thickness, height and material are untouched - only the run of the wall changes. */
export function scaleWalls(
  walls: WallElement[],
  ids: string[],
  before: ScaleBox,
  after: ScaleBox,
  snap: (value: number) => number = v => v
): { id: string; updates: Partial<WallElement> }[] {
  const selected = new Set(ids);
  return walls.filter(w => selected.has(w.id)).map(wall => {
    const from = mapPoint(wall.from, before, after);
    const to = mapPoint(wall.to, before, after);
    return {
      id: wall.id,
      updates: {
        from: { x: snap(from.x), y: snap(from.y) },
        to: { x: snap(to.x), y: snap(to.y) },
      },
    };
  });
}

/**
 * The object updates that carry a selection from `before` to `after`.
 *
 * Position only. An object's own width and height are a real-world size
 * and are never touched here - see this file's header for why a chair
 * does not grow with the room it stands in.
 */
export function scaleObjectPositions(
  objects: SynopticObject[],
  ids: string[],
  before: ScaleBox,
  after: ScaleBox,
  snap: (value: number) => number = v => v
): { id: string; updates: Partial<SynopticObject> }[] {
  const selected = new Set(ids);
  return objects.filter(o => selected.has(o.id)).map(obj => {
    // The CENTRE is what is carried, not the top-left: an object moved
    // by its corner drifts towards the origin as it is scaled, which
    // shows up as fixtures creeping away from the middle of a room.
    const width = obj.width * (obj.scaleX || 1);
    const height = obj.height * (obj.scaleY || 1);
    const centre = mapPoint({ x: obj.x + width / 2, y: obj.y + height / 2 }, before, after);
    return {
      id: obj.id,
      updates: {
        x: snap(centre.x - width / 2),
        y: snap(centre.y - height / 2),
      },
    };
  });
}

/** The bounding box of a set of walls, or null when there are none. */
export function wallsBounds(walls: WallElement[], ids: string[]): ScaleBox | null {
  const selected = new Set(ids);
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const wall of walls) {
    if (!selected.has(wall.id)) continue;
    minX = Math.min(minX, wall.from.x, wall.to.x);
    minY = Math.min(minY, wall.from.y, wall.to.y);
    maxX = Math.max(maxX, wall.from.x, wall.to.x);
    maxY = Math.max(maxY, wall.from.y, wall.to.y);
  }
  if (!Number.isFinite(minX)) return null;
  return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
}
