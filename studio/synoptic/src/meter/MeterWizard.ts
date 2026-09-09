// feat/meter-element part C: the picker that adds rows in bulk,
// grouped by unit - the e2TANGO-Studio pattern this whole element is
// modeled on (a tree of groups, checkboxes underneath, confirm adds
// everything checked at once). Pure, Konva-free, same convention as
// the rest of this element's logic (MeterElement.ts/MeterResolver.ts).

import type { Device, MeasuredDevice } from '../project/DeviceSchema';
import type { MeterElementRow } from './MeterElement';
import { getMeasuredDevices } from './MeterResolver';

export interface MeterWizardGroup {
  unit: string;
  devices: MeasuredDevice[];
}

/**
 * Every MEASURED device in the project, grouped by its own unit - "V"
 * collects every voltage, "A" every current, and so on; the group name
 * IS the unit, nothing fancier. Group order follows the order units
 * are first encountered scanning the device list (not alphabetical) -
 * arbitrary but deterministic, and irrelevant to the one thing the
 * task's own spec actually constrains: the ROWS added on confirm
 * follow this same tree order (buildRowsFromSelection below), whatever
 * that order happens to be.
 *
 * An empty (or device-less) project returns an empty array, never
 * throwing - the caller (MeterWizardDialog.tsx) is what turns that
 * into the "define measurement devices first" explanation, not this
 * function's job.
 */
export function groupMeasuredDevicesByUnit(devices: Device[]): MeterWizardGroup[] {
  const measured = getMeasuredDevices(devices);
  const order: string[] = [];
  const byUnit = new Map<string, MeasuredDevice[]>();
  measured.forEach(d => {
    if (!byUnit.has(d.unit)) {
      byUnit.set(d.unit, []);
      order.push(d.unit);
    }
    byUnit.get(d.unit)!.push(d);
  });
  return order.map(unit => ({ unit, devices: byUnit.get(unit)! }));
}

/**
 * Turns a set of checked device ids into new meter rows, in TREE order
 * (group order, then device order within the group) - never selection
 * (click) order, per the task's own explicit requirement. A checked id
 * that does not appear in `groups` (should not happen from the dialog
 * itself, but this stays defensive) is simply skipped, not an error.
 */
export function buildRowsFromSelection(groups: MeterWizardGroup[], selectedDeviceIds: Set<string>): MeterElementRow[] {
  const rows: MeterElementRow[] = [];
  groups.forEach(group => {
    group.devices.forEach(device => {
      if (selectedDeviceIds.has(device.id)) {
        rows.push({ device: device.id, label: '', manualValue: '', manualUnit: '' });
      }
    });
  });
  return rows;
}
