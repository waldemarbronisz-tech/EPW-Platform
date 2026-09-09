// feat/site-objects-2d commit 4: pure geometry helpers for the two
// SURFACE objects (14. Trawa/Grass, 15. Droga betonowa/Concrete road).
//
// Unlike every other TEREN object, a surface is explicitly ADJUSTABLE
// size (WYMAGANIA WSPOLNE) and is NOT drawn at docs/EPW_rysunki_
// referencja.py's own fixed 160x120 coordinates and then uniformly
// scaled (SITE_CANVAS_SCALE, commit 2) - that trick exists to fit one
// FIXED small drawing into a grid-aligned registered size; a surface
// has no fixed drawing to fit; it must redraw its own texture for
// whatever real size the object currently is, so a bigger rectangle
// shows MORE texture (spread evenly), not the same handful of marks
// stretched thin or squashed (mandatory test 8; PRZED ZGLOSZENIEM
// point 5, "texture spreads evenly").
//
// Every function below is a PURE function of width/height alone - same
// width/height in, byte-identical array out, every time (mandatory
// test 8) - GrassSymbol.tsx/ConcreteRoadSymbol.tsx only ever read these
// results and draw them; no Math.random() and no per-render mutable
// state anywhere in this file.

// Deterministic seeded PRNG (mulberry32) - not Math.random(). docs/
// EPW_rysunki_referencja.py's own trawa(on) seeds Python's random with
// a fixed constant (`random.seed(3)`) for exactly this reason - a
// repeatable layout, not a fresh shuffle every render. Same idea here:
// always start from the same fixed seed, so the ONLY thing that can
// ever change the resulting sequence is how many dashes are drawn,
// which itself depends only on width/height. No new dependency
// (GRANICE) - a self-contained ~5-line generator.
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// docs/EPW_rysunki_referencja.py's own trawa(on): `random.seed(3)`.
const GRASS_SEED = 3;
// That same function draws 46 dashes over its own 144x80 inner rect
// (the 8,20,144,80 banded rect, minus a roughly 6-8px margin the loop's
// own x/y ranges (14..154, 28..92) imply) - reused here as a per-area
// DENSITY constant instead of a fixed count, so a surface twice the
// area gets roughly twice the dashes, not the same 46 spread thinner.
const GRASS_DASH_DENSITY = 46 / (144 * 80);
// Keeps dashes off the banded outline itself, same margin order of
// magnitude as the reference's own 14/28 inset from its 8/20 rect origin.
export const GRASS_MARGIN = 8;

export interface GrassDash {
  x: number;
  y: number;
}

/**
 * Every small grass-blade dash mark for a WIDTHxHEIGHT grass surface -
 * deterministic (same width/height always gives the same array, in the
 * same order), and denser for a larger surface (GRASS_DASH_DENSITY)
 * rather than a fixed count stretched or squeezed to fit.
 */
export function computeGrassDashes(width: number, height: number): GrassDash[] {
  const innerWidth = Math.max(1, width - GRASS_MARGIN * 2);
  const innerHeight = Math.max(1, height - GRASS_MARGIN * 2);
  const count = Math.max(0, Math.round(innerWidth * innerHeight * GRASS_DASH_DENSITY));
  const rand = mulberry32(GRASS_SEED);
  const dashes: GrassDash[] = [];
  for (let i = 0; i < count; i++) {
    dashes.push({
      x: GRASS_MARGIN + rand() * innerWidth,
      y: GRASS_MARGIN + rand() * innerHeight
    });
  }
  return dashes;
}

// droga(on) has no randomness at all - every joint/dash position below
// is plain arithmetic, kept here only so it shares this file's own
// "pure function of width/height" shape and its own dedicated test.

// docs/EPW_rysunki_referencja.py's own droga(on): joints at x=56,104
// inside its own 8..152 (144-wide) banded rect - three equal 48-wide
// slabs. Reused as a target SLAB width so a wider road gets more
// slabs at roughly the same width, not 2 fixed joints stretched apart.
const ROAD_SLAB_WIDTH = 48;
export const ROAD_MARGIN_Y = 8;
// Reference's own dashed center line: `for i in range(0,7): line(20+i*20,58,32+i*20,58, ...)` - a 20-unit period, 12-unit dash.
const ROAD_DASH_PERIOD = 20;
const ROAD_DASH_LENGTH = 12;

/** X positions of every vertical expansion-joint line for a road WIDTH units wide (excludes the two outer edges - those are the banded rect's own outline). */
export function computeRoadJoints(width: number): number[] {
  const slabCount = Math.max(1, Math.round(width / ROAD_SLAB_WIDTH));
  const slabWidth = width / slabCount;
  const joints: number[] = [];
  for (let i = 1; i < slabCount; i++) joints.push(i * slabWidth);
  return joints;
}

export interface RoadDash {
  x1: number;
  x2: number;
}

/** Start/end x of every dash in the road's own dashed center line, for a road WIDTH units wide. */
export function computeRoadDashes(width: number): RoadDash[] {
  const count = Math.max(0, Math.floor(width / ROAD_DASH_PERIOD));
  const dashes: RoadDash[] = [];
  for (let i = 0; i < count; i++) {
    const x1 = i * ROAD_DASH_PERIOD + (ROAD_DASH_PERIOD - ROAD_DASH_LENGTH) / 2;
    dashes.push({ x1, x2: x1 + ROAD_DASH_LENGTH });
  }
  return dashes;
}
