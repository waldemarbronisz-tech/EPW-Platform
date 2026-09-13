/** @vitest-environment jsdom */
// The format bar's font size box works like Word's: what you type is
// applied on Enter or when you leave the box (applying each keystroke
// turned "12" into 6 and then 62), a size picked from the list applies at
// once, and A+ / A- step through the list.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup, act } from '@testing-library/react';
import { insertTextBox } from '../components/insertTextBox';
import { useStore } from '../store';
import type { SynopticObject } from '../store';
import { FormatBar } from '../components/FormatBar';
import { stepFontSize, TEXT_BOX_TYPE } from '../project/TextFormatting';

const box: SynopticObject = {
  id: 't', type: TEXT_BOX_TYPE, category: 'SCADA', x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
  visible: true, locked: false, layer: 1, tag: '', description: '',
  color: '', fill: '', border: '', text: 'Hello', font: 'Tahoma', fontSize: 13,
  tooltip: '', width: 240, height: 48, customProperties: {},
};

const fontSize = () => useStore.getState().objects.find(o => o.id === 't')?.fontSize;
const sizeBox = () => screen.getByTitle('Font size') as HTMLInputElement;
const type = (value: string) => fireEvent.input(sizeBox(), { target: { value }, inputType: 'insertText' });

beforeEach(() => {
  useStore.setState({ objects: [{ ...box }], selectedIds: ['t'], previewMode: false });
  render(<FormatBar />);
});
afterEach(cleanup);

describe('font size box', () => {
  it('does not apply half-typed numbers', () => {
    type('1');
    expect(fontSize()).toBe(13);
    expect(sizeBox().value).toBe('1');
    type('12');
    expect(fontSize()).toBe(13);
  });

  it('applies a typed size on Enter', () => {
    type('24');
    fireEvent.keyDown(sizeBox(), { key: 'Enter' });
    expect(fontSize()).toBe(24);
    expect(sizeBox().value).toBe('24');
  });

  it('applies a typed size when leaving the box', () => {
    type('36');
    fireEvent.blur(sizeBox());
    expect(fontSize()).toBe(36);
  });

  it('Escape throws the typed size away', () => {
    type('40');
    fireEvent.keyDown(sizeBox(), { key: 'Escape' });
    fireEvent.blur(sizeBox());
    expect(fontSize()).toBe(13);
    expect(sizeBox().value).toBe('13');
  });

  it('a size picked from the list applies at once', () => {
    fireEvent.click(screen.getByTitle('Show all font sizes'));
    fireEvent.mouseDown(screen.getByRole('option', { name: '18' }));
    expect(fontSize()).toBe(18);
    expect(screen.queryByRole('listbox')).toBeNull();
  });

  it('A+ and A- step through the size list', () => {
    fireEvent.click(screen.getByTitle('Increase font size'));
    expect(fontSize()).toBe(14);
    fireEvent.click(screen.getByTitle('Decrease font size'));
    fireEvent.click(screen.getByTitle('Decrease font size'));
    expect(fontSize()).toBe(12);
  });

  it('ignores text that is not a number', () => {
    type('big');
    fireEvent.keyDown(sizeBox(), { key: 'Enter' });
    expect(fontSize()).toBe(13);
  });
});

describe('stepFontSize', () => {
  it('moves to the neighbouring list size', () => {
    expect(stepFontSize(36, 1)).toBe(48);
    expect(stepFontSize(13, -1)).toBe(12);
    expect(stepFontSize(15, 1)).toBe(16);
    expect(stepFontSize(8, -1)).toBe(7);
  });
});

describe('format bar with nothing selected', () => {
  it('stays usable and sets the format of the next text box, as in a word processor', () => {
    act(() => { useStore.setState({ selectedIds: [], nextTextFormat: {} }); });
    const bold = screen.getByTitle('Bold') as HTMLButtonElement;
    expect(bold.disabled).toBe(false);
    fireEvent.click(bold);
    type('20');
    fireEvent.keyDown(sizeBox(), { key: 'Enter' });
    expect(useStore.getState().nextTextFormat).toMatchObject({ fontBold: true, fontSize: 20 });
    expect(fontSize()).toBe(13); // the unselected box is untouched

    act(() => { insertTextBox(); });
    const created = useStore.getState().objects[useStore.getState().objects.length - 1];
    expect(created.fontBold).toBe(true);
    expect(created.fontSize).toBe(20);
  });
});
