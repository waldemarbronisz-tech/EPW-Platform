// feat/site-objects-2d commit 3 - "13. Glosnik alarmowy, tuba" from
// docs/EPW_rysunki_referencja.py's own tuba(on). A horn on a body,
// with a seam line down its own bell and, when lit, three
// sound-wave arcs in front of the opening.

import React from 'react';
import { Group, Line, Path } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedRect } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import {
  COLOR_OUTLINE, COLOR_LAMP_LIT, SITE_DGREY, SITE_GREY, SITE_HORN_LIT, SITE_DARK,
  SITE_BAND_WIDTH, SITE_BAND_WIDTH_NARROW, SITE_OUTLINE_WIDTH, SITE_OUTLINE_WIDTH_MEDIUM, SITE_CANVAS_SCALE
} from '../../theme/ScadaTheme';

export type AlarmHornState = 'ON' | 'OFF';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as scada/ symbols.
export const ALARM_HORN_STATES: AlarmHornState[] = ['ON', 'OFF'];

// Three sound-wave arcs, each a fixed x/opacity pair -
// docs/EPW_rysunki_referencja.py's own `for i,(x,op) in enumerate(...)`
// loop. Opacity kept local (a shape/rendering ratio, not a palette
// color/thickness) - same convention as bandedCircle/glow's own
// proportions in BandedShading.tsx.
const SOUND_WAVES = [
  { x: 132, opacity: 0.55 },
  { x: 142, opacity: 0.38 },
  { x: 152, opacity: 0.22 }
];

export const AlarmHornSymbol: React.FC<SymbolProps> = ({ state }) => {
  const on = resolveSiteState(state, ALARM_HORN_STATES, 'OFF') === 'ON';
  const horn = on ? SITE_HORN_LIT : SITE_GREY;

  return (
    <Group scaleX={SITE_CANVAS_SCALE} scaleY={SITE_CANVAS_SCALE}>
      {bandedRect(30, 52, 26, 28, SITE_DGREY)}
      <Line points={[56, 42, 120, 20, 120, 110, 56, 90]} closed fill={horn.base} stroke={COLOR_OUTLINE} strokeWidth={SITE_OUTLINE_WIDTH} />
      <Line points={[120, 20, 120, 110]} stroke={COLOR_OUTLINE} strokeWidth={SITE_BAND_WIDTH_NARROW} />
      {on && SOUND_WAVES.map((wave, i) => (
        <Path
          key={wave.x}
          data={`M${wave.x},${34 + i * 4} Q${wave.x + 9},65 ${wave.x},${96 - i * 4}`}
          stroke={COLOR_LAMP_LIT}
          strokeWidth={SITE_BAND_WIDTH}
          opacity={wave.opacity}
          listening={false}
        />
      ))}
      {bandedRect(18, 58, 14, 16, SITE_DARK, { band: SITE_BAND_WIDTH_NARROW, outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
    </Group>
  );
};
