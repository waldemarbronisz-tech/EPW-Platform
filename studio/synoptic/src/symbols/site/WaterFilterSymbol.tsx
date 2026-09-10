// feat/water-management commit 4 - "5. Filtr wody" (filtr) from docs/
// EPW_gospodarka_wodna_referencja.py's own filtr(on). Pure graphics -
// no tag, no aparat.

import React from 'react';
import { Group, Path, Rect, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedRect, waterStub } from './BandedShading';
import { COLOR_OUTLINE, SITE_GREY, SITE_DGREY, SITE_OUTLINE_WIDTH } from '../../theme/ScadaTheme';

export type WaterFilterState = 'ON' | 'OFF';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as every other site/ symbol.
export const WATER_FILTER_STATES: WaterFilterState[] = ['ON', 'OFF'];

// feat/wire-routing-around-obstacles commit 5: ON/OFF used
// to only ever affect this symbol's own krociec (nothing else in its
// body reads `state` at all) - now that the krociec reads net state
// instead, this object's own body draws identically regardless of its
// state, same as before this commit's fix except now correctly so.
export const WaterFilterSymbol: React.FC<SymbolProps> = ({ terminalNetState }) => {
  const netState = (id: string) => (terminalNetState?.(id) ?? 'INACTIVE') === 'ACTIVE';

  return (
    <Group>
      {/* fix/hydraulic-connections commit 5: krociec+kolnierz on both
          terminals (WLOT/LEFT, WYLOT/RIGHT), each running from the
          flask's own wall (x=44/84, already at y=48 - the true
          terminal height) straight out to the canvas edge - the old
          single edge-to-edge pipe (y=40, 8 units off the real
          terminal) is retired in favor of this.
          feat/wire-routing-around-obstacles commit 5: each krociec now
          colors from its OWN terminal's net state, not this object's
          own on/off state. */}
      {waterStub(44, 48, 'L', netState('WLOT'), 128, 96)}
      {waterStub(84, 48, 'R', netState('WYLOT'), 128, 96)}

      {/* Flask-shaped filter body. */}
      <Path data="M44,48 L84,48 L84,74 Q64,88 44,74 Z" fill={SITE_GREY.base} stroke={COLOR_OUTLINE} strokeWidth={SITE_OUTLINE_WIDTH} />
      <Rect x={48} y={52} width={5} height={24} fill={SITE_GREY.light} listening={false} />
      {[0, 1, 2, 3].map(i => (
        <Line key={i} points={[50, 56 + i * 6, 78, 56 + i * 6]} stroke={SITE_DGREY.dark} strokeWidth={1.6} listening={false} />
      ))}

      {bandedRect(46, 34, 36, 14, SITE_GREY, { band: 3, outlineWidth: 2 })}
    </Group>
  );
};
