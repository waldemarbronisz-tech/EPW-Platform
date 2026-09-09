// feat/editing-and-signal-panel commit 8: the picker that adds signal
// panel rows in bulk, grouped by LOCATION rather than by unit - see
// this file's own header note below for why. Mirrors MeterWizard.ts's
// own structure (a tree of groups, checkboxes underneath, confirm adds
// everything checked at once, in tree order). Pure, Konva-free, same
// convention as the rest of this element's logic.
//
// Grouping by unit (the meter's own wizard) makes sense for a
// measurement - "V" collects every voltage. A two-state signal has no
// unit at all, so that axis is meaningless here; what DOES group
// signals naturally is where they physically are - a "STAN BRAMY"
// panel wants every gate-related aparat together, a boiler-room panel
// wants every kotlownia aparat together. The device id's own prefix
// before the underscore (e.g. 'KOT_KMG1' -> 'KOT', 'BRAMA_FC1' ->
// 'BRAMA') already encodes exactly that split - it is the same prefix
// DeviceSchema.ts's own LocationEntry.code is meant to describe, just
// read directly off the id rather than cross-referenced against the
// registry's locations list (a device with no matching LocationEntry
// still has an id, and still groups sensibly by it).

import type { Device } from '../project/DeviceSchema';
import type { SignalPanelRow } from './SignalPanelElement';
import { getSignalCapableDevices, type SignalCapableDevice } from './SignalPanelResolver';

export interface SignalPanelWizardGroup {
  location: string;
  devices: SignalCapableDevice[];
}

/** An id with no underscore at all groups under its own full id - still deterministic, never thrown away. */
function locationOf(deviceId: string): string {
  const idx = deviceId.indexOf('_');
  return idx === -1 ? deviceId : deviceId.slice(0, idx);
}

/**
 * Every SIGNAL or SWITCHED device in the project, grouped by the
 * prefix of its id before the first underscore. Group order follows
 * the order locations are first encountered scanning the device list
 * (not alphabetical) - arbitrary but deterministic, same convention as
 * MeterWizard.ts's groupMeasuredDevicesByUnit. A MEASURED or MODULATED
 * device never appears in any group (getSignalCapableDevices already
 * excludes them). An empty (or device-less) project returns an empty
 * array, never throwing - the caller (SignalPanelWizardDialog.tsx) is
 * what turns that into the "define signal devices first" explanation.
 */
export function groupSignalCapableDevicesByLocation(devices: Device[]): SignalPanelWizardGroup[] {
  const capable = getSignalCapableDevices(devices);
  const order: string[] = [];
  const byLocation = new Map<string, SignalCapableDevice[]>();
  capable.forEach(d => {
    const location = locationOf(d.id);
    if (!byLocation.has(location)) {
      byLocation.set(location, []);
      order.push(location);
    }
    byLocation.get(location)!.push(d);
  });
  return order.map(location => ({ location, devices: byLocation.get(location)! }));
}

/**
 * Turns a set of checked device ids into new signal panel rows, in
 * TREE order (group order, then device order within the group) -
 * never selection (click) order, same explicit requirement as the
 * meter's own wizard. A checked id that does not appear in `groups`
 * (should not happen from the dialog itself, but this stays
 * defensive) is simply skipped, not an error.
 */
export function buildSignalPanelRowsFromSelection(groups: SignalPanelWizardGroup[], selectedDeviceIds: Set<string>): SignalPanelRow[] {
  const rows: SignalPanelRow[] = [];
  groups.forEach(group => {
    group.devices.forEach(device => {
      if (selectedDeviceIds.has(device.id)) {
        rows.push({ device: device.id, label: '', manualState: 'OFF' });
      }
    });
  });
  return rows;
}
