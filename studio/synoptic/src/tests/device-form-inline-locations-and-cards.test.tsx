/** @vitest-environment jsdom */
// fix/inline-device-creation commit 2: locations and cards can be added
// without leaving the device form - AddLocationDialog.tsx (next to the
// location <select>) and AddCardDialog.tsx (opened from
// ChannelAddressPicker.tsx's own "+ Karta" button). Both use the exact
// same check-then-save path as DeviceRegistriesDialog.tsx's own Add
// row (checkAddLocation/checkAddCard, DeviceRegistryMutations.ts) -
// mandatory test 6 confirms the SAME error code, not merely a similar
// message, comes back for a duplicate.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { DeviceFormDialog } from '../components/DeviceFormDialog';
import { AddLocationDialog } from '../components/AddLocationDialog';
import { checkAddLocation } from '../project/DeviceRegistryMutations';

function resetStore() {
  useStore.setState({
    locations: [],
    cards: [],
    devices: []
  });
}

describe('4/5. adding a location from the device form appends it to the registry and selects it immediately', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('appends the new location to the store and selects it in the form, without losing the already-typed designation', () => {
    render(<DeviceFormDialog mode="add" onSave={() => {}} onCancel={() => {}} />);

    // Already-filled field, per Commit 2's own requirement that adding
    // a location must not lose it.
    fireEvent.change(screen.getByPlaceholderText('-K1'), { target: { value: '-K9' } });

    fireEvent.click(screen.getByTitle('Add new location'));
    fireEvent.change(screen.getByPlaceholderText('KOT'), { target: { value: 'KOT' } });
    fireEvent.change(screen.getByPlaceholderText('Boiler room'), { target: { value: 'Boiler room' } });
    fireEvent.click(screen.getByText('Add'));

    // 4: appended to the registry.
    expect(useStore.getState().locations).toEqual([{ code: 'KOT', description: 'Boiler room' }]);

    // 5: immediately selected in the form's own location <select>.
    const locationSelect = screen.getByDisplayValue('KOT') as HTMLSelectElement;
    expect(locationSelect.tagName).toBe('SELECT');

    // The designation typed before opening the mini-dialog survived.
    expect((screen.getByPlaceholderText('-K1') as HTMLInputElement).value).toBe('-K9');
  });
});

describe('6. a duplicate location code is rejected with the same error code the Registries window itself would report', () => {
  beforeEach(() => {
    useStore.setState({ locations: [{ code: 'KOT', description: 'Boiler room' }], cards: [], devices: [] });
  });
  afterEach(cleanup);

  it('shows an error and does not add a second KOT entry', () => {
    let added: string | null = null;
    render(<AddLocationDialog onAdded={(code) => { added = code; }} onCancel={() => {}} />);

    fireEvent.change(screen.getByPlaceholderText('KOT'), { target: { value: 'KOT' } });
    fireEvent.change(screen.getByPlaceholderText('Boiler room'), { target: { value: 'Boiler room 2' } });
    fireEvent.click(screen.getByText('Add'));

    expect(added).toBeNull();
    expect(useStore.getState().locations).toHaveLength(1);

    // Same function DeviceRegistriesDialog.tsx's own Add row calls -
    // proving the code shown here is not a second, independently
    // invented one.
    const outcome = checkAddLocation({ code: 'KOT', description: 'x' }, [{ code: 'KOT', description: 'Boiler room' }], [], []);
    expect(outcome.ok).toBe(false);
    if (!outcome.ok) {
      expect(outcome.issue.code).toBe('LOCATION_DUPLICATE_CODE');
      expect(screen.getByText(outcome.issue.message)).toBeTruthy();
    }
  });
});

describe('7. cancelling the mini-dialog changes nothing', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('AddLocationDialog: Cancel calls onCancel, never onAdded, and adds nothing to the store', () => {
    let added = false;
    let cancelled = false;
    render(<AddLocationDialog onAdded={() => { added = true; }} onCancel={() => { cancelled = true; }} />);

    fireEvent.change(screen.getByPlaceholderText('KOT'), { target: { value: 'KOT' } });
    fireEvent.change(screen.getByPlaceholderText('Boiler room'), { target: { value: 'Boiler room' } });
    fireEvent.click(screen.getByText('Cancel'));

    expect(cancelled).toBe(true);
    expect(added).toBe(false);
    expect(useStore.getState().locations).toEqual([]);
  });

  it('the device form itself is untouched by opening then cancelling the location mini-dialog', () => {
    render(<DeviceFormDialog mode="add" onSave={() => {}} onCancel={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText('-K1'), { target: { value: '-K9' } });
    fireEvent.click(screen.getByTitle('Add new location'));
    fireEvent.change(screen.getByPlaceholderText('KOT'), { target: { value: 'ZZZ' } });
    // Two Cancel buttons are on screen now - the mini-dialog's own, and
    // the device form's own footer one, still sitting behind it. The
    // mini-dialog's is the one rendered first (inside the location
    // property-row, ahead of the form's own footer in DOM order).
    fireEvent.click(screen.getAllByText('Cancel')[0]);

    expect(useStore.getState().locations).toEqual([]);
    expect((screen.getByPlaceholderText('-K1') as HTMLInputElement).value).toBe('-K9');
    // The mini-dialog itself is gone, back to the plain form.
    expect(screen.queryByPlaceholderText('KOT')).toBeNull();
  });
});

describe('8. adding a card from the device form appends it and selects its first channel immediately', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('a fresh SWITCHED device\'s doClose picker can add a DO card and gets it selected at channel 1', () => {
    render(<DeviceFormDialog mode="add" onSave={() => {}} onCancel={() => {}} />);

    // Default behavior is SWITCHED (defaultSwitchedFields), feedback
    // mode NONE - so doClose's ChannelAddressPicker (expectedKind DO)
    // is the only one actually rendered with a visible "+ Karta".
    fireEvent.click(screen.getByTitle('Add a new DO card'));
    fireEvent.change(screen.getByPlaceholderText('ELA1'), { target: { value: 'ADA1' } });
    fireEvent.change(screen.getByPlaceholderText('ELA01'), { target: { value: 'ADA01' } });
    fireEvent.click(screen.getByText('Add'));

    expect(useStore.getState().cards).toEqual([{ id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 16 }]);

    // Selected immediately: the card <select> now shows ADA1 and the
    // channel <select> shows 1 - i.e. the field's own value is
    // 'ADA1.DO.1', not left blank for the user to pick by hand.
    expect(screen.getByDisplayValue('ADA1')).toBeTruthy();
    expect(screen.getAllByDisplayValue('1').length).toBeGreaterThan(0);
  });
});
