import { describe, it, expect } from 'vitest';
import {
  snapPointToGrid, appendWirePoint, removeLastWirePoint,
  reorthogonalizeAfterMove, insertBendOnSegment, nearestPointOnPolyline
} from '../utils/WireDrawing';
import { GRID_SIZE } from '../theme/ScadaTheme';

describe('snapPointToGrid', () => {
  it('rounds both coordinates to the nearest grid node', () => {
    expect(snapPointToGrid(37, 40)).toEqual({ x: 32, y: 48 });
  });

  it('leaves an already-aligned point untouched', () => {
    expect(snapPointToGrid(32, 64)).toEqual({ x: 32, y: 64 });
  });
});

describe('appendWirePoint', () => {
  it('the first point just starts the wire', () => {
    expect(appendWirePoint([], { x: 16, y: 16 })).toEqual([{ x: 16, y: 16 }]);
  });

  it('a horizontally-aligned next point is appended directly, no bend inserted', () => {
    const points = appendWirePoint([{ x: 0, y: 0 }], { x: 64, y: 0 });
    expect(points).toEqual([{ x: 0, y: 0 }, { x: 64, y: 0 }]);
  });

  it('a vertically-aligned next point is appended directly, no bend inserted', () => {
    const points = appendWirePoint([{ x: 0, y: 0 }], { x: 0, y: 64 });
    expect(points).toEqual([{ x: 0, y: 0 }, { x: 0, y: 64 }]);
  });

  it('a diagonal next point gets one automatic right-angle bend inserted - the segment is never diagonal', () => {
    const points = appendWirePoint([{ x: 0, y: 0 }], { x: 64, y: 32 });
    expect(points.length).toBe(3);
    // Every consecutive pair shares an x or a y - no diagonal segment.
    for (let i = 0; i < points.length - 1; i++) {
      const a = points[i];
      const b = points[i + 1];
      expect(a.x === b.x || a.y === b.y).toBe(true);
    }
    expect(points[points.length - 1]).toEqual({ x: 64, y: 32 });
  });

  it('does not add a zero-length segment for a repeated point', () => {
    const points = appendWirePoint([{ x: 0, y: 0 }], { x: 0, y: 0 });
    expect(points).toEqual([{ x: 0, y: 0 }]);
  });
});

describe('removeLastWirePoint', () => {
  it('drops the last point, undoing the most recent bend', () => {
    expect(removeLastWirePoint([{ x: 0, y: 0 }, { x: 16, y: 0 }, { x: 16, y: 16 }])).toEqual([{ x: 0, y: 0 }, { x: 16, y: 0 }]);
  });

  it('an empty or single-point list has nothing more to undo, without throwing', () => {
    expect(() => removeLastWirePoint([])).not.toThrow();
    expect(removeLastWirePoint([{ x: 0, y: 0 }])).toEqual([]);
  });
});

describe('reorthogonalizeAfterMove', () => {
  it('moving an interior bend to a position that keeps both neighbors aligned needs no extra points', () => {
    const points = [{ x: 0, y: 0 }, { x: 32, y: 0 }, { x: 32, y: 32 }];
    // Slide the bend along the same horizontal/vertical lines it already sits on.
    const result = reorthogonalizeAfterMove(points, 1, { x: 32, y: 0 });
    expect(result).toEqual(points);
  });

  it('dragging a bend off both of its neighbors still yields a fully orthogonal wire', () => {
    const points = [{ x: 0, y: 0 }, { x: 32, y: 0 }, { x: 32, y: 32 }];
    const result = reorthogonalizeAfterMove(points, 1, { x: 64, y: 64 });
    for (let i = 0; i < result.length - 1; i++) {
      const a = result[i];
      const b = result[i + 1];
      expect(a.x === b.x || a.y === b.y).toBe(true);
    }
    // The endpoints (indices not moved) are untouched.
    expect(result[0]).toEqual({ x: 0, y: 0 });
    expect(result[result.length - 1]).toEqual({ x: 32, y: 32 });
  });

  it('moving an endpoint only fixes the one segment touching it', () => {
    const points = [{ x: 0, y: 0 }, { x: 32, y: 0 }];
    const result = reorthogonalizeAfterMove(points, 1, { x: 32, y: 48 });
    // Already aligned (shares x=32 with itself trivially not relevant) - here x differs from point 0's x (0) and y differs, so a bend is needed between 0 and the new point.
    for (let i = 0; i < result.length - 1; i++) {
      const a = result[i];
      const b = result[i + 1];
      expect(a.x === b.x || a.y === b.y).toBe(true);
    }
  });
});

describe('insertBendOnSegment', () => {
  it('inserts a new point in the middle of the given segment', () => {
    const points = [{ x: 0, y: 0 }, { x: 64, y: 0 }];
    const result = insertBendOnSegment(points, 0, { x: 32, y: 0 });
    expect(result).toEqual([{ x: 0, y: 0 }, { x: 32, y: 0 }, { x: 64, y: 0 }]);
  });

  it('an out-of-range segment index is a no-op', () => {
    const points = [{ x: 0, y: 0 }, { x: 64, y: 0 }];
    expect(insertBendOnSegment(points, 5, { x: 32, y: 0 })).toEqual(points);
    expect(insertBendOnSegment(points, -1, { x: 32, y: 0 })).toEqual(points);
  });
});

describe('nearestPointOnPolyline', () => {
  it('finds the closest point on a horizontal segment, clamped to its ends and snapped to the grid', () => {
    const points = [{ x: 0, y: 0 }, { x: 320, y: 0 }];
    const result = nearestPointOnPolyline(points, { x: 163, y: 5 });
    expect(result).not.toBeNull();
    expect(result!.segmentIndex).toBe(0);
    expect(result!.point.y).toBe(0);
    expect(result!.point.x % GRID_SIZE).toBe(0);
  });

  it('clamps to the segment endpoint when the target is beyond it', () => {
    const points = [{ x: 0, y: 0 }, { x: 100, y: 0 }];
    const result = nearestPointOnPolyline(points, { x: 500, y: 0 });
    expect(result!.point.x).toBeLessThanOrEqual(100);
  });

  it('a wire with fewer than 2 points has no segment to find a point on', () => {
    expect(nearestPointOnPolyline([{ x: 0, y: 0 }], { x: 10, y: 10 })).toBeNull();
    expect(nearestPointOnPolyline([], { x: 10, y: 10 })).toBeNull();
  });

  it('picks the correct segment out of several on a multi-bend wire', () => {
    const points = [{ x: 0, y: 0 }, { x: 0, y: 100 }, { x: 100, y: 100 }];
    const result = nearestPointOnPolyline(points, { x: 60, y: 98 });
    expect(result!.segmentIndex).toBe(1); // the second segment, the horizontal one
  });
});
