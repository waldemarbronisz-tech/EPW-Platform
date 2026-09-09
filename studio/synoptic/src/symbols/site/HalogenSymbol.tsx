// feat/site-objects-2d commit 3 - "8. Halogen" from
// docs/EPW_rysunki_referencja.py's own halogen(on). A reflector shape
// with a lit panel and a mounting bar.

import React from 'react';
import { Group, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedRect, glow } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import {
  COLOR_OUTLINE, SITE_DGREY, SITE_YELL, SITE_DARK,
  SITE_OUTLINE_WIDTH, SITE_CONNECTOR_WIDTH, SITE_CANVAS_SCALE
} from '../../theme/ScadaTheme';

export type HalogenState = 'ZALACZONY' | 'WYLACZONY';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as scada/ symbols.
export const HALOGEN_STATES: HalogenState[] = ['ZALACZONY', 'WYLACZONY'];

export const HalogenSymbol: React.FC<SymbolProps> = ({ state }) => {
  const on = resolveSiteState(state, HALOGEN_STATES, 'WYLACZONY') === 'ZALACZONY';
  const panel = on ? SITE_YELL : SITE_DARK;

  return (
    <Group scaleX={SITE_CANVAS_SCALE} scaleY={SITE_CANVAS_SCALE}>
      {bandedRect(66, 74, 28, 32, SITE_DGREY)}
      <Line points={[30, 26, 130, 26, 122, 66, 38, 66]} closed fill={SITE_DGREY.base} stroke={COLOR_OUTLINE} strokeWidth={SITE_OUTLINE_WIDTH} />
      {on && glow(80, 52, 26)}
      {bandedRect(40, 32, 80, 28, panel)}
      <Line points={[80, 66, 80, 74]} stroke={COLOR_OUTLINE} strokeWidth={SITE_CONNECTOR_WIDTH} />
    </Group>
  );
};
