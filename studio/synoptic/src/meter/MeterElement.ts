// The meter element (feat/meter-element, part A): a screen element that
// shows measurement values, one per row. Deliberately NOT a symbol - it
// has no terminals, no fixed canvas, no entry in SymbolRegistry, and
// lives in its own store array (see store.ts's `meters`), not `objects`.
// Its height is never set by hand: it is always derived from how many
// rows it has, whether it has a title, and its own font size (see
// computeMeterHeight below) - there is deliberately no height field on
// the model at all.
//
// Pure, Konva-free (safe to import from a Vitest test run under Node),
// the same convention GridSnap.ts/Terminals.ts/WireDrawing.ts already
// established for logic shared between the canvas and tests.

import { computePanelHeight, clampPanelWidth, PANEL_DEFAULT_FONT_SIZE } from '../elements/PanelLayout';

/**
 * One row of a meter. `device` is a device id from the project's device
 * list (src/project/DeviceSchema.ts) - empty means a manual row. Which
 * of manualValue/manualUnit vs. the device's own unit/format/designation
 * actually gets shown is Part B's job (src/meter/MeterResolver.ts); this
 * file only holds the row's own raw fields and the height math, which
 * needs nothing from a device.
 */
export interface MeterElementRow {
  device: string;       // device id, or '' for a manual row
  label: string;        // '' = fall back to the device's designation (part B)
  manualValue: string;  // used only when device is ''
  manualUnit: string;   // used only when device is ''
}

export interface MeterElement {
  id: string;
  x: number;
  y: number;
  width: number;        // user-set, clamped to [METER_MIN_WIDTH, METER_MAX_WIDTH]
  title?: string;        // optional, bold + centered + underlined with a divider when present
  fontSize: number;      // defaults to METER_DEFAULT_FONT_SIZE
  rows: MeterElementRow[];
}

export const METER_MIN_WIDTH = 120;
export const METER_MAX_WIDTH = 480;
export const METER_DEFAULT_FONT_SIZE = PANEL_DEFAULT_FONT_SIZE;

/** Keeps a user-entered width inside the element's own [min, max] spec. */
export function clampMeterWidth(width: number): number {
  return clampPanelWidth(width, METER_MIN_WIDTH, METER_MAX_WIDTH);
}

// ---- Height ---------------------------------------------------------

/**
 * The meter's total rendered height - purely a function of row count,
 * title presence and font size. Never throws, including for zero rows:
 * an empty meter is still a valid (if minimal) panel, per the task's
 * own explicit "renders without exception" requirement.
 *
 * feat/editing-and-signal-panel commit 6: delegates to elements/
 * PanelLayout.ts's computePanelHeight, shared with SignalPanelElement.ts
 * (the exact same formula this function always used - meter-element.
 * test.ts's own height tests pass unmodified, proving this is not a
 * behavior change, only where the formula lives).
 */
export function computeMeterHeight(meter: Pick<MeterElement, 'title' | 'fontSize' | 'rows'>): number {
  return computePanelHeight({ title: meter.title, fontSize: meter.fontSize, rowCount: meter.rows?.length || 0 });
}

// ---- Manual row display (part A) -------------------------------------

/**
 * A manual row's own "value unit" text, straight from its own fields -
 * no device involved. A device-linked row (row.device truthy) is not
 * this function's concern at all: resolving what a device-linked row
 * shows is Part B's job (MeterResolver.ts), which supersedes this for
 * that case. Empty when both fields are empty, not " " or "undefined".
 */
export function formatManualRowValue(row: MeterElementRow): string {
  const parts = [row.manualValue, row.manualUnit].filter(p => !!p);
  return parts.join(' ');
}
