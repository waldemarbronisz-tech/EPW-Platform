/** @vitest-environment jsdom */
// feat/device-list-ui commit 1 - mandatory tests 1-3. Renders the REAL
// DeviceRegistriesDialog against the REAL store, same convention
// properties-cleanup.test.tsx already established.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { DeviceRegistriesDialog } from '../components/DeviceRegistriesDialog';
import type { SwitchedDevice } from '../project/DeviceSchema';

function resetStore() {
  useStore.setState({ locations: [], cards: [], devices: [] });
}

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

describe('DeviceRegistriesDialog (mandatory test 1)', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('test 1: a location code saved in lowercase is rejected (validateDeviceRegistry\'s own LOCATION_INVALID_CODE rule)', () => {
    render(<DeviceRegistriesDialog onClose={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText('KOT'), { target: { value: 'kot' } });
    fireEvent.change(screen.getByPlaceholderText('Kotlownia'), { target: { value: 'Kotlownia' } });
    fireEvent.click(screen.getByText('+ Dodaj'));

    expect(useStore.getState().locations).toEqual([]);
    expect(screen.getByText(/must contain only A-Z and 0-9/)).toBeTruthy();
  });
});

describe('DeviceRegistriesDialog (mandatory test 2)', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('test 2: deleting a location still referenced by a device is blocked', () => {
    useStore.setState({
      locations: [{ code: 'KOT', description: 'Kotlownia' }],
      cards: [{ id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 16 }, { id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 16 }],
      devices: [makeSwitchedDevice()]
    });
    render(<DeviceRegistriesDialog onClose={() => {}} />);

    // A disabled button does not dispatch its click handler at all (the
    // browser itself, not this component, suppresses it) - the deletion
    // is blocked at the button level, and the count is surfaced via its
    // title tooltip, so a click could never reach the delete action.
    const deleteButton = screen.getByRole('button', { name: 'Usun' }) as HTMLButtonElement;
    expect(deleteButton.disabled).toBe(true);
    expect(deleteButton.title).toMatch(/Uzywana przez 1 aparat/);
    fireEvent.click(deleteButton);

    expect(useStore.getState().locations).toHaveLength(1);
  });
});

describe('DeviceRegistriesDialog (mandatory test 3)', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('test 3: deleting a card with a channel still used by a device is blocked', () => {
    useStore.setState({
      locations: [{ code: 'KOT', description: 'Kotlownia' }],
      cards: [{ id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 16 }, { id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 16 }],
      devices: [makeSwitchedDevice()]
    });
    render(<DeviceRegistriesDialog onClose={() => {}} />);
    fireEvent.click(screen.getByText('Karty'));

    const deleteButtons = screen.getAllByRole('button', { name: 'Usun' }) as HTMLButtonElement[];
    // ELA1 is used (feedback.diClosed/diOpen), ADA1 is used (command.doClose) - both rows disabled.
    expect(deleteButtons).toHaveLength(2);
    for (const btn of deleteButtons) {
      expect(btn.disabled).toBe(true);
      expect(btn.title).toMatch(/Uzywana przez 1 aparat/);
      fireEvent.click(btn);
    }

    expect(useStore.getState().cards).toHaveLength(2);
  });
});
