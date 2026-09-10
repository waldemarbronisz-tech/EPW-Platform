// feat/water-management commit 5 - "7. Przeplywomierz" (przeplyw2)
// from docs/EPW_gospodarka_wodna_referencja.py's own przeplyw2(on).
// MEASURED - instantaneous flow. Reads its own value through the EXACT
// SAME path as the meter element (MeterResolver.ts's own
// getMeasuredPreviewValue/formatMeasuredValue, findDeviceById;
// MeterElementNode.tsx's own colorForRow for PREVIEW/MISSING shading) -
// GRANICE names this object explicitly alongside the tank for that
// requirement. Unlike wodomierz2 (the water meter, a running total
// that never resets), this one shows a fixed "0.0" whenever there is
// no flow, regardless of what the device itself is configured to -
// an INSTANTANEOUS reading has nothing to show when nothing is
// flowing. The direction arrow is likewise only ever drawn while
// flowing.

import React from 'react';
import { Group, Circle, Text, Path } from 'react-konva';
import { useStore } from '../../store';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedCircleLightOnly, waterStub } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import { findDeviceById, getMeasuredPreviewValue, formatMeasuredValue } from '../../meter/MeterResolver';
import { colorForRow } from '../../components/MeterElementNode';
import { COLOR_OUTLINE, COLOR_WHITE, SITE_GREY, SITE_LCD_BACKGROUND } from '../../theme/ScadaTheme';

export type FlowMeterState = 'ON' | 'OFF';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as every other site/ symbol.
export const FLOW_METER_STATES: FlowMeterState[] = ['ON', 'OFF'];

export const FlowMeterSymbol: React.FC<SymbolProps> = ({ obj, state, terminalNetState }) => {
  const on = resolveSiteState(state, FLOW_METER_STATES, 'OFF') === 'ON';
  const netState = (id: string) => (terminalNetState?.(id) ?? 'INACTIVE') === 'ACTIVE';

  const devices = useStore(s => s.devices);
  const device = obj.deviceId ? findDeviceById(devices, obj.deviceId) : undefined;
  const isMeasured = device?.behavior === 'MEASURED';
  const valueText = !on ? '0.0' : (isMeasured ? formatMeasuredValue(getMeasuredPreviewValue(device), device.format) : '?');
  const valueColor = colorForRow(isMeasured ? 'PREVIEW' : 'MISSING');

  return (
    <Group>
      {/* fix/hydraulic-connections commit 5: krociec+kolnierz at both
          terminals, from the dial's own horizontal edges (x=44/84,
          already at the true terminal height y=48) - the old single
          pipe (y=62, 14 units off the real terminal) and its own
          dial-to-pipe connector line are retired; the dial's own
          circle now sits directly astride the pipe run instead. */}
      {waterStub(44, 48, 'L', netState('WLOT'), 128, 96)}
      {waterStub(84, 48, 'R', netState('WYLOT'), 128, 96)}
      {bandedCircleLightOnly(64, 36, 20, SITE_GREY)}
      <Circle x={64} y={36} radius={14} fill={SITE_LCD_BACKGROUND} stroke={COLOR_OUTLINE} strokeWidth={2} listening={false} />
      <Text x={39} y={31} width={50} align="center" text={valueText} fontFamily="Consolas, DejaVu Sans Mono, monospace" fontSize={11} fontStyle="bold" fill={valueColor} listening={false} />
      <Text x={44} y={11} width={40} align="center" text="l/min" fontSize={9} fontStyle="bold" fill={COLOR_OUTLINE} listening={false} />
      {on && <Path data="M92,48 L108,48 M102,42 L108,48 L102,54" stroke={COLOR_WHITE} strokeWidth={2.5} lineJoin="round" listening={false} />}
    </Group>
  );
};
