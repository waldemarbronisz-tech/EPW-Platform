/** @vitest-environment jsdom */
// feat/device-form-from-canvas commit 2 - the shared openDeviceForm
// called from every other place an aparat is visible: Properties'
// Aparat row (2a), a meter row (2b), a signal-panel row (2c), a
// wizard row (2d), and Lista aparatow's own Edytuj button (unified
// here too, for test 12's own meaningful comparison). Renders the
// REAL components against the REAL store, same convention every other
// PropertyInspector/DeviceListDialog test in this project already uses.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { PropertyInspector } from '../components/PropertyInspector';
import { DeviceListDialog } from '../components/DeviceListDialog';
import { MeterWizardDialog } from '../components/MeterWizardDialog';
import { SignalPanelWizardDialog } from '../components/SignalPanelWizardDialog';
import { handleSymbolDblClick } from '../components/canvas/ObjectNode';
import type { SynopticObject } from '../store';
import type { SwitchedDevice, MeasuredDevice } from '../project/DeviceSchema';

import objectNodeSource from '../components/canvas/ObjectNode.tsx?raw';
import deviceListDialogSource from '../components/DeviceListDialog.tsx?raw';
import appSource from '../App.tsx?raw';

function makeObj(overrides: Partial<SynopticObject> = {}): SynopticObject {
  return {
    id: 'O1', type: 'electrical.circuit_breaker', category: 'Electrical',
    x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 1,
    tag: 'O1', description: '', color: '#000', fill: '#000', border: '#000',
    text: '', font: 'Arial', fontSize: 12, tooltip: '',
    width: 64, height: 64, customProperties: {},
    ...overrides
  };
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

function makeMeasured(overrides: Partial<MeasuredDevice> = {}): MeasuredDevice {
  return {
    id: 'KOT_TT1', designation: '-TT1', name: 'Czujnik temperatury', behavior: 'MEASURED', kind: 'sensor', publishToHa: false,
    input: 'ELA1.AI.1', unit: 'C', rangeMin: 0, rangeMax: 100, format: '0.0', deadband: 1,
    ...overrides
  };
}

function resetStore() {
  useStore.setState({
    objects: [], connections: [], meters: [], signalPanels: [], frames: [], groupCommands: [], setpointPanels: [],
    locations: [{ code: 'KOT', description: 'Kotlownia' }],
    cards: [{ id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 16 }, { id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 16 }],
    devices: [makeSwitched(), makeMeasured()],
    selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: [],
    messages: [],
    deviceFormRequest: null,
    history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [], groupCommands: [], setpointPanels: [] }],
    historyIndex: 0
  });
}

describe('2a / 9. Properties\' Aparat row has a button to open the bound device\'s form', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('9: disabled when Aparat is empty (no device bound)', () => {
    useStore.setState({ objects: [makeObj({ deviceId: undefined })], selectedIds: ['O1'] });
    render(<PropertyInspector />);
    const button = screen.getByRole('button', { name: 'Otworz...' }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
  });

  it('enabled and opens the bound device\'s form when Aparat is set', () => {
    useStore.setState({ objects: [makeObj({ deviceId: 'KOT_KMG1', designation: '-K1' })], selectedIds: ['O1'] });
    render(<PropertyInspector />);
    const button = screen.getByRole('button', { name: 'Otworz...' }) as HTMLButtonElement;
    expect(button.disabled).toBe(false);

    fireEvent.click(button);
    expect(useStore.getState().deviceFormRequest?.deviceId).toBe('KOT_KMG1');
    expect(useStore.getState().deviceFormRequest?.sourceContext).toContain('Panel Properties');
  });
});

describe('2b / 10. Double-click on a meter row opens that row\'s own device form', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('10: opens the form for a MEASURED-device-bound row', () => {
    useStore.setState({ meters: [{ id: 'M1', x: 0, y: 0, width: 200, fontSize: 13, rows: [{ device: 'KOT_TT1', label: '', manualValue: '', manualUnit: '' }] }], selectedMeterIds: ['M1'] });
    render(<PropertyInspector />);
    fireEvent.doubleClick(screen.getByPlaceholderText('Label').closest('.property-row')!);
    expect(useStore.getState().deviceFormRequest?.deviceId).toBe('KOT_TT1');
  });

  it('a manual row (no device) does nothing on double-click', () => {
    useStore.setState({ meters: [{ id: 'M1', x: 0, y: 0, width: 200, fontSize: 13, rows: [{ device: '', label: 'Manual', manualValue: '1', manualUnit: 'C' }] }], selectedMeterIds: ['M1'] });
    render(<PropertyInspector />);
    fireEvent.doubleClick(screen.getByDisplayValue('Manual').closest('.property-row')!);
    expect(useStore.getState().deviceFormRequest).toBeNull();
  });
});

describe('2c. Double-click on a signal panel row opens that row\'s own device form', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('opens the form for a SWITCHED-device-bound row', () => {
    useStore.setState({ signalPanels: [{ id: 'P1', x: 0, y: 0, width: 160, fontSize: 13, rows: [{ device: 'KOT_KMG1', label: '', manualState: 'OFF' }] }], selectedSignalPanelIds: ['P1'] });
    render(<PropertyInspector />);
    fireEvent.doubleClick(screen.getByPlaceholderText('Label').closest('.property-row')!);
    expect(useStore.getState().deviceFormRequest?.deviceId).toBe('KOT_KMG1');
  });
});

describe('2d / 11. Double-click on a wizard row opens the device form without touching the checkbox', () => {
  afterEach(cleanup);

  it('11 (meter wizard): opens the form and leaves the checkbox unchecked', () => {
    render(
      <MeterWizardDialog
        devices={[makeMeasured()]}
        onConfirm={() => {}}
        onAddManualRow={() => {}}
        onCancel={() => {}}
      />
    );
    useStore.setState({ deviceFormRequest: null });
    const checkbox = screen.getByRole('checkbox') as HTMLInputElement;
    expect(checkbox.checked).toBe(false);

    fireEvent.doubleClick(screen.getByText('-TT1 - Czujnik temperatury'));

    expect(useStore.getState().deviceFormRequest?.deviceId).toBe('KOT_TT1');
    expect(checkbox.checked).toBe(false);
  });

  it('the checkbox itself still toggles selection normally (regression check)', () => {
    render(
      <MeterWizardDialog
        devices={[makeMeasured()]}
        onConfirm={() => {}}
        onAddManualRow={() => {}}
        onCancel={() => {}}
      />
    );
    const checkbox = screen.getByRole('checkbox') as HTMLInputElement;
    fireEvent.click(checkbox);
    expect(checkbox.checked).toBe(true);
    expect(screen.getByText(/Zaznaczono: 1/)).toBeTruthy();
  });

  it('11 (signal panel wizard): opens the form and leaves the checkbox unchecked', () => {
    render(
      <SignalPanelWizardDialog
        devices={[makeSwitched()]}
        onConfirm={() => {}}
        onAddManualRow={() => {}}
        onCancel={() => {}}
      />
    );
    useStore.setState({ deviceFormRequest: null });
    const checkbox = screen.getByRole('checkbox') as HTMLInputElement;

    fireEvent.doubleClick(screen.getByText('-K1 - Stycznik grzalki'));

    expect(useStore.getState().deviceFormRequest?.deviceId).toBe('KOT_KMG1');
    expect(checkbox.checked).toBe(false);
  });
});

describe('12. The form opened from the schematic and from Lista aparatow is the SAME component', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('both ObjectNode.tsx (schematic double-click) and DeviceListDialog.tsx (Edytuj) call the identical shared function, by source', () => {
    expect(objectNodeSource).toContain('.openDeviceForm(');
    expect(deviceListDialogSource).toContain('.openDeviceForm(');
  });

  it('App.tsx renders the SAME DeviceFormDialog import from exactly two request sites (deviceFormRequest, deviceCreateOrAssignRequest) - never a second, different form component', () => {
    // fix/inline-device-creation commit 3: a device-less symbol's own
    // double-click now opens deviceCreateOrAssignRequest instead of
    // posting a Messages notice - a second call site of the identical
    // <DeviceFormDialog>, not a second form (GRANICE: "nie twórz
    // drugiego okna formularza aparatu").
    const lazyImportMatches = appSource.match(/const DeviceFormDialog = lazy\(/g) || [];
    expect(lazyImportMatches.length).toBe(1);
    const renderMatches = appSource.match(/<DeviceFormDialog/g) || [];
    expect(renderMatches.length).toBe(2);
  });

  it('DeviceListDialog.tsx itself only ever renders DeviceFormDialog in mode="add" now - Edytuj no longer has a local copy', () => {
    expect(deviceListDialogSource).toContain('mode="add"');
    expect(deviceListDialogSource).not.toContain("mode={form.mode}");
  });

  it('behaviorally: double-clicking a bound symbol and clicking Edytuj on the same device produce the identical deviceFormRequest shape', () => {
    useStore.setState({ objects: [makeObj({ deviceId: 'KOT_KMG1' })] });
    handleSymbolDblClick({ cancelBubble: false }, useStore.getState().objects[0]);
    const fromSchematic = useStore.getState().deviceFormRequest;
    expect(fromSchematic?.deviceId).toBe('KOT_KMG1');

    useStore.getState().closeDeviceForm();

    render(<DeviceListDialog onClose={() => {}} />);
    fireEvent.click(screen.getByText('KOT_KMG1'));
    fireEvent.click(screen.getByRole('button', { name: 'Edytuj' }));
    const fromList = useStore.getState().deviceFormRequest;

    expect(fromList?.deviceId).toBe(fromSchematic?.deviceId);
  });

  it('Edytuj opens with no sourceContext, so the form\'s header stays exactly what it always was for this path', () => {
    render(<DeviceListDialog onClose={() => {}} />);
    fireEvent.click(screen.getByText('KOT_KMG1'));
    fireEvent.click(screen.getByRole('button', { name: 'Edytuj' }));
    expect(useStore.getState().deviceFormRequest?.sourceContext).toBeUndefined();
  });
});
