import { describe, it, expect } from 'vitest';
import { getDeviceCommands, getDeviceInhibitNames, getDeviceInhibits, getDeviceSignals } from '../project/DeviceSignals';
import type { MeasuredDevice, ModulatedDevice, SignalDevice, SwitchedDevice } from '../project/DeviceSchema';

function baseSwitchedDevice(overrides: Partial<SwitchedDevice> = {}): SwitchedDevice {
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
    switchCounter: false,
    ...overrides
  };
}

describe('getDeviceSignals', () => {
  it('32. SWITCHED with switchCounter true includes .COUNTER', () => {
    const device = baseSwitchedDevice({ switchCounter: true });
    expect(getDeviceSignals(device)).toContain('.COUNTER');
  });

  it('33. SWITCHED with switchCounter false does not include .COUNTER', () => {
    const device = baseSwitchedDevice({ switchCounter: false });
    expect(getDeviceSignals(device)).not.toContain('.COUNTER');
  });

  it('34. SWITCHED without diFault does not include .FAULT', () => {
    const device = baseSwitchedDevice();
    expect(getDeviceSignals(device)).not.toContain('.FAULT');
  });

  it('35. SWITCHED with diFault includes .FAULT', () => {
    const device = baseSwitchedDevice({ extraInputs: { diFault: 'ELA1.DI.9' } });
    expect(getDeviceSignals(device)).toContain('.FAULT');
  });

  it('37. MEASURED returns .VALUE and .QUALITY', () => {
    const device: MeasuredDevice = {
      id: 'KOT_TT1',
      designation: '-TT1',
      name: 'Czujnik temperatury',
      behavior: 'MEASURED',
      kind: 'temperature_sensor',
      publishToHa: false,
      input: 'AIA1.AI.1',
      unit: '°C',
      rangeMin: 0,
      rangeMax: 100,
      format: '0.0',
      deadband: 0.5
    };
    const signals = getDeviceSignals(device);
    expect(signals).toContain('.VALUE');
    expect(signals).toContain('.QUALITY');
  });

  it('AC. SWITCHED read signals never include any .INHIBIT_ signal', () => {
    const device = baseSwitchedDevice({ switchCounter: true, extraInputs: { diFault: 'ELA1.DI.9' } });
    const signals = getDeviceSignals(device);
    expect(signals.some(s => s.startsWith('.INHIBIT_'))).toBe(false);
  });
});

describe('getDeviceCommands', () => {
  it('36. SIGNAL returns an empty command list', () => {
    const device: SignalDevice = {
      id: 'KOT_SL1',
      designation: '-SL1',
      name: 'Czujnik poziomu',
      behavior: 'SIGNAL',
      kind: 'level_switch',
      publishToHa: false,
      feedback: { di: 'ELA1.DI.7', invert: false },
      alarmState: 'HIGH',
      debounceMs: 50
    };
    expect(getDeviceCommands(device)).toEqual([]);
  });

  it('38. MODULATED returns the .SET command', () => {
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
      startupValue: 0,
      safeValue: 0
    };
    expect(getDeviceCommands(device)).toContain('.SET');
  });
});

describe('Inhibit signals (getDeviceInhibits / getDeviceInhibitNames)', () => {
  it('Y. SWITCHED commands include .INHIBIT_CLOSE and .INHIBIT_OPEN', () => {
    const device = baseSwitchedDevice();
    const commands = getDeviceCommands(device);
    expect(commands).toContain('.INHIBIT_CLOSE');
    expect(commands).toContain('.INHIBIT_OPEN');
  });

  it('Z. MODULATED commands include .INHIBIT_SET', () => {
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
      startupValue: 0,
      safeValue: 0
    };
    expect(getDeviceCommands(device)).toContain('.INHIBIT_SET');
  });

  it('AA. SIGNAL returns an empty inhibit list', () => {
    const device: SignalDevice = {
      id: 'KOT_SL1',
      designation: '-SL1',
      name: 'Czujnik poziomu',
      behavior: 'SIGNAL',
      kind: 'level_switch',
      publishToHa: false,
      feedback: { di: 'ELA1.DI.7', invert: false },
      alarmState: 'HIGH',
      debounceMs: 50
    };
    expect(getDeviceInhibits(device)).toEqual([]);
  });

  it('AB. MEASURED returns an empty inhibit list', () => {
    const device: MeasuredDevice = {
      id: 'KOT_TT1',
      designation: '-TT1',
      name: 'Czujnik temperatury',
      behavior: 'MEASURED',
      kind: 'temperature_sensor',
      publishToHa: false,
      input: 'AIA1.AI.1',
      unit: '°C',
      rangeMin: 0,
      rangeMax: 100,
      format: '0.0',
      deadband: 0.5
    };
    expect(getDeviceInhibits(device)).toEqual([]);
  });

  it('AD. getDeviceInhibitNames returns full point names, e.g. KOT_KMG1.INHIBIT_CLOSE', () => {
    const device = baseSwitchedDevice();
    expect(getDeviceInhibitNames(device)).toContain('KOT_KMG1.INHIBIT_CLOSE');
  });
});
