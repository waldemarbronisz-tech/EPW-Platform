import { describe, it, expect } from 'vitest';
import { calculateOrthogonalPath } from '../utils/GeometryUtils';

describe('Orthogonal Router Directions', () => {
  it('straight horizontal from right-facing port', () => {
    const path = calculateOrthogonalPath(0, 0, 100, 0, {x:1, y:0}, {x:-1, y:0});
    expect(path).toBe('M 0 0 L 100 0');
  });

  it('straight vertical from bottom-facing port', () => {
    const path = calculateOrthogonalPath(0, 0, 0, 100, {x:0, y:1}, {x:0, y:-1});
    expect(path).toBe('M 0 0 L 0 100');
  });

  it('one-bend L-shape from bottom to side', () => {
    const path = calculateOrthogonalPath(0, 0, 50, 100, {x:0, y:1}, {x:0, y:-1});
    expect(path).toBe('M 0 0 L 0 50 L 50 50 L 50 100');
  });

  it('two-bend S-shape resolving side to side (midX split)', () => {
    const path = calculateOrthogonalPath(0, 0, 100, 20, {x:1, y:0}, {x:-1, y:0});
    expect(path).toBe('M 0 0 L 50 0 L 50 20 L 100 20');
  });
});
