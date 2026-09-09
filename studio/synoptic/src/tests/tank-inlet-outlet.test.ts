// fix/hydraulic-connections commit 6 - the 4 mandatory tests for the
// tank's own rebuilt connection layout (DOPLYW left, ODPLYW right,
// docs/EPW_kolnierze_referencja.py's own updated tank()).

import { describe, it, expect } from 'vitest';
import { getSymbolDefinition } from '../symbols/SymbolRegistry';
import { getTerminalOffsetForSide } from '../utils/Terminals';
import {
  isTankOutflowLive, LEVEL_PERCENT_BY_STATE,
  TANK_SHELL_BOUNDS, TANK_VALUE_FIELD_BOUNDS, TANK_LEVEL_WINDOW_BOUNDS
} from '../symbols/site/RainwaterTank2Symbol';

function overlaps(a: { x: number; y: number; width: number; height: number }, b: typeof a): boolean {
  return a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y;
}

describe('23. the tank has a DOPLYW terminal on the left and an ODPLYW terminal on the right', () => {
  it('the registry declares exactly these two terminals, both WATER', () => {
    const def = getSymbolDefinition('site.rainwater_tank2')!;
    expect(def.terminals).toEqual([
      { id: 'DOPLYW', side: 'LEFT', medium: 'WATER' },
      { id: 'ODPLYW', side: 'RIGHT', medium: 'WATER' }
    ]);
  });

  it('LEFT/RIGHT resolve to the true edge midpoints on this object\'s own 128x96 canvas', () => {
    const def = getSymbolDefinition('site.rainwater_tank2')!;
    expect(getTerminalOffsetForSide('LEFT', def.defaultWidth, def.defaultHeight)).toEqual({ x: 0, y: 48 });
    expect(getTerminalOffsetForSide('RIGHT', def.defaultWidth, def.defaultHeight)).toEqual({ x: 128, y: 48 });
  });
});

describe('24. the outflow is inactive when the level is zero', () => {
  it('isTankOutflowLive(0) is false - none of the three real states (18/52/88%) reach zero on their own, so this is checked directly', () => {
    expect(isTankOutflowLive(0)).toBe(false);
  });

  it('isTankOutflowLive is true for every real, nonzero percentage this object actually uses', () => {
    for (const pct of Object.values(LEVEL_PERCENT_BY_STATE)) {
      expect(isTankOutflowLive(pct)).toBe(true);
    }
  });
});

describe('25. the percent field never overlaps the shell, at none of the three states', () => {
  it('the percent field\'s own fixed bounds do not overlap the shell\'s own fixed bounds - true for every state, since neither box moves with pct', () => {
    for (const pct of Object.values(LEVEL_PERCENT_BY_STATE)) {
      expect(pct).toBeGreaterThan(0); // sanity: a real state, not a vacuous check
      expect(overlaps(TANK_VALUE_FIELD_BOUNDS, TANK_SHELL_BOUNDS)).toBe(false);
    }
  });

  it('sanity: the overlap check itself actually catches a real overlap', () => {
    expect(overlaps({ x: 0, y: 0, width: 10, height: 10 }, { x: 5, y: 5, width: 10, height: 10 })).toBe(true);
  });
});

describe('26. the level window fits inside the shell', () => {
  it('the level window\'s own bounds are fully contained within the shell\'s own bounds', () => {
    expect(TANK_LEVEL_WINDOW_BOUNDS.x).toBeGreaterThanOrEqual(TANK_SHELL_BOUNDS.x);
    expect(TANK_LEVEL_WINDOW_BOUNDS.y).toBeGreaterThanOrEqual(TANK_SHELL_BOUNDS.y);
    expect(TANK_LEVEL_WINDOW_BOUNDS.x + TANK_LEVEL_WINDOW_BOUNDS.width).toBeLessThanOrEqual(TANK_SHELL_BOUNDS.x + TANK_SHELL_BOUNDS.width);
    expect(TANK_LEVEL_WINDOW_BOUNDS.y + TANK_LEVEL_WINDOW_BOUNDS.height).toBeLessThanOrEqual(TANK_SHELL_BOUNDS.y + TANK_SHELL_BOUNDS.height);
  });
});
