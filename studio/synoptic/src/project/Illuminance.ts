// feat/room-lighting: illuminance on the working plane - the DIALux
// half of this editor.
//
// WHAT THIS IS. Given the luminaires actually placed in a room, this
// computes the illuminance E [lx] on the working plane, on a grid, and
// the four numbers a lighting design is judged by: average, minimum,
// maximum and uniformity. It is a real photometric calculation, not a
// glow effect - the pools of light drawn on the floor elsewhere in this
// editor are decoration, and this is not.
//
// THE MODEL, stated plainly so its limits are visible.
//
// Each luminaire is a point (or, for a linear fitting, a row of points)
// with a rotationally symmetric cosine-power intensity distribution:
//
//     I(theta) = I0 * cos^n(theta)
//
// Integrating that over the lower hemisphere gives the flux, so
//
//     I0 = PHI * (n + 1) / (2 * PI)
//
// and the illuminance at a point on the working plane, at horizontal
// distance r from a fitting mounted h above that plane, follows from
// the inverse-square and cosine laws:
//
//     d = sqrt(h^2 + r^2),  cos(theta) = h / d
//     E = I(theta) * cos(theta) / d^2 = I0 * h^(n+1) / d^(n+3)
//
// `n` is what separates a downlight from a diffuser: n = 1 is nearly
// Lambertian (a wide, soft distribution), n = 8 is a narrow spot.
//
// WHAT IT DELIBERATELY DOES NOT MODEL, because pretending otherwise
// would be worse than the gap:
//   - INTERREFLECTION. This is the DIRECT component only. A real room
//     gains a substantial indirect component from its walls, ceiling
//     and floor, which a full calculation (or a utilisation-factor
//     method) accounts for. Everything here therefore reads LOW for a
//     light room, and the numbers are honest about being direct-only.
//   - Real photometric files. A manufacturer's LDT/IES distribution is
//     measured; a cosine power is an idealisation of it.
//   - Shadows from furniture, and any wall obstruction.
//
// That is enough to answer the question this plan is actually for - is
// this room lit roughly right, and where are the dark spots - without
// claiming to be a certification-grade result.
//
// Pure functions only, no store and no Konva.

import type { SynopticObject } from '../store';
import type { WallPoint } from '../elements/WallElement';
import { PIXELS_PER_METRE } from '../theme/Scale';
import type { WallElement } from '../elements/WallElement';
import { findClosedRooms } from './RoomFloors';

/** Metres per canvas pixel - every distance in this module is in METRES, because photometry is. */
const METRES_PER_PIXEL = 1 / PIXELS_PER_METRE;

export interface Photometry {
  /** Luminous flux of the fitting, in lumens - what leaves the luminaire, not the bare lamp. */
  flux: number;
  /** Cosine-power exponent: 1 is a wide diffuser, 8 a narrow spot. */
  exponent: number;
  /** Mounting height ABOVE THE WORKING PLANE, in metres - not above the floor. */
  mountingHeight: number;
  /** A linear fitting is sampled along its own length instead of as one point; false for a compact one. */
  linear?: boolean;
}

/**
 * Per fitting type. Values are ordinary catalogue figures for the kind
 * of fitting each symbol represents, chosen to be defensible rather
 * than flattering - a 2x36 W batten is taken at its real luminaire
 * output, not at bare lamp lumens.
 *
 * Heights assume a 2.70 m ceiling over a 0.85 m working plane, the
 * usual office/workshop convention, so a ceiling fitting is 1.85 m
 * above the plane it is lighting.
 */
export const PHOTOMETRY: Record<string, Photometry> = {
  'building.luminaire': { flux: 1200, exponent: 1.5, mountingHeight: 1.85 },
  'building.luminaire_pendant': { flux: 900, exponent: 1.0, mountingHeight: 1.25 },
  // A sconce throws most of its output at the wall behind it; only part
  // of it reaches the working plane, which is why its useful flux is
  // entered low rather than its nominal one.
  'building.luminaire_wall': { flux: 350, exponent: 2.0, mountingHeight: 1.15 },
  'building.luminaire_fluorescent': { flux: 4800, exponent: 1.2, mountingHeight: 1.85, linear: true },
  'building.luminaire_halogen': { flux: 350, exponent: 8.0, mountingHeight: 1.85 },
};

export function isLuminaire(type: string): boolean {
  return Object.prototype.hasOwnProperty.call(PHOTOMETRY, type);
}

/** A point source, resolved from a placed object - already in metres, already split up if the fitting is linear. */
interface PointSource {
  x: number;
  y: number;
  intensity: number; // I0, in candela
  exponent: number;
  height: number;
}

/** How many points a linear fitting is split into. Enough that a 1.2 m batten reads as a line rather than a blob, few enough to keep a whole room's grid cheap. */
const LINEAR_SAMPLES = 7;

/**
 * Every lit luminaire on the screen, as point sources in metres.
 *
 * Only fittings that are actually ON contribute - the calculation
 * answers "what does this room look like with these circuits switched
 * on", which is the question worth asking on a plan where circuits can
 * be switched.
 */
export function collectSources(objects: SynopticObject[]): PointSource[] {
  const sources: PointSource[] = [];

  for (const obj of objects) {
    const photometry = PHOTOMETRY[obj.type];
    if (!photometry) continue;
    if (obj.editor?.preview_state !== 'ON') continue;

    const centreX = (obj.x + obj.width / 2) * METRES_PER_PIXEL;
    const centreY = (obj.y + obj.height / 2) * METRES_PER_PIXEL;

    if (!photometry.linear) {
      sources.push({
        x: centreX,
        y: centreY,
        intensity: (photometry.flux * (photometry.exponent + 1)) / (2 * Math.PI),
        exponent: photometry.exponent,
        height: photometry.mountingHeight,
      });
      continue;
    }

    // A linear fitting: split its flux along its own longer axis, so a
    // 1.2 m batten lights a band rather than a spot. Treating it as one
    // point would overstate the peak directly under it by roughly the
    // ratio of its length to the mounting height.
    const horizontal = obj.width >= obj.height;
    const lengthPx = horizontal ? obj.width : obj.height;
    const lengthM = lengthPx * METRES_PER_PIXEL;
    const perSampleFlux = photometry.flux / LINEAR_SAMPLES;
    for (let i = 0; i < LINEAR_SAMPLES; i++) {
      const t = (i + 0.5) / LINEAR_SAMPLES - 0.5; // -0.5 .. +0.5
      sources.push({
        x: centreX + (horizontal ? t * lengthM : 0),
        y: centreY + (horizontal ? 0 : t * lengthM),
        intensity: (perSampleFlux * (photometry.exponent + 1)) / (2 * Math.PI),
        exponent: photometry.exponent,
        height: photometry.mountingHeight,
      });
    }
  }

  return sources;
}

/** Illuminance at one point on the working plane, in lux. Coordinates in METRES. */
export function illuminanceAt(sources: PointSource[], x: number, y: number): number {
  let total = 0;
  for (const source of sources) {
    const dx = x - source.x;
    const dy = y - source.y;
    const distanceSquared = dx * dx + dy * dy + source.height * source.height;
    const distance = Math.sqrt(distanceSquared);
    // E = I0 * h^(n+1) / d^(n+3)
    total += source.intensity * Math.pow(source.height, source.exponent + 1)
      / Math.pow(distance, source.exponent + 3);
  }
  return total;
}

/** Standard even-odd point-in-polygon. Polygon in canvas pixels. */
export function pointInPolygon(polygon: WallPoint[], x: number, y: number): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const a = polygon[i];
    const b = polygon[j];
    const intersects = (a.y > y) !== (b.y > y)
      && x < ((b.x - a.x) * (y - a.y)) / (b.y - a.y) + a.x;
    if (intersects) inside = !inside;
  }
  return inside;
}

export interface IlluminanceGrid {
  /** Grid origin and pitch, in CANVAS PIXELS - what the renderer needs. */
  originX: number;
  originY: number;
  step: number;
  columns: number;
  rows: number;
  /** Illuminance in lux, row-major. NaN for a cell outside the room. */
  values: Float32Array;
  /** Statistics over the cells INSIDE the room only. */
  stats: {
    average: number;
    min: number;
    max: number;
    /** Emin / Eavg - the uniformity a lighting spec actually states (often written g1 or Uo). */
    uniformity: number;
    /** Emin / Emax - the stricter "diversity" figure. */
    diversity: number;
    /** How many grid points were inside the room; 0 means nothing could be computed. */
    samples: number;
  };
}

/** Grid pitch, in canvas pixels. One grid cell (20 cm) - fine enough to resolve a downlight's pool, coarse enough that a whole room is a few hundred points. */
export const ILLUMINANCE_STEP = 16;

/**
 * The illuminance grid over one room polygon.
 *
 * Cells outside the polygon are NaN rather than zero: a zero would drag
 * the average down and would make the minimum meaningless, and the
 * minimum is the number a lighting design usually fails on.
 */
export function computeIlluminanceGrid(
  room: WallPoint[],
  objects: SynopticObject[],
  step: number = ILLUMINANCE_STEP
): IlluminanceGrid {
  const xs = room.map(p => p.x);
  const ys = room.map(p => p.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const columns = Math.max(1, Math.ceil((maxX - minX) / step) + 1);
  const rows = Math.max(1, Math.ceil((maxY - minY) / step) + 1);
  const values = new Float32Array(columns * rows);

  const sources = collectSources(objects);

  let sum = 0;
  let min = Infinity;
  let max = 0;
  let samples = 0;

  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < columns; col++) {
      const px = minX + col * step;
      const py = minY + row * step;
      const index = row * columns + col;

      if (!pointInPolygon(room, px, py)) {
        values[index] = Number.NaN;
        continue;
      }
      const lux = illuminanceAt(sources, px * METRES_PER_PIXEL, py * METRES_PER_PIXEL);
      values[index] = lux;
      sum += lux;
      samples += 1;
      if (lux < min) min = lux;
      if (lux > max) max = lux;
    }
  }

  const average = samples > 0 ? sum / samples : 0;
  return {
    originX: minX,
    originY: minY,
    step,
    columns,
    rows,
    values,
    stats: {
      average,
      min: samples > 0 ? min : 0,
      max,
      uniformity: average > 0 ? (samples > 0 ? min : 0) / average : 0,
      diversity: max > 0 ? (samples > 0 ? min : 0) / max : 0,
      samples,
    },
  };
}

/**
 * The statistics for every closed room formed by these walls - what the
 * result panel reports.
 *
 * Lives here rather than beside the layer that draws the map: it is
 * pure, and a component file exporting a non-component breaks fast
 * refresh (and makes the calculation look like a rendering detail,
 * which is the opposite of true).
 */
export function roomIlluminanceStats(walls: WallElement[], objects: SynopticObject[]) {
  return findClosedRooms(walls).map((room, index) => ({
    index,
    stats: computeIlluminanceGrid(room, objects).stats,
  }));
}

// ---- false colour ---------------------------------------------------------

/**
 * The false-colour scale, dark blue to white through the spectrum -
 * the convention every lighting tool uses, so the picture reads the way
 * a lighting engineer expects without a legend having to teach it.
 */
const SCALE: { stop: number; rgb: [number, number, number] }[] = [
  { stop: 0.0, rgb: [16, 16, 80] },
  { stop: 0.15, rgb: [24, 70, 180] },
  { stop: 0.32, rgb: [0, 160, 190] },
  { stop: 0.48, rgb: [0, 175, 90] },
  { stop: 0.62, rgb: [160, 200, 0] },
  { stop: 0.76, rgb: [250, 210, 0] },
  { stop: 0.88, rgb: [245, 130, 0] },
  { stop: 1.0, rgb: [255, 250, 230] },
];

/** The colour for a normalised value 0..1. */
export function falseColour(t: number): [number, number, number] {
  const clamped = Math.max(0, Math.min(1, t));
  for (let i = 1; i < SCALE.length; i++) {
    if (clamped <= SCALE[i].stop) {
      const a = SCALE[i - 1];
      const b = SCALE[i];
      const span = b.stop - a.stop || 1;
      const local = (clamped - a.stop) / span;
      return [
        Math.round(a.rgb[0] + (b.rgb[0] - a.rgb[0]) * local),
        Math.round(a.rgb[1] + (b.rgb[1] - a.rgb[1]) * local),
        Math.round(a.rgb[2] + (b.rgb[2] - a.rgb[2]) * local),
      ];
    }
  }
  return SCALE[SCALE.length - 1].rgb;
}

/**
 * The isolux levels worth drawing for a given maximum, taken from the
 * standard series lighting practice actually uses (EN 12464-1's own
 * maintained-illuminance steps) rather than from evenly dividing the
 * range - 300 lx means something to an electrician and 287 lx does not.
 */
export const ISOLUX_SERIES = [10, 20, 30, 50, 75, 100, 150, 200, 300, 500, 750, 1000, 1500, 2000];

export function isoluxLevelsFor(max: number): number[] {
  return ISOLUX_SERIES.filter(level => level < max * 0.98);
}

// ---- isolux contours (marching squares) -----------------------------------

export interface ContourSegment {
  x1: number; y1: number; x2: number; y2: number;
}

/** Linear interpolation of where `level` crosses between two grid values, as a fraction 0..1. */
function crossing(a: number, b: number, level: number): number {
  if (a === b) return 0.5;
  return (level - a) / (b - a);
}

/**
 * Isolux contours for one level, by marching squares over the grid.
 *
 * A cell with any NaN corner is skipped entirely: those are the cells
 * straddling the room's edge, and interpolating a contour into a corner
 * that was never calculated would draw a line through the wall.
 */
export function contourAt(grid: IlluminanceGrid, level: number): ContourSegment[] {
  const segments: ContourSegment[] = [];
  const { columns, rows, values, step, originX, originY } = grid;

  for (let row = 0; row < rows - 1; row++) {
    for (let col = 0; col < columns - 1; col++) {
      const topLeft = values[row * columns + col];
      const topRight = values[row * columns + col + 1];
      const bottomRight = values[(row + 1) * columns + col + 1];
      const bottomLeft = values[(row + 1) * columns + col];
      if (Number.isNaN(topLeft) || Number.isNaN(topRight) || Number.isNaN(bottomRight) || Number.isNaN(bottomLeft)) continue;

      const x0 = originX + col * step;
      const y0 = originY + row * step;

      // Corner above/below the level, as the usual 4-bit case index.
      const index =
        (topLeft >= level ? 8 : 0) |
        (topRight >= level ? 4 : 0) |
        (bottomRight >= level ? 2 : 0) |
        (bottomLeft >= level ? 1 : 0);
      if (index === 0 || index === 15) continue;

      // Crossing points on each edge, when that edge is crossed.
      const top = { x: x0 + step * crossing(topLeft, topRight, level), y: y0 };
      const right = { x: x0 + step, y: y0 + step * crossing(topRight, bottomRight, level) };
      const bottom = { x: x0 + step * crossing(bottomLeft, bottomRight, level), y: y0 + step };
      const left = { x: x0, y: y0 + step * crossing(topLeft, bottomLeft, level) };

      const push = (a: { x: number; y: number }, b: { x: number; y: number }) =>
        segments.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y });

      switch (index) {
        case 1: case 14: push(left, bottom); break;
        case 2: case 13: push(bottom, right); break;
        case 3: case 12: push(left, right); break;
        case 4: case 11: push(top, right); break;
        case 6: case 9: push(top, bottom); break;
        case 7: case 8: push(left, top); break;
        // The two ambiguous saddles: both pairs drawn, which is the
        // conservative choice - a contour tool that guesses one way
        // produces a line that jumps as the data shifts slightly.
        case 5: push(left, top); push(bottom, right); break;
        case 10: push(left, bottom); push(top, right); break;
      }
    }
  }
  return segments;
}
