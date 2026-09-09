// feat/wire-routing-around-obstacles commit 1 - the 9 mandatory tests
// for wire/obstacle collision detection (WireCollision.ts).

import { describe, it, expect } from 'vitest';
import type { SynopticObject, SynopticConnection } from '../store';
import { getObstacles, segmentHitsObstacle, findCollisions } from '../project/WireCollision';
import type { Screen } from '../project/WireCollision';
import type { MeterElement } from '../meter/MeterElement';
import type { FrameElement } from '../elements/FrameElement';

function breaker(overrides: Partial<SynopticObject> = {}): SynopticObject {
  return {
    id: 'b1', type: 'electrical.circuit_breaker', category: 'Electrical',
    x: 100, y: 100, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 0,
    tag: '', description: '', color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
    customProperties: {}, width: 64, height: 64,
    ...overrides
  } as SynopticObject;
}

function grass(overrides: Partial<SynopticObject> = {}): SynopticObject {
  return {
    id: 'g1', type: 'site.grass', category: 'TEREN',
    x: 100, y: 100, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 0,
    tag: '', description: '', color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
    customProperties: {}, width: 128, height: 96,
    ...overrides
  } as SynopticObject;
}

function wire(points: SynopticConnection['points']): SynopticConnection {
  return { id: 'w1', medium: 'ELECTRICAL', style: 'NORMAL', points };
}

describe('1. a segment passing through the center of an obstacle is detected', () => {
  it('vertical segment straight through a breaker at (100,100,64,64)', () => {
    const obstacles = getObstacles({ objects: [breaker()] });
    const collision = segmentHitsObstacle({ x: 132, y: 50 }, { x: 132, y: 250 }, obstacles[0]);
    expect(collision).toBe(true);
  });
});

describe('2. a segment passing two grid cells clear of an obstacle is NOT detected', () => {
  it('vertical segment at x=196 (obstacle right edge 164 + 32) never touches it', () => {
    const obstacles = getObstacles({ objects: [breaker()] });
    expect(segmentHitsObstacle({ x: 196, y: 50 }, { x: 196, y: 250 }, obstacles[0])).toBe(false);
  });
});

describe('3. a segment running right along an obstacle\'s own edge is NOT detected, thanks to the margin', () => {
  it('vertical segment at x=100 (the breaker\'s own unshrunk left edge) misses the shrunk obstacle rect', () => {
    const obstacles = getObstacles({ objects: [breaker()] });
    expect(obstacles[0].x).toBeGreaterThan(100); // sanity: the obstacle really was shrunk inward
    expect(segmentHitsObstacle({ x: 100, y: 50 }, { x: 100, y: 250 }, obstacles[0])).toBe(false);
  });
});

describe('4. the symbol a wire is anchored to is never an obstacle for that same wire', () => {
  it('excluding the anchored symbol\'s id removes it from the obstacle list entirely', () => {
    const obj = breaker();
    const withoutExclusion = getObstacles({ objects: [obj] });
    const withExclusion = getObstacles({ objects: [obj] }, [obj.id]);
    expect(withoutExclusion.length).toBe(1);
    expect(withExclusion.length).toBe(0);
  });

  it('a wire ending inside the valve it is anchored to reports no collision once excluded', () => {
    const obj = breaker();
    const w = wire([{ x: 50, y: 132 }, { x: 132, y: 132, anchor: { symbolId: obj.id, terminalId: 'IN' } }]);
    const obstacles = getObstacles({ objects: [obj] }, [obj.id]);
    expect(findCollisions(w, obstacles)).toEqual([]);
  });
});

describe('5. grass and concrete road are never obstacles', () => {
  it('site.grass is dropped entirely (isSurface), even though a segment runs straight through it', () => {
    const obstacles = getObstacles({ objects: [grass()] });
    expect(obstacles).toEqual([]);
  });
});

describe('6. a meter IS an obstacle', () => {
  it('a wire crossing a meter\'s own rectangle collides', () => {
    const meter: MeterElement = { id: 'm1', x: 100, y: 100, width: 120, title: 'Test', fontSize: 13, rows: [{ device: '', label: 'Row', manualValue: '1', manualUnit: 'V' }] };
    const screen: Screen = { objects: [], meters: [meter] };
    const obstacles = getObstacles(screen);
    expect(obstacles.length).toBe(1);
    const w = wire([{ x: 130, y: 50 }, { x: 130, y: 200 }]);
    expect(findCollisions(w, obstacles).length).toBe(1);
  });
});

describe('7. a frame IS an obstacle', () => {
  it('a wire crossing a frame\'s own rectangle collides', () => {
    const frame: FrameElement = { id: 'f1', x: 100, y: 100, width: 80, height: 80, titlePosition: 'TOP_LEFT', variant: 'PLAIN' };
    const screen: Screen = { objects: [], frames: [frame] };
    const obstacles = getObstacles(screen);
    expect(obstacles.length).toBe(1);
    const w = wire([{ x: 140, y: 50 }, { x: 140, y: 200 }]);
    expect(findCollisions(w, obstacles).length).toBe(1);
  });
});

describe('8. a three-segment polyline with exactly one colliding segment returns exactly one collision', () => {
  it('one segment straight through the obstacle, the other two well clear of it', () => {
    const obstacles = getObstacles({ objects: [breaker()] }); // shrunk rect roughly x:108-156, y:108-156
    const w = wire([
      { x: 0, y: 132 },
      { x: 200, y: 132 }, // collides - horizontal, fully crosses the obstacle's x-range at y=132 (inside 108-156)
      { x: 200, y: 300 }, // clear - vertical at x=200, past the obstacle's right edge (156)
      { x: 400, y: 300 }  // clear - horizontal at y=300, past the obstacle's bottom edge (156)
    ]);
    const collisions = findCollisions(w, obstacles);
    expect(collisions.length).toBe(1);
    expect(collisions[0].segmentIndex).toBe(0);
  });
});

describe('9. an empty screen with no obstacles returns an empty list, never an exception', () => {
  it('getObstacles on an empty screen', () => {
    expect(getObstacles({ objects: [] })).toEqual([]);
  });

  it('findCollisions against no obstacles at all', () => {
    const w = wire([{ x: 0, y: 0 }, { x: 100, y: 0 }]);
    expect(() => findCollisions(w, [])).not.toThrow();
    expect(findCollisions(w, [])).toEqual([]);
  });
});
