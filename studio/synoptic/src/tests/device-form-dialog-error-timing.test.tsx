/** @vitest-environment jsdom */
// fix/device-form-polish commit 2: WHEN a field's own validation
// message becomes visible - not which rules exist or what they say
// (validateDeviceRegistry decides that alone, completely unchanged;
// see DeviceValidation.ts). Mandatory tests 4-12. Same "render the
// REAL DeviceFormDialog against the REAL store" convention as every
// other DeviceFormDialog test file.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { DeviceFormDialog } from '../components/DeviceFormDialog';
import type { SwitchedDevice } from '../project/DeviceSchema';

function row(labelText: string): HTMLElement {
  return screen.getByText(labelText).closest('.property-row')!;
}
function input(labelText: string): HTMLInputElement {
  return row(labelText).querySelector('input') as HTMLInputElement;
}
function isSaveDisabled(): boolean {
  return screen.getByRole('button', { name: 'Zapisz' }).getAttribute('aria-disabled') === 'true';
}
function attemptSave() {
  fireEvent.click(screen.getByRole('button', { name: 'Zapisz' }));
}

function makeSwitched(overrides: Partial<SwitchedDevice> = {}): SwitchedDevice {
  return {
    id: 'KOT_KMG1', designation: '-K1', name: 'Stycznik grzalki', behavior: 'SWITCHED', kind: 'contactor', publishToHa: false,
    feedback: { mode: 'DUAL', diClosed: 'ELA1.DI.2', diOpen: 'ELA1.DI.3' },
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
    devices: []
  });
}

describe('DeviceFormDialog - validation message timing', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  // A fresh add-mode form: SWITCHED defaults, one location present (so
  // locationCode is already picked but the suffix is not - id stays
  // empty), designation/name/kind all empty - several real, TRUE
  // validation issues exist from the very first render.
  function openFreshAddForm(onSave = (_d: any) => {}) {
    render(<DeviceFormDialog mode="add" onSave={onSave} onCancel={() => {}} />);
  }

  // 4. a freshly opened new-device form shows NO error message at all
  it('4: a freshly opened add form shows no error message, even though the device is genuinely invalid', () => {
    openFreshAddForm();
    // Known message fragments for the errors this fresh form DOES have
    // (empty id/designation/name/kind) - none of them may appear yet.
    expect(screen.queryByText(/must not be empty/)).toBeNull();
    expect(screen.queryByText(/must be a non-empty string/)).toBeNull();
  });

  // 5. the save button in a freshly opened form is inactive
  it('5: Save is inactive (aria-disabled) in a freshly opened add form', () => {
    openFreshAddForm();
    expect(isSaveDisabled()).toBe(true);
  });

  // 6. the error counter is visible in a freshly opened form
  it('6: the error counter next to Save is visible from the start', () => {
    openFreshAddForm();
    expect(screen.getByTitle(/blad\(y\) walidacji/)).toBeTruthy();
  });

  // 7. leaving the empty designation field shows its own message
  it('7: leaving the empty Oznaczenie field shows its own error message', () => {
    openFreshAddForm();
    const designationInput = input('Oznaczenie');
    fireEvent.focus(designationInput);
    fireEvent.blur(designationInput);
    expect(screen.getByText(/designation must not be empty/)).toBeTruthy();
  });

  // 8. another, untouched field's message still does not show
  it('8: another, untouched field\'s error stays hidden after only Oznaczenie was touched', () => {
    openFreshAddForm();
    const designationInput = input('Oznaczenie');
    fireEvent.focus(designationInput);
    fireEvent.blur(designationInput);
    // Nazwa is also empty (a real error), but was never touched.
    expect(screen.queryByText(/name must not be empty/)).toBeNull();
  });

  // 9. attempting to save shows every current message at once
  it('9: pressing Save while invalid reveals every current error at once', () => {
    openFreshAddForm();
    // None visible yet.
    expect(screen.queryByText(/designation must not be empty/)).toBeNull();
    expect(screen.queryByText(/name must not be empty/)).toBeNull();
    attemptSave();
    // Every one of the still-untouched fields' own errors is visible now.
    expect(screen.getByText(/designation must not be empty/)).toBeTruthy();
    expect(screen.getByText(/name must not be empty/)).toBeTruthy();
  });

  // 10. fixing a field removes its own message immediately (live
  // validation itself is unchanged - only the moment it FIRST appears is)
  it('10: correcting a touched field removes its message immediately', () => {
    openFreshAddForm();
    const designationInput = input('Oznaczenie');
    fireEvent.blur(designationInput);
    expect(screen.getByText(/designation must not be empty/)).toBeTruthy();
    fireEvent.change(designationInput, { target: { value: '-K1' } });
    expect(screen.queryByText(/designation must not be empty/)).toBeNull();
  });

  // 11. an edit-mode form of an existing, VALID device shows nothing
  it('11: an edit form of an already-valid device shows no error message', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeSwitched()} onSave={() => {}} onCancel={() => {}} />);
    expect(screen.queryByText(/must not be empty/)).toBeNull();
    expect(isSaveDisabled()).toBe(false);
  });

  // 12. an edit-mode form of an existing, INVALID device shows its
  // errors immediately - a different situation from a fresh add form
  it('12: an edit form of an already-invalid device shows its errors right away, with no interaction at all', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeSwitched({ designation: '' })} onSave={() => {}} onCancel={() => {}} />);
    expect(screen.getByText(/designation must not be empty/)).toBeTruthy();
    expect(isSaveDisabled()).toBe(true);
  });
});
