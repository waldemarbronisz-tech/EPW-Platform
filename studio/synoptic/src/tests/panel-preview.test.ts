// Panel preview (store/previewSlice.ts): the main view screen shown as
// the panel shows it, operable - a click on an apparatus is a command
// for the controller when live is on, and the simulation otherwise; the
// "main view" mark round-trips through the file and decides which
// screen the preview (and runtime's page) opens with.

import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import { ProjectManager } from '../project/ProjectManager';
import { computePanelView } from '../utils/CanvasView';
import type { Device } from '../project/DeviceSchema';
import type { SynopticObject } from '../store';

const switched = (id: string, feedback: Record<string, unknown>): Device => ({
  id, designation: '-K1', name: id, behavior: 'SWITCHED', kind: 'contactor', publishToHa: false,
  feedback, extraInputs: {}, command: { outputCount: 1, style: 'MAINTAINED', doClose: 'ADA1.DO.1' },
  supervision: { confirmTimeoutMs: 2000, discrepancyAlarm: true },
  safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' }, switchCounter: false,
} as unknown as Device);

const obj = (id: string, type: string, extra: Partial<SynopticObject> = {}): SynopticObject => ({
  id, type, category: 'ELECTRICAL', x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1, visible: true, locked: false,
  layer: 1, tag: '', description: '', color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
  tooltip: '', width: 40, height: 40, customProperties: {}, editor: { preview_state: 'OFF' }, ...extra,
} as unknown as SynopticObject);

describe('panel preview', () => {
  beforeEach(() => {
    ProjectManager.newProject('Preview');
  });

  it('opens on the main view, puts the editor into preview mode and comes back to the edited screen', () => {
    const first = useStore.getState().activeScreenId;
    useStore.getState().addScreen('Biuro');
    const second = useStore.getState().activeScreenId;
    useStore.getState().switchScreen(first);
    useStore.getState().setMainScreen(second);
    expect(useStore.getState().mainScreenId).toBe(second);
    expect(useStore.getState().previewMode).toBe(false);

    useStore.getState().enterPanelPreview(null);
    let s = useStore.getState();
    expect(s.panelPreview).toEqual({ screenId: second, returnScreenId: first, wasPreviewMode: false });
    expect(s.activeScreenId).toBe(second);
    expect(s.previewMode).toBe(true);

    // Another screen from the preview's own selector keeps the way back.
    useStore.getState().enterPanelPreview(first);
    s = useStore.getState();
    expect(s.panelPreview?.screenId).toBe(first);
    expect(s.panelPreview?.returnScreenId).toBe(first);

    useStore.getState().exitPanelPreview();
    s = useStore.getState();
    expect(s.panelPreview).toBeNull();
    expect(s.activeScreenId).toBe(first);
    expect(s.previewMode).toBe(false);

    // Without a main view the active screen is shown; an unknown id too.
    useStore.getState().setMainScreen(null);
    useStore.getState().enterPanelPreview('nope');
    expect(useStore.getState().panelPreview?.screenId).toBe(first);
    useStore.getState().exitPanelPreview();
  });

  it('a click on a live apparatus queues the opposite command for the controller', () => {
    useStore.setState({
      objects: [obj('o1', 'electrical.circuit_breaker', { deviceId: 'KOT_KM1' }), obj('o2', 'building.chair')],
      devices: [switched('KOT_KM1', { mode: 'SINGLE', diClosed: 'ELA1.DI.1', invert: false })],
    });
    useStore.getState().setLiveValues({ 'ELA1.DI.1': true });
    expect(useStore.getState().commandAt('o1')).toEqual({ deviceId: 'KOT_KM1', action: 'OPEN' });
    useStore.getState().setLiveValues({ 'ELA1.DI.1': false });
    expect(useStore.getState().commandAt('o1')).toEqual({ deviceId: 'KOT_KM1', action: 'CLOSE' });
    expect(useStore.getState().commandAt('o2')).toBeNull();          // no apparatus behind it
    expect(useStore.getState().commandAt('missing')).toBeNull();
    expect(useStore.getState().takeCommands()).toEqual([
      { deviceId: 'KOT_KM1', action: 'OPEN' }, { deviceId: 'KOT_KM1', action: 'CLOSE' },
    ]);
    expect(useStore.getState().takeCommands()).toEqual([]);           // drained
    useStore.getState().setLiveValues(null);
  });

  it('the main view mark round-trips through the file and a stale one is dropped', () => {
    const first = useStore.getState().activeScreenId;
    useStore.getState().addScreen('Biuro');
    const second = useStore.getState().activeScreenId;
    useStore.getState().setMainScreen(second);
    const json = ProjectManager.getProjectData()!;
    expect(JSON.parse(json).mainScreenId).toBe(second);

    ProjectManager.newProject('Other');
    expect(useStore.getState().mainScreenId).toBeNull();
    ProjectManager.loadProject(json, 'p.epwsyn');
    expect(useStore.getState().mainScreenId).toBe(second);
    expect(useStore.getState().activeScreenId).not.toBe(first === second ? '' : '');

    const stale = JSON.parse(json);
    stale.mainScreenId = 'gone';
    ProjectManager.loadProject(JSON.stringify(stale), 'p.epwsyn');
    expect(useStore.getState().mainScreenId).toBeNull();
  });

  it('the panel view fits the runtime frame edge to edge, else everything drawn with a margin', () => {
    const frame = computePanelView({ x: 100, y: 100, width: 800, height: 600 }, null, 800, 600);
    expect(frame.zoom).toBeCloseTo(0.99, 5);
    const content = computePanelView(undefined, { minX: 0, minY: 0, maxX: 400, maxY: 300 }, 800, 600);
    expect(content.zoom).toBeCloseTo(2 * 0.92, 5);
    expect(computePanelView(undefined, null, 800, 600)).toEqual({ zoom: 1, panX: 0, panY: 0 });
  });
});
