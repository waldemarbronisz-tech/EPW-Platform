// feat/text-formatting: how tall a text box has to be for its text.
//
// A text box grows downward as you type, the way a word processor's text
// box does, instead of clipping the last lines. Measured with a 2D canvas
// context in the box's own font, wrapping words at the box's inner width -
// the same wrap Konva applies when it draws the text. Without a DOM (unit
// tests) a character-count estimate is used instead.

import type { SynopticObject } from '../store/types';
import { textFormatOf, TEXT_BOX_PADDING, TEXT_LINE_HEIGHT } from '../project/TextFormatting';

/** Heights snap to the canvas grid, like every other element. */
const GRID = 16;

let context: CanvasRenderingContext2D | null | undefined;

function measureContext(): CanvasRenderingContext2D | null {
  if (context !== undefined) return context;
  try {
    context = typeof document !== 'undefined' ? document.createElement('canvas').getContext('2d') : null;
  } catch {
    context = null;
  }
  return context;
}

/** Number of lines `text` takes when word-wrapped to `width` pixels. */
export function wrappedLineCount(text: string, width: number, font: string, fontSize: number): number {
  const ctx = measureContext();
  const measure = ctx
    ? (s: string) => { ctx.font = font; return ctx.measureText(s).width; }
    : (s: string) => s.length * fontSize * 0.55;

  let lines = 0;
  for (const paragraph of text.split('\n')) {
    const words = paragraph.split(/(\s+)/).filter(w => w.length > 0);
    if (words.length === 0) { lines += 1; continue; }
    let current = '';
    let count = 1;
    for (const word of words) {
      const candidate = current + word;
      if (current.trim() !== '' && measure(candidate.trimEnd()) > width) {
        count += 1;
        current = word.trimStart();
        // A single word wider than the box breaks across lines too.
        while (current && measure(current) > width && current.length > 1) {
          let cut = current.length - 1;
          while (cut > 1 && measure(current.slice(0, cut)) > width) cut -= 1;
          current = current.slice(cut);
          count += 1;
        }
      } else {
        current = candidate;
      }
    }
    lines += count;
  }
  return Math.max(1, lines);
}

/** The height (grid-snapped) a text box needs to show all of its text. */
export function fitTextBoxHeight(obj: SynopticObject): number {
  const format = textFormatOf(obj);
  const inner = Math.max(1, obj.width - TEXT_BOX_PADDING * 2);
  const css = `${format.italic ? 'italic ' : ''}${format.bold ? 'bold ' : ''}${format.fontSize}px "${format.font}"`;
  const lines = wrappedLineCount(obj.text || ' ', inner, css, format.fontSize);
  const height = lines * format.fontSize * TEXT_LINE_HEIGHT + TEXT_BOX_PADDING * 2;
  return Math.max(GRID * 2, Math.ceil(height / GRID) * GRID);
}
