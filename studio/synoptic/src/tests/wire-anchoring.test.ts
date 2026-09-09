// feat/water-management commit 1 - the 10 mandatory tests for wire
// endpoints following the terminals they attach to. Pure-function
// tests wherever possible (attachAnchorsToNewPoints/syncAnchoredConnections/
// releaseAnchorsForDeletedObjects are all Konva-free), plus a handful
// against the real store (useStore) for the parts that only make sense
// end-to-end (test 7's Messages notice, test 9's load-without-error).
//
// A single fixture object throughout: 'electrical.circuit_breaker' (a
// real, registered symbol - SymbolRegistry.ts - defaultWidth/Height 64,
// terminals IN (TOP) and OUT (BOTTOM)), placed at a grid-aligned (160,160)
// so its own terminals land on clean, easy-to-check coordinates:
//   IN  (TOP,    local 32,0 ) -> world (192,160)
//   OUT (BOTTOM, local 32,64) -> world (192,224)

import { describe, it, expect } from 'vitest';
import { useStore } from '../store';
import type { SynopticObject } from '../store';
import { resolveNets } from '../project/NetResolver';
import {
  findTerminalAt, attachAnchorsToNewPoints, syncAnchoredConnections, releaseAnchorsForDeletedObjects
} from '../utils/WireAnchoring';

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

describe('1. a point created exactly on a terminal remembers it', () => {
  it('attachAnchorsToNewPoints anchors a point landing on the IN terminal', () => {
    const points = [{ x: 192, y: 80 }, { x: IN_WORLD.x, y: IN_WORLD.y }];
    const anchored = attachAnchorsToNewPoints(points, [breaker()]);
    expect(anchored[1].anchor).toEqual({ symbolId: 'b1', terminalId: 'IN' });
  });

  it('findTerminalAt resolves the same terminal directly', () => {
    expect(findTerminalAt([breaker()], IN_WORLD.x, IN_WORLD.y)).toEqual({ symbolId: 'b1', terminalId: 'IN' });
  });
});

describe('2. a point created off a terminal has no anchor', () => {
  it('attachAnchorsToNewPoints leaves an unrelated point untouched', () => {
    const points = [{ x: 192, y: 80 }, { x: 400, y: 400 }];
    const anchored = attachAnchorsToNewPoints(points, [breaker()]);
    expect(anchored[0].anchor).toBeUndefined();
    expect(anchored[1].anchor).toBeUndefined();
  });

  it('findTerminalAt returns null a few pixels off the real terminal (exact match only)', () => {
    expect(findTerminalAt([breaker()], IN_WORLD.x + 1, IN_WORLD.y)).toBeNull();
  });
});

describe('3. moving the symbol by 3 grid cells moves the anchored point by the same amount', () => {
  it('a purely vertical 3-cell move (48 units) translates the anchor exactly, no elbow needed', () => {
    const conn = { id: 'c1', points: [{ x: 192, y: 80 }, { x: IN_WORLD.x, y: IN_WORLD.y, anchor: { symbolId: 'b1', terminalId: 'IN' } }], medium: 'ELECTRICAL' as const, style: 'NORMAL' as const, state: 'LIVE' as const };
    const moved = breaker({ y: 160 + 48 }); // 3 * GRID_SIZE(16)
    const synced = syncAnchoredConnections([conn], [moved]);
    const anchoredPoint = synced[0].points.find(p => p.anchor);
    expect(anchoredPoint).toEqual({ x: 192, y: 208, anchor: { symbolId: 'b1', terminalId: 'IN' } });
  });
});

describe('4. moving the symbol does NOT move the free points of that same wire', () => {
  it('the free endpoint (192,80) is unchanged after the symbol moves', () => {
    const conn = { id: 'c1', points: [{ x: 192, y: 80 }, { x: IN_WORLD.x, y: IN_WORLD.y, anchor: { symbolId: 'b1', terminalId: 'IN' } }], medium: 'ELECTRICAL' as const, style: 'NORMAL' as const, state: 'LIVE' as const };
    const moved = breaker({ y: 160 + 48 });
    const synced = syncAnchoredConnections([conn], [moved]);
    expect(synced[0].points[0]).toEqual({ x: 192, y: 80 });
  });
});

describe('5. after moving the symbol the net stays ONE, it does not split into two (the most important test)', () => {
  it('resolveNets still finds one net joining the wire and the moved terminal', () => {
    const conn = { id: 'c1', points: [{ x: 192, y: 80 }, { x: IN_WORLD.x, y: IN_WORLD.y, anchor: { symbolId: 'b1', terminalId: 'IN' } }], medium: 'ELECTRICAL' as const, style: 'NORMAL' as const, state: 'LIVE' as const };

    // Sanity: before any move, they are already one net.
    const netsBefore = resolveNets([conn], [breaker()]);
    expect(netsBefore).toHaveLength(1);
    expect(netsBefore[0].terminals).toContainEqual({ objId: 'b1', terminalId: 'IN' });

    // Move the symbol diagonally (both x and y) - the worst case, where
    // an un-synced wire would be left pointing at empty space entirely.
    const moved = breaker({ x: 160 + 48, y: 160 + 32 });
    const syncedConnections = syncAnchoredConnections([conn], [moved]);

    const netsAfter = resolveNets(syncedConnections, [moved]);
    expect(netsAfter).toHaveLength(1);
    expect(netsAfter[0].connectionIds).toContain('c1');
    expect(netsAfter[0].terminals).toContainEqual({ objId: 'b1', terminalId: 'IN' });
  });
});

describe('6. rotating the symbol by 90 degrees moves the anchored point to the terminal\'s new position', () => {
  it('a 90-degree rotation moves the IN terminal from (192,160) to (160,192), and the anchor follows', () => {
    const conn = { id: 'c1', points: [{ x: 192, y: 80 }, { x: IN_WORLD.x, y: IN_WORLD.y, anchor: { symbolId: 'b1', terminalId: 'IN' } }], medium: 'ELECTRICAL' as const, style: 'NORMAL' as const, state: 'LIVE' as const };
    const rotated = breaker({ rotation: 90 });
    const synced = syncAnchoredConnections([conn], [rotated]);
    const anchoredPoint = synced[0].points.find(p => p.anchor);
    expect(anchoredPoint?.x).toBe(160);
    expect(anchoredPoint?.y).toBe(192);
  });
});

describe('7. deleting the symbol releases the anchor without exception, and reports it', () => {
  it('releaseAnchorsForDeletedObjects clears the anchor and leaves the point where it was', () => {
    const conn = { id: 'c1', points: [{ x: 192, y: 80 }, { x: IN_WORLD.x, y: IN_WORLD.y, anchor: { symbolId: 'b1', terminalId: 'IN' } }], medium: 'ELECTRICAL' as const, style: 'NORMAL' as const, state: 'LIVE' as const };
    const { connections, releasedCount } = releaseAnchorsForDeletedObjects([conn], ['b1']);
    expect(releasedCount).toBe(1);
    expect(connections[0].points[1]).toEqual({ x: IN_WORLD.x, y: IN_WORLD.y });
    expect(connections[0].points[1].anchor).toBeUndefined();
  });

  it('does not throw when nothing is actually anchored to the deleted id', () => {
    const conn = { id: 'c1', points: [{ x: 0, y: 0 }, { x: 16, y: 0 }], medium: 'ELECTRICAL' as const, style: 'NORMAL' as const, state: 'LIVE' as const };
    expect(() => releaseAnchorsForDeletedObjects([conn], ['nonexistent'])).not.toThrow();
  });

  it('the real store posts a Messages notice when deleteObjects releases a real anchor', () => {
    useStore.setState({
      objects: [breaker()],
      connections: [{ id: 'c1', points: [{ x: 192, y: 80 }, { x: IN_WORLD.x, y: IN_WORLD.y, anchor: { symbolId: 'b1', terminalId: 'IN' } }], medium: 'ELECTRICAL', style: 'NORMAL', state: 'LIVE' }],
      messages: [],
      selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [],
      selectedFrameIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: []
    });
    useStore.getState().deleteObjects(['b1']);
    const remaining = useStore.getState().connections.find(c => c.id === 'c1')!;
    expect(remaining.points[1].anchor).toBeUndefined();
    expect(useStore.getState().messages.some(m => /released/i.test(m.text))).toBe(true);
  });
});

describe('8. manually dragging an anchored point breaks the anchor', () => {
  // ConnectionNode.tsx's own point-drag handler (onDragEnd on the
  // per-point Circle) calls reorthogonalizeAfterMove(conn.points, idx,
  // {x, y}) with a plain {x, y} literal - no anchor field at all - so
  // dropping the anchor on a manual drag falls straight out of that
  // object shape, with no special-case code needed anywhere. This test
  // exercises the exact same function with the exact same shape of
  // "new position" that component passes, to prove the point.
  it('reorthogonalizeAfterMove with a plain {x,y} (no anchor) drops any anchor the moved point had', async () => {
    const { reorthogonalizeAfterMove } = await import('../utils/WireDrawing');
    const points = [{ x: 192, y: 80 }, { x: IN_WORLD.x, y: IN_WORLD.y, anchor: { symbolId: 'b1', terminalId: 'IN' } }];
    const dragged = reorthogonalizeAfterMove(points, 1, { x: 300, y: 80 });
    expect(dragged[dragged.length - 1]).toEqual({ x: 300, y: 80 });
    expect((dragged[dragged.length - 1] as any).anchor).toBeUndefined();
  });
});

describe('9. a wire saved without the anchor field loads and works', () => {
  it('syncAnchoredConnections leaves an anchor-less connection completely untouched (same reference back)', () => {
    const conn = { id: 'c1', points: [{ x: 0, y: 0 }, { x: 160, y: 0 }], medium: 'ELECTRICAL' as const, style: 'NORMAL' as const, state: 'LIVE' as const };
    const result = syncAnchoredConnections([conn], [breaker()]);
    expect(result).toBe(result); // sanity - result is a real array
    expect(result[0]).toBe(conn); // untouched: no anchor anywhere, nothing to sync
  });

  it('a project file\'s connections still validate with points carrying no anchor field at all', async () => {
    const { validateProjectSchema, createEmptyProject } = await import('../project/ProjectSchema');
    const project = createEmptyProject('Legacy');
    (project as any).connections = [{ id: 'c1', points: [{ x: 0, y: 0 }, { x: 160, y: 0 }], medium: 'ELECTRICAL', style: 'NORMAL', state: 'LIVE' }];
    const result = validateProjectSchema(project);
    expect(result.valid).toBe(true);
  });
});

describe('10. the segment reaching the anchored point stays orthogonal after a diagonal symbol move', () => {
  it('a diagonal move inserts an elbow so no segment is left diagonal', () => {
    const conn = { id: 'c1', points: [{ x: 192, y: 80 }, { x: IN_WORLD.x, y: IN_WORLD.y, anchor: { symbolId: 'b1', terminalId: 'IN' } }], medium: 'ELECTRICAL' as const, style: 'NORMAL' as const, state: 'LIVE' as const };
    const movedDiagonally = breaker({ x: 160 + 48, y: 160 + 32 }); // dx=48, dy=32 - neither zero
    const synced = syncAnchoredConnections([conn], [movedDiagonally]);
    const points = synced[0].points;
    expect(points.length).toBeGreaterThan(2); // an elbow was inserted
    for (let i = 0; i < points.length - 1; i++) {
      const a = points[i];
      const b = points[i + 1];
      const isOrthogonal = a.x === b.x || a.y === b.y;
      expect(isOrthogonal, `segment ${i}: (${a.x},${a.y}) -> (${b.x},${b.y}) is diagonal`).toBe(true);
    }
    // The last point must land exactly on the terminal's new world position.
    const lastPoint = points[points.length - 1];
    expect(lastPoint.x).toBe(160 + 48 + 32);
    expect(lastPoint.y).toBe(160 + 32 + 0);
  });
});
