// Generic lookups against the project's device list (src/project/
// DeviceSchema.ts's contract) - shared by MeterResolver.ts and
// feat/editing-and-signal-panel commit 7's SignalPanelResolver.ts, both
// of which need "find one device by id" and "keep only devices with
// one of these behaviors" and neither of which is specific to either
// element. Pure, Konva-free (same convention as GridSnap.ts/
// Terminals.ts).
//
// findDeviceById used to live in MeterResolver.ts itself; moved here
// once a second resolver needed the exact same function rather than a
// duplicate of it - meter-resolver.test.ts's own tests (which exercise
// it indirectly, through resolveMeterRow/getMeterDanglingRows) pass
// unmodified, proving this relocation changed nothing about what it does.

import type { Device, DeviceBehavior } from './DeviceSchema';

export function findDeviceById(devices: Device[], id: string): Device | undefined {
  return devices.find(d => d.id === id);
}

/** Keeps only devices whose behavior is one of `behaviors` - what getMeasuredDevices/getSignalCapableDevices both reduce to. */
export function filterDevicesByBehavior<B extends DeviceBehavior>(
  devices: Device[],
  behaviors: readonly B[]
): Extract<Device, { behavior: B }>[] {
  const set: readonly DeviceBehavior[] = behaviors;
  return devices.filter((d): d is Extract<Device, { behavior: B }> => set.includes(d.behavior));
}
