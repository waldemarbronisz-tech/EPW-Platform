// Task "wylacznik jednocewkowy bistabilny" - a third command style,
// PULSE_TOGGLE: one impulse-relay coil (R15/3P-class) behind one or two
// outputs, every pulse toggles, so feedback is mandatory (without it the
// runtime could not know whether a CLOSE would close or open the device).
import { describe, it, expect } from 'vitest';
import { validateDeviceFields, validateDeviceRegistry } from '../project/DeviceValidation';
import type { CardEntry, LocationEntry, SwitchedDevice } from '../project/DeviceSchema';

const KOT: LocationEntry = { code: 'KOT', description: 'Kotlownia' };
const CARDS: CardEntry[] = [
  { id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 16 },
  { id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 16 },
];

function km1(overrides: Partial<SwitchedDevice['command']> = {}, feedbackMode: 'SINGLE' | 'DUAL' | 'NONE' = 'SINGLE'): SwitchedDevice {
  const feedback: SwitchedDevice['feedback'] = feedbackMode === 'NONE' ? { mode: 'NONE' }
    : feedbackMode === 'SINGLE' ? { mode: 'SINGLE', diClosed: 'ELA1.DI.2' }
    : { mode: 'DUAL', diClosed: 'ELA1.DI.2', diOpen: 'ELA1.DI.3' };
  return {
    id: 'KOT_KM1', designation: '-KM1', name: 'Stycznik KM1', behavior: 'SWITCHED', kind: 'contactor',
    publishToHa: false, feedback,
    // The schematic: DO3 "na zalacz", DO4 "na wylacz", both onto KP2's one coil.
    command: { outputCount: 2, style: 'PULSE_TOGGLE', doClose: 'ADA1.DO.3', doOpen: 'ADA1.DO.4', pulseMs: 100, ...overrides },
    supervision: { confirmTimeoutMs: 2000, discrepancyAlarm: true },
    safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' },
    switchCounter: false,
  };
}

describe('PULSE_TOGGLE - single-coil impulse relay', () => {
  it('the schematic configuration (two outputs, one coil, DI feedback) is valid', () => {
    expect(validateDeviceFields(km1())).toEqual([]);
    const result = validateDeviceRegistry({ locations: [KOT], cards: CARDS, devices: [km1()] });
    expect(result.valid).toBe(true);
  });

  it('is also valid with a single output pulsing the coil both ways', () => {
    expect(validateDeviceFields(km1({ outputCount: 1, doOpen: undefined }))).toEqual([]);
  });

  it('needs a pulse time like PULSE does', () => {
    const issues = validateDeviceFields(km1({ pulseMs: undefined }));
    expect(issues.some(i => i.code === 'SWITCHED_PULSE_MISSING_PULSEMS')).toBe(true);
  });

  it('refuses feedback mode NONE - every pulse toggles, so the state must be known', () => {
    const issues = validateDeviceFields(km1({}, 'NONE'));
    expect(issues.some(i => i.code === 'SWITCHED_TOGGLE_NEEDS_FEEDBACK')).toBe(true);
  });

  it('plain PULSE with feedback NONE stays allowed, as before', () => {
    const issues = validateDeviceFields(km1({ style: 'PULSE' }, 'NONE'));
    expect(issues.some(i => i.code === 'SWITCHED_TOGGLE_NEEDS_FEEDBACK')).toBe(false);
  });

  it('the shape check accepts the new style and still rejects an unknown one', () => {
    const ok = validateDeviceRegistry({ locations: [KOT], cards: CARDS, devices: [km1()] });
    expect(ok.issues.some(i => i.code === 'DEVICE_INVALID_SHAPE')).toBe(false);
    const bad = validateDeviceRegistry({
      locations: [KOT], cards: CARDS,
      devices: [{ ...km1(), command: { ...km1().command, style: 'FLIP' } } as unknown as SwitchedDevice],
    });
    expect(bad.valid).toBe(false);
  });
});
