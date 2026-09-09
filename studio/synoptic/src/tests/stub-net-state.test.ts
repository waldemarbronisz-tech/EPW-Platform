// feat/wire-routing-around-obstacles commit 5 - the 8 mandatory tests
// for krociec colour coming from net state, and the tank being a
// source. Exercises NetResolver.ts's own resolveNets/getTerminalNetStates
// directly (the exact same functions SymbolRenderer.tsx now calls to
// color a krociec) - no Konva rendering needed, same convention
// net-resolver.test.ts already established.

import { describe, it, expect } from 'vitest';
import { resolveNets, getTerminalNetStates } from '../project/NetResolver';
import type { SynopticConnection, SynopticObject } from '../store';
import { isTankOutflowLive, tankPercentFromState } from '../symbols/site/RainwaterTank2Symbol';
import { getObjectTerminals, getTerminalWorldPosition } from '../utils/Terminals';

function makeWire(id: string, points: { x: number; y: number }[]): SynopticConnection {
  return { id, points, medium: 'WATER', style: 'NORMAL' };
}

/** A terminal's exact world position, read the same way the real app does - never hand-computed, so a factory's own width/height/label quirks (the boundary point's own text-driven sizing, in particular) can never silently drift out of sync with a hand-picked coordinate. */
function terminalPos(obj: SynopticObject, terminalId: string): { x: number; y: number } {
  const terminal = getObjectTerminals(obj).find(t => t.id === terminalId)!;
  return getTerminalWorldPosition(obj, terminal);
}

/** An orthogonal two-segment path between two arbitrary world points - a plain elbow, valid regardless of how the points relate to each other. */
function elbowPath(a: { x: number; y: number }, b: { x: number; y: number }): { x: number; y: number }[] {
  if (a.x === b.x || a.y === b.y) return [a, b];
  return [a, { x: b.x, y: a.y }, b];
}

function checkValve(id: string, x: number): SynopticObject {
  return {
    id, type: 'site.check_valve', category: 'Water',
    x, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 0,
    tag: '', description: '', color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
    customProperties: {}, width: 128, height: 96
  } as SynopticObject;
}

function selectorValve(id: string, x: number): SynopticObject {
  return {
    id, type: 'site.water_selector_valve_switched', category: 'Water',
    x, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 0,
    tag: '', description: '', color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
    customProperties: {}, width: 128, height: 96
  } as SynopticObject;
}

function boundarySource(id: string, x: number): SynopticObject {
  return {
    id, type: 'scada.boundary_point', category: 'SCADA',
    x, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 0,
    tag: '', description: '', color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
    customProperties: {}, width: 64, height: 64,
    boundaryDirection: 'SOURCE', boundaryMedium: 'WATER', boundaryPortSide: 'RIGHT'
  } as SynopticObject;
}

function tank(id: string, x: number, previewState: string): SynopticObject {
  return {
    id, type: 'site.rainwater_tank2', category: 'Water',
    x, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 0,
    tag: '', description: '', color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
    customProperties: {}, width: 128, height: 96,
    editor: { preview_state: previewState }
  } as SynopticObject;
}

describe('28. an unconnected terminal\'s krociec is inactive', () => {
  it('getTerminalNetStates has no entry at all for a terminal touched by no wire - the caller\'s own fallback (SymbolRenderer.tsx) reads that as INACTIVE', () => {
    const valve = checkValve('v1', 0);
    const states = getTerminalNetStates([], [valve]);
    expect(states.get('v1:WLOT')).toBeUndefined();
    expect(states.get('v1:WYLOT')).toBeUndefined();
  });
});

describe('29. a terminal wired to an active source is active', () => {
  it('a wire from a SOURCE boundary point to a valve\'s WLOT makes that terminal ACTIVE', () => {
    const valve = checkValve('v1', 400);
    const source = boundarySource('s1', 0);
    const wire = makeWire('w1', elbowPath(terminalPos(source, 'T1'), terminalPos(valve, 'WLOT')));
    const states = getTerminalNetStates([wire], [valve, source]);
    expect(states.get('v1:WLOT')).toBe('ACTIVE');
  });
});

describe('30. a closed valve reads active on one side, inactive on the other', () => {
  it('WLOT wired to an active source, WYLOT_A wired to nothing - two different states on the same object', () => {
    const valve = selectorValve('v1', 400);
    const source = boundarySource('s1', 0);
    const wireToWlot = makeWire('w1', elbowPath(terminalPos(source, 'T1'), terminalPos(valve, 'WLOT')));
    // A free-floating wire elsewhere, touching nothing - WYLOT_A stays
    // off any net at all (point c: unconnected, not merely inactive-
    // but-networked).
    const stray = makeWire('w2', [{ x: 900, y: 900 }, { x: 916, y: 900 }]);
    const states = getTerminalNetStates([wireToWlot, stray], [valve, source]);
    expect(states.get('v1:WLOT')).toBe('ACTIVE');
    expect(states.get('v1:WYLOT_A')).toBeUndefined();
  });
});

describe('31. a tank with a nonzero level is an active source on its own outflow', () => {
  it('WYSOKI (88%) tank, wire on ODPLYW, nothing else feeding it - the net is still ACTIVE, purely from the tank itself', () => {
    const t = tank('t1', 0, 'WYSOKI');
    const odplyw = terminalPos(t, 'ODPLYW');
    const wire = makeWire('w1', [odplyw, { x: odplyw.x + 32, y: odplyw.y }]);
    const nets = resolveNets([wire], [t]);
    expect(nets.length).toBe(1);
    expect(nets[0].state).toBe('ACTIVE');
  });
});

describe('32. a tank at level zero is not a source', () => {
  it('isTankOutflowLive(0) is false - the exact guard the tank source rule depends on (none of the three real states reach zero on their own, same as commit 4\'s own test 26)', () => {
    expect(isTankOutflowLive(0)).toBe(false);
  });

  it('every real, nonzero state IS live - the rule only ever gates on the water level actually being zero', () => {
    for (const s of ['NISKI', 'SREDNI', 'WYSOKI']) {
      expect(isTankOutflowLive(tankPercentFromState(s))).toBe(true);
    }
  });
});

describe('33. the net downstream of a full tank is active - the most important test: the gap flagged after the previous task, now closed', () => {
  it('a wire from a WYSOKI tank\'s ODPLYW to an ordinary valve\'s WLOT: the whole net (both terminals, the wire itself) reads ACTIVE', () => {
    const t = tank('t1', 0, 'WYSOKI');
    const valve = checkValve('v1', 400);
    const wire = makeWire('w1', elbowPath(terminalPos(t, 'ODPLYW'), terminalPos(valve, 'WLOT')));
    const nets = resolveNets([wire], [t, valve]);
    expect(nets.length).toBe(1);
    expect(nets[0].state).toBe('ACTIVE');
    const states = getTerminalNetStates([wire], [t, valve]);
    expect(states.get('t1:ODPLYW')).toBe('ACTIVE');
    expect(states.get('v1:WLOT')).toBe('ACTIVE');
  });
});

describe('34. the tank\'s own inflow takes its state from the inflow-side net, never from the water level', () => {
  it('a full (WYSOKI) tank\'s DOPLYW, wired to nothing else active, still reads INACTIVE - it is never a source itself', () => {
    const t = tank('t1', 0, 'WYSOKI');
    const doplyw = terminalPos(t, 'DOPLYW');
    const wire = makeWire('w1', [doplyw, { x: doplyw.x - 32, y: doplyw.y }]); // a dangling wire, no other source touches it
    const states = getTerminalNetStates([wire], [t]);
    expect(states.get('t1:DOPLYW')).toBe('INACTIVE');
  });

  it('but the SAME DOPLYW terminal reads ACTIVE once a real source feeds it - proving it genuinely reads the inflow net, not a hardcoded value', () => {
    const t = tank('t1', 0, 'WYSOKI');
    const source = boundarySource('s1', -600);
    const wire = makeWire('w1', elbowPath(terminalPos(source, 'T1'), terminalPos(t, 'DOPLYW')));
    const states = getTerminalNetStates([wire], [t, source]);
    expect(states.get('t1:DOPLYW')).toBe('ACTIVE');
  });
});

describe('35. no water aparat passes a hardcoded state to its own krociec any more', () => {
  it('every commit-5-touched component source reads terminalNetState for its own waterStub calls, not a bare state/on/true literal', async () => {
    const sources = await Promise.all([
      import('../symbols/site/CheckValveSymbol.tsx?raw'),
      import('../symbols/site/WaterFilterSymbol.tsx?raw'),
      import('../symbols/site/HydroforSymbol.tsx?raw'),
      import('../symbols/site/FlowMeterSymbol.tsx?raw'),
      import('../symbols/site/WaterMeterSymbol.tsx?raw'),
      import('../symbols/site/PressureSwitchSymbol.tsx?raw'),
      import('../symbols/site/SprinklerHeadSymbol.tsx?raw'),
      import('../symbols/site/DripLineSymbol.tsx?raw'),
      import('../symbols/site/WaterValveSymbol.tsx?raw'),
      import('../symbols/site/WaterSelectorValveSymbol.tsx?raw'),
      import('../symbols/site/RainTankSymbol.tsx?raw'),
      import('../symbols/site/SewagePlantSymbol.tsx?raw'),
      import('../symbols/site/WaterManholeSymbol.tsx?raw'),
      import('../symbols/site/GardenSprinklerSymbol.tsx?raw'),
      import('../symbols/site/RainwaterTank2Symbol.tsx?raw'),
      import('../symbols/water/ValveSymbol.tsx?raw'),
      import('../symbols/water/GateValveSymbol.tsx?raw'),
      import('../symbols/water/BallValveSymbol.tsx?raw'),
      import('../symbols/water/SolenoidValveSymbol.tsx?raw'),
      import('../symbols/water/DrainValveSymbol.tsx?raw'),
      import('../symbols/water/PumpSymbol.tsx?raw'),
      import('../symbols/water/TankSymbol.tsx?raw'),
      import('../symbols/water/DrainSymbol.tsx?raw')
    ]);
    for (const mod of sources) {
      const source = mod.default;
      expect(source).toContain('terminalNetState');
      // The old hardcoded forms this commit specifically removes.
      expect(source).not.toMatch(/waterStub\([^)]*,\s*true,/);
      expect(source).not.toMatch(/waterStub\([^)]*,\s*on,/);
      expect(source).not.toMatch(/waterStub\([^)]*,\s*live,/);
      expect(source).not.toMatch(/waterStub\([^)]*,\s*isRunning,/);
      expect(source).not.toMatch(/waterStub\([^)]*,\s*isOpen,/);
      expect(source).not.toMatch(/waterStub\([^)]*,\s*isA,/);
      expect(source).not.toMatch(/waterStub\([^)]*,\s*!isA,/);
      expect(source).not.toMatch(/waterStub\([^)]*,\s*isB,/);
      expect(source).not.toMatch(/waterStub\([^)]*,\s*!isClosed,/);
    }
  });

  it('SymbolRenderer.tsx never invents a second net-state mechanism - it calls NetResolver.ts\'s own getTerminalNetStates, nothing else', async () => {
    const rendererSource = (await import('../symbols/SymbolRenderer.tsx?raw')).default;
    expect(rendererSource).toContain('getTerminalNetStates');
    expect(rendererSource).toMatch(/from ['"]\.\.\/project\/NetResolver['"]/);
  });
});
