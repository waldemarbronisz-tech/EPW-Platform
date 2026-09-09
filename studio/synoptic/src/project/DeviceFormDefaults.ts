// Default values for a NEWLY created device's behavior-specific fields,
// keyed only by DeviceSchema.ts's own field names - just enough shape to
// satisfy validateDeviceShape (DeviceValidation.ts) so a freshly added
// device is a well-formed Device object from the moment it exists, even
// before its own channel addresses are filled in. This is NOT a
// validation rule (it never decides what is valid - a doClose of '' is
// still a string, so the shape check accepts it; validateDeviceFields
// will then correctly flag it as an invalid channel address, which is
// exactly the point: a fresh device shows up in the list as invalid
// until its own required fields are actually filled in).

import type {
  Device, DeviceBehavior, DeviceCommon,
  SwitchedDevice, SignalDevice, MeasuredDevice, ModulatedDevice, SelectorDevice
} from './DeviceSchema';

export type SwitchedOwnFields = Omit<SwitchedDevice, keyof DeviceCommon | 'behavior'>;
export type SignalOwnFields = Omit<SignalDevice, keyof DeviceCommon | 'behavior'>;
export type MeasuredOwnFields = Omit<MeasuredDevice, keyof DeviceCommon | 'behavior'>;
export type ModulatedOwnFields = Omit<ModulatedDevice, keyof DeviceCommon | 'behavior'>;
export type SelectorOwnFields = Omit<SelectorDevice, keyof DeviceCommon | 'behavior'>;

export type DeviceOwnFields = SwitchedOwnFields | SignalOwnFields | MeasuredOwnFields | ModulatedOwnFields | SelectorOwnFields;

export function defaultSwitchedFields(): SwitchedOwnFields {
  return {
    feedback: { mode: 'NONE' },
    command: { outputCount: 1, style: 'MAINTAINED', doClose: '' },
    supervision: { confirmTimeoutMs: 1000, discrepancyAlarm: false },
    safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' },
    switchCounter: false
  };
}

export function defaultSignalFields(): SignalOwnFields {
  return { feedback: { di: '', invert: false }, alarmState: 'HIGH', debounceMs: 50 };
}

export function defaultMeasuredFields(): MeasuredOwnFields {
  return { input: '', unit: '', rangeMin: 0, rangeMax: 100, format: '0.0', deadband: 0 };
}

export function defaultModulatedFields(): ModulatedOwnFields {
  return { setpointOutput: '', unit: '', rangeMin: 0, rangeMax: 100, startupValue: 0, safeValue: 0 };
}

/** Defaults to the classic three-position Hand-Off-Auto layout - the single most common real selector switch, and a recognizable starting point to edit from (rename/add/remove positions freely afterward). */
export function defaultSelectorFields(): SelectorOwnFields {
  return { positions: [{ name: 'RECZNIE' }, { name: '0' }, { name: 'AUTOMAT' }] };
}

export function defaultFieldsForBehavior(behavior: DeviceBehavior): DeviceOwnFields {
  switch (behavior) {
    case 'SWITCHED': return defaultSwitchedFields();
    case 'SIGNAL': return defaultSignalFields();
    case 'MEASURED': return defaultMeasuredFields();
    case 'MODULATED': return defaultModulatedFields();
    case 'SELECTOR': return defaultSelectorFields();
  }
}

/** Assembles a full Device from its common fields (behavior included) and that behavior's own fields (defaults or user-edited) - a plain merge, not a validation. */
export function assembleDevice(common: DeviceCommon, ownFields: DeviceOwnFields): Device {
  return { ...common, ...ownFields } as Device;
}
