// SCADA-style symbol 10: a panel push button (owner 2026-09-24: "Przycisk
// robimy - robota synoptyki, ale w logice też chcę bity"). On the panel
// it WRITES one of the logic's IN bits (bindings.command.tag = M.<name>),
// toggling it or pulsing it (editor.button_mode); the logic reads the
// bit through its ordinary "Wejście bitowe" block. The cap shows the
// bit's live value: PRESSED (TRUE) or RELEASED (FALSE). Canvas 150x150,
// the label (obj.text) under the cap.

import React from 'react';
import { Circle, Group, Rect, Text } from 'react-konva';
import {
  COLOR_BEVEL_DARK, COLOR_BEVEL_LIGHT, COLOR_OUTLINE, COLOR_PANEL, COLOR_RUN, FONT_SIZE_BASE, FONT_UI,
  OUTLINE_WIDTH, SYMBOL_STROKE,
} from '../../theme/ScadaTheme';

export type PushButtonState = 'RELEASED' | 'PRESSED';
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this state list belongs beside its component.
export const PUSH_BUTTON_STATES: PushButtonState[] = ['RELEASED', 'PRESSED'];

/** How the button writes its bit: TOGGLE flips it on every click, PULSE sets it TRUE and clears it after `pulse_ms`. */
export type PushButtonMode = 'TOGGLE' | 'PULSE';
// oxlint-disable-next-line react/only-export-components -- the mode list belongs beside the symbol that uses it.
export const PUSH_BUTTON_MODES: PushButtonMode[] = ['TOGGLE', 'PULSE'];
// oxlint-disable-next-line react/only-export-components -- the default belongs beside the symbol that uses it.
export const DEFAULT_PULSE_MS = 500;

/** The cap: green while the bit is TRUE (the theme's "stan załączony"), the light bevel grey while it is FALSE. */
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this helper belongs beside its component.
export function getPushButtonCapColor(state: PushButtonState): string {
  return state === 'PRESSED' ? COLOR_RUN : COLOR_BEVEL_LIGHT;
}

export interface PushButtonSymbolProps {
  state: PushButtonState;
  /** The text under the cap - the object's own `text`. */
  label?: string;
}

const PLATE = { x: 15, y: 15, width: 120, height: 120, radius: 10 };
const CAP_CENTER = { x: 75, y: 62 };
const CAP_RADIUS = 30;
const LABEL_Y = 104;

export const PushButtonSymbol: React.FC<PushButtonSymbolProps> = ({ state, label }) => {
  const pressed = state === 'PRESSED';
  return (
    <Group>
      <Rect x={PLATE.x} y={PLATE.y} width={PLATE.width} height={PLATE.height} cornerRadius={PLATE.radius}
        fill={COLOR_PANEL} stroke={COLOR_OUTLINE} strokeWidth={OUTLINE_WIDTH} />
      {/* the collar the cap sits in - dark when the cap is down, so a pressed button reads as recessed */}
      <Circle x={CAP_CENTER.x} y={CAP_CENTER.y} radius={CAP_RADIUS + 6}
        fill={pressed ? COLOR_BEVEL_DARK : COLOR_BEVEL_LIGHT} stroke={COLOR_OUTLINE} strokeWidth={SYMBOL_STROKE} />
      <Circle x={CAP_CENTER.x} y={CAP_CENTER.y} radius={pressed ? CAP_RADIUS - 3 : CAP_RADIUS}
        fill={getPushButtonCapColor(state)} stroke={COLOR_OUTLINE} strokeWidth={SYMBOL_STROKE} />
      <Text x={PLATE.x} y={LABEL_Y} width={PLATE.width} align="center" text={label || ''}
        fontSize={FONT_SIZE_BASE} fontFamily={FONT_UI} fontStyle="bold" fill={COLOR_OUTLINE} />
    </Group>
  );
};
