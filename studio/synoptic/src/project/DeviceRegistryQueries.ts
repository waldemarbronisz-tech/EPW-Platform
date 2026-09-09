// Usage queries against the device registry (DeviceSchema.ts's contract)
// for the UI's own needs: which devices reference a location or a card,
// which channels a card already has occupied, and a device's own
// location code. NONE of this is validation - DeviceValidation.ts's
// validateDeviceRegistry remains the only place a business rule is
// checked or an error is reported; this file only answers "who is
// using X", which the delete-protection dialogs (commit 1) and the
// channel picker (commit 3) both need, but which validateDeviceRegistry
// itself has no reason to expose (it produces a flat issue list, not a
// queryable index).

import type { Device } from './DeviceSchema';
import { parseChannelAddress } from './DeviceValidation';
import { getDeviceChannelAddressFields } from './DeviceFieldMap';

/** Every device whose id starts with this location code (DeviceValidation.ts's own id rule: CODE_suffix). Used to block deleting a location still in use, and to count how many devices would be affected. */
export function getDevicesUsingLocation(devices: Device[], locationCode: string): Device[] {
  const prefix = `${locationCode}_`;
  return devices.filter(d => d.id.startsWith(prefix));
}

export interface ChannelUsage {
  deviceId: string;
  field: string;
  addr: string;
}

/** Every (device, field, address) triple whose address resolves to a channel on `cardId` - what "channel already occupied" and "card still in use" both reduce to. */
export function getChannelUsagesForCard(devices: Device[], cardId: string): ChannelUsage[] {
  const usages: ChannelUsage[] = [];
  for (const device of devices) {
    for (const { field, addr } of getDeviceChannelAddressFields(device)) {
      const parsed = parseChannelAddress(addr);
      if (parsed && parsed.card === cardId) {
        usages.push({ deviceId: device.id, field, addr });
      }
    }
  }
  return usages;
}

/**
 * Every channel address already in use across the registry, normalized
 * (CARD.KIND.CHANNEL) so 'ELA1.DI.12' and 'ELA1.DI.012' collide the same
 * way DeviceValidation.ts's own collision check treats them - mapped to
 * which device occupies it. `excludeDeviceId`, when given, leaves that
 * device's own current addresses out (editing a device must not report
 * its own already-saved channel as "taken by someone else").
 */
export function getOccupiedChannels(devices: Device[], excludeDeviceId?: string): Map<string, { deviceId: string; field: string }> {
  const map = new Map<string, { deviceId: string; field: string }>();
  for (const device of devices) {
    if (device.id === excludeDeviceId) continue;
    for (const { field, addr } of getDeviceChannelAddressFields(device)) {
      const parsed = parseChannelAddress(addr);
      if (!parsed) continue;
      const key = `${parsed.card}.${parsed.kind}.${parsed.channel}`;
      if (!map.has(key)) map.set(key, { deviceId: device.id, field });
    }
  }
  return map;
}

/** The location-code prefix of a device id ('KOT_KMG1' -> 'KOT') - the list window's own location filter is computed from this, never stored on the device itself (this task's own explicit rule: location is derived, not duplicated data). Returns the whole id if there is no underscore (an already-invalid id, per DeviceValidation's own id rule - still needs SOME value to filter/group by rather than throwing). */
export function getDeviceLocationCode(deviceId: string): string {
  const idx = deviceId.indexOf('_');
  return idx >= 0 ? deviceId.slice(0, idx) : deviceId;
}

/** Total channels ELA1/ADA1/... 64+32+... a project's card registry declares - the list window's status bar denominator. */
export function getTotalChannelCount(cards: { channelCount: number }[]): number {
  return cards.reduce((sum, c) => sum + c.channelCount, 0);
}

/** Total channels actually referenced by some device, across the whole registry (normalized, so a duplicate/collision is still only counted once - it is one physical terminal). */
export function getUsedChannelCount(devices: Device[]): number {
  return getOccupiedChannels(devices).size;
}

/**
 * How many placed screen symbols (SynopticObject.deviceId) currently
 * reference each device - DeviceListDialog.tsx's own Uzycia column, and
 * (fix/inline-device-creation commit 3) the row-by-row usage count
 * PRZYPISZ ISTNIEJACY's own device list shows. The SAME device used by
 * several symbols is normal, not an error, per this task's own
 * architecture, so this only counts, it never flags - moved here
 * (rather than staying a local useMemo in one dialog) so a second
 * dialog needing the identical count is not tempted to re-derive it.
 */
export function getObjectUsageCounts(objects: { deviceId?: string }[]): Map<string, number> {
  const map = new Map<string, number>();
  for (const obj of objects) {
    if (!obj.deviceId) continue;
    map.set(obj.deviceId, (map.get(obj.deviceId) ?? 0) + 1);
  }
  return map;
}
