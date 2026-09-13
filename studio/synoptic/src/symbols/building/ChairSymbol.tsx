// feat/room-plan: chair (krzeslo), plan view.
//
// A chair from above is a seat with a backrest along one edge. Which
// edge matters - it says which way the chair faces - so the backrest is
// drawn as a distinctly thicker bar at the TOP of the symbol's own
// coordinates; rotate the object to seat it round a table.
//
// Scale: 45 x 45 cm (Scale.ts).

import React from 'react';
import { Group, Rect } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { COLOR_OUTLINE, FURNITURE_DARK, FURNITURE_TOP, PLAN_SHADOW, symbolStroke } from './BuildingSymbolTheme';

export const ChairSymbol: React.FC<SymbolProps> = ({ obj }) => {
  const w = obj.width;
  const h = obj.height;
  const stroke = symbolStroke(w, h);
  const backHeight = h * 0.2;
  const radius = Math.min(w, h) * 0.16;

  return (
    <Group>
      {/* Seat. */}
      <Rect
        y={backHeight * 0.8}
        width={w} height={h - backHeight * 0.8}
        fill={FURNITURE_TOP}
        stroke={COLOR_OUTLINE} strokeWidth={stroke}
        cornerRadius={radius}
        {...PLAN_SHADOW}
      />
      {/* Backrest - thicker and darker, so the facing direction is
          unmistakable even at a small zoom. */}
      <Rect
        width={w} height={backHeight}
        fill={FURNITURE_DARK}
        stroke={COLOR_OUTLINE} strokeWidth={stroke}
        cornerRadius={radius * 0.6}
      />
    </Group>
  );
};
