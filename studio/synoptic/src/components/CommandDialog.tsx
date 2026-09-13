// feat/workspace: the controller's command window - "czy zalaczyc?".
//
// This is the faceplate an operator sees on a real panel, and it is
// modelled on one rather than on a browser confirm(): the question at
// the top, the facts underneath it, and two buttons that say what they
// do rather than "OK" and "Cancel". The facts are not decoration - they
// are what makes confirming meaningful. An operator who cannot see WHICH
// aparat, WHICH output and HOW MANY fixtures is only being asked to
// click twice instead of once.
//
// Every value on it comes from the device's own configuration
// (project/CommandRequest.ts). Nothing is invented for the simulation.
//
// A BLOCKED COMMAND STILL OPENS THIS WINDOW. Silently ignoring a click
// on an unassigned lamp is how an operator ends up pressing the same
// spot five times; the window opens, says exactly what is missing, and
// offers only "Zamknij". The controller behaves the same way, and the
// refusal is in the event log either way.
//
// Keyboard: Enter confirms an executable command, Escape always cancels.
// A confirmation nobody can dismiss with Escape is a trap.

import React, { useEffect } from 'react';
import { useStore } from '../store';
import {
  commandQuestion, commandVerb, describeBlock, describeConfirmation, describeOutput, describeUnbound,
} from '../project/CommandRequest';
import {
  COLOR_ALARM, COLOR_BEVEL_DARK, COLOR_BEVEL_LIGHT, COLOR_LAMP_LIT, COLOR_OUTLINE,
  COLOR_PANEL, COLOR_RUN, COLOR_VALUE_FIELD, FONT_SIZE_SMALL, FONT_SIZE_TITLE, FONT_UI, VENTILATION_ACTIVE,
} from '../theme/ScadaTheme';

const backdropStyle: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  // Dimmed, not blacked out: an operator confirming a command should
  // still see the plan the command is about.
  background: 'rgba(0,0,0,0.35)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 200,
  fontFamily: FONT_UI,
};

const windowStyle: React.CSSProperties = {
  minWidth: 380,
  maxWidth: 520,
  background: COLOR_PANEL,
  border: `2px solid ${COLOR_OUTLINE}`,
  borderTopColor: COLOR_BEVEL_LIGHT,
  borderLeftColor: COLOR_BEVEL_LIGHT,
  boxShadow: '4px 4px 12px rgba(0,0,0,0.5)',
  color: COLOR_OUTLINE,
};

const titleBarStyle: React.CSSProperties = {
  background: COLOR_OUTLINE,
  color: COLOR_BEVEL_LIGHT,
  padding: '3px 8px',
  fontSize: FONT_SIZE_SMALL,
  fontWeight: 'bold',
  letterSpacing: 0.5,
};

const rowStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 12,
  padding: '2px 0',
  fontSize: FONT_SIZE_SMALL,
};

const valueStyle: React.CSSProperties = {
  background: COLOR_VALUE_FIELD,
  border: `1px solid ${COLOR_BEVEL_DARK}`,
  padding: '0 4px',
  fontFamily: 'Consolas, "DejaVu Sans Mono", monospace',
  textAlign: 'right',
  minWidth: 150,
};

export const CommandDialog: React.FC = () => {
  const request = useStore(s => s.commandRequest);
  const confirmCommand = useStore(s => s.confirmCommand);
  const cancelCommand = useStore(s => s.cancelCommand);

  // Registered unconditionally, gated inside - a hook must not depend on
  // whether the dialog happens to be open this render.
  useEffect(() => {
    if (!request) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        cancelCommand();
      } else if (e.key === 'Enter' && !request.blocked) {
        e.preventDefault();
        confirmCommand();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [request, confirmCommand, cancelCommand]);

  if (!request) return null;

  const executable = !request.blocked;
  const turningOn = request.action === 'CLOSE';

  return (
    <div style={backdropStyle} onMouseDown={cancelCommand}>
      <div style={windowStyle} onMouseDown={e => e.stopPropagation()}>
        <div style={titleBarStyle}>
          CONTROL - {request.circuit || request.objectLabel}
        </div>

        <div style={{ padding: 10 }}>
          <div style={{ fontSize: FONT_SIZE_TITLE, fontWeight: 'bold', marginBottom: 8 }}>
            {executable ? commandQuestion(request) : 'Command rejected'}
          </div>

          {!executable && (
            <div
              style={{
                background: COLOR_VALUE_FIELD,
                border: `1px solid ${COLOR_ALARM}`,
                borderLeft: `4px solid ${COLOR_ALARM}`,
                padding: 6,
                marginBottom: 8,
                fontSize: FONT_SIZE_SMALL,
              }}
            >
              {describeBlock(request.blocked!)}
            </div>
          )}

          {/* Nothing on the controller would carry this out: it still
              switches, so the drawing can be tried, but never looks like
              a real command. */}
          {executable && request.unbound && (
            <div
              style={{
                background: COLOR_VALUE_FIELD,
                border: `1px solid ${VENTILATION_ACTIVE}`,
                borderLeft: `4px solid ${VENTILATION_ACTIVE}`,
                padding: 6,
                marginBottom: 8,
                fontSize: FONT_SIZE_SMALL,
              }}
            >
              {describeUnbound(request)}
            </div>
          )}

          <div style={rowStyle}>
            <span>Device</span><span style={valueStyle}>{request.deviceLabel}</span>
          </div>
          <div style={rowStyle}>
            <span>Output</span><span style={valueStyle}>{describeOutput(request)}</span>
          </div>
          <div style={rowStyle}>
            <span>Current state</span>
            <span style={{ ...valueStyle, fontWeight: 'bold', color: request.currentlyOn ? COLOR_RUN : COLOR_OUTLINE }}>
              {request.currentlyOn ? request.onLabel : request.offLabel}
            </span>
          </div>
          {executable && (
            <div style={rowStyle}>
              <span>State after command</span>
              <span style={{ ...valueStyle, fontWeight: 'bold', color: turningOn ? COLOR_RUN : COLOR_OUTLINE }}>
                {turningOn ? request.onLabel : request.offLabel}
              </span>
            </div>
          )}
          <div style={rowStyle}>
            <span>Devices affected</span>
            <span style={valueStyle}>{request.fixtureCount} pcs</span>
          </div>
          <div style={rowStyle}>
            <span>Feedback</span><span style={valueStyle}>{describeConfirmation(request)}</span>
          </div>

          {/* Said before the command, not explained after it: with no
              auxiliary contact the lamp is shown lit because the output
              closed, not because anything reported back. That is correct
              for lighting - and an operator should know which of the two
              they are looking at. */}
          {executable && request.assumed && !request.unbound && (
            <div
              style={{
                marginTop: 8,
                padding: 6,
                background: COLOR_VALUE_FIELD,
                borderLeft: `4px solid ${COLOR_LAMP_LIT}`,
                fontSize: FONT_SIZE_SMALL,
              }}
            >
              This circuit has no feedback signal. Once executed, the state shown
              is assumed from the closed DO.
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 12 }}>
            {executable && (
              <button
                autoFocus
                onClick={confirmCommand}
                style={{ padding: '4px 16px', fontWeight: 'bold', minWidth: 110 }}
                title="Execute the command (Enter)"
              >
                {commandVerb(request)}
              </button>
            )}
            <button
              onClick={cancelCommand}
              autoFocus={!executable}
              style={{ padding: '4px 16px', minWidth: 110 }}
              title="Close without executing (Esc)"
            >
              {executable ? 'CANCEL' : 'CLOSE'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
