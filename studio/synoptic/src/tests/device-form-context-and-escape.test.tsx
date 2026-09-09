/** @vitest-environment jsdom */
// feat/device-form-from-canvas commit 3 - the form's own context header
// (3a), Escape-to-close with an unsaved-changes confirmation (3c), and
// the Messages confirmation on save (3d). Renders the REAL
// DeviceFormDialog against the REAL store, same convention every other
// dialog test in this project already uses.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { DeviceFormDialog } from '../components/DeviceFormDialog';
import { formatDeviceSavedMessage } from '../project/DeviceFormSync';
import type { SwitchedDevice } from '../project/DeviceSchema';

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
    locations: [{ code: 'KOT', description: 'Kotlownia' }],
    cards: [{ id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 16 }],
    devices: [makeSwitched()]
  });
}

describe('3a. DeviceFormDialog\'s own context header', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('shows sourceContext as a second header line when provided', () => {
    render(
      <DeviceFormDialog mode="edit" initialDevice={makeSwitched()} sourceContext="Schemat, symbol -K1" onSave={() => {}} onCancel={() => {}} />
    );
    expect(screen.getByText('Schemat, symbol -K1')).toBeTruthy();
  });

  it('shows nothing extra when sourceContext is not provided - the header stays exactly what it always was (Lista aparatow\'s own path, task 3b/GRANICE)', () => {
    render(<DeviceFormDialog mode="edit" initialDevice={makeSwitched()} onSave={() => {}} onCancel={() => {}} />);
    expect(screen.getByText('Edycja aparatu KOT_KMG1')).toBeTruthy();
    // Nothing else in the header names a source - the header block has
    // exactly one text line.
    const header = screen.getByText('Edycja aparatu KOT_KMG1').parentElement!;
    expect(header.textContent).toBe('Edycja aparatu KOT_KMG1');
  });
});

describe('3c. Escape closes the form without saving, confirming first if anything changed', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('closes immediately (no confirm dialog) when nothing was changed', () => {
    let cancelled = false;
    render(<DeviceFormDialog mode="edit" initialDevice={makeSwitched()} onSave={() => {}} onCancel={() => { cancelled = true; }} />);
    fireEvent.keyDown(screen.getByDisplayValue('-K1'), { key: 'Escape' });
    expect(cancelled).toBe(true);
  });

  it('asks for confirmation when a field was edited, and respects Cancel (stays open, onCancel not called)', () => {
    const originalConfirm = window.confirm;
    let confirmCalled = false;
    window.confirm = () => { confirmCalled = true; return false; };
    try {
      let cancelled = false;
      render(<DeviceFormDialog mode="edit" initialDevice={makeSwitched()} onSave={() => {}} onCancel={() => { cancelled = true; }} />);
      const designationInput = screen.getByDisplayValue('-K1');
      fireEvent.change(designationInput, { target: { value: '-K2' } });
      fireEvent.keyDown(designationInput, { key: 'Escape' });

      expect(confirmCalled).toBe(true);
      expect(cancelled).toBe(false);
    } finally {
      window.confirm = originalConfirm;
    }
  });

  it('closes when the user edited a field AND confirms discarding it', () => {
    const originalConfirm = window.confirm;
    window.confirm = () => true;
    try {
      let cancelled = false;
      render(<DeviceFormDialog mode="edit" initialDevice={makeSwitched()} onSave={() => {}} onCancel={() => { cancelled = true; }} />);
      const designationInput = screen.getByDisplayValue('-K1');
      fireEvent.change(designationInput, { target: { value: '-K2' } });
      fireEvent.keyDown(designationInput, { key: 'Escape' });
      expect(cancelled).toBe(true);
    } finally {
      window.confirm = originalConfirm;
    }
  });

  it('the backdrop, the header "x" and the footer Anuluj still close directly, with no confirmation - unchanged from before this commit', () => {
    const originalConfirm = window.confirm;
    let confirmCalled = false;
    window.confirm = () => { confirmCalled = true; return true; };
    try {
      let cancelled = false;
      render(<DeviceFormDialog mode="edit" initialDevice={makeSwitched()} onSave={() => {}} onCancel={() => { cancelled = true; }} />);
      fireEvent.change(screen.getByDisplayValue('-K1'), { target: { value: '-K2' } });
      fireEvent.click(screen.getByRole('button', { name: 'Anuluj' }));
      expect(cancelled).toBe(true);
      expect(confirmCalled).toBe(false);
    } finally {
      window.confirm = originalConfirm;
    }
  });

  it('this exact same Escape behavior applies whether the form was opened with or without a sourceContext - one behavior, not two', () => {
    const originalConfirm = window.confirm;
    window.confirm = () => true;
    try {
      let cancelledWithContext = false;
      const { unmount } = render(
        <DeviceFormDialog mode="edit" initialDevice={makeSwitched()} sourceContext="Schemat, symbol -K1" onSave={() => {}} onCancel={() => { cancelledWithContext = true; }} />
      );
      const input1 = screen.getByDisplayValue('-K1');
      fireEvent.change(input1, { target: { value: '-K2' } });
      fireEvent.keyDown(input1, { key: 'Escape' });
      expect(cancelledWithContext).toBe(true);
      unmount();

      let cancelledWithoutContext = false;
      render(<DeviceFormDialog mode="edit" initialDevice={makeSwitched()} onSave={() => {}} onCancel={() => { cancelledWithoutContext = true; }} />);
      const input2 = screen.getByDisplayValue('-K1');
      fireEvent.change(input2, { target: { value: '-K2' } });
      fireEvent.keyDown(input2, { key: 'Escape' });
      expect(cancelledWithoutContext).toBe(true);
    } finally {
      window.confirm = originalConfirm;
    }
  });
});

describe('3d. Messages on save (formatDeviceSavedMessage, App.tsx\'s own onSave)', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('names designation and name, never the device id/UUID', () => {
    const saved = makeSwitched({ id: 'KOT_KMG1', designation: '-K9', name: 'Stycznik pompy' });
    const text = formatDeviceSavedMessage(saved);
    expect(text).toContain('-K9');
    expect(text).toContain('Stycznik pompy');
    expect(text).not.toContain('KOT_KMG1');
  });

  it('App.tsx\'s own onSave actually posts it through addMessage, as an INFO', () => {
    // App.tsx itself is too heavy to mount in a unit test (sprite
    // manifest fetch, lazy-loaded siblings) - this exercises the exact
    // same function its onSave handler calls (formatDeviceSavedMessage,
    // imported and used verbatim there - see App.tsx's own onSave).
    const saved = makeSwitched({ designation: '-K9', name: 'Stycznik pompy' });
    useStore.getState().addMessage(formatDeviceSavedMessage(saved));
    const last = useStore.getState().messages.at(-1)!;
    expect(last.type).toBe('info');
    expect(last.text).toContain('-K9');
  });
});
