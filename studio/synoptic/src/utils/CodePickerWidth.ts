// fix/device-form-polish commit 1: the pixel width a <select> listing
// short registry codes (location codes, in practice - see
// DeviceFormDialog.tsx) needs to show its CURRENTLY SELECTED option in
// full, computed from the registry's own content rather than a literal
// baked into the component. Pure and DOM-free on purpose, same
// convention as utils/ResizeHandles.ts/InsertMode.ts - directly
// testable without a rendering harness.
//
// The per-character factor below is deliberately more generous than
// the estimateTextWidth helper already duplicated in
// ObjectLabelRenderer.tsx/FrameElementNode.tsx/LabelFrameSymbol.tsx
// (0.62 * fontSize) - that one measures bare glyphs on a Konva canvas,
// with no box around them at all. A <select> is a real form control:
// its own padding, border and native dropdown arrow (SELECT_ARROW_
// ALLOWANCE already covers the arrow itself) all sit around the text,
// so a comfortable per-character allowance for THIS context needs more
// room than a tight glyph measurement would give it - kept as its own
// local literal, same reasoning those three keep their own factor
// local rather than promoting it to ScadaTheme.ts: this is a shape
// RATIO used to arrive at a width, not a picker width itself, and
// GRANICE's own rule for this fix is specifically about widths.
import { LOCATION_PICKER_MIN_WIDTH, LOCATION_PICKER_MAX_WIDTH, SELECT_ARROW_ALLOWANCE, FONT_SIZE_BASE } from '../theme/ScadaTheme';

const CHAR_WIDTH_FACTOR = 1.5;

/**
 * The width (px) a <select> needs to show the longest code among
 * `codes` in full, plus room for the dropdown arrow - clamped to
 * ScadaTheme's own LOCATION_PICKER_MIN_WIDTH/MAX_WIDTH. An empty
 * registry (no codes at all) still returns the minimum, never 0 or a
 * negative width.
 */
export function computeCodePickerWidth(codes: string[], fontSize: number = FONT_SIZE_BASE): number {
  const longest = codes.reduce((max, code) => Math.max(max, code.length), 0);
  const estimated = longest * fontSize * CHAR_WIDTH_FACTOR + SELECT_ARROW_ALLOWANCE;
  return Math.min(LOCATION_PICKER_MAX_WIDTH, Math.max(LOCATION_PICKER_MIN_WIDTH, estimated));
}
