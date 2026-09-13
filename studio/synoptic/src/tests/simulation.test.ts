// feat/workspace: simulation - the plan operated the way a controller
// operates it.
//
// Two things are worth pinning here, and they are not the UI. First,
// that a command in simulation NEVER moves the drawing before it is
// confirmed: that is the whole difference from Podglad mode, and a
// regression in it would turn a confirmation dialog into decoration.
// Second, that the two feedback cases stay different - a circuit with no
// auxiliary contact is assumed from the DO immediately, one with a
// contact is held pending until the contact answers. Collapsing those
// two would teach the wrong thing about the installation being drawn.
//
// The command model (CommandRequest.ts) is pure and checked directly.
// The slice is exercised through the real store, because the ordering
// (nothing happens, THEN it happens) is the claim being made.

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  buildCommandRequest, circuitSwitchUpdates, commandQuestion, commandVerb,
  describeBlock, describeConfirmation, describeOutput, describeUnbound,
} from '../project/CommandRequest';
import { useStore } from '../store';
import type { SynopticObject } from '../store';
import type { Device } from '../project/DeviceSchema';

import commandDialogSource from '../components/CommandDialog.tsx?raw';
import simulationPanelSource from '../components/SimulationPanel.tsx?raw';

const obj = (id: string, type: string, extra: Partial<SynopticObject> = {}): SynopticObject => ({
  id, type, category: 'BUILDING', x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
  visible: true, locked: false, layer: 0, tag: '', description: '',
  color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
  tooltip: '', width: 32, height: 32, customProperties: {},
  ...extra,
});

const device = (overrides: Partial<Device> = {}): Device => ({
  id: 'K1',
  designation: '-K1',
  name: 'Stycznik oswietlenia',
  behavior: 'SWITCHED',
  kind: 'contactor',
  publishToHa: false,
  feedback: { mode: 'NONE' },
  command: { outputCount: 1, style: 'MAINTAINED', doClose: 'ELA1.DO.12' },
  supervision: { confirmTimeoutMs: 5000, discrepancyAlarm: false },
  safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' },
  switchCounter: false,
  ...overrides,
} as Device);

const lamps = () => [
  obj('l1', 'building.luminaire', { circuit: 'OBW_1' }),
  obj('l2', 'building.luminaire', { circuit: 'OBW_1' }),
];

// ---------------------------------------------------------------------
describe('the command a click would issue', () => {
  it('offers the action that is available, and says how many aparats it moves', () => {
    const request = buildCommandRequest(lamps(), [{ name: 'OBW_1', deviceId: 'K1' }], [device()], 'l1')!;
    expect(request.action).toBe('CLOSE');
    expect(request.fixtureCount).toBe(2);
    expect(commandQuestion(request)).toBe('Switch ON circuit OBW_1?');
    expect(commandVerb(request)).toBe('SWITCH ON');
    expect(describeOutput(request)).toContain('ELA1.DO.12');
  });

  it('offers the opposite action once the circuit is on', () => {
    const on = lamps().map(o => ({ ...o, editor: { preview_state: 'ON' } }));
    const request = buildCommandRequest(on, [{ name: 'OBW_1', deviceId: 'K1' }], [device()], 'l1')!;
    expect(request.action).toBe('OPEN');
    expect(commandQuestion(request)).toBe('Switch OFF circuit OBW_1?');
  });

  it('is not a command at all for furniture', () => {
    // Clicking a chair is not a rejected command - it is not a command.
    expect(buildCommandRequest([obj('c1', 'building.chair')], [], [], 'c1')).toBeNull();
  });

  it('still produces a request when the command cannot go out, and says exactly what is missing', () => {
    // "Nothing happened" is the worst answer a control system can give.
    const gone = buildCommandRequest(lamps(), [{ name: 'OBW_1', deviceId: 'nope' }], [device()], 'l1')!;
    expect(gone.blocked).toBe('DEVICE_MISSING');

    const noOutput = buildCommandRequest(
      lamps(), [{ name: 'OBW_1', deviceId: 'K1' }],
      [device({ command: { outputCount: 1, style: 'MAINTAINED', doClose: '' } } as Partial<Device>)],
      'l1'
    )!;
    expect(noOutput.blocked).toBe('NO_OUTPUT');

    for (const block of ['NO_CIRCUIT', 'NO_DEVICE', 'DEVICE_MISSING', 'NOT_SWITCHED', 'NO_OUTPUT', 'NOT_OPERABLE'] as const) {
      expect(describeBlock(block).length).toBeGreaterThan(10);
    }
  });

  it('simulates a fixture with no circuit, or a circuit with no device - and says it is simulated only', () => {
    const noCircuit = buildCommandRequest([obj('l1', 'building.luminaire')], [], [], 'l1')!;
    expect(noCircuit.blocked).toBeNull();
    expect(noCircuit.unbound).toBe('NO_CIRCUIT');
    expect(noCircuit.target).toBe('OBJECT');

    const noDevice = buildCommandRequest(lamps(), [], [], 'l1')!;
    expect(noDevice.blocked).toBeNull();
    expect(noDevice.unbound).toBe('NO_DEVICE');
    expect(describeUnbound(noDevice)).toContain('simulation only');
  });

  it('operates a breaker on the schematic by itself - close / open, not a plan circuit', () => {
    const breaker = obj('q1', 'electrical.circuit_breaker', { category: 'Electrical', editor: { preview_state: 'OPEN' } });
    const request = buildCommandRequest([breaker], [], [], 'q1')!;
    expect(request.target).toBe('OBJECT');
    expect(request.action).toBe('CLOSE');
    expect(commandQuestion(request)).toContain('Close');
    expect(commandVerb(request)).toBe('CLOSE');
    expect(request.unbound).toBe('NO_DEVICE');

    const bound = buildCommandRequest([{ ...breaker, deviceId: 'K1' }], [], [device()], 'q1')!;
    expect(bound.unbound).toBeNull();
    expect(bound.output).toBe('ELA1.DO.12');
  });

  it('quotes the device own command style rather than inventing one', () => {
    const pulsed = buildCommandRequest(
      lamps(), [{ name: 'OBW_1', deviceId: 'K1' }],
      [device({ command: { outputCount: 1, style: 'PULSE', doClose: 'ELA1.DO.12', pulseMs: 400 } } as Partial<Device>)],
      'l1'
    )!;
    expect(pulsed.style).toBe('PULSE');
    expect(pulsed.pulseMs).toBe(400);
    expect(describeOutput(pulsed)).toContain('400 ms');
  });

  it('names the opening output on a two-output device rather than the closing one', () => {
    const on = lamps().map(o => ({ ...o, editor: { preview_state: 'ON' } }));
    const request = buildCommandRequest(
      on, [{ name: 'OBW_1', deviceId: 'K1' }],
      [device({ command: { outputCount: 2, style: 'MAINTAINED', doClose: 'ELA1.DO.12', doOpen: 'ELA1.DO.13' } } as Partial<Device>)],
      'l1'
    )!;
    expect(request.action).toBe('OPEN');
    expect(request.output).toBe('ELA1.DO.13');
  });

  it('states plainly that a circuit with no contact is assumed, and what a contact would mean', () => {
    const assumed = buildCommandRequest(lamps(), [{ name: 'OBW_1', deviceId: 'K1' }], [device()], 'l1')!;
    expect(assumed.assumed).toBe(true);
    expect(describeConfirmation(assumed)).toContain('No feedback');

    const confirmed = buildCommandRequest(
      lamps(), [{ name: 'OBW_1', deviceId: 'K1' }],
      [device({ feedback: { mode: 'SINGLE', diClosed: 'ELA1.DI.4' } } as Partial<Device>)],
      'l1'
    )!;
    expect(confirmed.assumed).toBe(false);
    // The LIMIT quoted is the device's own supervision timeout.
    expect(describeConfirmation(confirmed)).toContain('5000');
  });

  it('switches the plan and the schematic together, in one set of updates', () => {
    const objects = [
      ...lamps(),
      obj('sym1', 'switchgear.contactor', { deviceId: 'K1' }),
    ];
    const updates = circuitSwitchUpdates(objects, [{ name: 'OBW_1', deviceId: 'K1' }], [device()], 'OBW_1', true);
    expect(updates.map(u => u.id).sort()).toEqual(['l1', 'l2', 'sym1']);
    expect(updates.find(u => u.id === 'l1')!.updates.editor!.preview_state).toBe('ON');
    // The schematic symbol speaks the contactor's vocabulary, not the lamp's.
    expect(updates.find(u => u.id === 'sym1')!.updates.editor!.preview_state).toBe('CLOSED');
  });
});

// ---------------------------------------------------------------------
describe('simulation through the store', () => {
  beforeEach(() => {
    useStore.setState({
      objects: lamps(),
      circuits: [{ name: 'OBW_1', deviceId: 'K1' }],
      devices: [device()],
      simulationRunning: false,
      commandRequest: null,
      pendingCircuits: [],
      simulationLog: [],
      isDirty: false,
    });
  });

  it('toggles at once while editing - Podglad is meant to be immediate', () => {
    useStore.getState().operateAt('l1');
    expect(useStore.getState().commandRequest).toBeNull();
    expect(useStore.getState().objects[0].editor?.preview_state).toBe('ON');
  });

  it('asks instead of acting once the simulation is running', () => {
    useStore.getState().startSimulation();
    useStore.getState().operateAt('l1');

    const request = useStore.getState().commandRequest;
    expect(request).not.toBeNull();
    expect(request!.circuit).toBe('OBW_1');
    // NOTHING has moved on the drawing yet. This is the claim.
    expect(useStore.getState().objects.every(o => o.editor?.preview_state !== 'ON')).toBe(true);
  });

  it('acts only on confirmation, and cancelling really does nothing', () => {
    useStore.getState().startSimulation();
    useStore.getState().operateAt('l1');
    useStore.getState().cancelCommand();
    expect(useStore.getState().commandRequest).toBeNull();
    expect(useStore.getState().objects.every(o => o.editor?.preview_state !== 'ON')).toBe(true);

    useStore.getState().operateAt('l1');
    useStore.getState().confirmCommand();
    expect(useStore.getState().objects.every(o => o.editor?.preview_state === 'ON')).toBe(true);
  });

  it('assumes the state from the DO at once when there is no feedback', () => {
    useStore.getState().startSimulation();
    useStore.getState().operateAt('l1');
    useStore.getState().confirmCommand();

    expect(useStore.getState().pendingCircuits).toEqual([]);
    const log = useStore.getState().simulationLog.map(e => e.text).join('\n');
    expect(log).toContain('ELA1.DO.12');
    expect(log).toContain('assumed from DO');
  });

  it('holds a circuit WITH a contact pending until the contact answers', () => {
    vi.useFakeTimers();
    try {
      useStore.setState({ devices: [device({ feedback: { mode: 'SINGLE', diClosed: 'ELA1.DI.4' } } as Partial<Device>)] });
      useStore.getState().startSimulation();
      useStore.getState().operateAt('l1');
      useStore.getState().confirmCommand();

      // The gap is real: the command has gone out, the lamps have not
      // moved, and the circuit is marked as waiting.
      expect(useStore.getState().pendingCircuits).toEqual(['OBW_1']);
      expect(useStore.getState().objects.every(o => o.editor?.preview_state !== 'ON')).toBe(true);

      vi.advanceTimersByTime(1000);

      expect(useStore.getState().pendingCircuits).toEqual([]);
      expect(useStore.getState().objects.every(o => o.editor?.preview_state === 'ON')).toBe(true);
      expect(useStore.getState().simulationLog.map(e => e.text).join('\n')).toContain('confirmed by contact');
    } finally {
      vi.useRealTimers();
    }
  });

  it('journals a refused command instead of ignoring the click', () => {
    // Silent refusal is how an operator ends up pressing the same spot
    // five times.
    useStore.setState({ circuits: [{ name: 'OBW_1', deviceId: 'nope' }] });
    useStore.getState().startSimulation();
    useStore.getState().operateAt('l1');

    expect(useStore.getState().commandRequest!.blocked).toBe('DEVICE_MISSING');
    const refusal = useStore.getState().simulationLog.find(e => e.severity === 'ERROR');
    expect(refusal).toBeDefined();
    expect(refusal!.text).toContain('rejected');
  });

  it('closes an unassigned breaker on confirmation, and journals it as simulated only', () => {
    useStore.setState({
      objects: [obj('q1', 'electrical.circuit_breaker', { editor: { preview_state: 'OPEN' } })],
      circuits: [], devices: [],
    });
    useStore.getState().startSimulation();
    useStore.getState().operateAt('q1');
    expect(useStore.getState().objects[0].editor?.preview_state).toBe('OPEN');

    useStore.getState().confirmCommand();
    expect(useStore.getState().objects[0].editor?.preview_state).toBe('CLOSED');
    expect(useStore.getState().simulationLog.some(e => e.severity === 'WARNING' && e.text.includes('simulation only'))).toBe(true);
  });

  it('puts every state back when the simulation stops - operating is not editing', () => {
    useStore.getState().startSimulation();
    useStore.getState().operateAt('l1');
    useStore.getState().confirmCommand();
    expect(useStore.getState().objects.every(o => o.editor?.preview_state === 'ON')).toBe(true);

    useStore.getState().stopSimulation();
    expect(useStore.getState().objects.every(o => o.editor?.preview_state !== 'ON')).toBe(true);
    // ...and the project is exactly as dirty as it was before.
    expect(useStore.getState().isDirty).toBe(false);
  });

  it('does not let a command that was in flight land after the simulation stopped', () => {
    vi.useFakeTimers();
    try {
      useStore.setState({ devices: [device({ feedback: { mode: 'DUAL', diClosed: 'ELA1.DI.4', diOpen: 'ELA1.DI.5' } } as Partial<Device>)] });
      useStore.getState().startSimulation();
      useStore.getState().operateAt('l1');
      useStore.getState().confirmCommand();
      useStore.getState().stopSimulation();

      vi.advanceTimersByTime(2000);
      expect(useStore.getState().objects.every(o => o.editor?.preview_state !== 'ON')).toBe(true);
    } finally {
      vi.useRealTimers();
    }
  });

  it('forces clicks to operate rather than select when it starts', () => {
    useStore.setState({ previewMode: false });
    useStore.getState().startSimulation();
    expect(useStore.getState().previewMode).toBe(true);
  });

  it('writes no history entry for a command - an afternoon of simulating must not bury undo', () => {
    const before = useStore.getState().history.length;
    useStore.getState().startSimulation();
    useStore.getState().operateAt('l1');
    useStore.getState().confirmCommand();
    expect(useStore.getState().history.length).toBe(before);
  });
});

// ---------------------------------------------------------------------
describe('command window (source scan)', () => {
  it('shows the facts a confirmation needs, not just a question', () => {
    for (const label of ['Device', 'Output', 'Current state', 'Feedback']) {
      expect(commandDialogSource).toContain(label);
    }
  });

  it('opens for a blocked command too, offering only a way out', () => {
    expect(commandDialogSource).toContain('Command rejected');
    expect(commandDialogSource).toContain('CLOSE');
  });

  it('can always be dismissed with Escape', () => {
    expect(commandDialogSource).toContain("e.key === 'Escape'");
  });

  it('keeps an event log beside the circuits', () => {
    expect(simulationPanelSource).toContain('simulationLog');
    expect(simulationPanelSource).toContain('operateAt');
  });
});
