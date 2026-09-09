// feat/editing-and-signal-panel commit 7: what a signal panel row
// actually shows once it points at a device. Mirrors MeterResolver.ts's
// own structure closely - see raport.md for what is shared between the
// two (project/DeviceLookup.ts's findDeviceById/filterDevicesByBehavior)
// and what is duplicated (this file's own resolve/dangling-rows
// functions - the actual resolution rules differ enough, per medium
// vs. per behavior, that folding them into one shared function would
// need its own behavior-specific branches anyway).
//
// Pure, Konva-free - the store's own `devices` array is passed in by
// the caller, never read from the store directly here, same convention
// as MeterResolver.ts.

import type { Device, SignalDevice, SwitchedDevice } from '../project/DeviceSchema';
import type { SignalPanelElement, SignalPanelRow } from './SignalPanelElement';
import type { IndicatorDiodeState } from '../symbols/scada/IndicatorDiodeSymbol';
import { findDeviceById, filterDevicesByBehavior } from '../project/DeviceLookup';

export type SignalCapableDevice = SignalDevice | SwitchedDevice;

/**
 * Every SIGNAL or SWITCHED device in a project's device list - the
 * canonical path from the device registry contract to anything in this
 * element that needs a signal-capable device. MEASURED and MODULATED
 * devices are never included here, in either sense: they belong to the
 * meter (MEASURED) or to nothing built yet (MODULATED) - a panel row
 * pointing at one of those resolves exactly like a row pointing at a
 * device that does not exist at all (resolveSignalPanelRow below).
 */
export function getSignalCapableDevices(devices: Device[]): SignalCapableDevice[] {
  return filterDevicesByBehavior(devices, ['SIGNAL', 'SWITCHED'] as const);
}

export type SignalPanelRowColorKind = 'NORMAL' | 'PREVIEW' | 'MISSING';

export interface SignalPanelRowDisplay {
  label: string;
  state: IndicatorDiodeState;
  colorKind: SignalPanelRowColorKind;
}

/**
 * What one row actually shows. A manual row (no device) is untouched
 * from commit 6 - manualState, straight through. A device-linked row
 * resolves its label (falling back to the device's own designation
 * when the row's own label is empty) from the device; the editor has
 * no live input/closed-contact data, the same reasoning
 * MeterResolver.ts's preview value follows, just with nothing to
 * compute (a two-state signal has no "middle" to preview).
 *
 * The preview STATE depends on which behavior resolved: a SWITCHED
 * device previews ON - a contactor sitting closed/energized is its
 * normal operating state, not an alarm condition. A SIGNAL device
 * previews ALARM instead (feat/selector-symbol-setpoint-alarm) - a
 * SIGNAL device's entire reason for being modeled separately from
 * SWITCHED is alarm signalling (see its own alarmState field in
 * DeviceSchema.ts), so the representative preview for laying out a
 * panel is what it looks like TRIPPED, not a meaningless generic ON.
 *
 * A row pointing at a device id that either does not exist, or exists
 * but is not itself SIGNAL or SWITCHED (a MEASURED or MODULATED device
 * has no notion of "closed"/"input active" to preview at all), is
 * treated as missing: QUALITY, never an exception.
 */
export function resolveSignalPanelRow(row: SignalPanelRow, devices: Device[]): SignalPanelRowDisplay {
  if (!row.device) {
    return { label: row.label, state: row.manualState, colorKind: 'NORMAL' };
  }

  const device = findDeviceById(devices, row.device);
  if (!device || (device.behavior !== 'SIGNAL' && device.behavior !== 'SWITCHED')) {
    return { label: row.label, state: 'QUALITY', colorKind: 'MISSING' };
  }

  const label = row.label || device.designation;
  const state = device.behavior === 'SIGNAL' ? 'ALARM' : 'ON';
  return { label, state, colorKind: 'PREVIEW' };
}

export interface SignalPanelDanglingRowIssue {
  rowIndex: number;
  deviceId: string;
}

/**
 * Every row whose device reference does not resolve to a SIGNAL or
 * SWITCHED device - what drives the Messages notice a dangling row
 * raises. Computed independently of resolveSignalPanelRow so a caller
 * (SignalPanelElementNode.tsx) can react to a CHANGE in this list
 * without re-deriving it from every row's display on every render -
 * same structure as MeterResolver.ts's getMeterDanglingRows.
 */
export function getSignalPanelDanglingRows(panel: Pick<SignalPanelElement, 'rows'>, devices: Device[]): SignalPanelDanglingRowIssue[] {
  const issues: SignalPanelDanglingRowIssue[] = [];
  panel.rows.forEach((row, rowIndex) => {
    if (!row.device) return;
    const device = findDeviceById(devices, row.device);
    if (!device || (device.behavior !== 'SIGNAL' && device.behavior !== 'SWITCHED')) {
      issues.push({ rowIndex, deviceId: row.device });
    }
  });
  return issues;
}
