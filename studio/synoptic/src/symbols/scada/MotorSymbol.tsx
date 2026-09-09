// SCADA-style symbol 5/9: motor. Canvas 150x150, fed from the top port.

import React from 'react';
import { Circle, Group, Line, Text } from 'react-konva';
import {
  COLOR_ALARM,
  COLOR_DE_ENERGIZED,
  COLOR_ENERGIZED,
  COLOR_OUTLINE,
  COLOR_RUN,
  CONDUCTOR_OUTLINE,
  CONDUCTOR_WIDTH,
  OUTLINE_WIDTH
} from '../../theme/ScadaTheme';

export type MotorState = 'RUN' | 'STOP' | 'FAULT';
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this state list belongs beside its component.
export const MOTOR_STATES: MotorState[] = ['RUN', 'STOP', 'FAULT'];

// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this helper belongs beside its component.
export function getMotorFillColor(state: MotorState): string {
  if (state === 'RUN') return COLOR_RUN;
  if (state === 'FAULT') return COLOR_ALARM;
  return COLOR_DE_ENERGIZED; // STOP
}

/**
 * A conductor is only ever energized or de-energized (the shared rule for
 * every symbol's wire), never one of a symbol's own state-specific fill
 * colors. STOP has no power flowing; RUN and FAULT both imply line power
 * is present (a faulted running motor still has power, it just is not
 * behaving correctly) - interpretation decision, not spelled out by the
 * task text itself.
 */
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this helper belongs beside its component.
export function getMotorConductorColor(state: MotorState): string {
  return state === 'STOP' ? COLOR_DE_ENERGIZED : COLOR_ENERGIZED;
}

export interface MotorSymbolProps {
  state: MotorState;
}

const MOTOR_RADIUS = 34;

export const MotorSymbol: React.FC<MotorSymbolProps> = ({ state }) => {
  const edgeY = 75 - MOTOR_RADIUS;
  const outlineWidth = CONDUCTOR_WIDTH + CONDUCTOR_OUTLINE;
  const conductorColor = getMotorConductorColor(state);

  return (
    <Group>
      <Line points={[75, 0, 75, edgeY]} stroke={COLOR_OUTLINE} strokeWidth={outlineWidth} lineCap="butt" lineJoin="miter" />
      <Line points={[75, 0, 75, edgeY]} stroke={conductorColor} strokeWidth={CONDUCTOR_WIDTH} lineCap="butt" lineJoin="miter" />

      <Circle x={75} y={75} radius={MOTOR_RADIUS} fill={getMotorFillColor(state)} stroke={COLOR_OUTLINE} strokeWidth={OUTLINE_WIDTH} />

      <Text
        x={75 - MOTOR_RADIUS}
        y={75 - MOTOR_RADIUS}
        width={MOTOR_RADIUS * 2}
        height={MOTOR_RADIUS * 2}
        align="center"
        verticalAlign="middle"
        text="M"
        fontSize={34}
        fontStyle="bold"
        fill={COLOR_OUTLINE}
      />
    </Group>
  );
};
