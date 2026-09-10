// feat/water-management commit 5 - "10. Czujnik deszczu"
// (czujnik_deszczu) from docs/EPW_gospodarka_wodna_referencja.py's own
// czujnik_deszczu(on). SIGNAL - raindrops above the sensor's own
// awning when it is raining, plus a blue status LED (this task's own
// "dioda niebieska" - the one object in this whole library whose LED
// is blue by default rather than green).

import React from 'react';
import { Group, Line, Ellipse, Path } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedRect, statusLed } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import { COLOR_OUTLINE, SITE_DGREY, SITE_GREY, SITE_BLUE, SITE_LED_ON_BLUE, SITE_OUTLINE_WIDTH } from '../../theme/ScadaTheme';

export type RainSensorState = 'ON' | 'OFF';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as every other site/ symbol.
export const RAIN_SENSOR_STATES: RainSensorState[] = ['ON', 'OFF'];

const RAINDROP_POSITIONS = [[30, 16], [46, 8], [62, 14], [80, 7], [96, 17]];

export const RainSensorSymbol: React.FC<SymbolProps> = ({ state }) => {
  const on = resolveSiteState(state, RAIN_SENSOR_STATES, 'OFF') === 'ON';

  return (
    <Group>
      {bandedRect(48, 64, 32, 26, SITE_DGREY)}
      <Line points={[26, 64, 102, 64, 94, 44, 34, 44]} closed fill={SITE_GREY.base} stroke={COLOR_OUTLINE} strokeWidth={SITE_OUTLINE_WIDTH} />
      <Ellipse x={64} y={44} radiusX={32} radiusY={7} fill={SITE_GREY.light} stroke={COLOR_OUTLINE} strokeWidth={SITE_OUTLINE_WIDTH} />
      {on && RAINDROP_POSITIONS.map(([x, y]) => (
        <Path key={x} data={`M${x},${y} q4,9 0,13 q-4,-4 0,-13 Z`} fill={SITE_BLUE.base} stroke={COLOR_OUTLINE} strokeWidth={1.6} listening={false} />
      ))}
      {statusLed(64, 78, on, { color: SITE_LED_ON_BLUE })}
    </Group>
  );
};
