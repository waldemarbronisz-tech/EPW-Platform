// fix/device-form-polish commit 1: the location-code <select> in
// DeviceFormDialog.tsx's own Id field used to render at a few pixels
// wide - its width is now computed from the registry's own content
// (computeCodePickerWidth) rather than a literal in the component.
// Pure-function tests, same convention as resize-handles.test.ts /
// insert-mode.test.ts - no DOM/rendering harness needed for the RULE
// itself (see raport.md for the live-app verification of the actual
// rendered <select>).

import { describe, it, expect } from 'vitest';
import { computeCodePickerWidth } from '../utils/CodePickerWidth';
import { LOCATION_PICKER_MIN_WIDTH, LOCATION_PICKER_MAX_WIDTH } from '../theme/ScadaTheme';

describe('computeCodePickerWidth - location picker width from registry content', () => {
  // 1. width at a five-character longest code is greater than at a three-character one
  it('a five-character code produces a wider result than a three-character one', () => {
    const w3 = computeCodePickerWidth(['KOT']);
    const w5 = computeCodePickerWidth(['PRZEP']);
    expect(w5).toBeGreaterThan(w3);
  });

  // 2. width never drops below 96px, even for a one-character code
  it('a one-character code still clamps to the minimum, never below it', () => {
    expect(computeCodePickerWidth(['A'])).toBe(LOCATION_PICKER_MIN_WIDTH);
    expect(LOCATION_PICKER_MIN_WIDTH).toBe(96);
  });

  // 3. width never exceeds 160px, even for a very long code
  it('a very long code clamps to the maximum, never above it', () => {
    expect(computeCodePickerWidth(['VERYLONGLOCATIONCODE'])).toBe(LOCATION_PICKER_MAX_WIDTH);
    expect(LOCATION_PICKER_MAX_WIDTH).toBe(160);
  });

  it('the LONGEST code among several decides the width, not the first or last', () => {
    const wShortOnly = computeCodePickerWidth(['A', 'B']);
    const wWithLong = computeCodePickerWidth(['A', 'PRZEPOMPOWNIA', 'B']);
    expect(wWithLong).toBeGreaterThan(wShortOnly);
  });

  it('an empty registry (no codes at all) still returns the minimum, never 0 or negative', () => {
    expect(computeCodePickerWidth([])).toBe(LOCATION_PICKER_MIN_WIDTH);
  });

  it('never returns a value outside the min/max bounds, across a range of lengths', () => {
    for (let n = 0; n <= 30; n++) {
      const w = computeCodePickerWidth(['x'.repeat(n)]);
      expect(w).toBeGreaterThanOrEqual(LOCATION_PICKER_MIN_WIDTH);
      expect(w).toBeLessThanOrEqual(LOCATION_PICKER_MAX_WIDTH);
    }
  });
});
