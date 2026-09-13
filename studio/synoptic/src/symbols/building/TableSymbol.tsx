// feat/room-plan: table (stol), plan view.
//
// A table from above is its top, and the only detail worth drawing is
// the edge - a thin inset line that reads as the board's own thickness
// and stops the shape being a plain rectangle. Scale: 140 x 80 cm
// (Scale.ts) - a six-seater.
//
// Pure graphics: no state, no circuit, nothing to operate. It is here
// so a room reads as a room.

import React from 'react';
import { Group, Rect } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { COLOR_OUTLINE, FURNITURE_DARK, FURNITURE_SIDE, FURNITURE_TOP, PLAN_SHADOW, symbolStroke } from './BuildingSymbolTheme';

export const TableSymbol: React.FC<SymbolProps> = ({ obj }) => {
  const w = obj.width;
  const h = obj.height;
  const stroke = symbolStroke(w, h);
  const inset = Math.min(w, h) * 0.1;

  return (
    <Group>
      {/* The board's own edge, showing under the top on two sides -
          the cheapest hint of thickness that still reads at plan zoom. */}
      <Rect
        x={stroke * 0.6} y={stroke * 0.6}
        width={w} height={h}
        fill={FURNITURE_DARK}
        cornerRadius={inset * 0.6}
        {...PLAN_SHADOW}
        listening={false}
      />
      <Rect
        width={w} height={h}
        fill={FURNITURE_TOP}
        stroke={COLOR_OUTLINE} strokeWidth={stroke}
        cornerRadius={inset * 0.6}
      />
      <Rect
        x={inset} y={inset}
        width={w - inset * 2} height={h - inset * 2}
        stroke={FURNITURE_SIDE} strokeWidth={stroke * 0.6}
        cornerRadius={inset * 0.4}
        listening={false}
      />
    </Group>
  );
};
