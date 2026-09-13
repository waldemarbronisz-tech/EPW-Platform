// feat/room-plan: door (drzwi), plan view.
//
// The standard plan door: the leaf drawn open at 90 degrees plus the
// quarter-circle arc it sweeps. The arc is not decoration - it is how a
// plan says which way the door opens and how much floor it needs, which
// is exactly the question you ask before putting a shelf next to it.
//
// The door does NOT draw a reveal of its own any more. The wall is now
// genuinely cut where the door sits (project/WallOpenings.ts - the wall
// body is clipped and its jambs drawn at the cut), so the floor shows
// through the opening on its own. The band this symbol used to paint
// over the wall was a stand-in for that hole, and with a real hole
// there it would just put a grey plate back into it.
//
// Seating is automatic: dropped or dragged onto a wall, the door
// centres on the wall's line and turns to its angle (Canvas.tsx).
//
// Scale: 90 cm leaf, 25 cm deep (Scale.ts).

import React from 'react';
import { Arc, Group, Line, Rect } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { COLOR_OUTLINE, FURNITURE_TOP, symbolStroke } from './BuildingSymbolTheme';

export const DoorSymbol: React.FC<SymbolProps> = ({ obj }) => {
  const w = obj.width;
  const h = obj.height;
  const stroke = symbolStroke(w, h);
  // The leaf is a real door thickness (about 4 cm) rather than a
  // fraction of the symbol, so a wider door gets a wider opening, not a
  // fatter door.
  const leafThickness = Math.max(2, h * 0.14);
  const hingeY = h / 2;

  return (
    <Group>
      {/* Swing arc, hinged at the left jamb. Dashed: it marks a path,
          not a built thing. */}
      <Arc
        x={0} y={hingeY}
        innerRadius={w} outerRadius={w}
        angle={90} rotation={0}
        stroke={COLOR_OUTLINE} strokeWidth={stroke * 0.6}
        dash={[5, 4]}
        opacity={0.75}
        listening={false}
      />
      {/* The leaf, standing open across the opening. */}
      <Rect
        x={0} y={hingeY}
        width={leafThickness} height={w}
        fill={FURNITURE_TOP}
        stroke={COLOR_OUTLINE} strokeWidth={stroke}
      />
      {/* Threshold - a light line across the opening, so the door is
          still readable as a door when the wall behind it is thin. */}
      <Line
        points={[0, hingeY, w, hingeY]}
        stroke={COLOR_OUTLINE}
        strokeWidth={stroke * 0.4}
        dash={[3, 3]}
        opacity={0.45}
        listening={false}
      />
    </Group>
  );
};
