// feat/text-formatting: editing a text box behaves like a word processor.
//
// The height rule is pure enough to check directly (TextMeasure.ts falls
// back to a character estimate without a DOM); the editor's behaviour is
// pinned by source scan, as elsewhere in this suite.

import { describe, it, expect } from 'vitest';
import { fitTextBoxHeight, wrappedLineCount } from '../utils/TextMeasure';
import { TEXT_BOX_TYPE } from '../project/TextFormatting';
import type { SynopticObject } from '../store';

import overlaySource from '../components/TextEditOverlay.tsx?raw';
import formatBarSource from '../components/FormatBar.tsx?raw';

const box = (text: string, extra: Partial<SynopticObject> = {}): SynopticObject => ({
  id: 't', type: TEXT_BOX_TYPE, category: 'SCADA', x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
  visible: true, locked: false, layer: 1, tag: '', description: '',
  color: '', fill: '', border: '', text, font: 'Tahoma', fontSize: 13,
  tooltip: '', width: 240, height: 48, customProperties: {},
  ...extra,
});

describe('text box height', () => {
  it('counts explicit new lines', () => {
    expect(wrappedLineCount('a\nb\nc', 500, '13px Tahoma', 13)).toBe(3);
  });

  it('wraps a long paragraph onto more lines', () => {
    expect(wrappedLineCount('word '.repeat(80), 200, '13px Tahoma', 13)).toBeGreaterThan(3);
  });

  it('grows the box for more text and for a bigger font, snapped to the grid', () => {
    const short = fitTextBoxHeight(box('Hello'));
    const long = fitTextBoxHeight(box('Hello\nsecond\nthird\nfourth'));
    const big = fitTextBoxHeight(box('Hello\nsecond', { fontSize: 36 }));
    expect(long).toBeGreaterThan(short);
    expect(big).toBeGreaterThan(fitTextBoxHeight(box('Hello\nsecond')));
    expect(long % 16).toBe(0);
  });
});

describe('the in-place editor (source scan)', () => {
  it('ends editing on a click anywhere else - not on blur, which a canvas click never causes', () => {
    expect(overlaySource).toContain("window.addEventListener('pointerdown', onPointerDown, true)");
    expect(overlaySource).not.toContain('onBlur=');
  });

  it('grows the box while typing and keeps the whole edit as one history step', () => {
    expect(overlaySource).toContain('onInput=');
    expect(overlaySource).toContain('fitTextBoxHeight');
    expect(overlaySource).toContain('saveHistory()');
  });

  it('starts editing a selected text box with Enter or F2, and Escape restores it', () => {
    expect(overlaySource).toContain("e.key !== 'F2'");
    expect(overlaySource).toContain('originalHeightRef');
  });

  it('grows boxes when the format bar makes the text bigger', () => {
    expect(formatBarSource).toContain('fitTextBoxHeight');
  });
});
