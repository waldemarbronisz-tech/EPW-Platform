/** @vitest-environment jsdom */
// feat/water-management commit 5 - the last 6 of 12 water management
// objects (flow meter, water meter, pressure switch, rain sensor,
// sprinkler head, drip line). No numbered mandatory tests for this
// commit specifically in the task itself - verifies registration, the
// deliberate flow-meter-vs-water-meter value-freezing difference the
// task itself calls out, and the drip line's own adjustable-size
// geometry.

import { describe, it, expect } from 'vitest';
import { getSymbolDefinition, getSymbolsByCategory } from '../symbols/SymbolRegistry';
import flowMeterSource from '../symbols/site/FlowMeterSymbol.tsx?raw';
import waterMeterSource from '../symbols/site/WaterMeterSymbol.tsx?raw';
import { computeDripperPositions } from '../symbols/site/DripLineSymbol';

describe('the last 6 objects are registered (Water/Instrumentation - fix/hydraulic-connections commit 7 moved them out of TEREN) with the right states/terminals', () => {
  it('site.flow_meter, site.water_meter, site.pressure_switch: two states, two WATER terminals each', () => {
    for (const type of ['site.flow_meter', 'site.water_meter', 'site.pressure_switch']) {
      const def = getSymbolDefinition(type)!;
      expect(def.category).toBe('Water');
      expect(def.allowedStates).toEqual(['ZALACZONY', 'WYLACZONY']);
      expect(def.terminals!.length).toBe(2);
      expect(def.terminals!.every(t => t.medium === 'WATER')).toBe(true);
    }
  });

  it('site.rain_sensor: two states, one ELECTRICAL terminal (a powered sensor, no plumbing), category Instrumentation', () => {
    const def = getSymbolDefinition('site.rain_sensor')!;
    expect(def.category).toBe('Instrumentation');
    expect(def.allowedStates).toEqual(['ZALACZONY', 'WYLACZONY']);
    expect(def.terminals).toEqual([{ id: 'ZASILANIE', side: 'BOTTOM', medium: 'ELECTRICAL' }]);
  });

  it('site.sprinkler_head: two states, one WATER terminal, no aparat expected (task\'s own "BEZ tagu")', () => {
    const def = getSymbolDefinition('site.sprinkler_head')!;
    expect(def.allowedStates).toEqual(['ZALACZONY', 'WYLACZONY']);
    expect(def.terminals!.length).toBe(1);
    expect(def.terminals![0].medium).toBe('WATER');
  });

  it('site.drip_line: adjustable size (wider default than a fixed-size object), not marked isSurface', () => {
    const def = getSymbolDefinition('site.drip_line')!;
    expect(def.defaultWidth).toBeGreaterThan(128);
    expect(def.isSurface).toBeFalsy();
  });

  it('the five now in Water show up there; the sixth (rain sensor) shows up in Instrumentation', () => {
    const water = getSymbolsByCategory()['Water'].map(d => d.type);
    for (const type of ['site.flow_meter', 'site.water_meter', 'site.pressure_switch', 'site.sprinkler_head', 'site.drip_line']) {
      expect(water).toContain(type);
    }
    const instrumentation = getSymbolsByCategory()['Instrumentation'].map(d => d.type);
    expect(instrumentation).toContain('site.rain_sensor');
  });
});

describe('flow meter vs. water meter: the deliberate value-freezing difference the task itself calls out', () => {
  it('FlowMeterSymbol shows a fixed "0.0" whenever not flowing, regardless of the device', () => {
    expect(flowMeterSource).toContain("'0.0'");
    // The gate is the object's own on/off state, not the device.
    expect(flowMeterSource).toMatch(/!on \? '0\.0'/);
  });

  it('WaterMeterSymbol\'s own value text is NOT gated on the on/off state at all - a running total keeps reading regardless', () => {
    expect(waterMeterSource).not.toContain("'0.0'");
    expect(waterMeterSource).not.toMatch(/on \?[^:]*formatMeasuredValue/);
  });

  it('both still read through the exact same MeterResolver/colorForRow path as the tank (DOWOD point 5, extended to these two)', () => {
    for (const source of [flowMeterSource, waterMeterSource]) {
      expect(source).toContain('getMeasuredPreviewValue');
      expect(source).toContain('formatMeasuredValue');
      expect(source).toContain('findDeviceById');
      expect(source).toContain('colorForRow');
    }
  });
});

describe('DripLineSymbol - adjustable size, deterministic dripper layout', () => {
  it('the same width always gives the same dripper positions', () => {
    expect(computeDripperPositions(300)).toEqual(computeDripperPositions(300));
  });

  it('a wider drip line gets more drippers, not the same few stretched apart', () => {
    expect(computeDripperPositions(600).length).toBeGreaterThan(computeDripperPositions(150).length);
  });

  it('every dripper stays within the line\'s own bounds', () => {
    const positions = computeDripperPositions(250);
    positions.forEach(x => {
      expect(x).toBeGreaterThanOrEqual(0);
      expect(x).toBeLessThanOrEqual(250);
    });
  });

  it('a degenerate (near-zero) width never throws', () => {
    expect(() => computeDripperPositions(1)).not.toThrow();
  });
});
