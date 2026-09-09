// feat/meter-element part C: the group-by-unit picker's pure logic -
// grouping and bulk row building, independent of the dialog UI itself.

import { describe, it, expect } from 'vitest';
import { groupMeasuredDevicesByUnit, buildRowsFromSelection } from '../meter/MeterWizard';
import type { MeasuredDevice, Device, SwitchedDevice } from '../project/DeviceSchema';

function makeMeasured(id: string, unit: string, overrides: Partial<MeasuredDevice> = {}): MeasuredDevice {
  return {
    id, designation: `-B${id}`, name: `Sensor ${id}`, behavior: 'MEASURED', kind: 'sensor', publishToHa: false,
    input: 'ELA1.AI.1', unit, rangeMin: 0, rangeMax: 100, format: '0.0', deadband: 1,
    ...overrides
  };
}

function makeSwitched(id: string): SwitchedDevice {
  return {
    id, designation: `-K${id}`, name: `Contactor ${id}`, behavior: 'SWITCHED', kind: 'contactor', publishToHa: false,
    feedback: { mode: 'NONE' },
    command: { outputCount: 1, style: 'MAINTAINED', doClose: 'ADA1.DO.1' },
    supervision: { confirmTimeoutMs: 1000, discrepancyAlarm: false },
    safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' },
    switchCounter: false
  };
}

describe('MeterWizard.groupMeasuredDevicesByUnit', () => {
  // 9. three devices in V and two in A yield two groups of size 3 and 2
  it('groups devices by unit - 3 in V and 2 in A yields two groups sized 3 and 2', () => {
    const devices: Device[] = [
      makeMeasured('1', 'V'), makeMeasured('2', 'V'), makeMeasured('3', 'V'),
      makeMeasured('4', 'A'), makeMeasured('5', 'A'),
      makeSwitched('6') // not MEASURED - must not show up in any group
    ];
    const groups = groupMeasuredDevicesByUnit(devices);
    expect(groups.length).toBe(2);
    const byUnit = Object.fromEntries(groups.map(g => [g.unit, g.devices.length]));
    expect(byUnit).toEqual({ V: 3, A: 2 });
  });

  // 10. an empty device list returns zero groups, without throwing
  it('an empty device list returns zero groups without throwing', () => {
    expect(() => groupMeasuredDevicesByUnit([])).not.toThrow();
    expect(groupMeasuredDevicesByUnit([])).toEqual([]);
  });

  it('a device list with devices but none MEASURED also returns zero groups', () => {
    expect(groupMeasuredDevicesByUnit([makeSwitched('1'), makeSwitched('2')])).toEqual([]);
  });

  it('a group\'s device list preserves the designation and name needed for display', () => {
    const groups = groupMeasuredDevicesByUnit([makeMeasured('1', 'V', { designation: '-U1', name: 'Mains voltage' })]);
    expect(groups[0].devices[0].designation).toBe('-U1');
    expect(groups[0].devices[0].name).toBe('Mains voltage');
  });
});

describe('MeterWizard.buildRowsFromSelection', () => {
  // 11. confirming with 4 selected items adds exactly 4 rows
  it('confirming with 4 selected devices adds exactly 4 rows', () => {
    const devices: Device[] = [
      makeMeasured('1', 'V'), makeMeasured('2', 'V'),
      makeMeasured('3', 'A'), makeMeasured('4', 'A'), makeMeasured('5', 'A')
    ];
    const groups = groupMeasuredDevicesByUnit(devices);
    const selected = new Set(['1', '2', '3', '4']); // everything but device 5
    const rows = buildRowsFromSelection(groups, selected);
    expect(rows.length).toBe(4);
    expect(rows.map(r => r.device).sort()).toEqual(['1', '2', '3', '4']);
  });

  it('adds rows in TREE order (group order, then device order), not selection/click order', () => {
    const devices: Device[] = [makeMeasured('1', 'V'), makeMeasured('2', 'V'), makeMeasured('3', 'A')];
    const groups = groupMeasuredDevicesByUnit(devices);
    // Selected in reverse-click order (3 clicked first, then 1): the
    // resulting rows must still follow V-then-A, 1-then-2 tree order.
    const selected = new Set(['3', '1', '2']);
    const rows = buildRowsFromSelection(groups, selected);
    expect(rows.map(r => r.device)).toEqual(['1', '2', '3']);
  });

  it('an empty selection adds zero rows, without throwing', () => {
    const groups = groupMeasuredDevicesByUnit([makeMeasured('1', 'V')]);
    expect(() => buildRowsFromSelection(groups, new Set())).not.toThrow();
    expect(buildRowsFromSelection(groups, new Set())).toEqual([]);
  });

  it('a new row from the wizard has an empty label/manualValue/manualUnit - only device is set', () => {
    const groups = groupMeasuredDevicesByUnit([makeMeasured('1', 'V')]);
    const rows = buildRowsFromSelection(groups, new Set(['1']));
    expect(rows[0]).toEqual({ device: '1', label: '', manualValue: '', manualUnit: '' });
  });
});
