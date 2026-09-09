// feat/selector-symbol-setpoint-alarm - the setpoint panel: a screen
// element for MODULATED devices, mirroring the meter element's own
// structure (src/meter/MeterElement.ts/MeterResolver.ts) closely. Same
// split as group-command-element.test.ts: pure resolver logic first,
// then store wiring (add/update/delete, selection, clipboard, undo).

import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import {
  getSetpointCapableDevices, getSetpointPreviewValue, formatSetpointValue,
  resolveSetpointRow, getSetpointDanglingRows
} from '../elements/SetpointResolver';
import { clampSetpointWidth, SETPOINT_MIN_WIDTH, SETPOINT_MAX_WIDTH, computeSetpointHeight, formatManualSetpointValue } from '../elements/SetpointElement';
import type { SetpointPanelElement, SetpointRow } from '../elements/SetpointElement';
import type { Device, ModulatedDevice, MeasuredDevice } from '../project/DeviceSchema';

function makeModulated(overrides: Partial<ModulatedDevice> = {}): ModulatedDevice {
  return {
    id: 'KOT_TV1', designation: '-TV1', name: 'Zawor modulowany', behavior: 'MODULATED', kind: 'valve', publishToHa: false,
    setpointOutput: 'ADA1.AO.1', unit: '%', rangeMin: 0, rangeMax: 100, startupValue: 25, safeValue: 0,
    ...overrides
  };
}

function makeMeasured(): MeasuredDevice {
  return {
    id: 'KOT_TT1', designation: '-TT1', name: 'Czujnik', behavior: 'MEASURED', kind: 'sensor', publishToHa: false,
    input: 'ELA1.AI.1', unit: 'C', rangeMin: 0, rangeMax: 100, format: '0.0', deadband: 1
  };
}

function makeRow(overrides: Partial<SetpointRow> = {}): SetpointRow {
  return { device: '', label: '', manualValue: '', manualUnit: '', ...overrides };
}

function makePanel(overrides: Partial<SetpointPanelElement> = {}): SetpointPanelElement {
  return { id: 'S1', x: 0, y: 0, width: 200, fontSize: 13, rows: [], ...overrides };
}

describe('SetpointElement geometry', () => {
  it('clampSetpointWidth keeps a width within [min, max]', () => {
    expect(clampSetpointWidth(10)).toBe(SETPOINT_MIN_WIDTH);
    expect(clampSetpointWidth(10000)).toBe(SETPOINT_MAX_WIDTH);
    expect(clampSetpointWidth(200)).toBe(200);
  });

  it('computeSetpointHeight grows with row count and never throws for zero rows', () => {
    const empty = computeSetpointHeight(makePanel({ rows: [] }));
    const withRows = computeSetpointHeight(makePanel({ rows: [makeRow(), makeRow()] }));
    expect(empty).toBeGreaterThan(0);
    expect(withRows).toBeGreaterThan(empty);
  });

  it('formatManualSetpointValue joins value and unit, empty when both are blank', () => {
    expect(formatManualSetpointValue(makeRow({ manualValue: '45', manualUnit: '%' }))).toBe('45 %');
    expect(formatManualSetpointValue(makeRow())).toBe('');
  });
});

describe('SetpointResolver - which devices are settable', () => {
  it('getSetpointCapableDevices keeps only MODULATED devices', () => {
    const devices: Device[] = [makeModulated(), makeMeasured()];
    expect(getSetpointCapableDevices(devices).map(d => d.id)).toEqual(['KOT_TV1']);
  });
});

describe('SetpointResolver - preview value and formatting', () => {
  it('previews the device\'s own startupValue, not a range midpoint', () => {
    const device = makeModulated({ startupValue: 25, rangeMin: 0, rangeMax: 100 });
    expect(getSetpointPreviewValue(device)).toBe(25);
  });

  it('formatSetpointValue always shows one decimal place (MODULATED has no format string of its own)', () => {
    expect(formatSetpointValue(25)).toBe('25.0');
    expect(formatSetpointValue(25.456)).toBe('25.5');
  });
});

describe('SetpointResolver.resolveSetpointRow', () => {
  it('a row pointing at a MODULATED device falls back to its designation when the row label is empty', () => {
    const device = makeModulated({ id: 'KOT_TV1', designation: '-TV7' });
    const row = makeRow({ device: 'KOT_TV1', label: '' });
    const display = resolveSetpointRow(row, [device]);
    expect(display.label).toBe('-TV7');
    expect(display.valueText).toBe('25.0 %');
    expect(display.colorKind).toBe('PREVIEW');
  });

  it('a non-empty row label overrides the device designation', () => {
    const device = makeModulated({ id: 'KOT_TV1' });
    const row = makeRow({ device: 'KOT_TV1', label: 'Naciag pasa' });
    expect(resolveSetpointRow(row, [device]).label).toBe('Naciag pasa');
  });

  it('a row pointing at a MEASURED device is rejected - resolves the same as a missing device', () => {
    const device = makeMeasured();
    const row = makeRow({ device: 'KOT_TT1' });
    const display = resolveSetpointRow(row, [device]);
    expect(display.valueText).toBe('?');
    expect(display.colorKind).toBe('MISSING');
  });

  it('a row pointing at a non-existent device resolves to "?" without throwing', () => {
    const row = makeRow({ device: 'GHOST' });
    expect(() => resolveSetpointRow(row, [])).not.toThrow();
    expect(resolveSetpointRow(row, []).colorKind).toBe('MISSING');
  });

  it('a manual row (no device) is untouched by device resolution', () => {
    const row = makeRow({ manualValue: '45', manualUnit: '%', label: 'Manual' });
    const display = resolveSetpointRow(row, [makeModulated()]);
    expect(display.valueText).toBe('45 %');
    expect(display.label).toBe('Manual');
    expect(display.colorKind).toBe('NORMAL');
  });
});

describe('SetpointResolver.getSetpointDanglingRows', () => {
  it('flags a row pointing at a non-existent device and a MEASURED device - not a MODULATED one', () => {
    const panel = { rows: [makeRow({ device: '' }), makeRow({ device: 'GHOST' }), makeRow({ device: 'KOT_TT1' }), makeRow({ device: 'KOT_TV1' })] };
    const devices: Device[] = [makeMeasured(), makeModulated()];
    const issues = getSetpointDanglingRows(panel, devices);
    expect(issues.map(i => i.rowIndex)).toEqual([1, 2]);
  });

  it('never throws for an empty row list', () => {
    expect(() => getSetpointDanglingRows({ rows: [] }, [])).not.toThrow();
    expect(getSetpointDanglingRows({ rows: [] }, [])).toEqual([]);
  });
});

// ---- Store wiring: CRUD, selection, clipboard, delete ----

function resetStore() {
  useStore.setState({
    objects: [], connections: [], meters: [], signalPanels: [], frames: [], groupCommands: [], setpointPanels: [],
    selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: [],
    clipboard: [], clipboardMeters: [], clipboardSignalPanels: [], clipboardFrames: [], clipboardGroupCommands: [], clipboardSetpointPanels: [], clipboardConnections: [],
    history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [], groupCommands: [], setpointPanels: [] }],
    historyIndex: 0
  });
}

describe('Store wiring for setpointPanels', () => {
  beforeEach(resetStore);

  it('addSetpointPanel assigns a fresh id and appends to the array', () => {
    useStore.getState().addSetpointPanel({ x: 10, y: 20, width: 200, fontSize: 13, rows: [] });
    const list = useStore.getState().setpointPanels;
    expect(list.length).toBe(1);
    expect(list[0].id).toBeTruthy();
  });

  it('updateSetpointPanel merges partial updates without touching other fields', () => {
    useStore.getState().addSetpointPanel({ x: 10, y: 20, width: 200, fontSize: 13, rows: [], title: 'A' });
    const id = useStore.getState().setpointPanels[0].id;
    useStore.getState().updateSetpointPanel(id, { title: 'Renamed' });
    const updated = useStore.getState().setpointPanels[0];
    expect(updated.title).toBe('Renamed');
    expect(updated.x).toBe(10);
  });

  it('selectSetpointPanels replaces the selection and clears every other kind (non-multi)', () => {
    useStore.setState({ selectedIds: ['obj1'] });
    useStore.getState().addSetpointPanel({ x: 0, y: 0, width: 200, fontSize: 13, rows: [] });
    const id = useStore.getState().setpointPanels[0].id;
    useStore.getState().selectSetpointPanels([id], false);
    expect(useStore.getState().selectedSetpointPanelIds).toEqual([id]);
    expect(useStore.getState().selectedIds).toEqual([]);
  });

  it('deleteObjects removes a setpoint panel by id and clears its selection', () => {
    useStore.getState().addSetpointPanel({ x: 0, y: 0, width: 200, fontSize: 13, rows: [] });
    const id = useStore.getState().setpointPanels[0].id;
    useStore.getState().selectSetpointPanels([id], false);
    useStore.getState().deleteObjects([], [], [], [], [], [], [id]);
    expect(useStore.getState().setpointPanels).toEqual([]);
    expect(useStore.getState().selectedSetpointPanelIds).toEqual([]);
  });

  it('copySelected + paste clones a setpoint panel with a fresh id, offset, and re-selects the copy', () => {
    useStore.getState().addSetpointPanel({ x: 0, y: 0, width: 200, fontSize: 13, rows: [{ device: 'KOT_TV1', label: '', manualValue: '', manualUnit: '' }] });
    const originalId = useStore.getState().setpointPanels[0].id;
    useStore.getState().selectSetpointPanels([originalId], false);
    useStore.getState().copySelected();
    useStore.getState().paste();

    const all = useStore.getState().setpointPanels;
    expect(all.length).toBe(2);
    const pasted = all.find(p => p.id !== originalId)!;
    expect(pasted.rows).toEqual([{ device: 'KOT_TV1', label: '', manualValue: '', manualUnit: '' }]);
    expect(pasted.x).toBeGreaterThan(0);
    expect(useStore.getState().selectedSetpointPanelIds).toEqual([pasted.id]);
  });

  it('duplicateSetpointPanelInPlace leaves an unselected clone at the exact same position', () => {
    useStore.getState().addSetpointPanel({ x: 50, y: 50, width: 200, fontSize: 13, rows: [] });
    const originalId = useStore.getState().setpointPanels[0].id;
    useStore.getState().duplicateSetpointPanelInPlace(originalId);
    const all = useStore.getState().setpointPanels;
    expect(all.length).toBe(2);
    const clone = all.find(p => p.id !== originalId)!;
    expect(clone.x).toBe(50);
    expect(clone.y).toBe(50);
  });

  it('undo restores a deleted setpoint panel', () => {
    useStore.getState().addSetpointPanel({ x: 0, y: 0, width: 200, fontSize: 13, rows: [] });
    const id = useStore.getState().setpointPanels[0].id;
    useStore.getState().deleteObjects([], [], [], [], [], [], [id]);
    expect(useStore.getState().setpointPanels).toEqual([]);
    useStore.getState().undo();
    expect(useStore.getState().setpointPanels.map(p => p.id)).toEqual([id]);
  });
});
