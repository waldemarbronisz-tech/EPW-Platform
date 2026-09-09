// feat/control-elements commit 2 - resolving a group command button's
// deviceIds against the live device list. Mirrors SignalPanelResolver.ts's
// own structure (see that file's header for why a per-element resolver
// exists at all, rather than the shared, project-wide
// DeviceBindingValidation.ts, which only ever covers a SynopticObject's
// single Aparat binding).
//
// Pure, Konva-free - the store's own `devices` array is passed in by
// the caller, never read from the store directly here, same convention
// as SignalPanelResolver.ts/MeterResolver.ts.

import type { Device, SwitchedDevice } from '../project/DeviceSchema';
import type { GroupCommandElement } from './GroupCommandElement';
import { findDeviceById, filterDevicesByBehavior } from '../project/DeviceLookup';
import { getDeviceCommandNames } from '../project/DeviceSignals';

/**
 * Only SWITCHED devices have a .CLOSE/.OPEN command at all
 * (DeviceSignals.ts's own getDeviceCommands) - a group command button
 * can only ever offer those as members. SIGNAL/MEASURED/MODULATED/
 * SELECTOR devices are never valid members, exactly like a MEASURED/
 * MODULATED device is never a valid signal panel row (SignalPanelResolver.ts).
 */
export function getCommandableDevices(devices: Device[]): SwitchedDevice[] {
  return filterDevicesByBehavior(devices, ['SWITCHED'] as const);
}

export interface GroupCommandMemberDisplay {
  deviceId: string;
  designation: string; // '(brak)' when dangling - see below
  dangling: boolean;
}

/**
 * Every member id resolved against the current device list, in the
 * order the button stores them, for display in the Properties panel.
 * A dangling id (deleted device, or a device whose behavior changed
 * away from SWITCHED) is never dropped silently - it stays in the list,
 * marked, exactly like a signal panel's own dangling row.
 */
export function resolveGroupCommandMembers(el: Pick<GroupCommandElement, 'deviceIds'>, devices: Device[]): GroupCommandMemberDisplay[] {
  return el.deviceIds.map(deviceId => {
    const device = findDeviceById(devices, deviceId);
    if (!device || device.behavior !== 'SWITCHED') {
      return { deviceId, designation: '(brak)', dangling: true };
    }
    return { deviceId, designation: device.designation, dangling: false };
  });
}

export interface GroupCommandDanglingIssue {
  deviceId: string;
}

/**
 * Every member id that does not resolve to a SWITCHED device - what
 * drives the Messages notice a dangling member raises. Computed
 * independently of resolveGroupCommandMembers so a caller
 * (GroupCommandElementNode.tsx) can react to a CHANGE in this list
 * without re-deriving it on every render, same structure as
 * SignalPanelResolver.ts's getSignalPanelDanglingRows.
 */
export function getGroupCommandDanglingMembers(el: Pick<GroupCommandElement, 'deviceIds'>, devices: Device[]): GroupCommandDanglingIssue[] {
  return el.deviceIds
    .filter(deviceId => {
      const device = findDeviceById(devices, deviceId);
      return !device || device.behavior !== 'SWITCHED';
    })
    .map(deviceId => ({ deviceId }));
}

/**
 * The full point names this click WOULD command, e.g.
 * ['KOT_W1.CLOSE', 'KOT_W2.CLOSE'] - dangling members excluded (there
 * is nothing to command). This editor is design-time only - see this
 * file's own header - so nothing actually sends these; this is what a
 * runtime client reads to know what a click means, and what this
 * element's own preview/log message is built from.
 */
export function getGroupCommandTargetNames(el: Pick<GroupCommandElement, 'command' | 'deviceIds'>, devices: Device[]): string[] {
  const suffix = el.command === 'CLOSE' ? '.CLOSE' : '.OPEN';
  return el.deviceIds
    .map(id => findDeviceById(devices, id))
    .filter((d): d is SwitchedDevice => !!d && d.behavior === 'SWITCHED')
    .flatMap(d => getDeviceCommandNames(d).filter(name => name.endsWith(suffix)));
}
