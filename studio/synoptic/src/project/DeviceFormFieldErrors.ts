// feat/device-list-ui commit 3 - maps validateDeviceRegistry's own
// ValidationIssue[] (DeviceValidation.ts) onto the form field each one is
// actually about, so the form can show a red message right under the
// field it applies to. This file decides NOTHING about what is valid -
// it only reads codes and messages validateDeviceRegistry already
// produced and files them under a field key; every rule stays exactly
// where GRANICE requires it to stay.
//
// Two complications validateDeviceRegistry's own message shape forces
// on this file, both handled below rather than by touching that file:
//
// 1. A handful of codes carry no `deviceId` at all (validateChannelAddress's
//    own CHANNEL_ADDRESS_* issues, and the cross-device CHANNEL_ADDRESS_
//    COLLISION) - getDeviceOwnIssues works around the missing deviceId by
//    running validateDeviceRegistry once against a REGISTRY OF ONE (just
//    this candidate device), where any device-shaped issue that comes
//    back is unambiguously about it, merged with a full-registry run
//    filtered by deviceId for the genuinely cross-device rules (duplicate
//    id/designation, channel collisions).
// 2. Those same fieldless codes don't name which of the device's OWN
//    fields the bad address came from either - mapDeviceIssuesToFields
//    recovers it by matching the address text embedded in the message
//    against the device's own current field values (DeviceFieldMap.ts),
//    not by re-deriving any validity rule of its own.

import type { CardEntry, Device, LocationEntry } from './DeviceSchema';
import { validateDeviceRegistry, type ValidationIssue } from './DeviceValidation';
import { getDeviceChannelAddressFields } from './DeviceFieldMap';

/** Every issue that belongs to `candidate` alone - see this file's header for why two runs are needed. */
export function getDeviceOwnIssues(candidate: Device, otherDevices: Device[], locations: LocationEntry[], cards: CardEntry[]): ValidationIssue[] {
  const isolated = validateDeviceRegistry({ locations, cards, devices: [candidate] }).issues
    .filter(i => !i.code.startsWith('LOCATION_') && !i.code.startsWith('CARD_') && !i.code.startsWith('REGISTRY_'));
  const fromFull = validateDeviceRegistry({ locations, cards, devices: [...otherDevices, candidate] }).issues
    .filter(i => i.deviceId === candidate.id);

  const seen = new Set<string>();
  const result: ValidationIssue[] = [];
  for (const issue of [...isolated, ...fromFull]) {
    const key = `${issue.code}|${issue.message}`;
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(issue);
  }
  return result;
}

// Codes whose field is fixed and unconditional - the large majority.
const FIXED_FIELD_BY_CODE: Record<string, string | string[]> = {
  DEVICE_ID_EMPTY: 'id',
  DEVICE_ID_INVALID_CHARS: 'id',
  DEVICE_ID_UNDERSCORE_COUNT: 'id',
  DEVICE_ID_UNKNOWN_LOCATION: 'id',
  DEVICE_ID_EMPTY_SUFFIX: 'id',
  DEVICE_DUPLICATE_ID: 'id',
  DEVICE_EMPTY_DESIGNATION: 'designation',
  DEVICE_DUPLICATE_DESIGNATION_IN_LOCATION: 'designation',
  DEVICE_EMPTY_NAME: 'name',
  DEVICE_EMPTY_KIND: 'kind',

  SWITCHED_DUAL_MISSING_DICLOSED: 'feedback.diClosed',
  SWITCHED_SINGLE_MISSING_DICLOSED: 'feedback.diClosed',
  SWITCHED_NONE_FORBIDDEN_DICLOSED: 'feedback.diClosed',
  SWITCHED_DUAL_MISSING_DIOPEN: 'feedback.diOpen',
  SWITCHED_SINGLE_FORBIDDEN_DIOPEN: 'feedback.diOpen',
  SWITCHED_NONE_FORBIDDEN_DIOPEN: 'feedback.diOpen',
  SWITCHED_DUAL_FORBIDDEN_INVERT: 'feedback.invert',
  SWITCHED_OUTPUT2_MISSING_DOOPEN: 'command.doOpen',
  SWITCHED_OUTPUT1_FORBIDDEN_DOOPEN: 'command.doOpen',
  SWITCHED_PULSE_MISSING_PULSEMS: 'command.pulseMs',
  SWITCHED_MAINTAINED_FORBIDDEN_PULSEMS: 'command.pulseMs',
  SWITCHED_INVALID_CONFIRM_TIMEOUT: 'supervision.confirmTimeoutMs',

  SIGNAL_INVALID_DEBOUNCE: 'debounceMs',

  MEASURED_INVALID_RANGE: ['rangeMin', 'rangeMax'],
  MEASURED_INVALID_DEADBAND: 'deadband',
  MEASURED_EMPTY_UNIT: 'unit',

  MODULATED_INVALID_RANGE: ['rangeMin', 'rangeMax'],
  MODULATED_STARTUP_OUT_OF_RANGE: 'startupValue',
  MODULATED_SAFE_OUT_OF_RANGE: 'safeValue',
  MODULATED_EMPTY_UNIT: 'unit',

  SELECTOR_TOO_FEW_POSITIONS: 'positions',
  SELECTOR_EMPTY_POSITION_NAME: 'positions',
  SELECTOR_DUPLICATE_POSITION_NAME: 'positions',
  SELECTOR_NO_FEEDBACK_AT_ALL: 'positions',
};

const FIELD_LABEL_RE = /field '([^']+)'/;
const ADDRESS_RE = /'([^']*)'/;

function fieldsForAddress(device: Device, addr: string): string[] {
  return getDeviceChannelAddressFields(device).filter(f => f.addr === addr).map(f => f.field);
}

/** Files each issue under the field key(s) it applies to. Anything that cannot be attributed to a specific field lands under the '_general' key instead of being dropped. */
export function mapDeviceIssuesToFields(issues: ValidationIssue[], device: Device): Map<string, string[]> {
  const result = new Map<string, string[]>();
  const add = (field: string, message: string) => {
    if (!result.has(field)) result.set(field, []);
    result.get(field)!.push(message);
  };

  for (const issue of issues) {
    const fixed = FIXED_FIELD_BY_CODE[issue.code];
    if (fixed) {
      for (const f of Array.isArray(fixed) ? fixed : [fixed]) add(f, issue.message);
      continue;
    }

    if (issue.code === 'DEVICE_FIELD_INVALID_ADDRESS' || issue.code === 'DEVICE_FIELD_WRONG_CHANNEL_KIND') {
      const m = issue.message.match(FIELD_LABEL_RE);
      if (m) { add(m[1], issue.message); continue; }
    }

    if (issue.code.startsWith('CHANNEL_ADDRESS_')) {
      const m = issue.message.match(ADDRESS_RE);
      const addr = m ? m[1] : '';
      const fields = fieldsForAddress(device, addr);
      if (fields.length > 0) {
        for (const f of fields) add(f, issue.message);
        continue;
      }
    }

    add('_general', issue.message);
  }

  return result;
}
