// feat/editing-and-signal-panel commit 7: a signal panel row resolves
// its label/state from the device list - SIGNAL and SWITCHED only;
// MEASURED and MODULATED are rejected exactly like a missing device.

import { describe, it, expect } from 'vitest';
import {
  getSignalCapableDevices, resolveSignalPanelRow, getSignalPanelDanglingRows
} from '../elements/SignalPanelResolver';
import type { Device, SignalDevice, SwitchedDevice, MeasuredDevice, ModulatedDevice } from '../project/DeviceSchema';
import type { SignalPanelRow } from '../elements/SignalPanelElement';

function makeSignal(overrides: Partial<SignalDevice> = {}): SignalDevice {
  return {
    id: 'SIG1', designation: '-B1', name: 'Krancowka otwarta', behavior: 'SIGNAL', kind: 'limit_switch', publishToHa: false,
    feedback: { di: 'ELA1.DI.1', invert: false }, alarmState: 'HIGH', debounceMs: 50,
    ...overrides
  };
}

function makeSwitched(overrides: Partial<SwitchedDevice> = {}): SwitchedDevice {
  return {
    id: 'SW1', designation: '-K1', name: 'Stycznik bramy', behavior: 'SWITCHED', kind: 'contactor', publishToHa: false,
    feedback: { mode: 'NONE' },
    command: { outputCount: 1, style: 'MAINTAINED', doClose: 'ADA1.DO.1' },
    supervision: { confirmTimeoutMs: 1000, discrepancyAlarm: false },
    safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' },
    switchCounter: false,
    ...overrides
  };
}

function makeMeasured(overrides: Partial<MeasuredDevice> = {}): MeasuredDevice {
  return {
    id: 'MEAS1', designation: '-B9', name: 'Temperatura', behavior: 'MEASURED', kind: 'sensor', publishToHa: false,
    input: 'ELA1.AI.1', unit: 'C', rangeMin: 0, rangeMax: 100, format: '0.0', deadband: 1,
    ...overrides
  };
}

function makeModulated(overrides: Partial<ModulatedDevice> = {}): ModulatedDevice {
  return {
    id: 'MOD1', designation: '-Y1', name: 'Zawor modulowany', behavior: 'MODULATED', kind: 'valve', publishToHa: false,
    setpointOutput: 'ADA1.AO.1', unit: '%', rangeMin: 0, rangeMax: 100, startupValue: 0, safeValue: 0,
    ...overrides
  };
}

function makeRow(overrides: Partial<SignalPanelRow> = {}): SignalPanelRow {
  return { device: '', label: '', manualState: 'OFF', ...overrides };
}

describe('SignalPanelResolver.getSignalCapableDevices', () => {
  it('keeps only SIGNAL and SWITCHED devices, in either order', () => {
    const devices: Device[] = [makeSignal({ id: 'A' }), makeMeasured({ id: 'B' }), makeSwitched({ id: 'C' }), makeModulated({ id: 'D' })];
    const capable = getSignalCapableDevices(devices);
    expect(capable.map(d => d.id).sort()).toEqual(['A', 'C']);
  });
});

describe('SignalPanelResolver.resolveSignalPanelRow', () => {
  // 12. a row pointing at a SIGNAL device takes its label from designation
  it('a row pointing at a SIGNAL device with an empty label falls back to the device designation', () => {
    const device = makeSignal({ id: 'SIG1', designation: '-B7' });
    const row = makeRow({ device: 'SIG1', label: '' });
    const display = resolveSignalPanelRow(row, [device]);
    expect(display.label).toBe('-B7');
    // feat/selector-symbol-setpoint-alarm: a SIGNAL device previews
    // ALARM, not a generic ON - see resolveSignalPanelRow's own comment
    // for why (a SIGNAL device's whole reason for existing is alarm
    // signalling, unlike a SWITCHED device's normal-operation ON below).
    expect(display.state).toBe('ALARM');
    expect(display.colorKind).toBe('PREVIEW');
  });

  it('a non-empty row label overrides the device designation', () => {
    const device = makeSignal({ id: 'SIG1', designation: '-B7' });
    const row = makeRow({ device: 'SIG1', label: 'Krancowka otwarta' });
    expect(resolveSignalPanelRow(row, [device]).label).toBe('Krancowka otwarta');
  });

  // 13. a row pointing at a SWITCHED device is allowed
  it('a row pointing at a SWITCHED device resolves normally, previewing ON', () => {
    const device = makeSwitched({ id: 'SW1' });
    const row = makeRow({ device: 'SW1' });
    const display = resolveSignalPanelRow(row, [device]);
    expect(display.colorKind).toBe('PREVIEW');
    expect(display.state).toBe('ON');
  });

  // 14. a row pointing at a MEASURED device is rejected
  it('a row pointing at a MEASURED device is rejected - resolves the same as a missing device', () => {
    const device = makeMeasured({ id: 'MEAS1' });
    const row = makeRow({ device: 'MEAS1' });
    const display = resolveSignalPanelRow(row, [device]);
    expect(display.state).toBe('QUALITY');
    expect(display.colorKind).toBe('MISSING');
  });

  // 15. a row pointing at a MODULATED device is rejected
  it('a row pointing at a MODULATED device is rejected - resolves the same as a missing device', () => {
    const device = makeModulated({ id: 'MOD1' });
    const row = makeRow({ device: 'MOD1' });
    const display = resolveSignalPanelRow(row, [device]);
    expect(display.state).toBe('QUALITY');
    expect(display.colorKind).toBe('MISSING');
  });

  // 16. a row pointing at a non-existent device renders (resolves)
  // without throwing
  it('a row pointing at a non-existent device resolves to QUALITY without throwing', () => {
    const row = makeRow({ device: 'GHOST' });
    expect(() => resolveSignalPanelRow(row, [])).not.toThrow();
    const display = resolveSignalPanelRow(row, []);
    expect(display.state).toBe('QUALITY');
    expect(display.colorKind).toBe('MISSING');
  });

  // 17 (already covered directly in signal-panel-element.test.ts, but
  // exercised here through the full resolver too): a manual row uses
  // manualState untouched.
  it('a manual row (no device) is untouched by device resolution', () => {
    const row = makeRow({ manualState: 'ON', label: 'Manual row' });
    const display = resolveSignalPanelRow(row, [makeSignal({ id: 'SIG1' })]);
    expect(display.state).toBe('ON');
    expect(display.label).toBe('Manual row');
    expect(display.colorKind).toBe('NORMAL');
  });
});

describe('SignalPanelResolver.getSignalPanelDanglingRows', () => {
  it('flags a row pointing at a non-existent device, a MEASURED device and a MODULATED device - not a SIGNAL or SWITCHED one', () => {
    const panel = {
      rows: [
        makeRow({ device: '' }),
        makeRow({ device: 'GHOST' }),
        makeRow({ device: 'MEAS1' }),
        makeRow({ device: 'MOD1' }),
        makeRow({ device: 'SIG1' })
      ]
    };
    const devices: Device[] = [makeMeasured({ id: 'MEAS1' }), makeModulated({ id: 'MOD1' }), makeSignal({ id: 'SIG1' })];
    const issues = getSignalPanelDanglingRows(panel, devices);
    expect(issues.map(i => i.rowIndex)).toEqual([1, 2, 3]);
  });

  it('never throws for an empty row list', () => {
    expect(() => getSignalPanelDanglingRows({ rows: [] }, [])).not.toThrow();
    expect(getSignalPanelDanglingRows({ rows: [] }, [])).toEqual([]);
  });
});
