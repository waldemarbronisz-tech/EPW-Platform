// feat/site-objects-2d commit 3 - "12. Kogut alarmowy czerwony" from
// docs/EPW_rysunki_referencja.py's own kogut(on). A dome on a base,
// with a highlight arc and, when lit, a glow plus three radiating
// rays. The dome/highlight arcs are literal SVG path data (elliptical
// arcs, same as bandedCircle's own light/shadow arcs) reproduced
// through Konva's own Path shape - the reference draws these two arcs
// directly rather than through its own C.circ(), so this component
// does the same rather than forcing them through bandedCircle.

import React from 'react';
import { Group, Line, Path } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedRect, glow } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import {
  COLOR_OUTLINE, SITE_DGREY, SITE_RED, SITE_RED_DIM, SITE_RED_DIM_HIGHLIGHT,
  SITE_ALARM_GLOW, SITE_ALARM_RAY, SITE_ALARM_RAY_WIDTH,
  SITE_OUTLINE_WIDTH, SITE_CROSSBAR_WIDTH, SITE_CANVAS_SCALE
} from '../../theme/ScadaTheme';

export type AlarmBeaconState = 'ON' | 'OFF';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as scada/ symbols.
export const ALARM_BEACON_STATES: AlarmBeaconState[] = ['ON', 'OFF'];

// Three rays at -60/-90/-120 degrees from the dome's own center, radius
// 34 to 48 - docs/EPW_rysunki_referencja.py's own `for a in
// ((-60,1),(-90,1),(-120,1))` loop (the second tuple element, `l`, is
// never actually used there either - only the angle matters).
const RAY_ANGLES_DEG = [-60, -90, -120];

export const AlarmBeaconSymbol: React.FC<SymbolProps> = ({ state }) => {
  const on = resolveSiteState(state, ALARM_BEACON_STATES, 'OFF') === 'ON';
  const dome = on ? SITE_RED : SITE_RED_DIM;
  const highlight = on ? SITE_RED.light : SITE_RED_DIM_HIGHLIGHT;

  return (
    <Group scaleX={SITE_CANVAS_SCALE} scaleY={SITE_CANVAS_SCALE}>
      {bandedRect(60, 86, 40, 20, SITE_DGREY)}
      {on && glow(80, 56, 30, { color: SITE_ALARM_GLOW })}
      <Path data="M52,86 A28,34 0 0 1 108,86 Z" fill={dome.base} stroke={COLOR_OUTLINE} strokeWidth={SITE_OUTLINE_WIDTH} />
      <Path data="M60,72 A22,26 0 0 1 74,50" stroke={highlight} strokeWidth={SITE_CROSSBAR_WIDTH} lineCap="round" />
      {on && RAY_ANGLES_DEG.map(deg => {
        const rad = (deg * Math.PI) / 180;
        const x1 = 80 + 34 * Math.cos(rad);
        const y1 = 70 + 34 * Math.sin(rad);
        const x2 = 80 + 48 * Math.cos(rad);
        const y2 = 70 + 48 * Math.sin(rad);
        return <Line key={deg} points={[x1, y1, x2, y2]} stroke={SITE_ALARM_RAY} strokeWidth={SITE_ALARM_RAY_WIDTH} lineCap="round" listening={false} />;
      })}
    </Group>
  );
};
