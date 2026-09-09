// SCADA-style symbol 6/9: pilot lamp (a panel indicator lamp - a diagonal
// cross inside a circle, distinct from the small round indicator diode,
// symbol 8). Canvas 150x150, no conductor (none is specified for this
// symbol - only the circle and cross).

import React from 'react';
import { Circle, Group, Line } from 'react-konva';
import { COLOR_BEVEL_DARK, COLOR_LAMP_LIT, COLOR_OUTLINE, OUTLINE_WIDTH, SYMBOL_STROKE } from '../../theme/ScadaTheme';

export type PilotLampState = 'ON' | 'OFF';
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this state list belongs beside its component.
export const PILOT_LAMP_STATES: PilotLampState[] = ['ON', 'OFF'];

/**
 * "ciemnoszare" (dark gray) maps to the darker of the theme's two grays:
 * BEVEL_DARK is objectively darker than DE_ENERGIZED (lower luminance).
 * DE_ENERGIZED is semantically "no voltage", which does not describe an
 * OFF panel lamp reporting a plain OFF signal - so BEVEL_DARK, chosen by
 * literal color match, not by borrowing the voltage-absence color.
 * (Interpretation decision - the task names a color, not a semantic state.)
 */
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this helper belongs beside its component.
export function getPilotLampFillColor(state: PilotLampState): string {
  return state === 'ON' ? COLOR_LAMP_LIT : COLOR_BEVEL_DARK;
}

export interface PilotLampSymbolProps {
  state: PilotLampState;
}

const LAMP_RADIUS = 34;
const CROSS_HALF_LENGTH = LAMP_RADIUS * 0.6;

export const PilotLampSymbol: React.FC<PilotLampSymbolProps> = ({ state }) => {
  const r = CROSS_HALF_LENGTH;

  return (
    <Group>
      <Circle x={75} y={75} radius={LAMP_RADIUS} fill={getPilotLampFillColor(state)} stroke={COLOR_OUTLINE} strokeWidth={OUTLINE_WIDTH} />
      <Line points={[75 - r, 75 - r, 75 + r, 75 + r]} stroke={COLOR_OUTLINE} strokeWidth={SYMBOL_STROKE} lineCap="butt" lineJoin="miter" />
      <Line points={[75 - r, 75 + r, 75 + r, 75 - r]} stroke={COLOR_OUTLINE} strokeWidth={SYMBOL_STROKE} lineCap="butt" lineJoin="miter" />
    </Group>
  );
};
