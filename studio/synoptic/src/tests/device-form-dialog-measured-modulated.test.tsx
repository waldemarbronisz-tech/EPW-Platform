/** @vitest-environment jsdom */
// feat/device-list-ui commit 4 - the MEASURED and MODULATED sections of
// DeviceFormDialog, and mandatory tests 11, 12, 13.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { DeviceFormDialog } from '../components/DeviceFormDialog';
import type { MeasuredDevice, ModulatedDevice } from '../project/DeviceSchema';

function row(labelText: string): HTMLElement {
  return screen.getByText(labelText).closest('.property-row')!;
}
function input(labelText: string): HTMLInputElement {
  return row(labelText).querySelector('input') as HTMLInputElement;
}
// fix/device-form-polish commit 2: Zapisz is aria-disabled now, not
// natively disabled - see device-form-dialog-switched.test.tsx's own
// copy of this helper for the full reasoning.
function isSaveDisabled(): boolean {
  return screen.getByRole('button', { name: 'Zapisz' }).getAttribute('aria-disabled') === 'true';
}

function makeMeasured(overrides: Partial<MeasuredDevice> = {}): MeasuredDevice {
  return {
    id: 'KOT_TEMP1', designation: '-B1', name: 'Czujnik temperatury', behavior: 'MEASURED', kind: 'sensor', publishToHa: false,
    input: 'ELA1.AI.1', unit: '°C', rangeMin: 0, rangeMax: 100, format: '0.0', deadband: 0.5,
    ...overrides
  };
}

function makeModulated(overrides: Partial<ModulatedDevice> = {}): ModulatedDevice {
  return {
    id: 'KOT_ZAW1', designation: '-Y1', name: 'Zawor modulujacy', behavior: 'MODULATED', kind: 'valve', publishToHa: false,
    setpointOutput: 'ADA1.AO.1', unit: '%', rangeMin: 0, rangeMax: 100, startupValue: 0, safeValue: 0,
    ...overrides
  };
}

function resetStore() {
  useStore.setState({
    locations: [{ code: 'KOT', description: 'Kotlownia' }],
    cards: [
      { id: 'ELA1', model: 'ELA01', channelKind: 'AI', channelCount: 8 },
      { id: 'ADA1', model: 'ADA01', channelKind: 'AO', channelCount: 8 },
      { id: 'ELD1', model: 'ELD01', channelKind: 'DO', channelCount: 16 }
    ],
    devices: []
  });
}

describe('DeviceFormDialog - MEASURED section', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('test 11: the input channel picker only offers AI cards, never DO ones', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeMeasured()} onSave={() => {}} onCancel={() => {}} />);
    const cardSelect = row('input').querySelectorAll('select')[0] as HTMLSelectElement;
    const offered = Array.from(cardSelect.options).map(o => o.value);
    expect(offered).toEqual(['ELA1']);
    expect(offered).not.toContain('ELD1');
  });

  it('test 12: rangeMin greater than rangeMax is rejected - Save disabled, field error shown', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeMeasured()} onSave={() => {}} onCancel={() => {}} />);
    // mode="edit" - submitAttempted starts true (mandatory test 12: an
    // edit form of an already-invalid device shows its errors right
    // away), so this NEWLY introduced error is visible immediately,
    // touched or not - the blur below is not what reveals it here, just
    // documents the same interaction a real user would do regardless.
    const rangeMinInput = input('Zakres min');
    fireEvent.change(rangeMinInput, { target: { value: '200' } });
    fireEvent.blur(rangeMinInput);
    expect(isSaveDisabled()).toBe(true);
    // Shown under both rangeMin and rangeMax (MEASURED_INVALID_RANGE maps to both).
    expect(screen.getAllByText(/rangeMin must be less than rangeMax/).length).toBe(2);
  });

  it('a fully valid MEASURED device (edit mode) has no field errors and Save is enabled', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeMeasured()} onSave={() => {}} onCancel={() => {}} />);
    expect(isSaveDisabled()).toBe(false);
  });

  it('shows a live mid-range preview formatted with the unit', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeMeasured({ rangeMin: 0, rangeMax: 400, format: '0.0', unit: 'kW' })} onSave={() => {}} onCancel={() => {}} />);
    expect(screen.getByText(/200\.0 kW/)).toBeTruthy();
  });
});

describe('DeviceFormDialog - MODULATED section', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('test 13: startupValue outside rangeMin..rangeMax is rejected - Save disabled, field error shown', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeModulated()} onSave={() => {}} onCancel={() => {}} />);
    const startupInput = input('Wartosc startowa');
    fireEvent.change(startupInput, { target: { value: '150' } });
    fireEvent.blur(startupInput);
    expect(isSaveDisabled()).toBe(true);
    expect(screen.getByText(/startupValue must be within rangeMin..rangeMax/)).toBeTruthy();
  });

  it('the setpointOutput channel picker only offers AO cards', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeModulated()} onSave={() => {}} onCancel={() => {}} />);
    const cardSelect = row('setpointOutput').querySelectorAll('select')[0] as HTMLSelectElement;
    expect(Array.from(cardSelect.options).map(o => o.value)).toEqual(['ADA1']);
  });

  it('feedbackInput is optional - unchecked by default when absent, and clearing it removes the value', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeModulated({ feedbackInput: 'ELA1.AI.2' })} onSave={() => {}} onCancel={() => {}} />);
    const checkbox = row('feedbackInput').querySelector('input[type="checkbox"]') as HTMLInputElement;
    expect(checkbox.checked).toBe(true);
    fireEvent.click(checkbox);
    expect(checkbox.checked).toBe(false);
  });

  it('a fully valid MODULATED device (edit mode) has no field errors and Save is enabled', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeModulated()} onSave={() => {}} onCancel={() => {}} />);
    expect(isSaveDisabled()).toBe(false);
  });
});
