// feat/water-management commit 4 - "2. Zawor trojdrogowy przelaczajacy"
// (zawor3) from docs/EPW_gospodarka_wodna_referencja.py's own
// zawor3(pos). SWITCHED, DUAL feedback: diClosed/diOpen are repurposed
// as "krancowka A"/"krancowka B" for this device (see DeviceFormDialog.tsx's
// own commit 4 change to the field labels for a three-way valve kind -
// the underlying diClosed/diOpen fields themselves are UNCHANGED, per
// GRANICE's "nie modyfikuj DeviceSchema.ts"). Two positions, A and B -
// whichever branch is NOT currently selected reads as inactive
// (unpowered pipe stub), matching this task's own "Nitka bez przeplywu
// rysowana jako nieaktywna".

import React from 'react';
import { Group, Path, Line, Text } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedRect, bandedCircleLightOnly, statusLed, waterStub } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import { COLOR_OUTLINE, SITE_DGREY, SITE_GREEN, SITE_BLUE, SITE_LEVER_WIDTH, SITE_LEVER_ARROW_WIDTH, SITE_OUTLINE_WIDTH_MEDIUM } from '../../theme/ScadaTheme';

export type WaterValveState = 'A' | 'B';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as every other site/ symbol.
export const WATER_VALVE_STATES: WaterValveState[] = ['A', 'B'];

// fix/hydraulic-connections commit 5: was 58,54 - the true WLOT (LEFT)/
// WYLOT_A (RIGHT)/WYLOT_B (BOTTOM) terminals sit at x=64 (canvas
// half-width) and y=48 (half-height), not 58/54. Every other
// coordinate in this file is already expressed relative to CX/CY, so
// this one change re-centers the whole body on the real terminals.
const CX = 64, CY = 48;

export const WaterValveSymbol: React.FC<SymbolProps> = ({ state, terminalNetState }) => {
  const isA = resolveSiteState(state, WATER_VALVE_STATES, 'A') === 'A';
  const angle = isA ? 0 : 90;
  const netState = (id: string) => (terminalNetState?.(id) ?? 'INACTIVE') === 'ACTIVE';

  return (
    <Group>
      {/* feat/wire-routing-around-obstacles commit 5, point (b): each
          terminal now reads its OWN net - the earlier hardcoded WLOT=
          true, WYLOT_A=isA, WYLOT_B=!isA (the valve's own position,
          not real connectivity) is exactly the usterka this task's own
          example describes ("zawor zamkniety ma po jednej stronie
          krociec niebieski, po drugiej szary"). isA still drives the
          lever's own drawn position below, unchanged. */}
      {waterStub(CX, CY, 'L', netState('WLOT'), 128, 96)}
      {waterStub(CX, CY, 'R', netState('WYLOT_A'), 128, 96)}
      {waterStub(CX, CY, 'B', netState('WYLOT_B'), 128, 96)}
      {bandedCircleLightOnly(CX, CY, 17, SITE_DGREY)}

      {/* Lever handle - rotates about (CX,CY): a Konva Group pivoting
          on its own x/y is the direct equivalent of the reference's own
          transform="rotate(ang cx cy)", with the lever's geometry drawn
          relative to that pivot instead of absolute coordinates. */}
      <Group x={CX} y={CY} rotation={angle} listening={false}>
        <Path data="M-13,0 L13,0" stroke={SITE_BLUE.base} strokeWidth={SITE_LEVER_WIDTH} lineCap="round" />
        <Path data="M6,-6 L13,0 L6,6" stroke={SITE_BLUE.base} strokeWidth={SITE_LEVER_ARROW_WIDTH} lineJoin="round" />
      </Group>

      {bandedRect(CX - 11, CY - 38, 22, 20, SITE_GREEN, { band: 3, outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
      <Line points={[CX, CY - 18, CX, CY - 16]} stroke={COLOR_OUTLINE} strokeWidth={7} listening={false} />

      {statusLed(CX - 22, CY - 46, isA)}
      <Text x={CX - 32} y={CY - 60} width={20} align="center" text="A" fontSize={10} fontStyle="bold" fill={COLOR_OUTLINE} listening={false} />
      {statusLed(CX + 22, CY - 46, !isA)}
      <Text x={CX + 12} y={CY - 60} width={20} align="center" text="B" fontSize={10} fontStyle="bold" fill={COLOR_OUTLINE} listening={false} />
    </Group>
  );
};
