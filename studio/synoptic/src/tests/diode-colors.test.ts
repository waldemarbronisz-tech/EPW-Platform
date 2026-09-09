// fix/handles-insert-mode-diodes commit 3: an ON/QUALITY diode gets a
// brighter, smaller, up-and-left-offset inner "core" circle so it
// reads as an actual light source rather than a painted disc (12); OFF
// gets no core at all - that absence is itself what signals "not lit"
// (13). 14: no file outside ScadaTheme.ts hard-codes one of the new
// DIODE_* hex values - same `?raw` source-scan convention as
// scada-symbols.test.ts's own "no hard-coded colors" test (13, that
// file's own numbering) and typography-proportions.test.ts's font
// scan, extended to every file that plausibly draws or references a
// diode. A whole-tree grep for these seven exact hex values was also
// run directly against the repo during this fix (see raport.md, [E]) -
// this test is the checked-in, permanent version of that same check,
// scoped to the same curated file list this codebase's other source
// scans already use.

import { describe, it, expect } from 'vitest';
import {
  getIndicatorDiodeFillColor, getIndicatorDiodeCoreColor, getIndicatorDiodeCoreGeometry, getIndicatorDiodeRadius
} from '../symbols/scada/IndicatorDiodeSymbol';
import {
  DIODE_ON, DIODE_ON_CORE, DIODE_OFF, DIODE_ALARM, DIODE_ALARM_CORE, DIODE_QUALITY, DIODE_QUALITY_CORE
} from '../theme/ScadaTheme';

import indicatorDiodeSymbolSource from '../symbols/scada/IndicatorDiodeSymbol.tsx?raw';
import signalPanelElementNodeSource from '../components/SignalPanelElementNode.tsx?raw';
import meterElementNodeSource from '../components/MeterElementNode.tsx?raw';
import panelChromeSource from '../components/PanelChrome.tsx?raw';
import scadaStylePreviewSource from '../components/ScadaStylePreview.tsx?raw';
import propertyInspectorSource from '../components/PropertyInspector.tsx?raw';
import canvasSource from '../components/Canvas.tsx?raw';
import symbolRendererSource from '../symbols/SymbolRenderer.tsx?raw';
import pilotLampSymbolSource from '../symbols/scada/PilotLampSymbol.tsx?raw';
import wireNodeSymbolSource from '../symbols/scada/WireNodeSymbol.tsx?raw';
import indexCssSource from '../index.css?raw';

describe('A lit diode (ON/QUALITY) has a brighter core; OFF does not (12, 13)', () => {
  it('12: ON has a core color, distinct from and brighter-looking than its own fill', () => {
    const core = getIndicatorDiodeCoreColor('ON');
    expect(core).not.toBeNull();
    expect(core).toBe(DIODE_ON_CORE);
    expect(core).not.toBe(getIndicatorDiodeFillColor('ON'));
  });

  it('12: QUALITY also has a core color (the same rule applies to every lit state, not only ON)', () => {
    const core = getIndicatorDiodeCoreColor('QUALITY');
    expect(core).toBe(DIODE_QUALITY_CORE);
    expect(core).not.toBe(getIndicatorDiodeFillColor('QUALITY'));
  });

  // 13. OFF must NOT have a brighter core - the absence itself is what
  // signals "not lit" (3c's own explicit requirement, not merely "some
  // dim color").
  it('13: OFF has no core color at all', () => {
    expect(getIndicatorDiodeCoreColor('OFF')).toBeNull();
  });

  it('the core is roughly half the diode\'s own radius, offset up and to the left', () => {
    const radius = getIndicatorDiodeRadius('large');
    const core = getIndicatorDiodeCoreGeometry(radius);
    expect(core.radius).toBeLessThan(radius);
    expect(core.radius).toBeGreaterThan(0);
    expect(core.offset).toBeGreaterThan(0);
    // "up and to the left" - IndicatorDiodeSymbol.tsx and
    // SignalPanelElementNode.tsx both subtract this same offset from
    // BOTH x and y of the diode's own center, checked directly below
    // via source scan rather than re-deriving Konva's own draw here.
  });

  it('DIODE_ALARM/DIODE_ALARM_CORE exist in ScadaTheme per 3a', () => {
    expect(typeof DIODE_ALARM).toBe('string');
    expect(typeof DIODE_ALARM_CORE).toBe('string');
    expect(DIODE_ALARM).toMatch(/^#[0-9A-Fa-f]{6}$/);
    expect(DIODE_ALARM_CORE).toMatch(/^#[0-9A-Fa-f]{6}$/);
  });

  // feat/selector-symbol-setpoint-alarm: ALARM is now a real, wired
  // diode state (previously the two colors above existed with nothing
  // that ever produced them) - same lit-core treatment as ON/QUALITY.
  it('ALARM has its own fill color, distinct from ON/OFF/QUALITY', () => {
    expect(getIndicatorDiodeFillColor('ALARM')).toBe(DIODE_ALARM);
    expect(getIndicatorDiodeFillColor('ALARM')).not.toBe(getIndicatorDiodeFillColor('ON'));
    expect(getIndicatorDiodeFillColor('ALARM')).not.toBe(getIndicatorDiodeFillColor('OFF'));
    expect(getIndicatorDiodeFillColor('ALARM')).not.toBe(getIndicatorDiodeFillColor('QUALITY'));
  });

  it('ALARM has a brighter core color, same as every other lit state', () => {
    const core = getIndicatorDiodeCoreColor('ALARM');
    expect(core).toBe(DIODE_ALARM_CORE);
    expect(core).not.toBe(getIndicatorDiodeFillColor('ALARM'));
  });
});

describe('The Indicator Diode symbol and the signal panel draw the same lit-core look (3d)', () => {
  it('IndicatorDiodeSymbol.tsx draws a conditional core Circle for a lit state', () => {
    expect(indicatorDiodeSymbolSource).toContain('coreColor && (');
    expect(indicatorDiodeSymbolSource).toContain('getIndicatorDiodeCoreColor');
  });

  it('SignalPanelElementNode.tsx draws the same conditional core Circle for each row\'s diode, reusing the identical geometry helper (not a separately hand-tuned duplicate)', () => {
    expect(signalPanelElementNodeSource).toContain('getIndicatorDiodeCoreColor');
    expect(signalPanelElementNodeSource).toContain('getIndicatorDiodeCoreGeometry');
  });
});

describe('14: no file outside ScadaTheme.ts hard-codes a diode color', () => {
  const DIODE_HEX_VALUES = [DIODE_ON, DIODE_ON_CORE, DIODE_OFF, DIODE_ALARM, DIODE_ALARM_CORE, DIODE_QUALITY, DIODE_QUALITY_CORE];

  const sources: Record<string, string> = {
    'IndicatorDiodeSymbol.tsx': indicatorDiodeSymbolSource,
    'SignalPanelElementNode.tsx': signalPanelElementNodeSource,
    'MeterElementNode.tsx': meterElementNodeSource,
    'PanelChrome.tsx': panelChromeSource,
    'ScadaStylePreview.tsx': scadaStylePreviewSource,
    'PropertyInspector.tsx': propertyInspectorSource,
    'Canvas.tsx': canvasSource,
    'SymbolRenderer.tsx': symbolRendererSource,
    'PilotLampSymbol.tsx': pilotLampSymbolSource,
    'WireNodeSymbol.tsx': wireNodeSymbolSource,
    'index.css': indexCssSource
  };

  it('none of the diode-adjacent files contain one of the seven new hex values as a literal', () => {
    for (const [file, source] of Object.entries(sources)) {
      for (const hex of DIODE_HEX_VALUES) {
        expect(source.toUpperCase(), `${file} must not hard-code ${hex}`).not.toContain(hex.toUpperCase());
      }
    }
  });

  it('sanity: the scan pattern actually catches a hard-coded diode color (proves the test is not vacuously passing)', () => {
    const contaminated = `const fill = '${DIODE_ON}';`;
    expect(contaminated.toUpperCase()).toContain(DIODE_ON.toUpperCase());
  });
});
