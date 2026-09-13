// feat/room-plan: wall luminaire / sconce (kinkiet), plan view.
//
// A sconce is mounted ON a wall, so in plan it is a half-disc with its
// flat back against that wall and a short mounting plate behind it -
// the same "flat side sits on the wall" convention the socket outlet
// uses, which is what makes the two read as a matched pair. Lit, the
// body fills and the light spreads forward, away from the wall, rather
// than all round: a sconce does not light what is behind it.
//
// Scale: 25 x 13 cm (Scale.ts). Rotate it to face into the room.

import React from 'react';
import { Group, Line, Wedge } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { COLOR_OUTLINE, FITTING_BODY, FITTING_BODY_DARK, LIT, symbolStroke } from './BuildingSymbolTheme';

export const WallLuminaireSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;
  const stroke = symbolStroke(w, h);
  const isOn = state === 'ON';

  // The back plate takes the top sliver; the shade bulges downward from
  // it, so "up" in the symbol's own coordinates is the wall.
  const plateHeight = Math.max(2, h * 0.22);
  const cx = w / 2;
  const radius = Math.min(w / 2, h - plateHeight) - stroke / 2;

  return (
    <Group>
      {/* Forward throw - a wedge, not a circle: the wall blocks the rest. */}
      {isOn && (
        <Wedge
          x={cx} y={plateHeight} radius={radius * 3}
          angle={160} rotation={10}
          fill={LIT} opacity={0.2} listening={false}
        />
      )}
      {/* Mounting plate against the wall. */}
      <Line
        points={[cx - radius * 0.9, plateHeight, cx + radius * 0.9, plateHeight]}
        stroke={COLOR_OUTLINE} strokeWidth={stroke * 1.4}
      />
      {/* The shade. */}
      <Wedge
        x={cx} y={plateHeight} radius={radius}
        angle={180} rotation={0}
        fill={isOn ? LIT : FITTING_BODY}
        stroke={COLOR_OUTLINE} strokeWidth={stroke}
      />
      <Line
        points={[cx, plateHeight, cx, plateHeight + radius * 0.55]}
        stroke={isOn ? COLOR_OUTLINE : FITTING_BODY_DARK}
        strokeWidth={stroke * 0.8}
        listening={false}
      />
    </Group>
  );
};
