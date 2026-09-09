// SCADA-style symbol 1/9: controllable two-state switch (a load switch /
// contactor, matching a digital output channel). Canvas 150x150, ports at
// (75,0) top / (75,150) bottom / (0,75) left / (150,75) right, though this
// symbol only draws on the vertical (top/bottom) axis.

import React from 'react';
import { Circle, Group, Line } from 'react-konva';
import {
  COLOR_ALARM,
  COLOR_DE_ENERGIZED,
  COLOR_ENERGIZED,
  COLOR_OUTLINE,
  COLOR_WHITE,
  CONDUCTOR_OUTLINE,
  CONDUCTOR_WIDTH,
  SYMBOL_STROKE
} from '../../theme/ScadaTheme';

export type LoadSwitchState = 'CLOSED' | 'OPEN' | 'FAULT';
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this state list belongs beside its component.
export const LOAD_SWITCH_STATES: LoadSwitchState[] = ['CLOSED', 'OPEN', 'FAULT'];

/** Top segment (75,0)-(75,52) is the incoming feed - always energized. */
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this helper belongs beside its component.
export function getLoadSwitchTopConductorColor(): string {
  return COLOR_ENERGIZED;
}

/**
 * Bottom segment (75,98)-(75,150) is energized only when the switch is
 * CLOSED. OPEN and FAULT are both "not reliably closed", so both read as
 * de-energized - the task's own wording ("pod napieciem tylko gdy
 * zamkniety") settles FAULT's case without needing a separate rule.
 */
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this helper belongs beside its component.
export function getLoadSwitchBottomConductorColor(state: LoadSwitchState): string {
  return state === 'CLOSED' ? COLOR_ENERGIZED : COLOR_DE_ENERGIZED;
}

// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this helper belongs beside its component.
export function getLoadSwitchBladeColor(state: LoadSwitchState): string {
  return state === 'FAULT' ? COLOR_ALARM : COLOR_OUTLINE;
}

/**
 * The task defines a blade shape for CLOSED and one for OPEN, but not a
 * distinct one for FAULT - only its color (alarm red). FAULT is drawn
 * using the OPEN blade position: a discrepancy/fault reads as "not
 * reliably closed", consistent with the bottom-conductor rule above.
 * (Interpretation decision - the task text does not resolve this itself.)
 */
function getLoadSwitchBladeEnd(state: LoadSwitchState): { x: number; y: number } {
  return state === 'CLOSED' ? { x: 75, y: 52 } : { x: 105, y: 56 };
}

export interface LoadSwitchSymbolProps {
  state: LoadSwitchState;
}

export const LoadSwitchSymbol: React.FC<LoadSwitchSymbolProps> = ({ state }) => {
  const bladeEnd = getLoadSwitchBladeEnd(state);
  const outlineWidth = CONDUCTOR_WIDTH + CONDUCTOR_OUTLINE;

  return (
    <Group>
      {/* Top conductor: black outline pass, then colored core pass. */}
      <Line points={[75, 0, 75, 52]} stroke={COLOR_OUTLINE} strokeWidth={outlineWidth} lineCap="butt" lineJoin="miter" />
      <Line points={[75, 0, 75, 52]} stroke={getLoadSwitchTopConductorColor()} strokeWidth={CONDUCTOR_WIDTH} lineCap="butt" lineJoin="miter" />

      {/* Bottom conductor: same two-pass treatment. */}
      <Line points={[75, 98, 75, 150]} stroke={COLOR_OUTLINE} strokeWidth={outlineWidth} lineCap="butt" lineJoin="miter" />
      <Line points={[75, 98, 75, 150]} stroke={getLoadSwitchBottomConductorColor(state)} strokeWidth={CONDUCTOR_WIDTH} lineCap="butt" lineJoin="miter" />

      {/* Blade */}
      <Line points={[75, 98, bladeEnd.x, bladeEnd.y]} stroke={getLoadSwitchBladeColor(state)} strokeWidth={SYMBOL_STROKE} lineCap="butt" lineJoin="miter" />

      {/* Terminals, drawn last so they sit on top of the blade/conductor ends. */}
      <Circle x={75} y={52} radius={6} fill={COLOR_WHITE} stroke={COLOR_OUTLINE} strokeWidth={3.5} />
      <Circle x={75} y={98} radius={6} fill={COLOR_WHITE} stroke={COLOR_OUTLINE} strokeWidth={3.5} />
    </Group>
  );
};
