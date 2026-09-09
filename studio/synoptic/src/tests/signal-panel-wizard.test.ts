// feat/editing-and-signal-panel commit 8: the location-grouped picker's
// pure logic - grouping and bulk row building, independent of the
// dialog UI itself. Mirrors meter-wizard.test.ts's own coverage.

import { describe, it, expect } from 'vitest';
import { groupSignalCapableDevicesByLocation, buildSignalPanelRowsFromSelection } from '../elements/SignalPanelWizard';
import type { Device, SignalDevice, SwitchedDevice, MeasuredDevice, ModulatedDevice } from '../project/DeviceSchema';

function makeSignal(id: string, overrides: Partial<SignalDevice> = {}): SignalDevice {
  return {
    id, designation: `-B${id}`, name: `Signal ${id}`, behavior: 'SIGNAL', kind: 'limit_switch', publishToHa: false,
    feedback: { di: 'ELA1.DI.1', invert: false }, alarmState: 'HIGH', debounceMs: 50,
    ...overrides
  };
}

function makeSwitched(id: string, overrides: Partial<SwitchedDevice> = {}): SwitchedDevice {
  return {
    id, designation: `-K${id}`, name: `Switched ${id}`, behavior: 'SWITCHED', kind: 'contactor', publishToHa: false,
    feedback: { mode: 'NONE' },
    command: { outputCount: 1, style: 'MAINTAINED', doClose: 'ADA1.DO.1' },
    supervision: { confirmTimeoutMs: 1000, discrepancyAlarm: false },
    safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' },
    switchCounter: false,
    ...overrides
  };
}

function makeMeasured(id: string): MeasuredDevice {
  return {
    id, designation: `-B${id}`, name: `Measured ${id}`, behavior: 'MEASURED', kind: 'sensor', publishToHa: false,
    input: 'ELA1.AI.1', unit: 'C', rangeMin: 0, rangeMax: 100, format: '0.0', deadband: 1
  };
}

function makeModulated(id: string): ModulatedDevice {
  return {
    id, designation: `-Y${id}`, name: `Modulated ${id}`, behavior: 'MODULATED', kind: 'valve', publishToHa: false,
    setpointOutput: 'ADA1.AO.1', unit: '%', rangeMin: 0, rangeMax: 100, startupValue: 0, safeValue: 0
  };
}

describe('SignalPanelWizard.groupSignalCapableDevicesByLocation', () => {
  // 18. three KOT and two BRAMA aparaty give two groups sized 3 and 2
  it('groups devices by the id prefix before the underscore - 3 in KOT and 2 in BRAMA yields two groups sized 3 and 2', () => {
    const devices: Device[] = [
      makeSignal('KOT_1'), makeSignal('KOT_2'), makeSwitched('KOT_3'),
      makeSignal('BRAMA_1'), makeSwitched('BRAMA_2')
    ];
    const groups = groupSignalCapableDevicesByLocation(devices);
    expect(groups.length).toBe(2);
    const byLocation = Object.fromEntries(groups.map(g => [g.location, g.devices.length]));
    expect(byLocation).toEqual({ KOT: 3, BRAMA: 2 });
  });

  // 19. the wizard does NOT show MEASURED or MODULATED aparaty
  it('never includes a MEASURED or MODULATED device in any group', () => {
    const devices: Device[] = [
      makeSignal('KOT_1'), makeMeasured('KOT_2'), makeModulated('KOT_3'), makeSwitched('BRAMA_1')
    ];
    const groups = groupSignalCapableDevicesByLocation(devices);
    const allIds = groups.flatMap(g => g.devices.map(d => d.id));
    expect(allIds.sort()).toEqual(['BRAMA_1', 'KOT_1']);
  });

  // 20. an empty aparat list returns zero groups, without exception
  it('an empty device list returns zero groups without throwing', () => {
    expect(() => groupSignalCapableDevicesByLocation([])).not.toThrow();
    expect(groupSignalCapableDevicesByLocation([])).toEqual([]);
  });

  it('a device list with devices but none SIGNAL/SWITCHED also returns zero groups', () => {
    expect(groupSignalCapableDevicesByLocation([makeMeasured('KOT_1'), makeModulated('KOT_2')])).toEqual([]);
  });

  it('an id with no underscore groups under its own full id', () => {
    const groups = groupSignalCapableDevicesByLocation([makeSignal('STANDALONE')]);
    expect(groups.length).toBe(1);
    expect(groups[0].location).toBe('STANDALONE');
  });
});

describe('SignalPanelWizard.buildSignalPanelRowsFromSelection', () => {
  // 21. confirming with 4 selected items adds exactly 4 rows
  it('confirming with 4 selected devices adds exactly 4 rows', () => {
    const devices: Device[] = [
      makeSignal('KOT_1'), makeSignal('KOT_2'),
      makeSwitched('BRAMA_1'), makeSwitched('BRAMA_2'), makeSignal('BRAMA_3')
    ];
    const groups = groupSignalCapableDevicesByLocation(devices);
    const selected = new Set(['KOT_1', 'KOT_2', 'BRAMA_1', 'BRAMA_2']); // everything but BRAMA_3
    const rows = buildSignalPanelRowsFromSelection(groups, selected);
    expect(rows.length).toBe(4);
    expect(rows.map(r => r.device).sort()).toEqual(['BRAMA_1', 'BRAMA_2', 'KOT_1', 'KOT_2']);
  });

  it('adds rows in TREE order (group order, then device order), not selection/click order', () => {
    const devices: Device[] = [makeSignal('KOT_1'), makeSignal('KOT_2'), makeSwitched('BRAMA_1')];
    const groups = groupSignalCapableDevicesByLocation(devices);
    // Selected in reverse-click order (BRAMA_1 clicked first): the
    // resulting rows must still follow KOT-then-BRAMA, 1-then-2 order.
    const selected = new Set(['BRAMA_1', 'KOT_1', 'KOT_2']);
    const rows = buildSignalPanelRowsFromSelection(groups, selected);
    expect(rows.map(r => r.device)).toEqual(['KOT_1', 'KOT_2', 'BRAMA_1']);
  });

  it('an empty selection adds zero rows, without throwing', () => {
    const groups = groupSignalCapableDevicesByLocation([makeSignal('KOT_1')]);
    expect(() => buildSignalPanelRowsFromSelection(groups, new Set())).not.toThrow();
    expect(buildSignalPanelRowsFromSelection(groups, new Set())).toEqual([]);
  });

  it('a new row from the wizard has an empty label, device set, and a default manualState - only device matters for a linked row', () => {
    const groups = groupSignalCapableDevicesByLocation([makeSignal('KOT_1')]);
    const rows = buildSignalPanelRowsFromSelection(groups, new Set(['KOT_1']));
    expect(rows[0]).toEqual({ device: 'KOT_1', label: '', manualState: 'OFF' });
  });
});
