// feat/wire-routing-around-obstacles commit 2 - the 7 mandatory tests
// for orthogonal obstacle-avoiding routing (WireRouter.ts).

import { describe, it, expect } from 'vitest';
import type { WirePoint } from '../store';
import { routeAround } from '../project/WireRouter';
import type { Obstacle } from '../project/WireCollision';
import { findCollisions } from '../project/WireCollision';

const GRID = 16;

function countBends(points: WirePoint[]): number {
  let bends = 0;
  for (let i = 1; i < points.length - 1; i++) {
    const prevDir = points[i].x === points[i - 1].x ? 'V' : 'H';
    const nextDir = points[i + 1].x === points[i].x ? 'V' : 'H';
    if (prevDir !== nextDir) bends++;
  }
  return bends;
}

function isOrthogonal(points: WirePoint[]): boolean {
  for (let i = 0; i < points.length - 1; i++) {
    if (points[i].x !== points[i + 1].x && points[i].y !== points[i + 1].y) return false;
  }
  return true;
}

function onGrid(points: WirePoint[]): boolean {
  return points.every(p => p.x % GRID === 0 && p.y % GRID === 0);
}

describe('10. a route between two points with no obstacles is a straight line, no bends', () => {
  it('same y, no obstacles at all', () => {
    const route = routeAround({ x: 0, y: 80 }, { x: 192, y: 80 }, [], GRID);
    expect(route).toEqual([{ x: 0, y: 80 }, { x: 192, y: 80 }]);
    expect(countBends(route)).toBe(0);
  });
});

describe('11. a route with one obstacle directly in the way goes around it with exactly two bends', () => {
  const obstacle: Obstacle = { id: 'o1', label: 'Zawor', x: 64, y: 32, width: 64, height: 64 }; // x:64-128, y:32-96
  const start: WirePoint = { x: 0, y: 64 };
  const end: WirePoint = { x: 192, y: 64 }; // straight line at y=64 runs squarely through the obstacle

  it('exactly two bends', () => {
    const route = routeAround(start, end, [obstacle], GRID);
    expect(countBends(route)).toBe(2);
    expect(route.length).toBe(4);
  });

  it('12. the returned route never crosses the obstacle', () => {
    const route = routeAround(start, end, [obstacle], GRID);
    const wire = { id: 'w', medium: 'ELECTRICAL' as const, style: 'NORMAL' as const, points: route };
    expect(findCollisions(wire, [obstacle])).toEqual([]);
  });

  it('13. every point of the route lands on a grid node', () => {
    const route = routeAround(start, end, [obstacle], GRID);
    expect(onGrid(route)).toBe(true);
  });

  it('14. every segment of the route is horizontal or vertical', () => {
    const route = routeAround(start, end, [obstacle], GRID);
    expect(isOrthogonal(route)).toBe(true);
  });
});

describe('15. when the end point is walled in on every side, the direct route is returned, no exception', () => {
  // A closed ring of four obstacles around (496,496), no seam anywhere
  // along its own perimeter - every straight-line approach from outside
  // must cross one of the four walls.
  const walls: Obstacle[] = [
    { id: 'top', label: 'Wall', x: 464, y: 464, width: 72, height: 16 },
    { id: 'bottom', label: 'Wall', x: 464, y: 520, width: 72, height: 16 },
    { id: 'left', label: 'Wall', x: 464, y: 464, width: 16, height: 72 },
    { id: 'right', label: 'Wall', x: 520, y: 464, width: 16, height: 72 }
  ];
  const start: WirePoint = { x: 0, y: 496 };
  const end: WirePoint = { x: 496, y: 496 };

  it('never throws', () => {
    expect(() => routeAround(start, end, walls, GRID)).not.toThrow();
  });

  it('returns the direct point-to-point route (same y, so a single straight segment)', () => {
    const route = routeAround(start, end, walls, GRID);
    expect(route).toEqual([start, end]);
  });
});

describe('16. a screen with 30 obstacles still computes, within the step limit', () => {
  it('completes and returns a valid, fully orthogonal, grid-aligned route', () => {
    const obstacles: Obstacle[] = [];
    for (let i = 0; i < 30; i++) {
      obstacles.push({ id: `o${i}`, label: `Obstacle ${i}`, x: (i % 6) * 64 + 32, y: Math.floor(i / 6) * 64 + 200, width: 24, height: 24 });
    }
    const start: WirePoint = { x: 0, y: 232 };
    const end: WirePoint = { x: 400, y: 232 };
    const route = routeAround(start, end, obstacles, GRID);
    expect(route.length).toBeGreaterThanOrEqual(2);
    expect(onGrid(route)).toBe(true);
    expect(isOrthogonal(route)).toBe(true);
  });
});
