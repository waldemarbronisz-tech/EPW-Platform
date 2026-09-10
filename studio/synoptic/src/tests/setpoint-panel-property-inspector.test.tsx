/** @vitest-environment jsdom */
// feat/selector-symbol-setpoint-alarm - PropertyInspector's own Setpoint
// Panel Properties section: renders the REAL PropertyInspector against
// the REAL store, same convention plan-object-properties.test.tsx /
// group-command-property-inspector.test.tsx already established.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { PropertyInspector } from '../components/PropertyInspector';
import type { SetpointPanelElement } from '../elements/SetpointElement';
import type { ModulatedDevice } from '../project/DeviceSchema';

function makePanel(overrides: Partial<SetpointPanelElement> = {}): SetpointPanelElement {
  return { id: 'S1', x: 0, y: 0, width: 200, fontSize: 13, rows: [], ...overrides };
}

function makeModulated(id: string, designation: string): ModulatedDevice {
  return {
    id, designation, name: 'Zawor modulowany', behavior: 'MODULATED', kind: 'valve', publishToHa: false,
    setpointOutput: 'ADA1.AO.1', unit: '%', rangeMin: 0, rangeMax: 100, startupValue: 25, safeValue: 0
  };
}

function resetStore() {
  useStore.setState({
    objects: [], connections: [], meters: [], signalPanels: [], frames: [], groupCommands: [], setpointPanels: [],
    devices: [],
    selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: [],
    history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [], groupCommands: [], setpointPanels: [] }],
    historyIndex: 0
  });
}

function row(labelText: string): HTMLElement {
  return screen.getByText(labelText).closest('.property-row')!;
}

describe('PropertyInspector - setpoint panel', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('shows title/font size/width of the selected panel', () => {
    useStore.setState({ setpointPanels: [makePanel({ title: 'Zawory' })], selectedSetpointPanelIds: ['S1'] });
    render(<PropertyInspector />);
    expect((screen.getByDisplayValue('Zawory') as HTMLInputElement).value).toBe('Zawory');
    expect((row('Width').querySelector('input') as HTMLInputElement).value).toBe('200');
  });

  it('lists only MODULATED devices not already used in the "add device" dropdown', () => {
    useStore.setState({
      devices: [makeModulated('KOT_TV1', '-TV1'), makeModulated('KOT_TV2', '-TV2')],
      setpointPanels: [makePanel({ rows: [{ device: 'KOT_TV1', label: '', manualValue: '', manualUnit: '' }] })],
      selectedSetpointPanelIds: ['S1']
    });
    render(<PropertyInspector />);
    const addSelect = screen.getByText('+ Add device...').closest('select') as HTMLSelectElement;
    const options = Array.from(addSelect.options).map(o => o.value).filter(v => v !== '');
    expect(options).toEqual(['KOT_TV2']);
  });

  it('picking a device from the add dropdown adds it as a new row', () => {
    useStore.setState({
      devices: [makeModulated('KOT_TV1', '-TV1')],
      setpointPanels: [makePanel({ rows: [] })],
      selectedSetpointPanelIds: ['S1']
    });
    render(<PropertyInspector />);
    const addSelect = screen.getByText('+ Add device...').closest('select') as HTMLSelectElement;
    fireEvent.change(addSelect, { target: { value: 'KOT_TV1' } });
    expect(useStore.getState().setpointPanels[0].rows).toEqual([{ device: 'KOT_TV1', label: '', manualValue: '', manualUnit: '' }]);
  });

  it('+ Manual row adds a blank row with manual value/unit fields shown', () => {
    useStore.setState({ setpointPanels: [makePanel({ rows: [] })], selectedSetpointPanelIds: ['S1'] });
    render(<PropertyInspector />);
    fireEvent.click(screen.getByRole('button', { name: '+ Manual row' }));
    expect(useStore.getState().setpointPanels[0].rows.length).toBe(1);
    expect(screen.getByPlaceholderText('Value')).toBeTruthy();
    expect(screen.getByPlaceholderText('Unit')).toBeTruthy();
  });

  it('a device-bound row shows "device: <id>" instead of manual value/unit inputs', () => {
    useStore.setState({
      devices: [makeModulated('KOT_TV1', '-TV1')],
      setpointPanels: [makePanel({ rows: [{ device: 'KOT_TV1', label: '', manualValue: '', manualUnit: '' }] })],
      selectedSetpointPanelIds: ['S1']
    });
    render(<PropertyInspector />);
    expect(screen.getByText(/device: KOT_TV1/)).toBeTruthy();
    expect(screen.queryByPlaceholderText('Value')).toBeNull();
  });

  it('removing a row via its own "x" button drops it', () => {
    useStore.setState({
      setpointPanels: [makePanel({ rows: [{ device: '', label: 'Row A', manualValue: '', manualUnit: '' }] })],
      selectedSetpointPanelIds: ['S1']
    });
    render(<PropertyInspector />);
    fireEvent.click(screen.getByRole('button', { name: 'x' }));
    expect(useStore.getState().setpointPanels[0].rows).toEqual([]);
  });
});
