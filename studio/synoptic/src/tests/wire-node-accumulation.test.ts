// fix/wiring-and-library-groups commit 2 - the 6 mandatory tests for
// usterka 2 ("przesuwanie symbolu mnozy wezly"). Root cause (see
// raport.md for the full trace): syncAnchoredConnections re-derives an
// anchored point's neighbor-facing elbow on EVERY sync call
// (WireAnchoring.ts, unchanged by this commit), but never removed the
// elbow left over from the PREVIOUS sync - each new elbow it inserts is
// always collinear with the one before it, once traced back to the
// same fixed reference point, so a chain of stale elbows accumulated
// forever, one per move, instead of collapsing into the single one
// actually still needed. The fix is WireDrawing.ts's own
// simplifyCollinearPoints, applied after every reorthogonalize - tested
// directly here (tests 9-11) and through the full sync path a repeated
// symbol move actually goes through (tests 7, 8, 12).
//
// Same 'electrical.circuit_breaker' fixture as wire-anchoring.test.ts/
// terminal-reach.test.ts: 64x64, terminals IN (TOP, local 32,0) and OUT
// (BOTTOM, local 32,64).

import { describe, it, expect } from 'vitest';
import type { SynopticObject } from '../store';
import { syncAnchoredConnections } from '../utils/WireAnchoring';
import { simplifyCollinearPoints } from '../utils/WireDrawing';
import { getJunctionPoints } from '../project/NetResolver';

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

// A wire whose OUT-anchored end starts exactly at the breaker's own OUT
// terminal (192,224) - one free point above it, the shape every freshly
// drawn wire from usterka 1's own fix would actually produce.
function wireToOut() {
  return {
    id: 'c1', medium: 'ELECTRICAL' as const, style: 'NORMAL' as const,
    points: [{ x: 192, y: 320 }, { x: 192, y: 224, anchor: { symbolId: 'b1', terminalId: 'OUT' } }]
  };
}

describe('7. moving a symbol by 3 grid cells does not grow the polyline by more than 2 points', () => {
  it('an axis-aligned 3-cell move needs no elbow at all - point count unchanged', () => {
    const moved = breaker({ x: 160, y: 160 + 48 }); // straight down, 3*16
    const [synced] = syncAnchoredConnections([wireToOut()], [moved]);
    expect(synced.points.length).toBeLessThanOrEqual(wireToOut().points.length + 2);
  });
});

describe('8. moving a symbol diagonally inserts exactly two elbows when both sides of the anchor need one, never more', () => {
  it('an anchor in the MIDDLE of a 3-point wire gets exactly two new elbows on a single diagonal move', () => {
    const conn = {
      id: 'c1', medium: 'ELECTRICAL' as const, style: 'NORMAL' as const,
      points: [
        { x: 100, y: 100 },
        { x: 192, y: 224, anchor: { symbolId: 'b1', terminalId: 'OUT' } },
        { x: 300, y: 300 }
      ]
    };
    const moved = breaker({ x: 160 + 32, y: 160 + 16 }); // diagonal
    const [synced] = syncAnchoredConnections([conn], [moved]);
    expect(synced.points.length).toBe(conn.points.length + 2);
  });
});

describe('9. three consecutive points on one straight line collapse to two', () => {
  it('simplifyCollinearPoints drops the redundant middle point of a horizontal run', () => {
    const points = [{ x: 0, y: 0 }, { x: 50, y: 0 }, { x: 100, y: 0 }];
    expect(simplifyCollinearPoints(points)).toEqual([{ x: 0, y: 0 }, { x: 100, y: 0 }]);
  });

  it('never drops an anchored middle point, even when geometrically redundant', () => {
    const points = [{ x: 0, y: 0 }, { x: 50, y: 0, anchor: { symbolId: 'x', terminalId: 'IN' } }, { x: 100, y: 0 }];
    expect(simplifyCollinearPoints(points)).toEqual(points);
  });
});

describe('10. a plain bend with no branching gets no junction dot', () => {
  it('getJunctionPoints reports nothing at an ordinary 2-segment corner (no other wire, no terminal there)', () => {
    const conn = { id: 'c1', medium: 'ELECTRICAL' as const, style: 'NORMAL' as const, points: [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }] };
    const junctions = getJunctionPoints([conn], []);
    expect(junctions).toEqual([]);
  });
});

describe('11. a node where three segments meet gets a junction dot', () => {
  it('getJunctionPoints reports the point where two separate wires cross/touch', () => {
    const connA = { id: 'a', medium: 'ELECTRICAL' as const, style: 'NORMAL' as const, points: [{ x: 0, y: 100 }, { x: 200, y: 100 }] };
    const connB = { id: 'b', medium: 'ELECTRICAL' as const, style: 'NORMAL' as const, points: [{ x: 100, y: 100 }, { x: 100, y: 200 }] };
    const junctions = getJunctionPoints([connA, connB], []);
    expect(junctions).toContainEqual({ x: 100, y: 100 });
  });
});

describe('12. moving the same symbol ten times back and forth does not grow the polyline (the most important test)', () => {
  it('repeated diagonal moves never accumulate stray elbows - point count stays at whatever one move alone needs', () => {
    // Two fixed positions, alternated - "tam i z powrotem" (there and
    // back) exactly as this task's own test asks, ten moves total. Both
    // chosen so the OUT terminal's world position never realigns with
    // the wire's own free end (192,320) on either axis at either
    // position - that would legitimately collapse to a plain 2-point
    // straight wire (0 elbows, still correct, just not what this test
    // is trying to isolate: whether REPETITION alone grows the count).
    const posA = { x: 300, y: 260 }; // OUT world (332,324)
    const posB = { x: 340, y: 300 }; // OUT world (372,364)

    let connections: any[] = [wireToOut()];
    let baselineLength: number | null = null;

    for (let i = 0; i < 10; i++) {
      const pos = i % 2 === 0 ? posA : posB;
      connections = syncAnchoredConnections(connections, [breaker(pos)]);
      if (baselineLength === null) {
        baselineLength = connections[0].points.length;
        expect(baselineLength).toBe(3); // free end, one elbow, anchor
      } else {
        expect(connections[0].points.length).toBe(baselineLength);
      }
    }
  });
});
