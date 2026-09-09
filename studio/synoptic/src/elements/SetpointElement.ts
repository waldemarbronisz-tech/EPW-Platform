// feat/selector-symbol-setpoint-alarm: the setpoint panel - a screen
// element that lets an engineer lay out where a MODULATED device's own
// setpoint (a modulating valve/VFD's continuously variable output) is
// shown and, at runtime in EPW-OS, entered - the same role the meter
// element already plays for MEASURED devices (src/meter/MeterElement.ts,
// whose own structure this file mirrors closely; see that file and
// raport.md-equivalent commit comments for what stayed shared - the
// panel height/width-clamp math, elements/PanelLayout.ts - and what is
// duplicated here, and why: the manual-row value formatting is
// small enough, and specific enough to each element's own row shape,
// that sharing it would need more indirection than it saves).
//
// Deliberately NOT a symbol - no terminals, no fixed canvas, no entry
// in SymbolRegistry, its own store array (setpointPanels), not
// `objects`. No height field on the model at all - always derived,
// same as the meter/signal panel.
//
// This editor is design-time only (see GroupCommandResolver.ts's own
// header for the fuller statement of that boundary): placing and
// configuring this element decides WHERE a setpoint control appears
// and WHICH device it targets, never sends or simulates an actual
// runtime command - that is EPW-OS's job when it renders this same
// project live.

import { computePanelHeight, clampPanelWidth, PANEL_DEFAULT_FONT_SIZE } from './PanelLayout';

/**
 * One row of a setpoint panel. `device` is a MODULATED device id from
 * the project's device list, or '' for a manual row. Which of
 * manualValue/manualUnit vs. the device's own unit/range/startupValue
 * actually gets shown is SetpointResolver.ts's job, mirroring
 * MeterResolver.ts's own THE ONE RULE (a device-linked row never
 * stores its own copy of the unit - always read from the device).
 */
export interface SetpointRow {
  device: string;       // MODULATED device id, or '' for a manual row
  label: string;         // '' = fall back to the device's designation
  manualValue: string;   // used only when device is ''
  manualUnit: string;    // used only when device is ''
}

export interface SetpointPanelElement {
  id: string;
  x: number;
  y: number;
  width: number;   // user-set, clamped to [SETPOINT_MIN_WIDTH, SETPOINT_MAX_WIDTH]
  title?: string;   // optional, bold + centered + underlined with a divider when present
  fontSize: number; // defaults to SETPOINT_DEFAULT_FONT_SIZE
  rows: SetpointRow[];
}

export const SETPOINT_MIN_WIDTH = 120;
export const SETPOINT_MAX_WIDTH = 480; // same span as the meter - a value field needs the same room regardless of which behavior fills it
export const SETPOINT_DEFAULT_FONT_SIZE = PANEL_DEFAULT_FONT_SIZE;

/** Keeps a user-entered width inside the element's own [min, max] spec. */
export function clampSetpointWidth(width: number): number {
  return clampPanelWidth(width, SETPOINT_MIN_WIDTH, SETPOINT_MAX_WIDTH);
}

/**
 * The panel's total rendered height - purely a function of row count,
 * title presence and font size, via the same shared formula the meter/
 * signal panel elements use (elements/PanelLayout.ts). Never throws,
 * including for zero rows.
 */
export function computeSetpointHeight(panel: Pick<SetpointPanelElement, 'title' | 'fontSize' | 'rows'>): number {
  return computePanelHeight({ title: panel.title, fontSize: panel.fontSize, rowCount: panel.rows?.length || 0 });
}

/**
 * A manual row's own "value unit" text, straight from its own fields -
 * no device involved, same shape and reasoning as MeterElement.ts's
 * own formatManualRowValue. Empty when both fields are empty, not " "
 * or "undefined".
 */
export function formatManualSetpointValue(row: SetpointRow): string {
  const parts = [row.manualValue, row.manualUnit].filter(p => !!p);
  return parts.join(' ');
}
