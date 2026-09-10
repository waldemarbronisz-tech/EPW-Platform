/** @vitest-environment jsdom */
// feat/device-list-ui commit 3 - the SIGNAL section of DeviceFormDialog.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { DeviceFormDialog } from '../components/DeviceFormDialog';
import type { SignalDevice } from '../project/DeviceSchema';

function row(labelText: string): HTMLElement {
  return screen.getByText(labelText).closest('.property-row')!;
}
function input(labelText: string): HTMLInputElement {
  return row(labelText).querySelector('input') as HTMLInputElement;
}
function select(labelText: string): HTMLSelectElement {
  return row(labelText).querySelector('select') as HTMLSelectElement;
}
// fix/device-form-polish commit 2: Save is aria-disabled now, not
// natively disabled - see device-form-dialog-switched.test.tsx's own
// copy of this helper for the full reasoning.
function isSaveDisabled(): boolean {
  return screen.getByRole('button', { name: 'Save' }).getAttribute('aria-disabled') === 'true';
}

function makeSignal(overrides: Partial<SignalDevice> = {}): SignalDevice {
  return {
    id: 'KOT_STY1', designation: '-B1', name: 'Czujnik plomienia', behavior: 'SIGNAL', kind: 'sensor', publishToHa: false,
    feedback: { di: 'ELA1.DI.1', invert: false }, alarmState: 'HIGH', debounceMs: 50,
    ...overrides
  };
}

function resetStore() {
  useStore.setState({
    locations: [{ code: 'KOT', description: 'Boiler room' }],
    cards: [
      { id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 16 },
      { id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 16 }
    ],
    devices: []
  });
}

describe('DeviceFormDialog - SIGNAL section', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('a fully valid SIGNAL device (edit mode) has no field errors and Save is enabled', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeSignal()} onSave={() => {}} onCancel={() => {}} />);
    expect(isSaveDisabled()).toBe(false);
  });

  it('SIGNAL debounceMs -1 is rejected: Save disabled and a field error is shown', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeSignal()} onSave={() => {}} onCancel={() => {}} />);
    const debounceInput = input('Debounce (ms)');
    fireEvent.change(debounceInput, { target: { value: '-1' } });
    fireEvent.blur(debounceInput);
    expect(isSaveDisabled()).toBe(true);
    expect(screen.getByText(/debounceMs must be >= 0/)).toBeTruthy();
  });

  it('the di channel picker only offers DI cards, never DO ones', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeSignal()} onSave={() => {}} onCancel={() => {}} />);
    const cardSelect = row('di').querySelectorAll('select')[0] as HTMLSelectElement;
    const offeredCards = Array.from(cardSelect.options).map(o => o.value);
    expect(offeredCards).toEqual(['ELA1']);
  });

  it('saving calls onSave with the edited fields applied', () => {
    let saved: SignalDevice | null = null;
    render(<DeviceFormDialog mode="edit" initialDevice={makeSignal()} onSave={(d) => { saved = d as SignalDevice; }} onCancel={() => {}} />);
    fireEvent.change(select('Alarm State'), { target: { value: 'LOW' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(saved).not.toBeNull();
    expect(saved!.alarmState).toBe('LOW');
    expect(saved!.id).toBe('KOT_STY1');
  });
});
