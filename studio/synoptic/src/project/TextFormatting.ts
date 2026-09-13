// feat/text-formatting: character and paragraph formatting for text on
// a screen, the way a word processor does it.
//
// A text box is typed into directly on the canvas and formatted from a
// Word-style bar: a paragraph style, a font, a size, bold / italic /
// underline, and left / centre / right / justified alignment. This
// module is the pure half of that - what each control reads and what it
// writes - so the bar, the canvas renderer and the in-place editor all
// agree on one interpretation of the same few fields.
//
// Every field is optional on the object. A text box saved before this
// existed simply renders with the defaults below.

import type { SynopticObject } from '../store/types';
import { FONT_SIZE_BASE, FONT_SIZE_SMALL } from '../theme/ScadaTheme';

export type TextAlign = 'left' | 'center' | 'right' | 'justify';
export type TextStyleId = 'normal' | 'title' | 'heading1' | 'heading2' | 'caption';

/** The type string of the text box element. */
export const TEXT_BOX_TYPE = 'scada.text_box';

/** Inner margin of a text box, in canvas units - shared by the renderer and the in-place editor so the text does not jump when editing starts. */
export const TEXT_BOX_PADDING = 4;

/** Line spacing, shared for the same reason. */
export const TEXT_LINE_HEIGHT = 1.2;

export interface TextStyleDefinition {
  id: TextStyleId;
  label: string;
  size: number;
  bold: boolean;
  italic: boolean;
}

/** Paragraph styles, in the order a word processor lists them. */
export const TEXT_STYLES: TextStyleDefinition[] = [
  { id: 'normal', label: 'Normal', size: FONT_SIZE_BASE, bold: false, italic: false },
  { id: 'title', label: 'Title', size: 28, bold: true, italic: false },
  { id: 'heading1', label: 'Heading 1', size: 20, bold: true, italic: false },
  { id: 'heading2', label: 'Heading 2', size: 16, bold: true, italic: false },
  { id: 'caption', label: 'Caption', size: FONT_SIZE_SMALL, bold: false, italic: true },
];

/** Fonts offered in the font box - ones present on every Windows install the editor runs on. */
export const FONT_FAMILIES = [
  'Tahoma', 'Arial', 'Verdana', 'Segoe UI', 'Calibri',
  'Times New Roman', 'Georgia', 'Courier New', 'Consolas',
];

/** Sizes offered in the size box. Any other value can still be typed. */
export const FONT_SIZES = [8, 9, 10, 11, 12, 13, 14, 16, 18, 20, 22, 24, 28, 32, 36, 48, 72];

export const MIN_FONT_SIZE = 6;
export const MAX_FONT_SIZE = 400;

export const DEFAULT_FONT_FAMILY = 'Tahoma';

/** Whether the formatting bar and the in-place editor apply to this element type. */
export function isTextFormattable(type: string): boolean {
  return type === TEXT_BOX_TYPE || type === 'graphics.text';
}

export interface TextFormat {
  font: string;
  fontSize: number;
  bold: boolean;
  italic: boolean;
  underline: boolean;
  align: TextAlign;
  style: TextStyleId;
  color: string;
}

/** The first family of a CSS font stack, unquoted - "Tahoma, Verdana, sans-serif" is shown and edited as "Tahoma". */
export function primaryFontFamily(font: string | undefined): string {
  const first = (font || '').split(',')[0].trim().replace(/^["']|["']$/g, '');
  return first || DEFAULT_FONT_FAMILY;
}

export function clampFontSize(size: number): number {
  if (!Number.isFinite(size)) return FONT_SIZE_BASE;
  return Math.min(MAX_FONT_SIZE, Math.max(MIN_FONT_SIZE, Math.round(size)));
}

/** The next size in the list up (+1) or down (-1) from `size`, as Word's
 *  grow/shrink font buttons do; a mixed selection (null) starts from the base size. */
export function stepFontSize(size: number | null, direction: 1 | -1): number {
  const current = size ?? FONT_SIZE_BASE;
  if (direction > 0) {
    return FONT_SIZES.find(s => s > current) ?? clampFontSize(current + 10);
  }
  const smaller = FONT_SIZES.filter(s => s < current);
  return smaller.length ? smaller[smaller.length - 1] : clampFontSize(current - 1);
}

/** The effective format of one element, defaults filled in. */
export function textFormatOf(obj: SynopticObject): TextFormat {
  return {
    font: primaryFontFamily(obj.font),
    fontSize: clampFontSize(obj.fontSize || FONT_SIZE_BASE),
    // A symbol's label is bold unless set otherwise; a text box is not.
    bold: obj.fontBold ?? !isTextFormattable(obj.type),
    italic: !!obj.fontItalic,
    underline: !!obj.fontUnderline,
    align: obj.textAlign || 'left',
    style: obj.textStyle || 'normal',
    color: textColorOf(obj),
  };
}

/** The colour an element's text is drawn in: its own text colour, else its colour, else black. Always #rrggbb, so a colour input can show it. */
export function textColorOf(obj: Pick<SynopticObject, 'textColor' | 'color'>): string {
  const candidate = obj.textColor || obj.color || '';
  return /^#[0-9a-f]{6}$/i.test(candidate) ? candidate : '#000000';
}

/** Konva's fontStyle string for a format: 'normal', 'bold', 'italic' or 'italic bold'. */
export function konvaFontStyle(format: Pick<TextFormat, 'bold' | 'italic'>): string {
  if (format.bold && format.italic) return 'italic bold';
  if (format.bold) return 'bold';
  if (format.italic) return 'italic';
  return 'normal';
}

/** What choosing a paragraph style writes: the style and the character format it implies, exactly as a word processor applies one. */
export function styleUpdates(styleId: TextStyleId): Partial<SynopticObject> {
  const style = TEXT_STYLES.find(s => s.id === styleId) ?? TEXT_STYLES[0];
  return {
    textStyle: style.id,
    fontSize: style.size,
    fontBold: style.bold,
    fontItalic: style.italic,
  };
}

/** A value shared by every element in a selection, or null when they differ - the bar shows a blank box for "mixed". */
export interface CommonTextFormat {
  font: string | null;
  fontSize: number | null;
  bold: boolean | null;
  italic: boolean | null;
  underline: boolean | null;
  align: TextAlign | null;
  style: TextStyleId | null;
  color: string | null;
}

export function commonTextFormat(objects: SynopticObject[]): CommonTextFormat {
  const formats = objects.map(textFormatOf);
  const pick = <K extends keyof TextFormat>(key: K): TextFormat[K] | null => {
    if (formats.length === 0) return null;
    const first = formats[0][key];
    return formats.every(f => f[key] === first) ? first : null;
  };
  return {
    font: pick('font'),
    fontSize: pick('fontSize'),
    bold: pick('bold'),
    italic: pick('italic'),
    underline: pick('underline'),
    align: pick('align'),
    style: pick('style'),
    color: pick('color'),
  };
}
