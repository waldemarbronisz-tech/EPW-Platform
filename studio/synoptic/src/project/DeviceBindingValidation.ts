// feat/device-list-ui commit 5 - validation for a NEW concept this
// commit introduces: a schematic symbol's own binding to a device
// (SynopticObject.deviceId), not anything DeviceValidation.ts's
// validateDeviceRegistry already covers (that function validates the
// device registry itself - locations, cards, devices - and knows
// nothing about screens or symbols). This file is intentionally
// separate and does not touch or duplicate any rule from that file.
//
// There is exactly one rule: a deviceId that does not resolve to any
// device in the project's registry is worth flagging. Two symbols (or
// two screens) pointing at the SAME device id is explicitly NOT an
// issue - that is this task's own stated architecture (a device is
// defined once, referenced whichever places need it) - so this file
// never checks for duplicates.

import type { Device } from './DeviceSchema';
import type { SynopticObject } from '../store/types';
import { describeObject } from '../utils/ObjectDisplay';

export interface DeviceBindingIssue {
  severity: 'WARNING';
  objectId: string;
  message: string;
}

/** Every object whose deviceId is set but does not match any device in the registry. */
export function validateDeviceBindings(objects: SynopticObject[], devices: Device[]): DeviceBindingIssue[] {
  const knownIds = new Set(devices.map(d => d.id));
  const issues: DeviceBindingIssue[] = [];
  for (const obj of objects) {
    if (obj.deviceId && !knownIds.has(obj.deviceId)) {
      issues.push({
        severity: 'WARNING',
        objectId: obj.id,
        message: `Symbol ${describeObject(obj)} points to a nonexistent device '${obj.deviceId}'`
      });
    }
  }
  return issues;
}

export function isSymbolDeviceMissing(obj: SynopticObject, devices: Device[]): boolean {
  return !!obj.deviceId && !devices.some(d => d.id === obj.deviceId);
}
