// feat/selector-symbol-setpoint-alarm: what a setpoint panel row
// actually shows once it points at a device. Mirrors MeterResolver.ts's
// own structure closely (same THE ONE RULE: a device-linked row never
// stores its own copy of the unit - always read from the device, every
// time this resolves).
//
// Pure, Konva-free - the store's own `devices` array is passed in by
// the caller, never read from the store directly here, same convention
// as MeterResolver.ts/SignalPanelResolver.ts.

import type { Device, ModulatedDevice } from '../project/DeviceSchema';
import type { SetpointPanelElement, SetpointRow } from './SetpointElement';
import { formatManualSetpointValue } from './SetpointElement';
import { findDeviceById, filterDevicesByBehavior } from '../project/DeviceLookup';

/**
 * Every MODULATED device in a project's device list - the canonical
 * path from the device registry contract to anything in this element
 * that needs a settable device. Only MODULATED devices have a setpoint
 * to show at all (DeviceSchema.ts) - SWITCHED/SIGNAL/MEASURED/SELECTOR
 * devices are never valid rows here, mirroring how getCommandableDevices
 * (GroupCommandResolver.ts) keeps only SWITCHED for its own, different
 * reason.
 */
export function getSetpointCapableDevices(devices: Device[]): ModulatedDevice[] {
  return filterDevicesByBehavior(devices, ['MODULATED'] as const);
}

/**
 * The editor has no live data - a device-linked row previews the
 * device's own configured STARTUP value, not a made-up number or a
 * range midpoint: for a WRITABLE point, "what would this show before
 * anyone touches it" is the one number DeviceSchema.ts already commits
 * to (startupValue), unlike a MEASURED device's preview
 * (getMeasuredPreviewValue, MeterResolver.ts), which has no equivalent
 * concept to read and falls back to a plain range midpoint instead.
 */
export function getSetpointPreviewValue(device: ModulatedDevice): number {
  return device.startupValue;
}

/**
 * MODULATED devices have no format string of their own (unlike
 * MeasuredDevice.format) - always one decimal place, the same fallback
 * formatMeasuredValue (MeterResolver.ts) uses for a missing format.
 */
export function formatSetpointValue(value: number): string {
  return value.toFixed(1);
}

export type SetpointRowColorKind = 'NORMAL' | 'PREVIEW' | 'MISSING';

export interface SetpointRowDisplay {
  label: string;
  valueText: string;
  colorKind: SetpointRowColorKind;
}

/**
 * What one row actually shows. A manual row (no device) is untouched -
 * manualValue/manualUnit, straight through. A device-linked row
 * resolves its label (falling back to the device's own designation
 * when the row's own label is empty) and its unit EXCLUSIVELY from the
 * device. A row pointing at a device id that either does not exist, or
 * exists but is not itself MODULATED (no setpoint to preview at all),
 * is treated as missing: a "?" value, never an exception.
 */
export function resolveSetpointRow(row: SetpointRow, devices: Device[]): SetpointRowDisplay {
  if (!row.device) {
    return { label: row.label, valueText: formatManualSetpointValue(row), colorKind: 'NORMAL' };
  }

  const device = findDeviceById(devices, row.device);
  if (!device || device.behavior !== 'MODULATED') {
    return { label: row.label, valueText: '?', colorKind: 'MISSING' };
  }

  const label = row.label || device.designation;
  const value = getSetpointPreviewValue(device);
  const valueText = `${formatSetpointValue(value)} ${device.unit}`;
  return { label, valueText, colorKind: 'PREVIEW' };
}

export interface SetpointDanglingRowIssue {
  rowIndex: number;
  deviceId: string;
}

/**
 * Every row whose device reference does not resolve to a MODULATED
 * device - what drives the Messages notice a dangling row raises, same
 * structure as MeterResolver.ts's getMeterDanglingRows.
 */
export function getSetpointDanglingRows(panel: Pick<SetpointPanelElement, 'rows'>, devices: Device[]): SetpointDanglingRowIssue[] {
  const issues: SetpointDanglingRowIssue[] = [];
  panel.rows.forEach((row, rowIndex) => {
    if (!row.device) return;
    const device = findDeviceById(devices, row.device);
    if (!device || device.behavior !== 'MODULATED') {
      issues.push({ rowIndex, deviceId: row.device });
    }
  });
  return issues;
}
