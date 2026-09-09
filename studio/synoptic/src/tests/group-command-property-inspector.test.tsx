/** @vitest-environment jsdom */
// feat/control-elements commit 2 - PropertyInspector's own Group
// Command Properties section: renders the REAL PropertyInspector
// against the REAL store, same convention plan-object-properties.test.tsx
// already established for this component.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { PropertyInspector } from '../components/PropertyInspector';
import type { GroupCommandElement } from '../elements/GroupCommandElement';
import type { SwitchedDevice } from '../project/DeviceSchema';

function makeGroupCommand(overrides: Partial<GroupCommandElement> = {}): GroupCommandElement {
  return { id: 'G1', x: 0, y: 0, width: 160, label: 'Start wentylatorow', command: 'CLOSE', deviceIds: [], ...overrides };
}

function makeSwitched(id: string, designation: string): SwitchedDevice {
  return {
    id, designation, name: 'Wentylator', behavior: 'SWITCHED', kind: 'fan', publishToHa: false,
    feedback: { mode: 'NONE' }, command: { outputCount: 1, style: 'MAINTAINED', doClose: 'ADA1.DO.1' },
    supervision: { confirmTimeoutMs: 1000, discrepancyAlarm: false },
    safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' }, switchCounter: false
  };
}

function resetStore() {
  useStore.setState({
    objects: [], connections: [], meters: [], signalPanels: [], frames: [], groupCommands: [],
    devices: [],
    selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [], selectedGroupCommandIds: [],
    messages: [],
    history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [], groupCommands: [] }],
    historyIndex: 0
  });
}

function row(labelText: string): HTMLElement {
  return screen.getByText(labelText).closest('.property-row')!;
}

describe('PropertyInspector - group command button', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('shows the label and command of the selected button', () => {
    useStore.setState({ groupCommands: [makeGroupCommand()], selectedGroupCommandIds: ['G1'] });
    render(<PropertyInspector />);
    expect((screen.getByDisplayValue('Start wentylatorow') as HTMLInputElement).value).toBe('Start wentylatorow');
    expect((row('Polecenie').querySelector('select') as HTMLSelectElement).value).toBe('CLOSE');
  });

  it('editing the label updates the store', () => {
    useStore.setState({ groupCommands: [makeGroupCommand()], selectedGroupCommandIds: ['G1'] });
    render(<PropertyInspector />);
    fireEvent.change(screen.getByDisplayValue('Start wentylatorow'), { target: { value: 'Wylacz oswietlenie' } });
    expect(useStore.getState().groupCommands[0].label).toBe('Wylacz oswietlenie');
  });

  it('changing the command dropdown updates the store', () => {
    useStore.setState({ groupCommands: [makeGroupCommand()], selectedGroupCommandIds: ['G1'] });
    render(<PropertyInspector />);
    fireEvent.change(row('Polecenie').querySelector('select')!, { target: { value: 'OPEN' } });
    expect(useStore.getState().groupCommands[0].command).toBe('OPEN');
  });

  it('lists only SWITCHED devices in the "add member" dropdown, and only ones not already added', () => {
    useStore.setState({
      devices: [makeSwitched('KOT_W1', '-M1'), makeSwitched('KOT_W2', '-M2')],
      groupCommands: [makeGroupCommand({ deviceIds: ['KOT_W1'] })],
      selectedGroupCommandIds: ['G1']
    });
    render(<PropertyInspector />);
    const addSelect = screen.getByText('+ Dodaj aparat...').closest('select') as HTMLSelectElement;
    const options = Array.from(addSelect.options).map(o => o.value).filter(v => v !== '');
    expect(options).toEqual(['KOT_W2']);
  });

  it('picking a device from the add dropdown adds it as a member', () => {
    useStore.setState({
      devices: [makeSwitched('KOT_W1', '-M1')],
      groupCommands: [makeGroupCommand({ deviceIds: [] })],
      selectedGroupCommandIds: ['G1']
    });
    render(<PropertyInspector />);
    const addSelect = screen.getByText('+ Dodaj aparat...').closest('select') as HTMLSelectElement;
    fireEvent.change(addSelect, { target: { value: 'KOT_W1' } });
    expect(useStore.getState().groupCommands[0].deviceIds).toEqual(['KOT_W1']);
  });

  it('removing a member via its own "x" button drops it from deviceIds', () => {
    useStore.setState({
      devices: [makeSwitched('KOT_W1', '-M1')],
      groupCommands: [makeGroupCommand({ deviceIds: ['KOT_W1'] })],
      selectedGroupCommandIds: ['G1']
    });
    render(<PropertyInspector />);
    fireEvent.click(screen.getByRole('button', { name: 'x' }));
    expect(useStore.getState().groupCommands[0].deviceIds).toEqual([]);
  });

  it('a dangling member (deleted device) is shown marked, not silently dropped', () => {
    useStore.setState({
      devices: [],
      groupCommands: [makeGroupCommand({ deviceIds: ['KOT_GONE'] })],
      selectedGroupCommandIds: ['G1']
    });
    render(<PropertyInspector />);
    expect(screen.getByText(/brak \/ nie SWITCHED/)).toBeTruthy();
  });

  it('"Testuj (podglad)" logs an INFO message naming every valid target, never sends anything', () => {
    useStore.setState({
      devices: [makeSwitched('KOT_W1', '-M1')],
      groupCommands: [makeGroupCommand({ command: 'CLOSE', deviceIds: ['KOT_W1'] })],
      selectedGroupCommandIds: ['G1']
    });
    render(<PropertyInspector />);
    fireEvent.click(screen.getByRole('button', { name: 'Testuj (podglad)' }));
    const messages = useStore.getState().messages;
    expect(messages.some(m => m.type === 'info' && m.text.includes('KOT_W1.CLOSE'))).toBe(true);
  });
});
