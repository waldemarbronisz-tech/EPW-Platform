/** @vitest-environment jsdom */
// fix/inline-device-creation commit 4: collapsible sections and sticky
// actions in DeviceFormDialog - tidies up the long SWITCHED form
// WITHOUT changing any field or validation rule (every existing
// SWITCHED/SIGNAL/MEASURED/MODULATED/SELECTOR/interlock test still
// passes unmodified in substance - only three of them now click a
// section header open first, matching how a real user would reach a
// field that starts collapsed). Mandatory tests 19-20.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { DeviceFormDialog } from '../components/DeviceFormDialog';
import type { SwitchedDevice } from '../project/DeviceSchema';

import deviceFormDialogSource from '../components/DeviceFormDialog.tsx?raw';

function row(labelText: string): HTMLElement {
  return screen.getByText(labelText).closest('.property-row')!;
}
function input(labelText: string): HTMLInputElement {
  return row(labelText).querySelector('input') as HTMLInputElement;
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

function resetStore() {
  useStore.setState({
    locations: [{ code: 'KOT', description: 'Kotlownia' }],
    cards: [{ id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 16 }],
    devices: []
  });
}

describe('19. a section containing a validation error is shown expanded, without clicking anything', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('Nadzor (supervision) auto-expands when confirmTimeoutMs is invalid, while an error-free section stays collapsed', () => {
    const device = makeSwitched({ supervision: { confirmTimeoutMs: 50, discrepancyAlarm: false } });
    render(<DeviceFormDialog mode="edit" initialDevice={device} onSave={() => {}} onCancel={() => {}} />);

    // Nadzor holds the error (confirmTimeoutMs 50 < 100) - its own
    // field is visible immediately, no click needed.
    expect(input('Timeout potwierdzenia (ms)')).toBeTruthy();
    expect(screen.getByText(/confirmTimeoutMs must be >= 100/)).toBeTruthy();

    // Blokady (interlock) holds no error and was never clicked - still
    // collapsed, its own fields are not even in the document.
    expect(screen.queryByText('Opis blokady ZAMKNIJ')).toBeNull();
  });

  it('collapsing an errored section by hand has no visible effect - the error can never be hidden', () => {
    const device = makeSwitched({ supervision: { confirmTimeoutMs: 50, discrepancyAlarm: false } });
    render(<DeviceFormDialog mode="edit" initialDevice={device} onSave={() => {}} onCancel={() => {}} />);

    fireEvent.click(screen.getByText('Nadzor (supervision)'));
    expect(input('Timeout potwierdzenia (ms)')).toBeTruthy();
  });

  it('fixing the error collapses the section back down on its own - it was never manually opened, only forced open by the error', () => {
    const device = makeSwitched({ supervision: { confirmTimeoutMs: 50, discrepancyAlarm: false } });
    render(<DeviceFormDialog mode="edit" initialDevice={device} onSave={() => {}} onCancel={() => {}} />);

    fireEvent.change(input('Timeout potwierdzenia (ms)'), { target: { value: '1000' } });

    expect(screen.queryByText(/confirmTimeoutMs must be >= 100/)).toBeNull();
    expect(screen.queryByText('Timeout potwierdzenia (ms)')).toBeNull();

    // Clicking the header now genuinely opens it (a plain toggle, no
    // error left to force anything).
    fireEvent.click(screen.getByText('Nadzor (supervision)'));
    expect(screen.getByText('Timeout potwierdzenia (ms)')).toBeTruthy();
  });
});

describe('20. Enter in a text field moves to the next field, never saves the form', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('pressing Enter in Nazwa never calls onSave, and moves focus to the next field', () => {
    let saved: SwitchedDevice | null = null;
    render(<DeviceFormDialog mode="edit" initialDevice={makeSwitched()} onSave={(d) => { saved = d as SwitchedDevice; }} onCancel={() => {}} />);

    const nameInput = input('Nazwa');
    nameInput.focus();
    fireEvent.keyDown(nameInput, { key: 'Enter' });

    expect(saved).toBeNull();
    expect(document.activeElement).not.toBe(nameInput);
  });

  it('Enter on a checkbox is left alone (no forced focus move)', () => {
    let saved: SwitchedDevice | null = null;
    render(<DeviceFormDialog mode="edit" initialDevice={makeSwitched()} onSave={(d) => { saved = d as SwitchedDevice; }} onCancel={() => {}} />);

    const checkbox = row('Publikuj do HA').querySelector('input[type="checkbox"]') as HTMLInputElement;
    checkbox.focus();
    fireEvent.keyDown(checkbox, { key: 'Enter' });

    expect(saved).toBeNull();
  });

  it('this dialog is still a plain div, not a <form> - there has never been anything for Enter to submit', () => {
    expect(deviceFormDialogSource).not.toMatch(/<form[\s>]/);
  });

  it('Escape\'s own existing unsaved-changes-confirm mechanism (feat/device-form-from-canvas commit 3c) is untouched - no second Escape handler was introduced', () => {
    const escapeMatches = deviceFormDialogSource.match(/e\.key === 'Escape'/g) || [];
    expect(escapeMatches.length).toBe(1);
    expect(deviceFormDialogSource).toContain('onKeyDown={(e) => { if (e.key === \'Escape\') handleEscape(); }}');
    expect(deviceFormDialogSource).not.toContain("addEventListener('keydown'");
  });
});
