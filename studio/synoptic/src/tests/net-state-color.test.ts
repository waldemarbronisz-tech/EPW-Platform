// feat/water-management commit 2 - the 7 mandatory tests (11-17) for
// net state derived from the network instead of set by hand.
//
// A net's state is computed by resolveNets itself now (NetResolver.ts)
// from whether it touches an ACTIVE SOURCE: a SOURCE boundary point, or
// a symbol bound to a SWITCHED device whose own Editor Preview state is
// 'CLOSED', checked at that symbol's own 'OUT' terminal (the universal
// IN/OUT naming every two-terminal symbol in this registry already
// uses - electrical.circuit_breaker included, reused here as the
// fixture, same as wire-anchoring.test.ts's own).

import { describe, it, expect } from 'vitest';
import { resolveNets } from '../project/NetResolver';
import { getConductorCoreColor } from '../components/ConnectionLine';
import type { SynopticConnection, SynopticObject } from '../store';
import type { Device } from '../project/DeviceSchema';
import { COLOR_ENERGIZED, COLOR_DE_ENERGIZED, COLOR_WATER, COLOR_WATER_INACTIVE, VENTILATION_ACTIVE, VENTILATION_INACTIVE } from '../theme/ScadaTheme';

function wire(id: string, points: { x: number; y: number }[], overrides: Partial<SynopticConnection> = {}): SynopticConnection {
  return { id, points, medium: 'ELECTRICAL', style: 'NORMAL', ...overrides };
}

function boundaryPoint(id: string, x: number, direction: 'SOURCE' | 'SINK'): SynopticObject {
  return {
    id, type: 'scada.boundary_point', category: 'SCADA',
    x, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 1,
    tag: id, description: '', color: '#000', fill: '#000', border: '#000',
    text: '', font: 'Arial', fontSize: 12, tooltip: '',
    width: 96, height: 52, customProperties: {},
    designation: 'A', boundaryDirection: direction, boundaryMedium: 'ELECTRICAL', boundaryPortSide: 'BOTTOM'
  } as SynopticObject;
  // Single-char label clamps to MIN_WIDTH 96, BOTTOM side -> local
  // (48,52) snapped to grid -> world terminal at (x+48, 48).
}

// electrical.circuit_breaker: defaultWidth/Height 64, terminals IN
// (TOP, local 32,0) / OUT (BOTTOM, local 32,64) - same fixture shape as
// wire-anchoring.test.ts's own breaker().
function breaker(id: string, x: number, overrides: Partial<SynopticObject> = {}): SynopticObject {
  return {
    id, type: 'electrical.circuit_breaker', category: 'Electrical',
    x, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 0,
    tag: '', description: '', color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
    customProperties: {}, width: 64, height: 64,
    ...overrides
  } as SynopticObject;
}

function switchedDevice(id: string): Device {
  return {
    id, designation: '-K1', name: 'Test breaker', behavior: 'SWITCHED', kind: 'breaker', publishToHa: false,
    feedback: { mode: 'NONE' },
    command: { outputCount: 1, style: 'MAINTAINED', doClose: 'ADA1.DO.1' },
    supervision: { confirmTimeoutMs: 500, discrepancyAlarm: false },
    safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' },
    switchCounter: false
  } as Device;
}

describe('11. a net with a SOURCE boundary point is active', () => {
  it('resolveNets marks the net ACTIVE', () => {
    const src = boundaryPoint('S1', 0, 'SOURCE');
    const w = wire('W1', [{ x: 48, y: 48 }, { x: 200, y: 48 }]);
    const nets = resolveNets([w], [src]);
    expect(nets).toHaveLength(1);
    expect(nets[0].state).toBe('ACTIVE');
  });
});

describe('12. a net with no source at all is inactive', () => {
  it('a plain wire touching no source resolves INACTIVE', () => {
    const sink = boundaryPoint('S1', 0, 'SINK');
    const w = wire('W1', [{ x: 48, y: 48 }, { x: 200, y: 48 }]);
    const nets = resolveNets([w], [sink]);
    expect(nets).toHaveLength(1);
    expect(nets[0].state).toBe('INACTIVE');
  });

  it('a wire touching no terminal at all also resolves INACTIVE', () => {
    const w = wire('W1', [{ x: 0, y: 0 }, { x: 64, y: 0 }]);
    const nets = resolveNets([w], []);
    expect(nets[0].state).toBe('INACTIVE');
  });
});

describe('13. a net with a SWITCHED device in closed state is active on the output side', () => {
  it('resolveNets marks the net touching the breaker\'s OUT terminal ACTIVE when the device is SWITCHED and the symbol reads CLOSED', () => {
    const b = breaker('B1', 0, { deviceId: 'D1', editor: { preview_state: 'CLOSED' } });
    // OUT terminal at local (32,64) -> world (32,64).
    const w = wire('W1', [{ x: 32, y: 64 }, { x: 32, y: 128 }]);
    const nets = resolveNets([w], [b], [switchedDevice('D1')]);
    expect(nets).toHaveLength(1);
    expect(nets[0].state).toBe('ACTIVE');
  });
});

describe('14. a net with a SWITCHED device in open state is inactive', () => {
  it('the same breaker, now reading OPEN, no longer makes its net ACTIVE', () => {
    const b = breaker('B1', 0, { deviceId: 'D1', editor: { preview_state: 'OPEN' } });
    const w = wire('W1', [{ x: 32, y: 64 }, { x: 32, y: 128 }]);
    const nets = resolveNets([w], [b], [switchedDevice('D1')]);
    expect(nets[0].state).toBe('INACTIVE');
  });
});

describe('15. a net whose source device does not exist is inactive', () => {
  it('a deviceId that resolves to nothing in the devices list never counts as a source', () => {
    const b = breaker('B1', 0, { deviceId: 'GHOST', editor: { preview_state: 'CLOSED' } });
    const w = wire('W1', [{ x: 32, y: 64 }, { x: 32, y: 128 }]);
    const nets = resolveNets([w], [b], []); // devices list empty - GHOST resolves to nothing
    expect(nets[0].state).toBe('INACTIVE');
  });

  it('a symbol with no deviceId at all never counts as a source, even if its own state happens to read CLOSED', () => {
    const b = breaker('B1', 0, { editor: { preview_state: 'CLOSED' } });
    const w = wire('W1', [{ x: 32, y: 64 }, { x: 32, y: 128 }]);
    const nets = resolveNets([w], [b], [switchedDevice('D1')]);
    expect(nets[0].state).toBe('INACTIVE');
  });
});

describe('16. two disjoint nets can have different states at the same time', () => {
  it('one net with a source and one without, resolved together, disagree', () => {
    const src = boundaryPoint('S1', 0, 'SOURCE');
    const sink = boundaryPoint('S2', 400, 'SINK');
    const activeWire = wire('W1', [{ x: 48, y: 48 }, { x: 200, y: 48 }]);
    const inactiveWire = wire('W2', [{ x: 448, y: 48 }, { x: 600, y: 48 }]);
    const nets = resolveNets([activeWire, inactiveWire], [src, sink]);
    expect(nets).toHaveLength(2);
    const activeNet = nets.find(n => n.connectionIds.includes('W1'))!;
    const inactiveNet = nets.find(n => n.connectionIds.includes('W2'))!;
    expect(activeNet.state).toBe('ACTIVE');
    expect(inactiveNet.state).toBe('INACTIVE');
  });
});

describe('17. connection Properties no longer has a manual state field', () => {
  it('PropertyInspector.tsx no longer renders a state <select> for a wire (source-scan, same convention as scada-symbols.test.ts)', async () => {
    const source = (await import('../components/PropertyInspector.tsx?raw')).default as unknown as string;
    expect(source).not.toMatch(/name="state"/);
    expect(source).not.toContain('<option value="LIVE">Live</option>');
    expect(source).not.toContain('<option value="DEAD">Dead</option>');
  });

  it('the State row that remains is read-only (a disabled input, not a select the user can change)', async () => {
    const source = (await import('../components/PropertyInspector.tsx?raw')).default as unknown as string;
    expect(source).toMatch(/<label>State<\/label>\s*<input[^>]*disabled/);
  });
});

describe('wire color follows net state and medium (six pairs from the task\'s own table)', () => {
  it('WATER active -> blue, inactive -> light gray', () => {
    expect(getConductorCoreColor('WATER', 'ACTIVE')).toBe(COLOR_WATER);
    expect(getConductorCoreColor('WATER', 'INACTIVE')).toBe(COLOR_WATER_INACTIVE);
  });
  it('ELECTRICAL active -> red, inactive -> gray', () => {
    expect(getConductorCoreColor('ELECTRICAL', 'ACTIVE')).toBe(COLOR_ENERGIZED);
    expect(getConductorCoreColor('ELECTRICAL', 'INACTIVE')).toBe(COLOR_DE_ENERGIZED);
  });
  it('VENTILATION active -> gold, inactive -> dimmed gold', () => {
    expect(getConductorCoreColor('VENTILATION', 'ACTIVE')).toBe(VENTILATION_ACTIVE);
    expect(getConductorCoreColor('VENTILATION', 'INACTIVE')).toBe(VENTILATION_INACTIVE);
  });
});
