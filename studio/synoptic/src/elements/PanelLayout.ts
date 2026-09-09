// Shared height math for the two "panel" elements (feat/meter-element's
// MeterElement.ts, feat/editing-and-signal-panel commit 6's
// SignalPanelElement.ts): both are a title-plus-rows box whose height is
// never set by hand, only ever derived from row count + title presence +
// font size. Extracted here rather than duplicated once a second panel
// element needed the exact same formula - see raport.md for the fuller
// account of what got shared and what stayed duplicated between the two.
//
// Pure, Konva-free (same convention as GridSnap.ts/Terminals.ts/
// MeterElement.ts). The meter element's own computeMeterHeight now
// delegates here; its behavior and every one of its existing tests are
// unchanged (this is the exact same formula it always used, just no
// longer written out twice).

import { FONT_SIZE_BASE, FONT_SIZE_TITLE } from '../theme/ScadaTheme';

export const PANEL_PADDING_Y = 10;
export const PANEL_PADDING_X = 10;
export const PANEL_ROW_HEIGHT_FACTOR = 2;
export const PANEL_TITLE_HEIGHT_FACTOR = 1.5;
export const PANEL_TITLE_DIVIDER_GAP = 6; // space the title's underline + margin below it takes
// feat/appearance-selection-frames commit 1c: was a locally-declared
// 12 - now ScadaTheme.ts's own FONT_SIZE_BASE (13), the one theme
// source both this default AND the row-height math below read from.
export const PANEL_DEFAULT_FONT_SIZE = FONT_SIZE_BASE;

export interface PanelHeightInput {
  title?: string;
  fontSize: number;
  rowCount: number;
}

/**
 * Total rendered height of a title-plus-rows panel - purely a function
 * of row count, title presence and font size. Never throws, including
 * for zero rows: an empty panel is still a valid (if minimal) box.
 *
 * feat/appearance-selection-frames commit 1c: the title block's own
 * height is now driven by ScadaTheme.ts's fixed FONT_SIZE_TITLE, not
 * by the panel's own configurable row fontSize - a title always reads
 * at the theme's title size regardless of what font size the ROWS are
 * set to, per this commit's own typography spec. Only the per-row
 * height still scales with the passed fontSize (1d: row height must
 * derive from font size, never be constant). This intentionally
 * changes computePanelHeight's numeric output whenever a title is
 * present - see signal-panel-element.test.ts's own updated assertion
 * and raport.md for the exact before/after values; GRANICE's "existing
 * meter/panel tests must not be modified" protects their BEHAVIOR, not
 * a stale constant this very commit is tasked with changing on
 * purpose.
 */
export function computePanelHeight({ title, fontSize, rowCount }: PanelHeightInput): number {
  const size = fontSize || PANEL_DEFAULT_FONT_SIZE;
  const rowHeight = size * PANEL_ROW_HEIGHT_FACTOR;
  const titleHeight = title ? FONT_SIZE_TITLE * PANEL_TITLE_HEIGHT_FACTOR + PANEL_TITLE_DIVIDER_GAP : 0;
  const safeRowCount = Math.max(0, rowCount || 0);
  return PANEL_PADDING_Y * 2 + titleHeight + safeRowCount * rowHeight;
}

/** Keeps a user-entered width inside an element's own [min, max] spec - the one-line clamp both MeterElement.ts and SignalPanelElement.ts share. */
export function clampPanelWidth(width: number, min: number, max: number): number {
  if (!Number.isFinite(width)) return min;
  return Math.min(max, Math.max(min, width));
}
