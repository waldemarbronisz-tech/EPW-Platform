// feat/water-management commit 4 - "6. Hydrofor" (hydrofor) from docs/
// EPW_gospodarka_wodna_referencja.py's own hydrofor(on). SWITCHED -
// pressure vessel plus pump; the vessel itself reads blue while the
// pump is running, per this task's own "Naczynie niebieskie przy
// pracy".

import React from 'react';
import { Group, Rect, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedRect, bandedCircleLightOnly, statusLed, objectPipeSegment, waterStub } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import { COLOR_OUTLINE, SITE_GREY, SITE_BLUE, SITE_GREEN, SITE_RED, SITE_DARK, SITE_CONC, SITE_OUTLINE_WIDTH, SITE_OUTLINE_WIDTH_MEDIUM } from '../../theme/ScadaTheme';

export type HydroforState = 'ON' | 'OFF';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as every other site/ symbol.
export const HYDROFOR_STATES: HydroforState[] = ['ON', 'OFF'];

// fix/hydraulic-connections commit 5: everything shifted up by 7 (was
// centered on y=55/56, the true WYLOT terminal height is 48) so the
// vessel's own left wall can carry a proper krociec/kolnierz out to
// the real terminal - this object had NONE at all before (its old
// internal pipe, x56-66, was purely a vessel-to-pump connector, never
// reaching the canvas edge where WYLOT actually is).
export const HydroforSymbol: React.FC<SymbolProps> = ({ state, terminalNetState }) => {
  const on = resolveSiteState(state, HYDROFOR_STATES, 'OFF') === 'ON';
  const vessel = on ? SITE_BLUE : SITE_GREY;
  const wylotLive = (terminalNetState?.('WYLOT') ?? 'INACTIVE') === 'ACTIVE';

  return (
    <Group>
      {bandedRect(10, 73, 108, 8, SITE_CONC, { band: 3, outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}

      {/* Pressure vessel - rounded rect, blue when running, grey when not. */}
      <Rect x={14} y={23} width={42} height={50} cornerRadius={8} fill={vessel.base} stroke={COLOR_OUTLINE} strokeWidth={SITE_OUTLINE_WIDTH} />
      <Rect x={18} y={27} width={6} height={42} fill={vessel.light} listening={false} />
      <Rect x={47} y={27} width={5} height={42} fill={vessel.dark} opacity={0.6} listening={false} />

      {bandedCircleLightOnly(86, 49, 20, on ? SITE_GREEN : SITE_RED)}
      <Line points={[78, 39, 78, 59, 98, 49]} closed fill={SITE_DARK.base} listening={false} />

      {objectPipeSegment([{ x: 56, y: 49 }, { x: 66, y: 49 }], on, { width: 10 })}
      {statusLed(110, 19, on)}

      {/* WYLOT: the vessel's own left wall, out to the true terminal -
          feat/wire-routing-around-obstacles commit 5: reads its OWN
          net state now, not the pump's own on/off appearance. */}
      {waterStub(14, 48, 'L', wylotLive, 128, 96)}
    </Group>
  );
};
