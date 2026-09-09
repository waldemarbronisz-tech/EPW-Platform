import { describe, it, expect } from 'vitest';
import {
  parseChannelAddress,
  validateDeviceId,
  validateChannelAddress,
  validateDeviceFields,
  validateDeviceRegistry
} from '../project/DeviceValidation';
import type {
  CardEntry,
  DeviceRegistry,
  LocationEntry,
  MeasuredDevice,
  ModulatedDevice,
  SignalDevice,
  SwitchedDevice
} from '../project/DeviceSchema';

const KOT: LocationEntry = { code: 'KOT', description: 'Kotlownia' };
const MAG: LocationEntry = { code: 'MAG', description: 'Magazyn' };

function baseSwitchedDevice(): SwitchedDevice {
  // A valid bistable contactor: DUAL feedback, 2 pulsed outputs (500ms).
  return {
    id: 'KOT_KMG1',
    designation: '-K1',
    name: 'Stycznik grzalki',
    behavior: 'SWITCHED',
    kind: 'contactor',
    publishToHa: false,
    feedback: { mode: 'DUAL', diClosed: 'ELA1.DI.1', diOpen: 'ELA1.DI.2' },
    command: { outputCount: 2, style: 'PULSE', doClose: 'ADA1.DO.1', doOpen: 'ADA1.DO.2', pulseMs: 500 },
    supervision: { confirmTimeoutMs: 2000, discrepancyAlarm: true },
    safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' },
    switchCounter: false
  };
}

function makeSignalDevice(id: string, designation: string, di: string): SignalDevice {
  return {
    id,
    designation,
    name: 'Czujnik poziomu',
    behavior: 'SIGNAL',
    kind: 'level_switch',
    publishToHa: false,
    feedback: { di, invert: false },
    alarmState: 'HIGH',
    debounceMs: 50
  };
}

function makeSwitchedDevice(id: string, designation: string, diClosed: string, diOpen: string, doClose: string, doOpen: string): SwitchedDevice {
  return {
    id,
    designation,
    name: 'Stycznik',
    behavior: 'SWITCHED',
    kind: 'contactor',
    publishToHa: false,
    feedback: { mode: 'DUAL', diClosed, diOpen },
    command: { outputCount: 2, style: 'PULSE', doClose, doOpen, pulseMs: 500 },
    supervision: { confirmTimeoutMs: 2000, discrepancyAlarm: true },
    safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' },
    switchCounter: false
  };
}

function makeMeasuredDevice(id: string, designation: string, input: string): MeasuredDevice {
  return {
    id,
    designation,
    name: 'Czujnik temperatury',
    behavior: 'MEASURED',
    kind: 'temperature_sensor',
    publishToHa: false,
    input,
    unit: '°C',
    rangeMin: 0,
    rangeMax: 100,
    format: '0.0',
    deadband: 0.5
  };
}

describe('Device id validation (validateDeviceId)', () => {
  it('1. accepts a valid id with a registered location', () => {
    expect(validateDeviceId('KOT_KMG1', [KOT])).toEqual([]);
  });

  it('2. rejects lowercase characters', () => {
    const issues = validateDeviceId('kot_kmg1', [KOT]);
    expect(issues.some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('3. rejects a hyphen', () => {
    const issues = validateDeviceId('KOT-KMG1', [KOT]);
    expect(issues.some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('4. rejects two underscores', () => {
    const issues = validateDeviceId('KOT_KMG_1', [KOT]);
    expect(issues.some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('5. rejects a missing underscore', () => {
    const issues = validateDeviceId('KMG1', [KOT]);
    expect(issues.some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('6. rejects an unregistered location', () => {
    const issues = validateDeviceId('XXX_KMG1', [KOT]);
    expect(issues.some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('7. rejects an empty part after the underscore', () => {
    const issues = validateDeviceId('KOT_', [KOT]);
    expect(issues.some(i => i.severity === 'ERROR')).toBe(true);
  });
});

describe('Channel address validation (validateChannelAddress / parseChannelAddress)', () => {
  const cards: CardEntry[] = [{ id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 64 }];

  it('8. accepts a valid address within range', () => {
    expect(validateChannelAddress('ELA1.DI.12', cards)).toEqual([]);
  });

  it('9. rejects a nonexistent card', () => {
    const issues = validateChannelAddress('ELA9.DI.12', cards);
    expect(issues.some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('10. rejects a channel kind that does not match the card', () => {
    const issues = validateChannelAddress('ELA1.DO.12', cards);
    expect(issues.some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('11. rejects a channel number out of range', () => {
    const issues = validateChannelAddress('ELA1.DI.99', cards);
    expect(issues.some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('12. rejects channel zero (numbering starts at 1)', () => {
    const issues = validateChannelAddress('ELA1.DI.0', cards);
    expect(issues.some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('13. rejects an incomplete address', () => {
    const issues = validateChannelAddress('ELA1.DI', cards);
    expect(issues.some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('parseChannelAddress parses a well-formed address', () => {
    expect(parseChannelAddress('ELA1.DI.12')).toEqual({ card: 'ELA1', kind: 'DI', channel: 12 });
  });

  it('parseChannelAddress returns null for an incomplete address', () => {
    expect(parseChannelAddress('ELA1.DI')).toBeNull();
  });
});

describe('Mode-dependent field validation (validateDeviceFields)', () => {
  it('14. SWITCHED DUAL without diOpen is an error', () => {
    const device = baseSwitchedDevice();
    device.feedback = { mode: 'DUAL', diClosed: 'ELA1.DI.1' };
    expect(validateDeviceFields(device).some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('15. SWITCHED SINGLE with diOpen is an error', () => {
    const device = baseSwitchedDevice();
    device.feedback = { mode: 'SINGLE', diClosed: 'ELA1.DI.1', diOpen: 'ELA1.DI.2' };
    expect(validateDeviceFields(device).some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('16. SWITCHED NONE with diClosed is an error', () => {
    const device = baseSwitchedDevice();
    device.feedback = { mode: 'NONE', diClosed: 'ELA1.DI.1' };
    expect(validateDeviceFields(device).some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('17. SWITCHED outputCount 2 without doOpen is an error', () => {
    const device = baseSwitchedDevice();
    device.command = { outputCount: 2, style: 'PULSE', doClose: 'ADA1.DO.1', pulseMs: 500 };
    expect(validateDeviceFields(device).some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('18. SWITCHED outputCount 1 with doOpen is an error', () => {
    const device = baseSwitchedDevice();
    device.command = { outputCount: 1, style: 'PULSE', doClose: 'ADA1.DO.1', doOpen: 'ADA1.DO.2', pulseMs: 500 };
    expect(validateDeviceFields(device).some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('19. SWITCHED PULSE without pulseMs is an error', () => {
    const device = baseSwitchedDevice();
    device.command = { outputCount: 2, style: 'PULSE', doClose: 'ADA1.DO.1', doOpen: 'ADA1.DO.2' };
    expect(validateDeviceFields(device).some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('20. SWITCHED MAINTAINED with pulseMs is an error', () => {
    const device = baseSwitchedDevice();
    device.command = { outputCount: 2, style: 'MAINTAINED', doClose: 'ADA1.DO.1', doOpen: 'ADA1.DO.2', pulseMs: 500 };
    expect(validateDeviceFields(device).some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('21. SWITCHED with doClose pointing at a DI channel is an error', () => {
    const device = baseSwitchedDevice();
    device.command = { ...device.command, doClose: 'ELA1.DI.5' };
    expect(validateDeviceFields(device).some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('22. MEASURED with input pointing at a DO channel is an error', () => {
    const device = makeMeasuredDevice('KOT_TT1', '-TT1', 'ADA1.DO.1');
    expect(validateDeviceFields(device).some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('23. MEASURED with rangeMin greater than rangeMax is an error', () => {
    const device = makeMeasuredDevice('KOT_TT1', '-TT1', 'AIA1.AI.1');
    device.rangeMin = 100;
    device.rangeMax = 0;
    expect(validateDeviceFields(device).some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('24. MODULATED with startupValue out of range is an error', () => {
    const device: ModulatedDevice = {
      id: 'KOT_TV1',
      designation: '-TV1',
      name: 'Zawor modulowany',
      behavior: 'MODULATED',
      kind: 'modulating_valve',
      publishToHa: false,
      setpointOutput: 'AOA1.AO.1',
      unit: '%',
      rangeMin: 0,
      rangeMax: 100,
      startupValue: 150,
      safeValue: 0
    };
    expect(validateDeviceFields(device).some(i => i.severity === 'ERROR')).toBe(true);
  });

  it('25. a valid bistable contactor (DUAL, 2 outputs, PULSE 500ms) has zero errors', () => {
    expect(validateDeviceFields(baseSwitchedDevice())).toEqual([]);
  });
});

describe('Device registry validation (validateDeviceRegistry)', () => {
  const REG_LOCATIONS: LocationEntry[] = [KOT, MAG];
  const REG_CARDS: CardEntry[] = [
    { id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 64 },
    { id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 60 },
    { id: 'AIA1', model: 'AIA01', channelKind: 'AI', channelCount: 16 }
  ];

  it('26. two devices with the same id is an error', () => {
    const registry: DeviceRegistry = {
      locations: REG_LOCATIONS,
      cards: REG_CARDS,
      devices: [
        makeSignalDevice('KOT_Q1', '-Q1', 'ELA1.DI.1'),
        makeSignalDevice('KOT_Q1', '-Q2', 'ELA1.DI.2')
      ]
    };
    const result = validateDeviceRegistry(registry);
    expect(result.valid).toBe(false);
    expect(result.issues.some(i => i.code === 'DEVICE_DUPLICATE_ID')).toBe(true);
  });

  it('27. the same designation in two different locations is valid', () => {
    const registry: DeviceRegistry = {
      locations: REG_LOCATIONS,
      cards: REG_CARDS,
      devices: [
        makeSignalDevice('KOT_Q1', '-Q1', 'ELA1.DI.1'),
        makeSignalDevice('MAG_Q1', '-Q1', 'ELA1.DI.2')
      ]
    };
    const result = validateDeviceRegistry(registry);
    expect(result.valid).toBe(true);
    expect(result.issues).toEqual([]);
  });

  it('28. the same designation twice within one location is an error', () => {
    const registry: DeviceRegistry = {
      locations: REG_LOCATIONS,
      cards: REG_CARDS,
      devices: [
        makeSignalDevice('KOT_Q1', '-Q1', 'ELA1.DI.1'),
        makeSignalDevice('KOT_Q2', '-Q1', 'ELA1.DI.2')
      ]
    };
    const result = validateDeviceRegistry(registry);
    expect(result.valid).toBe(false);
    expect(result.issues.some(i => i.code === 'DEVICE_DUPLICATE_DESIGNATION_IN_LOCATION')).toBe(true);
  });

  it('29. two devices using the same channel address is a collision error', () => {
    const registry: DeviceRegistry = {
      locations: REG_LOCATIONS,
      cards: REG_CARDS,
      devices: [
        makeSignalDevice('KOT_Q1', '-Q1', 'ELA1.DI.12'),
        makeSignalDevice('KOT_Q2', '-Q2', 'ELA1.DI.12')
      ]
    };
    const result = validateDeviceRegistry(registry);
    expect(result.valid).toBe(false);
    expect(result.issues.some(i => i.code === 'CHANNEL_ADDRESS_COLLISION')).toBe(true);
  });

  it('30. a collision between one device diClosed and another device diFault is an error', () => {
    const deviceA = makeSwitchedDevice('KOT_KMG1', '-K1', 'ELA1.DI.1', 'ELA1.DI.2', 'ADA1.DO.1', 'ADA1.DO.2');
    const deviceB = makeSwitchedDevice('KOT_KMG2', '-K2', 'ELA1.DI.3', 'ELA1.DI.4', 'ADA1.DO.3', 'ADA1.DO.4');
    deviceB.extraInputs = { diFault: 'ELA1.DI.1' }; // collides with deviceA's diClosed
    const registry: DeviceRegistry = { locations: REG_LOCATIONS, cards: REG_CARDS, devices: [deviceA, deviceB] };
    const result = validateDeviceRegistry(registry);
    expect(result.valid).toBe(false);
    expect(result.issues.some(i => i.code === 'CHANNEL_ADDRESS_COLLISION')).toBe(true);
  });

  it('31. a valid registry with 3 devices of different behaviors has zero errors', () => {
    const registry: DeviceRegistry = {
      locations: REG_LOCATIONS,
      cards: REG_CARDS,
      devices: [
        makeSwitchedDevice('KOT_KMG1', '-K1', 'ELA1.DI.1', 'ELA1.DI.2', 'ADA1.DO.1', 'ADA1.DO.2'),
        makeSignalDevice('KOT_SL1', '-SL1', 'ELA1.DI.3'),
        makeMeasuredDevice('KOT_TT1', '-TT1', 'AIA1.AI.1')
      ]
    };
    const result = validateDeviceRegistry(registry);
    expect(result.valid).toBe(true);
    expect(result.issues).toEqual([]);
  });
});

describe('Shape validation (validateDeviceRegistry against untrusted input)', () => {
  it('A. registry === null is an error, not a crash', () => {
    expect(() => validateDeviceRegistry(null)).not.toThrow();
    expect(validateDeviceRegistry(null).valid).toBe(false);
  });

  it('B. registry.devices === null is an error, not a crash', () => {
    const registry = { locations: [KOT], cards: [], devices: null };
    expect(() => validateDeviceRegistry(registry)).not.toThrow();
    const result = validateDeviceRegistry(registry);
    expect(result.valid).toBe(false);
    expect(result.issues.some(i => i.code === 'REGISTRY_INVALID_DEVICES')).toBe(true);
  });

  it('C. registry.devices as an object instead of an array is an error, not a crash', () => {
    const registry = { locations: [KOT], cards: [], devices: { foo: 'bar' } };
    expect(() => validateDeviceRegistry(registry)).not.toThrow();
    const result = validateDeviceRegistry(registry);
    expect(result.valid).toBe(false);
    expect(result.issues.some(i => i.code === 'REGISTRY_INVALID_DEVICES')).toBe(true);
  });

  it('D. registry.locations === undefined is an error, not a crash', () => {
    const registry = { cards: [], devices: [] };
    expect(() => validateDeviceRegistry(registry)).not.toThrow();
    const result = validateDeviceRegistry(registry);
    expect(result.valid).toBe(false);
    expect(result.issues.some(i => i.code === 'REGISTRY_INVALID_LOCATIONS')).toBe(true);
  });

  it('E. a null device inside the devices array is an error, not a crash', () => {
    const registry = { locations: [KOT], cards: [], devices: [null] };
    expect(() => validateDeviceRegistry(registry)).not.toThrow();
    const result = validateDeviceRegistry(registry);
    expect(result.valid).toBe(false);
    expect(result.issues.some(i => i.code === 'DEVICE_INVALID_SHAPE')).toBe(true);
  });

  it('F. behavior "ROBOT" is rejected with DEVICE_UNKNOWN_BEHAVIOR', () => {
    const registry = {
      locations: [KOT],
      cards: [],
      devices: [{ id: 'KOT_R1', designation: '-R1', name: 'Robot', kind: 'robot', publishToHa: false, behavior: 'ROBOT' }]
    };
    const result = validateDeviceRegistry(registry);
    expect(result.valid).toBe(false);
    expect(result.issues.some(i => i.code === 'DEVICE_UNKNOWN_BEHAVIOR')).toBe(true);
  });

  it('G. SWITCHED without a feedback section is an error, not a crash', () => {
    const device = baseSwitchedDevice() as any;
    delete device.feedback;
    const registry = { locations: [KOT], cards: [], devices: [device] };
    expect(() => validateDeviceRegistry(registry)).not.toThrow();
    expect(validateDeviceRegistry(registry).valid).toBe(false);
  });

  it('H. SWITCHED without a command section is an error, not a crash', () => {
    const device = baseSwitchedDevice() as any;
    delete device.command;
    const registry = { locations: [KOT], cards: [], devices: [device] };
    expect(() => validateDeviceRegistry(registry)).not.toThrow();
    expect(validateDeviceRegistry(registry).valid).toBe(false);
  });

  it('I. feedback.mode "TRIPLE" is an error', () => {
    const device = baseSwitchedDevice() as any;
    device.feedback = { mode: 'TRIPLE', diClosed: 'ELA1.DI.1' };
    const registry = { locations: [KOT], cards: [], devices: [device] };
    expect(validateDeviceRegistry(registry).valid).toBe(false);
  });

  it('J. command.outputCount 3 is an error', () => {
    const device = baseSwitchedDevice() as any;
    device.command = { ...device.command, outputCount: 3 };
    const registry = { locations: [KOT], cards: [], devices: [device] };
    expect(validateDeviceRegistry(registry).valid).toBe(false);
  });

  it('K. MEASURED rangeMin === NaN is an error (typeof NaN is "number")', () => {
    const device = makeMeasuredDevice('KOT_TT1', '-TT1', 'AIA1.AI.1') as any;
    device.rangeMin = NaN;
    const registry = { locations: [KOT], cards: [], devices: [device] };
    expect(validateDeviceRegistry(registry).valid).toBe(false);
  });

  it('L. publishToHa as the string "yes" is an error', () => {
    const device = makeSignalDevice('KOT_SL1', '-SL1', 'ELA1.DI.1') as any;
    device.publishToHa = 'yes';
    const registry = { locations: [KOT], cards: [], devices: [device] };
    expect(validateDeviceRegistry(registry).valid).toBe(false);
  });
});

describe('Adversarial gaps (H1-H4 and B5 consistency rules)', () => {
  it('M. empty designation is rejected with DEVICE_EMPTY_DESIGNATION', () => {
    const device = baseSwitchedDevice();
    device.designation = '';
    expect(validateDeviceFields(device).some(i => i.code === 'DEVICE_EMPTY_DESIGNATION')).toBe(true);
  });

  it('N. whitespace-only designation is rejected', () => {
    const device = baseSwitchedDevice();
    device.designation = '   ';
    expect(validateDeviceFields(device).some(i => i.code === 'DEVICE_EMPTY_DESIGNATION')).toBe(true);
  });

  it('O. empty name is rejected with DEVICE_EMPTY_NAME', () => {
    const device = baseSwitchedDevice();
    device.name = '';
    expect(validateDeviceFields(device).some(i => i.code === 'DEVICE_EMPTY_NAME')).toBe(true);
  });

  it('P. empty kind is rejected with DEVICE_EMPTY_KIND', () => {
    const device = baseSwitchedDevice();
    device.kind = '';
    expect(validateDeviceFields(device).some(i => i.code === 'DEVICE_EMPTY_KIND')).toBe(true);
  });

  it('Q. confirmTimeoutMs -5000 is rejected', () => {
    const device = baseSwitchedDevice();
    device.supervision = { confirmTimeoutMs: -5000, discrepancyAlarm: true };
    expect(validateDeviceFields(device).some(i => i.code === 'SWITCHED_INVALID_CONFIRM_TIMEOUT')).toBe(true);
  });

  it('R. confirmTimeoutMs 50 is rejected (below the 100ms floor)', () => {
    const device = baseSwitchedDevice();
    device.supervision = { confirmTimeoutMs: 50, discrepancyAlarm: true };
    expect(validateDeviceFields(device).some(i => i.code === 'SWITCHED_INVALID_CONFIRM_TIMEOUT')).toBe(true);
  });

  it('S. confirmTimeoutMs 100 is valid (the floor is inclusive)', () => {
    const device = baseSwitchedDevice();
    device.supervision = { confirmTimeoutMs: 100, discrepancyAlarm: true };
    expect(validateDeviceFields(device)).toEqual([]);
  });

  it('T. two devices on ELA1.DI.12 and ELA1.DI.012 collide exactly once (leading zero must not evade detection)', () => {
    const registry: DeviceRegistry = {
      locations: [KOT],
      cards: [{ id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 64 }],
      devices: [
        makeSignalDevice('KOT_Q1', '-Q1', 'ELA1.DI.12'),
        makeSignalDevice('KOT_Q2', '-Q2', 'ELA1.DI.012')
      ]
    };
    const result = validateDeviceRegistry(registry);
    const collisions = result.issues.filter(i => i.code === 'CHANNEL_ADDRESS_COLLISION');
    expect(collisions.length).toBe(1);
  });

  it('U. two devices on ELA1.DI.12 and ELA1.DI.13 produce zero collision errors', () => {
    const registry: DeviceRegistry = {
      locations: [KOT],
      cards: [{ id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 64 }],
      devices: [
        makeSignalDevice('KOT_Q1', '-Q1', 'ELA1.DI.12'),
        makeSignalDevice('KOT_Q2', '-Q2', 'ELA1.DI.13')
      ]
    };
    const result = validateDeviceRegistry(registry);
    expect(result.issues.some(i => i.code === 'CHANNEL_ADDRESS_COLLISION')).toBe(false);
  });

  it('V. SIGNAL debounceMs -1 is rejected', () => {
    const device = makeSignalDevice('KOT_SL1', '-SL1', 'ELA1.DI.1');
    device.debounceMs = -1;
    expect(validateDeviceFields(device).some(i => i.code === 'SIGNAL_INVALID_DEBOUNCE')).toBe(true);
  });

  it('W. MEASURED with an empty unit is rejected', () => {
    const device = makeMeasuredDevice('KOT_TT1', '-TT1', 'AIA1.AI.1');
    device.unit = '';
    expect(validateDeviceFields(device).some(i => i.code === 'MEASURED_EMPTY_UNIT')).toBe(true);
  });

  it('X. a fully valid registry after all hardening changes has zero errors', () => {
    const registry: DeviceRegistry = {
      locations: [KOT, MAG],
      cards: [
        { id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 64 },
        { id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 60 },
        { id: 'AIA1', model: 'AIA01', channelKind: 'AI', channelCount: 16 }
      ],
      devices: [
        makeSwitchedDevice('KOT_KMG1', '-K1', 'ELA1.DI.1', 'ELA1.DI.2', 'ADA1.DO.1', 'ADA1.DO.2'),
        makeSignalDevice('KOT_SL1', '-SL1', 'ELA1.DI.3'),
        makeMeasuredDevice('KOT_TT1', '-TT1', 'AIA1.AI.1')
      ]
    };
    const result = validateDeviceRegistry(registry);
    expect(result.valid).toBe(true);
    expect(result.issues).toEqual([]);
  });
});

describe('Part A: discrepancyAlarm shape + channel address whitespace trimming', () => {
  it('A-a. discrepancyAlarm as the string "yes" is rejected', () => {
    const device = baseSwitchedDevice() as any;
    device.supervision = { confirmTimeoutMs: 2000, discrepancyAlarm: 'yes' };
    const registry = { locations: [KOT], cards: [], devices: [device] };
    expect(validateDeviceRegistry(registry).valid).toBe(false);
  });

  it('A-b. discrepancyAlarm as a boolean is valid', () => {
    const device = baseSwitchedDevice();
    device.supervision = { confirmTimeoutMs: 2000, discrepancyAlarm: true };
    const registry: DeviceRegistry = {
      locations: [KOT],
      cards: [
        { id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 64 },
        { id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 60 }
      ],
      devices: [device]
    };
    expect(validateDeviceRegistry(registry).valid).toBe(true);
  });

  it('A-c. a channel address with surrounding whitespace parses and validates cleanly', () => {
    const cards: CardEntry[] = [{ id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 64 }];
    expect(parseChannelAddress(' ELA1.DI.12 ')).toEqual({ card: 'ELA1', kind: 'DI', channel: 12 });
    expect(validateChannelAddress(' ELA1.DI.12 ', cards)).toEqual([]);
  });

  it("A-d. two devices on ' ELA1.DI.12' and 'ELA1.DI.12' collide exactly once (whitespace must not evade detection)", () => {
    const registry: DeviceRegistry = {
      locations: [KOT],
      cards: [{ id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 64 }],
      devices: [
        makeSignalDevice('KOT_Q1', '-Q1', ' ELA1.DI.12'),
        makeSignalDevice('KOT_Q2', '-Q2', 'ELA1.DI.12')
      ]
    };
    const result = validateDeviceRegistry(registry);
    const collisions = result.issues.filter(i => i.code === 'CHANNEL_ADDRESS_COLLISION');
    expect(collisions.length).toBe(1);
  });
});
