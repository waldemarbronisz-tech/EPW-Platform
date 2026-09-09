// feat/appearance-selection-frames commit 1: diode radii and typography
// all read from ScadaTheme.ts's own constants (DIODE_RADIUS_SMALL/
// LARGE, FONT_UI, FONT_VALUE, FONT_SIZE_BASE/SMALL/TITLE) - never a
// hand-picked family or pixel size anywhere else. Mirrors scada-
// symbols.test.ts's own "no hard-coded colors" test (?raw source
// imports + a regex scan) for the same purpose, one axis over: fonts
// instead of colors.
//
// SCOPE OF THE "NO HARD-CODED FONT" SCAN (mandatory test 2): every
// file that is already fully migrated onto ScadaTheme's own COLOR
// constants (meter, signal panel, object labels, the nine scada/
// symbols, the theme-integrated measurement display, the app's own
// CSS chrome) is scanned here and must be clean. A second group of
// files - src/symbols/instrumentation/*.tsx, src/symbols/electrical/
// {Motor,GenericLoad,Generator,GridSource}Symbol.tsx and every
// src/symbols/automation/*.tsx file - still paint their own raw hex
// colors throughout (never migrated onto ScadaTheme's palette at all -
// confirmed by grep, zero ScadaTheme import in automation/*, only
// SYMBOL_STROKE - a dimension, not a color - in the electrical/
// instrumentation files listed). GRANICE explicitly exempts these
// files' COLORS from this whole task ("NIE ruszaj kolorow w starych
// rendererach - osobne zadanie"); their handful of font literals are
// left alone for the identical reason, so a future color migration and
// a future font migration land together, not as two disconnected half
// edits to the same lines. src/symbols/scada/MotorSymbol.tsx (hidden,
// not one of the 22 visible symbols) is IN the theme-integrated group
// but keeps one deliberate exception: its "M" glyph's fontSize (34) is
// sized to exactly fill MOTOR_RADIUS (34) - a shape dimension, the
// same category ScadaTheme.ts's own header comment already allows a
// symbol to keep as a literal ("the busbar's 3px outline, the label
// frame's 4px outline"), not a legibility/typography choice. Every one
// of these exclusions is listed explicitly in raport.md.

import { describe, it, expect } from 'vitest';
import { DIODE_RADIUS_SMALL, DIODE_RADIUS_LARGE } from '../theme/ScadaTheme';
import { getIndicatorDiodeRadius } from '../symbols/scada/IndicatorDiodeSymbol';
import { getPanelRowLayout } from '../components/PanelChrome';

import panelChromeSource from '../components/PanelChrome.tsx?raw';
import meterElementNodeSource from '../components/MeterElementNode.tsx?raw';
import signalPanelElementNodeSource from '../components/SignalPanelElementNode.tsx?raw';
import objectLabelRendererSource from '../components/ObjectLabelRenderer.tsx?raw';
import scadaStylePreviewSource from '../components/ScadaStylePreview.tsx?raw';
import propertyInspectorSource from '../components/PropertyInspector.tsx?raw';
import meterWizardDialogSource from '../components/MeterWizardDialog.tsx?raw';
import signalPanelWizardDialogSource from '../components/SignalPanelWizardDialog.tsx?raw';
import toolbarSource from '../components/Toolbar.tsx?raw';
import canvasSource from '../components/Canvas.tsx?raw';
import symbolRendererSource from '../symbols/SymbolRenderer.tsx?raw';
import labelFrameSymbolSource from '../symbols/scada/LabelFrameSymbol.tsx?raw';
import meterSymbolSource from '../symbols/scada/MeterSymbol.tsx?raw';
import measurementDisplaySymbolSource from '../symbols/measurements/MeasurementDisplaySymbol.tsx?raw';
import panelLayoutSource from '../elements/PanelLayout.ts?raw';
import meterElementSource from '../meter/MeterElement.ts?raw';
import signalPanelElementSource from '../elements/SignalPanelElement.ts?raw';
import indexCssSource from '../index.css?raw';

describe('Diode radii (ScadaTheme.DIODE_RADIUS_SMALL/LARGE)', () => {
  // 1. small diode radius 5, large diode radius 7
  it('DIODE_RADIUS_SMALL is 5 and DIODE_RADIUS_LARGE is 7', () => {
    expect(DIODE_RADIUS_SMALL).toBe(5);
    expect(DIODE_RADIUS_LARGE).toBe(7);
  });

  it('getIndicatorDiodeRadius resolves both sizes from these exact constants, not a coincidentally equal literal', () => {
    expect(getIndicatorDiodeRadius('small')).toBe(DIODE_RADIUS_SMALL);
    expect(getIndicatorDiodeRadius('large')).toBe(DIODE_RADIUS_LARGE);
  });
});

describe('Row height derives from font size (meter and signal panel, commit 1d)', () => {
  // 3. row height at font size 16 is greater than at font size 13
  it('a row is taller at font size 16 than at font size 13 (shared by the meter and the signal panel)', () => {
    const at13 = getPanelRowLayout(13, false).rowHeight;
    const at16 = getPanelRowLayout(16, false).rowHeight;
    expect(at16).toBeGreaterThan(at13);
  });

  it('row height is never a constant regardless of hasTitle - only the title block depends on that', () => {
    const noTitle = getPanelRowLayout(13, false);
    const withTitle = getPanelRowLayout(13, true);
    expect(noTitle.rowHeight).toBe(withTitle.rowHeight);
  });
});

describe('No hard-coded font name or size outside ScadaTheme (commit 1e)', () => {
  const sources: Record<string, string> = {
    'PanelChrome.tsx': panelChromeSource,
    'MeterElementNode.tsx': meterElementNodeSource,
    'SignalPanelElementNode.tsx': signalPanelElementNodeSource,
    'ObjectLabelRenderer.tsx': objectLabelRendererSource,
    'ScadaStylePreview.tsx': scadaStylePreviewSource,
    'PropertyInspector.tsx': propertyInspectorSource,
    'MeterWizardDialog.tsx': meterWizardDialogSource,
    'SignalPanelWizardDialog.tsx': signalPanelWizardDialogSource,
    'Toolbar.tsx': toolbarSource,
    'Canvas.tsx': canvasSource,
    'SymbolRenderer.tsx': symbolRendererSource,
    'LabelFrameSymbol.tsx (scada)': labelFrameSymbolSource,
    'MeterSymbol.tsx (scada)': meterSymbolSource,
    'MeasurementDisplaySymbol.tsx': measurementDisplaySymbolSource,
    'PanelLayout.ts': panelLayoutSource,
    'MeterElement.ts': meterElementSource,
    'SignalPanelElement.ts': signalPanelElementSource,
    'index.css': indexCssSource
  };

  // A literal font-family value: a quote immediately after the
  // property, e.g. fontFamily="sans-serif" or font-family: 'Tahoma'.
  // fontFamily={FONT_UI} and font-family: var(--scada-font-ui) both
  // have no quote right there, so neither matches.
  const HARD_CODED_FONT_FAMILY = /font-?[Ff]amily\s*[:=]\s*[`'"]/;

  // A literal font-size value: a digit immediately after the property
  // (optionally through a JSX brace), e.g. fontSize={12}, fontSize: 12,
  // font-size: 11px. fontSize={FONT_SIZE_BASE} and fontSize={fontSize}
  // (a variable) both start with a letter, not a digit, so neither
  // matches - and neither does a genuinely proportional expression
  // like fontSize={w*0.3} for the same reason.
  const HARD_CODED_FONT_SIZE = /font-?[Ss]ize\s*[:=]\s*\{?\s*[0-9]/;

  it('none of these files hard-codes a font-family string', () => {
    for (const [file, source] of Object.entries(sources)) {
      const matches = source.match(new RegExp(HARD_CODED_FONT_FAMILY, 'g'));
      expect(matches, `${file} must not hard-code a font family - found: ${matches?.join(', ')}`).toBeNull();
    }
  });

  it('none of these files hard-codes a font-size number', () => {
    for (const [file, source] of Object.entries(sources)) {
      const matches = source.match(new RegExp(HARD_CODED_FONT_SIZE, 'g'));
      expect(matches, `${file} must not hard-code a font size - found: ${matches?.join(', ')}`).toBeNull();
    }
  });

  it('sanity: the scan patterns actually catch a hard-coded font (proves the test is not vacuously passing)', () => {
    expect('fontFamily="sans-serif"').toMatch(HARD_CODED_FONT_FAMILY);
    expect("font-family: 'Tahoma', sans-serif;").toMatch(HARD_CODED_FONT_FAMILY);
    expect('fontSize={12}').toMatch(HARD_CODED_FONT_SIZE);
    expect('font-size: 11px;').toMatch(HARD_CODED_FONT_SIZE);
    // and confirms the theme-sourced forms do NOT trip it
    expect('fontFamily={FONT_UI}').not.toMatch(HARD_CODED_FONT_FAMILY);
    expect('font-family: var(--scada-font-ui);').not.toMatch(HARD_CODED_FONT_FAMILY);
    expect('fontSize={FONT_SIZE_BASE}').not.toMatch(HARD_CODED_FONT_SIZE);
    expect('fontSize={w*0.3}').not.toMatch(HARD_CODED_FONT_SIZE);
  });
});

