// feat/device-form-from-canvas commit 1 - double-click on a schematic
// symbol opens its own device's configuration form. Tests the pure
// pieces directly (handleSymbolDblClick, the shared openDeviceForm/
// closeDeviceForm store actions, syncObjectDesignationsAfterDeviceSave)
// rather than rendering Konva - this codebase has no rendering harness
// (see diode-colors.test.ts's own established convention for why the
// wire-finish/label-edit regression checks below are source scans
// instead of full Canvas renders).

import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import { handleSymbolDblClick } from '../components/canvas/ObjectNode';
import { syncObjectDesignationsAfterDeviceSave } from '../project/DeviceFormSync';
import type { SynopticObject } from '../store';
import type { SwitchedDevice } from '../project/DeviceSchema';

import canvasSource from '../components/Canvas.tsx?raw';
import objectLabelRendererSource from '../components/ObjectLabelRenderer.tsx?raw';

function makeObj(overrides: Partial<SynopticObject> = {}): SynopticObject {
  return {
    id: 'OBJ1', type: 'electrical.circuit_breaker', category: 'Electrical',
    x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 1,
    tag: 'OBJ1', description: '', color: '#000', fill: '#000', border: '#000',
    text: '', font: 'Arial', fontSize: 12, tooltip: '',
    width: 64, height: 64, customProperties: {},
    ...overrides
  };
}

function makeSwitched(overrides: Partial<SwitchedDevice> = {}): SwitchedDevice {
  return {
    id: 'KOT_KMG1', designation: '-K1', name: 'Stycznik grzalki', behavior: 'SWITCHED', kind: 'contactor', publishToHa: false,
    feedback: { mode: 'NONE' }, command: { outputCount: 1, style: 'MAINTAINED', doClose: 'ADA1.DO.1' },
    supervision: { confirmTimeoutMs: 1000, discrepancyAlarm: false },
    safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' }, switchCounter: false,
    ...overrides
  };
}

function resetStore() {
  useStore.setState({
    objects: [], devices: [], messages: [],
    selectedIds: ['SOMETHING_ELSE'],
    deviceFormRequest: null,
    deviceCreateOrAssignRequest: null,
    isDrawingConnection: false
  });
}

function mockEvent() {
  return { cancelBubble: false };
}

describe('1. double-click on a symbol WITH a device opens that device\'s form', () => {
  beforeEach(resetStore);

  it('sets deviceFormRequest to the bound device id', () => {
    const device = makeSwitched({ id: 'KOT_KMG1' });
    const obj = makeObj({ deviceId: 'KOT_KMG1', designation: '-K1' });
    useStore.setState({ devices: [device] });

    handleSymbolDblClick(mockEvent(), obj);

    expect(useStore.getState().deviceFormRequest?.deviceId).toBe('KOT_KMG1');
  });

  it('cancels Konva bubbling so it never also reaches Canvas.tsx\'s own Stage-level dblclick handler', () => {
    const device = makeSwitched({ id: 'KOT_KMG1' });
    const obj = makeObj({ deviceId: 'KOT_KMG1' });
    useStore.setState({ devices: [device] });
    const e = mockEvent();

    handleSymbolDblClick(e, obj);

    expect(e.cancelBubble).toBe(true);
  });
});

// fix/inline-device-creation commit 3: a device-less symbol used to
// just post a Messages notice here - it now opens
// deviceCreateOrAssignRequest instead (DeviceFormDialog's own "create
// or assign" mode - see mandatory test 9 in
// device-create-or-assign.test.tsx for the fuller behavioral coverage
// of that flow). This describe block only re-covers what changed at
// THIS exact function - handleSymbolDblClick's own no-device branch.
describe('2. double-click on a symbol WITHOUT a device opens the create-or-assign flow instead of reporting it', () => {
  beforeEach(resetStore);

  it('sets deviceCreateOrAssignRequest with the symbol\'s own id/type and posts no message at all', () => {
    const obj = makeObj({ id: 'OBJ1', deviceId: undefined, designation: '-Q1', type: 'electrical.disconnect_switch' });

    handleSymbolDblClick(mockEvent(), obj);

    expect(useStore.getState().deviceFormRequest).toBeNull();
    expect(useStore.getState().deviceCreateOrAssignRequest).toEqual({
      symbolId: 'OBJ1',
      symbolType: 'electrical.disconnect_switch',
      sourceContext: expect.stringContaining('-Q1')
    });
    expect(useStore.getState().messages).toEqual([]);
  });

  it('an empty-string deviceId is treated the same as no device at all', () => {
    const obj = makeObj({ deviceId: '' });
    handleSymbolDblClick(mockEvent(), obj);
    expect(useStore.getState().deviceFormRequest).toBeNull();
    expect(useStore.getState().deviceCreateOrAssignRequest).not.toBeNull();
  });
});

describe('3. double-click on a symbol pointing at a NONEXISTENT device does not throw, and reports it', () => {
  beforeEach(resetStore);

  it('never throws', () => {
    const obj = makeObj({ deviceId: 'GHOST_1' });
    expect(() => handleSymbolDblClick(mockEvent(), obj)).not.toThrow();
  });

  it('leaves deviceFormRequest null (no empty form) and posts a WARNING naming the missing id', () => {
    const obj = makeObj({ deviceId: 'GHOST_1' });
    handleSymbolDblClick(mockEvent(), obj);

    expect(useStore.getState().deviceFormRequest).toBeNull();
    const messages = useStore.getState().messages;
    expect(messages.length).toBe(1);
    expect(messages[0].type).toBe('warning');
    expect(messages[0].text).toContain('GHOST_1');
  });
});

describe('The wire tool takes priority: a double-click while it is armed opens nothing', () => {
  beforeEach(resetStore);

  it('does nothing at all while isDrawingConnection is true, even for a valid device', () => {
    useStore.setState({ isDrawingConnection: true, devices: [makeSwitched({ id: 'KOT_KMG1' })] });
    const obj = makeObj({ deviceId: 'KOT_KMG1' });
    const e = mockEvent();

    handleSymbolDblClick(e, obj);

    expect(useStore.getState().deviceFormRequest).toBeNull();
    expect(useStore.getState().messages).toEqual([]);
    // Bubbling is left alone (not cancelled) so Canvas.tsx's own
    // Stage-level handleDblClick still receives it and finishes the wire.
    expect(e.cancelBubble).toBe(false);
  });
});

// 4. wire-finish double-click must work unchanged - regression guard via
// source scan (no Konva rendering harness in this codebase - see
// diode-colors.test.ts's own established convention for why).
describe('4. Canvas.tsx\'s own wire-finish double-click is untouched', () => {
  it('handleDblClick still finishes the wire and is still wired to the Stage', () => {
    expect(canvasSource).toContain('isDrawingConnection && drawingPointsRef.current');
    expect(canvasSource).toContain('finishDrawing()');
    expect(canvasSource).toContain('onDblClick={handleDblClick}');
    expect(canvasSource).toContain('onDblTap={handleDblClick}');
  });
});

// 5. label edit-in-place double-click must work unchanged - same
// regression-guard convention as test 4.
describe('5. ObjectLabelRenderer.tsx\'s own edit-in-place double-click is untouched', () => {
  it('startEditing is still wired to the label\'s own Group', () => {
    expect(objectLabelRendererSource).toContain('onDblClick={startEditing}');
    expect(objectLabelRendererSource).toContain('onDblTap={startEditing}');
  });
});

// 6. saving from the double-click-opened form updates the symbol's label
describe('6. syncObjectDesignationsAfterDeviceSave (App.tsx\'s own onSave)', () => {
  it('updates every object whose designation still matches the device\'s OLD designation', () => {
    const objects = [makeObj({ id: 'O1', deviceId: 'KOT_KMG1', designation: '-K1' })];
    const saved = makeSwitched({ id: 'KOT_KMG1', designation: '-K2' });
    const updates = syncObjectDesignationsAfterDeviceSave(objects, '-K1', saved);
    expect(updates).toEqual([{ id: 'O1', updates: { designation: '-K2' } }]);
  });

  it('leaves a symbol whose designation was customized away from the device\'s own untouched', () => {
    const objects = [makeObj({ id: 'O1', deviceId: 'KOT_KMG1', designation: 'Grzalka glowna' })];
    const saved = makeSwitched({ id: 'KOT_KMG1', designation: '-K2' });
    const updates = syncObjectDesignationsAfterDeviceSave(objects, '-K1', saved);
    expect(updates).toEqual([]);
  });

  it('updates every matching object, not only the one that was double-clicked (same device bound to two symbols)', () => {
    const objects = [
      makeObj({ id: 'O1', deviceId: 'KOT_KMG1', designation: '-K1' }),
      makeObj({ id: 'O2', deviceId: 'KOT_KMG1', designation: '-K1' }),
      makeObj({ id: 'O3', deviceId: 'OTHER_DEVICE', designation: '-K1' })
    ];
    const saved = makeSwitched({ id: 'KOT_KMG1', designation: '-K2' });
    const updates = syncObjectDesignationsAfterDeviceSave(objects, '-K1', saved);
    expect(updates.map(u => u.id).sort()).toEqual(['O1', 'O2']);
  });

  it('returns no updates when the designation did not actually change', () => {
    const objects = [makeObj({ id: 'O1', deviceId: 'KOT_KMG1', designation: '-K1' })];
    const saved = makeSwitched({ id: 'KOT_KMG1', designation: '-K1' });
    expect(syncObjectDesignationsAfterDeviceSave(objects, '-K1', saved)).toEqual([]);
  });
});

// 7. selection persists after closing the form
describe('7. closing the device form never touches the canvas selection', () => {
  beforeEach(resetStore);

  it('closeDeviceForm only clears deviceFormRequest, selectedIds is untouched', () => {
    useStore.setState({ selectedIds: ['OBJ1'], deviceFormRequest: { deviceId: 'KOT_KMG1' } });
    useStore.getState().closeDeviceForm();
    expect(useStore.getState().deviceFormRequest).toBeNull();
    expect(useStore.getState().selectedIds).toEqual(['OBJ1']);
  });
});

// 8. cancelling the form never changes the device
describe('8. cancelling (closeDeviceForm alone, no updateDevice call) never changes the device', () => {
  beforeEach(resetStore);

  it('the device in the store is exactly what it was before the form opened', () => {
    const device = makeSwitched({ id: 'KOT_KMG1', designation: '-K1' });
    useStore.setState({ devices: [device] });
    const obj = makeObj({ deviceId: 'KOT_KMG1' });

    handleSymbolDblClick(mockEvent(), obj);
    expect(useStore.getState().deviceFormRequest).not.toBeNull();

    // Cancel: exactly what App.tsx's own onCancel does - closeDeviceForm
    // alone, never a call to updateDevice.
    useStore.getState().closeDeviceForm();

    expect(useStore.getState().devices).toEqual([device]);
    expect(useStore.getState().deviceFormRequest).toBeNull();
  });
});

describe('openDeviceForm / closeDeviceForm (deviceFormSlice.ts) directly', () => {
  beforeEach(resetStore);

  it('opens with the given sourceContext', () => {
    useStore.setState({ devices: [makeSwitched({ id: 'KOT_KMG1' })] });
    useStore.getState().openDeviceForm('KOT_KMG1', 'Panel Properties');
    expect(useStore.getState().deviceFormRequest).toEqual({ deviceId: 'KOT_KMG1', sourceContext: 'Panel Properties' });
  });

  it('a missing device never opens the form and reports a WARNING naming the id', () => {
    useStore.getState().openDeviceForm('GHOST_2');
    expect(useStore.getState().deviceFormRequest).toBeNull();
    expect(useStore.getState().messages.some(m => m.type === 'warning' && m.text.includes('GHOST_2'))).toBe(true);
  });
});

