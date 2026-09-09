// feat/control-elements commit 3 - whether a schematic symbol's bound
// device carries a configured interlock description
// (SwitchedDevice.interlock - DeviceSchema.ts). Kept separate from
// DeviceBindingValidation.ts on purpose: that file's own header states
// its scope as "exactly one rule" (a dangling deviceId) and is not the
// place to grow a second, unrelated concern.
//
// This is a pure DISPLAY concern, not a validation rule - a missing
// interlock is not wrong, it just means "no configured blockage", so
// there is no ValidationIssue here, only a boolean and (for the
// Properties/tooltip text a caller may want) the description itself.

import type { Device } from './DeviceSchema';
import type { SynopticObject } from '../store/types';
import { findDeviceById } from './DeviceLookup';

/**
 * True when `obj`'s bound device is a SWITCHED device with at least
 * one non-blank interlock description. A device that does not exist,
 * is not SWITCHED, or has an interlock object with only blank/absent
 * strings, all resolve to false - exactly the same "problem/absence,
 * never an exception" treatment isSymbolDeviceMissing already uses.
 */
export function isSymbolInterlocked(obj: SynopticObject, devices: Device[]): boolean {
  if (!obj.deviceId) return false;
  const device = findDeviceById(devices, obj.deviceId);
  if (!device || device.behavior !== 'SWITCHED') return false;
  const { closeDescription, openDescription } = device.interlock ?? {};
  return !!(closeDescription?.trim() || openDescription?.trim());
}
