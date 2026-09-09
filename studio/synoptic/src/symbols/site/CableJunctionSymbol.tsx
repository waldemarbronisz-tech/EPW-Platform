// feat/site-objects-2d commit 3 - "11. Zlacze kablowe" from
// docs/EPW_rysunki_referencja.py's own zlacze(on). A cabinet with a
// terminal strip (three rows, each a state-colored block plus a
// concrete-colored block), two status lamps, a "ZK" label.
//
// The second lamp's own logic is deliberately inverted from the
// first, exactly as the reference has it: the first reads GREEN when
// on / DGREY when off (a normal running indicator), the second reads
// RED when off / DGREY when on (a fault/stopped indicator) - not a
// typo, reproduced as-is.

import React from 'react';
import { Group, Text } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedRect, bandedCircle } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import {
  COLOR_OUTLINE, FONT_UI, SITE_GREY, SITE_DARK, SITE_RED, SITE_GREEN, SITE_DGREY, SITE_CONC,
  SITE_BAND_WIDTH, SITE_BAND_WIDTH_NARROWEST, SITE_OUTLINE_WIDTH_MEDIUM, SITE_OUTLINE_WIDTH_THINNEST,
  SITE_CANVAS_SCALE
} from '../../theme/ScadaTheme';

export type CableJunctionState = 'ZALACZONY' | 'WYLACZONY';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as scada/ symbols.
export const CABLE_JUNCTION_STATES: CableJunctionState[] = ['ZALACZONY', 'WYLACZONY'];

const ROW_Y = [38, 50, 62];

export const CableJunctionSymbol: React.FC<SymbolProps> = ({ state }) => {
  const on = resolveSiteState(state, CABLE_JUNCTION_STATES, 'WYLACZONY') === 'ZALACZONY';

  return (
    <Group scaleX={SITE_CANVAS_SCALE} scaleY={SITE_CANVAS_SCALE}>
      {bandedRect(34, 22, 92, 84, SITE_GREY, { band: SITE_BAND_WIDTH })}
      {bandedRect(42, 30, 76, 50, SITE_DARK, { outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
      {ROW_Y.map(y => (
        <Group key={y}>
          {bandedRect(48, y, 20, 8, on ? SITE_RED : SITE_DGREY, { band: SITE_BAND_WIDTH_NARROWEST, outlineWidth: SITE_OUTLINE_WIDTH_THINNEST })}
          {bandedRect(76, y, 34, 8, SITE_CONC, { band: SITE_BAND_WIDTH_NARROWEST, outlineWidth: SITE_OUTLINE_WIDTH_THINNEST })}
        </Group>
      ))}
      {bandedCircle(58, 92, 7, on ? SITE_GREEN : SITE_DGREY, { outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
      {bandedCircle(80, 92, 7, on ? SITE_DGREY : SITE_RED, { outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
      <Text x={89} y={87} width={30} align="center" text="ZK" fontSize={13} fontFamily={FONT_UI} fontStyle="bold" fill={COLOR_OUTLINE} />
    </Group>
  );
};
