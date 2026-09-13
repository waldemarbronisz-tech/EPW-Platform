// feat/text-formatting + feat/toolbar-grouping: text boxes formatted the
// way a word processor formats them, and the top toolbar trimmed to the
// basics with inserting moved into the library.
//
// The formatting rules are pure (project/TextFormatting.ts) and checked
// directly; the wiring is checked by source scan, the convention this
// suite already uses where there is no runnable harness.

import { describe, it, expect } from 'vitest';
import {
  clampFontSize, commonTextFormat, isTextFormattable, konvaFontStyle, primaryFontFamily,
  styleUpdates, textFormatOf, TEXT_BOX_TYPE, TEXT_STYLES, MAX_FONT_SIZE, MIN_FONT_SIZE,
} from '../project/TextFormatting';
import { getSymbolDefinition, getSymbolsByCategory } from '../symbols/SymbolRegistry';
import type { SynopticObject } from '../store';

import formatBarSource from '../components/FormatBar.tsx?raw';
import toolbarSource from '../components/Toolbar.tsx?raw';
import modeOptionsBarSource from '../components/ModeOptionsBar.tsx?raw';
import libraryDomainsSource from '../project/LibraryDomains.ts?raw';
import objectNodeSource from '../components/canvas/ObjectNode.tsx?raw';
import canvasSource from '../components/Canvas.tsx?raw';
import appSource from '../App.tsx?raw';

const box = (extra: Partial<SynopticObject> = {}): SynopticObject => ({
  id: 't1', type: TEXT_BOX_TYPE, category: 'SCADA', x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
  visible: true, locked: false, layer: 1, tag: '', description: '',
  color: '', fill: '', border: '', text: 'Hello', font: 'Tahoma, Verdana, sans-serif', fontSize: 13,
  tooltip: '', width: 240, height: 48, customProperties: {},
  ...extra,
});

describe('the text box element', () => {
  it('is a visible SCADA library symbol that redraws on resize instead of stretching', () => {
    const def = getSymbolDefinition(TEXT_BOX_TYPE)!;
    expect(def.label).toBe('Text box');
    expect(def.category).toBe('SCADA');
    expect(def.resizeRedraws).toBe(true);
    expect((getSymbolsByCategory().SCADA || []).some(d => d.type === TEXT_BOX_TYPE)).toBe(true);
  });

  it('is what the formatting bar acts on - and a pump is not', () => {
    expect(isTextFormattable(TEXT_BOX_TYPE)).toBe(true);
    expect(isTextFormattable('graphics.text')).toBe(true);
    expect(isTextFormattable('site.hydrofor')).toBe(false);
  });
});

describe('character formatting', () => {
  it('fills in word-processor defaults for text saved before formatting existed', () => {
    expect(textFormatOf(box())).toEqual({
      font: 'Tahoma', fontSize: 13, bold: false, italic: false, underline: false, align: 'left', style: 'normal',
    });
  });

  it('shows and edits the first family of a CSS font stack', () => {
    expect(primaryFontFamily('Tahoma, Verdana, "DejaVu Sans", sans-serif')).toBe('Tahoma');
    expect(primaryFontFamily('"Times New Roman", serif')).toBe('Times New Roman');
    expect(primaryFontFamily('')).toBe('Tahoma');
  });

  it('maps bold and italic onto the style string Konva expects', () => {
    expect(konvaFontStyle({ bold: false, italic: false })).toBe('normal');
    expect(konvaFontStyle({ bold: true, italic: false })).toBe('bold');
    expect(konvaFontStyle({ bold: false, italic: true })).toBe('italic');
    expect(konvaFontStyle({ bold: true, italic: true })).toBe('italic bold');
  });

  it('keeps a typed size inside a sane range', () => {
    expect(clampFontSize(2)).toBe(MIN_FONT_SIZE);
    expect(clampFontSize(10_000)).toBe(MAX_FONT_SIZE);
    expect(clampFontSize(Number.NaN)).toBe(13);
    expect(clampFontSize(11.6)).toBe(12);
  });
});

describe('paragraph styles', () => {
  it('lists Normal first, the way a word processor does', () => {
    expect(TEXT_STYLES[0].id).toBe('normal');
    expect(TEXT_STYLES.map(s => s.label)).toEqual(['Normal', 'Title', 'Heading 1', 'Heading 2', 'Caption']);
  });

  it('writes the style together with the character format it implies', () => {
    expect(styleUpdates('heading1')).toEqual({ textStyle: 'heading1', fontSize: 20, fontBold: true, fontItalic: false });
    expect(styleUpdates('caption')).toMatchObject({ fontItalic: true, fontBold: false });
  });
});

describe('a selection of several text boxes', () => {
  it('reports what they share and leaves mixed values blank', () => {
    const common = commonTextFormat([
      box({ id: 'a', fontBold: true, textAlign: 'center', fontSize: 16 }),
      box({ id: 'b', fontBold: true, textAlign: 'right', fontSize: 16 }),
    ]);
    expect(common.bold).toBe(true);
    expect(common.fontSize).toBe(16);
    expect(common.align).toBeNull();
  });

  it('reports nothing at all for an empty selection', () => {
    expect(commonTextFormat([]).font).toBeNull();
  });
});

describe('wiring (source scan)', () => {
  it('offers the Word-style groups in order: insert, style, font, size, B I U, alignment', () => {
    // The groups as they appear in the rendered bar...
    const jsx = formatBarSource.slice(formatBarSource.indexOf('export const FormatBar'));
    const order = ['Text box', 'Paragraph style', 'title="Font"', 'Font size', 'title="Bold"', 'title="Italic"', 'title="Underline"', 'ALIGNMENTS.map('];
    let at = -1;
    for (const marker of order) {
      const next = jsx.indexOf(marker);
      expect(next, marker).toBeGreaterThan(at);
      at = next;
    }
    // ...and the alignment buttons in the order a word processor shows them.
    const table = formatBarSource.slice(0, formatBarSource.indexOf('export const FormatBar'));
    const aligns = ['Align text left', 'Center text', 'Align text right', 'Justify text'].map(m => table.indexOf(m));
    expect(aligns.every((pos, i) => pos > (i === 0 ? -1 : aligns[i - 1]))).toBe(true);
  });

  it('keeps its own class so Studio, which hides the drawing toolbar, still shows it', () => {
    expect(formatBarSource).toContain('className="format-bar"');
    // feat/synoptic-modes: the row under the toolbar shows the options of
    // the work mode, and in ANNOTATIONS those are the format bar.
    expect(appSource).toContain('<ModeOptionsBar />');
    expect(modeOptionsBarSource).toContain("if (workMode === 'ANNOTATIONS') return <FormatBar />;");
  });

  it('opens a text box for typing on double-click and straight after it is dropped', () => {
    expect(objectNodeSource).toContain('setEditingTextId(obj.id)');
    expect(canvasSource).toContain('<TextEditOverlay />');
    expect(canvasSource).toContain('data.type === TEXT_BOX_TYPE');
  });

  it('leaves inserting panels to the Object Library and keeps the basics on the toolbar, each with a stable command', () => {
    for (const moved of ['Add Meter', 'Add Signal Panel', 'addMeter', 'addSignalPanel']) {
      expect(toolbarSource, moved).not.toContain(moved);
    }
    expect(libraryDomainsSource).toContain("'widget.meter', 'widget.signal_panel'");
    for (const basic of ['undo', 'redo', 'copy', 'paste', 'delete']) {
      expect(toolbarSource, basic).toContain(`cmd="${basic}"`);
    }
  });
});
