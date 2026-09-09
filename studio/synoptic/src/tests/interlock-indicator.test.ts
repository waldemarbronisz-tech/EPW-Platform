// feat/control-elements commit 3 - configurable interlock indication.
// Covers isSymbolInterlocked (InterlockIndicator.ts) - a pure display
// check, not a validation rule, mirroring device-symbol-binding.test.tsx's
// own coverage of isSymbolDeviceMissing.

import { describe, it, expect } from 'vitest';
import { isSymbolInterlocked } from '../project/InterlockIndicator';
import type { SynopticObject } from '../store/types';
import type { Device, SwitchedDevice, SignalDevice } from '../project/DeviceSchema';

function makeObj(overrides: Partial<SynopticObject> = {}): SynopticObject {
  return {
    id: 'O1', type: 'electrical.contactor', category: 'Electrical',
    x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 1,
    tag: '', description: '', color: '#000', fill: '#000', border: '#000',
    text: '', font: 'Arial', fontSize: 12, tooltip: '',
    width: 64, height: 64, customProperties: {},
    ...overrides
  };
}

function makeSwitched(overrides: Partial<SwitchedDevice> = {}): SwitchedDevice {
  return {
    id: 'KOT_KMG1', designation: '-K1', name: 'Stycznik', behavior: 'SWITCHED', kind: 'contactor', publishToHa: false,
    feedback: { mode: 'NONE' }, command: { outputCount: 1, style: 'MAINTAINED', doClose: 'ADA1.DO.1' },
    supervision: { confirmTimeoutMs: 1000, discrepancyAlarm: false },
    safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' }, switchCounter: false,
    ...overrides
  };
}

function makeSignal(): SignalDevice {
  return {
    id: 'KOT_S1', designation: '-S1', name: 'Czujnik', behavior: 'SIGNAL', kind: 'sensor', publishToHa: false,
    feedback: { di: 'ELA1.DI.1', invert: false }, alarmState: 'HIGH', debounceMs: 50
  };
}

describe('isSymbolInterlocked', () => {
  it('false when the object has no deviceId at all', () => {
    const obj = makeObj({ deviceId: undefined });
    expect(isSymbolInterlocked(obj, [makeSwitched({ id: 'X', interlock: { closeDescription: 'blocked' } })])).toBe(false);
  });

  it('false when the device does not exist (dangling binding)', () => {
    const obj = makeObj({ deviceId: 'GONE' });
    expect(isSymbolInterlocked(obj, [])).toBe(false);
  });

  it('false when the bound device exists but is not SWITCHED', () => {
    const devices: Device[] = [makeSignal()];
    const obj = makeObj({ deviceId: 'KOT_S1' });
    expect(isSymbolInterlocked(obj, devices)).toBe(false);
  });

  it('false when the SWITCHED device has no interlock field at all', () => {
    const devices: Device[] = [makeSwitched()];
    const obj = makeObj({ deviceId: 'KOT_KMG1' });
    expect(isSymbolInterlocked(obj, devices)).toBe(false);
  });

  it('false when interlock is present but both descriptions are blank/whitespace-only', () => {
    const devices: Device[] = [makeSwitched({ interlock: { closeDescription: '   ', openDescription: '' } })];
    const obj = makeObj({ deviceId: 'KOT_KMG1' });
    expect(isSymbolInterlocked(obj, devices)).toBe(false);
  });

  it('true when closeDescription alone is a real, non-blank string', () => {
    const devices: Device[] = [makeSwitched({ interlock: { closeDescription: 'Zablokowane, gdy drzwi otwarte' } })];
    const obj = makeObj({ deviceId: 'KOT_KMG1' });
    expect(isSymbolInterlocked(obj, devices)).toBe(true);
  });

  it('true when openDescription alone is a real, non-blank string', () => {
    const devices: Device[] = [makeSwitched({ interlock: { openDescription: 'Zablokowane podczas biegu pompy' } })];
    const obj = makeObj({ deviceId: 'KOT_KMG1' });
    expect(isSymbolInterlocked(obj, devices)).toBe(true);
  });

  it('true when both descriptions are set', () => {
    const devices: Device[] = [makeSwitched({ interlock: { closeDescription: 'A', openDescription: 'B' } })];
    const obj = makeObj({ deviceId: 'KOT_KMG1' });
    expect(isSymbolInterlocked(obj, devices)).toBe(true);
  });

  it('two objects pointing at the same interlocked device are both flagged (no per-object state)', () => {
    const devices: Device[] = [makeSwitched({ interlock: { closeDescription: 'A' } })];
    const obj1 = makeObj({ id: 'O1', deviceId: 'KOT_KMG1' });
    const obj2 = makeObj({ id: 'O2', deviceId: 'KOT_KMG1' });
    expect(isSymbolInterlocked(obj1, devices)).toBe(true);
    expect(isSymbolInterlocked(obj2, devices)).toBe(true);
  });
});
