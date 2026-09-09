// feat/appearance-selection-frames commit 3: the frame element - drawn
// by dragging a rectangle, like graphics.rectangle already is, but for
// illustrating a cabinet/room/zone rather than being a symbol. Pure
// data model + the one piece of pure math (minimum-size clamping) -
// Konva rendering lives in FrameElementNode.tsx, same split as the
// meter/signal panel elements.
//
// A frame is NOT a symbol: no terminals, no wire connection, no state,
// no aparat link - it is not in SymbolRegistry.ts and never will be
// (see this file's own header note on GRANICE). It IS a project-level
// element like the meter/signal panel, its own array in the store, and
// it participates in every selection/copy/move mechanism those two
// already do.

import { GRID_SIZE } from '../theme/ScadaTheme';

export type FrameTitlePosition = 'TOP_LEFT' | 'TOP_CENTER';
export type FrameVariant = 'PLAIN' | 'BUILDING';

export interface FrameElement {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  title?: string;
  titlePosition: FrameTitlePosition;
  variant: FrameVariant;
}

// 3g: a frame smaller than 2 grid cells in either direction is not a
// valid frame at all - drawing one smaller creates a MINIMUM-size
// frame instead of a zero (or near-zero) one.
export const FRAME_MIN_SIZE = GRID_SIZE * 2;

/** Clamps a single dimension (width or height) up to FRAME_MIN_SIZE - never down, never to zero, regardless of how small a drag gesture was. */
export function clampFrameSize(size: number): number {
  if (!Number.isFinite(size)) return FRAME_MIN_SIZE;
  return Math.max(FRAME_MIN_SIZE, size);
}

/**
 * Turns two arbitrary drag corners into a normalized, minimum-clamped
 * frame rect - handles a drag in any of the four directions (the
 * second point can be above/left of the first) the same way a
 * graphics program's own rectangle tool does. Both x and y snap
 * outward to whichever corner is smaller, exactly like Math.min/max on
 * two arbitrary corners always does - no separate grid-snap step here,
 * the caller (Canvas.tsx) already snaps each corner to the grid before
 * this runs, same convention as every other drawn shape.
 */
export function computeFrameRectFromDrag(x1: number, y1: number, x2: number, y2: number): { x: number; y: number; width: number; height: number } {
  const x = Math.min(x1, x2);
  const y = Math.min(y1, y2);
  const width = clampFrameSize(Math.abs(x2 - x1));
  const height = clampFrameSize(Math.abs(y2 - y1));
  return { x, y, width, height };
}
