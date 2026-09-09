// SCADA-style symbol 8/9: indicator diode - a small, pure status dot. No
// conductor, no ports (per the task's own spec for this symbol).

import React from 'react';
import { Circle, Group } from 'react-konva';
import {
  COLOR_OUTLINE, DIODE_RADIUS_SMALL, DIODE_RADIUS_LARGE,
  DIODE_ON, DIODE_ON_CORE, DIODE_OFF, DIODE_ALARM, DIODE_ALARM_CORE, DIODE_QUALITY, DIODE_QUALITY_CORE
} from '../../theme/ScadaTheme';

// feat/selector-symbol-setpoint-alarm: ALARM joins the three original
// states - see this file's own getIndicatorDiodeFillColor/CoreColor
// comment below for what it wires into, and SignalPanelResolver.ts for
// the one place a device's own behavior now picks it automatically.
export type IndicatorDiodeState = 'ON' | 'OFF' | 'QUALITY' | 'ALARM';
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this state list belongs beside its component.
export const INDICATOR_DIODE_STATES: IndicatorDiodeState[] = ['ON', 'OFF', 'QUALITY', 'ALARM'];

export type IndicatorDiodeSize = 'small' | 'large';

// feat/appearance-selection-frames commit 1: the two radii used to be
// literal numbers (8/12) local to this file - now ScadaTheme.ts's own
// DIODE_RADIUS_SMALL/DIODE_RADIUS_LARGE, so a signal panel's diode
// (which reuses this same helper, see SignalPanelElementNode.tsx) and
// this symbol always shrink or grow together, from one source.
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this helper belongs beside its component.
export function getIndicatorDiodeRadius(size: IndicatorDiodeSize): number {
  return size === 'small' ? DIODE_RADIUS_SMALL : DIODE_RADIUS_LARGE;
}

// fix/handles-insert-mode-diodes commit 3a: the diode's own fill,
// deliberately from ScadaTheme's dedicated DIODE_* set rather than the
// COLOR_RUN/COLOR_LAMP_LIT every other symbol's state color reuses -
// see that constant's own comment for why.
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this helper belongs beside its component.
export function getIndicatorDiodeFillColor(state: IndicatorDiodeState): string {
  if (state === 'ON') return DIODE_ON;
  if (state === 'QUALITY') return DIODE_QUALITY;
  if (state === 'ALARM') return DIODE_ALARM;
  return DIODE_OFF; // OFF
}

// 3b/3c: a LIT state (ON, QUALITY, ALARM) gets a brighter, smaller
// inner circle - the highlight that reads as an actual light source,
// not a painted disc. OFF returns null: no inner circle at all is what
// signals "not lit" (3c is explicit that this must be the absence of
// a highlight, not a color choice of its own).
//
// feat/selector-symbol-setpoint-alarm: ALARM now wired in (was
// previously flagged as unreachable dead colors - DIODE_ALARM/
// DIODE_ALARM_CORE existed in ScadaTheme.ts per an earlier fix's own
// 3a spec, but no state ever produced them). See SignalPanelResolver.ts
// for the one place a device's own behavior picks this automatically
// (a SIGNAL device's row previews ALARM, not a generic ON - a SIGNAL
// device's whole reason for existing is alarm signalling); everywhere
// else (a manual signal-panel row, a placed Indicator Diode symbol's
// own preview_state) it is simply one more choice in the same
// INDICATOR_DIODE_STATES list PropertyInspector.tsx's dropdown already
// reads, no special-casing needed there.
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this helper belongs beside its component.
export function getIndicatorDiodeCoreColor(state: IndicatorDiodeState): string | null {
  if (state === 'ON') return DIODE_ON_CORE;
  if (state === 'QUALITY') return DIODE_QUALITY_CORE;
  if (state === 'ALARM') return DIODE_ALARM_CORE;
  return null; // OFF - no highlight, on purpose
}

// Core circle proportions - a dimension, not a palette color, so it
// stays a local literal per ScadaTheme.ts's own header rule (that file
// holds colors/thicknesses the task gives explicitly, not every
// derived geometry ratio). "roughly half the diode's own radius,
// offset slightly up-and-left" per this fix's own 3b spec.
const DIODE_CORE_RADIUS_FRACTION = 0.5;
const DIODE_CORE_OFFSET_FRACTION = 0.3;

// Exported for the exact same reason DIODE_OUTLINE_WIDTH below already
// is: SignalPanelElementNode.tsx draws its own diode circles rather
// than rendering this component directly (a row also needs its own
// label Text beside the diode), but must still match this symbol's
// own look EXACTLY, core highlight included - not a coincidentally
// equal, separately hand-tuned duplicate of it.
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this helper belongs beside its component.
export function getIndicatorDiodeCoreGeometry(radius: number): { radius: number; offset: number } {
  return { radius: radius * DIODE_CORE_RADIUS_FRACTION, offset: radius * DIODE_CORE_OFFSET_FRACTION };
}

export interface IndicatorDiodeSymbolProps {
  state: IndicatorDiodeState;
  size: IndicatorDiodeSize;
}

// feat/editing-and-signal-panel commit 6: exported so the signal panel
// element's own diode rows (SignalPanelElementNode.tsx) draw with
// EXACTLY this symbol's own outline weight, not a coincidentally equal
// duplicate of it - "use the existing Indicator Diode symbol where it
// can be reused" extends to this constant, not just the color/radius
// helpers above.
export const DIODE_OUTLINE_WIDTH = 3.5; // per this symbol's own spec, not OUTLINE_WIDTH

export const IndicatorDiodeSymbol: React.FC<IndicatorDiodeSymbolProps> = ({ state, size }) => {
  const radius = getIndicatorDiodeRadius(size);
  const coreColor = getIndicatorDiodeCoreColor(state);
  const core = getIndicatorDiodeCoreGeometry(radius);

  return (
    <Group>
      <Circle x={75} y={75} radius={radius} fill={getIndicatorDiodeFillColor(state)} stroke={COLOR_OUTLINE} strokeWidth={DIODE_OUTLINE_WIDTH} />
      {coreColor && (
        <Circle x={75 - core.offset} y={75 - core.offset} radius={core.radius} fill={coreColor} listening={false} />
      )}
    </Group>
  );
};
