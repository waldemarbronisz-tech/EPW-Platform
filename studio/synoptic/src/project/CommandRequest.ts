// feat/workspace: the command a click would issue - the model behind the
// controller's own "czy zalaczyc?" window.
//
// WHY A CONFIRMATION AT ALL. In Podglad mode a click flips a circuit
// instantly, which is right for drawing: you are checking that the lamp
// you placed lights up. SIMULATION is a different question - it asks
// what the finished installation will do when an operator touches it -
// and on a real controller an operator never touches anything directly.
// They open the device's faceplate, read what it is and what state it is
// in, and confirm. Every command in a SCADA goes through that window,
// because a stray click on a touch panel must not start a gate.
//
// So a simulated click must produce the same window, with the same
// facts on it: which circuit, which aparat, which output, what it will
// do, how it will be confirmed - and, when the command cannot be sent,
// why not, BEFORE anything moves on the drawing.
//
// WHAT MAKES THE CONFIRMATION HONEST. The numbers on the window are the
// device's own (DeviceSchema.ts): MAINTAINED or PULSE and its length,
// the confirmation timeout, the feedback mode. Nothing here is invented
// for the simulation - if a plan simulates differently from how the
// controller will behave, the simulation is worse than not having one.
//
// Feedback, again (CircuitBindings.ts's header has the full argument): a
// lighting circuit on a plain DO has none, so its state is ASSUMED the
// moment the command goes out. That is the normal case, it is said on
// the window in those words, and it must never be dressed up as a
// confirmation that does not exist.
//
// Pure: no store, no timers, no Konva. The slice runs this; this only
// decides what is true.

import type { Device } from './DeviceSchema';
import type { SynopticObject } from '../store/types';
import type { CircuitBinding } from './CircuitBindings';
import { circuitDevice, findBinding } from './CircuitBindings';
import { isCircuitOn, isCircuitOperable, isObjectOn, normalizeCircuitName, objectsInCircuit, setCircuitUpdates } from './CircuitResolver';
import { describeObject } from '../utils/ObjectDisplay';

/** What the command does to the output. The controller's own vocabulary, not the lamp's. */
export type CommandAction = 'CLOSE' | 'OPEN';

/** Why a command cannot be issued at all. Null means it can. */
export type CommandBlock =
  | 'NOT_OPERABLE'   // clicked a chair
  | 'NO_CIRCUIT'     // the fixture belongs to no circuit
  | 'NO_DEVICE'      // the circuit is bound to nothing
  | 'DEVICE_MISSING' // bound to a device that no longer exists
  | 'NOT_SWITCHED'   // bound to something that is not a two-state device
  | 'NO_OUTPUT';     // a SWITCHED device with no DO to close

/**
 * Why a command that CAN be simulated has nothing on the controller to
 * carry it out. The simulation still switches it - a drawing can be tried
 * out before its devices exist - and the window says it is simulated only.
 */
export type CommandUnbound =
  | 'NO_CIRCUIT'       // a fixture with no circuit: only it changes
  | 'NO_DEVICE'        // nothing assigned
  | 'DEVICE_UNUSABLE'; // assigned, but missing / not SWITCHED / no DO

export interface CommandRequest {
  /** CIRCUIT: a named plan circuit switches as one. OBJECT: one apparatus on the schematic (a breaker, a disconnect switch) - or a fixture with no circuit - switches by itself. */
  target: 'CIRCUIT' | 'OBJECT';
  /** The words this apparatus uses for its two states ('ON'/'OFF', 'CLOSED'/'OPEN'). */
  onLabel: string;
  offLabel: string;
  /** Null when a device carries the command. */
  unbound: CommandUnbound | null;
  /** The object that was clicked - what the window is "about", and what to highlight. */
  objectId: string;
  objectLabel: string;
  circuit: string;
  /** How many fixtures this one command will move. An operator switching eight lamps should be told it is eight. */
  fixtureCount: number;
  /** The state the circuit is in NOW, as the plan shows it. */
  currentlyOn: boolean;
  /** What confirming would do. Always the opposite of the current state - a faceplate offers the action that is available. */
  action: CommandAction;
  deviceId: string | null;
  deviceLabel: string;
  /** The physical output, e.g. 'ELA1.DO.12'. Null when the chain does not reach one. */
  output: string | null;
  style: 'MAINTAINED' | 'PULSE' | 'PULSE_TOGGLE';
  pulseMs: number | null;
  feedback: 'NONE' | 'SINGLE' | 'DUAL' | null;
  /** The device's own supervision timeout, in ms. How long the controller would wait for the contact before calling it a failure. */
  confirmTimeoutMs: number;
  /** True when nothing reads the result back, so the shown state follows the command directly. */
  assumed: boolean;
  /** Null when the command can go out. */
  blocked: CommandBlock | null;
}

/** The default a device without its own supervision block would get. Matches DeviceSchema's own usual value rather than being invented here. */
const DEFAULT_CONFIRM_TIMEOUT_MS = 5000;

/**
 * Two-state switching apparatus drawn on a one-line schematic, and the
 * words each uses for its states. Clicking one in simulation switches
 * THAT apparatus (and every other symbol of the same device) - a
 * schematic breaker is not a plan circuit, it is the thing itself.
 */
const SWITCHING_STATES: Record<string, { on: string; off: string }> = {
  'electrical.circuit_breaker': { on: 'CLOSED', off: 'OPEN' },
  'electrical.disconnect_switch': { on: 'CLOSED', off: 'OPEN' },
  'electrical.rcd': { on: 'CLOSED', off: 'OPEN' },
  'scada.load_switch': { on: 'CLOSED', off: 'OPEN' },
  'electrical.contactor': { on: 'ON', off: 'OFF' },
};

/** Whether this type is a switching apparatus a simulated click operates by itself. */
export function isSwitchingSymbol(type: string): boolean {
  return Object.prototype.hasOwnProperty.call(SWITCHING_STATES, type);
}

/** The state words of a switching apparatus, or null for anything else. */
export function switchingLabels(type: string): { on: string; off: string } | null {
  return SWITCHING_STATES[type] ?? null;
}

/** Whether a switching apparatus is closed / on right now. */
export function isSymbolOn(obj: SynopticObject): boolean {
  const states = SWITCHING_STATES[obj.type];
  return !!states && obj.editor?.preview_state === states.on;
}

/** The symbols one switching command moves: the clicked one and every other switching symbol of the same device. */
function switchingGroup(objects: SynopticObject[], target: SynopticObject): SynopticObject[] {
  if (!target.deviceId) return [target];
  return objects.filter(o => o.deviceId === target.deviceId && isSwitchingSymbol(o.type));
}

/** The updates that switch one apparatus (and its device's other symbols) to `on`. Empty for anything that is not a switching apparatus. */
export function symbolSwitchUpdates(
  objects: SynopticObject[],
  objectId: string,
  on: boolean
): { id: string; updates: Partial<SynopticObject> }[] {
  const target = objects.find(o => o.id === objectId);
  if (!target || !isSwitchingSymbol(target.type)) return [];
  return switchingGroup(objects, target).map(o => {
    const states = SWITCHING_STATES[o.type];
    return { id: o.id, updates: { editor: { ...o.editor, preview_state: on ? states.on : states.off } } };
  });
}

function buildSymbolRequest(objects: SynopticObject[], devices: Device[], target: SynopticObject): CommandRequest {
  const states = SWITCHING_STATES[target.type];
  const currentlyOn = isSymbolOn(target);
  const device = target.deviceId ? devices.find(d => d.id === target.deviceId) : undefined;
  const base: CommandRequest = {
    target: 'OBJECT',
    onLabel: states.on,
    offLabel: states.off,
    unbound: target.deviceId ? 'DEVICE_UNUSABLE' : 'NO_DEVICE',
    objectId: target.id,
    objectLabel: describeObject(target),
    circuit: '',
    fixtureCount: switchingGroup(objects, target).length,
    currentlyOn,
    action: currentlyOn ? 'OPEN' : 'CLOSE',
    deviceId: target.deviceId ?? null,
    deviceLabel: device ? labelFor(device) : (target.deviceId ? `${target.deviceId} (missing)` : 'not assigned'),
    output: null,
    style: 'MAINTAINED',
    pulseMs: null,
    feedback: null,
    confirmTimeoutMs: DEFAULT_CONFIRM_TIMEOUT_MS,
    assumed: true,
    blocked: null,
  };
  if (!device || device.behavior !== 'SWITCHED') return base;
  const command = device.command;
  if (!command?.doClose) return base;

  const feedback = device.feedback?.mode ?? 'NONE';
  const request: CommandRequest = {
    ...base,
    unbound: null,
    output: command.doClose,
    style: command.style ?? 'MAINTAINED',
    pulseMs: command.style !== 'MAINTAINED' ? (command.pulseMs ?? null) : null,
    feedback,
    confirmTimeoutMs: device.supervision?.confirmTimeoutMs ?? DEFAULT_CONFIRM_TIMEOUT_MS,
    assumed: feedback === 'NONE',
  };
  if (request.action === 'OPEN' && command.outputCount === 2 && command.doOpen) request.output = command.doOpen;
  return request;
}

/**
 * What clicking this object in simulation would ask for - or, when it is
 * blocked, exactly what is missing.
 *
 * Returns null ONLY for an object that is not a switchable fixture at
 * all (a chair, a table): clicking the furniture is not a rejected
 * command, it is not a command. Everything else returns a request, a
 * blocked one if need be, because "nothing happened" is the single worst
 * answer a control system can give.
 */
export function buildCommandRequest(
  objects: SynopticObject[],
  bindings: CircuitBinding[],
  devices: Device[],
  objectId: string
): CommandRequest | null {
  const target = objects.find(o => o.id === objectId);
  if (!target) return null;
  if (!isCircuitOperable(target.type)) {
    return isSwitchingSymbol(target.type) ? buildSymbolRequest(objects, devices, target) : null;
  }

  const circuit = (target.circuit ?? '').trim();
  const members = objectsInCircuit(objects, circuit);
  const currentlyOn = isCircuitOn(objects, circuit);

  const base = {
    target: 'CIRCUIT' as CommandRequest['target'],
    onLabel: 'ON',
    offLabel: 'OFF',
    unbound: null as CommandUnbound | null,
    objectId,
    objectLabel: describeObject(target),
    circuit,
    fixtureCount: members.length,
    currentlyOn,
    action: (currentlyOn ? 'OPEN' : 'CLOSE') as CommandAction,
    deviceId: null as string | null,
    deviceLabel: '-',
    output: null as string | null,
    style: 'MAINTAINED' as CommandRequest['style'],
    pulseMs: null as number | null,
    feedback: null as CommandRequest['feedback'],
    confirmTimeoutMs: DEFAULT_CONFIRM_TIMEOUT_MS,
    assumed: true,
  };

  if (!normalizeCircuitName(circuit)) {
    // No circuit: the fixture switches by itself, in the simulation only.
    const on = isObjectOn(target);
    return {
      ...base, target: 'OBJECT', circuit: '', fixtureCount: 1, currentlyOn: on,
      action: on ? 'OPEN' : 'CLOSE', unbound: 'NO_CIRCUIT', blocked: null,
    };
  }

  const binding = findBinding(bindings, circuit);
  if (!binding?.deviceId) {
    // A circuit nobody has assigned a device to yet still switches - the
    // window says it is simulated only.
    return { ...base, unbound: 'NO_DEVICE', blocked: null };
  }

  const device = circuitDevice(bindings, devices, circuit);
  if (!device) {
    return { ...base, deviceId: binding.deviceId, blocked: 'DEVICE_MISSING' };
  }
  if (device.behavior !== 'SWITCHED') {
    return {
      ...base,
      deviceId: device.id,
      deviceLabel: labelFor(device),
      blocked: 'NOT_SWITCHED',
    };
  }

  const command = device.command;
  const feedback = device.feedback?.mode ?? 'NONE';
  const resolved: CommandRequest = {
    ...base,
    deviceId: device.id,
    deviceLabel: labelFor(device),
    output: command?.doClose ?? null,
    style: command?.style ?? 'MAINTAINED',
    pulseMs: command && command.style !== 'MAINTAINED' ? (command.pulseMs ?? null) : null,
    feedback,
    confirmTimeoutMs: device.supervision?.confirmTimeoutMs ?? DEFAULT_CONFIRM_TIMEOUT_MS,
    assumed: feedback === 'NONE',
    blocked: command?.doClose ? null : 'NO_OUTPUT',
  };

  // A two-output device opens on its own DO rather than by releasing the
  // close output, and the window should name the one that will actually
  // energise.
  if (resolved.action === 'OPEN' && command?.outputCount === 2 && command.doOpen) {
    resolved.output = command.doOpen;
  }

  return resolved;
}

function labelFor(device: Device): string {
  const designation = device.designation || device.id;
  return device.name ? `${designation} - ${device.name}` : designation;
}

/** The question at the top of the window, in the controller's own phrasing. */
export function commandQuestion(request: CommandRequest): string {
  const what = request.circuit ? `circuit ${request.circuit}` : request.objectLabel;
  if (request.onLabel === 'CLOSED') {
    return request.action === 'CLOSE' ? `Close ${what}?` : `Open ${what}?`;
  }
  return request.action === 'CLOSE' ? `Switch ON ${what}?` : `Switch OFF ${what}?`;
}

/** The verb on the confirm button. */
export function commandVerb(request: CommandRequest): string {
  if (request.onLabel === 'CLOSED') return request.action === 'CLOSE' ? 'CLOSE' : 'OPEN';
  return request.action === 'CLOSE' ? 'SWITCH ON' : 'SWITCH OFF';
}

/** What a command with nothing on the controller to carry it means - said on the window before it goes out. Null when a device carries it. */
export function describeUnbound(request: CommandRequest): string | null {
  switch (request.unbound) {
    case null:
      return null;
    case 'NO_CIRCUIT':
      return 'The device belongs to no circuit - only this one changes, and only in the simulation.';
    case 'NO_DEVICE':
      return request.target === 'CIRCUIT'
        ? 'The circuit has no device assigned - it switches in the simulation only; the controller would have nothing to switch it with.'
        : 'No device is assigned - it switches in the simulation only; the controller would have nothing to operate.';
    case 'DEVICE_UNUSABLE':
      return 'The assigned device cannot carry the command (missing, not a switching device, or no DO output) - switched in the simulation only.';
  }
}

/** Plain Polish for why a blocked command cannot go out - and, where there is one, what to do about it. */
export function describeBlock(block: CommandBlock): string {
  switch (block) {
    case 'NO_CIRCUIT':
      return 'The device belongs to no circuit - give it a circuit name in Properties.';
    case 'NO_DEVICE':
      return 'The circuit has no device assigned - the controller has nothing to switch it with.';
    case 'DEVICE_MISSING':
      return 'The assigned device no longer exists in the project registry.';
    case 'NOT_SWITCHED':
      return 'The assigned device is not a switching device (SWITCHED).';
    case 'NO_OUTPUT':
      return 'The device has no DO output - there is nothing to close.';
    case 'NOT_OPERABLE':
      return 'This element cannot be controlled.';
  }
}

/** How the result will be known, said on the window before the command goes out rather than explained afterwards. */
export function describeConfirmation(request: CommandRequest): string {
  switch (request.feedback) {
    case 'DUAL':
      return `Feedback from two contacts, waiting up to ${request.confirmTimeoutMs} ms.`;
    case 'SINGLE':
      return `Feedback from an auxiliary contact, waiting up to ${request.confirmTimeoutMs} ms.`;
    default:
      // The normal case for lighting, stated as normal.
      return 'No feedback - the state is taken directly from the DO.';
  }
}

/** How the output will be driven. A PULSE command and a MAINTAINED one behave differently enough that the window must say which. */
export function describeOutput(request: CommandRequest): string {
  if (!request.output) return 'no output';
  if (request.style === 'PULSE_TOGGLE') {
    return `${request.output} - pulse ${request.pulseMs ?? '?'} ms on a single-coil impulse relay (toggles)`;
  }
  if (request.style === 'PULSE') {
    return `${request.output} - pulse ${request.pulseMs ?? '?'} ms`;
  }
  return `${request.output} - maintained`;
}

/**
 * Everything that has to change when a circuit is switched - the
 * fixtures on the plan AND every schematic symbol carrying the same
 * aparat.
 *
 * THE PLAN AND THE SCHEMATIC MOVE TOGETHER. Closing a light on the floor
 * plan visibly closes its contactor on the one-line diagram, and
 * NetResolver.ts then energises everything downstream of that contactor
 * by its own existing rules. Without it the two drawings would disagree
 * about the same physical contactor, which is worse than having only one
 * of them.
 *
 * Lifted out of the store so the editor's instant Podglad toggle and the
 * simulation's confirmed command produce byte-for-byte the same result:
 * two code paths that switch a circuit slightly differently is exactly
 * the kind of divergence nobody notices until the two disagree on site.
 */
export function circuitSwitchUpdates(
  objects: SynopticObject[],
  bindings: CircuitBinding[],
  devices: Device[],
  circuit: string | undefined,
  on: boolean
): { id: string; updates: Partial<SynopticObject> }[] {
  const updates = setCircuitUpdates(objects, circuit, on);
  if (updates.length === 0) return updates;

  const device = circuitDevice(bindings, devices, circuit);
  if (!device) return updates;

  const schematicState = on ? 'CLOSED' : 'OPEN';
  for (const obj of objects) {
    if (obj.deviceId !== device.id) continue;
    if (updates.some(u => u.id === obj.id)) continue; // already handled as a fixture
    updates.push({
      id: obj.id,
      updates: { editor: { ...obj.editor, preview_state: schematicState } },
    });
  }
  return updates;
}
