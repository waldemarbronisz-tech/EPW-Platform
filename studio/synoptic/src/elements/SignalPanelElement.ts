// The signal panel element (feat/editing-and-signal-panel commit 6): the
// SAME mechanism as the meter element (src/meter/MeterElement.ts) with
// one difference - a row ends in a two-state DIODE instead of a value
// field. Modeled by mirroring that element's own pattern, not by
// inventing a new one - see raport.md for exactly what got shared
// (elements/PanelLayout.ts's height math, components/PanelChrome.tsx's
// panel/title/divider chrome) and what stayed duplicated, and why.
//
// Deliberately NOT a symbol - no terminals, no fixed canvas, no entry
// in SymbolRegistry, its own store array (signalPanels), not `objects`.
// No height field on the model at all - always derived, same as the
// meter.
//
// Pure, Konva-free (same convention as MeterElement.ts/GridSnap.ts/
// Terminals.ts).

import type { IndicatorDiodeState } from '../symbols/scada/IndicatorDiodeSymbol';
import { computePanelHeight, clampPanelWidth, PANEL_DEFAULT_FONT_SIZE } from './PanelLayout';

/**
 * One row of a signal panel. `device` is a device id from the project's
 * device list - empty means a manual row. manualState reuses
 * IndicatorDiodeState (ON/OFF/QUALITY) directly from the existing
 * Indicator Diode symbol, rather than declaring a second, identical
 * three-value type - the panel's diode IS that symbol's own state
 * concept, not a lookalike of it.
 */
export interface SignalPanelRow {
  device: string;              // device id, or '' for a manual row
  label: string;                // '' = fall back to the device's designation (commit 7)
  manualState: IndicatorDiodeState; // used only when device is ''
}

export interface SignalPanelElement {
  id: string;
  x: number;
  y: number;
  width: number;   // user-set, clamped to [SIGNAL_PANEL_MIN_WIDTH, SIGNAL_PANEL_MAX_WIDTH]
  title?: string;   // optional, bold + centered + underlined with a divider when present
  fontSize: number; // defaults to SIGNAL_PANEL_DEFAULT_FONT_SIZE
  rows: SignalPanelRow[];
}

export const SIGNAL_PANEL_MIN_WIDTH = 120;
export const SIGNAL_PANEL_MAX_WIDTH = 400; // narrower than the meter's 480 - a label plus a 12px-radius dot needs less room than a label plus a value field
export const SIGNAL_PANEL_DEFAULT_FONT_SIZE = PANEL_DEFAULT_FONT_SIZE;

/** Keeps a user-entered width inside the element's own [min, max] spec. */
export function clampSignalPanelWidth(width: number): number {
  return clampPanelWidth(width, SIGNAL_PANEL_MIN_WIDTH, SIGNAL_PANEL_MAX_WIDTH);
}

/**
 * The panel's total rendered height - purely a function of row count,
 * title presence and font size, via the same shared formula the meter
 * element uses (elements/PanelLayout.ts). Never throws, including for
 * zero rows.
 */
export function computeSignalPanelHeight(panel: Pick<SignalPanelElement, 'title' | 'fontSize' | 'rows'>): number {
  return computePanelHeight({ title: panel.title, fontSize: panel.fontSize, rowCount: panel.rows?.length || 0 });
}
