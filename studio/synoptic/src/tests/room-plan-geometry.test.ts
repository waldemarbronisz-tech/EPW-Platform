// feat/room-plan follow-up: merged wall bodies, open-end markers, and
// the real-world scale the plan symbols are drawn to.
//
// Split from room-plan.test.ts because it checks a different thing: that
// file covers the wall MODEL and the circuit logic, this one covers the
// GEOMETRY that turns separate walls into one mitred body. All pure
// functions with exact expected values - the reason WallGeometry.ts has
// no Konva in it at all.

import { describe, it, expect } from 'vitest';
import type { WallElement } from '../elements/WallElement';
import { WALL_DEFAULT_THICKNESS } from '../elements/WallElement';
import {
  bandFromChain, bandsFromWalls, chainsFromWalls, extrudeBand,
  offsetPolyline, openEndPoints, signedArea, unmergedWalls,
} from '../project/WallGeometry';
import { isCircuitOperable } from '../project/CircuitResolver';
import { SYMBOL_REGISTRY } from '../symbols/SymbolRegistry';
import { cm, m, pxToCm, formatLength } from '../theme/Scale';
import { GRID_SIZE } from '../theme/ScadaTheme';

import symbolRendererSource from '../symbols/SymbolRenderer.tsx?raw';

const wall = (from: [number, number], to: [number, number], extra: Partial<WallElement> = {}): WallElement => ({
  id: `${from.join(',')}->${to.join(',')}`,
  from: { x: from[0], y: from[1] },
  to: { x: to[0], y: to[1] },
  thickness: WALL_DEFAULT_THICKNESS,
  ...extra,
});

const SQUARE = [
  wall([0, 0], [100, 0]), wall([100, 0], [100, 100]),
  wall([100, 100], [0, 100]), wall([0, 100], [0, 0]),
];

describe('wall chains (chainsFromWalls)', () => {
  it('groups a room into ONE closed chain, not four separate segments', () => {
    const chains = chainsFromWalls(SQUARE);
    expect(chains).toHaveLength(1);
    expect(chains[0].closed).toBe(true);
    expect(chains[0].wallIds).toHaveLength(4);
  });

  it('groups an unfinished room into one OPEN chain', () => {
    const chains = chainsFromWalls(SQUARE.slice(0, 3));
    expect(chains).toHaveLength(1);
    expect(chains[0].closed).toBe(false);
    expect(chains[0].points).toHaveLength(4); // three walls, four corners
  });

  it('flags a chain whose walls disagree, so it is never painted as one body', () => {
    const mixed = [
      wall([0, 0], [100, 0], { thickness: 8 }),
      wall([100, 0], [100, 100], { thickness: 16 }),
      wall([100, 100], [0, 100], { thickness: 8 }),
      wall([0, 100], [0, 0], { thickness: 8 }),
    ];
    expect(chainsFromWalls(mixed)[0].mixed).toBe(true);
    // ...and it is SPLIT into one body per wall, never dropped: an
    // earlier version returned nothing here, which made every wall of a
    // room vanish the moment one of them was given a different
    // material.
    expect(bandsFromWalls(mixed)).toHaveLength(4);
    expect(bandsFromWalls(mixed).every(b => b.wallIds.length === 1)).toBe(true);
    expect(unmergedWalls(mixed)).toHaveLength(4);
  });

  it('does not merge across a junction - three walls meeting have no single continuation', () => {
    const tee = [
      wall([0, 0], [100, 0]), wall([100, 0], [200, 0]), wall([100, 0], [100, 100]),
    ];
    expect(chainsFromWalls(tee).every(c => c.wallIds.length === 1)).toBe(true);
  });
});

describe('mitred offsetting (offsetPolyline)', () => {
  it('offsets a straight run sideways by exactly the distance', () => {
    expect(offsetPolyline([{ x: 0, y: 0 }, { x: 100, y: 0 }], 5, false))
      .toEqual([{ x: 0, y: 5 }, { x: 100, y: 5 }]);
  });

  it('meets both faces at ONE mitred point on a right-angle corner', () => {
    // This is the corner that used to show a notch: two thick
    // rectangles overlapping. Mitred, the two offset faces intersect at
    // a single point instead of each stopping at its own end cap.
    const result = offsetPolyline(
      [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }], 10, false
    );
    expect(result[1].x).toBeCloseTo(90);
    expect(result[1].y).toBeCloseTo(10);
  });

  it('produces the same wall whichever way round the room was drawn', () => {
    const ring = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }];
    const chain = { wallIds: [], thickness: 10, height: 40, material: undefined, mixed: false, closed: true };
    const oneWay = bandFromChain({ ...chain, points: ring });
    const otherWay = bandFromChain({ ...chain, points: [...ring].reverse() });
    expect(Math.abs(signedArea(oneWay.outer))).toBeCloseTo(Math.abs(signedArea(otherWay.outer)));
    // The outer ring must actually be the OUTER one - a room drawn the
    // other way round must not come out inside out.
    expect(Math.abs(signedArea(oneWay.outer))).toBeGreaterThan(Math.abs(signedArea(oneWay.inner!)));
    expect(Math.abs(signedArea(otherWay.outer))).toBeGreaterThan(Math.abs(signedArea(otherWay.inner!)));
  });
});

describe('extrusion (extrudeBand)', () => {
  const band = bandFromChain({
    points: [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }],
    closed: true, wallIds: [], thickness: 10, height: 40, material: undefined, mixed: false,
  });

  it('emits only viewer-facing faces, never the hidden far sides', () => {
    // A closed room shows exactly two: the near wall's outer face and
    // the far wall's inner face. Drawing all eight edges would paint
    // faces that belong behind the wall over the top of it.
    expect(extrudeBand(band)).toHaveLength(2);
  });

  it('emits nothing at all for a flat wall, so height 0 stays a plain plan', () => {
    expect(extrudeBand({ ...band, height: 0 })).toEqual([]);
  });
});

describe('open-end markers', () => {
  it('marks both ends of a single wall', () => {
    expect(openEndPoints([wall([0, 0], [100, 0])])).toHaveLength(2);
  });

  it('marks only the two loose ends of an unfinished room', () => {
    expect(openEndPoints(SQUARE.slice(0, 3))).toHaveLength(2);
  });

  it('marks nothing once the room is closed - which is the whole signal', () => {
    expect(openEndPoints(SQUARE)).toEqual([]);
  });
});

describe('real-world scale (theme/Scale)', () => {
  it('1 m is 80 px, and one grid cell is 20 cm', () => {
    expect(m(1)).toBe(80);
    expect(cm(20)).toBe(GRID_SIZE);
  });

  it('round-trips a length back to centimetres', () => {
    expect(pxToCm(cm(90))).toBeCloseTo(90);
  });

  it('labels below and above a metre the way a drawing does', () => {
    expect(formatLength(cm(90))).toBe('90 cm');
    expect(formatLength(cm(120))).toBe('1.20 m');
  });
});

describe('plan symbols and their two kinds of size', () => {
  // registry/building.ts draws THINGS THAT OCCUPY SPACE at true size and
  // ELECTRICAL ACCESSORIES as oversized symbols - ordinary drafting
  // practice, and stated in that file's own header. Both halves are
  // pinned here, because either one drifting is a real defect: a door
  // that is not 90 cm makes the plan lie, and a socket drawn at its true
  // 3 cm of switch plate makes it unusable.

  it('things that occupy space carry their actual dimensions', () => {
    expect(SYMBOL_REGISTRY['building.door'].defaultWidth).toBe(cm(90));
    expect(SYMBOL_REGISTRY['building.window'].defaultWidth).toBe(cm(120));
    expect(SYMBOL_REGISTRY['building.gate'].defaultWidth).toBe(m(3));
    expect(SYMBOL_REGISTRY['building.chair'].defaultWidth).toBe(cm(45));
    expect(SYMBOL_REGISTRY['building.table'].defaultWidth).toBe(cm(140));
  });

  it('a door is narrower than a window, and a gate wider than both', () => {
    const width = (type: string) => SYMBOL_REGISTRY[type].defaultWidth;
    expect(width('building.door')).toBeLessThan(width('building.window'));
    expect(width('building.window')).toBeLessThan(width('building.gate'));
  });

  it('a chair fits under a table', () => {
    expect(SYMBOL_REGISTRY['building.chair'].defaultWidth)
      .toBeLessThan(SYMBOL_REGISTRY['building.table'].defaultWidth);
  });

  it('the fluorescent batten keeps its TRUE length - it is a layout constraint', () => {
    // The one accessory dimension that stays true: a row of battens is
    // spaced by their length, and Illuminance.ts samples along it.
    expect(SYMBOL_REGISTRY['building.luminaire_fluorescent'].defaultWidth).toBe(cm(120));
  });

  it('accessories are drawn OVER true size, so they read beside furniture', () => {
    // At true size a 30 cm ceiling fitting came out as a speck next to a
    // 140 cm table. Each of these is drawn deliberately larger than the
    // thing it represents.
    expect(SYMBOL_REGISTRY['building.luminaire'].defaultWidth).toBeGreaterThan(cm(30));
    expect(SYMBOL_REGISTRY['building.luminaire_halogen'].defaultWidth).toBeGreaterThan(cm(17));
    expect(SYMBOL_REGISTRY['building.socket_outlet'].defaultWidth).toBeGreaterThan(cm(20));
    // ...but still smaller than the furniture they sit among, or the
    // symbol would stop being a symbol and start being an obstruction.
    expect(SYMBOL_REGISTRY['building.luminaire'].defaultWidth)
      .toBeLessThan(SYMBOL_REGISTRY['building.chair'].defaultWidth);
  });

  it('a batten still reads as far longer than a downlight', () => {
    expect(SYMBOL_REGISTRY['building.luminaire_fluorescent'].defaultWidth)
      .toBeGreaterThan(SYMBOL_REGISTRY['building.luminaire_halogen'].defaultWidth * 3);
  });
});

describe('the BUDYNEK department as a whole', () => {
  it('every luminaire and the socket are circuit-operable; furniture never is', () => {
    for (const type of [
      'building.luminaire', 'building.luminaire_pendant', 'building.luminaire_wall',
      'building.luminaire_fluorescent', 'building.luminaire_halogen', 'building.socket_outlet',
    ]) {
      expect(isCircuitOperable(type), type).toBe(true);
    }
    // Furniture and the PASSIVE openings never are. The gate is the
    // exception and deliberately not in this list: it has a drive, so
    // it is a controlled device that goes on a circuit like a lamp.
    for (const type of [
      'building.table', 'building.chair', 'building.shelf',
      'building.door', 'building.window',
    ]) {
      expect(isCircuitOperable(type), type).toBe(false);
    }
    expect(isCircuitOperable('building.gate')).toBe(true);
  });

  it('every BUDYNEK symbol has its own renderer case - none falls through to the generic box', () => {
    const types = Object.keys(SYMBOL_REGISTRY).filter(t => t.startsWith('building.'));
    expect(types.length).toBeGreaterThan(10);
    for (const type of types) {
      expect(symbolRendererSource, type).toContain(`case '${type}':`);
    }
  });

  it('declares no terminals anywhere - fixtures are driven by circuits, not wires', () => {
    for (const type of Object.keys(SYMBOL_REGISTRY).filter(t => t.startsWith('building.'))) {
      expect(SYMBOL_REGISTRY[type].terminals ?? [], type).toEqual([]);
    }
  });
});
