// feat/site-objects-2d: mandatory tests for the SITE (site object)
// category. Iterates the real registry (getSymbolsByCategory, same
// "visible" filter the Object Library itself uses) rather than a
// hand-picked list, so this file needs no changes as more objects get
// registered - each grows this test's own coverage automatically.
// site.concrete_road/site.grass (the two SURFACES) are named
// explicitly, since their own rules (no states; exactly two states)
// differ from most other site objects. feat/water-management commit 4
// added two more genuinely-three-state objects of its own (a 3-way
// selector valve, and a tank whose three states are literal water
// levels, not open/closed) alongside the original sliding gate - this
// file's own "everything else has exactly two states" assumption
// (from feat/site-objects-2d, when the gate was the only exception)
// is updated here to match, not just left broken.

import { describe, it, expect } from 'vitest';
import { getSymbolsByCategory, getSymbolDefinition } from '../symbols/SymbolRegistry';

const SURFACE_TYPES = ['site.concrete_road'];
const NO_STATE_TYPES = ['site.concrete_road']; // 4. droga betonowa has no states at all
// 3. brama has exactly three states, and specifically THESE three
// (mandatory test 3, feat/site-objects-2d) - kept as its own list
// since test 3 below asserts the exact state NAMES, not just the count.
const THREE_STATE_TYPES = ['site.sliding_gate'];
// fix/hydraulic-connections commit 7: site.water_selector_valve_3pos
// and site.rainwater_tank2 (both also genuinely three-state, feat/
// water-management commit 4) moved out of SITE into Water this commit
// - siteSymbols() below no longer returns them at all, so the
// exemption this file used to need for test 5 is dead code now, not a
// defect to route around.

function siteSymbols() {
  const cats = getSymbolsByCategory();
  return cats['SITE'] || [];
}

describe('SITE category - registration (1)', () => {
  it('sanity: at least one SITE symbol is registered and visible in the library (a passing empty loop proves nothing)', () => {
    expect(siteSymbols().length).toBeGreaterThan(0);
  });

  it('every registered SITE symbol is resolvable back through getSymbolDefinition (the same lookup the canvas itself uses)', () => {
    siteSymbols().forEach(def => {
      expect(getSymbolDefinition(def.type)).toBe(def);
    });
  });
});

describe('SITE category - state counts (2, 3, 4, 5)', () => {
  it('every SITE symbol declares its own list of states (allowedStates), non-empty unless it is a surface', () => {
    siteSymbols().forEach(def => {
      expect(Array.isArray(def.allowedStates)).toBe(true);
      if (!NO_STATE_TYPES.includes(def.type)) {
        expect(def.allowedStates.length).toBeGreaterThan(0);
      }
    });
  });

  it('3. the sliding gate has exactly three states: CLOSED, MOVING, OPEN', () => {
    THREE_STATE_TYPES.forEach(type => {
      const def = getSymbolDefinition(type);
      expect(def).toBeTruthy();
      expect(def!.allowedStates).toEqual(['CLOSED', 'MOVING', 'OPEN']);
    });
  });

  it('4. the concrete road has no states at all', () => {
    const def = getSymbolDefinition('site.concrete_road');
    if (def) expect(def.allowedStates).toEqual([]);
  });

  it('5. every other SITE symbol (not the gate, not a surface) has exactly two states', () => {
    siteSymbols().forEach(def => {
      if (THREE_STATE_TYPES.includes(def.type) || NO_STATE_TYPES.includes(def.type)) return;
      expect(def.allowedStates.length).toBe(2);
    });
  });
});

describe('SITE category - device binding (14)', () => {
  it('every SITE symbol is eligible for the Aparat (device) field - not a line, not graphics.*, not measurements.*', () => {
    siteSymbols().forEach(def => {
      expect(def.isLine).toBeFalsy();
      expect(def.type.startsWith('graphics.')).toBe(false);
      expect(def.type.startsWith('measurements.')).toBe(false);
    });
  });
});

describe('SITE category - surfaces have no terminals, everything else does (part of 6)', () => {
  it('a surface (grass, concrete road) has zero terminals', () => {
    siteSymbols().forEach(def => {
      if (SURFACE_TYPES.includes(def.type) || def.type === 'site.grass') {
        expect(def.terminals || []).toEqual([]);
      }
    });
  });

  it('every non-surface SITE symbol has at least one terminal (grid-alignment/centering itself is covered by terminal-centering.test.ts, which already iterates this same registry)', () => {
    siteSymbols().forEach(def => {
      if (SURFACE_TYPES.includes(def.type) || def.type === 'site.grass') return;
      expect((def.terminals || []).length).toBeGreaterThan(0);
    });
  });
});
