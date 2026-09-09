// fix/handles-insert-mode-diodes commit 1: corner/edge resize handles.
// computeResizeFromAnchor/computeWidthResizeFromAnchor are pure,
// Konva-free (same convention as GridSnap.ts/Terminals.ts/
// WireDrawing.ts) - every one of this commit's own mandatory tests is
// expressible directly against them, without a Konva rendering
// harness (this codebase has never had one - see raport.md).

import { describe, it, expect } from 'vitest';
import { computeResizeFromAnchor, computeWidthResizeFromAnchor } from '../utils/ResizeHandles';
import { useStore } from '../store';
import { GRID_SIZE } from '../theme/ScadaTheme';
import type { FrameElement } from '../elements/FrameElement';

const original = { x: 100, y: 100, width: 64, height: 64 };
const GRID = GRID_SIZE; // 16
const MIN = GRID_SIZE;  // a generic minimum for these tests - one grid cell

describe('computeResizeFromAnchor - corner handles resize both axes independently (1, 2)', () => {
  // 1. bottom-right corner dragged right and down increases width AND height
  it('bottom-right corner: dragging right and down grows width and height, each by the movement in that axis', () => {
    // dragged so the far corner moves from (164,164) to (196,212): +32 in x, +48 in y
    const result = computeResizeFromAnchor('bottom-right', original, 96, 112, GRID, MIN);
    expect(result.width).toBe(96);
    expect(result.height).toBe(112);
    // grown, not shrunk
    expect(result.width).toBeGreaterThan(original.width);
    expect(result.height).toBeGreaterThan(original.height);
  });

  // 2. bottom-right corner dragged right and UP grows width, SHRINKS height
  it('bottom-right corner: dragging right and up grows width but shrinks height', () => {
    const result = computeResizeFromAnchor('bottom-right', original, 96, 32, GRID, MIN);
    expect(result.width).toBeGreaterThan(original.width);
    expect(result.height).toBeLessThan(original.height);
    expect(result.width).toBe(96);
    expect(result.height).toBe(32);
  });

  it('top-left corner independently changes width and height too, in the opposite sense (dragging it left/up grows the shape)', () => {
    const result = computeResizeFromAnchor('top-left', original, 96, 112, GRID, MIN);
    expect(result.width).toBe(96);
    expect(result.height).toBe(112);
  });
});

describe('computeResizeFromAnchor - edge handles change exactly one axis (3, 4)', () => {
  // 3. a vertical-edge handle (left or right) never changes height
  it('middle-right (vertical edge): height is untouched regardless of rawHeight', () => {
    const result = computeResizeFromAnchor('middle-right', original, 128, 999, GRID, MIN);
    expect(result.height).toBe(original.height);
    expect(result.width).toBe(128);
  });

  it('middle-left (vertical edge): height is untouched regardless of rawHeight', () => {
    const result = computeResizeFromAnchor('middle-left', original, 128, 999, GRID, MIN);
    expect(result.height).toBe(original.height);
  });

  // 4. a horizontal-edge handle (top or bottom) never changes width
  it('bottom-center (horizontal edge): width is untouched regardless of rawWidth', () => {
    const result = computeResizeFromAnchor('bottom-center', original, 999, 128, GRID, MIN);
    expect(result.width).toBe(original.width);
    expect(result.height).toBe(128);
  });

  it('top-center (horizontal edge): width is untouched regardless of rawWidth', () => {
    const result = computeResizeFromAnchor('top-center', original, 999, 128, GRID, MIN);
    expect(result.width).toBe(original.width);
  });
});

describe('computeResizeFromAnchor - minimum size (5)', () => {
  // 5. resizing below the minimum stops exactly at the minimum, never zero or negative
  it('a corner dragged far past the minimum stops exactly at minWidth/minHeight, never zero or negative', () => {
    const result = computeResizeFromAnchor('bottom-right', original, -500, -500, GRID, MIN);
    expect(result.width).toBe(MIN);
    expect(result.height).toBe(MIN);
    expect(result.width).toBeGreaterThan(0);
    expect(result.height).toBeGreaterThan(0);
  });

  it('an edge handle dragged past the minimum in its one axis also stops at the minimum', () => {
    const result = computeResizeFromAnchor('middle-right', original, 2, 0, GRID, MIN);
    expect(result.width).toBe(MIN);
  });
});

describe('computeResizeFromAnchor - the opposite corner/edge stays fixed (6)', () => {
  it('dragging bottom-right leaves the top-left corner exactly where it was', () => {
    const result = computeResizeFromAnchor('bottom-right', original, 200, 48, GRID, MIN);
    expect(result.x).toBe(original.x);
    expect(result.y).toBe(original.y);
  });

  it('dragging top-left leaves the bottom-right corner exactly where it was', () => {
    const result = computeResizeFromAnchor('top-left', original, 200, 48, GRID, MIN);
    const originalRight = original.x + original.width;
    const originalBottom = original.y + original.height;
    expect(result.x + result.width).toBe(originalRight);
    expect(result.y + result.height).toBe(originalBottom);
  });

  it('dragging middle-left leaves the right edge (x+width) exactly fixed, top/bottom untouched', () => {
    const result = computeResizeFromAnchor('middle-left', original, 200, 999, GRID, MIN);
    const originalRight = original.x + original.width;
    expect(result.x + result.width).toBe(originalRight);
    expect(result.y).toBe(original.y);
    expect(result.height).toBe(original.height);
  });

  it('dragging top-center leaves the bottom edge (y+height) exactly fixed, left/right untouched', () => {
    const result = computeResizeFromAnchor('top-center', original, 999, 200, GRID, MIN);
    const originalBottom = original.y + original.height;
    expect(result.y + result.height).toBe(originalBottom);
    expect(result.x).toBe(original.x);
    expect(result.width).toBe(original.width);
  });

  // Even snapped to the grid, at a size the raw drag did NOT land
  // exactly on a grid line - the fixed corner must still be exact,
  // not just "close" (this is the entire reason this function exists
  // instead of snapping x/y and width/height independently).
  it('the fixed corner stays exact even when the raw size needed to be snapped', () => {
    const result = computeResizeFromAnchor('bottom-right', original, 103, 121, GRID, MIN); // not grid-aligned raw values
    expect(result.x).toBe(original.x);
    expect(result.y).toBe(original.y);
    expect(result.width % GRID).toBe(0);
    expect(result.height % GRID).toBe(0);
  });
});

describe('computeWidthResizeFromAnchor - meter/signal panel width-only resize (8)', () => {
  const originalW = { x: 200, width: 160 };

  it('dragging the right edge grows width, keeps x (left edge) fixed', () => {
    const result = computeWidthResizeFromAnchor('middle-right', originalW, 240, GRID, 120, 400);
    expect(result.width).toBe(240);
    expect(result.x).toBe(originalW.x);
  });

  it('dragging the left edge grows width, keeps the RIGHT edge fixed', () => {
    const result = computeWidthResizeFromAnchor('middle-left', originalW, 240, GRID, 120, 400);
    expect(result.width).toBe(240);
    expect(result.x + result.width).toBe(originalW.x + originalW.width);
  });

  it('clamps to the element-specific min/max width, never below min or above max', () => {
    const tooSmall = computeWidthResizeFromAnchor('middle-right', originalW, 10, GRID, 120, 400);
    expect(tooSmall.width).toBe(120);
    const tooBig = computeWidthResizeFromAnchor('middle-right', originalW, 900, GRID, 120, 400);
    expect(tooBig.width).toBe(400);
  });
});

describe('Grid snapping (part of every mandatory test above, checked directly too)', () => {
  it('every resulting width/height/x/y lands on a GRID_SIZE multiple, starting from a grid-aligned original', () => {
    const gridAligned = { x: 96, y: 96, width: 64, height: 64 };
    const result = computeResizeFromAnchor('bottom-right', gridAligned, 130, 170, GRID, MIN);
    expect(result.x % GRID).toBe(0);
    expect(result.y % GRID).toBe(0);
    expect(result.width % GRID).toBe(0);
    expect(result.height % GRID).toBe(0);
  });
});

// 7. a resize is exactly one history entry - verified at the store
// level the same way moveSelectionBy's own one-entry-per-call test
// already does (selection-and-keyboard.test.ts): the resize handlers
// (ObjectNode/FrameElementNode/MeterElementNode/SignalPanelElementNode's
// own onTransformEnd, wired in Canvas.tsx) all call the element's own
// update action exactly once, then saveHistory() exactly once - this
// exercises that exact same two-call sequence directly against the
// store, for a frame (representative of every element - all four
// follow the identical updateX-then-saveHistory pattern).
describe('A resize commits as exactly one history entry (7)', () => {
  function resetStore() {
    useStore.setState({
      objects: [], connections: [], meters: [], signalPanels: [], frames: [],
      selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [],
      history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [] }],
      historyIndex: 0
    });
  }

  it('resizing a frame (updateFrame + saveHistory, the exact sequence its own onTransformEnd runs) adds exactly one history entry', () => {
    resetStore();
    useStore.getState().addFrame({ x: 0, y: 0, width: 64, height: 64, titlePosition: 'TOP_LEFT', variant: 'PLAIN' });
    const frame: FrameElement = useStore.getState().frames[0];
    const before = useStore.getState().history.length;

    useStore.getState().updateFrame(frame.id, { width: 128, height: 96 });
    useStore.getState().saveHistory();

    expect(useStore.getState().history.length).toBe(before + 1);
    expect(useStore.getState().frames[0].width).toBe(128);
    expect(useStore.getState().frames[0].height).toBe(96);
  });

  it('resizing a meter (updateMeter width-only + saveHistory) adds exactly one history entry', () => {
    resetStore();
    useStore.getState().addMeter({ x: 0, y: 0, width: 200, fontSize: 12, rows: [] });
    const meter = useStore.getState().meters[0];
    const before = useStore.getState().history.length;

    useStore.getState().updateMeter(meter.id, { width: 280 });
    useStore.getState().saveHistory();

    expect(useStore.getState().history.length).toBe(before + 1);
    expect(useStore.getState().meters[0].width).toBe(280);
  });
});
