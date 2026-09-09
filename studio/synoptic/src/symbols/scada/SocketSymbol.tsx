// SCADA-style symbol 7/9: socket / outlet. Canvas 150x150. State is shown
// EXCLUSIVELY by the incoming conductor's color - the socket body itself
// always paints panel-colored, live or dead.

import React from 'react';
import { Group, Line, Rect, Wedge } from 'react-konva';
import { COLOR_DE_ENERGIZED, COLOR_ENERGIZED, COLOR_OUTLINE, COLOR_PANEL, CONDUCTOR_OUTLINE, CONDUCTOR_WIDTH, OUTLINE_WIDTH } from '../../theme/ScadaTheme';

export type SocketState = 'LIVE' | 'DEAD';
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this state list belongs beside its component.
export const SOCKET_STATES: SocketState[] = ['LIVE', 'DEAD'];

// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this helper belongs beside its component.
export function getSocketConductorColor(state: SocketState): string {
  return state === 'LIVE' ? COLOR_ENERGIZED : COLOR_DE_ENERGIZED;
}

export interface SocketSymbolProps {
  state: SocketState;
}

const SOCKET_RADIUS = 38;
// Flat top edge of the half-circle. Not given as an explicit coordinate by
// the task (only the radius and the bar's dimensions are) - placed so the
// arc's lowest point lands exactly at the canvas center (75,75), keeping
// the symbol visually centered on the shared 150x150 convention.
const SOCKET_ARC_CENTER_Y = 75 - SOCKET_RADIUS;
const SOCKET_BAR_WIDTH = 92;
const SOCKET_BAR_HEIGHT = 10;

export const SocketSymbol: React.FC<SocketSymbolProps> = ({ state }) => {
  const outlineWidth = CONDUCTOR_WIDTH + CONDUCTOR_OUTLINE;
  const conductorColor = getSocketConductorColor(state);
  const barY = SOCKET_ARC_CENTER_Y + SOCKET_RADIUS;

  return (
    <Group>
      <Line points={[75, 0, 75, SOCKET_ARC_CENTER_Y]} stroke={COLOR_OUTLINE} strokeWidth={outlineWidth} lineCap="butt" lineJoin="miter" />
      <Line points={[75, 0, 75, SOCKET_ARC_CENTER_Y]} stroke={conductorColor} strokeWidth={CONDUCTOR_WIDTH} lineCap="butt" lineJoin="miter" />

      {/* Half-circle open at the top: a 180 deg wedge starting at 0 deg
          (pointing right) sweeping through 90 deg (down) to 180 deg
          (pointing left) - the two radii at the start/end angles lie on
          one straight line, forming the flat top edge; the arc forms the
          curved bottom. */}
      <Wedge x={75} y={SOCKET_ARC_CENTER_Y} radius={SOCKET_RADIUS} angle={180} rotation={0} fill={COLOR_PANEL} stroke={COLOR_OUTLINE} strokeWidth={OUTLINE_WIDTH} />

      <Rect x={75 - SOCKET_BAR_WIDTH / 2} y={barY} width={SOCKET_BAR_WIDTH} height={SOCKET_BAR_HEIGHT} fill={COLOR_OUTLINE} />
    </Group>
  );
};
