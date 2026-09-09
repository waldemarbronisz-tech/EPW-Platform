// feat/meter-element part B: what a meter row actually shows once it
// points at a device. Pure, Konva-free - the store's own `devices`
// array (populated from the project file's optional `devices` field,
// see ProjectSchema.ts/ProjectManager.ts) is passed in by the caller,
// never read from the store directly, so this stays testable with a
// plain array and no Zustand involved at all.
//
// THE ONE RULE THIS FILE EXISTS TO ENFORCE: a device-linked row never
// stores its own copy of the unit or the format string. Both always
// come from the device, every time this resolves - never written back
// onto the row. A duplicated unit is a guaranteed future drift: the
// device gets reconfigured from watts to kilowatts and the meter,
// having cached its own copy, keeps right on printing watts.

import type { Device, MeasuredDevice } from '../project/DeviceSchema';
import type { MeterElement, MeterElementRow } from './MeterElement';
import { formatManualRowValue } from './MeterElement';
import { findDeviceById, filterDevicesByBehavior } from '../project/DeviceLookup';

// findDeviceById is re-exported here (not just imported for internal
// use) so existing callers of this module keep working unchanged - see
// project/DeviceLookup.ts's own header comment for why it moved there.
export { findDeviceById };

/**
 * Every MEASURED device in a project's device list. THE canonical path
 * from the device registry contract to anything in this editor that
 * needs measurement devices - the meter's own row resolution below,
 * and the wizard's group-by-unit list (MeterWizard.ts), both call
 * this rather than filtering `behavior === 'MEASURED'` themselves.
 */
export function getMeasuredDevices(devices: Device[]): MeasuredDevice[] {
  return filterDevicesByBehavior(devices, ['MEASURED'] as const);
}

/**
 * The editor has no live data - a device-linked row previews the
 * MIDDLE of the device's own configured range (0..400 -> 200,
 * -20..120 -> 50), not a made-up number. Whatever the actual live
 * value turns out to be at runtime is EPW-OS's concern, not this
 * editor's.
 */
export function getMeasuredPreviewValue(device: MeasuredDevice): number {
  return (device.rangeMin + device.rangeMax) / 2;
}

/**
 * Applies a MeasuredDevice's own format string (e.g. '0.0', '0.00',
 * '0') the same way EPW-OS is expected to: the digit count after the
 * decimal point in the format string is how many decimal places the
 * value is shown with. An empty or unrecognized format falls back to
 * one decimal place rather than throwing - a malformed format string
 * is a device-configuration problem, not a reason for the meter itself
 * to stop rendering.
 */
export function formatMeasuredValue(value: number, format: string): string {
  if (!format) return value.toFixed(1); // no format string at all - a sane default, not a throw
  const match = /\.(0+)/.exec(format);
  // A format with no decimal point at all (e.g. '0') genuinely means
  // zero decimal places - only a missing/empty format falls back to 1.
  const decimals = match ? match[1].length : 0;
  return value.toFixed(decimals);
}

export type MeterRowColorKind = 'NORMAL' | 'PREVIEW' | 'MISSING';

export interface MeterRowDisplay {
  label: string;
  valueText: string;
  colorKind: MeterRowColorKind;
}

/**
 * What one row actually shows. A manual row (no device) is untouched
 * from part A - manualValue/manualUnit, straight through. A device-
 * linked row resolves its label (falling back to the device's own
 * designation when the row's own label is empty), its unit and its
 * format EXCLUSIVELY from the device - see this file's own header
 * comment. A row pointing at a device id that either does not exist, or
 * exists but is not itself MEASURED (its unit/range/format do not
 * exist to read), is treated as missing: a "?" value, never an
 * exception - the meter still renders every other row normally.
 */
export function resolveMeterRow(row: MeterElementRow, devices: Device[]): MeterRowDisplay {
  if (!row.device) {
    return { label: row.label, valueText: formatManualRowValue(row), colorKind: 'NORMAL' };
  }

  const device = findDeviceById(devices, row.device);
  if (!device || device.behavior !== 'MEASURED') {
    return { label: row.label, valueText: '?', colorKind: 'MISSING' };
  }

  const label = row.label || device.designation;
  const value = getMeasuredPreviewValue(device);
  const valueText = `${formatMeasuredValue(value, device.format)} ${device.unit}`;
  return { label, valueText, colorKind: 'PREVIEW' };
}

export interface MeterDanglingRowIssue {
  rowIndex: number;
  deviceId: string;
}

/**
 * Every row whose device reference does not resolve - what drives the
 * Messages notice a dangling row is supposed to raise (per this
 * element's own spec: not a hard error, the meter keeps rendering, but
 * the user should hear about it). Computed independently of
 * resolveMeterRow so a caller (MeterElementNode.tsx) can react to a
 * CHANGE in this list without re-deriving it from every row's display
 * on every render.
 */
export function getMeterDanglingRows(meter: Pick<MeterElement, 'rows'>, devices: Device[]): MeterDanglingRowIssue[] {
  const issues: MeterDanglingRowIssue[] = [];
  meter.rows.forEach((row, rowIndex) => {
    if (!row.device) return;
    const device = findDeviceById(devices, row.device);
    if (!device || device.behavior !== 'MEASURED') {
      issues.push({ rowIndex, deviceId: row.device });
    }
  });
  return issues;
}
