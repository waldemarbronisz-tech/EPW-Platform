// feat/water-management commit 4 - "1. Zbiornik na deszczowke" (tank2)
// - fix/hydraulic-connections commit 6 rebuilds its own connection
// layout entirely from docs/EPW_kolnierze_referencja.py's own,
// UPDATED tank(pct): DOPLYW enters from the LEFT edge into the upper
// part of the shell, ODPLYW leaves to the RIGHT from the shell's lower
// part, both with a krociec+kolnierz (BandedShading.tsx's own
// waterStub/waterFlange - "zaden aparat nie rysuje wlasnego kroćca po
// swojemu" applies here exactly as it does everywhere else). The level
// window moves INSIDE the shell (no longer external - that was this
// object's own pre-existing overlap bug, not a deliberate design), and
// the percent field relocates to the upper-right, clear of the shell,
// the dome and both stubs at every one of the three states.
//
// fix/tank-language-and-media commit 2, point (a): ODPLYW moved AGAIN,
// from the RIGHT edge to the BOTTOM edge - water drains gravitationally
// from the shell's own floor, not sideways out of its wall. The
// krociec is now a single VERTICAL run straight down to the canvas
// edge. DOPLYW is unaffected (still LEFT, still horizontal).
// fix/tank-language-and-media commit 2, point (b): the shell/dome
// drawing itself is significantly enlarged within the same 128x96
// canvas - see TANK_SHELL_BOUNDS' own comment below for the numbers.
//
// DISCREPANCY still applies, unchanged from before this commit
// (raport.md has the full reasoning): this shares its exact task-given
// label, "Zbiornik na deszczowke", with the ALREADY-REGISTERED
// site.rain_tank (RainTankSymbol.tsx, feat/site-objects-2d) - both
// stay registered side by side under the identical display label.
// fix/tank-language-and-media commit 3 removes site.rain_tank from
// the library entirely (hidden, not deleted) - see that commit's own
// section of raport.md - so this discrepancy is resolved going
// forward, just not by this commit.
//
// TWO independent things still drive this symbol's own two displays:
//   - GEOMETRY (water bar height, level-window fill, whether ODPLYW
//     reads live) comes from the object's OWN state (LOW/MEDIUM/
//     HIGH -> 18/52/88%), exactly like every other site object's
//     editor.preview_state.
//   - The VALUE FIELD's own text still comes from the assigned
//     MEASURED device instead, through the EXACT SAME path the meter
//     element's own row already uses - MeterResolver.ts's own
//     getMeasuredPreviewValue/formatMeasuredValue, and
//     MeterElementNode.tsx's own colorForRow for the PREVIEW/MISSING
//     shading - never a second, independently-written resolver. This
//     mechanism is UNCHANGED by this commit.

import React from 'react';
import { Group, Path, Rect } from 'react-konva';
import { useStore } from '../../store';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedRect, valueField, waterStub } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import { findDeviceById, getMeasuredPreviewValue, formatMeasuredValue } from '../../meter/MeterResolver';
import { colorForRow } from '../../components/MeterElementNode';
import {
  COLOR_OUTLINE, SITE_GREY, SITE_DGREY, SITE_BLUE, SITE_CONC, SITE_TANK_WINDOW_BG,
  SITE_OUTLINE_WIDTH
} from '../../theme/ScadaTheme';

export type RainwaterTank2State = 'LOW' | 'MEDIUM' | 'HIGH';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as every other site/ symbol.
export const RAINWATER_TANK2_STATES: RainwaterTank2State[] = ['LOW', 'MEDIUM', 'HIGH'];

// docs/EPW_kolnierze_referencja.py's own tank(pct): the three named
// states this task gives map to these exact percentages. Exported so
// the no-overlap test can check the percent field's own fixed
// position against the shell/dome/stubs at all three real states
// without rendering anything.
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to, for testability without rendering Konva, same convention DripLineSymbol.tsx's own computeDripperPositions already uses.
export const LEVEL_PERCENT_BY_STATE: Record<RainwaterTank2State, number> = { LOW: 18, MEDIUM: 52, HIGH: 88 };

const W = 128, H = 96;

// fix/tank-language-and-media commit 2, point (b): the shell now
// spans 76 of the canvas's own 128 width (>50%, test 11) and 56 of its
// 96 height - a large increase from the previous 64x40 (roughly +66%
// area) so the tank reads clearly on a screen crowded with other
// aparaty, per this commit's own "ginie miedzy zaworami" complaint.
// Centered exactly on the canvas's own horizontal middle (x=26+38=64) -
// deliberately, so the new BOTTOM-edge ODPLYW terminal (also at x=64,
// the fixed side-only rule) lands exactly on the shell's own visual
// center, not an off-center point that would look like a mistake.
// Exported so the no-overlap/no-jog tests can check real geometry,
// not a hand-copied second set of the same numbers.
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to, same reasoning as LEVEL_PERCENT_BY_STATE above.
export const TANK_SHELL_BOUNDS = { x: 26, y: 20, width: 76, height: 56 };
// Upper-right corner, entirely to the right of the shell's own right
// edge (102) - guarantees zero overlap with the shell (and therefore
// the dome, which never extends past the shell's own width either)
// regardless of pct, since neither box's position depends on the
// water level at all.
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to, same reasoning as LEVEL_PERCENT_BY_STATE above.
export const TANK_VALUE_FIELD_BOUNDS = { x: 104, y: 8, width: 22, height: 18 };
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to, same reasoning as LEVEL_PERCENT_BY_STATE above.
export const TANK_LEVEL_WINDOW_BOUNDS = {
  x: TANK_SHELL_BOUNDS.x + TANK_SHELL_BOUNDS.width - 18,
  y: TANK_SHELL_BOUNDS.y + 5,
  width: 11,
  height: TANK_SHELL_BOUNDS.height - 10
};
const { x: BX, y: BY, width: BW, height: BH } = TANK_SHELL_BOUNDS;
const CXX = BX + BW / 2;

// fix/wire-routing-around-obstacles commit 4: the DOPLYW (LEFT)
// terminal's own true, fixed edge-midpoint height (H/2) - never a
// hand-picked height of its own. Exported so tests can check it
// against getTerminalOffsetForSide directly, without rendering
// anything.
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to, same convention as every other exported constant in this file.
export const TANK_TERMINAL_AXIS = H / 2;
// fix/tank-language-and-media commit 2: the ODPLYW (BOTTOM) terminal's
// own true, fixed edge-midpoint position along the bottom edge (W/2) -
// same reasoning as TANK_TERMINAL_AXIS above, for the other axis.
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to, same convention as every other exported constant in this file.
export const TANK_OUTFLOW_AXIS = W / 2;

// fix/hydraulic-connections commit 6: "Odplyw rysowany jako NIEAKTYWNY,
// gdy poziom wynosi zero" - exported so this exact rule is directly
// testable at pct=0 (none of the three real states - LOW/MEDIUM/
// HIGH, 18/52/88% - actually reach zero on their own).
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to, for testability without rendering Konva, same convention DripLineSymbol.tsx's own computeDripperPositions already uses.
export function isTankOutflowLive(pct: number): boolean {
  return pct > 0;
}

// feat/wire-routing-around-obstacles commit 5, point (e): the tank's
// own water level, from its object state alone - exactly what the
// component itself already derived inline, pulled out so NetResolver.ts's
// own "a tank with water is an active source" rule can compute the
// EXACT same number, never a second, parallel derivation of it. Deliberately
// NOT the assigned MEASURED device's own getMeasuredPreviewValue: that
// number is this symbol's own independent, decorative value-field
// reading (see this file's own header, "TWO independent things") -
// unrelated to whether the tank physically holds water, which is what
// governs whether it can act as a source. pct is that physical
// quantity; isTankOutflowLive(pct) is already the correct, established
// "does it have water" test.
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to, for testability without rendering Konva, same convention every other exported constant in this file already uses.
export function tankPercentFromState(state: string | undefined): number {
  return LEVEL_PERCENT_BY_STATE[resolveSiteState(state || '', RAINWATER_TANK2_STATES, 'LOW')];
}

export const RainwaterTank2Symbol: React.FC<SymbolProps> = ({ obj, state, terminalNetState }) => {
  const pct = tankPercentFromState(state);

  const devices = useStore(s => s.devices);
  const device = obj.deviceId ? findDeviceById(devices, obj.deviceId) : undefined;
  const isMeasured = device?.behavior === 'MEASURED';
  const valueText = isMeasured ? `${formatMeasuredValue(getMeasuredPreviewValue(device), device.format)}%` : '?';
  const valueColor = colorForRow(isMeasured ? 'PREVIEW' : 'MISSING');

  const hg = Math.floor((BH - 4) * pct / 100);
  const top = BY + BH - 2 - hg;
  const ih = Math.floor((BH - 14) * pct / 100);

  return (
    <Group>
      {/* fix/tank-language-and-media commit 2: repositioned/resized to
          sit under the new, larger shell (roughly matching its own
          width plus a small overhang), centered on the same x=64 the
          ODPLYW krociec now descends through - drawn first, so that
          krociec (drawn later, below) renders on top of it, exactly
          the way a drain line passing through a base pad actually
          looks. */}
      {bandedRect(20, 78, 88, 8, SITE_CONC, { band: 3, outlineWidth: 2 })}

      {/* Main cylinder body, water fill clipped to its own interior. */}
      <Rect x={BX} y={BY} width={BW} height={BH} fill={SITE_GREY.base} stroke={COLOR_OUTLINE} strokeWidth={SITE_OUTLINE_WIDTH} />
      {hg > 0 && (
        <Group clipFunc={(ctx: any) => { ctx.rect(BX + 2, BY + 2, BW - 4, BH - 4); }}>
          <Rect x={BX + 2} y={top} width={BW - 4} height={hg} fill={SITE_BLUE.base} />
          <Rect x={BX + 2} y={top} width={BW - 4} height={3} fill={SITE_BLUE.light} listening={false} />
        </Group>
      )}
      <Rect x={BX + 2} y={BY + 2} width={5} height={BH - 4} fill={SITE_GREY.light} opacity={0.45} listening={false} />
      <Rect x={BX} y={BY} width={BW} height={BH} stroke={COLOR_OUTLINE} strokeWidth={SITE_OUTLINE_WIDTH} listening={false} />

      {/* Lattice dome. */}
      <Path data={`M${BX},${BY} A${BW / 2},18 0 0 1 ${BX + BW},${BY} Z`} fill={SITE_GREY.base} stroke={COLOR_OUTLINE} strokeWidth={SITE_OUTLINE_WIDTH} />
      {[-22, -11, 0, 11, 22].map(dx => (
        <Path key={dx} data={`M${CXX},${BY - 17} Q${CXX + dx * 1.2},${BY - 12} ${CXX + dx * 1.42},${BY}`} stroke={SITE_DGREY.dark} strokeWidth={1.2} listening={false} />
      ))}
      <Path data={`M${CXX - 22},${BY - 6} A28,13 0 0 1 ${CXX + 22},${BY - 6}`} stroke={SITE_DGREY.dark} strokeWidth={1.2} listening={false} />
      <Path data={`M${BX + 7},${BY - 4} A22,13 0 0 1 ${BX + 24},${BY - 13}`} stroke={SITE_GREY.light} strokeWidth={3.5} lineCap="round" listening={false} />

      {/* DOPLYW: unchanged - a single straight horizontal krociec into
          the shell's own left wall, at the true LEFT terminal height. */}
      {waterStub(BX, TANK_TERMINAL_AXIS, 'L', (terminalNetState?.('DOPLYW') ?? 'INACTIVE') === 'ACTIVE', W, H)}

      {/* fix/tank-language-and-media commit 2, point (a): ODPLYW is now
          a single straight VERTICAL krociec, from the shell's own
          floor straight down to the canvas's bottom edge - water
          drains gravitationally, not sideways. waterStub's own 'B'
          side already does exactly this (bx shared with by=canvas
          edge, by is the along-axis coordinate for a vertical side) -
          the same shared function every other water aparat's terminal
          already uses, not a hand-built path. Reads its own net state
          exactly like DOPLYW - see fix/wire-routing-around-obstacles
          commit 5's own reasoning, unchanged by this move. */}
      {waterStub(TANK_OUTFLOW_AXIS, BY + BH, 'B', (terminalNetState?.('ODPLYW') ?? 'INACTIVE') === 'ACTIVE', W, H)}

      {/* Level window, inside the shell. */}
      <Rect {...TANK_LEVEL_WINDOW_BOUNDS} fill={SITE_TANK_WINDOW_BG} stroke={COLOR_OUTLINE} strokeWidth={2} listening={false} />
      {ih > 0 && <Rect x={TANK_LEVEL_WINDOW_BOUNDS.x + 2} y={BY + BH - 7 - ih} width={7} height={ih} fill={SITE_BLUE.base} listening={false} />}

      {/* Percent field, upper-right - entirely clear of the (now
          larger) shell, the dome and both stubs at all three states
          (18/52/88%), since none of those move the shell's own
          static bounds. */}
      {valueField(TANK_VALUE_FIELD_BOUNDS.x, TANK_VALUE_FIELD_BOUNDS.y, TANK_VALUE_FIELD_BOUNDS.width, valueText, { textColor: valueColor })}
    </Group>
  );
};
