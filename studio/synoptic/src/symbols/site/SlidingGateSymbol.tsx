// feat/site-objects-2d commit 2 - "3. Brama przesuwna" from
// docs/EPW_rysunki_referencja.py's own brama(state). Rail, two posts,
// a sliding leaf with vertical slats, a motor at one post, a status
// lamp matching the leaf's own color. Three states: ZAMKNIETA (leaf
// full width, red), W_RUCHU (half width, yellow), OTWARTA (almost no
// leaf visible, green) - the reference's own state names, used
// verbatim as this object's own state strings (its dict keys are
// exactly these three, not booleans the way every other site object's
// on/off is expressed).

import React from 'react';
import { Group, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedRect, bandedCircle } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import type { SiteShadeTriad } from '../../theme/ScadaTheme';
import {
  COLOR_OUTLINE, SITE_CONC, SITE_GREY, SITE_DARK, SITE_RED, SITE_YELL, SITE_GREEN,
  SITE_BAND_WIDTH_NARROW, SITE_TEXTURE_LINE_WIDTH, SITE_OUTLINE_WIDTH_MEDIUM, SITE_CANVAS_SCALE
} from '../../theme/ScadaTheme';

export type GateState = 'ZAMKNIETA' | 'W_RUCHU' | 'OTWARTA';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as scada/ symbols.
export const GATE_STATES: GateState[] = ['ZAMKNIETA', 'W_RUCHU', 'OTWARTA'];

const FRACTION_BY_STATE: Record<GateState, number> = { ZAMKNIETA: 1.0, W_RUCHU: 0.5, OTWARTA: 0.08 };
const COLOR_BY_STATE: Record<GateState, SiteShadeTriad> = { ZAMKNIETA: SITE_RED, W_RUCHU: SITE_YELL, OTWARTA: SITE_GREEN };

export const SlidingGateSymbol: React.FC<SymbolProps> = ({ state: rawState }) => {
  const state = resolveSiteState(rawState, GATE_STATES, 'ZAMKNIETA');
  const width = Math.floor(110 * FRACTION_BY_STATE[state]);
  const color = COLOR_BY_STATE[state];

  const slatCount = width > 6 ? Math.max(2, Math.floor(width / 16)) : 0;
  const slats: number[] = [];
  for (let i = 1; i < slatCount; i++) slats.push(26 + i * 16);

  return (
    // SITE_CANVAS_SCALE - see HouseSymbol.tsx's own comment on this
    // same wrapper for the full reasoning.
    <Group scaleX={SITE_CANVAS_SCALE} scaleY={SITE_CANVAS_SCALE}>
      {bandedRect(6, 80, 148, 14, SITE_CONC, { band: SITE_BAND_WIDTH_NARROW })}
      {[14, 146].map(x => (
        <Group key={x}>{bandedRect(x - 8, 44, 16, 44, SITE_GREY, { band: SITE_BAND_WIDTH_NARROW })}</Group>
      ))}
      {width > 6 && (
        <>
          {bandedRect(26, 50, width, 30, color)}
          {slats.map(x => (
            <Line key={x} points={[x, 52, x, 78]} stroke={COLOR_OUTLINE} strokeWidth={SITE_TEXTURE_LINE_WIDTH} listening={false} />
          ))}
        </>
      )}
      {bandedRect(20, 60, 14, 24, SITE_DARK, { band: SITE_BAND_WIDTH_NARROW, outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
      {bandedCircle(146, 38, 7, color, { outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
    </Group>
  );
};
