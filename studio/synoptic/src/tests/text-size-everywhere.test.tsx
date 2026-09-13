/** @vitest-environment jsdom */
// Reported: "text size is stuck on 13". In the running editor the size box
// of a text box worked - but the label on a symbol stayed 13 whatever
// Properties said, because the label renderer had its size written in
// (PRIMARY_FONT_SIZE = FONT_SIZE_BASE, i.e. 13) and never read the
// object's own fontSize. The label frame had the same constants, the
// format bar did not appear for a selected symbol at all, and text colour
// had no control anywhere.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, cleanup, fireEvent, act } from '@testing-library/react';
import { useStore } from '../store';
import type { SynopticObject } from '../store';
import { ProjectManager } from '../project/ProjectManager';
import { labelTextFormat } from '../components/ObjectLabelRenderer';
import { getLabelFrameSize } from '../symbols/scada/LabelFrameSymbol';
import { ModeOptionsBar } from '../components/ModeOptionsBar';
import { TEXT_BOX_TYPE } from '../project/TextFormatting';
import { setLanguage } from '../i18n/tr';
import labelRendererSource from '../components/ObjectLabelRenderer.tsx?raw';
import labelFrameSource from '../symbols/scada/LabelFrameSymbol.tsx?raw';
import textBoxSource from '../symbols/scada/TextBoxSymbol.tsx?raw';

const obj = (id: string, type: string, extra: Partial<SynopticObject> = {}): SynopticObject => ({
  id, type, category: 'X', x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
  visible: true, locked: false, layer: 1, tag: '', description: '', designation: '-Q1',
  color: '#000000', fill: '', border: '', text: '', font: 'Tahoma', fontSize: 13,
  tooltip: '', width: 64, height: 64, customProperties: {}, ...extra,
} as SynopticObject);

const sizeBox = () => document.querySelector('input[title="Font size"]') as HTMLInputElement;

beforeEach(() => {
  setLanguage('en');
  ProjectManager.newProject('Text');
});
afterEach(cleanup);

describe('the label on a symbol takes its format from the object', () => {
  it('its size follows fontSize (the second line in proportion); 13 is only the default', () => {
    expect(labelTextFormat(obj('a', 'electrical.circuit_breaker')).primarySize).toBe(13);
    const big = labelTextFormat(obj('a', 'electrical.circuit_breaker', { fontSize: 24 }));
    expect(big.primarySize).toBe(24);
    expect(big.secondarySize).toBeGreaterThan(labelTextFormat(obj('a', 'electrical.circuit_breaker')).secondarySize);
    expect(labelRendererSource).not.toMatch(/const PRIMARY_FONT_SIZE = FONT_SIZE_BASE/);
  });

  it('bold stays the default for a label, and font, italic, underline and colour come from the object', () => {
    expect(labelTextFormat(obj('a', 'water.pump')).bold).toBe(true);
    const styled = labelTextFormat(obj('a', 'water.pump', { fontBold: false, fontItalic: true, fontUnderline: true, font: 'Courier New', textColor: '#c00000' }));
    expect(styled).toMatchObject({ bold: false, italic: true, underline: true, family: 'Courier New', fill: '#c00000' });
  });

  it('the label frame grows with its font size instead of using fixed constants', () => {
    const small = getLabelFrameSize('POWER', '230V', 13);
    const large = getLabelFrameSize('POWER', '230V', 26);
    expect(large.height).toBeGreaterThan(small.height);
    expect(large.width).toBeGreaterThan(small.width);
    expect(labelFrameSource).not.toMatch(/const DESC_FONT_SIZE = FONT_SIZE_BASE/);
  });
});

describe('the format bar edits the text of a selected symbol', () => {
  it('appears in SYMBOLS mode with a symbol selected, shows its size, and a typed size reaches the label - one undo step', () => {
    act(() => {
      useStore.getState().addObject(obj('ignored', 'electrical.circuit_breaker'));
      useStore.setState({ workMode: 'SYMBOLS' });
    });
    const id = useStore.getState().objects[0].id;
    act(() => { useStore.getState().selectObjects([id]); });
    render(<ModeOptionsBar />);
    expect(sizeBox()).not.toBeNull();
    expect(sizeBox().value).toBe('13');
    const history = useStore.getState().historyIndex;
    fireEvent.input(sizeBox(), { target: { value: '22' }, inputType: 'insertText' });
    fireEvent.keyDown(sizeBox(), { key: 'Enter' });
    const placed = useStore.getState().objects[0];
    expect(placed.fontSize).toBe(22);
    expect(labelTextFormat(placed).primarySize).toBe(22);
    expect(useStore.getState().historyIndex).toBe(history + 1);
    act(() => { useStore.getState().undo(); });
    expect(useStore.getState().objects[0].fontSize).toBe(13);
  });
});

describe('text colour', () => {
  it('has a control in the format bar, and the text box draws in the chosen colour', () => {
    act(() => {
      useStore.getState().addObject(obj('ignored', TEXT_BOX_TYPE, { text: 'Hello', width: 240, height: 48 }));
      useStore.setState({ workMode: 'ANNOTATIONS' });
    });
    const id = useStore.getState().objects[0].id;
    act(() => { useStore.getState().selectObjects([id]); });
    render(<ModeOptionsBar />);
    const colour = document.querySelector('.format-bar input[type="color"]') as HTMLInputElement;
    expect(colour).not.toBeNull();
    fireEvent.input(colour, { target: { value: '#1040c0' } });
    fireEvent.change(colour, { target: { value: '#1040c0' } });
    expect(useStore.getState().objects[0].textColor).toBe('#1040c0');
    expect(textBoxSource).toContain('obj.textColor');
  });
});

describe('save and reopen', () => {
  it('keeps size, font, bold, alignment and colour of a text box and of a symbol label', () => {
    act(() => {
      useStore.getState().addObject(obj('t', TEXT_BOX_TYPE, { text: 'Hello', fontSize: 28, font: 'Courier New', fontBold: true, textAlign: 'center', textColor: '#1040c0' }));
      useStore.getState().addObject(obj('s', 'electrical.circuit_breaker', { fontSize: 20, textColor: '#c00000' }));
    });
    const saved = ProjectManager.getProjectData()!;
    ProjectManager.newProject('Other');
    ProjectManager.loadProject(saved, 'text.epwsyn');
    const [textBox, breaker] = useStore.getState().objects;
    expect(textBox).toMatchObject({ fontSize: 28, font: 'Courier New', fontBold: true, textAlign: 'center', textColor: '#1040c0' });
    expect(labelTextFormat(breaker).primarySize).toBe(20);
    expect(labelTextFormat(breaker).fill).toBe('#c00000');
  });
});
