// feat/room-plan: what connects a circuit on the floor plan to the
// controller that will actually switch it.
//
// THE POINT OF THE WHOLE PLAN. Up to here a circuit was a name shared by
// some fixtures, and clicking it changed a preview state - a drawing
// that behaved like a drawing. A circuit BOUND to a device is different:
// the device is a real entry in the project's own device registry
// (DeviceSchema.ts), its behaviour is SWITCHED, and its command.doClose
// is a physical output channel on a real I/O card. Bind the circuit to
// it and the plan stops being an illustration of the installation and
// becomes part of its configuration - the thing you clicked on the plan
// is the thing the controller will energise.
//
// WHAT THIS MODULE DOES NOT DO. It does not command anything and it does
// not read live state: this is an EDITOR, and DeviceSchema.ts's own
// header is explicit that a SWITCHED device's contract here is channel
// ADDRESSES, never a live value. Binding records an intent; EPW-OS is
// what acts on it.
//
// FEEDBACK, and why a lighting circuit normally has none.
//
// A lighting circuit is switched by a plain digital output: the DO
// closes and the lamp lights. There is no auxiliary contact to read
// back, so there is nothing to confirm the lamp WITH - the state of
// such a circuit is ASSUMED from the command, immediately, and that is
// correct rather than a shortcut. A contactor whose auxiliary contact
// IS wired (feedback SINGLE or DUAL) can be confirmed, and for those
// the assumption is unnecessary.
//
// This matters beyond wording. A circuit with no feedback must never
// grow a "waiting for confirmation" state, a discrepancy alarm or a
// confirmation timeout: there is no input that could ever satisfy them,
// so every one of those would be an alarm that fires on a perfectly
// healthy installation. circuitFeedbackMode below is what lets the rest
// of the editor tell the two cases apart and say which it is looking
// at, instead of leaving the reader to assume there is a confirmation
// behind a lamp that is simply commanded on.
//
// Pure functions only, no store and no Konva - the same contract every
// other module in this folder keeps.

import type { Device } from './DeviceSchema';
import { normalizeCircuitName } from './CircuitResolver';

/**
 * One circuit's binding. The circuit itself is still just a NAME shared
 * by fixtures (CircuitResolver.ts) - this adds, optionally, which device
 * switches it.
 *
 * Kept as a project-level list rather than a field copied onto every
 * fixture: a circuit has ONE device, and a per-object copy would drift
 * the moment one fixture was edited and its neighbours were not.
 */
export interface CircuitBinding {
  /** The circuit name, as the user typed it. Matching is case- and space-insensitive (normalizeCircuitName). */
  name: string;
  /** A device id from the project's device registry. Absent = the circuit is drawn but not yet wired to anything. */
  deviceId?: string;
}

/** The binding for a circuit, or undefined when it has none. */
export function findBinding(bindings: CircuitBinding[], circuit: string | undefined): CircuitBinding | undefined {
  const key = normalizeCircuitName(circuit);
  if (!key) return undefined;
  return bindings.find(b => normalizeCircuitName(b.name) === key);
}

/**
 * The list with `circuit` bound to `deviceId`, replacing any previous
 * binding for that circuit. An empty deviceId REMOVES the binding
 * rather than storing a blank one, so "not wired yet" has exactly one
 * representation.
 */
export function setBinding(
  bindings: CircuitBinding[],
  circuit: string,
  deviceId: string | undefined
): CircuitBinding[] {
  const key = normalizeCircuitName(circuit);
  if (!key) return bindings;
  const without = bindings.filter(b => normalizeCircuitName(b.name) !== key);
  if (!deviceId) return without;
  return [...without, { name: circuit.trim(), deviceId }];
}

/** Only the devices a circuit may be bound to: a circuit is switched on and off, so only a SWITCHED device can drive one. */
export function switchableDevices(devices: Device[]): Device[] {
  return devices.filter(d => d.behavior === 'SWITCHED');
}

/**
 * The controller OUTPUT that will energise this circuit - the bound
 * device's own command.doClose, e.g. 'ELA1.DO.12'.
 *
 * Null whenever the chain cannot be followed to the end: no binding, a
 * device id that no longer resolves (deleted from the registry), or a
 * device that is not SWITCHED. Never throws and never guesses - an
 * unresolvable binding must read as "not wired", because the alternative
 * is a plan that claims an output it does not have.
 */
export function circuitOutputAddress(
  bindings: CircuitBinding[],
  devices: Device[],
  circuit: string | undefined
): string | null {
  const binding = findBinding(bindings, circuit);
  if (!binding?.deviceId) return null;
  const device = devices.find(d => d.id === binding.deviceId);
  if (!device || device.behavior !== 'SWITCHED') return null;
  return device.command?.doClose ?? null;
}

/** The device bound to a circuit, or null - same "cannot follow the chain" rules as circuitOutputAddress. */
export function circuitDevice(
  bindings: CircuitBinding[],
  devices: Device[],
  circuit: string | undefined
): Device | null {
  const binding = findBinding(bindings, circuit);
  if (!binding?.deviceId) return null;
  return devices.find(d => d.id === binding.deviceId) ?? null;
}

/**
 * How a circuit's real state can be known, or null when it has no device
 * behind it at all.
 *
 *   'NONE'   - nothing is read back. The state shown is ASSUMED from the
 *              command the moment it is issued. Normal, and correct, for
 *              lighting on a plain DO.
 *   'SINGLE' - one auxiliary contact confirms the closed position.
 *   'DUAL'   - separate contacts confirm both positions.
 */
export function circuitFeedbackMode(
  bindings: CircuitBinding[],
  devices: Device[],
  circuit: string | undefined
): 'NONE' | 'SINGLE' | 'DUAL' | null {
  const device = circuitDevice(bindings, devices, circuit);
  if (!device || device.behavior !== 'SWITCHED') return null;
  return device.feedback?.mode ?? 'NONE';
}

/** Whether what the plan shows for this circuit is an ASSUMPTION from the command rather than something read back. True for an unbound circuit too - nothing at all is confirming that one. */
export function circuitStateIsAssumed(
  bindings: CircuitBinding[],
  devices: Device[],
  circuit: string | undefined
): boolean {
  const mode = circuitFeedbackMode(bindings, devices, circuit);
  return mode === null || mode === 'NONE';
}

/** A short human phrase for how a circuit is confirmed - or that it is not. */
export function describeCircuitFeedback(
  bindings: CircuitBinding[],
  devices: Device[],
  circuit: string | undefined
): string {
  const device = circuitDevice(bindings, devices, circuit);
  if (!device || device.behavior !== 'SWITCHED') return 'no device';
  const feedback = device.feedback;
  switch (feedback?.mode) {
    case 'DUAL':
      return `DI: ${feedback.diClosed ?? '?'} / ${feedback.diOpen ?? '?'}`;
    case 'SINGLE':
      return `DI: ${feedback.diClosed ?? '?'}`;
    default:
      // Not a gap to fill in later - the normal case for lighting.
      return 'none - state assumed from DO';
  }
}

/**
 * A short human label for a binding, for the property panel and the
 * schedule: the device's designation and its output, or a plain "not
 * wired" when there is nothing to show.
 */
export function describeCircuitBinding(
  bindings: CircuitBinding[],
  devices: Device[],
  circuit: string | undefined
): string {
  const device = circuitDevice(bindings, devices, circuit);
  if (!device) return 'not bound';
  const address = circuitOutputAddress(bindings, devices, circuit);
  const designation = device.designation || device.id;
  return address ? `${designation} -> ${address}` : `${designation} (no output)`;
}
