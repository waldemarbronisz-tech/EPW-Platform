// feat/meter-element part B: the project's device list actually
// survives a save/load round trip through ProjectManager - the
// concrete path a meter's device data travels: a project file's
// optional `devices` field -> ProjectManager.loadProject ->
// useStore's `devices` array -> MeterResolver.getMeasuredDevices /
// resolveMeterRow. This test exercises the file <-> store half of that
// path; meter-resolver.test.ts exercises the resolver half.

import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import { ProjectManager } from '../project/ProjectManager';
import type { MeasuredDevice } from '../project/DeviceSchema';

function makeMeasured(id: string): MeasuredDevice {
  return {
    id, designation: `-B${id}`, name: `Sensor ${id}`, behavior: 'MEASURED', kind: 'sensor', publishToHa: false,
    input: 'ELA1.AI.1', unit: 'kW', rangeMin: 0, rangeMax: 400, format: '0.0', deadband: 1
  };
}

describe('Device list round-trip through ProjectManager', () => {
  beforeEach(() => {
    useStore.setState({
      objects: [], connections: [], meters: [], devices: [],
      selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [],
      history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [] }],
      historyIndex: 0
    });
  });

  it('getProjectData includes the store devices array', () => {
    useStore.setState({ devices: [makeMeasured('DEV1')] });
    const json = ProjectManager.getProjectData();
    expect(json).not.toBeNull();
    const parsed = JSON.parse(json!);
    expect(parsed.devices).toEqual([makeMeasured('DEV1')]);
  });

  it('loadProject populates the store devices array from the file', () => {
    const projectJson = ProjectManager.getProjectData(); // an empty-devices baseline
    const project = JSON.parse(projectJson!);
    project.devices = [makeMeasured('DEV2')];

    const ok = ProjectManager.loadProject(JSON.stringify(project), 'test.epwsyn');

    expect(ok).toBe(true);
    expect(useStore.getState().devices).toEqual([makeMeasured('DEV2')]);
  });

  it('loading a project file with no devices field at all yields an empty array, not an error', () => {
    const projectJson = ProjectManager.getProjectData();
    const project = JSON.parse(projectJson!);
    delete project.devices;

    const ok = ProjectManager.loadProject(JSON.stringify(project), 'legacy.epwsyn');

    expect(ok).toBe(true);
    expect(useStore.getState().devices).toEqual([]);
  });
});
