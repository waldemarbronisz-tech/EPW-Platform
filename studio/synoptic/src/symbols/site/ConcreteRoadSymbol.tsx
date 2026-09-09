// feat/site-objects-2d commit 4 - "15. Droga betonowa/Concrete road"
// from docs/EPW_rysunki_referencja.py's own droga(on) - that function's
// own `on` parameter is never actually read anywhere in its body,
// confirming mandatory test 4 (the road has NO states) directly from
// the reference itself, not just from this task's own prose. A
// SURFACE, same reasoning as GrassSymbol.tsx's own header comment (real
// on-canvas size, inverse-scale Group, no SITE_CANVAS_SCALE) - concrete
// slabs with expansion joints and a dashed center line, both
// recomputed for the object's real width via SurfaceGeometry.ts.

import React from 'react';
import { Group, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedRect } from './BandedShading';
import { computeRoadJoints, computeRoadDashes, ROAD_MARGIN_Y } from './SurfaceGeometry';
import { SITE_CONC, SITE_ROAD_JOINT, COLOR_WHITE, SITE_BAND_WIDTH_WIDE, SITE_BAND_WIDTH_NARROW, SITE_OUTLINE_WIDTH_MEDIUM } from '../../theme/ScadaTheme';

// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as scada/ symbols; kept even though this symbol has no states of its own (mandatory test 4), so every TEREN object exports SOME states list.
export const CONCRETE_ROAD_STATES: string[] = [];

export const ConcreteRoadSymbol: React.FC<SymbolProps> = ({ obj }) => {
  const scaleX = obj.scaleX || 1;
  const scaleY = obj.scaleY || 1;
  const realWidth = obj.width * scaleX;
  const realHeight = obj.height * scaleY;
  const joints = computeRoadJoints(realWidth);
  const dashes = computeRoadDashes(realWidth);
  const centerY = realHeight / 2;

  return (
    <Group scaleX={1 / scaleX} scaleY={1 / scaleY}>
      {bandedRect(0, 0, realWidth, realHeight, SITE_CONC, { band: SITE_BAND_WIDTH_WIDE })}
      {/* Expansion joints - one vertical line per slab boundary. */}
      {joints.map((x, i) => (
        <Line key={`joint-${i}`} points={[x, ROAD_MARGIN_Y, x, realHeight - ROAD_MARGIN_Y]} stroke={SITE_ROAD_JOINT} strokeWidth={SITE_OUTLINE_WIDTH_MEDIUM} listening={false} />
      ))}
      {/* Full-width horizontal joint - docs/EPW_rysunki_referencja.py's own `line(8,60,152,60,...)`. */}
      <Line points={[0, centerY, realWidth, centerY]} stroke={SITE_ROAD_JOINT} strokeWidth={SITE_OUTLINE_WIDTH_MEDIUM} listening={false} />
      {/* Dashed center lane marking, on top of that same joint line. */}
      {dashes.map((d, i) => (
        <Line key={`dash-${i}`} points={[d.x1, centerY, d.x2, centerY]} stroke={COLOR_WHITE} strokeWidth={SITE_BAND_WIDTH_NARROW} listening={false} />
      ))}
    </Group>
  );
};
