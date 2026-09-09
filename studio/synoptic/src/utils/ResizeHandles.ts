// fix/handles-insert-mode-diodes commit 1: shared resize math for every
// element with corner/edge Transformer handles (symbols, frames,
// meters, signal panels). Pure, Konva-free (same convention as
// GridSnap.ts/Terminals.ts/WireDrawing.ts) - takes the anchor name
// Konva's own Transformer already uses, an original rect, and the raw
// (unsnapped) width/height the drag produced; returns a NEW rect.
//
// The one requirement this file exists to guarantee EXACTLY, not just
// approximately: the corner or edge OPPOSITE the one being dragged
// never moves. Snapping width/height and x/y independently (round each
// to the nearest grid line on its own) cannot promise this - the two
// roundings can disagree by up to half a grid cell, and the "fixed"
// corner drifts. Instead, this computes the new width/height FIRST
// (grid-snapped, minimum-clamped), then derives x/y directly FROM the
// side that must stay put and the new size - the fixed point is
// mathematically incapable of moving, not just unlikely to.

export type ResizeAnchor =
  | 'top-left' | 'top-center' | 'top-right'
  | 'middle-left' | 'middle-right'
  | 'bottom-left' | 'bottom-center' | 'bottom-right';

export interface ResizableRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

// Which Transformer anchor started the CURRENT resize gesture - a
// single, module-level flag (same convention as Canvas.tsx's own
// isAltPressed/isSpacePressed) shared between the Transformer-handle
// component that has access to Konva's own getActiveAnchor() (only
// available on the Transformer instance itself) and each element's own
// target Group, in a DIFFERENT file, whose onTransformEnd needs to
// know it to call computeResizeFromAnchor correctly. Konva's own
// events don't carry the anchor name to the target node directly, so
// this is the plumbing that gets it there: the Transformer's own
// onTransformStart calls setActiveResizeAnchor, the target's
// onTransformEnd calls getActiveResizeAnchor() (and should clear it
// with setActiveResizeAnchor(null) right after reading, the same way
// Canvas.tsx's own ObjectNode does).
let activeResizeAnchor: ResizeAnchor | 'rotater' | null = null;
export function setActiveResizeAnchor(anchor: ResizeAnchor | 'rotater' | null): void {
  activeResizeAnchor = anchor;
}
export function getActiveResizeAnchor(): ResizeAnchor | 'rotater' | null {
  return activeResizeAnchor;
}

function snapTo(value: number, gridSize: number): number {
  return Math.round(value / gridSize) * gridSize;
}

/**
 * A corner anchor (the four *-left/*-right combined with top/bottom)
 * changes both width and height; a vertical-edge anchor (middle-left/
 * middle-right) changes only width; a horizontal-edge anchor (top-
 * center/bottom-center) changes only height - Konva's own built-in
 * anchor behavior already enforces this for the ON-SCREEN drag itself
 * (a middle-left drag never touches height in the first place); this
 * mirrors that same rule for the FINAL, grid-snapped commit so the two
 * never disagree.
 */
export function computeResizeFromAnchor(
  anchor: ResizeAnchor,
  original: ResizableRect,
  rawWidth: number,
  rawHeight: number,
  gridSize: number,
  minWidth: number,
  minHeight: number = minWidth,
  // Held Alt bypasses grid snapping for a resize the exact same way it
  // already does for every drag/move in this app - default true so
  // every existing call site (and every mandatory test, which never
  // holds Alt) keeps snapping.
  snapEnabled: boolean = true
): ResizableRect {
  const changesWidth = anchor.includes('left') || anchor.includes('right');
  const changesHeight = anchor.includes('top') || anchor.includes('bottom');
  const snapped = (v: number) => snapEnabled ? snapTo(v, gridSize) : v;

  const newWidth = changesWidth ? Math.max(minWidth, snapped(rawWidth)) : original.width;
  const newHeight = changesHeight ? Math.max(minHeight, snapped(rawHeight)) : original.height;

  // Dragging a LEFT-side anchor keeps the RIGHT edge fixed (and vice
  // versa); dragging a TOP anchor keeps the BOTTOM edge fixed (and
  // vice versa). A middle-left/middle-right anchor never touches y at
  // all (changesHeight is false for those), so fixedTop/fixedBottom
  // simply never apply - same reasoning the other way for top-center/
  // bottom-center and x.
  let x = original.x;
  let y = original.y;
  if (changesWidth) {
    if (anchor.includes('left')) {
      x = (original.x + original.width) - newWidth; // right edge fixed
    }
    // a right-side anchor keeps the left edge (original.x) fixed - already the default
  }
  if (changesHeight) {
    if (anchor.includes('top')) {
      y = (original.y + original.height) - newHeight; // bottom edge fixed
    }
    // a bottom-side anchor keeps the top edge (original.y) fixed - already the default
  }

  return { x, y, width: newWidth, height: newHeight };
}

/** Width-only variant for the meter/signal panel elements (1's own note: height is always computed from row count, never resized by hand) - same fixed-edge guarantee, just one dimension. */
export function computeWidthResizeFromAnchor(
  anchor: ResizeAnchor,
  original: { x: number; width: number },
  rawWidth: number,
  gridSize: number,
  minWidth: number,
  maxWidth: number,
  snapEnabled: boolean = true
): { x: number; width: number } {
  const snapped = snapEnabled ? snapTo(rawWidth, gridSize) : rawWidth;
  const newWidth = Math.min(maxWidth, Math.max(minWidth, snapped));
  const x = anchor.includes('left') ? (original.x + original.width) - newWidth : original.x;
  return { x, width: newWidth };
}
