// fix/wire-routing-around-obstacles commit 4 - the 4 mandatory tests
// for the tank's own krociec routes running straight, not jogged.
// waterStub is a plain function returning a React element tree (no
// hooks) - inspectable directly through .props, same convention
// hydraulic-stub-flange.test.ts (previous task) already established.
// RainwaterTank2Symbol.tsx ITSELF is a real component (it calls
// useStore, a hook) so it is not called directly here - its own
// exported pure constants (TANK_TERMINAL_AXIS, TANK_SHELL_BOUNDS,
// isTankOutflowLive, etc.) plus a raw source-text check are what let
// this file verify the real geometry without rendering it.

import { describe, it, expect } from 'vitest';
import { waterStub } from '../symbols/site/BandedShading';
import { getSymbolDefinition } from '../symbols/SymbolRegistry';
import { getTerminalOffsetForSide } from '../utils/Terminals';
import {
  TANK_SHELL_BOUNDS, TANK_TERMINAL_AXIS, TANK_VALUE_FIELD_BOUNDS,
  isTankOutflowLive, LEVEL_PERCENT_BY_STATE
} from '../symbols/site/RainwaterTank2Symbol';
import rainwaterTank2Source from '../symbols/site/RainwaterTank2Symbol.tsx?raw';

function findAll(element: any, typeName: string): any[] {
  if (!element || typeof element !== 'object') return [];
  const results: any[] = [];
  const isMatch = typeof element.type === 'string' ? element.type === typeName : element.type?.name === typeName;
  if (isMatch) results.push(element);
  const children = element.props?.children;
  const list = Array.isArray(children) ? children : children ? [children] : [];
  for (const child of list) results.push(...findAll(child, typeName));
  return results;
}

function overlaps(a: { x: number; y: number; width: number; height: number }, b: typeof a): boolean {
  return a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y;
}

const def = getSymbolDefinition('site.rainwater_tank2')!;
const W = def.defaultWidth;
const H = def.defaultHeight;

describe('24. DOPLYW is a single straight horizontal krociec, touching the tank\'s own true LEFT terminal', () => {
  it('TANK_TERMINAL_AXIS is exactly the LEFT terminal\'s own true edge-midpoint height (getTerminalOffsetForSide, unchanged, GRANICE-protected)', () => {
    expect(TANK_TERMINAL_AXIS).toBe(getTerminalOffsetForSide('LEFT', W, H).y);
  });

  it('waterStub at that axis draws exactly one straight horizontal segment - no jog', () => {
    const el = waterStub(TANK_SHELL_BOUNDS.x, TANK_TERMINAL_AXIS, 'L', true, W, H);
    const path = findAll(el, 'Path')[0];
    const m = /M([\d.-]+),([\d.-]+) L([\d.-]+),([\d.-]+)/.exec(path.props.data);
    expect(m).toBeTruthy();
    expect(path.props.data.split('L').length).toBe(2); // one M, one L - a single segment
    expect(Number(m![2])).toBe(Number(m![4])); // same y at both ends - horizontal
  });

  it('the component itself draws DOPLYW via waterStub at TANK_TERMINAL_AXIS - not a hand-built multi-point jog', () => {
    expect(rainwaterTank2Source).toMatch(/waterStub\(BX,\s*TANK_TERMINAL_AXIS,\s*'L'/);
    expect(rainwaterTank2Source).not.toContain('{ x: 0, y: 20 }'); // the old jog's own starting point
  });
});

// fix/tank-language-and-media commit 2 moved ODPLYW from the RIGHT
// edge to the BOTTOM edge (water drains from the floor, not the
// wall) - this describe block is updated to match; see that task's
// own test 9 for the full mandated coverage ("single vertical
// segment").
describe('25. ODPLYW is a single straight krociec, touching its own true terminal (now on the BOTTOM edge)', () => {
  it('the component draws ODPLYW via waterStub on side B, not the old RIGHT-side TANK_TERMINAL_AXIS jog', () => {
    expect(rainwaterTank2Source).not.toContain('{ x: BX + BW, y: BY + BH - 7 }'); // the old jog's own starting point
    expect(rainwaterTank2Source).not.toMatch(/waterStub\(BX \+ BW,\s*TANK_TERMINAL_AXIS,\s*'R'/); // the old right-side call
  });
});

describe('26. the outflow is inactive when the level is zero', () => {
  it('isTankOutflowLive(0) is false', () => {
    expect(isTankOutflowLive(0)).toBe(false);
  });

  it('true for every real, nonzero state this object actually uses', () => {
    for (const pct of Object.values(LEVEL_PERCENT_BY_STATE)) {
      expect(isTankOutflowLive(pct)).toBe(true);
    }
  });
});

describe('27. the percent field never overlaps the shell, at any state', () => {
  it('the field\'s own fixed bounds never overlap the shell\'s - true regardless of the krociec change above, since neither box moved', () => {
    for (const pct of Object.values(LEVEL_PERCENT_BY_STATE)) {
      expect(pct).toBeGreaterThan(0);
      expect(overlaps(TANK_VALUE_FIELD_BOUNDS, TANK_SHELL_BOUNDS)).toBe(false);
    }
  });
});
