// feat/workspace: "Symulacja" - the operator's station for this screen.
//
// Two halves, and both are needed. On the left the circuits, each with
// its state, its output and a button - because an operator's panel lists
// what can be operated, and because a circuit whose fixtures are off the
// visible part of the plan still has to be reachable. On the right the
// EVENT LOG, which is the half people forget: a control system that
// switches things without writing down what it switched, when, and
// whether it was confirmed, is not a control system. Every command,
// every refusal and every confirmation lands there with a timestamp.
//
// Clicking a circuit here goes through exactly the same command window
// as clicking the lamp on the plan (store/simulationSlice.ts) - one
// path, so the confirmation can never be skipped by using the other
// route.
//
// Simulation is non-destructive by construction: stopping it restores
// every state it changed, which is why the button says so.

import React, { useEffect, useMemo, useRef } from 'react';
import { useStore } from '../store';
import { listCircuits, isCircuitOn, normalizeCircuitName, objectsInCircuit } from '../project/CircuitResolver';
import { circuitOutputAddress, describeCircuitBinding, describeCircuitFeedback } from '../project/CircuitBindings';
import { isSwitchingSymbol, isSymbolOn, switchingLabels } from '../project/CommandRequest';
import { describeObject } from '../utils/ObjectDisplay';
import {
  COLOR_ALARM, COLOR_BEVEL_DARK, COLOR_LAMP_LIT, COLOR_OUTLINE,
  COLOR_PANEL, COLOR_RUN, COLOR_VALUE_FIELD, FONT_SIZE_SMALL, FONT_UI, VENTILATION_ACTIVE,
} from '../theme/ScadaTheme';

const SEVERITY_COLOR: Record<string, string> = {
  INFO: COLOR_OUTLINE,
  WARNING: VENTILATION_ACTIVE,
  ERROR: COLOR_ALARM,
};

export const SimulationPanel: React.FC = () => {
  const objects = useStore(s => s.objects);
  const circuits = useStore(s => s.circuits);
  const devices = useStore(s => s.devices);
  const running = useStore(s => s.simulationRunning);
  const pending = useStore(s => s.pendingCircuits);
  const log = useStore(s => s.simulationLog);
  const startSimulation = useStore(s => s.startSimulation);
  const stopSimulation = useStore(s => s.stopSimulation);
  const operateAt = useStore(s => s.operateAt);
  const clearSimulationLog = useStore(s => s.clearSimulationLog);

  const rows = useMemo(() => listCircuits(objects)
    .filter(name => normalizeCircuitName(name))
    .map(name => {
      const members = objectsInCircuit(objects, name);
      return {
        name,
        count: members.length,
        // The object a command on this row acts through. Any member
        // would do - the circuit switches as one - so the first is as
        // good a representative as any.
        anchorId: members[0]?.id ?? null,
        on: isCircuitOn(objects, name),
        output: circuitOutputAddress(circuits, devices, name),
        binding: describeCircuitBinding(circuits, devices, name),
        feedback: describeCircuitFeedback(circuits, devices, name),
        pending: pending.includes(normalizeCircuitName(name)),
      };
    }), [objects, circuits, devices, pending]);

  // The switching apparatus on the schematic - breakers, disconnect
  // switches - each operable by itself, bound to a device or not.
  const switches = useMemo(() => objects
    .filter(o => isSwitchingSymbol(o.type))
    .map(o => {
      const device = o.deviceId ? devices.find(d => d.id === o.deviceId) : undefined;
      const labels = switchingLabels(o.type) ?? { on: 'ON', off: 'OFF' };
      return {
        id: o.id,
        name: describeObject(o),
        on: isSymbolOn(o),
        labels,
        output: device?.behavior === 'SWITCHED' ? (device.command?.doClose ?? null) : null,
        binding: device
          ? `${device.designation || device.id}${device.name ? ` - ${device.name}` : ''}`
          : 'no device assigned - simulated only',
        pending: pending.includes(`OBJ:${o.id}`),
      };
    }), [objects, devices, pending]);

  // The log reads newest-last, like a controller's journal, so it has to
  // follow itself down as events arrive - otherwise the one line you
  // wanted is always just below the fold.
  const logRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = logRef.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [log.length]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', fontFamily: FONT_UI, fontSize: FONT_SIZE_SMALL }}>
      <div
        style={{
          display: 'flex', alignItems: 'center', gap: 10, padding: '3px 8px',
          background: COLOR_PANEL, borderBottom: `1px solid ${COLOR_BEVEL_DARK}`,
        }}
      >
        <button
          onClick={running ? stopSimulation : startSimulation}
          style={{ padding: '2px 12px', fontWeight: 'bold', minWidth: 96 }}
          title={running
            ? 'Stop the simulation and restore the states from before it started'
            : 'Start the simulation - clicking a device will open its control window'}
        >
          {running ? 'STOP' : 'START'}
        </button>
        <span style={{ fontWeight: 'bold', color: running ? COLOR_RUN : COLOR_BEVEL_DARK }}>
          {running ? 'SIMULATION RUNNING' : 'SIMULATION STOPPED'}
        </span>
        <span style={{ opacity: 0.8 }}>
          {running
            ? 'Clicking a device opens its control window.'
            : 'Once started, clicking a device asks for confirmation, as on the controller.'}
        </span>
        <span style={{ flex: 1 }} />
        <button onClick={clearSimulationLog} style={{ padding: '0 8px' }} title="Clear the event log">
          Clear log
        </button>
      </div>

      <div style={{ flex: 1, minHeight: 0, display: 'flex' }}>
        {/* --- circuits ------------------------------------------------ */}
        <div style={{ flex: '1 1 55%', minWidth: 0, overflowY: 'auto', background: COLOR_VALUE_FIELD }}>
          {rows.length === 0 && switches.length === 0 && (
            <div style={{ padding: 10, opacity: 0.8 }}>
              There is nothing to operate on this screen yet - place a switch, a breaker or a luminaire.
            </div>
          )}
          {rows.map(row => (
            <div
              key={row.name}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '2px 8px', borderBottom: `1px solid ${COLOR_PANEL}`,
              }}
            >
              {/* The state lamp, drawn as a lamp: a filled disc, because
                  that is what it is on every panel this editor imitates. */}
              <span
                style={{
                  width: 12, height: 12, borderRadius: '50%',
                  border: `1px solid ${COLOR_OUTLINE}`,
                  background: row.pending ? VENTILATION_ACTIVE : (row.on ? COLOR_LAMP_LIT : COLOR_BEVEL_DARK),
                  flex: '0 0 auto',
                }}
                title={row.pending ? 'Waiting for feedback' : (row.on ? 'On' : 'Off')}
              />
              <span style={{ fontWeight: 'bold', minWidth: 90 }}>{row.name}</span>
              <span style={{ minWidth: 40, opacity: 0.85 }}>{row.count} pcs</span>
              <span
                style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                title={`${row.binding} | Feedback: ${row.feedback}`}
              >
                {row.output ?? row.binding}
              </span>
              <button
                disabled={!running || !row.anchorId || row.pending}
                onClick={() => { if (row.anchorId) operateAt(row.anchorId); }}
                style={{ padding: '0 10px', minWidth: 84 }}
                title={running
                  ? 'Open the control window for this circuit'
                  : 'Start the simulation first'}
              >
                {row.pending ? 'pending...' : (row.on ? 'SWITCH OFF' : 'SWITCH ON')}
              </button>
            </div>
          ))}
          {switches.map(row => (
            <div
              key={row.id}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '2px 8px', borderBottom: `1px solid ${COLOR_PANEL}`,
              }}
            >
              <span
                style={{
                  width: 12, height: 12, borderRadius: '50%',
                  border: `1px solid ${COLOR_OUTLINE}`,
                  background: row.pending ? VENTILATION_ACTIVE : (row.on ? COLOR_LAMP_LIT : COLOR_BEVEL_DARK),
                  flex: '0 0 auto',
                }}
                title={row.pending ? 'Waiting for feedback' : (row.on ? row.labels.on : row.labels.off)}
              />
              <span style={{ fontWeight: 'bold', minWidth: 90 }}>{row.name}</span>
              <span style={{ minWidth: 40, opacity: 0.85 }}>{row.on ? row.labels.on : row.labels.off}</span>
              <span
                style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                title={row.binding}
              >
                {row.output ?? row.binding}
              </span>
              <button
                disabled={!running || row.pending}
                onClick={() => operateAt(row.id)}
                style={{ padding: '0 10px', minWidth: 84 }}
                title={running ? 'Open the control window for this device' : 'Start the simulation first'}
              >
                {row.pending
                  ? 'pending...'
                  : row.on
                    ? (row.labels.off === 'OPEN' ? 'OPEN' : 'SWITCH OFF')
                    : (row.labels.on === 'CLOSED' ? 'CLOSE' : 'SWITCH ON')}
              </button>
            </div>
          ))}
        </div>

        {/* --- event log ----------------------------------------------- */}
        <div
          ref={logRef}
          style={{
            flex: '1 1 45%', minWidth: 0, overflowY: 'auto',
            // Light, like every other panel of the editor - a black
            // terminal here read as a broken, black screen.
            background: COLOR_VALUE_FIELD, color: COLOR_OUTLINE,
            borderLeft: `1px solid ${COLOR_BEVEL_DARK}`,
            fontFamily: 'Consolas, "DejaVu Sans Mono", monospace',
            padding: '2px 6px',
          }}
        >
          {log.length === 0 && (
            <div style={{ opacity: 0.6 }}>The event log is empty.</div>
          )}
          {log.map(event => (
            <div key={event.id} style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              <span style={{ opacity: 0.7 }}>{event.time} </span>
              <span style={{ color: SEVERITY_COLOR[event.severity] }}>
                {event.text}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
