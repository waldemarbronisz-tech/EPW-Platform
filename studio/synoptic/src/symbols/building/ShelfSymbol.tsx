// feat/room-plan: shelving unit (regal), plan view.
//
// Redrawn because the first version did not read as shelving at all -
// it was a grey box with a few lines, indistinguishable from a worktop.
// What makes a shelving unit recognisable from above is that you see
// INTO it: the back panel as a solid band, the uprights dividing it
// into bays, and the bays themselves partly filled with what is stored
// on them. That last part is the detail that settles it - an empty
// outlined rectangle is furniture, a rectangle with boxes in it is
// storage.
//
// Bay count and box layout are DERIVED from the unit's size, so
// stretching a unit to 2.4 m gives three bays of boxes rather than one
// stretched bay. Combined with resizeRedraws (registry/building.ts),
// resizing genuinely redraws the shelving instead of scaling a picture
// of it.
//
// Scale: 80 x 35 cm (Scale.ts) - one standard bay. It is drawn along
// whichever axis is longer, so it works against any wall.

import React from 'react';
import { Group, Line, Rect } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { cm } from '../../theme/Scale';
import { COLOR_OUTLINE, FURNITURE_DARK, METAL, METAL_DARK, PLAN_SHADOW, symbolStroke } from './BuildingSymbolTheme';

// One bay per 80 cm of run - the real bay width, so a 2.4 m unit draws
// three bays because it IS three bays.
const BAY_LENGTH = cm(80);

export const ShelfSymbol: React.FC<SymbolProps> = ({ obj }) => {
  const w = obj.width;
  const h = obj.height;
  const stroke = symbolStroke(w, h);
  const horizontal = w >= h;
  const runLength = horizontal ? w : h;
  const depth = horizontal ? h : w;
  const bays = Math.max(1, Math.round(runLength / BAY_LENGTH));

  // The back panel occupies the first slice of the depth; the shelves
  // (and what is on them) fill the rest.
  const backDepth = Math.max(2, depth * 0.16);

  /** Rect in run/depth terms, mapped to x/y for whichever way the unit runs. */
  const place = (alongStart: number, alongSize: number, acrossStart: number, acrossSize: number) =>
    horizontal
      ? { x: alongStart, y: acrossStart, width: alongSize, height: acrossSize }
      : { x: acrossStart, y: alongStart, width: acrossSize, height: alongSize };

  const boxes: { x: number; y: number; width: number; height: number }[] = [];
  for (let bay = 0; bay < bays; bay++) {
    const bayStart = (runLength * bay) / bays;
    const bayLength = runLength / bays;
    // Two stored items per bay, inset from the uprights and from the
    // front edge - enough to read as "things on shelves" without
    // pretending to inventory anything.
    for (let i = 0; i < 2; i++) {
      const pad = bayLength * 0.12;
      const itemLength = (bayLength - pad * 3) / 2;
      boxes.push(place(
        bayStart + pad + i * (itemLength + pad),
        itemLength,
        backDepth + depth * 0.1,
        depth * 0.5,
      ));
    }
  }

  return (
    <Group>
      {/* Carcass. */}
      <Rect width={w} height={h} fill={METAL} stroke={COLOR_OUTLINE} strokeWidth={stroke} {...PLAN_SHADOW} />

      {/* Back panel - a solid band on the side that goes against the
          wall. This is what tells you which way the unit faces. */}
      <Rect
        {...place(0, runLength, 0, backDepth)}
        fill={METAL_DARK}
        listening={false}
      />

      {/* Stored items. */}
      {boxes.map((box, i) => (
        <Rect
          key={i}
          {...box}
          fill={FURNITURE_DARK}
          stroke={COLOR_OUTLINE}
          strokeWidth={stroke * 0.5}
          opacity={0.85}
          listening={false}
        />
      ))}

      {/* Uprights between the bays, drawn over the items so the bay
          divisions stay legible however full the unit looks. */}
      {Array.from({ length: bays - 1 }, (_, i) => {
        const at = (runLength * (i + 1)) / bays;
        const points = horizontal ? [at, 0, at, h] : [0, at, w, at];
        return <Line key={i} points={points} stroke={COLOR_OUTLINE} strokeWidth={stroke * 1.3} listening={false} />;
      })}

      {/* Front edge, heavier - the open side. */}
      <Line
        points={horizontal ? [0, h, w, h] : [w, 0, w, h]}
        stroke={COLOR_OUTLINE}
        strokeWidth={stroke * 1.6}
        listening={false}
      />
    </Group>
  );
};
