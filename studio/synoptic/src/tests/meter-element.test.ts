// feat/meter-element part A: the meter element's own model - height
// math and a manual row's own display text. Pure, Konva-free (see
// MeterElement.ts's own header comment) - no Stage/Layer needed to
// exercise "renders without exception": the height function is what
// the renderer calls before drawing anything, so if it never throws
// for degenerate input, the panel it sizes never can either.

import { describe, it, expect } from 'vitest';
import { computeMeterHeight, formatManualRowValue, clampMeterWidth, METER_MIN_WIDTH, METER_MAX_WIDTH } from '../meter/MeterElement';
import type { MeterElementRow } from '../meter/MeterElement';

function makeRow(overrides: Partial<MeterElementRow> = {}): MeterElementRow {
  return { device: '', label: '', manualValue: '', manualUnit: '', ...overrides };
}

describe('MeterElement height', () => {
  // 1. a meter with 3 rows is taller than one with 1 row
  it('a meter with 3 rows is taller than one with 1 row', () => {
    const h1 = computeMeterHeight({ fontSize: 12, rows: [makeRow()] });
    const h3 = computeMeterHeight({ fontSize: 12, rows: [makeRow(), makeRow(), makeRow()] });
    expect(h3).toBeGreaterThan(h1);
  });

  // 2. a meter with 0 rows renders without exception
  it('a meter with 0 rows computes a height without throwing', () => {
    expect(() => computeMeterHeight({ fontSize: 12, rows: [] })).not.toThrow();
    const h0 = computeMeterHeight({ fontSize: 12, rows: [] });
    expect(h0).toBeGreaterThan(0);
    expect(Number.isFinite(h0)).toBe(true);
  });

  // 3. a meter with a title is taller than one without, same row count
  it('a meter with a title is taller than one without, at the same row count', () => {
    const rows = [makeRow(), makeRow()];
    const withTitle = computeMeterHeight({ title: 'Meter', fontSize: 12, rows });
    const withoutTitle = computeMeterHeight({ title: undefined, fontSize: 12, rows });
    expect(withTitle).toBeGreaterThan(withoutTitle);
  });

  // 12. font size 16 is taller than font size 12, same rows/title
  it('a meter at font size 16 is taller than the same meter at font size 12', () => {
    const rows = [makeRow(), makeRow()];
    const h12 = computeMeterHeight({ title: 'M', fontSize: 12, rows });
    const h16 = computeMeterHeight({ title: 'M', fontSize: 16, rows });
    expect(h16).toBeGreaterThan(h12);
  });

  it('an empty title (falsy) is treated the same as no title at all', () => {
    const rows = [makeRow()];
    const emptyString = computeMeterHeight({ title: '', fontSize: 12, rows });
    const undefinedTitle = computeMeterHeight({ title: undefined, fontSize: 12, rows });
    expect(emptyString).toBe(undefinedTitle);
  });
});

describe('MeterElement manual row display', () => {
  // 6. a manual row uses manualValue and manualUnit
  it('a manual row formats as "value unit" from its own fields', () => {
    const row = makeRow({ manualValue: '42', manualUnit: 'kW' });
    expect(formatManualRowValue(row)).toBe('42 kW');
  });

  it('a manual row with only a value (no unit) omits the trailing space', () => {
    const row = makeRow({ manualValue: '42', manualUnit: '' });
    expect(formatManualRowValue(row)).toBe('42');
  });

  it('a fully empty manual row formats as an empty string, not "undefined" or a lone space', () => {
    const row = makeRow();
    expect(formatManualRowValue(row)).toBe('');
  });
});

describe('MeterElement width clamp', () => {
  it('clamps below METER_MIN_WIDTH up to the minimum', () => {
    expect(clampMeterWidth(50)).toBe(METER_MIN_WIDTH);
  });

  it('clamps above METER_MAX_WIDTH down to the maximum', () => {
    expect(clampMeterWidth(900)).toBe(METER_MAX_WIDTH);
  });

  it('leaves an in-range width untouched', () => {
    expect(clampMeterWidth(200)).toBe(200);
  });
});
