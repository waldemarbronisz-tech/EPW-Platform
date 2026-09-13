// feat/room-lighting: the photometric calculation.
//
// This is physics, so it is tested against values worked out by hand
// from the formulae in Illuminance.ts's own header rather than against
// whatever the code happened to produce first. If a number here changes,
// either the model changed on purpose or it broke - there is no third
// option, which is the point of pinning them.

import { describe, it, expect } from 'vitest';
import {
  PHOTOMETRY, collectSources, computeIlluminanceGrid, contourAt,
  falseColour, illuminanceAt, isLuminaire, isoluxLevelsFor,
  pointInPolygon,
} from '../project/Illuminance';
import type { SynopticObject } from '../store';
import { cm, m } from '../theme/Scale';

const lamp = (
  id: string, type: string, xMetres: number, yMetres: number, on = true
): SynopticObject => ({
  id, type, category: 'BUILDING',
  // Objects are positioned by their top-left corner, so the centre a
  // luminaire radiates from is offset by half its size.
  x: m(xMetres) - cm(30) / 2,
  y: m(yMetres) - cm(30) / 2,
  rotation: 0, scaleX: 1, scaleY: 1, visible: true, locked: false, layer: 0,
  tag: '', description: '', color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
  tooltip: '', width: cm(30), height: cm(30), customProperties: {},
  editor: { preview_state: on ? 'ON' : 'OFF' },
});

describe('the photometric model', () => {
  it('knows which symbols emit light at all', () => {
    expect(isLuminaire('building.luminaire')).toBe(true);
    expect(isLuminaire('building.luminaire_halogen')).toBe(true);
    expect(isLuminaire('building.socket_outlet')).toBe(false);
    expect(isLuminaire('building.table')).toBe(false);
  });

  it('counts only luminaires that are switched ON', () => {
    expect(collectSources([lamp('a', 'building.luminaire', 1, 1, true)])).toHaveLength(1);
    expect(collectSources([lamp('b', 'building.luminaire', 1, 1, false)])).toHaveLength(0);
  });

  it('splits a linear fitting along its length instead of treating it as one point', () => {
    // A batten lights a band; taking it as a single point would
    // overstate the peak directly beneath it.
    const batten = lamp('f', 'building.luminaire_fluorescent', 2, 2);
    batten.width = cm(120);
    batten.height = cm(17);
    const sources = collectSources([batten]);
    expect(sources.length).toBeGreaterThan(1);
    // The samples spread along the LONG axis only.
    const xs = new Set(sources.map(s => Math.round(s.x * 1000)));
    const ys = new Set(sources.map(s => Math.round(s.y * 1000)));
    expect(xs.size).toBeGreaterThan(1);
    expect(ys.size).toBe(1);
    // And they share out the flux rather than each carrying all of it.
    const totalIntensity = sources.reduce((s, x) => s + x.intensity, 0);
    const single = (PHOTOMETRY['building.luminaire_fluorescent'].flux
      * (PHOTOMETRY['building.luminaire_fluorescent'].exponent + 1)) / (2 * Math.PI);
    expect(totalIntensity).toBeCloseTo(single, 4);
  });

  it('gives the hand-calculated illuminance directly under one fitting', () => {
    // E = I0 / h^2 at nadir, with I0 = PHI (n+1) / 2pi.
    // PHI = 1200 lm, n = 1.5, h = 1.85 m:
    //   I0 = 1200 * 2.5 / 2pi = 477.46 cd
    //   E  = 477.46 / 1.85^2 = 139.5 lx
    const sources = collectSources([lamp('a', 'building.luminaire', 2, 2)]);
    expect(illuminanceAt(sources, 2, 2)).toBeCloseTo(139.5, 1);
  });

  it('obeys the inverse-square law in the mounting height', () => {
    // At nadir the exponent cancels, so doubling the height must quarter
    // the illuminance whatever the distribution.
    const sources = collectSources([lamp('a', 'building.luminaire', 2, 2)]);
    const atNadir = illuminanceAt(sources, 2, 2);
    const doubled = sources.map(s => ({ ...s, height: s.height * 2 }));
    expect(illuminanceAt(doubled, 2, 2)).toBeCloseTo(atNadir / 4, 3);
  });

  it('falls off away from the fitting, and faster for a narrow beam', () => {
    const wide = collectSources([lamp('a', 'building.luminaire', 2, 2)]);
    const narrow = collectSources([lamp('b', 'building.luminaire_halogen', 2, 2)]);

    const wideRatio = illuminanceAt(wide, 3, 2) / illuminanceAt(wide, 2, 2);
    const narrowRatio = illuminanceAt(narrow, 3, 2) / illuminanceAt(narrow, 2, 2);

    expect(wideRatio).toBeLessThan(1);
    // A halogen's beam is far tighter than a diffuser's, so one metre
    // off axis costs it proportionally much more.
    expect(narrowRatio).toBeLessThan(wideRatio);
  });

  it('adds up contributions from several fittings', () => {
    const one = collectSources([lamp('a', 'building.luminaire', 2, 2)]);
    const two = collectSources([
      lamp('a', 'building.luminaire', 2, 2),
      lamp('b', 'building.luminaire', 2, 2),
    ]);
    expect(illuminanceAt(two, 2, 2)).toBeCloseTo(illuminanceAt(one, 2, 2) * 2, 3);
  });
});

describe('the grid over a room', () => {
  const room = [
    { x: 0, y: 0 }, { x: m(4), y: 0 }, { x: m(4), y: m(3) }, { x: 0, y: m(3) },
  ];

  it('excludes points outside the room from the statistics', () => {
    expect(pointInPolygon(room, m(2), m(1.5))).toBe(true);
    expect(pointInPolygon(room, m(5), m(1.5))).toBe(false);
  });

  it('produces no light at all for an unlit room, without dividing by zero', () => {
    const grid = computeIlluminanceGrid(room, []);
    expect(grid.stats.max).toBe(0);
    expect(grid.stats.average).toBe(0);
    expect(grid.stats.uniformity).toBe(0);
    expect(grid.stats.samples).toBeGreaterThan(0);
  });

  it('computes plausible figures for a lit room', () => {
    const objects = [
      lamp('a', 'building.luminaire', 1, 1),
      lamp('b', 'building.luminaire', 3, 1),
      lamp('c', 'building.luminaire', 1, 2),
      lamp('d', 'building.luminaire', 3, 2),
    ];
    const grid = computeIlluminanceGrid(room, objects);
    // Four 1200 lm fittings over 12 m2, direct component only.
    expect(grid.stats.average).toBeGreaterThan(80);
    expect(grid.stats.average).toBeLessThan(400);
    expect(grid.stats.max).toBeGreaterThan(grid.stats.average);
    expect(grid.stats.min).toBeLessThan(grid.stats.average);
    // Uniformity is a ratio, so it must land in 0..1.
    expect(grid.stats.uniformity).toBeGreaterThan(0);
    expect(grid.stats.uniformity).toBeLessThanOrEqual(1);
  });

  it('marks cells outside the room as NaN, not as darkness', () => {
    // A zero there would drag the average down and make the minimum -
    // the figure a design usually fails on - meaningless.
    const lShaped = [
      { x: 0, y: 0 }, { x: m(4), y: 0 }, { x: m(4), y: m(1) },
      { x: m(1), y: m(1) }, { x: m(1), y: m(3) }, { x: 0, y: m(3) },
    ];
    const grid = computeIlluminanceGrid(lShaped, []);
    const outside = [...grid.values].filter(Number.isNaN);
    expect(outside.length).toBeGreaterThan(0);
  });
});

describe('presentation', () => {
  it('maps the false-colour scale from dark to bright', () => {
    const low = falseColour(0);
    const high = falseColour(1);
    const sum = (c: [number, number, number]) => c[0] + c[1] + c[2];
    expect(sum(high)).toBeGreaterThan(sum(low));
    // Clamped, so a value outside 0..1 cannot produce a colour outside
    // the scale.
    expect(falseColour(-5)).toEqual(low);
    expect(falseColour(5)).toEqual(high);
  });

  it('offers isolux levels from the standard series, below the maximum', () => {
    const levels = isoluxLevelsFor(320);
    expect(levels).toContain(100);
    expect(levels).toContain(300);
    expect(levels.every(l => l < 320)).toBe(true);
    // Nothing to draw when there is no light.
    expect(isoluxLevelsFor(0)).toEqual([]);
  });

  it('traces a contour where the grid actually crosses the level', () => {
    // A hand-built 2x2 grid rising left to right: the 50 lx contour must
    // cross it exactly once, vertically.
    const grid = {
      originX: 0, originY: 0, step: 10, columns: 2, rows: 2,
      values: Float32Array.from([0, 100, 0, 100]),
      stats: { average: 50, min: 0, max: 100, uniformity: 0, diversity: 0, samples: 4 },
    };
    const segments = contourAt(grid, 50);
    expect(segments).toHaveLength(1);
    // Halfway along, since the rise is linear.
    expect(segments[0].x1).toBeCloseTo(5);
    expect(segments[0].x2).toBeCloseTo(5);
  });

  it('skips cells touching the room edge rather than drawing a contour through a wall', () => {
    const grid = {
      originX: 0, originY: 0, step: 10, columns: 2, rows: 2,
      values: Float32Array.from([0, 100, Number.NaN, 100]),
      stats: { average: 0, min: 0, max: 100, uniformity: 0, diversity: 0, samples: 3 },
    };
    expect(contourAt(grid, 50)).toEqual([]);
  });
});
