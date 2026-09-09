// feat/selector-symbol-setpoint-alarm: the schematic symbol for a
// SELECTOR device. terminal-centering.test.ts already covers the
// generic terminal/grid-alignment invariants for every visible symbol
// (this one included); this file covers what is specific to this one
// registry entry and component - same "source-scan since there is no
// Konva rendering harness" convention diode-colors.test.ts already
// established.

import { describe, it, expect } from 'vitest';
import { getSymbolDefinition, getSymbolsByCategory } from '../symbols/SymbolRegistry';
import { POSITION_ANGLE_DEG } from '../symbols/electrical/SelectorSwitchSymbol';
import symbolRendererSource from '../symbols/SymbolRenderer.tsx?raw';

describe('electrical.selector_switch registry entry', () => {
  const def = getSymbolDefinition('electrical.selector_switch');

  it('exists, in the Electrical category', () => {
    expect(def).toBeDefined();
    expect(def!.category).toBe('Electrical');
  });

  it('has LEFT/CENTER/RIGHT/FAULT as its allowed states, defaulting to CENTER', () => {
    expect(def!.allowedStates).toEqual(['LEFT', 'CENTER', 'RIGHT', 'FAULT']);
    expect(def!.defaultState).toBe('CENTER');
  });

  it('is visible in the Object Library (not hiddenFromLibrary)', () => {
    const electrical = getSymbolsByCategory().Electrical;
    expect(electrical.some(d => d.type === 'electrical.selector_switch')).toBe(true);
  });

  it('has a single IN terminal on TOP, an even GRID_SIZE multiple in size (terminal-centering.test.ts covers the general rule; this confirms this entry actually declares one)', () => {
    expect(def!.terminals).toEqual([{ id: 'IN', side: 'TOP', medium: 'ELECTRICAL' }]);
    expect(def!.defaultWidth % 32).toBe(0);
    expect(def!.defaultHeight % 32).toBe(0);
  });
});

describe('SymbolRenderer dispatches electrical.selector_switch to SelectorSwitchSymbol', () => {
  it('the switch has a case for it', () => {
    expect(symbolRendererSource).toContain("case 'electrical.selector_switch':");
    expect(symbolRendererSource).toContain('SelectorSwitchSymbol');
  });
});

describe('SelectorSwitchSymbol.POSITION_ANGLE_DEG', () => {
  it('CENTER points straight up (angle 0)', () => {
    expect(POSITION_ANGLE_DEG.CENTER).toBe(0);
  });

  it('LEFT and RIGHT are mirror images of each other around CENTER', () => {
    expect(POSITION_ANGLE_DEG.LEFT).toBe(-POSITION_ANGLE_DEG.RIGHT);
  });

  it('LEFT and RIGHT are both non-zero and distinct from CENTER', () => {
    expect(POSITION_ANGLE_DEG.LEFT).not.toBe(0);
    expect(POSITION_ANGLE_DEG.RIGHT).not.toBe(0);
  });
});
