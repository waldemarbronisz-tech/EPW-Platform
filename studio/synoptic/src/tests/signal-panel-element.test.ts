// feat/editing-and-signal-panel commit 6: the signal panel element's own
// model - height math (shared with the meter via elements/
// PanelLayout.ts) and width clamp. Same pure, Konva-free convention as
// meter-element.test.ts.

import { describe, it, expect } from 'vitest';
import { computeSignalPanelHeight, clampSignalPanelWidth, SIGNAL_PANEL_MIN_WIDTH, SIGNAL_PANEL_MAX_WIDTH } from '../elements/SignalPanelElement';
import type { SignalPanelRow } from '../elements/SignalPanelElement';
import { getIndicatorDiodeFillColor } from '../symbols/scada/IndicatorDiodeSymbol';
import { DIODE_ON, DIODE_OFF, DIODE_QUALITY } from '../theme/ScadaTheme';

function makeRow(overrides: Partial<SignalPanelRow> = {}): SignalPanelRow {
  return { device: '', label: '', manualState: 'OFF', ...overrides };
}

describe('SignalPanelElement height', () => {
  // 9. a panel with 5 rows is taller than one with 1 row
  it('a panel with 5 rows is taller than one with 1 row', () => {
    const h1 = computeSignalPanelHeight({ fontSize: 12, rows: [makeRow()] });
    const h5 = computeSignalPanelHeight({ fontSize: 12, rows: [makeRow(), makeRow(), makeRow(), makeRow(), makeRow()] });
    expect(h5).toBeGreaterThan(h1);
  });

  // 10. a panel with 0 rows renders (computes a height) without exception
  it('a panel with 0 rows computes a height without throwing', () => {
    expect(() => computeSignalPanelHeight({ fontSize: 12, rows: [] })).not.toThrow();
    const h0 = computeSignalPanelHeight({ fontSize: 12, rows: [] });
    expect(h0).toBeGreaterThan(0);
    expect(Number.isFinite(h0)).toBe(true);
  });

  // 11. a panel with a title is taller than one without, same row count
  it('a panel with a title is taller than one without, at the same row count', () => {
    const rows = [makeRow(), makeRow()];
    const withTitle = computeSignalPanelHeight({ title: 'Stan bramy', fontSize: 12, rows });
    const withoutTitle = computeSignalPanelHeight({ title: undefined, fontSize: 12, rows });
    expect(withTitle).toBeGreaterThan(withoutTitle);
  });

  it('uses the exact same height formula as the meter element (shared PanelLayout.ts)', () => {
    // Cross-checked against meter-element.test.ts's own numbers for the
    // same inputs - proof the two elements did not quietly drift apart.
    //
    // feat/appearance-selection-frames commit 1c: the title block's
    // height no longer scales with the passed fontSize (12 here) - it
    // is always ScadaTheme.ts's fixed FONT_SIZE_TITLE (14), a
    // deliberate typography change, not a behavior regression (see
    // PanelLayout.ts's computePanelHeight and raport.md). Expected
    // value updated 116 -> 119 (only the title term changed: 12*1.5+6=24
    // -> 14*1.5+6=27; the row term, 3*(12*2)=72, and padding, 10*2=20,
    // are untouched).
    const rows = [makeRow(), makeRow(), makeRow()];
    expect(computeSignalPanelHeight({ title: 'M', fontSize: 12, rows })).toBe(
      10 * 2 + (14 * 1.5 + 6) + 3 * (12 * 2)
    );
  });
});

describe('SignalPanelElement width clamp', () => {
  it('clamps below SIGNAL_PANEL_MIN_WIDTH up to the minimum', () => {
    expect(clampSignalPanelWidth(50)).toBe(SIGNAL_PANEL_MIN_WIDTH);
  });

  it('clamps above SIGNAL_PANEL_MAX_WIDTH (400, narrower than the meter\'s 480) down to the maximum', () => {
    expect(clampSignalPanelWidth(900)).toBe(SIGNAL_PANEL_MAX_WIDTH);
    expect(SIGNAL_PANEL_MAX_WIDTH).toBe(400);
  });

  it('leaves an in-range width untouched', () => {
    expect(clampSignalPanelWidth(200)).toBe(200);
  });
});

// 17. a manual row uses manualState
describe('Manual row state', () => {
  it('a manual row (no device) carries its own manualState directly - no separate resolver needed for this case', () => {
    const row = makeRow({ manualState: 'ON' });
    expect(row.device).toBe('');
    expect(row.manualState).toBe('ON');
  });

  // fix/handles-insert-mode-diodes commit 3a: the diode now paints
  // with ScadaTheme's own dedicated DIODE_ON/DIODE_OFF/DIODE_QUALITY,
  // deliberately separate from COLOR_RUN/COLOR_DE_ENERGIZED/
  // COLOR_LAMP_LIT (the state colors every OTHER symbol still uses) -
  // a manual row's diode still reuses the Indicator Diode symbol's own
  // color mapping unmodified, just that mapping itself now points at
  // the diode's own palette. See DIODE_ON's own comment in
  // ScadaTheme.ts and raport.md.
  it('the diode color for a manual row reuses the existing Indicator Diode symbol\'s own color mapping, unmodified', () => {
    expect(getIndicatorDiodeFillColor('ON')).toBe(DIODE_ON);
    expect(getIndicatorDiodeFillColor('OFF')).toBe(DIODE_OFF);
    expect(getIndicatorDiodeFillColor('QUALITY')).toBe(DIODE_QUALITY);
  });
});
