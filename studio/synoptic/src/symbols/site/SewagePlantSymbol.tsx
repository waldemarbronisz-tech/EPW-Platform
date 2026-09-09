// feat/site-objects-2d commit 2 - "5. Oczyszczalnia sciekow" from
// docs/EPW_rysunki_referencja.py's own oczyszczalnia(on). A
// rectangular tank with three chambers (each a ringed circle with an
// inner state-colored circle), a spigot on each side, a status lamp.

import React from 'react';
import { Group } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedRect, bandedCircle, waterStub } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import {
  SITE_CONC, SITE_DGREY, SITE_BLUE, SITE_WATER_DIM, SITE_GREEN, SITE_RED,
  SITE_OUTLINE_WIDTH_MEDIUM, SITE_OUTLINE_WIDTH_THIN, SITE_CANVAS_SCALE
} from '../../theme/ScadaTheme';

export type SewagePlantState = 'ZALACZONY' | 'WYLACZONY';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as scada/ symbols.
export const SEWAGE_PLANT_STATES: SewagePlantState[] = ['ZALACZONY', 'WYLACZONY'];

export const SewagePlantSymbol: React.FC<SymbolProps> = ({ state, terminalNetState }) => {
  const on = resolveSiteState(state, SEWAGE_PLANT_STATES, 'WYLACZONY') === 'ZALACZONY';
  const chamberColor = on ? SITE_BLUE : SITE_WATER_DIM;
  const netState = (id: string) => (terminalNetState?.(id) ?? 'INACTIVE') === 'ACTIVE';

  return (
    // SITE_CANVAS_SCALE - see HouseSymbol.tsx's own comment on this
    // same wrapper for the full reasoning.
    <Group scaleX={SITE_CANVAS_SCALE} scaleY={SITE_CANVAS_SCALE}>
      {bandedRect(16, 40, 128, 58, SITE_CONC)}
      {[48, 80, 112].map(cx => (
        <Group key={cx}>
          {bandedCircle(cx, 69, 15, SITE_DGREY, { outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
          {bandedCircle(cx, 69, 8, chamberColor, { outlineWidth: SITE_OUTLINE_WIDTH_THIN })}
        </Group>
      ))}
      {/* fix/hydraulic-connections commit 5: krociec+kolnierz on both
          terminals (WLOT/LEFT, WYLOT/RIGHT) - the true terminal height
          in this file's own pre-scale 160x120 space is y=60, exactly
          the old spigot rects' own TOP edge (their bodies ran DOWN
          from there to y=78, off-axis) and neither reached the true
          edge (stopped 6/6 units short). Replaces both spigot rects
          entirely - "zaden aparat nie rysuje wlasnego kroćca po
          swojemu". */}
      {waterStub(18, 60, 'L', netState('WLOT'), 160, 120)}
      {waterStub(142, 60, 'R', netState('WYLOT'), 160, 120)}
      {bandedCircle(140, 30, 8, on ? SITE_GREEN : SITE_RED, { outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
    </Group>
  );
};
