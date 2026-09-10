/** @vitest-environment jsdom */
// feat/control-elements commit 1 - the SELECTOR section of DeviceFormDialog.
// Same conventions as device-form-dialog-signal.test.tsx.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { DeviceFormDialog } from '../components/DeviceFormDialog';
import type { SelectorDevice } from '../project/DeviceSchema';

function makeSelector(overrides: Partial<SelectorDevice> = {}): SelectorDevice {
  return {
    id: 'KOT_HOA1', designation: '-SA1', name: 'Przelacznik reka-0-automat', behavior: 'SELECTOR', kind: 'selector_switch', publishToHa: false,
    // fix/audit-findings commit 1: feedback on positions[0] and [2],
    // none on [1] - same fixture shape selector-device.test.ts's own
    // makeSelector() already uses. A SELECTOR with feedback nowhere at
    // all is now rejected (SELECTOR_NO_FEEDBACK_AT_ALL), so a "fully
    // valid" default fixture must have at least one - two, so removing
    // either end position (as one test below does) still leaves one.
    positions: [{ name: 'MANUAL', feedback: 'ELA1.DI.1' }, { name: '0' }, { name: 'AUTOMAT', feedback: 'ELA1.DI.2' }],
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
    locations: [{ code: 'KOT', description: 'Boiler room' }],
    cards: [{ id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 16 }],
    devices: []
  });
}

describe('DeviceFormDialog - SELECTOR section', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('a fully valid 3-position selector (edit mode) has no field errors and Save is enabled', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeSelector()} onSave={() => {}} onCancel={() => {}} />);
    expect(isSaveDisabled()).toBe(false);
  });

  it('renders one name field per position, pre-filled', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeSelector()} onSave={() => {}} onCancel={() => {}} />);
    const nameInputs = screen.getAllByPlaceholderText('MANUAL') as HTMLInputElement[];
    expect(nameInputs.map(i => i.value)).toEqual(['MANUAL', '0', 'AUTOMAT']);
  });

  it('dropping to 1 position disables its own remove button and, if forced to 1 anyway, is rejected on Save', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeSelector({ positions: [{ name: 'MANUAL' }, { name: 'AUTOMAT' }] })} onSave={() => {}} onCancel={() => {}} />);
    const removeButtons = screen.getAllByTitle('At least 2 positions are required') as HTMLButtonElement[];
    expect(removeButtons.every(b => b.disabled)).toBe(true);
  });

  it('adding a position with an empty name blocks Save and shows the empty-name error', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeSelector()} onSave={() => {}} onCancel={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: '+ Add Position' }));
    expect(isSaveDisabled()).toBe(true);
    expect(screen.getByText(/positions\[3\]\.name must not be empty/)).toBeTruthy();
  });

  it('renaming two positions to the same name blocks Save with a duplicate-name error', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeSelector()} onSave={() => {}} onCancel={() => {}} />);
    const nameInputs = screen.getAllByPlaceholderText('MANUAL') as HTMLInputElement[];
    fireEvent.change(nameInputs[1], { target: { value: 'MANUAL' } });
    expect(isSaveDisabled()).toBe(true);
    expect(screen.getByText(/duplicate position name/)).toBeTruthy();
  });

  it('removing a position down to exactly 2 keeps Save enabled', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeSelector()} onSave={() => {}} onCancel={() => {}} />);
    const removeButtons = screen.getAllByRole('button', { name: 'x' }).filter(b => !(b as HTMLButtonElement).disabled);
    fireEvent.click(removeButtons[0]);
    expect(isSaveDisabled()).toBe(false);
  });

  it('saving calls onSave with the edited position name applied', () => {
    let saved: SelectorDevice | null = null;
    render(<DeviceFormDialog mode="edit" initialDevice={makeSelector()} onSave={(d) => { saved = d as SelectorDevice; }} onCancel={() => {}} />);
    const nameInputs = screen.getAllByPlaceholderText('MANUAL') as HTMLInputElement[];
    fireEvent.change(nameInputs[0], { target: { value: 'MANUAL (lokalnie)' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(saved).not.toBeNull();
    expect(saved!.positions[0].name).toBe('MANUAL (lokalnie)');
  });

  it('SELECTOR is offered in the behavior dropdown', () => {
    render(<DeviceFormDialog mode="add" onSave={() => {}} onCancel={() => {}} />);
    const behaviorRow = screen.getByText('Behaviour').closest('.property-row')!;
    const select = behaviorRow.querySelector('select') as HTMLSelectElement;
    const options = Array.from(select.options).map(o => o.value);
    expect(options).toContain('SELECTOR');
  });
});
