// feat/water-management commit 5 - "9. Presostat" (presostat) from
// docs/EPW_gospodarka_wodna_referencja.py's own presostat(on). SIGNAL -
// dry-run signalling (a low/no-pressure alarm), not a controllable
// device - a manometer with a needle plus a status LED. The main pipe
// is always drawn live (the reference's own literal `True`): a
// presostat sits on a pressurised line regardless of whether it is
// currently signalling an alarm.

import React from 'react';
import { Group, Circle, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedVRect, bandedCircleLightOnly, statusLed, waterStub } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import { COLOR_OUTLINE, SITE_GREY, SITE_TANK_WINDOW_BG, SITE_GAUGE_NEEDLE } from '../../theme/ScadaTheme';

export type PressureSwitchState = 'ZALACZONY' | 'WYLACZONY';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as every other site/ symbol.
export const PRESSURE_SWITCH_STATES: PressureSwitchState[] = ['ZALACZONY', 'WYLACZONY'];

export const PressureSwitchSymbol: React.FC<SymbolProps> = ({ state, terminalNetState }) => {
  const on = resolveSiteState(state, PRESSURE_SWITCH_STATES, 'WYLACZONY') === 'ZALACZONY';
  const netState = (id: string) => (terminalNetState?.(id) ?? 'INACTIVE') === 'ACTIVE';
  const angle = (on ? -40 : -140) * (Math.PI / 180);
  const needleX = 64 + 10 * Math.cos(angle);
  const needleY = 32 + 10 * Math.sin(angle);

  return (
    <Group>
      {/* fix/hydraulic-connections commit 5: krociec+kolnierz at both
          terminals, from the mount's own walls (x=52/76) at the true
          terminal height y=48 - within the mount's own y44-68 span, so
          the pipe passes directly behind it. The old pipe (y=74, 26
          units off the real terminal, past the mount entirely) is
          retired.
          feat/wire-routing-around-obstacles commit 5: no longer always
          drawn live - each side now reads its own net's state. */}
      {waterStub(52, 48, 'L', netState('WLOT'), 128, 96)}
      {waterStub(76, 48, 'R', netState('WYLOT'), 128, 96)}
      {bandedVRect(52, 44, 24, 24, SITE_GREY, { band: 3 })}
      {bandedCircleLightOnly(64, 32, 17, SITE_GREY)}
      <Circle x={64} y={32} radius={12} fill={SITE_TANK_WINDOW_BG} stroke={COLOR_OUTLINE} strokeWidth={2} listening={false} />
      <Line points={[64, 32, needleX, needleY]} stroke={SITE_GAUGE_NEEDLE} strokeWidth={2.5} lineCap="round" listening={false} />
      <Circle x={64} y={32} radius={2.5} fill={COLOR_OUTLINE} listening={false} />
      {statusLed(100, 32, on)}
    </Group>
  );
};
