/** @vitest-environment jsdom */
// feat/device-list-ui commit 2 - the "Lista aparatow" window, and
// mandatory test 15 (duplicating a device clears id/designation only).

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { DeviceListDialog } from '../components/DeviceListDialog';
import type { SwitchedDevice } from '../project/DeviceSchema';

function makeSwitchedDevice(overrides: Partial<SwitchedDevice> = {}): SwitchedDevice {
  return {
    id: 'KOT_KMG1', designation: '-K1', name: 'Stycznik grzalki', behavior: 'SWITCHED', kind: 'contactor', publishToHa: false,
    feedback: { mode: 'DUAL', diClosed: 'ELA1.DI.1', diOpen: 'ELA1.DI.2' },
    command: { outputCount: 1, style: 'MAINTAINED', doClose: 'ADA1.DO.1' },
    supervision: { confirmTimeoutMs: 500, discrepancyAlarm: false },
    safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' },
    switchCounter: false,
    ...overrides
  };
}

function resetStore() {
  useStore.setState({
    locations: [{ code: 'KOT', description: 'Kotlownia' }],
    cards: [
      { id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 16 },
      { id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 16 }
    ],
    devices: [makeSwitchedDevice()]
  });
}

describe('DeviceListDialog', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('lists the device with its id, designation, name and behavior', () => {
    render(<DeviceListDialog onClose={() => {}} />);
    expect(screen.getByText('KOT_KMG1')).toBeTruthy();
    expect(screen.getByText('-K1')).toBeTruthy();
    expect(screen.getByText('Stycznik grzalki')).toBeTruthy();
    // 'SWITCHED' also appears once as a <option> in the behavior filter.
    expect(screen.getAllByText('SWITCHED').length).toBeGreaterThanOrEqual(1);
  });

  it('the status bar reports device count and channel usage', () => {
    render(<DeviceListDialog onClose={() => {}} />);
    // 1 device, 0 validation errors (the seeded device is fully valid).
    expect(screen.getByText(/Aparaty: 1/)).toBeTruthy();
    expect(screen.getByText(/Bledy: 0/)).toBeTruthy();
  });

  it('test 15: duplicating a device opens a new draft with id and designation cleared, everything else unchanged', () => {
    render(<DeviceListDialog onClose={() => {}} />);
    fireEvent.click(screen.getByText('KOT_KMG1'));
    fireEvent.click(screen.getByRole('button', { name: 'Duplikuj' }));

    // The new-device form is open (title says "Nowy aparat", not "Edycja") -
    // designation is blank...
    expect(screen.getByText('Nowy aparat')).toBeTruthy();
    const designationInput = screen.getByPlaceholderText('-K1') as HTMLInputElement;
    expect(designationInput.value).toBe('');
    // ...the suffix part of the id is blank too (location dropdown is its
    // own separate control, not asserted here)...
    const suffixInput = screen.getByPlaceholderText('KMG1') as HTMLInputElement;
    expect(suffixInput.value).toBe('');
    // ...but the name carried over from the original device.
    const nameInput = screen.getByDisplayValue('Stycznik grzalki') as HTMLInputElement;
    expect(nameInput).toBeTruthy();
  });

  it('deleting the selected device removes it after confirmation', () => {
    const originalConfirm = window.confirm;
    window.confirm = () => true;
    try {
      render(<DeviceListDialog onClose={() => {}} />);
      fireEvent.click(screen.getByText('KOT_KMG1'));
      fireEvent.click(screen.getByRole('button', { name: 'Usun' }));
      expect(useStore.getState().devices).toHaveLength(0);
    } finally {
      window.confirm = originalConfirm;
    }
  });
});
