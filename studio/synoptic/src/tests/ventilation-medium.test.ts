// feat/media-and-proportions part B: VENTILATION as a third medium
// alongside ELECTRICAL and WATER. Five mandatory scenarios: a net
// mixing VENTILATION with WATER is an error, mixing VENTILATION with
// ELECTRICAL is an error, a net made purely of VENTILATION terminals is
// valid, a VENTILATION-medium wire draws in the ventilation color, and
// a VENTILATION boundary point resolves a valid terminal.

import { describe, it, expect } from 'vitest';
import { resolveNets, validateNets } from '../project/NetResolver';
import { getObjectTerminals } from '../utils/Terminals';
import { getConductorCoreColor } from '../components/ConnectionLine';
import type { SynopticConnection, SynopticObject } from '../store';
import { VENTILATION_ACTIVE, VENTILATION_INACTIVE } from '../theme/ScadaTheme';

function makeWire(id: string, points: { x: number; y: number }[], overrides: Partial<SynopticConnection> = {}): SynopticConnection {
  return { id, points, medium: 'ELECTRICAL', style: 'NORMAL', state: 'LIVE', ...overrides };
}

// A boundary point's single terminal is resolved dynamically from its
// own label/side fields (Terminals.ts), independent of any device
// type's registry terminals data - the same pattern net-resolver.test.ts
// uses for its own mixed-medium test, reused here so these tests do not
// depend on which device types happen to carry which terminal medium.
function makeBoundaryPoint(id: string, x: number, medium: SynopticObject['boundaryMedium']): SynopticObject {
  return {
    id, type: 'scada.boundary_point', category: 'SCADA',
    x, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 1,
    tag: id, description: '', color: '#000', fill: '#000', border: '#000',
    text: '', font: 'Arial', fontSize: 12, tooltip: '',
    width: 96, height: 52, customProperties: {},
    designation: 'A', boundaryDirection: 'SOURCE', boundaryMedium: medium, boundaryPortSide: 'BOTTOM'
  };
  // Single-character label clamps to MIN_WIDTH (96); BOTTOM side ->
  // local fraction (0.5,1) -> (48,52), snapped to the grid -> terminal
  // at world (x+48, 48).
}

describe('VENTILATION as a third medium', () => {
  // 1. a net with a ventilation terminal and a water terminal -> error
  it('a net spanning a ventilation terminal and a water terminal is flagged an error', () => {
    const ventPoint = makeBoundaryPoint('D1', 0, 'VENTILATION');
    const waterPoint = makeBoundaryPoint('D2', 192, 'WATER');
    const wire = makeWire('W', [{ x: 48, y: 48 }, { x: 240, y: 48 }]);
    const nets = resolveNets([wire], [ventPoint, waterPoint]);
    expect(nets.length).toBe(1);
    const issues = validateNets(nets, [ventPoint, waterPoint]);
    expect(issues.some(i => i.code === 'MIXED_MEDIUM' && i.severity === 'ERROR')).toBe(true);
  });

  // 2. a net with a ventilation terminal and an electrical terminal -> error
  it('a net spanning a ventilation terminal and an electrical terminal is flagged an error', () => {
    const ventPoint = makeBoundaryPoint('D1', 0, 'VENTILATION');
    const elecPoint = makeBoundaryPoint('D2', 192, 'ELECTRICAL');
    const wire = makeWire('W', [{ x: 48, y: 48 }, { x: 240, y: 48 }]);
    const nets = resolveNets([wire], [ventPoint, elecPoint]);
    expect(nets.length).toBe(1);
    const issues = validateNets(nets, [ventPoint, elecPoint]);
    expect(issues.some(i => i.code === 'MIXED_MEDIUM' && i.severity === 'ERROR')).toBe(true);
  });

  // 3. a net made entirely of ventilation terminals -> valid, no MIXED_MEDIUM
  it('a net made purely of ventilation terminals is valid', () => {
    const ventA = makeBoundaryPoint('D1', 0, 'VENTILATION');
    const ventB = makeBoundaryPoint('D2', 192, 'VENTILATION');
    const wire = makeWire('W', [{ x: 48, y: 48 }, { x: 240, y: 48 }], { medium: 'VENTILATION' });
    const nets = resolveNets([wire], [ventA, ventB]);
    expect(nets.length).toBe(1);
    const issues = validateNets(nets, [ventA, ventB]);
    expect(issues.some(i => i.code === 'MIXED_MEDIUM')).toBe(false);
  });

  // 4. a VENTILATION-medium wire draws in the ventilation color, not
  // power's red or water's blue - and ACTIVE/INACTIVE (net state, feat/
  // water-management commit 2 - no longer a manual per-connection
  // setting) still switches shade, exactly like every other medium now
  // (water included, which used to have no such split at all).
  it('a ventilation wire draws with the ventilation color, switching on net state', () => {
    expect(getConductorCoreColor('VENTILATION', 'ACTIVE')).toBe(VENTILATION_ACTIVE);
    expect(getConductorCoreColor('VENTILATION', 'INACTIVE')).toBe(VENTILATION_INACTIVE);
    expect(getConductorCoreColor('VENTILATION', 'ACTIVE')).not.toBe(getConductorCoreColor('WATER', 'ACTIVE'));
    expect(getConductorCoreColor('VENTILATION', 'ACTIVE')).not.toBe(getConductorCoreColor('ELECTRICAL', 'ACTIVE'));
  });

  // 5. a boundary point with medium VENTILATION resolves a valid terminal
  it('a boundary point with medium VENTILATION resolves one VENTILATION terminal', () => {
    const point = makeBoundaryPoint('D1', 0, 'VENTILATION');
    const terminals = getObjectTerminals(point);
    expect(terminals.length).toBe(1);
    expect(terminals[0].medium).toBe('VENTILATION');
    expect(terminals[0].x % 16).toBe(0);
    expect(terminals[0].y % 16).toBe(0);
  });
});
