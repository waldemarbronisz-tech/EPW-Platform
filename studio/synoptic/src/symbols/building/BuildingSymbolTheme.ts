// feat/room-plan: the shared look of the BUDYNEK plan symbols.
//
// One place for the handful of values every plan symbol repeats, so a
// room drawn from a dozen different symbols still reads as one drawing.
// Deliberately small: colours that mean something (lit / energized /
// inert material) and the stroke rule, nothing else. Anything a single
// symbol needs on its own stays in that symbol's own file.

import { COLOR_ENERGIZED, COLOR_LAMP_LIT, COLOR_OUTLINE } from '../../theme/ScadaTheme';

export { COLOR_OUTLINE };

/** Lit lamp glass / a live socket body. */
export const LIT = COLOR_LAMP_LIT;
export const LIVE = COLOR_ENERGIZED;

/** An unlit fitting: the body is still a real object, so it stays a light grey rather than disappearing. */
export const FITTING_BODY = '#E4E4E4';
export const FITTING_BODY_DARK = '#BFBFBF';

/** Furniture, seen from above. Warm neutral so it separates from the grey of walls and technical floors without shouting. */
export const FURNITURE_TOP = '#C8A97E';
export const FURNITURE_SIDE = '#A98A62';
export const FURNITURE_DARK = '#7C6446';

/** Metal - gate leaves, shelf uprights. */
export const METAL = '#9AA3AA';
export const METAL_DARK = '#6E767C';

/** Glass - window panes, gate infill. */
export const GLASS = '#BFE3EA';

/**
 * Outline width proportional to the symbol, never a fixed pixel count.
 * The platform's own SYMBOL_STROKE (5) is sized for the large schematic
 * glyphs; on a 14 px downlight it would swallow the symbol whole - a
 * mistake already made once here, where a lit luminaire came out as a
 * black blob (see LuminaireSymbol's own note).
 */
export function symbolStroke(width: number, height: number): number {
  return Math.max(1, Math.min(width, height) * 0.075);
}

/**
 * The shadow a floor-standing object casts.
 *
 * Offset down and to the right, away from the same upper-left light the
 * walls are shaded by (WallLayer's LIGHT_X) - one light for the whole
 * drawing, or the scene stops reading as one place. Spread onto the
 * object's own outermost shape, so the shadow takes that shape rather
 * than a bounding box: a round table casts a round shadow.
 *
 * Ceiling fittings deliberately do NOT get one. A luminaire is above
 * the floor, not on it, and giving it a contact shadow would make it
 * read as an object lying on the ground.
 */
export const PLAN_SHADOW = {
  shadowColor: '#000000',
  shadowBlur: 6,
  shadowOffsetX: 3,
  shadowOffsetY: 4,
  shadowOpacity: 0.32,
} as const;
