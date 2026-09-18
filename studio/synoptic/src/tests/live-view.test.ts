// feat/live-view (SPEC "żywe stany przy punktach podczas projektowania
// ekranu"): Studio pushes the controller's tag values; device-bound
// symbols draw their live state, the document's preview states stay.
import { describe, it, expect } from 'vitest';
import { useStore } from '../store';
import { deviceAsserted, liveStateFor, liveStatesFor, tagAsserted } from '../store/liveSlice';
import { setLiveValuesFromStudio } from '../project/StudioBridge';
import type { Device } from '../project/DeviceSchema';
import type { SynopticObject } from '../store';
import rendererSource from '../symbols/SymbolRenderer.tsx?raw';
import floorSource from '../components/RoomFloorLayer.tsx?raw';
import mainSource from '../main.tsx?raw';

const switched = (id: string, feedback: Record<string, unknown>, extra: Record<string, unknown> = {}): Device => ({
  id, designation: '-K1', name: id, behavior: 'SWITCHED', kind: 'contactor', publishToHa: false,
  feedback, extraInputs: {}, command: { outputCount: 1, style: 'MAINTAINED', doClose: 'ADA1.DO.1' },
  supervision: { confirmTimeoutMs: 2000, discrepancyAlarm: true },
  safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' }, switchCounter: false, ...extra,
} as unknown as Device);

const obj = (id: string, type: string, extra: Partial<SynopticObject> = {}): SynopticObject => ({
  id, type, category: 'BUILDING', x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1, visible: true, locked: false,
  layer: 1, tag: '', description: '', color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
  tooltip: '', width: 40, height: 40, customProperties: {}, editor: { preview_state: 'OFF' }, ...extra,
} as unknown as SynopticObject);

describe('live view', () => {
  it('reads a tag the way the controller means it', () => {
    expect(tagAsserted(true)).toBe(true);
    expect(tagAsserted(0)).toBe(false);
    expect(tagAsserted('on')).toBe(true);
    expect(tagAsserted(undefined)).toBeNull();
  });

  it('derives a device state from its feedback mode', () => {
    const dual = switched('K1', { mode: 'DUAL', diClosed: 'ELA1.DI.1', diOpen: 'ELA1.DI.2' });
    expect(deviceAsserted(dual, { 'ELA1.DI.1': true, 'ELA1.DI.2': false })).toBe(true);
    expect(deviceAsserted(dual, { 'ELA1.DI.1': false, 'ELA1.DI.2': true })).toBe(false);
    expect(deviceAsserted(dual, { 'ELA1.DI.1': true, 'ELA1.DI.2': true })).toBeNull();   // discrepancy: no answer
    expect(deviceAsserted(dual, { 'ELA1.DI.1': true })).toBeNull();                       // a tag missing
    const single = switched('K2', { mode: 'SINGLE', diClosed: 'ELA1.DI.3', invert: true });
    expect(deviceAsserted(single, { 'ELA1.DI.3': false })).toBe(true);
    const none = switched('K3', { mode: 'NONE' });
    expect(deviceAsserted(none, { 'ADA1.DO.1': 1 })).toBe(true);                          // the commanded output
  });

  it("maps asserted onto the symbol's own two-state pair", () => {
    expect(liveStateFor('building.luminaire', true)).toBe('ON');
    expect(liveStateFor('building.luminaire', false)).toBe('OFF');
    expect(liveStateFor('building.socket_outlet', true)).toBe('LIVE');
    expect(liveStateFor('building.table', true)).toBeNull();                              // nothing to show
  });

  it('the store derives per-object states from pushed values and clears them on null', () => {
    useStore.setState({
      objects: [obj('lamp', 'building.luminaire', { deviceId: 'K1' }), obj('lamp2', 'building.luminaire', { tag: 'ELA1.DI.5' }),
                obj('table', 'building.table')],
      devices: [switched('K1', { mode: 'SINGLE', diClosed: 'ELA1.DI.1' })],
      liveValues: null, liveStates: {},
    });
    setLiveValuesFromStudio({ 'ELA1.DI.1': true, 'ELA1.DI.5': 0 });
    expect(useStore.getState().liveStates).toEqual({ lamp: 'ON', lamp2: 'OFF' });
    expect(useStore.getState().objects.find(o => o.id === 'lamp')!.editor?.preview_state).toBe('OFF');  // untouched
    setLiveValuesFromStudio(null);
    expect(useStore.getState().liveStates).toEqual({}) ;
    expect(useStore.getState().liveValues).toBeNull();
    expect(liveStatesFor([], [], {})).toEqual({});
  });

  it('the renderer and the floor glow prefer the live state; Studio reaches it through __synopticLiveValues (source scan)', () => {
    expect(rendererSource).toContain('const liveState = useStore(s => s.liveStates[obj.id]);');
    expect(rendererSource).toContain("const state = liveState ?? (obj.editor?.preview_state || 'NORMAL');");
    expect(floorSource).toContain("(liveStates[o.id] ?? o.editor?.preview_state) === 'ON'");
    expect(mainSource).toContain('__synopticLiveValues');
  });
});
