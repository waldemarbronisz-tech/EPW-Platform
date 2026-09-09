import { describe, it, expect } from 'vitest';
import { resolveNets, validateNets, getJunctionPoints } from '../project/NetResolver';
import type { SynopticConnection, SynopticObject } from '../store';
import { GRID_SIZE } from '../theme/ScadaTheme';

function makeWire(id: string, points: { x: number; y: number }[], overrides: Partial<SynopticConnection> = {}): SynopticConnection {
  return { id, points, medium: 'ELECTRICAL', style: 'NORMAL', state: 'LIVE', ...overrides };
}

// A minimal object with one terminal at a known local point - enough for
// NetResolver, which only reads type/x/y/rotation/scale plus whatever
// getObjectTerminals resolves for that type. electrical.circuit_breaker
// has terminals at (16,0) and (16,48) after the Part E grid-alignment
// pass (see registry).
function makeDevice(id: string, x: number, y: number, overrides: Partial<SynopticObject> = {}): SynopticObject {
  return {
    id, type: 'electrical.circuit_breaker', category: 'Electrical',
    x, y, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 1,
    tag: id, description: '', color: '#000', fill: '#000', border: '#000',
    text: '', font: 'Arial', fontSize: 12, tooltip: '',
    width: 40, height: 40, customProperties: {},
    ...overrides
  };
}

describe('NetResolver.resolveNets', () => {
  // 1. two wires with a shared endpoint -> one net
  it('two wires sharing an endpoint form one net', () => {
    const a = makeWire('A', [{ x: 0, y: 0 }, { x: 32, y: 0 }]);
    const b = makeWire('B', [{ x: 32, y: 0 }, { x: 32, y: 32 }]);
    const nets = resolveNets([a, b], []);
    expect(nets.length).toBe(1);
    expect(nets[0].connectionIds.sort()).toEqual(['A', 'B']);
  });

  // 2. two wires with no shared point -> two nets
  it('two wires with no shared point form two separate nets', () => {
    const a = makeWire('A', [{ x: 0, y: 0 }, { x: 32, y: 0 }]);
    const b = makeWire('B', [{ x: 192, y: 192 }, { x: 224, y: 192 }]);
    const nets = resolveNets([a, b], []);
    expect(nets.length).toBe(2);
  });

  // 3. THE MOST IMPORTANT TEST: a wire ending in the MIDDLE of another
  // wire's segment -> one net. This is what makes a busbar work - a tap
  // landing anywhere along its length, not just at its two ends.
  it('a wire ending on the MIDDLE of another wire segment still forms one net (the busbar case)', () => {
    const bus = makeWire('BUS', [{ x: 0, y: 0 }, { x: 320, y: 0 }], { style: 'BUS' });
    const tap = makeWire('TAP', [{ x: 160, y: 0 }, { x: 160, y: 64 }]);
    // 160,0 is nowhere near either endpoint of BUS (0,0 and 320,0) - it
    // is a plain interior point of that one long segment.
    const nets = resolveNets([bus, tap], []);
    expect(nets.length).toBe(1);
    expect(nets[0].connectionIds.sort()).toEqual(['BUS', 'TAP']);
  });

  // 4. five wires touching one busbar at five different points -> one net, five connections total (bus + 4 taps = 5)
  it('five wires touching one busbar at different points form one net with five connections', () => {
    const bus = makeWire('BUS', [{ x: 0, y: 0 }, { x: 320, y: 0 }], { style: 'BUS' });
    const taps = [32, 96, 160, 224].map((x, i) =>
      makeWire(`TAP${i}`, [{ x, y: 0 }, { x, y: 48 }])
    );
    const nets = resolveNets([bus, ...taps], []);
    expect(nets.length).toBe(1);
    expect(nets[0].connectionIds.length).toBe(5);
  });

  // 5. transitive joining: A touches B, B touches C -> one net
  it('joins transitively: A-B and B-C touching means A, B and C are one net', () => {
    const a = makeWire('A', [{ x: 0, y: 0 }, { x: 0, y: 32 }]);
    const b = makeWire('B', [{ x: 0, y: 32 }, { x: 64, y: 32 }]);
    const c = makeWire('C', [{ x: 64, y: 32 }, { x: 64, y: 96 }]);
    const nets = resolveNets([a, b, c], []);
    expect(nets.length).toBe(1);
    expect(nets[0].connectionIds.sort()).toEqual(['A', 'B', 'C']);
  });

  // 6. a net with an electrical terminal and a water terminal -> error
  //
  // Built from two boundary points rather than device symbols: a boundary
  // point's single terminal is resolved dynamically (Terminals.ts) from
  // its own label/side fields, independent of the registry's per-type
  // terminals data - so this test does not depend on any one device type
  // having terminals populated.
  it('a net spanning an electrical terminal and a water terminal is flagged an error', () => {
    const elecPoint: SynopticObject = {
      id: 'D1', type: 'scada.boundary_point', category: 'SCADA',
      x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
      visible: true, locked: false, layer: 1,
      tag: 'D1', description: '', color: '#000', fill: '#000', border: '#000',
      text: '', font: 'Arial', fontSize: 12, tooltip: '',
      width: 96, height: 52, customProperties: {},
      designation: 'A', boundaryDirection: 'SOURCE', boundaryMedium: 'ELECTRICAL', boundaryPortSide: 'BOTTOM'
    };
    // Single-character label clamps to MIN_WIDTH (96), fixed label-frame
    // height 52; BOTTOM side -> local fraction (0.5,1) -> (48,52), snapped
    // to the grid -> terminal at world (48,48).
    const waterPoint: SynopticObject = {
      ...elecPoint, id: 'D2', x: 192, designation: 'B', boundaryMedium: 'WATER'
    };
    // x=192 is a grid multiple, so its terminal lands at world (240,48).
    const wire = makeWire('W', [{ x: 48, y: 48 }, { x: 240, y: 48 }]);
    const nets = resolveNets([wire], [elecPoint, waterPoint]);
    expect(nets.length).toBe(1);
    const issues = validateNets(nets, [elecPoint, waterPoint]);
    expect(issues.some(i => i.code === 'MIXED_MEDIUM' && i.severity === 'ERROR')).toBe(true);
  });

  // 7. a net with no terminal at all -> warning
  it('a wire touching no terminal at all is flagged a warning', () => {
    const wire = makeWire('W', [{ x: 0, y: 0 }, { x: 64, y: 0 }]);
    const nets = resolveNets([wire], []);
    expect(nets.length).toBe(1);
    const issues = validateNets(nets, []);
    expect(issues.some(i => i.code === 'DANGLING_NET' && i.severity === 'WARNING')).toBe(true);
  });

  // 8. a node with three segments -> junction dot drawn
  it('a node where three wire segments meet gets a junction dot', () => {
    const a = makeWire('A', [{ x: 0, y: 0 }, { x: 32, y: 0 }]);
    const b = makeWire('B', [{ x: 32, y: 0 }, { x: 32, y: 32 }]);
    const c = makeWire('C', [{ x: 32, y: 0 }, { x: 64, y: 0 }]);
    const junctions = getJunctionPoints([a, b, c], []);
    expect(junctions).toContainEqual({ x: 32, y: 0 });
  });

  // 9. a node with two segments -> NOT a junction (just a bend)
  it('a node where only two segments meet (a plain bend) gets no junction dot', () => {
    const bendWire = makeWire('A', [{ x: 0, y: 0 }, { x: 32, y: 0 }, { x: 32, y: 32 }]);
    const junctions = getJunctionPoints([bendWire], []);
    expect(junctions).not.toContainEqual({ x: 32, y: 0 });
    expect(junctions.length).toBe(0);
  });

  // 10. empty connection list -> empty net list, no exception
  it('an empty connection list produces an empty net list without throwing', () => {
    expect(() => resolveNets([], [])).not.toThrow();
    expect(resolveNets([], [])).toEqual([]);
    // Even with items/terminals present, no wires means no nets.
    const device = makeDevice('D1', 0, 0);
    expect(resolveNets([], [device])).toEqual([]);
  });
});

describe('NetResolver.validateNets - two SOURCE boundary points', () => {
  it('a net touching two SOURCE boundary point terminals is flagged a warning', () => {
    const sourceA: SynopticObject = {
      id: 'S1', type: 'scada.boundary_point', category: 'SCADA',
      x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
      visible: true, locked: false, layer: 1,
      tag: 'S1', description: '', color: '#000', fill: '#000', border: '#000',
      text: '', font: 'Arial', fontSize: 12, tooltip: '',
      width: 96, height: 52, customProperties: {},
      designation: 'A', boundaryDirection: 'SOURCE', boundaryMedium: 'ELECTRICAL', boundaryPortSide: 'BOTTOM'
    };
    const sourceB: SynopticObject = { ...sourceA, id: 'S2', x: 192, designation: 'B' };

    // A single-character label clamps the frame to MIN_WIDTH (96), height
    // is the fixed 52px label-frame height; BOTTOM side -> local fraction
    // (0.5,1) -> (48,52), snapped to the grid -> (48,48). sourceB sits at
    // x=192 (a grid multiple), so its terminal lands at world (240,48).
    const wire = makeWire('W', [{ x: 48, y: 48 }, { x: 240, y: 48 }]);
    const nets = resolveNets([wire], [sourceA, sourceB]);
    expect(nets.length).toBe(1);
    const issues = validateNets(nets, [sourceA, sourceB]);
    expect(issues.some(i => i.code === 'MULTIPLE_SOURCES' && i.severity === 'WARNING')).toBe(true);
  });
});

describe('NetResolver - grid-node sanity', () => {
  it('every point used across these tests is a GRID_SIZE multiple (documents the fixture, not a NetResolver behavior)', () => {
    [0, 16, 32, 48, 64, 96, 160, 192, 224, 240, 320].forEach(v => {
      expect(v % GRID_SIZE).toBe(0);
    });
  });
});
