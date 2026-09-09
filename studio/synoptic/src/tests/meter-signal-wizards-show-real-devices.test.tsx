/** @vitest-environment jsdom */
// feat/device-list-ui commit 4 - mandatory tests 18 and 19: the meter and
// signal-panel wizards, completely unchanged (MeterWizardDialog.tsx,
// SignalPanelWizardDialog.tsx, MeterWizard.ts, SignalPanelWizard.ts - see
// GRANICE), now show REAL devices once the device registry can actually
// produce some, driven end to end through DeviceFormDialog exactly the
// way KROK 5/6 of this task's own manual verification does.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { DeviceFormDialog } from '../components/DeviceFormDialog';
import { MeterWizardDialog } from '../components/MeterWizardDialog';
import { SignalPanelWizardDialog } from '../components/SignalPanelWizardDialog';
import type { SwitchedDevice } from '../project/DeviceSchema';

function row(labelText: string): HTMLElement {
  return screen.getByText(labelText).closest('.property-row')!;
}
function input(labelText: string): HTMLInputElement {
  return row(labelText).querySelector('input') as HTMLInputElement;
}
function select(labelText: string): HTMLSelectElement {
  return row(labelText).querySelector('select') as HTMLSelectElement;
}

function makeSwitched(overrides: Partial<SwitchedDevice> = {}): SwitchedDevice {
  return {
    id: 'KOT_KMG1', designation: '-K1', name: 'Stycznik grzalki', behavior: 'SWITCHED', kind: 'contactor', publishToHa: false,
    feedback: { mode: 'NONE' },
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
      { id: 'ELA1', model: 'ELA01', channelKind: 'AI', channelCount: 8 },
      { id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 16 }
    ],
    devices: []
  });
}

describe('Meter and signal-panel wizards show real devices from the registry', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('test 18: a MEASURED device created through DeviceFormDialog appears in the meter wizard', () => {
    render(<DeviceFormDialog mode="add" onSave={(d) => useStore.getState().addDevice(d)} onCancel={() => {}} />);
    fireEvent.change(select('Zachowanie'), { target: { value: 'MEASURED' } });
    const idRow = row('Id');
    fireEvent.change(idRow.querySelector('select')!, { target: { value: 'KOT' } });
    fireEvent.change(idRow.querySelector('input')!, { target: { value: 'TEMP1' } });
    fireEvent.change(input('Oznaczenie'), { target: { value: '-B1' } });
    fireEvent.change(input('Nazwa'), { target: { value: 'Czujnik temperatury' } });
    fireEvent.change(input('Rodzaj'), { target: { value: 'sensor' } });
    fireEvent.change(input('Jednostka'), { target: { value: '°C' } });
    const inputRow = row('input');
    fireEvent.change(inputRow.querySelectorAll('select')[0], { target: { value: 'ELA1' } });
    fireEvent.change(inputRow.querySelectorAll('select')[1], { target: { value: '1' } });
    fireEvent.click(screen.getByRole('button', { name: 'Zapisz' }));

    expect(useStore.getState().devices.map(d => d.id)).toEqual(['KOT_TEMP1']);
    cleanup();

    render(<MeterWizardDialog devices={useStore.getState().devices} onConfirm={() => {}} onAddManualRow={() => {}} onCancel={() => {}} />);
    expect(screen.getByText(/-B1 - Czujnik temperatury/)).toBeTruthy();
  });

  it('test 19: the signal-panel wizard shows SIGNAL and SWITCHED devices but never a MEASURED one', () => {
    useStore.setState({
      devices: [
        makeSwitched(),
        { id: 'KOT_TEMP1', designation: '-B1', name: 'Czujnik temperatury', behavior: 'MEASURED', kind: 'sensor', publishToHa: false, input: 'ELA1.AI.1', unit: '°C', rangeMin: 0, rangeMax: 100, format: '0.0', deadband: 0.5 }
      ]
    });
    render(<SignalPanelWizardDialog devices={useStore.getState().devices} onConfirm={() => {}} onAddManualRow={() => {}} onCancel={() => {}} />);

    expect(screen.getByText(/-K1 - Stycznik grzalki/)).toBeTruthy();
    expect(screen.queryByText(/Czujnik temperatury/)).toBeNull();
  });
});
