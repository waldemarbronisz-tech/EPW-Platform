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
// DISCREPANCY still applies, unchanged from before this commit
// (raport.md has the full reasoning): this shares its exact task-given
// label, "Zbiornik na deszczowke", with the ALREADY-REGISTERED
// site.rain_tank (RainTankSymbol.tsx, feat/site-objects-2d) - both stay
// registered side by side under the identical display label.
//
// TWO independent things still drive this symbol's own two displays:
//   - GEOMETRY (water bar height, level-window fill, whether ODPLYW
//     reads live) comes from the object's OWN state (NISKI/SREDNI/
//     WYSOKI -> 18/52/88%), exactly like every other site object's
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

export type RainwaterTank2State = 'NISKI' | 'SREDNI' | 'WYSOKI';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as every other site/ symbol.
export const RAINWATER_TANK2_STATES: RainwaterTank2State[] = ['NISKI', 'SREDNI', 'WYSOKI'];

// docs/EPW_kolnierze_referencja.py's own tank(pct): the three named
// states this task gives map to these exact percentages. Exported so
// the no-overlap test (25) can check the percent field's own fixed
// position against the shell/dome/stubs at all three real states
// without rendering anything.
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to, for testability without rendering Konva, same convention DripLineSymbol.tsx's own computeDripperPositions already uses.
export const LEVEL_PERCENT_BY_STATE: Record<RainwaterTank2State, number> = { NISKI: 18, SREDNI: 52, WYSOKI: 88 };

const W = 128, H = 96;
// Exported (not just local consts) so test 25 (the percent field
// never overlaps the shell, at any of the three real states) and test
// 26 (the level window fits inside the shell) can check real
// geometry, not a hand-copied second set of the same numbers.
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to, same reasoning as LEVEL_PERCENT_BY_STATE above.
export const TANK_SHELL_BOUNDS = { x: 26, y: 38, width: 64, height: 40 };
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to, same reasoning as LEVEL_PERCENT_BY_STATE above.
export const TANK_VALUE_FIELD_BOUNDS = { x: 94, y: 30, width: 30, height: 18 };
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to, same reasoning as LEVEL_PERCENT_BY_STATE above.
export const TANK_LEVEL_WINDOW_BOUNDS = {
  x: TANK_SHELL_BOUNDS.x + TANK_SHELL_BOUNDS.width - 18,
  y: TANK_SHELL_BOUNDS.y + 5,
  width: 11,
  height: TANK_SHELL_BOUNDS.height - 10
};
const { x: BX, y: BY, width: BW, height: BH } = TANK_SHELL_BOUNDS;
const CXX = BX + BW / 2;

// fix/wire-routing-around-obstacles commit 4: the one height both
// DOPLYW and ODPLYW krociec runs share - the LEFT/RIGHT terminal's own
// true, fixed edge-midpoint position (H/2), never a hand-picked height
// of its own. Exported so test 24/25 can check it against
// getTerminalOffsetForSide directly, without rendering anything.
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to, same convention as every other exported constant in this file.
export const TANK_TERMINAL_AXIS = H / 2;

// fix/hydraulic-connections commit 6: "Odplyw rysowany jako NIEAKTYWNY,
// gdy poziom wynosi zero" - exported so this exact rule is directly
// testable at pct=0 (none of the three real states - NISKI/SREDNI/
// WYSOKI, 18/52/88% - actually reach zero on their own).
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
  return LEVEL_PERCENT_BY_STATE[resolveSiteState(state || '', RAINWATER_TANK2_STATES, 'NISKI')];
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
      {bandedRect(20, 78, 76, 8, SITE_CONC, { band: 3, outlineWidth: 2 })}

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

      {/* fix/wire-routing-around-obstacles commit 4: DOPLYW/ODPLYW are
          now SINGLE STRAIGHT horizontal krociec runs (waterStub - the
          exact same standard shared function every other water
          aparat's own terminal uses, commit 5 of the previous task),
          not a jogged path. The previous jog ran at y=20 (in) / y=88
          (out) - neither height is the DOPLYW/ODPLYW terminal's own
          true, fixed position: getTerminalOffsetForSide('LEFT'/'RIGHT',
          128, 96) always resolves to the exact edge midpoint, y=48
          (Terminals.ts, unchanged by GRANICE in both this task and the
          previous one) - so that jogged krociec never actually touched
          its own wire-anchoring terminal at all, a worse, hidden defect
          than the visible turn this commit was asked to remove. Both
          stubs now run at y=48, DIRECTLY into the shell wall - straight
          per this commit's own requirement, and for the same reason
          exactly matching the terminal a connected wire actually snaps
          to. docs/EPW_kolnierze_referencja.py's own tank() places these
          off-center (BY+9 / BY+BH-9, distinct heights for in/out) -
          not used literally here, the same kind of documented
          discrepancy raport.md already flagged for this reference
          file's own STUB constant in the previous task: the reference
          is explicit that terminals sit at the canvas's own edge
          midpoint, and that invariant is what a real anchored wire
          depends on, not this one function's own illustrative numbers. */}
      {/* feat/wire-routing-around-obstacles commit 5: the krociec no
          longer carries a color of its own - DOPLYW reads whatever the
          inflow-side NET is (point e: the inflow is never itself a
          source, its state comes purely from what feeds it), and
          ODPLYW reads its own net too, which NetResolver.ts's own new
          rule makes ACTIVE whenever this tank has water (isTankOutflowLive)
          AND something is actually wired to it - an unconnected
          terminal still reads INACTIVE regardless of the water level
          (point c), exactly like every other water aparat's own
          terminal now does. */}
      {waterStub(BX, TANK_TERMINAL_AXIS, 'L', (terminalNetState?.('DOPLYW') ?? 'INACTIVE') === 'ACTIVE', W, H)}
      {waterStub(BX + BW, TANK_TERMINAL_AXIS, 'R', (terminalNetState?.('ODPLYW') ?? 'INACTIVE') === 'ACTIVE', W, H)}

      {/* Level window, now INSIDE the shell - the pre-existing overlap
          this commit fixes came from placing it externally instead. */}
      <Rect {...TANK_LEVEL_WINDOW_BOUNDS} fill={SITE_TANK_WINDOW_BG} stroke={COLOR_OUTLINE} strokeWidth={2} listening={false} />
      {ih > 0 && <Rect x={TANK_LEVEL_WINDOW_BOUNDS.x + 2} y={BY + BH - 7 - ih} width={7} height={ih} fill={SITE_BLUE.base} listening={false} />}

      {/* Percent field, upper-right - clear of the shell, the dome and
          both stubs at all three states (18/52/88%). */}
      {valueField(TANK_VALUE_FIELD_BOUNDS.x, TANK_VALUE_FIELD_BOUNDS.y, TANK_VALUE_FIELD_BOUNDS.width, valueText, { textColor: valueColor })}
    </Group>
  );
};
