import { describe, it, expect } from 'vitest';
import { getPortWorldDirection, getAbsolutePortPosition } from '../utils/GeometryUtils';

describe('Geometry Utils - Port Transformations', () => {
  const testObj = {
    id: 'test1',
    type: 'dummy',
    x: 100,
    y: 100,
    width: 40,
    height: 40,
    scaleX: 1,
    scaleY: 1,
    rotation: 0
  } as any;

  const topPort = { id: 'TOP', x: 0.5, y: 0, direction: 'passive', domain: 'electrical' } as any;


  it('calculates 0 degree absolute position correctly', () => {
    const pos = getAbsolutePortPosition(testObj, topPort);
    expect(pos.x).toBe(120);
    expect(pos.y).toBe(100);
  });

  it('calculates 90 degree absolute position correctly', () => {
    const rotatedObj = { ...testObj, rotation: 90 };
    const pos = getAbsolutePortPosition(rotatedObj, topPort);
    // Rotating around (120, 120).
    // top port is (120, 100) unrotated.
    // 90 deg clockwise puts it at (140, 120)
    expect(Math.round(pos.x)).toBe(140);
    expect(Math.round(pos.y)).toBe(120);
  });

  it('calculates 0 degree port direction correctly', () => {
    const dir = getPortWorldDirection(testObj, topPort);
    expect(dir.x).toBe(0);
    expect(dir.y).toBe(-1); // pointing up
  });

  it('calculates 90 degree port direction correctly', () => {
    const rotatedObj = { ...testObj, rotation: 90 };
    const dir = getPortWorldDirection(rotatedObj, topPort);
    expect(dir.x).toBe(1); // pointing right
    expect(dir.y).toBe(0);
  });
});
