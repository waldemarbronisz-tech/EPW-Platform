// feat/room-plan: the wall socket outlet, drawn as an ARCHITECTURAL
// FLOOR-PLAN symbol.
//
// Why a new symbol rather than reusing scada.socket: that one is the
// SCADA one-line schematic socket (a 150x150 schematic glyph whose
// whole state is carried by the incoming conductor's color - see
// SocketSymbol.tsx's own header). This is the plan symbol: the
// half-circle with a bar, sitting against a wall, seen from above.
// Different drawing, different convention - scada.socket stays exactly
// as it is for schematics.
//
// Standard plan convention: a semicircle whose flat side sits on the
// wall, a bar across that flat side, and a short stem from the bar out
// to the wall line. Energized, the body fills red (the platform's own
// COLOR_ENERGIZED, the same "pod napieciem" red every conductor uses);
// de-energized it stays panel grey.
//
// NO TERMINALS, deliberately - see registry/building.ts's own header.

import React from 'react';
import { Group, Line, Wedge } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import {
  COLOR_DE_ENERGIZED,
  COLOR_ENERGIZED,
  COLOR_OUTLINE,
  COLOR_PANEL,
} from '../../theme/ScadaTheme';

export type SocketOutletState = 'LIVE' | 'DEAD';
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this state list belongs beside its component.
export const SOCKET_OUTLET_STATES: SocketOutletState[] = ['LIVE', 'DEAD'];

export const SocketOutletSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;
  const isLive = state === 'LIVE';

  // Geometry, all derived from the object's own size so a resize keeps
  // the proportions: the stem takes the bottom fifth, the bar sits on
  // top of it, and the dome fills what is left above the bar.
  const stemHeight = h * 0.2;
  const barY = h - stemHeight;
  // Same size-proportional stroke as the luminaire - see its own note.
  const stroke = Math.max(1.2, Math.min(w, h) * 0.075);
  const radius = Math.min(w / 2, barY) - stroke / 2;
  const cx = w / 2;

  return (
    <Group>
      {/* The dome. Konva's Wedge draws clockwise from `rotation`, so
          180deg..360deg is the upper half. */}
      <Wedge
        x={cx}
        y={barY}
        radius={radius}
        angle={180}
        rotation={180}
        fill={isLive ? COLOR_ENERGIZED : COLOR_PANEL}
        stroke={COLOR_OUTLINE}
        strokeWidth={stroke}
      />
      {/* The bar across the flat side - the part that makes this a
          socket rather than a plain half-circle. */}
      <Line
        points={[cx - radius, barY, cx + radius, barY]}
        stroke={COLOR_OUTLINE}
        strokeWidth={stroke}
      />
      {/* The stem down to the wall the socket is mounted on. Colored
          like a conductor so a live socket reads at a glance, matching
          how every other energized thing on this canvas is drawn. */}
      <Line
        points={[cx, barY, cx, h]}
        stroke={isLive ? COLOR_ENERGIZED : COLOR_DE_ENERGIZED}
        strokeWidth={stroke}
      />
    </Group>
  );
};
