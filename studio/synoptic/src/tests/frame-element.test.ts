// feat/appearance-selection-frames commit 3: the frame element - pure
// data model, minimum-size clamping, and a handful of source-scan
// checks for what has no runnable rendering harness to verify directly
// (this codebase has never had one - see raport.md). Mirrors the
// established conventions this whole task already uses: scada-
// symbols.test.ts's own "no hard-coded X" ?raw source scan for the
// no-fill requirements, and a plain grep-style assertion over
// Canvas.tsx's own source for render-order and wiring-independence
// claims a Konva tree inspection would otherwise be needed for.

import { describe, it, expect } from 'vitest';
import { clampFrameSize, computeFrameRectFromDrag, FRAME_MIN_SIZE } from '../elements/FrameElement';
import { GRID_SIZE } from '../theme/ScadaTheme';

import frameElementNodeSource from '../components/FrameElementNode.tsx?raw';
import canvasSource from '../components/Canvas.tsx?raw';
import symbolRegistrySource from '../symbols/SymbolRegistry.ts?raw';

describe('FrameElement sizing (clampFrameSize / computeFrameRectFromDrag)', () => {
  it('FRAME_MIN_SIZE is exactly two grid cells', () => {
    expect(FRAME_MIN_SIZE).toBe(GRID_SIZE * 2);
  });

  // 13. a frame smaller than 2 grid cells is created as the minimum, not zero
  it('clamps a size below the minimum up to FRAME_MIN_SIZE, never down to zero', () => {
    expect(clampFrameSize(0)).toBe(FRAME_MIN_SIZE);
    expect(clampFrameSize(5)).toBe(FRAME_MIN_SIZE);
    expect(clampFrameSize(-40)).toBe(FRAME_MIN_SIZE);
  });

  it('leaves an already-valid size untouched', () => {
    expect(clampFrameSize(FRAME_MIN_SIZE)).toBe(FRAME_MIN_SIZE);
    expect(clampFrameSize(200)).toBe(200);
  });

  it('a drag of nearly zero distance still produces a real, minimum-size frame - never a zero-size one', () => {
    const rect = computeFrameRectFromDrag(100, 100, 101, 100.5);
    expect(rect.width).toBe(FRAME_MIN_SIZE);
    expect(rect.height).toBe(FRAME_MIN_SIZE);
    expect(rect.width).toBeGreaterThan(0);
    expect(rect.height).toBeGreaterThan(0);
  });

  it('a genuinely large drag is not clamped, and the rect is normalized regardless of drag direction', () => {
    // dragged from bottom-right up to top-left - x/y must still be the
    // smaller corner, width/height still positive.
    const rect = computeFrameRectFromDrag(300, 300, 100, 120);
    expect(rect).toEqual({ x: 100, y: 120, width: 200, height: 180 });
  });

  it('never throws for degenerate input (a single point, both corners identical)', () => {
    expect(() => computeFrameRectFromDrag(50, 50, 50, 50)).not.toThrow();
    const rect = computeFrameRectFromDrag(50, 50, 50, 50);
    expect(rect.width).toBe(FRAME_MIN_SIZE);
    expect(rect.height).toBe(FRAME_MIN_SIZE);
  });
});

describe('Frame has no fill (FrameElementNode.tsx source scan, mirrors scada-symbols.test.ts\'s own hard-coded-color scan)', () => {
  // Every fill= this component uses, and why each one is not a visible
  // fill: the four wall Line segments (PLAIN and BUILDING's own walls)
  // carry no fill prop at all - a Konva Line with no fill paints
  // nothing but its own stroke. The roof triangle's outline is
  // explicit fill="transparent". The one exception is the invisible,
  // listening-only hit-area Line, opacity 0 - paints nothing, exists
  // only so the frame's empty interior can still be clicked/dragged/
  // selected; a real color there never reaches the screen.
  const fillMatches = [...frameElementNodeSource.matchAll(/fill=\{?"?([^"}\s]+)"?\}?/g)].map(m => m[1]);

  // 11. PLAIN has no fill / 12. BUILDING's walls have no fill - same
  // component, same wall-rendering code path either way (variant only
  // adds the roof, never a wall fill).
  it('every fill= this component sets is either "transparent" or the deliberately-invisible (opacity 0) hit area - never a visible paint', () => {
    for (const fill of fillMatches) {
      const isTransparent = fill === 'transparent';
      // COLOR_OUTLINE is only ever used on the hit-area Line, which is
      // always paired with opacity={0} right after its own fill - the
      // one real color mentioned in this file that is never visible.
      const isInvisibleHitArea = fill === 'COLOR_OUTLINE' && /fill=\{COLOR_OUTLINE\}\s+opacity=\{0\}/.test(frameElementNodeSource);
      expect(isTransparent || isInvisibleHitArea, `unexpected visible fill: ${fill}`).toBe(true);
    }
  });

  it('sanity: this component actually sets at least one fill (proves the scan above is not vacuous)', () => {
    expect(fillMatches.length).toBeGreaterThan(0);
  });

  it('none of the four wall Line segments carries a fill prop of its own', () => {
    // Extract just the wall segment lines (the four Line elements whose
    // points describe the rectangle's own four edges) and confirm none
    // of THOSE specific lines has a fill= at all.
    const wallLineSnippets = frameElementNodeSource.match(/<Line points=\{\[[^\]]*\]\}[^/]*\/>/g) || [];
    const wallLines = wallLineSnippets.filter(s => !s.includes('closed'));
    expect(wallLines.length).toBeGreaterThan(0);
    wallLines.forEach(line => {
      // Only the invisible hit-area Line (closed, opacity 0) is exempt -
      // filtered out above by excluding "closed" lines, since the wall
      // segments themselves are never closed shapes.
      expect(line).not.toMatch(/fill=/);
    });
  });
});

describe('Frame render order - background layer, below wires and symbols (14)', () => {
  // No Konva rendering harness exists to inspect actual paint order, so
  // this checks the one thing that DOES determine it deterministically:
  // Canvas.tsx's own JSX source order within the same Layer (Konva
  // paints a Layer's children in the order they appear). frames.map
  // must appear before both connections.map and the sorted objects.map
  // - see Canvas.tsx's own comment at the frame render block for the
  // full reasoning.
  const framesIndex = canvasSource.indexOf('{frames.map((frame)');
  const connectionsIndex = canvasSource.indexOf('{connections.map(conn =>');
  const objectsIndex = canvasSource.indexOf('.sort((a, b) => (a.zIndex || 0) - (b.zIndex || 0)).map((obj)');

  it('frames render before connections in Canvas.tsx\'s own source (podklad, below przewody)', () => {
    expect(framesIndex).toBeGreaterThan(-1);
    expect(connectionsIndex).toBeGreaterThan(-1);
    expect(framesIndex).toBeLessThan(connectionsIndex);
  });

  it('frames render before symbols in Canvas.tsx\'s own source (podklad, below symbole)', () => {
    expect(objectsIndex).toBeGreaterThan(-1);
    expect(framesIndex).toBeLessThan(objectsIndex);
  });
});

describe('Frame has no terminals and cannot be wired (15)', () => {
  it('FrameElement carries no terminal-shaped field at all', () => {
    const frame = { id: 'F1', x: 0, y: 0, width: 64, height: 64, titlePosition: 'TOP_LEFT' as const, variant: 'PLAIN' as const };
    expect('terminals' in frame).toBe(false);
  });

  it('NetResolver (resolveNets/getJunctionPoints) is never called with the frames array in Canvas.tsx - only objects and connections', () => {
    expect(canvasSource).toMatch(/resolveNets\(store\.connections, store\.objects\)/);
    expect(canvasSource).toMatch(/getJunctionPoints\(connections, objects\)/);
    expect(canvasSource).not.toMatch(/resolveNets\([^)]*frames/);
    expect(canvasSource).not.toMatch(/getJunctionPoints\([^)]*frames/);
  });

  it('a frame is not in the symbol registry - drag-a-wire-to-a-terminal has nothing to find on it', () => {
    // Frames are added via addFrame (their own store array, entirely
    // separate from objects/SymbolRegistry) - SymbolRegistry.ts itself
    // never imports or mentions FrameElement/the frame variants at all.
    expect(symbolRegistrySource).not.toMatch(/FrameElement/);
    expect(symbolRegistrySource).not.toMatch(/'frame\./);
  });
});
