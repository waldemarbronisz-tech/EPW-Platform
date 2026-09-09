// feat/device-list-ui commit 2 - mandatory test 22: the whole device
// registry (locations, cards, devices - DeviceSchema.ts's DeviceRegistry
// shape) survives a save/load round trip through ProjectManager
// unchanged, the same path meter-devices-roundtrip.test.ts already
// exercises for `devices` alone.

import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import { ProjectManager } from '../project/ProjectManager';
import type { SwitchedDevice, LocationEntry, CardEntry } from '../project/DeviceSchema';

function makeLocations(): LocationEntry[] {
  return [{ code: 'KOT', description: 'Kotlownia' }];
}

function makeCards(): CardEntry[] {
  return [
    { id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 16 },
    { id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 16 }
  ];
}

function makeSwitched(): SwitchedDevice {
  return {
    id: 'KOT_KMG1', designation: '-K1', name: 'Stycznik grzalki', behavior: 'SWITCHED', kind: 'contactor', publishToHa: false,
    feedback: { mode: 'DUAL', diClosed: 'ELA1.DI.1', diOpen: 'ELA1.DI.2' },
    command: { outputCount: 1, style: 'MAINTAINED', doClose: 'ADA1.DO.1' },
    supervision: { confirmTimeoutMs: 500, discrepancyAlarm: false },
    safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' },
    switchCounter: false
  };
}

describe('Device registry (locations + cards + devices) round-trip through ProjectManager', () => {
  beforeEach(() => {
    useStore.setState({
      objects: [], connections: [], meters: [], devices: [], locations: [], cards: [],
      selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [],
      history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [] }],
      historyIndex: 0
    });
  });

  it('test 22: locations, cards and devices all round-trip identically through save then load', () => {
    useStore.setState({ locations: makeLocations(), cards: makeCards(), devices: [makeSwitched()] });

    const json = ProjectManager.getProjectData();
    expect(json).not.toBeNull();

    // Simulate closing and reopening the project.
    useStore.setState({ locations: [], cards: [], devices: [] });
    const ok = ProjectManager.loadProject(json!, 'roundtrip.epwsyn');

    expect(ok).toBe(true);
    expect(useStore.getState().locations).toEqual(makeLocations());
    expect(useStore.getState().cards).toEqual(makeCards());
    expect(useStore.getState().devices).toEqual([makeSwitched()]);
  });

  it('a project file with no locations/cards fields at all loads as empty arrays, not an error (legacy file)', () => {
    const projectJson = ProjectManager.getProjectData();
    const project = JSON.parse(projectJson!);
    delete project.locations;
    delete project.cards;

    const ok = ProjectManager.loadProject(JSON.stringify(project), 'legacy.epwsyn');

    expect(ok).toBe(true);
    expect(useStore.getState().locations).toEqual([]);
    expect(useStore.getState().cards).toEqual([]);
  });
});
