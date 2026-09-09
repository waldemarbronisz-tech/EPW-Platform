// Signal/command enumeration for the EPW Device Registry (DeviceSchema.ts).
//
// The signal set is ALWAYS derived from device.behavior (and, for SWITCHED,
// from extraInputs.diFault / switchCounter) - never declared in the device
// config itself. A declared list could drift from the actual configuration;
// a derived one has no way to lie.

import type { Device } from './DeviceSchema';

/** Signals a device makes available for control logic to READ. */
export function getDeviceSignals(device: Device): string[] {
  switch (device.behavior) {
    case 'SWITCHED': {
      const signals = ['.STATE', '.DISCREPANCY'];
      if (device.extraInputs?.diFault) signals.push('.FAULT');
      if (device.switchCounter) signals.push('.COUNTER');
      return signals;
    }
    case 'SIGNAL':
      return ['.STATE'];
    case 'MEASURED':
      return ['.VALUE', '.QUALITY'];
    case 'MODULATED':
      return ['.SETPOINT', '.FEEDBACK'];
    case 'SELECTOR':
      return ['.POSITION'];
  }
}

/**
 * Commands control logic may ISSUE to a device. Logic is entitled to
 * command any SWITCHED or MODULATED device - there is not, and must never
 * be, a field that enables or disables control from logic.
 *
 * In the EPW platform, control logic runs continuously in the runtime
 * ALONGSIDE EPW-OS. An operator command from a screen goes straight to the
 * output, bypassing logic - that is what lets the screen keep working
 * independently of the state of logic. Logic can independently issue
 * commands of its own.
 *
 * This creates a gap: logic can switch something ON, but has no way to
 * FORBID anything, and an operator command does not consult it at all -
 * an interlock authored in EPW-Logic-Studio would have no way to take
 * effect. The fix is INHIBIT signals: a device exposes inhibit points that
 * logic writes to, and EPW-OS checks them before EVERY command - its own
 * and the operator's - refusing to execute and telling the operator the
 * device is blocked.
 */
export function getDeviceCommands(device: Device): string[] {
  switch (device.behavior) {
    case 'SWITCHED':
      return ['.CLOSE', '.OPEN', '.INHIBIT_CLOSE', '.INHIBIT_OPEN'];
    case 'SIGNAL':
      return [];
    case 'MEASURED':
      return [];
    case 'MODULATED':
      return ['.SET', '.INHIBIT_SET'];
    // A selector switch is turned by hand at the panel - there is
    // nothing for logic or an operator to command remotely, unlike
    // SWITCHED/MODULATED. See DeviceSchema.ts's own SelectorDevice
    // comment for why this is deliberate, not an oversight.
    case 'SELECTOR':
      return [];
  }
}

/**
 * Inhibit signals only (the '.INHIBIT_'-prefixed subset of commands).
 * EPW-OS needs these on their own, to check them before executing a
 * command, without scanning the whole command list.
 */
export function getDeviceInhibits(device: Device): string[] {
  return getDeviceCommands(device).filter(suffix => suffix.startsWith('.INHIBIT_'));
}

/** Full point names for reading, e.g. 'KOT_KMG1.STATE'. */
export function getDeviceSignalNames(device: Device): string[] {
  return getDeviceSignals(device).map(suffix => `${device.id}${suffix}`);
}

/** Full point names for commanding, e.g. 'KOT_KMG1.CLOSE'. */
export function getDeviceCommandNames(device: Device): string[] {
  return getDeviceCommands(device).map(suffix => `${device.id}${suffix}`);
}

/** Full point names for inhibits, e.g. 'KOT_KMG1.INHIBIT_CLOSE'. */
export function getDeviceInhibitNames(device: Device): string[] {
  return getDeviceInhibits(device).map(suffix => `${device.id}${suffix}`);
}
