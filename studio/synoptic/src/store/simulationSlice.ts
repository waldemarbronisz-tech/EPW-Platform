import type { StateCreator } from 'zustand';
import type { AppState } from './appState';
import type { SynopticObject } from './types';
import {
  buildCommandRequest, circuitSwitchUpdates, commandVerb, describeBlock, describeUnbound,
  isSwitchingSymbol, isSymbolOn, symbolSwitchUpdates,
} from '../project/CommandRequest';
import type { CommandRequest } from '../project/CommandRequest';
import { isCircuitOn, isObjectOn, normalizeCircuitName, setObjectUpdates } from '../project/CircuitResolver';

// feat/workspace: simulation - the plan operated the way the controller
// will operate it, rather than the way a drawing is edited.
//
// THE DIFFERENCE FROM PODGLAD. Podglad mode flips a circuit on click:
// instant, no questions, right for checking that the lamp you just
// placed lights up. Simulation asks a different question - what will an
// operator's touch actually do - and on a real controller a touch never
// does anything directly. It opens the aparat's own window, which states
// what it is, what state it is in, which output will energise and how
// the result will be known, and waits to be confirmed. A stray finger on
// a touch panel must not start a gate.
//
// So in simulation every click raises a commandRequest and stops there.
// Nothing on the drawing moves until confirmCommand.
//
// WAITING IS PART OF IT. A circuit whose aparat has an auxiliary contact
// is NOT on the moment the command goes out - the controller holds it
// pending until the contact answers. That gap is real, it is where
// discrepancy alarms come from, and a simulation that skipped it would
// teach the wrong thing. A circuit with NO feedback (a lamp on a plain
// DO - the normal case, CircuitBindings.ts's header) has no gap at all:
// the state is assumed from the command, immediately, and the log says
// so in those words.
//
// SIMULATION DOES NOT EDIT THE PROJECT. Operating a plan is not drawing
// it: the states every command leaves behind are captured at start and
// PUT BACK at stop, along with the dirty flag, and no command writes a
// history entry. Otherwise an afternoon of simulating would bury the
// undo stack and leave the saved file full of lamps someone left on.

/** One line in the simulation's own event log - the controller's journal, not the editor's message panel. */
export interface SimulationEvent {
  id: string;
  /** Wall-clock HH:MM:SS, as an operator's log shows it. */
  time: string;
  severity: 'INFO' | 'WARNING' | 'ERROR';
  text: string;
}

export type SimulationSlice = Pick<AppState,
  | 'simulationRunning' | 'commandRequest' | 'pendingCircuits' | 'simulationLog'
  | 'startSimulation' | 'stopSimulation' | 'operateAt'
  | 'confirmCommand' | 'cancelCommand' | 'clearSimulationLog'
>;

/**
 * How long a healthy aparat takes to answer, in the simulation.
 *
 * NOT the device's own confirmTimeoutMs: that is the LIMIT past which
 * the controller declares a failure (often seconds), and sitting through
 * it on every command would make the simulation unusable. A real
 * contactor's auxiliary contact answers in a fraction of a second, which
 * is what this models - the device's real timeout is still what the
 * command window quotes as the limit.
 */
const SIMULATED_FEEDBACK_MS = 450;

/** Pending confirmation timers, by circuit key. Module-level rather than in the store: a timer handle is not state anyone can render, and keeping it out means the store stays plain data. */
const feedbackTimers = new Map<string, ReturnType<typeof setTimeout>>();

function clearAllTimers(): void {
  for (const timer of feedbackTimers.values()) clearTimeout(timer);
  feedbackTimers.clear();
}

function stamp(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
}

/** The log is a rolling window: a long session must not grow without bound, and nobody reads the thousandth-newest event. */
const MAX_LOG = 200;

let eventSeq = 0;

/** What stopSimulation puts back. Module-level for the same reason the timers are: it is a scratch copy, not state anything renders. */
let simulationRestore: { states: Record<string, string | undefined>; wasDirty: boolean } | null = null;

export const createSimulationSlice: StateCreator<AppState, [], [], SimulationSlice> = (set, get) => {
  /** Append one event. Kept local rather than exposed: everything that writes the log is in this file, and a log anything could write to would stop being a record of what the controller did. */
  const log = (severity: SimulationEvent['severity'], text: string) => {
    set((state) => ({
      simulationLog: [
        ...state.simulationLog.slice(-(MAX_LOG - 1)),
        { id: `ev${++eventSeq}`, time: stamp(), severity, text },
      ],
    }));
  };

  /** Apply a command to the drawing, with no history entry: a whole circuit (plan and schematic together, project/CommandRequest.ts), or one apparatus / one fixture. */
  const applyRequest = (request: CommandRequest, on: boolean) => {
    const { objects, circuits, devices } = get();
    let updates: { id: string; updates: Partial<SynopticObject> }[];
    if (request.target === 'CIRCUIT') {
      updates = circuitSwitchUpdates(objects, circuits, devices, request.circuit, on);
    } else {
      const target = objects.find(o => o.id === request.objectId);
      if (!target) return;
      updates = isSwitchingSymbol(target.type)
        ? symbolSwitchUpdates(objects, target.id, on)
        : setObjectUpdates(target, on);
    }
    if (updates.length > 0) get().updateObjects(updates);
  };

  /** What a pending command is keyed by: the circuit, or the one object. */
  const requestKey = (request: CommandRequest) =>
    request.target === 'CIRCUIT' ? normalizeCircuitName(request.circuit) : `OBJ:${request.objectId}`;

  /** How the log names what a command acts on. */
  const nameOf = (request: CommandRequest) =>
    request.target === 'CIRCUIT' ? `Circuit ${request.circuit}` : request.objectLabel;

  /** Whether what a command acts on is on now. */
  const requestIsOn = (request: CommandRequest) => {
    const objects = get().objects;
    if (request.target === 'CIRCUIT') return isCircuitOn(objects, request.circuit);
    const target = objects.find(o => o.id === request.objectId);
    if (!target) return false;
    return isSwitchingSymbol(target.type) ? isSymbolOn(target) : isObjectOn(target);
  };

  return {
    simulationRunning: false,
    commandRequest: null,
    pendingCircuits: [],
    simulationLog: [],

    startSimulation: () => {
      if (get().simulationRunning) return;
      const state = get();
      // The states to put back at stop. Only preview_state is captured:
      // it is the only thing a command ever changes, and capturing whole
      // objects would restore edits made DURING the simulation too.
      const restore: Record<string, string | undefined> = {};
      for (const obj of state.objects) restore[obj.id] = obj.editor?.preview_state;
      simulationRestore = { states: restore, wasDirty: state.isDirty };

      set({ simulationRunning: true, commandRequest: null, pendingCircuits: [] });
      // Clicks must operate rather than select - the same reason Podglad
      // disarms every drawing tool (toolsSlice.ts).
      get().setPreviewMode(true);
      log('INFO', 'Simulation started. Clicking a device opens its control window.');
    },

    stopSimulation: () => {
      if (!get().simulationRunning) return;
      clearAllTimers();

      const snapshot = simulationRestore;
      if (snapshot) {
        const updates = get().objects
          .filter(obj => Object.prototype.hasOwnProperty.call(snapshot.states, obj.id))
          .filter(obj => obj.editor?.preview_state !== snapshot.states[obj.id])
          .map(obj => ({
            id: obj.id,
            updates: { editor: { ...obj.editor, preview_state: snapshot.states[obj.id] } },
          }));
        if (updates.length > 0) get().updateObjects(updates);
        // Restored, so the project is exactly as dirty as it was before -
        // simulating is not editing.
        set({ isDirty: snapshot.wasDirty });
      }
      simulationRestore = null;

      set({ simulationRunning: false, commandRequest: null, pendingCircuits: [] });
      log('INFO', 'Simulation stopped. States restored to what they were before it started.');
    },

    // The ONE place a click on a fixture is turned into something
    // happening - so Canvas and every screen view behave identically
    // without either of them knowing the simulation exists.
    operateAt: (objectId) => {
      const state = get();
      if (!state.simulationRunning) {
        state.toggleCircuitAt(objectId);
        return;
      }

      const request = buildCommandRequest(state.objects, state.circuits, state.devices, objectId);
      // Null means furniture: not a rejected command, not a command.
      if (!request) return;

      if (state.pendingCircuits.includes(requestKey(request))) {
        log('WARNING', `${nameOf(request)}: previous command not confirmed yet - ignored.`);
        return;
      }

      // A real controller journals a command it refuses, at the moment it
      // refuses it. Silent refusal is how an operator ends up pressing
      // the same button five times.
      if (request.blocked) {
        log('ERROR', `Command rejected - ${request.objectLabel}: ${describeBlock(request.blocked)}`);
      }
      set({ commandRequest: request });
    },

    cancelCommand: () => {
      const request = get().commandRequest;
      if (request && !request.blocked) {
        log('INFO', `Command ${commandVerb(request)} ${request.circuit || request.objectLabel} cancelled by the operator.`);
      }
      set({ commandRequest: null });
    },

    confirmCommand: () => {
      const request = get().commandRequest;
      set({ commandRequest: null });
      if (!request || request.blocked) return;

      const on = request.action === 'CLOSE';
      const key = requestKey(request);
      const name = nameOf(request);
      const stateWord = on ? request.onLabel : request.offLabel;

      if (request.unbound) {
        // Nothing on the controller would carry this out. Switched anyway,
        // so the drawing can be tried - and journalled as simulated only.
        applyRequest(request, on);
        log('WARNING', `${commandVerb(request)} ${request.circuit || request.objectLabel}: ${describeUnbound(request)} State ${stateWord}.`);
        return;
      }

      const pulse = request.style === 'PULSE' ? ` pulse ${request.pulseMs ?? '?'} ms` : '';
      log('INFO',
        `${commandVerb(request)} ${request.circuit || request.objectLabel} -> ${request.output ?? 'no output'}${pulse}` +
        ` (${request.deviceLabel}).`);

      if (request.assumed) {
        // No contact to wait for. Immediate, and correct - not a
        // shortcut, see CircuitBindings.ts.
        applyRequest(request, on);
        log('INFO',
          `${name}: state ${stateWord} - assumed from DO` +
          `, ${request.fixtureCount} ${request.fixtureCount === 1 ? 'device' : 'devices'}.`);
        return;
      }

      // There IS a contact, so it is not there yet.
      set((s) => ({ pendingCircuits: [...s.pendingCircuits.filter(c => c !== key), key] }));
      log('INFO', `${name}: waiting for feedback (limit ${request.confirmTimeoutMs} ms).`);

      const existing = feedbackTimers.get(key);
      if (existing) clearTimeout(existing);
      feedbackTimers.set(key, setTimeout(() => {
        feedbackTimers.delete(key);
        // Stopping the simulation while a command was in flight must not
        // let the command land afterwards.
        if (!get().simulationRunning) return;
        applyRequest(request, on);
        set((s) => ({ pendingCircuits: s.pendingCircuits.filter(c => c !== key) }));
        const confirmed = requestIsOn(request) === on;
        log(confirmed ? 'INFO' : 'ERROR',
          confirmed
            ? `${name}: confirmed by contact - state ${stateWord}.`
            : `${name}: no feedback within ${request.confirmTimeoutMs} ms - discrepancy.`);
      }, SIMULATED_FEEDBACK_MS));
    },

    clearSimulationLog: () => set({ simulationLog: [] }),
  };
};
