// feat/site-objects-2d commit 2 - "10. Studzienka przylacza wody" from
// docs/EPW_rysunki_referencja.py's own studzienka(on). Top view: a
// manhole cover with radial ribbing (8 spokes, every 45 degrees) and a
// state-colored center.

import React from 'react';
import { Group, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedCircle, waterStub } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import { SITE_CONC, SITE_DGREY, SITE_BLUE, SITE_RIB_LINE, SITE_OUTLINE_WIDTH_MEDIUM, SITE_CANVAS_SCALE } from '../../theme/ScadaTheme';

export type WaterManholeState = 'ON' | 'OFF';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as scada/ symbols.
export const WATER_MANHOLE_STATES: WaterManholeState[] = ['ON', 'OFF'];

const CX = 80, CY = 64;
const RIB_INNER = 13, RIB_OUTER = 26;

// 8 spokes at 45-degree steps, inner radius 13 to outer radius 26 -
// docs/EPW_rysunki_referencja.py's own `for a in range(0,360,45)` loop.
const RIB_ANGLES_DEG = [0, 45, 90, 135, 180, 225, 270, 315];

export const WaterManholeSymbol: React.FC<SymbolProps> = ({ state, terminalNetState }) => {
  const on = resolveSiteState(state, WATER_MANHOLE_STATES, 'OFF') === 'ON';
  const przylaczeLive = (terminalNetState?.('PRZYLACZE') ?? 'INACTIVE') === 'ACTIVE';

  return (
    // SITE_CANVAS_SCALE - see HouseSymbol.tsx's own comment on this
    // same wrapper for the full reasoning.
    <Group scaleX={SITE_CANVAS_SCALE} scaleY={SITE_CANVAS_SCALE}>
      {bandedCircle(CX, CY, 40, SITE_CONC)}
      {bandedCircle(CX, CY, 29, SITE_DGREY, { outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
      {RIB_ANGLES_DEG.map(deg => {
        const rad = (deg * Math.PI) / 180;
        const x1 = CX + RIB_INNER * Math.cos(rad);
        const y1 = CY + RIB_INNER * Math.sin(rad);
        const x2 = CX + RIB_OUTER * Math.cos(rad);
        const y2 = CY + RIB_OUTER * Math.sin(rad);
        return <Line key={deg} points={[x1, y1, x2, y2]} stroke={SITE_RIB_LINE} strokeWidth={SITE_OUTLINE_WIDTH_MEDIUM} listening={false} />;
      })}
      {bandedCircle(CX, CY, 11, on ? SITE_BLUE : SITE_DGREY, { outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
      {/* fix/hydraulic-connections commit 5: krociec+kolnierz on the
          one terminal (PRZYLACZE, BOTTOM) - the manhole's own x
          already matches the true terminal (CX=80=160/2), only y
          needed extending from the manhole's own rim (CY+40=104) out
          to the true edge (120). Nothing reached the edge before. */}
      {waterStub(CX, CY + 40, 'B', przylaczeLive, 160, 120)}
    </Group>
  );
};
