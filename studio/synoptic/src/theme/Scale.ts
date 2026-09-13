// feat/room-plan: the drawing's real-world scale.
//
// Until now nothing on this canvas had a physical size - a symbol was
// "64 wide" and that was the whole story, which is fine for a one-line
// schematic where nothing is to scale anyway. A floor plan is
// different: a door has to be narrower than the wall it sits in, a
// chair has to fit under a table, and a 1.2 m fluorescent batten has to
// look like eight times a 15 cm downlight. So the plan elements get one
// shared scale, declared here once, and every one of their sizes is
// derived from a real dimension in centimetres rather than picked by
// eye.
//
// THE SCALE: 1 metre = 80 px, i.e. one GRID_SIZE (16 px) cell = 20 cm.
// Chosen so that
//   - a grid cell is a round number of centimetres (20), which makes
//     grid-snapped drawing land on sensible dimensions by itself;
//   - a 1 m module is exactly 5 cells, so a 3 m gate or a 2.4 m
//     ceiling reads as a whole number of cells;
//   - ordinary furniture lands in the 30-120 px range, big enough to
//     draw recognisably without dwarfing the symbols already on this
//     canvas.
//
// This governs the BUDYNEK department only. Schematic symbols
// (electrical.*, water.*, scada.*) are not to scale and never were -
// they are diagram glyphs, not objects seen from above.

export const PIXELS_PER_METRE = 80;

/** Pixels for a dimension given in centimetres. Rounded to whole pixels - a plan symbol's size is a drawing decision, not a measurement to preserve to the micron. */
export function cm(centimetres: number): number {
  return Math.round((centimetres / 100) * PIXELS_PER_METRE);
}

/** Pixels for a dimension given in metres. */
export function m(metres: number): number {
  return Math.round(metres * PIXELS_PER_METRE);
}

/** The inverse - what a pixel distance means on the ground, in centimetres. For anything that wants to SHOW a dimension to the user. */
export function pxToCm(pixels: number): number {
  return (pixels / PIXELS_PER_METRE) * 100;
}

/** A human label for a pixel distance: "90 cm" below a metre, "1.20 m" at or above it. */
export function formatLength(pixels: number): string {
  const centimetres = pxToCm(pixels);
  if (centimetres < 100) return `${Math.round(centimetres)} cm`;
  return `${(centimetres / 100).toFixed(2)} m`;
}
