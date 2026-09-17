// Punkt 2 / luka 7 ("unify the two apparatus registries"): Studio's own
// "Aparaty" list arrives through project/StudioBridge.ts's
// importDevicesFromStudio() (main.tsx puts it on window as
// __synopticImportDevices) - ADD-ONLY, like cards and locations: a
// device this editor already has keeps its own richer fields.
import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import { ProjectManager } from '../project/ProjectManager';
import { importDevicesFromStudio } from '../project/StudioBridge';
import type { SwitchedDevice, SignalDevice } from '../project/DeviceSchema';

const km1 = (): SwitchedDevice => ({
  id: 'KOT_KM1', designation: '-KM1', name: 'KOT_KM1', behavior: 'SWITCHED', kind: 'contactor', publishToHa: false,
  feedback: { mode: 'SINGLE', diClosed: 'ELA1.DI.2' },
  command: { outputCount: 2, style: 'PULSE_TOGGLE', doClose: 'ADA1.DO.3', doOpen: 'ADA1.DO.4', pulseMs: 100 },
  supervision: { confirmTimeoutMs: 1000, discrepancyAlarm: false },
  safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' },
  switchCounter: false,
});

const alarm = (): SignalDevice => ({
  id: 'KOT_ALARM', designation: '-ALARM', name: 'KOT_ALARM', behavior: 'SIGNAL', kind: 'signal', publishToHa: false,
  feedback: { di: 'ELA1.DI.6', invert: false }, alarmState: 'HIGH', debounceMs: 50,
});

describe('Studio apparatus bridge', () => {
  beforeEach(() => {
    ProjectManager.newProject('Fresh');
  });

  it('adds the devices Studio pushes and reports their ids', () => {
    expect(importDevicesFromStudio([km1(), alarm()])).toEqual(['KOT_KM1', 'KOT_ALARM']);
    const devices = useStore.getState().devices;
    expect(devices.map(d => d.id)).toEqual(['KOT_KM1', 'KOT_ALARM']);
    expect((devices[0] as SwitchedDevice).command.style).toBe('PULSE_TOGGLE');
    expect(useStore.getState().isDirty).toBe(true);
  });

  it('never overwrites a device this editor already has - the richer Synoptic fields survive', () => {
    useStore.getState().addDevice({ ...km1(), name: 'Stycznik KM1 (pompa)', publishToHa: true });

    expect(importDevicesFromStudio([km1(), alarm()])).toEqual(['KOT_ALARM']);

    const devices = useStore.getState().devices;
    expect(devices).toHaveLength(2);
    expect(devices[0].name).toBe('Stycznik KM1 (pompa)');
    expect(devices[0].publishToHa).toBe(true);
  });

  it('skips entries without an id and repeated ids within one push', () => {
    const added = importDevicesFromStudio([{ ...alarm(), id: '' }, alarm(), alarm(), null as never]);
    expect(added).toEqual(['KOT_ALARM']);
    expect(useStore.getState().devices).toHaveLength(1);
  });

  it('the imported device is what Studio sends - the same document round-trips through the project JSON', () => {
    importDevicesFromStudio([km1()]);
    const doc = JSON.parse(ProjectManager.getProjectData()!);
    expect(doc.devices[0]).toEqual(km1());
  });
});
