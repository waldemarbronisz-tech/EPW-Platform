// feat/water-management commit 4 - "4. Zawor zwrotny" (zawor_zwrotny2)
// from docs/EPW_gospodarka_wodna_referencja.py's own zawor_zwrotny2(live).
// Pure graphics - no tag, no aparat (GRANICE/task both explicit on
// this). A hinged flapper: angled open when flowing, vertical (shut)
// when not, plus a direction arrow above the body.

import React from 'react';
import { Group, Path, Circle } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedRect, waterStub } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import { COLOR_OUTLINE, SITE_GREY, SITE_GREEN, SITE_RED } from '../../theme/ScadaTheme';

export type CheckValveState = 'ON' | 'OFF';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as every other site/ symbol.
export const CHECK_VALVE_STATES: CheckValveState[] = ['ON', 'OFF'];

// fix/hydraulic-connections commit 5: the whole body shifted up by 6
// (was centered on y=54, the true WLOT/WYLOT terminal height is 48) so
// the krociec/kolnierz standard lands exactly on the real terminal
// instead of 6 units off it.
export const CheckValveSymbol: React.FC<SymbolProps> = ({ state, terminalNetState }) => {
  const live = resolveSiteState(state, CHECK_VALVE_STATES, 'OFF') === 'ON';
  const netState = (id: string) => (terminalNetState?.(id) ?? 'INACTIVE') === 'ACTIVE';

  return (
    <Group>
      {/* feat/wire-routing-around-obstacles commit 5: the krociec no
          longer carries the valve's own open/closed state - it reads
          the net each terminal actually belongs to (point b: WLOT and
          WYLOT can disagree, since they are on different nets). `live`
          (the valve's own state) still drives the flapper's own
          visual below, unchanged. */}
      {waterStub(42, 48, 'L', netState('WLOT'), 128, 96)}
      {waterStub(86, 48, 'R', netState('WYLOT'), 128, 96)}
      {bandedRect(42, 30, 44, 36, SITE_GREY)}

      {/* Hinged flapper - angled open (live) or vertical shut (not). */}
      {live ? (
        <Group listening={false}>
          <Path data="M52,36 L74,54" stroke={COLOR_OUTLINE} strokeWidth={7} lineCap="round" />
          <Path data="M52,36 L74,54" stroke={SITE_GREEN.base} strokeWidth={4} lineCap="round" />
        </Group>
      ) : (
        <Group listening={false}>
          <Path data="M52,36 L52,62" stroke={COLOR_OUTLINE} strokeWidth={7} lineCap="round" />
          <Path data="M52,36 L52,62" stroke={SITE_RED.base} strokeWidth={4} lineCap="round" />
        </Group>
      )}
      <Circle x={52} y={36} radius={3.5} fill={COLOR_OUTLINE} listening={false} />

      {/* Flow-direction arrow above the body. */}
      <Path data="M92,20 L108,20 M102,14 L108,20 L102,26" stroke={COLOR_OUTLINE} strokeWidth={2.5} lineJoin="round" listening={false} />
    </Group>
  );
};
