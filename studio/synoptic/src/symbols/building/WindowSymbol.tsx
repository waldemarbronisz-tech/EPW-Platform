// feat/room-plan: window (okno), plan view.
//
// The standard plan window: the opening's reveal with the glazing line
// running through it. Drawn as the frame band plus the pane - a thin
// glass-coloured line rather than a heavy rectangle, because in plan a
// window IS essentially a line in a wall.
//
// Like the door, this sits on a wall rather than cutting through it -
// see DoorSymbol's own note on why, and on why the reveal band is
// painted in the wall's tone.
//
// Scale: 120 cm (Scale.ts).

import React from 'react';
import { Group, Line, Rect } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { COLOR_OUTLINE, FITTING_BODY, GLASS, symbolStroke } from './BuildingSymbolTheme';

export const WindowSymbol: React.FC<SymbolProps> = ({ obj }) => {
  const w = obj.width;
  const h = obj.height;
  const stroke = symbolStroke(w, h);
  const midY = h / 2;

  return (
    <Group>
      {/* Reveal, in the wall's own tone. */}
      <Rect width={w} height={h} fill={FITTING_BODY} stroke={COLOR_OUTLINE} strokeWidth={stroke} />
      {/* Frame faces, inner and outer. */}
      <Line points={[0, h * 0.25, w, h * 0.25]} stroke={COLOR_OUTLINE} strokeWidth={stroke * 0.7} listening={false} />
      <Line points={[0, h * 0.75, w, h * 0.75]} stroke={COLOR_OUTLINE} strokeWidth={stroke * 0.7} listening={false} />
      {/* The glazing itself. */}
      <Line points={[0, midY, w, midY]} stroke={GLASS} strokeWidth={Math.max(1.5, h * 0.22)} listening={false} />
      <Line points={[0, midY, w, midY]} stroke={COLOR_OUTLINE} strokeWidth={stroke * 0.45} listening={false} />
    </Group>
  );
};
