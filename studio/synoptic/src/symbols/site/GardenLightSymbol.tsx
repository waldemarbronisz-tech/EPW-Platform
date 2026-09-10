// feat/site-objects-2d commit 3 - "9. Slupek oswietleniowy ogrodowy"
// from docs/EPW_rysunki_referencja.py's own slupek_ogr(on). A short
// bollard-style post with a lamp head and a cap.

import React from 'react';
import { Group, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedRect, bandedVRect, glow } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import {
  COLOR_OUTLINE, SITE_CONC, SITE_DGREY, SITE_YELL, SITE_DARK,
  SITE_BAND_WIDTH_NARROW, SITE_BAND_WIDTH_NARROWEST, SITE_OUTLINE_WIDTH, SITE_OUTLINE_WIDTH_MEDIUM, SITE_CANVAS_SCALE
} from '../../theme/ScadaTheme';

export type GardenLightState = 'ON' | 'OFF';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as scada/ symbols.
export const GARDEN_LIGHT_STATES: GardenLightState[] = ['ON', 'OFF'];

export const GardenLightSymbol: React.FC<SymbolProps> = ({ state }) => {
  const on = resolveSiteState(state, GARDEN_LIGHT_STATES, 'OFF') === 'ON';
  const fixture = on ? SITE_YELL : SITE_DARK;

  return (
    <Group scaleX={SITE_CANVAS_SCALE} scaleY={SITE_CANVAS_SCALE}>
      {bandedRect(66, 92, 28, 14, SITE_CONC, { band: SITE_BAND_WIDTH_NARROW, outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
      {bandedVRect(71, 44, 18, 50, SITE_DGREY)}
      {on && glow(80, 36, 18)}
      <Line points={[58, 44, 102, 44, 96, 22, 64, 22]} closed fill={fixture.base} stroke={COLOR_OUTLINE} strokeWidth={SITE_OUTLINE_WIDTH} />
      {bandedRect(56, 16, 48, 8, SITE_DGREY, { band: SITE_BAND_WIDTH_NARROWEST, outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
    </Group>
  );
};
