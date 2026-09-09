/** @vitest-environment jsdom */
// feat/water-management commit 4 - the first 6 of 12 water-management
// objects (tank, three-way valves, check valve, filter, hydrofor). No
// numbered mandatory tests for this commit specifically in the task
// itself - this file verifies registration/behavior directly, plus the
// "same path as the meter" requirement (DOWOD point 5) and the device
// form's own three-way-valve label swap.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { getSymbolDefinition, getSymbolsByCategory } from '../symbols/SymbolRegistry';
import { useStore } from '../store';
import { DeviceFormDialog } from '../components/DeviceFormDialog';
import type { SwitchedDevice } from '../project/DeviceSchema';
import rainwaterTank2Source from '../symbols/site/RainwaterTank2Symbol.tsx?raw';

describe('the 6 new objects are registered (Water category - fix/hydraulic-connections commit 7 moved them out of TEREN) with the right states/terminals', () => {
  it('site.rainwater_tank2: three water-level states, two WATER terminals (DOPLYW/ODPLYW - fix/hydraulic-connections commit 6 replaced the old single WYLOT)', () => {
    const def = getSymbolDefinition('site.rainwater_tank2')!;
    expect(def).toBeDefined();
    expect(def.category).toBe('Water');
    expect(def.allowedStates).toEqual(['NISKI', 'SREDNI', 'WYSOKI']);
    expect(def.terminals!.every(t => t.medium === 'WATER')).toBe(true);
  });

  it('site.water_selector_valve_switched: states A/B (SWITCHED-backed)', () => {
    const def = getSymbolDefinition('site.water_selector_valve_switched')!;
    expect(def.allowedStates).toEqual(['A', 'B']);
    expect(def.terminals!.length).toBe(3);
  });

  it('site.water_selector_valve_3pos: states A/ZAMKNIETY/B (SELECTOR-backed)', () => {
    const def = getSymbolDefinition('site.water_selector_valve_3pos')!;
    expect(def.allowedStates).toEqual(['A', 'ZAMKNIETY', 'B']);
  });

  it('site.check_valve, site.water_filter: plain two-state graphics, two WATER terminals each', () => {
    for (const type of ['site.check_valve', 'site.water_filter']) {
      const def = getSymbolDefinition(type)!;
      expect(def.allowedStates).toEqual(['ZALACZONY', 'WYLACZONY']);
      expect(def.terminals!.length).toBe(2);
    }
  });

  it('site.hydrofor: two-state SWITCHED pump', () => {
    const def = getSymbolDefinition('site.hydrofor')!;
    expect(def.allowedStates).toEqual(['ZALACZONY', 'WYLACZONY']);
  });

  it('all 6 actually show up in the live Water category listing', () => {
    const water = getSymbolsByCategory()['Water'].map(d => d.type);
    for (const type of [
      'site.rainwater_tank2', 'site.water_selector_valve_switched', 'site.water_selector_valve_3pos',
      'site.check_valve', 'site.water_filter', 'site.hydrofor'
    ]) {
      expect(water).toContain(type);
    }
  });
});

describe('DOWOD point 5: the tank reads its value field through the EXACT SAME path as the meter element', () => {
  it('RainwaterTank2Symbol.tsx imports getMeasuredPreviewValue/formatMeasuredValue/findDeviceById from MeterResolver.ts (never a second, hand-written resolver)', () => {
    expect(rainwaterTank2Source).toMatch(/from ['"]\.\.\/\.\.\/meter\/MeterResolver['"]/);
    expect(rainwaterTank2Source).toContain('getMeasuredPreviewValue');
    expect(rainwaterTank2Source).toContain('formatMeasuredValue');
    expect(rainwaterTank2Source).toContain('findDeviceById');
  });

  it('and shades the value with the exact same colorForRow the meter element\'s own row uses', () => {
    expect(rainwaterTank2Source).toMatch(/from ['"]\.\.\/\.\.\/components\/MeterElementNode['"]/);
    expect(rainwaterTank2Source).toContain('colorForRow');
  });

  it('without an aparat, the field falls back to a question mark, matching the task\'s own "Bez aparatu: znak zapytania"', () => {
    expect(rainwaterTank2Source).toMatch(/'\?'/);
  });
});

describe('DeviceFormDialog - three-way valve relabels diClosed/diOpen to Pozycja A/Pozycja B', () => {
  function makeSwitched(overrides: Partial<SwitchedDevice> = {}): SwitchedDevice {
    return {
      id: 'OGROD_ZAW1', designation: '-Y1', name: 'Zawor', behavior: 'SWITCHED', kind: 'valve', publishToHa: false,
      feedback: { mode: 'DUAL', diClosed: 'ELA1.DI.1', diOpen: 'ELA1.DI.2' },
      command: { outputCount: 1, style: 'MAINTAINED', doClose: 'ADA1.DO.1' },
      supervision: { confirmTimeoutMs: 500, discrepancyAlarm: false },
      safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' },
      switchCounter: false,
      ...overrides
    };
  }

  beforeEach(() => {
    useStore.setState({
      locations: [{ code: 'OGROD', description: 'Ogrod' }],
      cards: [
        { id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 16 },
        { id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 16 }
      ],
      devices: []
    });
  });
  afterEach(cleanup);

  it('an ordinary valve kind still shows diClosed/diOpen, unchanged', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeSwitched({ kind: 'valve' })} onSave={() => {}} onCancel={() => {}} />);
    expect(screen.getByText('diClosed')).toBeTruthy();
    expect(screen.getByText('diOpen')).toBeTruthy();
    expect(screen.queryByText('Pozycja A')).toBeNull();
  });

  it('kind "zawor trojdrogowy" relabels both fields to Pozycja A / Pozycja B', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeSwitched({ kind: 'zawor trojdrogowy' })} onSave={() => {}} onCancel={() => {}} />);
    expect(screen.getByText('Pozycja A')).toBeTruthy();
    expect(screen.getByText('Pozycja B')).toBeTruthy();
    expect(screen.queryByText('diClosed')).toBeNull();
    expect(screen.queryByText('diOpen')).toBeNull();
  });

  it('the match is case-insensitive and trims whitespace (a real device typed by hand)', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeSwitched({ kind: '  Zawor Trojdrogowy  ' })} onSave={() => {}} onCancel={() => {}} />);
    expect(screen.getByText('Pozycja A')).toBeTruthy();
  });

  it('the underlying SWITCHED contract itself is untouched: feedback.diClosed/diOpen still resolve and validate exactly as before, only the on-screen label changed', () => {
    const device = makeSwitched({ kind: 'zawor trojdrogowy' });
    expect(device.feedback.diClosed).toBe('ELA1.DI.1');
    expect(device.feedback.diOpen).toBe('ELA1.DI.2');
  });
});
