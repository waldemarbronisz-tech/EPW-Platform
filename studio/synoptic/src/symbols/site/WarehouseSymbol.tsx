// feat/site-objects-2d commit 2 - "2. Magazyn" from
// docs/EPW_rysunki_referencja.py's own magazyn(on). Side view: gable
// roof, corrugated-metal cladding (vertical texture lines), a rolling
// door in the middle, two windows. States ZALACZONY / WYLACZONY.

import React from 'react';
import { Group, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedRect } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import {
  COLOR_OUTLINE, SITE_GREY, SITE_DGREY, SITE_DARK, SITE_BLUE,
  SITE_METAL_TEXTURE, SITE_PANEL_TEXTURE, SITE_TEXTURE_LINE_WIDTH,
  SITE_BAND_WIDTH_NARROW, SITE_OUTLINE_WIDTH, SITE_OUTLINE_WIDTH_MEDIUM, SITE_OUTLINE_WIDTH_THINNEST, SITE_CANVAS_SCALE
} from '../../theme/ScadaTheme';

export type WarehouseState = 'ZALACZONY' | 'WYLACZONY';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as scada/ symbols.
export const WAREHOUSE_STATES: WarehouseState[] = ['ZALACZONY', 'WYLACZONY'];

export const WarehouseSymbol: React.FC<SymbolProps> = ({ state }) => {
  const on = resolveSiteState(state, WAREHOUSE_STATES, 'WYLACZONY') === 'ZALACZONY';
  const body = on ? SITE_GREY : SITE_DGREY;
  const windowColor = on ? SITE_BLUE : SITE_DGREY;

  // Corrugated wall cladding: 6 evenly spaced vertical lines - fixed
  // count/spacing from the reference (i=1..6 of 132/7), so this needs
  // no random/seeded generator the way trawa's own texture (commit 4)
  // does.
  const claddingX: number[] = [];
  for (let i = 1; i <= 6; i++) claddingX.push(14 + (i * 132) / 7);

  return (
    // SITE_CANVAS_SCALE - see HouseSymbol.tsx's own comment on this
    // same wrapper for the full reasoning.
    <Group scaleX={SITE_CANVAS_SCALE} scaleY={SITE_CANVAS_SCALE}>
      {bandedRect(14, 36, 132, 70, body)}
      <Line
        points={[8, 40, 80, 16, 152, 40, 146, 46, 80, 24, 14, 46]}
        closed fill={SITE_DGREY.base} stroke={COLOR_OUTLINE} strokeWidth={SITE_OUTLINE_WIDTH}
      />
      {claddingX.map(x => (
        <Line key={x} points={[x, 46, x, 106]} stroke={SITE_METAL_TEXTURE} strokeWidth={SITE_TEXTURE_LINE_WIDTH} listening={false} />
      ))}
      {bandedRect(58, 66, 44, 40, SITE_DARK)}
      {[1, 2, 3].map(i => (
        <Line key={i} points={[58, 66 + i * 10, 102, 66 + i * 10]} stroke={SITE_PANEL_TEXTURE} strokeWidth={SITE_OUTLINE_WIDTH_THINNEST} listening={false} />
      ))}
      {bandedRect(20, 72, 20, 16, windowColor, { band: SITE_BAND_WIDTH_NARROW, outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
      {bandedRect(120, 72, 20, 16, windowColor, { band: SITE_BAND_WIDTH_NARROW, outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
    </Group>
  );
};
