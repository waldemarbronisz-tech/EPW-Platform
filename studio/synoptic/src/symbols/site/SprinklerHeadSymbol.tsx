// feat/water-management commit 5 - "11. Zraszacz" (zraszacz) from
// docs/EPW_gospodarka_wodna_referencja.py's own zraszacz(on). Pure
// graphics - no tag: this task is explicit that the real aparat is the
// ZONE VALVE feeding it, not the individual sprinkler head. A separate
// object from the earlier site.garden_sprinkler ("Slupek podlewania
// ogrodowego", feat/site-objects-2d - a garden watering POST with its
// own WATER terminal) - different label, different geometry (this one
// is a low, flush pop-up head, not a post), no naming collision.

import React from 'react';
import { Group, Path } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedRect, bandedVRect, bandedCircleLightOnly, waterStub } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import { SITE_CONC, SITE_DGREY, SITE_BLUE, SITE_SPRAY_BLUE, SITE_OUTLINE_WIDTH_MEDIUM } from '../../theme/ScadaTheme';

export type SprinklerHeadState = 'ZALACZONY' | 'WYLACZONY';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as every other site/ symbol.
export const SPRINKLER_HEAD_STATES: SprinklerHeadState[] = ['ZALACZONY', 'WYLACZONY'];

const ARC_DX = [-34, -18, 0, 18, 34];

export const SprinklerHeadSymbol: React.FC<SymbolProps> = ({ state, terminalNetState }) => {
  const on = resolveSiteState(state, SPRINKLER_HEAD_STATES, 'WYLACZONY') === 'ZALACZONY';
  const wodaLive = (terminalNetState?.('WODA') ?? 'INACTIVE') === 'ACTIVE';

  return (
    <Group>
      {/* fix/hydraulic-connections commit 5: krociec+kolnierz on the
          one terminal (WODA, BOTTOM) - this object had NONE at all
          before (the concrete pad's own bottom edge, y=88, never
          reached the true terminal at y=96).
          feat/wire-routing-around-obstacles commit 5: reads its own
          net state, not this object's own on/off appearance. */}
      {waterStub(64, 88, 'B', wodaLive, 128, 96)}
      {bandedRect(46, 72, 36, 16, SITE_CONC, { band: 3, outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
      {bandedVRect(56, 52, 16, 22, SITE_DGREY, { band: 3 })}
      {bandedCircleLightOnly(64, 48, 9, on ? SITE_BLUE : SITE_DGREY, { outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
      {on && ARC_DX.map(dx => (
        <Path key={dx} data={`M64,42 Q${64 + dx * 1.4},10 ${64 + dx * 2.0},44`} stroke={SITE_SPRAY_BLUE} strokeWidth={3} opacity={0.8} listening={false} />
      ))}
    </Group>
  );
};
