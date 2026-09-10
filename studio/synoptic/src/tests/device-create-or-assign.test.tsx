/** @vitest-environment jsdom */
// fix/inline-device-creation commit 3: double-clicking a device-less
// symbol opens DeviceFormDialog's own "create or assign" mode -
// CREATE NEW (default, the ordinary add form with behavior/id/
// designation suggested from the symbol's own type) or PRZYPISZ
// ISTNIEJACY (a searchable, pre-filtered list of project devices).
// Mandatory tests 9-18.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import type { SynopticObject } from '../store';
import { handleSymbolDblClick } from '../components/canvas/ObjectNode';
import { DeviceFormDialog } from '../components/DeviceFormDialog';
import { AssignExistingDeviceList } from '../components/AssignExistingDeviceList';
import { suggestBehaviorForSymbolType } from '../project/SymbolBehaviorMapping';
import { suggestNextDeviceIdSuffix, suggestNextDesignation } from '../project/DeviceCreationSuggestions';
import { createAndAssignDevice, assignExistingDeviceById } from '../project/DeviceFormSync';
import type { Device, SwitchedDevice } from '../project/DeviceSchema';

function makeObj(overrides: Partial<SynopticObject> = {}): SynopticObject {
  return {
    id: 'OBJ1', type: 'electrical.disconnect_switch', category: 'Electrical',
    x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 1,
    tag: 'OBJ1', description: '', color: '#000', fill: '#000', border: '#000',
    text: '', font: 'Arial', fontSize: 12, tooltip: '',
    width: 64, height: 64, customProperties: {},
    ...overrides
  };
}

function makeSwitched(overrides: Partial<SwitchedDevice> = {}): SwitchedDevice {
  return {
    id: 'KOT_KMG1', designation: '-K1', name: 'Stycznik grzalki', behavior: 'SWITCHED', kind: 'contactor', publishToHa: false,
    feedback: { mode: 'NONE' }, command: { outputCount: 1, style: 'MAINTAINED', doClose: 'ADA1.DO.1' },
    supervision: { confirmTimeoutMs: 1000, discrepancyAlarm: false },
    safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' }, switchCounter: false,
    ...overrides
  };
}

// fix/device-form-polish commit 2: Save is aria-disabled now, not
// natively disabled - see device-form-dialog-switched.test.tsx's own
// copy of this helper for the full reasoning.
function isSaveDisabled(): boolean {
  return screen.getByRole('button', { name: 'Save' }).getAttribute('aria-disabled') === 'true';
}

function resetStore() {
  useStore.setState({
    objects: [], devices: [], messages: [], locations: [{ code: 'KOT', description: 'Boiler room' }], cards: [],
    deviceFormRequest: null, deviceCreateOrAssignRequest: null, isDrawingConnection: false
  });
}

describe('9. double-click on a device-less symbol opens CREATE NEW mode by default', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('sets deviceCreateOrAssignRequest (not deviceFormRequest, no Messages notice)', () => {
    const obj = makeObj({ id: 'OBJ1', type: 'electrical.disconnect_switch', designation: '-Q1' });
    handleSymbolDblClick({ cancelBubble: false }, obj);

    const req = useStore.getState().deviceCreateOrAssignRequest;
    expect(req).toEqual({ symbolId: 'OBJ1', symbolType: 'electrical.disconnect_switch', sourceContext: expect.stringContaining('-Q1') });
    expect(useStore.getState().deviceFormRequest).toBeNull();
    expect(useStore.getState().messages).toEqual([]);
  });

  it('DeviceFormDialog renders in CREATE NEW mode by default, with the mode switcher visible and the header showing where it was opened from', () => {
    render(
      <DeviceFormDialog
        mode="add"
        sourceContext="Diagram, symbol -Q1"
        creationContext={{ symbolType: 'electrical.disconnect_switch', onAssignExisting: () => {} }}
        onSave={() => {}}
        onCancel={() => {}}
      />
    );
    expect(screen.getByText('Create New')).toBeTruthy();
    expect(screen.getByText('Assign Existing')).toBeTruthy();
    expect(screen.getByText('Diagram, symbol -Q1')).toBeTruthy();
    // CREATE NEW's own body (the ordinary form) is showing, not the
    // assign list's search box.
    expect(screen.queryByPlaceholderText('Search by id, designation or name...')).toBeNull();
    expect(screen.getByPlaceholderText('-K1')).toBeTruthy();
  });
});

describe('10/11/12. behavior suggestion from the symbol\'s own type (SymbolBehaviorMapping.ts)', () => {
  afterEach(cleanup);

  it('10: a disconnect-switch symbol suggests SWITCHED', () => {
    expect(suggestBehaviorForSymbolType('electrical.disconnect_switch')).toBe('SWITCHED');
  });

  it('11: a temperature-sensor symbol suggests MEASURED', () => {
    expect(suggestBehaviorForSymbolType('instrumentation.temperature_sensor')).toBe('MEASURED');
  });

  it('12: a symbol outside the mapping suggests nothing, and the form leaves Behaviour unchosen (Save disabled) until the user picks one', () => {
    expect(suggestBehaviorForSymbolType('water.tank')).toBeUndefined();

    resetStore();
    render(
      <DeviceFormDialog
        mode="add"
        creationContext={{ symbolType: 'water.tank', onAssignExisting: () => {} }}
        onSave={() => {}}
        onCancel={() => {}}
      />
    );
    expect(screen.getByText('-- select --')).toBeTruthy();
    expect(isSaveDisabled()).toBe(true);
  });
});

describe('13/14. next-free-id suggestion (DeviceCreationSuggestions.ts)', () => {
  it('13: with existing KOT_KMG1 and KOT_KMG2 (both kind "contactor"), a new contactor in KOT suggests KOT_KMG3\'s own suffix, KMG3', () => {
    const devices = [
      makeSwitched({ id: 'KOT_KMG1', kind: 'contactor' }),
      makeSwitched({ id: 'KOT_KMG2', kind: 'contactor' }),
    ];
    expect(suggestNextDeviceIdSuffix('KOT', 'contactor', devices)).toBe('KMG3');
  });

  it('14: with no devices at all in the location, the suggested number is 1', () => {
    expect(suggestNextDeviceIdSuffix('KOT', 'contactor', [])).toMatch(/1$/);
  });

  it('designation suggestion follows the same shape: -K1, -K2 existing suggests -K3; none existing suggests -K1 for a SWITCHED device', () => {
    const devices = [
      makeSwitched({ id: 'KOT_KMG1', kind: 'contactor', designation: '-K1' }),
      makeSwitched({ id: 'KOT_KMG2', kind: 'contactor', designation: '-K2' }),
    ];
    expect(suggestNextDesignation('KOT', 'SWITCHED', 'contactor', devices)).toBe('-K3');
    expect(suggestNextDesignation('KOT', 'SWITCHED', 'contactor', [])).toBe('-K1');
    expect(suggestNextDesignation('KOT', 'MEASURED', 'temperature_sensor', [])).toBe('-B1');
  });
});

describe('15. saving in CREATE NEW creates the device AND assigns it to the originating symbol', () => {
  it('createAndAssignDevice calls addDevice then updateObject then saveHistory, one Messages confirmation', () => {
    const calls: string[] = [];
    const store = {
      addDevice: (d: Device) => calls.push(`addDevice:${d.id}`),
      updateObject: (id: string, updates: { deviceId?: string }) => calls.push(`updateObject:${id}:${updates.deviceId}`),
      saveHistory: () => calls.push('saveHistory'),
      addMessage: (text: string) => calls.push(`addMessage:${text}`),
    };
    const device = makeSwitched({ id: 'KOT_KMG3', designation: '-K3' });

    createAndAssignDevice(store, 'OBJ1', device);

    expect(calls[0]).toBe('addDevice:KOT_KMG3');
    expect(calls[1]).toBe('updateObject:OBJ1:KOT_KMG3');
    expect(calls[2]).toBe('saveHistory');
    expect(calls[3]).toContain('-K3');
  });
});

describe('16. ASSIGN EXISTING assigns the chosen device without creating a new one', () => {
  it('assignExistingDeviceById never calls addDevice, only updateObject + saveHistory + a Messages confirmation', () => {
    const calls: string[] = [];
    const store = {
      addDevice: (d: Device) => calls.push(`addDevice:${d.id}`), // must never be called
      updateObject: (id: string, updates: { deviceId?: string }) => calls.push(`updateObject:${id}:${updates.deviceId}`),
      saveHistory: () => calls.push('saveHistory'),
      addMessage: (text: string) => calls.push(`addMessage:${text}`),
      devices: [makeSwitched({ id: 'KOT_KMG1' })],
    };

    assignExistingDeviceById(store, 'OBJ2', 'KOT_KMG1');

    expect(calls[0]).toBe('updateObject:OBJ2:KOT_KMG1');
    expect(calls[1]).toBe('saveHistory');
    expect(calls[2]).toContain('-K1');
    expect(calls.some(c => c.startsWith('addDevice'))).toBe(false);
  });

  it('a missing device (deleted meanwhile) is a no-op, never throws', () => {
    const store = { addDevice: () => {}, updateObject: () => { throw new Error('must not be called'); }, saveHistory: () => {}, addMessage: () => {}, devices: [] as Device[] };
    expect(() => assignExistingDeviceById(store, 'OBJ1', 'GHOST')).not.toThrow();
  });
});

describe('17. search in ASSIGN EXISTING filters by id, designation and name', () => {
  afterEach(cleanup);

  it('typing a designation shows only the matching device', () => {
    const devices = [
      makeSwitched({ id: 'KOT_KMG1', designation: '-K1', name: 'Stycznik grzalki' }),
      makeSwitched({ id: 'KOT_KMG2', designation: '-K2', name: 'Stycznik pompy' }),
    ];
    render(<AssignExistingDeviceList devices={devices} objects={[]} selectedId={null} onSelect={() => {}} />);

    expect(screen.getByText('KOT_KMG1')).toBeTruthy();
    expect(screen.getByText('KOT_KMG2')).toBeTruthy();

    fireEvent.change(screen.getByPlaceholderText('Search by id, designation or name...'), { target: { value: '-K2' } });

    expect(screen.queryByText('KOT_KMG1')).toBeNull();
    expect(screen.getByText('KOT_KMG2')).toBeTruthy();
  });

  it('pre-filters by the symbol\'s own suggested behavior, and the filter can be turned off', () => {
    const devices = [
      makeSwitched({ id: 'KOT_KMG1' }),
      { id: 'KOT_TT1', designation: '-B1', name: 'Czujnik temperatury', behavior: 'MEASURED', kind: 'temperature_sensor', publishToHa: false, input: 'ELA1.AI.1', unit: '°C', rangeMin: 0, rangeMax: 100, format: '0.0', deadband: 0.5 } as unknown as Device,
    ];
    render(<AssignExistingDeviceList devices={devices} objects={[]} suggestedBehavior="SWITCHED" selectedId={null} onSelect={() => {}} />);

    expect(screen.getByText('KOT_KMG1')).toBeTruthy();
    expect(screen.queryByText('KOT_TT1')).toBeNull();

    fireEvent.click(screen.getByRole('checkbox'));
    expect(screen.getByText('KOT_TT1')).toBeTruthy();
  });
});

describe('18. assigning the same device to a second symbol raises no error', () => {
  afterEach(cleanup);

  it('assignExistingDeviceById succeeds for a second, different symbolId with no thrown error and no error message', () => {
    const calls: string[] = [];
    const store = {
      addDevice: () => {},
      updateObject: (id: string, updates: { deviceId?: string }) => calls.push(`updateObject:${id}:${updates.deviceId}`),
      saveHistory: () => {},
      addMessage: (text: string) => calls.push(text),
      devices: [makeSwitched({ id: 'KOT_KMG1' })],
    };

    expect(() => assignExistingDeviceById(store, 'OBJ1', 'KOT_KMG1')).not.toThrow();
    expect(() => assignExistingDeviceById(store, 'OBJ2', 'KOT_KMG1')).not.toThrow();

    expect(calls).toContain('updateObject:OBJ1:KOT_KMG1');
    expect(calls).toContain('updateObject:OBJ2:KOT_KMG1');
    expect(calls.every(c => !c.toLowerCase().includes('error') && !c.toLowerCase().includes('blad'))).toBe(true);
  });

  it('the assign list itself shows a usage count of 2 for a device already on two symbols, not an error state', () => {
    const devices = [makeSwitched({ id: 'KOT_KMG1' })];
    const objects = [{ deviceId: 'KOT_KMG1' }, { deviceId: 'KOT_KMG1' }];
    render(<AssignExistingDeviceList devices={devices} objects={objects} selectedId={null} onSelect={() => {}} />);
    expect(screen.getByText('2')).toBeTruthy();
  });
});
