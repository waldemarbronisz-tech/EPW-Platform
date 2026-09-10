// fix/tank-language-and-media commit 2 - the 6 mandatory tests for
// the tank's own outlet moving to the bottom edge and its drawing
// growing larger. RainwaterTank2Symbol.tsx itself is a real component
// (calls useStore, a hook) so it is not called directly here - same
// convention tank-stubs-straight.test.ts (previous task) already
// established: its own exported pure constants plus waterStub
// (a plain function, no hooks) and a raw source-text scan.

import { describe, it, expect } from 'vitest';
import { waterStub } from '../symbols/site/BandedShading';
import { getSymbolDefinition } from '../symbols/SymbolRegistry';
import { getTerminalOffsetForSide } from '../utils/Terminals';
import {
  TANK_SHELL_BOUNDS, TANK_TERMINAL_AXIS, TANK_OUTFLOW_AXIS, TANK_VALUE_FIELD_BOUNDS,
  LEVEL_PERCENT_BY_STATE
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

describe('8. the tank has its outflow terminal on the BOTTOM edge, not the right', () => {
  it('the registry declares ODPLYW on side BOTTOM', () => {
    expect(def.terminals).toEqual([
      { id: 'DOPLYW', side: 'LEFT', medium: 'WATER' },
      { id: 'ODPLYW', side: 'BOTTOM', medium: 'WATER' }
    ]);
  });

  it('BOTTOM resolves to the true edge midpoint (64, 96) on this object\'s own 128x96 canvas', () => {
    expect(getTerminalOffsetForSide('BOTTOM', W, H)).toEqual({ x: 64, y: 96 });
    expect(TANK_OUTFLOW_AXIS).toBe(64);
  });
});

describe('9. the outflow krociec is a single vertical segment', () => {
  it('waterStub on side B, from the shell floor straight down to the canvas edge, is exactly one vertical segment', () => {
    const el = waterStub(TANK_OUTFLOW_AXIS, TANK_SHELL_BOUNDS.y + TANK_SHELL_BOUNDS.height, 'B', true, W, H);
    const path = findAll(el, 'Path')[0];
    const m = /M([\d.-]+),([\d.-]+) L([\d.-]+),([\d.-]+)/.exec(path.props.data);
    expect(m).toBeTruthy();
    expect(path.props.data.split('L').length).toBe(2); // one M, one L - a single segment
    expect(Number(m![1])).toBe(Number(m![3])); // same x at both ends - vertical
    expect(Number(m![3])).toBe(TANK_OUTFLOW_AXIS);
    expect(Number(m![4])).toBe(H); // reaches exactly the canvas edge
  });

  it('the component itself draws it via waterStub(TANK_OUTFLOW_AXIS, ..., \'B\', ...) - not the old right-side call', () => {
    expect(rainwaterTank2Source).toMatch(/waterStub\(TANK_OUTFLOW_AXIS,\s*BY \+ BH,\s*'B'/);
  });
});

describe('10. the inflow krociec is a single horizontal segment (unchanged by this commit)', () => {
  it('waterStub on side L is exactly one horizontal segment at TANK_TERMINAL_AXIS', () => {
    const el = waterStub(TANK_SHELL_BOUNDS.x, TANK_TERMINAL_AXIS, 'L', true, W, H);
    const path = findAll(el, 'Path')[0];
    const m = /M([\d.-]+),([\d.-]+) L([\d.-]+),([\d.-]+)/.exec(path.props.data);
    expect(path.props.data.split('L').length).toBe(2);
    expect(Number(m![2])).toBe(Number(m![4])); // same y - horizontal
    expect(Number(m![2])).toBe(TANK_TERMINAL_AXIS);
  });

  it('the component still draws DOPLYW via waterStub at TANK_TERMINAL_AXIS on side L', () => {
    expect(rainwaterTank2Source).toMatch(/waterStub\(BX,\s*TANK_TERMINAL_AXIS,\s*'L'/);
  });
});

describe('11. the shell occupies more than half the canvas width', () => {
  it('TANK_SHELL_BOUNDS.width exceeds 64 (half of the 128-wide canvas)', () => {
    expect(TANK_SHELL_BOUNDS.width).toBeGreaterThan(W / 2);
  });

  it('the shell is meaningfully larger than the pre-commit-2 drawing (64x40) - not a token increase', () => {
    const oldArea = 64 * 40;
    const newArea = TANK_SHELL_BOUNDS.width * TANK_SHELL_BOUNDS.height;
    expect(newArea).toBeGreaterThan(oldArea * 1.3);
  });
});

describe('12. the percent field never overlaps the shell, at any state', () => {
  it('the field\'s own fixed bounds never overlap the shell\'s - true for every real state, since neither box moves with pct', () => {
    for (const pct of Object.values(LEVEL_PERCENT_BY_STATE)) {
      expect(pct).toBeGreaterThan(0); // sanity: a real state, not a vacuous check
      expect(overlaps(TANK_VALUE_FIELD_BOUNDS, TANK_SHELL_BOUNDS)).toBe(false);
    }
  });

  it('specifically checked at 88 percent (HIGH), per this commit\'s own explicit requirement', () => {
    expect(LEVEL_PERCENT_BY_STATE.HIGH).toBe(88);
    expect(overlaps(TANK_VALUE_FIELD_BOUNDS, TANK_SHELL_BOUNDS)).toBe(false);
  });

  it('sanity: the overlap check itself actually catches a real overlap', () => {
    expect(overlaps({ x: 0, y: 0, width: 10, height: 10 }, { x: 5, y: 5, width: 10, height: 10 })).toBe(true);
  });
});

describe('13. both krociec runs inherit their colour from net state - neither is hardcoded', () => {
  it('both waterStub calls read terminalNetState, never a bare true/false literal or a local pct-derived boolean', () => {
    expect(rainwaterTank2Source).toMatch(/waterStub\(BX,\s*TANK_TERMINAL_AXIS,\s*'L',\s*\(terminalNetState\?\.\('DOPLYW'\)/);
    expect(rainwaterTank2Source).toMatch(/waterStub\(TANK_OUTFLOW_AXIS,\s*BY \+ BH,\s*'B',\s*\(terminalNetState\?\.\('ODPLYW'\)/);
  });
});
