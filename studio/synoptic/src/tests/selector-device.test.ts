// feat/control-elements commit 1 - the SELECTOR device behavior (a
// physical Hand-Off-Auto-style selector switch). Mirrors the structure
// of device-validation.test.ts / device-signals.test.ts for the four
// pre-existing behaviors, but kept in its own file since this is a new
// behavior added well after those files' own numbered test sequences.

import { describe, it, expect } from 'vitest';
import { validateDeviceFields, validateDeviceRegistry } from '../project/DeviceValidation';
import { getDeviceSignals, getDeviceCommands, getDeviceSignalNames } from '../project/DeviceSignals';
import { defaultSelectorFields, defaultFieldsForBehavior } from '../project/DeviceFormDefaults';
import type { CardEntry, DeviceRegistry, LocationEntry, SelectorDevice } from '../project/DeviceSchema';

const KOT: LocationEntry = { code: 'KOT', description: 'Kotlownia' };
const CARDS: CardEntry[] = [{ id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 16 }];

function makeSelector(overrides: Partial<SelectorDevice> = {}): SelectorDevice {
  return {
    id: 'KOT_HOA1',
    designation: '-SA1',
    name: 'Przelacznik reka-0-automat',
    behavior: 'SELECTOR',
    kind: 'selector_switch',
    publishToHa: false,
    positions: [
      { name: 'RECZNIE', feedback: 'ELA1.DI.1' },
      { name: '0' },
      { name: 'AUTOMAT', feedback: 'ELA1.DI.2' }
    ],
    ...overrides
  };
}

describe('SelectorDevice defaults (DeviceFormDefaults)', () => {
  it('defaultSelectorFields gives the classic 3-position Hand-Off-Auto layout', () => {
    expect(defaultSelectorFields().positions.map(p => p.name)).toEqual(['RECZNIE', '0', 'AUTOMAT']);
  });

  it('defaultFieldsForBehavior(SELECTOR) delegates to defaultSelectorFields', () => {
    expect(defaultFieldsForBehavior('SELECTOR')).toEqual(defaultSelectorFields());
  });
});

describe('SelectorDevice signals/commands (DeviceSignals)', () => {
  it('exposes exactly one signal, .POSITION', () => {
    expect(getDeviceSignals(makeSelector())).toEqual(['.POSITION']);
  });

  it('exposes zero commands - a real selector switch is turned by hand, never driven remotely', () => {
    expect(getDeviceCommands(makeSelector())).toEqual([]);
  });

  it('the full point name is <id>.POSITION', () => {
    expect(getDeviceSignalNames(makeSelector())).toEqual(['KOT_HOA1.POSITION']);
  });
});

describe('SelectorDevice business-rule validation (validateDeviceFields)', () => {
  it('a well-formed 3-position selector has zero errors', () => {
    expect(validateDeviceFields(makeSelector())).toEqual([]);
  });

  it('fewer than 2 positions is an error', () => {
    const device = makeSelector({ positions: [{ name: 'RECZNIE' }] });
    expect(validateDeviceFields(device).some(i => i.code === 'SELECTOR_TOO_FEW_POSITIONS')).toBe(true);
  });

  it('an empty position name is an error', () => {
    const device = makeSelector({ positions: [{ name: '' }, { name: 'AUTOMAT' }] });
    expect(validateDeviceFields(device).some(i => i.code === 'SELECTOR_EMPTY_POSITION_NAME')).toBe(true);
  });

  it('two positions with the same name is an error', () => {
    const device = makeSelector({ positions: [{ name: 'RECZNIE' }, { name: 'RECZNIE' }] });
    expect(validateDeviceFields(device).some(i => i.code === 'SELECTOR_DUPLICATE_POSITION_NAME')).toBe(true);
  });

  it('a position feedback pointing at a DO channel is rejected (must be DI)', () => {
    const device = makeSelector({ positions: [{ name: 'RECZNIE', feedback: 'ADA1.DO.1' }, { name: 'AUTOMAT' }] });
    expect(validateDeviceFields(device).some(i => i.code === 'DEVICE_FIELD_WRONG_CHANNEL_KIND')).toBe(true);
  });

  it('a SINGLE position with no feedback is valid - feedback is optional per position, as long as some OTHER position has one', () => {
    const device = makeSelector({ positions: [{ name: 'RECZNIE', feedback: 'ELA1.DI.1' }, { name: 'AUTOMAT' }] });
    expect(validateDeviceFields(device)).toEqual([]);
  });

  // fix/audit-findings commit 1: external audit finding - a SELECTOR
  // where NO position has feedback has no input at all and can never
  // report where it actually is, yet this passed validation before
  // this rule existed (this exact test used to assert `toEqual([])`
  // for this same fixture).
  describe('at least one position must have a feedback channel (SELECTOR_NO_FEEDBACK_AT_ALL)', () => {
    // 1. no position at all has feedback -> error
    it('two positions, neither with feedback, is an error', () => {
      const device = makeSelector({ positions: [{ name: 'RECZNIE' }, { name: 'AUTOMAT' }] });
      const issues = validateDeviceFields(device);
      expect(issues.some(i => i.code === 'SELECTOR_NO_FEEDBACK_AT_ALL')).toBe(true);
    });

    // 2. one of two positions has feedback -> valid
    it('two positions, one with feedback, is valid', () => {
      const device = makeSelector({ positions: [{ name: 'RECZNIE', feedback: 'ELA1.DI.1' }, { name: 'AUTOMAT' }] });
      expect(validateDeviceFields(device)).toEqual([]);
    });

    // 3. one of three positions has feedback -> valid
    it('three positions, one with feedback, is valid', () => {
      const device = makeSelector({ positions: [{ name: 'RECZNIE' }, { name: '0' }, { name: 'AUTOMAT', feedback: 'ELA1.DI.2' }] });
      expect(validateDeviceFields(device)).toEqual([]);
    });

    // 4. every position has feedback -> valid
    it('every position with feedback is valid', () => {
      expect(validateDeviceFields(makeSelector())).toEqual([]);
    });

    // 5. a selector with only one position (already invalid on its
    // own) and no feedback reports BOTH errors, not just one -
    // SELECTOR_NO_FEEDBACK_AT_ALL does not suppress or replace
    // SELECTOR_TOO_FEW_POSITIONS.
    it('one position with no feedback reports both SELECTOR_TOO_FEW_POSITIONS and SELECTOR_NO_FEEDBACK_AT_ALL', () => {
      const device = makeSelector({ positions: [{ name: 'RECZNIE' }] });
      const codes = validateDeviceFields(device).map(i => i.code);
      expect(codes).toContain('SELECTOR_TOO_FEW_POSITIONS');
      expect(codes).toContain('SELECTOR_NO_FEEDBACK_AT_ALL');
    });
  });
});

describe('SelectorDevice shape validation (validateDeviceRegistry against untrusted input)', () => {
  it('positions as a non-array is rejected, not a crash', () => {
    const device = { ...makeSelector(), positions: 'RECZNIE' };
    const registry = { locations: [KOT], cards: CARDS, devices: [device] };
    expect(() => validateDeviceRegistry(registry)).not.toThrow();
    expect(validateDeviceRegistry(registry).valid).toBe(false);
  });

  it('a position missing its name field is rejected, not a crash', () => {
    const device = { ...makeSelector(), positions: [{ feedback: 'ELA1.DI.1' }, { name: 'AUTOMAT' }] };
    const registry = { locations: [KOT], cards: CARDS, devices: [device] };
    expect(() => validateDeviceRegistry(registry)).not.toThrow();
    expect(validateDeviceRegistry(registry).valid).toBe(false);
  });

  it('SELECTOR is accepted as a known behavior (not DEVICE_UNKNOWN_BEHAVIOR)', () => {
    const registry: DeviceRegistry = { locations: [KOT], cards: CARDS, devices: [makeSelector()] };
    const result = validateDeviceRegistry(registry);
    expect(result.issues.some(i => i.code === 'DEVICE_UNKNOWN_BEHAVIOR')).toBe(false);
    expect(result.valid).toBe(true);
  });

  it('a SELECTOR position feedback colliding with another device channel is a collision error', () => {
    const selector = makeSelector({ positions: [{ name: 'RECZNIE', feedback: 'ELA1.DI.5' }, { name: 'AUTOMAT' }] });
    const otherDevice: SelectorDevice = makeSelector({ id: 'KOT_HOA2', positions: [{ name: 'RECZNIE', feedback: 'ELA1.DI.5' }, { name: 'AUTOMAT' }] });
    const registry: DeviceRegistry = { locations: [KOT], cards: CARDS, devices: [selector, otherDevice] };
    const result = validateDeviceRegistry(registry);
    expect(result.issues.some(i => i.code === 'CHANNEL_ADDRESS_COLLISION')).toBe(true);
  });
});

describe('SwitchedDevice interlock field (documentation only, feat/control-elements commit 3)', () => {
  it('a SWITCHED device with no interlock at all is valid - it is optional', () => {
    const device = {
      id: 'KOT_KMG1', designation: '-K1', name: 'Stycznik', behavior: 'SWITCHED' as const, kind: 'contactor', publishToHa: false,
      feedback: { mode: 'NONE' as const }, command: { outputCount: 1 as const, style: 'MAINTAINED' as const, doClose: 'ADA1.DO.1' },
      supervision: { confirmTimeoutMs: 1000, discrepancyAlarm: false }, safeState: { onStartup: 'NO_CHANGE' as const, onLinkLoss: 'NO_CHANGE' as const },
      switchCounter: false
    };
    const registry = { locations: [KOT], cards: [{ id: 'ADA1', model: 'ADA01', channelKind: 'DO' as const, channelCount: 16 }], devices: [device] };
    expect(validateDeviceRegistry(registry).valid).toBe(true);
  });

  it('an interlock with a non-string closeDescription is rejected, not a crash', () => {
    const device: any = {
      id: 'KOT_KMG1', designation: '-K1', name: 'Stycznik', behavior: 'SWITCHED', kind: 'contactor', publishToHa: false,
      feedback: { mode: 'NONE' }, command: { outputCount: 1, style: 'MAINTAINED', doClose: 'ADA1.DO.1' },
      supervision: { confirmTimeoutMs: 1000, discrepancyAlarm: false }, safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' },
      switchCounter: false, interlock: { closeDescription: 123 }
    };
    const registry = { locations: [KOT], cards: [{ id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 16 }], devices: [device] };
    expect(() => validateDeviceRegistry(registry)).not.toThrow();
    expect(validateDeviceRegistry(registry).valid).toBe(false);
  });

  it('a well-formed interlock description on both close and open is valid', () => {
    const device = {
      id: 'KOT_KMG1', designation: '-K1', name: 'Stycznik', behavior: 'SWITCHED' as const, kind: 'contactor', publishToHa: false,
      feedback: { mode: 'NONE' as const }, command: { outputCount: 1 as const, style: 'MAINTAINED' as const, doClose: 'ADA1.DO.1' },
      supervision: { confirmTimeoutMs: 1000, discrepancyAlarm: false }, safeState: { onStartup: 'NO_CHANGE' as const, onLinkLoss: 'NO_CHANGE' as const },
      switchCounter: false,
      interlock: { closeDescription: 'Zablokowane, gdy drzwi rozdzielnicy sa otwarte', openDescription: 'Zablokowane podczas biegu pompy rezerwowej' }
    };
    const registry = { locations: [KOT], cards: [{ id: 'ADA1', model: 'ADA01', channelKind: 'DO' as const, channelCount: 16 }], devices: [device] };
    expect(validateDeviceRegistry(registry).valid).toBe(true);
  });
});
