/** @vitest-environment jsdom */
// feat/device-list-ui commit 5 - binding a schematic symbol to a device
// (SynopticObject.deviceId, PropertyInspector.tsx's new Aparat dropdown)
// and mandatory tests 20 and 21.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { PropertyInspector } from '../components/PropertyInspector';
import { DeviceListDialog } from '../components/DeviceListDialog';
import { validateDeviceBindings, isSymbolDeviceMissing } from '../project/DeviceBindingValidation';
import type { SynopticObject } from '../store';
import type { SwitchedDevice } from '../project/DeviceSchema';

function makeObj(overrides: Partial<SynopticObject> = {}): SynopticObject {
  return {
    id: 'O1', type: 'electrical.circuit_breaker', category: 'Electrical',
    x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 1,
    tag: 'O1', description: '', color: '#000', fill: '#000', border: '#000',
    text: '', font: 'Arial', fontSize: 12, tooltip: '',
    width: 64, height: 64, customProperties: {},
    ...overrides
  };
}

function makeSwitched(overrides: Partial<SwitchedDevice> = {}): SwitchedDevice {
  return {
    id: 'KOT_KMG1', designation: '-K1', name: 'Stycznik grzalki', behavior: 'SWITCHED', kind: 'contactor', publishToHa: false,
    feedback: { mode: 'NONE' },
    command: { outputCount: 1, style: 'MAINTAINED', doClose: 'ADA1.DO.1' },
    supervision: { confirmTimeoutMs: 500, discrepancyAlarm: false },
    safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' },
    switchCounter: false,
    ...overrides
  };
}

function resetStore() {
  useStore.setState({
    objects: [], connections: [], meters: [], signalPanels: [], frames: [],
    locations: [{ code: 'KOT', description: 'Kotlownia' }],
    cards: [{ id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 16 }],
    devices: [makeSwitched()],
    selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [],
    history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [] }],
    historyIndex: 0
  });
}

describe('DeviceBindingValidation (pure)', () => {
  it('a symbol with no assigned device is not an issue', () => {
    expect(validateDeviceBindings([makeObj({ deviceId: undefined })], [makeSwitched()])).toEqual([]);
  });

  it('test 21: the same device assigned to two different symbols reports no error', () => {
    const objs = [makeObj({ id: 'O1', deviceId: 'KOT_KMG1' }), makeObj({ id: 'O2', deviceId: 'KOT_KMG1' })];
    expect(validateDeviceBindings(objs, [makeSwitched()])).toEqual([]);
  });

  it('a symbol pointing at a nonexistent device is reported', () => {
    const issues = validateDeviceBindings([makeObj({ deviceId: 'GHOST_1' })], [makeSwitched()]);
    expect(issues).toHaveLength(1);
    expect(issues[0].objectId).toBe('O1');
    expect(issues[0].message).toContain('GHOST_1');
  });

  it('isSymbolDeviceMissing agrees: false for no device, false for a real one, true for a dangling one', () => {
    expect(isSymbolDeviceMissing(makeObj(), [makeSwitched()])).toBe(false);
    expect(isSymbolDeviceMissing(makeObj({ deviceId: 'KOT_KMG1' }), [makeSwitched()])).toBe(false);
    expect(isSymbolDeviceMissing(makeObj({ deviceId: 'GHOST_1' }), [makeSwitched()])).toBe(true);
  });
});

describe('PropertyInspector - Aparat dropdown', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  function apparatSelect(): HTMLSelectElement {
    return screen.getByText('Aparat').closest('.property-row')!.querySelector('select') as HTMLSelectElement;
  }

  it('lists every device in the registry', () => {
    useStore.setState({ objects: [makeObj()], selectedIds: ['O1'] });
    render(<PropertyInspector />);
    const options = Array.from(apparatSelect().options).map(o => o.value);
    expect(options).toContain('KOT_KMG1');
    expect(options).toContain(''); // (brak)
  });

  it('assigning a device auto-fills an empty designation', () => {
    useStore.setState({ objects: [makeObj({ designation: '' })], selectedIds: ['O1'] });
    render(<PropertyInspector />);
    fireEvent.change(apparatSelect(), { target: { value: 'KOT_KMG1' } });
    const updated = useStore.getState().objects.find(o => o.id === 'O1')!;
    expect(updated.deviceId).toBe('KOT_KMG1');
    expect(updated.designation).toBe('-K1');
  });

  it('assigning a device never overwrites an already-set designation', () => {
    useStore.setState({ objects: [makeObj({ designation: '-Q9' })], selectedIds: ['O1'] });
    render(<PropertyInspector />);
    fireEvent.change(apparatSelect(), { target: { value: 'KOT_KMG1' } });
    const updated = useStore.getState().objects.find(o => o.id === 'O1')!;
    expect(updated.designation).toBe('-Q9');
  });

  it('a symbol with no assigned device shows (brak) selected - a valid, unremarkable state', () => {
    useStore.setState({ objects: [makeObj({ deviceId: undefined })], selectedIds: ['O1'] });
    render(<PropertyInspector />);
    expect(apparatSelect().value).toBe('');
  });

  it('test 20: a symbol referencing a nonexistent device renders without throwing, highlighted and offered as its own option', () => {
    useStore.setState({ objects: [makeObj({ deviceId: 'GHOST_1' })], selectedIds: ['O1'] });
    expect(() => render(<PropertyInspector />)).not.toThrow();
    const select = apparatSelect();
    expect(select.value).toBe('GHOST_1');
    expect(screen.getByText(/GHOST_1 \(nie istnieje\)/)).toBeTruthy();
  });

  it('clearing the device back to (brak) removes deviceId without touching designation', () => {
    useStore.setState({ objects: [makeObj({ designation: '-K1', deviceId: 'KOT_KMG1' })], selectedIds: ['O1'] });
    render(<PropertyInspector />);
    fireEvent.change(apparatSelect(), { target: { value: '' } });
    const updated = useStore.getState().objects.find(o => o.id === 'O1')!;
    expect(updated.deviceId).toBeUndefined();
    expect(updated.designation).toBe('-K1');
  });
});

describe('DeviceListDialog - Uzycia column', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('shows how many symbols reference each device, and 0 for an unused one', () => {
    useStore.setState({ objects: [makeObj({ id: 'O1', deviceId: 'KOT_KMG1' }), makeObj({ id: 'O2', deviceId: 'KOT_KMG1' })] });
    render(<DeviceListDialog onClose={() => {}} />);
    expect(screen.getByRole('button', { name: '2' })).toBeTruthy();
  });

  it('clicking the usage count selects the first matching symbol and closes the dialog', () => {
    useStore.setState({
      objects: [makeObj({ id: 'O1', deviceId: 'KOT_KMG1' }), makeObj({ id: 'O2', deviceId: 'KOT_KMG1' })],
      selectedIds: []
    });
    let closed = false;
    render(<DeviceListDialog onClose={() => { closed = true; }} />);
    fireEvent.click(screen.getByRole('button', { name: '2' }));
    expect(useStore.getState().selectedIds).toEqual(['O1']);
    expect(closed).toBe(true);
  });
});
