// feat/meter-element part B: unit/format come from the device, never
// from the row itself; preview values sit at the middle of the
// device's own range; a dangling device reference renders as "?"
// without throwing and is reported separately for the Messages notice.

import { describe, it, expect } from 'vitest';
import {
  getMeasuredDevices, getMeasuredPreviewValue, formatMeasuredValue,
  resolveMeterRow, getMeterDanglingRows
} from '../meter/MeterResolver';
import type { MeasuredDevice, Device, SwitchedDevice } from '../project/DeviceSchema';
import type { MeterElementRow } from '../meter/MeterElement';

function makeMeasured(overrides: Partial<MeasuredDevice> = {}): MeasuredDevice {
  return {
    id: 'DEV1', designation: '-B1', name: 'Test sensor', behavior: 'MEASURED', kind: 'sensor', publishToHa: false,
    input: 'ELA1.AI.1', unit: 'kW', rangeMin: 0, rangeMax: 400, format: '0.0', deadband: 1,
    ...overrides
  };
}

function makeSwitched(overrides: Partial<SwitchedDevice> = {}): SwitchedDevice {
  return {
    id: 'SW1', designation: '-K1', name: 'Test contactor', behavior: 'SWITCHED', kind: 'contactor', publishToHa: false,
    feedback: { mode: 'NONE' },
    command: { outputCount: 1, style: 'MAINTAINED', doClose: 'ADA1.DO.1' },
    supervision: { confirmTimeoutMs: 1000, discrepancyAlarm: false },
    safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' },
    switchCounter: false,
    ...overrides
  };
}

function makeRow(overrides: Partial<MeterElementRow> = {}): MeterElementRow {
  return { device: '', label: '', manualValue: '', manualUnit: '', ...overrides };
}

describe('MeterResolver.getMeasuredDevices', () => {
  it('keeps only MEASURED-behavior devices', () => {
    const devices: Device[] = [makeMeasured({ id: 'M1' }), makeSwitched({ id: 'S1' }), makeMeasured({ id: 'M2' })];
    const measured = getMeasuredDevices(devices);
    expect(measured.map(d => d.id).sort()).toEqual(['M1', 'M2']);
  });
});

describe('MeterResolver preview value at range midpoint', () => {
  // 7. range 0..400 -> 200
  it('a device with range 0 to 400 previews at 200', () => {
    expect(getMeasuredPreviewValue(makeMeasured({ rangeMin: 0, rangeMax: 400 }))).toBe(200);
  });

  // 8. range -20..120 -> 50
  it('a device with range -20 to 120 previews at 50', () => {
    expect(getMeasuredPreviewValue(makeMeasured({ rangeMin: -20, rangeMax: 120 }))).toBe(50);
  });
});

describe('MeterResolver.formatMeasuredValue', () => {
  it('applies the device format string decimal count', () => {
    expect(formatMeasuredValue(200, '0.0')).toBe('200.0');
    expect(formatMeasuredValue(200, '0.00')).toBe('200.00');
    expect(formatMeasuredValue(200, '0')).toBe('200');
  });

  it('falls back to one decimal for an empty/unrecognized format, never throwing', () => {
    expect(() => formatMeasuredValue(200, '')).not.toThrow();
    expect(formatMeasuredValue(200, '')).toBe('200.0');
  });
});

describe('MeterResolver.resolveMeterRow', () => {
  // 4. a row pointing at a MEASURED device takes the unit from the
  // device, not the row - the row itself never carries a unit field
  // for a device-linked row at all (there is no such field to check -
  // this test proves the resolved unit is the DEVICE's).
  it('a row pointing at a MEASURED device takes its unit from the device', () => {
    const device = makeMeasured({ id: 'DEV1', unit: 'kW', rangeMin: 0, rangeMax: 400, format: '0.0' });
    const row = makeRow({ device: 'DEV1' });
    const display = resolveMeterRow(row, [device]);
    expect(display.valueText).toBe('200.0 kW');
    expect(display.colorKind).toBe('PREVIEW');
  });

  it('an empty row label falls back to the device designation', () => {
    const device = makeMeasured({ id: 'DEV1', designation: '-B7' });
    const row = makeRow({ device: 'DEV1', label: '' });
    expect(resolveMeterRow(row, [device]).label).toBe('-B7');
  });

  it('a non-empty row label overrides the device designation', () => {
    const device = makeMeasured({ id: 'DEV1', designation: '-B7' });
    const row = makeRow({ device: 'DEV1', label: 'Custom label' });
    expect(resolveMeterRow(row, [device]).label).toBe('Custom label');
  });

  // 5. a row pointing at a non-existent device renders (no throw) and
  // is flagged
  it('a row pointing at a non-existent device resolves to "?" without throwing', () => {
    const row = makeRow({ device: 'GHOST' });
    expect(() => resolveMeterRow(row, [])).not.toThrow();
    const display = resolveMeterRow(row, []);
    expect(display.valueText).toBe('?');
    expect(display.colorKind).toBe('MISSING');
  });

  it('a row pointing at a device that exists but is not MEASURED also resolves to "?"', () => {
    const row = makeRow({ device: 'SW1' });
    const display = resolveMeterRow(row, [makeSwitched({ id: 'SW1' })]);
    expect(display.valueText).toBe('?');
    expect(display.colorKind).toBe('MISSING');
  });

  // 6. a manual row uses manualValue and manualUnit (already covered in
  // meter-element.test.ts's formatManualRowValue tests; repeated here
  // through the full resolver to prove the device-aware path does not
  // disturb the manual path).
  it('a manual row (no device) is untouched by device resolution', () => {
    const row = makeRow({ manualValue: '42', manualUnit: 'kW' });
    const display = resolveMeterRow(row, [makeMeasured({ id: 'DEV1' })]);
    expect(display.valueText).toBe('42 kW');
    expect(display.colorKind).toBe('NORMAL');
  });
});

describe('MeterResolver.getMeterDanglingRows', () => {
  it('flags a row pointing at a non-existent device, with its row index and device id', () => {
    const meter = { rows: [makeRow({ device: '' }), makeRow({ device: 'GHOST' })] };
    const issues = getMeterDanglingRows(meter, []);
    expect(issues).toEqual([{ rowIndex: 1, deviceId: 'GHOST' }]);
  });

  it('does not flag a manual row or a row resolving to a real MEASURED device', () => {
    const device = makeMeasured({ id: 'DEV1' });
    const meter = { rows: [makeRow({ device: '' }), makeRow({ device: 'DEV1' })] };
    expect(getMeterDanglingRows(meter, [device])).toEqual([]);
  });

  it('never throws for an empty row list', () => {
    expect(() => getMeterDanglingRows({ rows: [] }, [])).not.toThrow();
    expect(getMeterDanglingRows({ rows: [] }, [])).toEqual([]);
  });
});
