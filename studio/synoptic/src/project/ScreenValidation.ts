// feat/workspace: "kompilacja" - what would stop this screen from being
// handed to a controller.
//
// Drawing a room is not the same as having a working installation, and
// the gap between the two is made of things that are invisible on the
// drawing: a lamp nobody gave a circuit to, a circuit nobody bound to an
// output, a door left floating beside the wall it was meant to sit in. A
// plan with any of those looks finished and is not.
//
// So this is a COMPILER's error list, in the sense that matters: it
// answers "could this be built and run", not "is this pretty". Every
// issue names the one object or circuit it is about, so the panel that
// shows them can select it on the canvas - an error you cannot find is
// only half reported.
//
// SEVERITY IS NOT DECORATION.
//   ERROR   - the controller could not act on this. A luminaire with no
//             circuit, a circuit with no output: there is no command to
//             send.
//   WARNING - it will run, but something is probably not what was meant
//             (two circuits sharing one output, a fixture outside every
//             room).
//   INFO    - worth knowing, wrong to alarm about. Above all: a circuit
//             with no feedback, which is the NORMAL case for lighting on
//             a plain DO (CircuitBindings.ts's own header) and must
//             never be reported as a fault.
//
// Pure: plain arrays in, plain data out. No store, no Konva.

import type { Device } from './DeviceSchema';
import type { SynopticObject } from '../store/types';
import type { WallElement } from '../elements/WallElement';
import type { CircuitBinding } from './CircuitBindings';
import { circuitDevice, circuitFeedbackMode, findBinding } from './CircuitBindings';
import { isCircuitOperable, listCircuits, normalizeCircuitName, objectsInCircuit } from './CircuitResolver';
import { isOpeningType, wallForOpening } from './WallOpenings';
import { openEndPoints } from './WallGeometry';
import { findClosedRooms } from './RoomFloors';
import { pointInPolygon } from './Illuminance';
import { describeObject } from '../utils/ObjectDisplay';

export type IssueSeverity = 'ERROR' | 'WARNING' | 'INFO';

export interface ScreenIssue {
  severity: IssueSeverity;
  /** A stable key for React lists and for de-duplicating repeated reports. */
  code: string;
  message: string;
  /** What to select when the row is clicked, when the issue is about one object. */
  objectId?: string;
  /** The circuit the issue is about, when it is about a circuit rather than an object. */
  circuit?: string;
}

export interface ScreenValidation {
  issues: ScreenIssue[];
  errors: number;
  warnings: number;
  infos: number;
  /** True when nothing would stop this screen being run. Warnings do not spoil it - they are opinions, not blockers. */
  runnable: boolean;
}

/** Everything wrong (and everything merely notable) about one screen. */
export function validateScreen(
  objects: SynopticObject[],
  walls: WallElement[],
  bindings: CircuitBinding[],
  devices: Device[]
): ScreenValidation {
  const issues: ScreenIssue[] = [];

  // --- fixtures without a circuit -----------------------------------
  // The commonest real mistake: the lamp is drawn, looks right, and is
  // wired to nothing at all.
  for (const obj of objects) {
    if (!isCircuitOperable(obj.type)) continue;
    if (normalizeCircuitName(obj.circuit)) continue;
    issues.push({
      severity: 'ERROR',
      code: `no-circuit:${obj.id}`,
      objectId: obj.id,
      message: `${describeObject(obj)}: not assigned to any circuit.`,
    });
  }

  // --- circuits and their devices ------------------------------------
  const deviceUsage = new Map<string, string[]>();

  for (const circuit of listCircuits(objects)) {
    if (!normalizeCircuitName(circuit)) continue;
    const members = objectsInCircuit(objects, circuit);
    if (members.length === 0) continue;

    const binding = findBinding(bindings, circuit);
    const device = circuitDevice(bindings, devices, circuit);

    if (!binding?.deviceId) {
      issues.push({
        severity: 'ERROR',
        code: `circuit-unbound:${circuit}`,
        circuit,
        objectId: members[0].id,
        message: `Circuit ${circuit}: no device assigned - the controller has nothing to switch it with.`,
      });
      continue;
    }

    if (!device) {
      // The device was deleted from the registry after the binding was
      // made. A dangling pointer, not an empty one - worth saying which.
      issues.push({
        severity: 'ERROR',
        code: `circuit-dangling:${circuit}`,
        circuit,
        objectId: members[0].id,
        message: `Circuit ${circuit}: assigned device '${binding.deviceId}' no longer exists in the registry.`,
      });
      continue;
    }

    if (device.behavior !== 'SWITCHED') {
      issues.push({
        severity: 'ERROR',
        code: `circuit-behavior:${circuit}`,
        circuit,
        objectId: members[0].id,
        message: `Circuit ${circuit}: device ${device.designation} has behaviour ${device.behavior}, but a circuit needs SWITCHED.`,
      });
      continue;
    }

    const doClose = device.command?.doClose;
    if (!doClose) {
      issues.push({
        severity: 'ERROR',
        code: `circuit-no-output:${circuit}`,
        circuit,
        objectId: members[0].id,
        message: `Circuit ${circuit}: device ${device.designation} has no DO output (command.doClose).`,
      });
    } else {
      const already = deviceUsage.get(device.id) ?? [];
      deviceUsage.set(device.id, [...already, circuit]);
    }

    // Not a fault. Stated so that a reader of this list knows the state
    // on the plan is ASSUMED for this circuit, rather than assuming
    // there is a confirmation behind it that nobody wired.
    if (circuitFeedbackMode(bindings, devices, circuit) === 'NONE') {
      issues.push({
        severity: 'INFO',
        code: `circuit-assumed:${circuit}`,
        circuit,
        message: `Circuit ${circuit}: no feedback - state assumed from DO (${doClose ?? '?'}). This is normal for lighting.`,
      });
    }
  }

  // Two circuit NAMES on one output can never be switched separately,
  // which is almost always a copied binding rather than an intent.
  for (const [deviceId, circuits] of deviceUsage) {
    if (circuits.length < 2) continue;
    const device = devices.find(d => d.id === deviceId);
    issues.push({
      severity: 'WARNING',
      code: `device-shared:${deviceId}`,
      circuit: circuits[0],
      message: `Device ${device?.designation ?? deviceId} drives several circuits (${circuits.join(', ')}) - they will switch together.`,
    });
  }

  // --- symbols pointing at a device that is gone ---------------------
  const knownDeviceIds = new Set(devices.map(d => d.id));
  for (const obj of objects) {
    if (obj.deviceId && !knownDeviceIds.has(obj.deviceId)) {
      issues.push({
        severity: 'ERROR',
        code: `symbol-dangling:${obj.id}`,
        objectId: obj.id,
        message: `${describeObject(obj)}: points to a device that does not exist: '${obj.deviceId}'.`,
      });
    }
  }

  // --- geometry -------------------------------------------------------
  // A door drawn NEXT to a wall instead of IN it still looks like a door
  // on the drawing; it simply never cuts an opening. Silent, and wrong.
  for (const obj of objects) {
    if (!isOpeningType(obj.type)) continue;
    if (wallForOpening(walls, obj)) continue;
    issues.push({
      severity: 'WARNING',
      code: `opening-loose:${obj.id}`,
      objectId: obj.id,
      message: `${describeObject(obj)}: not set into any wall - it will not cut an opening.`,
    });
  }

  const openEnds = openEndPoints(walls);
  if (openEnds.length > 0) {
    issues.push({
      severity: 'WARNING',
      code: 'walls-open',
      message: `Walls do not close a room (${openEnds.length} open ends) - no floor or lighting calculation will be produced.`,
    });
  }

  // A fixture outside every room is not an error - a lamp over a yard is
  // a real thing - but it is left out of the lighting calculation, and
  // that surprises people.
  const rooms = findClosedRooms(walls);
  if (rooms.length > 0) {
    for (const obj of objects) {
      if (!obj.type.startsWith('building.luminaire')) continue;
      const cx = obj.x + obj.width / 2;
      const cy = obj.y + obj.height / 2;
      if (rooms.some(room => pointInPolygon(room, cx, cy))) continue;
      issues.push({
        severity: 'WARNING',
        code: `fixture-outside:${obj.id}`,
        objectId: obj.id,
        message: `${describeObject(obj)}: outside the room outline - left out of the illuminance calculation.`,
      });
    }
  }

  const errors = issues.filter(i => i.severity === 'ERROR').length;
  const warnings = issues.filter(i => i.severity === 'WARNING').length;
  const infos = issues.filter(i => i.severity === 'INFO').length;
  return { issues, errors, warnings, infos, runnable: errors === 0 };
}

/** A one-line summary for a tab badge or a status bar. */
export function summarizeValidation(validation: ScreenValidation): string {
  if (validation.issues.length === 0) return 'Build check OK';
  const parts: string[] = [];
  if (validation.errors) parts.push(`${validation.errors} err.`);
  if (validation.warnings) parts.push(`${validation.warnings} warn.`);
  if (validation.infos) parts.push(`${validation.infos} info`);
  return parts.join(', ');
}
