// fix/wiring-and-library-groups commit 1 - the 6 mandatory tests for
// usterka 1 ("zaciski znikaja przy probie ich kliknieca"). Pure-function
// tests against src/utils/TerminalReach.ts - Konva-free, so the actual
// hover hit-rect/nearby-terminal/magnetism math is verified directly,
// without needing to render anything.
//
// Same fixture convention as wire-anchoring.test.ts: a real, registered
// 'electrical.circuit_breaker' (defaultWidth/Height 64, terminals IN
// (TOP) and OUT (BOTTOM)), placed at grid-aligned (160,160):
//   IN  (TOP,    local 32,0 ) -> world (192,160)
//   OUT (BOTTOM, local 32,64) -> world (192,224)

import { describe, it, expect } from 'vitest';
import type { SynopticObject } from '../store';
import { getHoverHitRect, getNearbyTerminals, findNearestTerminal, snapToTerminalOrGrid } from '../utils/TerminalReach';
import { GRID_SIZE, TERMINAL_HOVER_MARGIN, TERMINAL_RADIUS_HIGHLIGHTED } from '../theme/ScadaTheme';

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
const OUT_WORLD = { x: 192, y: 224 };

describe('1. the hover hit-rect is bigger than the symbol\'s own outline', () => {
  it('getHoverHitRect pads a 64x64 symbol on every side by at least three terminal radii', () => {
    const rect = getHoverHitRect(64, 64);
    expect(rect.x).toBeLessThan(0);
    expect(rect.y).toBeLessThan(0);
    expect(rect.width).toBeGreaterThan(64);
    expect(rect.height).toBeGreaterThan(64);
    // The margin on every side equals TERMINAL_HOVER_MARGIN, itself
    // defined (ScadaTheme.ts) as at least three times a terminal dot's
    // own radius - this is the "co najmniej promieniowi razy trzy"
    // requirement, checked against the constant it is built from.
    expect(-rect.x).toBe(TERMINAL_HOVER_MARGIN);
    expect(rect.width).toBe(64 + TERMINAL_HOVER_MARGIN * 2);
  });
});

describe('2. hovering the terminal dot itself, even past the symbol\'s own edge, keeps terminals visible', () => {
  it('the padded hit-rect fully contains every terminal\'s own (highlighted-size) dot, in every direction', () => {
    const rect = getHoverHitRect(64, 64);
    // IN sits on the TOP edge (local 32,0) - its own dot circle pokes
    // TERMINAL_RADIUS_HIGHLIGHTED above that edge, into negative y.
    const dotTop = 0 - TERMINAL_RADIUS_HIGHLIGHTED;
    expect(dotTop).toBeGreaterThanOrEqual(rect.y);
    // OUT sits on the BOTTOM edge (local 32,64) - its dot pokes past
    // height=64, into rect's own padded bottom margin.
    const dotBottom = 64 + TERMINAL_RADIUS_HIGHLIGHTED;
    expect(dotBottom).toBeLessThanOrEqual(rect.y + rect.height);
    // Sanity: TERMINAL_HOVER_MARGIN is not just "bigger than zero" but
    // actually bigger than the highlighted dot's own radius - otherwise
    // this containment would be a coincidence of these two specific
    // numbers, not a guaranteed property of the fix.
    expect(TERMINAL_HOVER_MARGIN).toBeGreaterThan(TERMINAL_RADIUS_HIGHLIGHTED);
  });
});

describe('3. while drawing, a terminal 3 grid cells away from the cursor is visible', () => {
  it('getNearbyTerminals includes the OUT terminal when the cursor is 3*GRID_SIZE away', () => {
    const cursor = { x: OUT_WORLD.x, y: OUT_WORLD.y + GRID_SIZE * 3 };
    const nearby = getNearbyTerminals([breaker()], cursor);
    expect(nearby.some(t => t.objId === 'b1' && t.terminalId === 'OUT')).toBe(true);
  });
});

describe('4. while drawing, a terminal 8 grid cells away from the cursor is NOT visible', () => {
  it('getNearbyTerminals excludes the OUT terminal when the cursor is 8*GRID_SIZE away', () => {
    const cursor = { x: OUT_WORLD.x, y: OUT_WORLD.y + GRID_SIZE * 8 };
    const nearby = getNearbyTerminals([breaker()], cursor);
    expect(nearby.some(t => t.objId === 'b1' && t.terminalId === 'OUT')).toBe(false);
  });
});

describe('5. a terminal closer than half a grid cell to the cursor is highlighted', () => {
  it('findNearestTerminal finds IN when the cursor is GRID_SIZE/4 away (well within half a cell)', () => {
    const cursor = { x: IN_WORLD.x, y: IN_WORLD.y + GRID_SIZE / 4 };
    const nearest = findNearestTerminal([breaker()], cursor);
    expect(nearest).toEqual({ objId: 'b1', terminalId: 'IN', x: IN_WORLD.x, y: IN_WORLD.y, medium: 'ELECTRICAL' });
  });

  it('finds nothing when the cursor is exactly half a grid cell away (the spec\'s own "mniejsza niz", strictly less)', () => {
    const cursor = { x: IN_WORLD.x, y: IN_WORLD.y + GRID_SIZE / 2 };
    expect(findNearestTerminal([breaker()], cursor)).toBeNull();
  });

  it('finds nothing when nothing is close enough at all', () => {
    const cursor = { x: IN_WORLD.x + GRID_SIZE * 5, y: IN_WORLD.y };
    expect(findNearestTerminal([breaker()], cursor)).toBeNull();
  });
});

describe('6. the drawn wire\'s end snaps to the highlighted terminal', () => {
  it('snapToTerminalOrGrid lands exactly on OUT\'s own coordinate when the raw cursor is close (not just the nearest grid node)', () => {
    // A raw position that is NOT itself grid-aligned - between two grid
    // nodes - but within half a cell of the OUT terminal specifically.
    const raw = { x: OUT_WORLD.x + 3, y: OUT_WORLD.y - 2 };
    const snapped = snapToTerminalOrGrid(raw.x, raw.y, [breaker()]);
    expect(snapped).toEqual({ x: OUT_WORLD.x, y: OUT_WORLD.y });
  });

  it('falls back to plain grid-snap when nothing is close enough to magnetize to', () => {
    const raw = { x: 500, y: 500 };
    const snapped = snapToTerminalOrGrid(raw.x, raw.y, [breaker()]);
    expect(snapped).toEqual({ x: 496, y: 496 }); // 500 rounds to the nearest 16px node
    // Sanity: this is genuinely the grid-snap path, not a coincidental
    // terminal match - 500,500 is nowhere near breaker()'s own terminals.
    expect(findNearestTerminal([breaker()], raw)).toBeNull();
  });
});
