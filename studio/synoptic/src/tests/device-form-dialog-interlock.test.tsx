/** @vitest-environment jsdom */
// feat/control-elements commit 3 - the interlock section of
// DeviceFormDialog's SWITCHED form. Same conventions as
// device-form-dialog-switched.test.tsx.

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
// fix/inline-device-creation commit 4: Interlocks is one of
// SWITCHED's own CollapsibleSections, collapsed by default (it is pure
// optional documentation, never blocks Save) - every test below opens
// it first, the same as a real user would click its header.
function expandInterlock(): void {
  fireEvent.click(screen.getByText('Interlocks'));
}

function makeSwitched(overrides: Partial<SwitchedDevice> = {}): SwitchedDevice {
  return {
    id: 'KOT_KMG1', designation: '-K1', name: 'Stycznik grzalki', behavior: 'SWITCHED', kind: 'contactor', publishToHa: false,
    feedback: { mode: 'NONE' }, command: { outputCount: 1, style: 'MAINTAINED', doClose: 'ADA1.DO.1' },
    supervision: { confirmTimeoutMs: 500, discrepancyAlarm: false },
    safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' }, switchCounter: false,
    ...overrides
  };
}

function resetStore() {
  useStore.setState({
    locations: [{ code: 'KOT', description: 'Boiler room' }],
    cards: [{ id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 16 }],
    devices: []
  });
}

describe('DeviceFormDialog - interlock section (SWITCHED)', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('a device with no interlock at all shows both description fields blank, and Save stays enabled', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeSwitched()} onSave={() => {}} onCancel={() => {}} />);
    expandInterlock();
    expect(input('CLOSE Interlock Description').value).toBe('');
    expect(input('OPEN Interlock Description').value).toBe('');
    expect((screen.getByRole('button', { name: 'Save' }) as HTMLButtonElement).disabled).toBe(false);
  });

  it('an existing interlock description is shown pre-filled', () => {
    const device = makeSwitched({ interlock: { closeDescription: 'Zablokowane, gdy drzwi otwarte' } });
    render(<DeviceFormDialog mode="edit" initialDevice={device} onSave={() => {}} onCancel={() => {}} />);
    expandInterlock();
    expect(input('CLOSE Interlock Description').value).toBe('Zablokowane, gdy drzwi otwarte');
  });

  it('typing a close-interlock description and saving persists it on the device', () => {
    let saved: SwitchedDevice | null = null;
    render(<DeviceFormDialog mode="edit" initialDevice={makeSwitched()} onSave={(d) => { saved = d as SwitchedDevice; }} onCancel={() => {}} />);
    expandInterlock();
    fireEvent.change(input('CLOSE Interlock Description'), { target: { value: 'Zablokowane, gdy drzwi otwarte' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(saved).not.toBeNull();
    expect(saved!.interlock?.closeDescription).toBe('Zablokowane, gdy drzwi otwarte');
  });

  it('typing then clearing both descriptions saves the device with no interlock object at all (empty is absent, not a saved empty)', () => {
    let saved: SwitchedDevice | null = null;
    const device = makeSwitched({ interlock: { closeDescription: 'temp' } });
    render(<DeviceFormDialog mode="edit" initialDevice={device} onSave={(d) => { saved = d as SwitchedDevice; }} onCancel={() => {}} />);
    expandInterlock();
    fireEvent.change(input('CLOSE Interlock Description'), { target: { value: '' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(saved!.interlock).toBeUndefined();
  });

  it('setting only openDescription leaves closeDescription unset, and Save stays enabled', () => {
    let saved: SwitchedDevice | null = null;
    render(<DeviceFormDialog mode="edit" initialDevice={makeSwitched()} onSave={(d) => { saved = d as SwitchedDevice; }} onCancel={() => {}} />);
    expandInterlock();
    fireEvent.change(input('OPEN Interlock Description'), { target: { value: 'Zablokowane podczas biegu pompy rezerwowej' } });
    expect((screen.getByRole('button', { name: 'Save' }) as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(saved!.interlock?.openDescription).toBe('Zablokowane podczas biegu pompy rezerwowej');
    expect(saved!.interlock?.closeDescription).toBeUndefined();
  });
});
