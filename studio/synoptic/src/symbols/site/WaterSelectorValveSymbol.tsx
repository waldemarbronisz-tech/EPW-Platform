// feat/water-management commit 4 - "3. Zawor trojdrogowy
// trojpolozeniowy" (zawor3sel) from docs/EPW_gospodarka_wodna_
// referencja.py's own zawor3sel(pos). Uses the existing SELECTOR
// behavior unchanged (no contract change at all, per GRANICE) - three
// positions, three LEDs, a red cross-shaped wedge shown in the body
// when CLOSED (both outlet branches read inactive then).
//
// State name: the reference's own Python checks `pos=='ZAMK'` (an
// abbreviation, purely for brevity in that pattern file) but this
// task's own prose spells the middle position out in full -
// "CLOSED" - matching the same full-word convention every other
// site object's own states already use (e.g. sliding gate's CLOSED/
// OPEN). The exposed state string here is 'CLOSED', not the
// reference's own shortened 'ZAMK'.

import React from 'react';
import { Group, Rect, Path, Line, Text } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedRect, bandedCircleLightOnly, statusLed, waterStub } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import {
  COLOR_OUTLINE, SITE_DGREY, SITE_GREEN, SITE_BLUE, SITE_RED, SITE_LED_ON_RED,
  SITE_LEVER_WIDTH, SITE_LEVER_ARROW_WIDTH, SITE_OUTLINE_WIDTH_MEDIUM
} from '../../theme/ScadaTheme';

export type WaterSelectorValveState = 'A' | 'CLOSED' | 'B';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as every other site/ symbol.
export const WATER_SELECTOR_VALVE_STATES: WaterSelectorValveState[] = ['A', 'CLOSED', 'B'];

// fix/hydraulic-connections commit 5: was 58,54 - see WaterValveSymbol.tsx's
// own comment on this identical change; every other coordinate here is
// already relative to CX/CY.
const CX = 64, CY = 48;

export const WaterSelectorValveSymbol: React.FC<SymbolProps> = ({ state, terminalNetState }) => {
  const resolved = resolveSiteState(state, WATER_SELECTOR_VALVE_STATES, 'CLOSED');
  const isA = resolved === 'A';
  const isB = resolved === 'B';
  const isClosed = resolved === 'CLOSED';
  const netState = (id: string) => (terminalNetState?.(id) ?? 'INACTIVE') === 'ACTIVE';

  return (
    <Group>
      {/* feat/wire-routing-around-obstacles commit 5: each terminal's
          krociec reads its own net now, not this valve's own position -
          isA/isB/isClosed still drive the lever/wedge artwork below,
          unchanged. */}
      {waterStub(CX, CY, 'L', netState('WLOT'), 128, 96)}
      {waterStub(CX, CY, 'R', netState('WYLOT_A'), 128, 96)}
      {waterStub(CX, CY, 'B', netState('WYLOT_B'), 128, 96)}
      {bandedCircleLightOnly(CX, CY, 17, SITE_DGREY)}

      {isClosed ? (
        <Group listening={false}>
          <Rect x={CX - 14} y={CY - 4} width={28} height={8} fill={SITE_RED.base} stroke={COLOR_OUTLINE} strokeWidth={2} />
          <Rect x={CX - 4} y={CY - 14} width={8} height={28} fill={SITE_RED.base} stroke={COLOR_OUTLINE} strokeWidth={2} />
        </Group>
      ) : (
        <Group x={CX} y={CY} rotation={isA ? 0 : 90} listening={false}>
          <Path data="M-13,0 L13,0" stroke={SITE_BLUE.base} strokeWidth={SITE_LEVER_WIDTH} lineCap="round" />
          <Path data="M6,-6 L13,0 L6,6" stroke={SITE_BLUE.base} strokeWidth={SITE_LEVER_ARROW_WIDTH} lineJoin="round" />
        </Group>
      )}

      {bandedRect(CX - 11, CY - 38, 22, 20, SITE_GREEN, { band: 3, outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
      <Line points={[CX, CY - 18, CX, CY - 16]} stroke={COLOR_OUTLINE} strokeWidth={7} listening={false} />

      {statusLed(CX - 30, CY - 48, isA)}
      <Text x={CX - 40} y={CY - 62} width={20} align="center" text="A" fontSize={10} fontStyle="bold" fill={COLOR_OUTLINE} listening={false} />
      {statusLed(CX, CY - 48, isClosed, { color: SITE_LED_ON_RED })}
      <Text x={CX - 10} y={CY - 62} width={20} align="center" text="Z" fontSize={10} fontStyle="bold" fill={COLOR_OUTLINE} listening={false} />
      {statusLed(CX + 30, CY - 48, isB)}
      <Text x={CX + 20} y={CY - 62} width={20} align="center" text="B" fontSize={10} fontStyle="bold" fill={COLOR_OUTLINE} listening={false} />
    </Group>
  );
};
