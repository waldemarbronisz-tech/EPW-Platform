// feat/tank-language-and-media commit 1 - the 7 mandatory tests for
// rejecting a mismatched-medium connection at DRAW time instead of
// only after the fact. Exercises the real pure functions Canvas.tsx
// itself calls (findNearestTerminal/findMediaConflictAtPoint/
// areMediaCompatible) - the same level anchor-terminal-consistency.
// test.ts and wire-routing-drawing.test.ts already operate at, since
// Canvas.tsx's own event handlers are not otherwise unit-testable
// without rendering a live browser (unavailable in this session - see
// raport.md).

import { describe, it, expect } from 'vitest';
import type { SynopticObject, SynopticConnection } from '../store';
import { findNearestTerminal } from '../utils/TerminalReach';
import { areMediaCompatible, findMediaConflictAtPoint, resolveNets, validateNets } from '../project/NetResolver';
import { mediaConflictMessage } from '../components/MediaMismatchDialog';
import canvasSource from '../components/Canvas.tsx?raw';
import netResolverSource from '../project/NetResolver.ts?raw';

function breaker(id: string, x: number): SynopticObject {
  return {
    id, type: 'electrical.circuit_breaker', category: 'Electrical',
    x, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 0,
    tag: '', description: '', color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
    customProperties: {}, width: 64, height: 64
  } as SynopticObject;
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

// electrical.circuit_breaker's own IN terminal: side TOP on a 64x64
// object, so local (width/2, 0) = (32, 0) - getTerminalOffsetForSide's
// own fixed rule, same fixture anchor-terminal-consistency.test.ts
// already relies on.
const IN_WORLD = (obj: SynopticObject) => ({ x: obj.x + 32, y: obj.y + 0 });

describe('1. a WATER terminal is dimmed (never the magnetism target) while drawing an ELECTRICAL wire', () => {
  it('findNearestTerminal with requiredMedium ELECTRICAL never returns a WATER terminal, even sitting right at the cursor', () => {
    const valve = checkValve('v1', 0); // WLOT at world (0,48)
    const cursor = { x: 0, y: 48 };
    expect(findNearestTerminal([valve], cursor, 8, 'ELECTRICAL')).toBeNull();
  });
});

describe('2. a WATER terminal IS highlighted while drawing a WATER wire', () => {
  it('findNearestTerminal with requiredMedium WATER finds it', () => {
    const valve = checkValve('v1', 0);
    const cursor = { x: 0, y: 48 };
    const found = findNearestTerminal([valve], cursor, 8, 'WATER');
    expect(found?.objId).toBe('v1');
    expect(found?.terminalId).toBe('WLOT');
  });
});

describe('3. finishing an ELECTRICAL wire on a WATER terminal creates no connection', () => {
  it('findMediaConflictAtPoint flags the WLOT terminal as a conflict for an ELECTRICAL wire - Canvas.tsx\'s own guard returns before calling addConnection at all', () => {
    const valve = checkValve('v1', 0);
    const conflict = findMediaConflictAtPoint({ x: 0, y: 48 }, [valve], [], 'ELECTRICAL');
    expect(conflict).toEqual({ drawnMedium: 'ELECTRICAL', otherMedium: 'WATER', source: 'terminal' });
  });
});

describe('4. an incompatible connection attempt reports an ERROR message', () => {
  it('mediaConflictMessage always starts with [ERROR] and names both media', () => {
    const message = mediaConflictMessage({ drawnMedium: 'ELECTRICAL', otherMedium: 'WATER', source: 'terminal' });
    expect(message.startsWith('[ERROR]')).toBe(true);
    expect(message).toContain('Electrical');
    expect(message).toContain('Water');
  });

  it('Canvas.tsx actually posts it to the Messages panel when a conflict is found', () => {
    expect(canvasSource).toMatch(/addMessage\(mediaConflictMessage\(conflict\)\)/);
  });
});

describe('5. drawing stays armed after a rejected attempt', () => {
  it('the conflict-handling block only sets the dialog state and posts a message, then returns - it never disarms the wire tool or clears the in-progress polyline', () => {
    const match = /if \(conflict\) \{([\s\S]*?)\n {6}\}/.exec(canvasSource);
    expect(match, 'the conflict-handling block should exist in Canvas.tsx').toBeTruthy();
    const block = match![1];
    expect(block).toContain('setMediaConflict(conflict)');
    expect(block).toContain('addMessage(mediaConflictMessage(conflict))');
    expect(block).not.toContain('setDrawingMode');
    expect(block).not.toContain('setDrawingPoints(null)');
    expect(block).not.toContain('commitWire');
  });
});

describe('6. a WATER wire touching the middle of an ELECTRICAL wire does not join one net', () => {
  const elecWire: SynopticConnection = { id: 'e1', medium: 'ELECTRICAL', style: 'NORMAL', points: [{ x: 0, y: 0 }, { x: 160, y: 0 }] };
  const midpoint = { x: 80, y: 0 }; // exactly on e1's own segment, not an endpoint

  it('findMediaConflictAtPoint flags the touch before the WATER wire is ever created', () => {
    const conflict = findMediaConflictAtPoint(midpoint, [], [elecWire], 'WATER');
    expect(conflict).toEqual({ drawnMedium: 'WATER', otherMedium: 'ELECTRICAL', source: 'wire' });
  });

  it('sanity: had this NOT been blocked, resolveNets would have unioned them into one (mixed-medium) net - this is the real bug the guard prevents', () => {
    const waterWire: SynopticConnection = { id: 'w1', medium: 'WATER', style: 'NORMAL', points: [{ x: 80, y: 0 }, { x: 80, y: 64 }] };
    const nets = resolveNets([elecWire, waterWire], []);
    expect(nets.length).toBe(1);
    expect(nets[0].connectionIds.sort()).toEqual(['e1', 'w1']);
  });
});

describe('7. the compatibility check uses the exact same rule as NetResolver\'s own validation', () => {
  it('findMediaConflictAtPoint and validateNets both call areMediaCompatible - never a second, independent copy of the rule', () => {
    const occurrences = netResolverSource.match(/areMediaCompatible\(/g) || [];
    // The function's own declaration, plus at least one real call from
    // validateNets and one from findMediaConflictAtPoint.
    expect(occurrences.length).toBeGreaterThanOrEqual(3);
  });

  it('the two paths agree on the same pair: a net mixing ELECTRICAL and WATER terminals is exactly what findMediaConflictAtPoint would already have refused at draw time', () => {
    const elec = breaker('b1', 0);
    const valve = checkValve('v1', 200);
    const inWorld = IN_WORLD(elec);
    const wire: SynopticConnection = { id: 'w1', medium: 'ELECTRICAL', style: 'NORMAL', points: [inWorld, { x: inWorld.x, y: 48 }, { x: 200, y: 48 }] };
    // validateNets' own path (post-hoc, on an already-formed net).
    const nets = resolveNets([wire], [elec, valve]);
    const issues = validateNets(nets, [elec, valve]);
    expect(issues.some(i => i.code === 'MIXED_MEDIUM')).toBe(true);
    // findMediaConflictAtPoint's own path (pre-hoc, the exact same pair).
    expect(areMediaCompatible('ELECTRICAL', 'WATER')).toBe(false);
    const conflict = findMediaConflictAtPoint({ x: 200, y: 48 }, [elec, valve], [], 'ELECTRICAL');
    expect(conflict?.otherMedium).toBe('WATER');
  });
});
