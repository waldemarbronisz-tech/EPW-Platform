// feat/site-objects-2d commit 2 - "1. Dom" from
// docs/EPW_rysunki_referencja.py's own dom(on). Side view: gable roof
// with ridge, four windows, a door, a chimney. States ZALACZONY (lit
// windows, brick roof) / WYLACZONY (dimmed windows, dimmed roof).

import React from 'react';
import { Group, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedRect } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import {
  COLOR_OUTLINE, SITE_CONC, SITE_BRICK, SITE_BRICK_DIM, SITE_BLUE, SITE_DGREY, SITE_WOOD, SITE_CHIMNEY,
  SITE_BAND_WIDTH_NARROW, SITE_OUTLINE_WIDTH, SITE_OUTLINE_WIDTH_MEDIUM, SITE_CANVAS_SCALE
} from '../../theme/ScadaTheme';

export type HouseState = 'ZALACZONY' | 'WYLACZONY';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as scada/ symbols.
export const HOUSE_STATES: HouseState[] = ['ZALACZONY', 'WYLACZONY'];

export const HouseSymbol: React.FC<SymbolProps> = ({ state }) => {
  const on = resolveSiteState(state, HOUSE_STATES, 'WYLACZONY') === 'ZALACZONY';
  const roof = on ? SITE_BRICK : SITE_BRICK_DIM;
  const windowColor = on ? SITE_BLUE : SITE_DGREY;

  return (
    // SITE_CANVAS_SCALE: this whole shape is drawn at
    // docs/EPW_rysunki_referencja.py's own literal 160x120 coordinates
    // below, unmodified - this outer Group scales that down to this
    // symbol's own declared 128x96 (see ScadaTheme.ts's own comment on
    // that constant, and registry/site.ts's own comment, for why).
    <Group scaleX={SITE_CANVAS_SCALE} scaleY={SITE_CANVAS_SCALE}>
      {bandedRect(18, 34, 124, 72, SITE_CONC)}
      <Line
        points={[12, 38, 80, 10, 148, 38, 140, 44, 80, 20, 20, 44]}
        closed fill={roof.base} stroke={COLOR_OUTLINE} strokeWidth={SITE_OUTLINE_WIDTH}
      />
      {/* Roof underside - a flat dark silhouette (all three triad
          channels collapsed to the roof's own dark tone), no outline
          of its own (reference: ow=0) - reads as the eave's shadow. */}
      <Line points={[20, 44, 80, 20, 140, 44, 140, 50, 80, 26, 20, 50]} closed fill={roof.dark} />
      <Line points={[80, 20, 80, 106]} stroke={COLOR_OUTLINE} strokeWidth={SITE_OUTLINE_WIDTH_MEDIUM} />
      {[36, 56, 104, 124].map(x => (
        <Group key={x}>
          {bandedRect(x - 9, 58, 18, 16, windowColor, { band: SITE_BAND_WIDTH_NARROW, outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
        </Group>
      ))}
      {bandedRect(70, 80, 20, 26, SITE_WOOD, { band: SITE_BAND_WIDTH_NARROW, outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
      {bandedRect(112, 14, 12, 20, SITE_CHIMNEY, { band: SITE_BAND_WIDTH_NARROW, outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
    </Group>
  );
};
