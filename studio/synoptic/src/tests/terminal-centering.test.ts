// feat/editing-and-signal-panel commit 1: a terminal lies always on the
// middle of a symbol's edge, in a grid node, for a symbol whose own
// dimensions are an EVEN GRID_SIZE multiple. This iterates the real
// symbol registry (getSymbolsByCategory - the same "visible" filter
// the Object Library itself uses), not a handful of hand-picked cases,
// so a new symbol added later without a terminal fix would fail this
// automatically.

import { describe, it, expect } from 'vitest';
import { getSymbolsByCategory } from '../symbols/SymbolRegistry';
import { getTerminalOffsetForSide } from '../utils/Terminals';
import { GRID_SIZE } from '../theme/ScadaTheme';

function allVisibleSymbols() {
  const cats = getSymbolsByCategory();
  return Object.values(cats).flat();
}

describe('Every visible symbol - terminal centering and grid alignment', () => {
  const symbols = allVisibleSymbols();

  it('sanity: the registry actually returned symbols to check (a passing empty loop proves nothing)', () => {
    expect(symbols.length).toBeGreaterThan(0);
  });

  // 3. every visible symbol has dimensions that are an EVEN multiple of
  // GRID_SIZE (32, 64, 96, ... - not 16 or 48), so that w/2 and h/2 -
  // where a terminal always sits - are themselves grid-aligned.
  it('every visible symbol has defaultWidth/defaultHeight as an EVEN GRID_SIZE multiple', () => {
    const problems: string[] = [];
    symbols.forEach((def: any) => {
      const evenStep = GRID_SIZE * 2; // 32
      if (def.defaultWidth % evenStep !== 0) problems.push(`${def.type}: width ${def.defaultWidth}`);
      if (def.defaultHeight % evenStep !== 0) problems.push(`${def.type}: height ${def.defaultHeight}`);
    });
    expect(problems).toEqual([]);
  });

  // 1 & 2. every terminal is centered on an edge AND lands on a grid node.
  it('every terminal sits on the exact middle of a symbol edge, on a grid node', () => {
    const problems: string[] = [];
    symbols.forEach((def: any) => {
      const w = def.defaultWidth;
      const h = def.defaultHeight;
      (def.terminals || []).forEach((spec: any) => {
        const { x, y } = getTerminalOffsetForSide(spec.side, w, h);
        const isCentered =
          (x === w / 2 && (y === 0 || y === h)) ||
          (y === h / 2 && (x === 0 || x === w));
        if (!isCentered) problems.push(`${def.type}.${spec.id}: (${x},${y}) not centred on an edge of ${w}x${h}`);
        if (x % GRID_SIZE !== 0) problems.push(`${def.type}.${spec.id}: x=${x} not grid-aligned`);
        if (y % GRID_SIZE !== 0) problems.push(`${def.type}.${spec.id}: y=${y} not grid-aligned`);
      });
    });
    expect(problems).toEqual([]);
  });

  it('at least one visible symbol actually HAS terminals (a passing loop over zero terminals also proves nothing)', () => {
    const withTerminals = symbols.filter((def: any) => (def.terminals || []).length > 0);
    expect(withTerminals.length).toBeGreaterThan(0);
  });
});

describe('getTerminalOffsetForSide', () => {
  it('resolves each of the four sides to the exact middle of that edge', () => {
    expect(getTerminalOffsetForSide('TOP', 64, 96)).toEqual({ x: 32, y: 0 });
    expect(getTerminalOffsetForSide('BOTTOM', 64, 96)).toEqual({ x: 32, y: 96 });
    expect(getTerminalOffsetForSide('LEFT', 64, 96)).toEqual({ x: 0, y: 48 });
    expect(getTerminalOffsetForSide('RIGHT', 64, 96)).toEqual({ x: 64, y: 48 });
  });
});
