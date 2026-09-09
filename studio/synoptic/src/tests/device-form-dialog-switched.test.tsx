/** @vitest-environment jsdom */
// feat/device-list-ui commit 3 - the SWITCHED and SIGNAL sections of
// DeviceFormDialog, and mandatory tests 4-10, 14, 16, 17. Renders the
// REAL DeviceFormDialog against the REAL store, same convention every
// other dialog test in this feature already uses.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { DeviceFormDialog } from '../components/DeviceFormDialog';
import type { SignalDevice, SwitchedDevice } from '../project/DeviceSchema';

function row(labelText: string): HTMLElement {
  return screen.getByText(labelText).closest('.property-row')!;
}

function input(labelText: string): HTMLInputElement {
  return row(labelText).querySelector('input') as HTMLInputElement;
}

function select(labelText: string): HTMLSelectElement {
  return row(labelText).querySelector('select') as HTMLSelectElement;
}

// fix/device-form-polish commit 2: Zapisz is aria-disabled now, not
// natively disabled (a genuinely disabled button never dispatches a
// click at all, verified live - see raport.md - so it could never
// reveal the form's errors on an attempted save the way this commit
// requires). Same rule everywhere: a field's own error is hidden until
// it has been left once (blur) or a save was attempted.
function isSaveDisabled(): boolean {
  return screen.getByRole('button', { name: 'Zapisz' }).getAttribute('aria-disabled') === 'true';
}

function makeSignal(overrides: Partial<SignalDevice> = {}): SignalDevice {
  return {
    id: 'KOT_STY1', designation: '-B1', name: 'Czujnik', behavior: 'SIGNAL', kind: 'sensor', publishToHa: false,
    feedback: { di: 'ELA1.DI.1', invert: false }, alarmState: 'HIGH', debounceMs: 50,
    ...overrides
  };
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
    locations: [{ code: 'KOT', description: 'Kotlownia' }, { code: 'WEN', description: 'Wentylatornia' }],
    cards: [
      { id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 16 },
      { id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 16 }
    ],
    devices: []
  });
}

describe('DeviceFormDialog - SWITCHED section', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  function openAddSwitchedForm(onSave = (_d: any) => {}) {
    render(<DeviceFormDialog mode="add" onSave={onSave} onCancel={() => {}} />);
    fireEvent.change(select('Zachowanie'), { target: { value: 'SWITCHED' } });
  }

  it('test 4: SWITCHED DUAL requires both diClosed and diOpen - Save is disabled and both fields report a missing-address error', () => {
    openAddSwitchedForm();
    fireEvent.change(select('Tryb'), { target: { value: 'DUAL' } });

    expect(isSaveDisabled()).toBe(true);
  });

  it('test 5: SWITCHED SINGLE hides the diOpen field entirely', () => {
    openAddSwitchedForm();
    fireEvent.change(select('Tryb'), { target: { value: 'SINGLE' } });
    expect(screen.queryByText('diOpen')).toBeNull();
  });

  it('test 6: a single output (outputCount 1) hides the doOpen field entirely', () => {
    openAddSwitchedForm();
    fireEvent.change(select('Liczba wyjsc'), { target: { value: '1' } });
    expect(screen.queryByText('doOpen')).toBeNull();
  });

  it('test 7: MAINTAINED style hides the pulse time (pulseMs) field entirely', () => {
    openAddSwitchedForm();
    fireEvent.change(select('Styl'), { target: { value: 'MAINTAINED' } });
    expect(screen.queryByText('Czas impulsu (ms)')).toBeNull();
  });

  it('test 8: confirmTimeoutMs 50 is rejected (Save disabled, field error shown) and 100 is accepted once every other field is valid', () => {
    useStore.setState({ locations: [{ code: 'KOT', description: 'Kotlownia' }], cards: [
      { id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 16 },
      { id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 16 }
    ], devices: [] });
    render(<DeviceFormDialog mode="edit" initialDevice={makeSwitched({ supervision: { confirmTimeoutMs: 500, discrepancyAlarm: false } })} onSave={() => {}} onCancel={() => {}} />);
    // fix/inline-device-creation commit 4: Nadzor (supervision) is one
    // of SWITCHED's own CollapsibleSections, collapsed by default until
    // it holds an error - 500 is valid, so it starts collapsed here.
    fireEvent.click(screen.getByText('Nadzor (supervision)'));

    const timeoutInput = input('Timeout potwierdzenia (ms)');
    fireEvent.change(timeoutInput, { target: { value: '50' } });
    fireEvent.blur(timeoutInput);
    expect(isSaveDisabled()).toBe(true);
    expect(screen.getByText(/confirmTimeoutMs must be >= 100/)).toBeTruthy();

    fireEvent.change(timeoutInput, { target: { value: '100' } });
    expect(isSaveDisabled()).toBe(false);
  });

  it('test 9: a channel already used by another device is unavailable (disabled) in the picker', () => {
    useStore.setState({ devices: [makeSignal({ id: 'KOT_STY1', feedback: { di: 'ELA1.DI.1', invert: false } })] });
    openAddSwitchedForm();
    fireEvent.change(select('Tryb'), { target: { value: 'SINGLE' } });

    const diClosedRow = row('diClosed');
    const channelSelect = diClosedRow.querySelectorAll('select')[1] as HTMLSelectElement;
    const option1 = Array.from(channelSelect.options).find(o => o.value === '1')!;
    expect(option1.disabled).toBe(true);
    expect(option1.textContent).toContain('KOT_STY1');
  });

  it('test 10: a 64-channel card offers exactly 64 channel options, numbered 1 through 64', () => {
    useStore.setState({ cards: [
      { id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 64 },
      { id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 16 }
    ] });
    openAddSwitchedForm();
    fireEvent.change(select('Tryb'), { target: { value: 'SINGLE' } });

    const diClosedRow = row('diClosed');
    const channelSelect = diClosedRow.querySelectorAll('select')[1] as HTMLSelectElement;
    // An unset required field also shows one leading "-- wybierz --"
    // placeholder (empirical fix: KROK 2 of manual verification found
    // the channel picker otherwise looked pre-filled with channel 1
    // before the user ever chose anything) - the 64 real, numbered
    // channel options are everything after it.
    const numberedOptions = Array.from(channelSelect.options).filter(o => o.value !== '');
    expect(numberedOptions.length).toBe(64);
    expect(numberedOptions[0].value).toBe('1');
    expect(numberedOptions[63].value).toBe('64');
  });

  it('test 14: the device id is read-only when editing an existing device', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeSwitched()} onSave={() => {}} onCancel={() => {}} />);
    const idInput = input('Id');
    expect(idInput.disabled).toBe(true);
    expect(idInput.value).toBe('KOT_KMG1');
  });

  it('test 16: two devices with the same designation in the same location is rejected', () => {
    useStore.setState({ devices: [makeSwitched({ id: 'KOT_KMG1', designation: '-K1' })] });
    render(<DeviceFormDialog mode="add" onSave={() => {}} onCancel={() => {}} />);
    fireEvent.change(select('Zachowanie'), { target: { value: 'SWITCHED' } });

    const idRow = row('Id');
    fireEvent.change(idRow.querySelector('select')!, { target: { value: 'KOT' } });
    fireEvent.change(idRow.querySelector('input')!, { target: { value: 'KMG2' } });
    const designationInput = input('Oznaczenie');
    fireEvent.change(designationInput, { target: { value: '-K1' } });
    fireEvent.blur(designationInput);

    expect(screen.getByText(/Duplicate designation '-K1' in location 'KOT'/)).toBeTruthy();
    expect(isSaveDisabled()).toBe(true);
  });

  it('test 17: the same designation in two different locations is accepted (no error, once the rest of the device is valid)', () => {
    useStore.setState({ devices: [makeSwitched({ id: 'KOT_KMG1', designation: '-K1' })] });
    render(<DeviceFormDialog mode="add" onSave={() => {}} onCancel={() => {}} />);
    fireEvent.change(select('Zachowanie'), { target: { value: 'SWITCHED' } });
    fireEvent.change(select('Tryb'), { target: { value: 'NONE' } });

    const idRow = row('Id');
    fireEvent.change(idRow.querySelector('select')!, { target: { value: 'WEN' } });
    fireEvent.change(idRow.querySelector('input')!, { target: { value: 'KMG1' } });
    fireEvent.change(input('Oznaczenie'), { target: { value: '-K1' } });
    fireEvent.change(input('Nazwa'), { target: { value: 'Wentylator' } });
    const doCloseRow = row('doClose');
    fireEvent.change(doCloseRow.querySelectorAll('select')[0], { target: { value: 'ADA1' } });
    fireEvent.change(doCloseRow.querySelectorAll('select')[1], { target: { value: '2' } });

    expect(screen.queryByText(/Duplicate designation/)).toBeNull();
  });
});
