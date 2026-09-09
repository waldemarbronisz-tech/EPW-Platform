// feat/site-objects-2d commit 4 - mandatory test 8: grass texture is
// deterministic (two calls with the same size give an identical
// result). Tests the pure functions in SurfaceGeometry.ts directly -
// GrassSymbol.tsx/ConcreteRoadSymbol.tsx only ever call these and draw
// whatever they return, so this is the real, load-bearing check; no
// Konva/DOM rendering needed, same "test the pure function, not the
// Konva tree" convention as banded-shading.test.tsx.

import { describe, it, expect } from 'vitest';
import { computeGrassDashes, computeRoadJoints, computeRoadDashes } from '../symbols/site/SurfaceGeometry';

describe('8. grass texture is deterministic', () => {
  it('two calls with the SAME width/height give byte-identical results', () => {
    const a = computeGrassDashes(320, 240);
    const b = computeGrassDashes(320, 240);
    expect(a).toEqual(b);
    expect(a.length).toBeGreaterThan(0);
  });

  it('a different size is not required to match, and in practice does not (sanity: the result actually depends on size, not a constant)', () => {
    const small = computeGrassDashes(128, 96);
    const large = computeGrassDashes(512, 384);
    expect(small).not.toEqual(large);
    // Larger area -> more dashes (density-based, not a fixed count
    // stretched to fit) - GRASS_DASH_DENSITY in SurfaceGeometry.ts.
    expect(large.length).toBeGreaterThan(small.length);
  });

  it('every dash stays within the surface bounds (a margin inset from each edge)', () => {
    const dashes = computeGrassDashes(200, 150);
    dashes.forEach(d => {
      expect(d.x).toBeGreaterThanOrEqual(0);
      expect(d.x).toBeLessThanOrEqual(200);
      expect(d.y).toBeGreaterThanOrEqual(0);
      expect(d.y).toBeLessThanOrEqual(150);
    });
  });

  it('a degenerate (near-zero) size never throws and never returns a negative count', () => {
    expect(() => computeGrassDashes(1, 1)).not.toThrow();
    expect(computeGrassDashes(1, 1).length).toBeGreaterThanOrEqual(0);
  });
});

// Same "pure function of width alone" shape for the concrete road's own
// (fully deterministic, no randomness at all) joint/dash layout - not
// one of the 14 mandatory tests by number, but the same load-bearing
// logic PRZED ZGLOSZENIEM's own checklist relies on ("stretch it -
// texture spreads evenly" applies to the road's slabs/dashes too).
describe('concrete road slab joints and lane-marking dashes', () => {
  it('two calls with the same width give identical joint positions', () => {
    expect(computeRoadJoints(300)).toEqual(computeRoadJoints(300));
  });

  it('a wider road gets more slab joints, not the same two stretched apart', () => {
    expect(computeRoadJoints(600).length).toBeGreaterThan(computeRoadJoints(150).length);
  });

  it('two calls with the same width give identical dash layouts', () => {
    expect(computeRoadDashes(300)).toEqual(computeRoadDashes(300));
  });

  it('a wider road gets more lane-marking dashes, at the same dash length', () => {
    const narrow = computeRoadDashes(150);
    const wide = computeRoadDashes(600);
    expect(wide.length).toBeGreaterThan(narrow.length);
    narrow.concat(wide).forEach(d => expect(d.x2 - d.x1).toBe(12));
  });
});
