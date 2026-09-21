// The part of the plan the panel (runtime) shows for one screen, in
// canvas pixels - set from View -> "Runtime frame" as "what I see now".
// Absent, the panel fits everything drawn (walls, symbols, panels, wires)
// with a small margin, so a single 6 x 4 m room fills the screen instead
// of sitting as a stamp in the middle of a 1920 x 1080 canvas.
//
// Kept per screen (ScreenContent.viewport, mirrored into
// canvasConfig.viewport while the screen is live) and written into each
// screen document's `canvas.viewport`, where runtime's reader
// (epwsyn_loader.py) picks it up.

export interface RuntimeViewport {
  x: number;
  y: number;
  width: number;
  height: number;
}

/** A viewport read from a file: the four finite numbers with a positive size, or undefined for anything else. */
export function normalizeViewport(value: unknown): RuntimeViewport | undefined {
  if (!value || typeof value !== 'object') return undefined;
  const v = value as Record<string, unknown>;
  const nums = [v.x, v.y, v.width, v.height].map(n => (typeof n === 'number' && Number.isFinite(n) ? n : NaN));
  if (nums.some(n => Number.isNaN(n)) || nums[2] <= 0 || nums[3] <= 0) return undefined;
  return { x: nums[0], y: nums[1], width: nums[2], height: nums[3] };
}
