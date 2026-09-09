// fix/wiring-and-library-groups commit 3 - the 4 mandatory tests for
// usterka 3 ("zaczepienie nie trafia w zacisk"). Plain move/rotate
// (13/14) were already correct before this commit (feat/water-
// management's own syncAnchoredConnections already recomputes from
// getTerminalWorldPosition, never a vector shift) - included here for
// this commit's own numbering, not because they needed a code change.
// Resize (15) had no dedicated test anywhere before this commit -
// genuinely new coverage, confirming scaleX/scaleY already flow
// through correctly too. The REAL fix this commit makes is
// moveSelectionBy's own connection-move branch (selectionSlice.ts),
// which used to silently drop an anchor whenever a selected wire moved
// - even when its own anchor's symbol was moving right along with it
// in the very same group action - and findAnchorDiscrepancies
// (WireAnchoring.ts), the consistency check point (c) asks for.

import { describe, it, expect } from 'vitest';
import { useStore } from '../store';
import type { SynopticObject } from '../store';
import { resolveNets } from '../project/NetResolver';
import { syncAnchoredConnections, findAnchorDiscrepancies } from '../utils/WireAnchoring';
import { getObjectTerminals, getTerminalWorldPosition } from '../utils/Terminals';

function breaker(overrides: Partial<SynopticObject> = {}): SynopticObject {
  return {
    id: 'b1', type: 'electrical.circuit_breaker', category: 'Electrical',
    x: 160, y: 160, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 0,
    tag: '', description: '', color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
    customProperties: {}, width: 64, height: 64,
    ...overrides
  } as SynopticObject;
}

const IN_WORLD = { x: 192, y: 160 };

function wireAnchoredToIn() {
  return { id: 'c1', medium: 'ELECTRICAL' as const, style: 'NORMAL' as const, points: [{ x: 192, y: 80 }, { x: IN_WORLD.x, y: IN_WORLD.y, anchor: { symbolId: 'b1', terminalId: 'IN' } }] };
}

describe('13. after moving a symbol, the anchored point has coordinates EXACTLY equal to the terminal', () => {
  it('syncAnchoredConnections lands the anchored point exactly on the recomputed terminal, not a vector shift', () => {
    const moved = breaker({ x: 160 + 48, y: 160 + 32 });
    const [synced] = syncAnchoredConnections([wireAnchoredToIn()], [moved]);
    const anchoredPoint = synced.points.find(p => p.anchor)!;
    const expected = getTerminalWorldPosition(moved, getObjectTerminals(moved).find(t => t.id === 'IN')!);
    expect({ x: anchoredPoint.x, y: anchoredPoint.y }).toEqual(expected);
  });
});

describe('14. after a 90 degree rotation, the anchored point lands on the terminal\'s new position', () => {
  it('recomputed from rotation, not the old position plus a delta', () => {
    const rotated = breaker({ rotation: 90 });
    const [synced] = syncAnchoredConnections([wireAnchoredToIn()], [rotated]);
    const anchoredPoint = synced.points.find(p => p.anchor)!;
    const expected = getTerminalWorldPosition(rotated, getObjectTerminals(rotated).find(t => t.id === 'IN')!);
    expect({ x: anchoredPoint.x, y: anchoredPoint.y }).toEqual(expected);
  });
});

describe('15. after resizing a symbol, the anchored point lands on the recomputed terminal', () => {
  it('a 2x scale moves the anchored IN point to exactly double its own local offset from the object origin', () => {
    const resized = breaker({ scaleX: 2, scaleY: 2 });
    const [synced] = syncAnchoredConnections([wireAnchoredToIn()], [resized]);
    const anchoredPoint = synced.points.find(p => p.anchor)!;
    // IN's local offset is (32,0) - at 2x scale, world = (160+64, 160+0) = (224,160).
    expect({ x: anchoredPoint.x, y: anchoredPoint.y }).toEqual({ x: 224, y: 160 });
    const expected = getTerminalWorldPosition(resized, getObjectTerminals(resized).find(t => t.id === 'IN')!);
    expect({ x: anchoredPoint.x, y: anchoredPoint.y }).toEqual(expected);
  });
});

describe('16. the net stays one after a move, a rotation and a resize in sequence', () => {
  it('resolveNets still finds exactly one net touching the terminal after all three', () => {
    let connections: any[] = [wireAnchoredToIn()];
    let obj = breaker();

    obj = breaker({ x: obj.x + 32, y: obj.y + 16 });
    connections = syncAnchoredConnections(connections, [obj]);

    obj = { ...obj, rotation: 90 };
    connections = syncAnchoredConnections(connections, [obj]);

    obj = { ...obj, scaleX: 1.5, scaleY: 1.5 };
    connections = syncAnchoredConnections(connections, [obj]);

    const nets = resolveNets(connections, [obj]);
    expect(nets).toHaveLength(1);
    expect(nets[0].terminals).toContainEqual({ objId: 'b1', terminalId: 'IN' });
  });
});

describe('the actual fix: moveSelectionBy preserves an anchor when its own symbol moves together with the wire', () => {
  function resetStore(objects: SynopticObject[], connections: any[], selectedIds: string[], selectedConnectionIds: string[]) {
    useStore.setState({
      objects, connections, messages: [],
      selectedIds, selectedConnectionIds, selectedMeterIds: [], selectedSignalPanelIds: [],
      selectedFrameIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: []
    });
  }

  it('symbol AND its wire selected together: the anchor survives a group move, and the point still matches the terminal', () => {
    resetStore([breaker()], [wireAnchoredToIn()], ['b1'], ['c1']);
    useStore.getState().moveSelectionBy(32, 16);
    const conn = useStore.getState().connections.find(c => c.id === 'c1')!;
    const anchoredPoint = conn.points.find(p => p.anchor);
    expect(anchoredPoint?.anchor).toEqual({ symbolId: 'b1', terminalId: 'IN' });
    const obj = useStore.getState().objects.find(o => o.id === 'b1')!;
    const expected = getTerminalWorldPosition(obj, getObjectTerminals(obj).find(t => t.id === 'IN')!);
    expect({ x: anchoredPoint!.x, y: anchoredPoint!.y }).toEqual(expected);
  });

  it('wire selected WITHOUT its own symbol: moving it breaks the anchor (same rule a manual point-drag already applies)', () => {
    resetStore([breaker()], [wireAnchoredToIn()], [], ['c1']);
    useStore.getState().moveSelectionBy(32, 16);
    const conn = useStore.getState().connections.find(c => c.id === 'c1')!;
    const anchoredPoint = conn.points.find(p => p.anchor);
    expect(anchoredPoint).toBeUndefined();
  });

  it('a later, solo move of the symbol still correctly follows the wire after a symbol+wire group move (the bug this fix actually prevents)', () => {
    resetStore([breaker()], [wireAnchoredToIn()], ['b1'], ['c1']);
    useStore.getState().moveSelectionBy(32, 16); // group move - anchor must survive
    useStore.setState({ selectedIds: ['b1'], selectedConnectionIds: [] }); // now select ONLY the symbol
    useStore.getState().moveSelectionBy(16, 48); // a second, solo symbol move
    const conn = useStore.getState().connections.find(c => c.id === 'c1')!;
    const anchoredPoint = conn.points.find(p => p.anchor)!;
    const obj = useStore.getState().objects.find(o => o.id === 'b1')!;
    const expected = getTerminalWorldPosition(obj, getObjectTerminals(obj).find(t => t.id === 'IN')!);
    expect({ x: anchoredPoint.x, y: anchoredPoint.y }).toEqual(expected);
  });
});

describe('the consistency check (point c): findAnchorDiscrepancies', () => {
  it('reports nothing when every anchored point already agrees with its terminal', () => {
    expect(findAnchorDiscrepancies([wireAnchoredToIn()], [breaker()])).toEqual([]);
  });

  it('reports a discrepancy when an anchored point has drifted from its own terminal', () => {
    const driftedConn = { id: 'c1', medium: 'ELECTRICAL' as const, style: 'NORMAL' as const, points: [{ x: 192, y: 80 }, { x: 300, y: 300, anchor: { symbolId: 'b1', terminalId: 'IN' } }] };
    const issues = findAnchorDiscrepancies([driftedConn], [breaker()]);
    expect(issues).toEqual([{ connectionId: 'c1', symbolId: 'b1', terminalId: 'IN' }]);
  });

  // Not tested through the real store's own saveHistory(): that
  // function runs syncAnchoredConnections BEFORE this check, and sync's
  // whole job is to eliminate exactly this kind of drift - so by
  // construction, this check can never actually find anything in a
  // normal call, only in an isolated call that bypasses the sync
  // (exactly what the two tests above already do). That is the point:
  // a standing guard that costs nothing while everything upstream of it
  // keeps working, not a scenario meant to be exercised end to end.
});
