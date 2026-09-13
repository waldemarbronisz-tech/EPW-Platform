/** @vitest-environment jsdom */
// Reported three times as "text size stuck on 13". The cause: the size box
// was <input list> with a <datalist> - typing suggestions the browser
// filters by what is in the box. With "13" there, the drop-down showed
// only 13. The box must offer every size, whatever it holds, and still
// take a size that is not on the list.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup, act } from '@testing-library/react';
import { useStore } from '../store';
import type { SynopticObject } from '../store';
import { FormatBar } from '../components/FormatBar';
import { FONT_FAMILIES, FONT_SIZES, TEXT_BOX_TYPE } from '../project/TextFormatting';
import { setLanguage } from '../i18n/tr';
import formatBarSource from '../components/FormatBar.tsx?raw';

const box: SynopticObject = {
  id: 't', type: TEXT_BOX_TYPE, category: 'SCADA', x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
  visible: true, locked: false, layer: 1, tag: '', description: '',
  color: '', fill: '', border: '', text: 'Hello', font: 'Tahoma', fontSize: 13,
  tooltip: '', width: 240, height: 48, customProperties: {},
};

const sizeBox = () => screen.getByTitle('Font size') as HTMLInputElement;
const openList = () => fireEvent.click(screen.getByTitle('Show all font sizes'));
// Only the size list's entries - the style and font selects have options of their own.
const listed = () => Array.from(document.querySelectorAll('[data-list="font-sizes"] [role="option"]')).map(o => o.textContent);
const fontSize = () => useStore.getState().objects.find(o => o.id === 't')!.fontSize;

beforeEach(() => {
  setLanguage('en');
  useStore.setState({
    objects: [{ ...box }], selectedIds: ['t'], previewMode: false, workMode: 'ANNOTATIONS',
    history: [{ objects: [{ ...box }], connections: [], meters: [], signalPanels: [], frames: [], walls: [], circuits: [], groupCommands: [], setpointPanels: [] }],
    historyIndex: 0,
  });
  render(<FormatBar />);
});
afterEach(cleanup);

describe('the font size list', () => {
  it('lists every size in FONT_SIZES with 13 in the box - not just the one that matches', () => {
    expect(sizeBox().value).toBe('13');
    expect(screen.queryByRole('listbox')).toBeNull();
    openList();
    expect(listed()).toEqual(FONT_SIZES.map(String));
    expect(listed()).toHaveLength(17);
    expect(screen.getByRole('option', { name: '13' }).getAttribute('aria-selected')).toBe('true');
  });

  it('still lists every size when the box holds 72, or a half-typed "1"', () => {
    act(() => { useStore.getState().updateObject('t', { fontSize: 72 }); });
    openList();
    expect(listed()).toEqual(FONT_SIZES.map(String));
    fireEvent.change(sizeBox(), { target: { value: '1' } });
    expect(listed()).toEqual(FONT_SIZES.map(String));
  });

  it('a size clicked in the list is applied, closes the list, and is one undo step', () => {
    openList();
    fireEvent.mouseDown(screen.getByRole('option', { name: '48' }));
    expect(fontSize()).toBe(48);
    expect(screen.queryByRole('listbox')).toBeNull();
    expect(sizeBox().value).toBe('48');
    act(() => { useStore.getState().undo(); });
    expect(fontSize()).toBe(13);
  });

  it('takes a size that is not on the list, within 6..400', () => {
    fireEvent.change(sizeBox(), { target: { value: '150' } });
    fireEvent.keyDown(sizeBox(), { key: 'Enter' });
    expect(fontSize()).toBe(150);
    fireEvent.change(sizeBox(), { target: { value: '500' } });
    fireEvent.keyDown(sizeBox(), { key: 'Enter' });
    expect(fontSize()).toBe(400);
    fireEvent.change(sizeBox(), { target: { value: '3' } });
    fireEvent.blur(sizeBox());
    expect(fontSize()).toBe(6);
  });

  it('opens from the keyboard (Alt+Down, F4), closes with Escape without changing anything, and a press outside closes it', () => {
    fireEvent.keyDown(sizeBox(), { key: 'ArrowDown', altKey: true });
    expect(listed()).toHaveLength(17);
    fireEvent.keyDown(sizeBox(), { key: 'Escape' });
    expect(screen.queryByRole('listbox')).toBeNull();
    expect(fontSize()).toBe(13);
    fireEvent.keyDown(sizeBox(), { key: 'F4' });
    expect(listed()).toHaveLength(17);
    act(() => { document.body.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true })); });
    expect(screen.queryByRole('listbox')).toBeNull();
  });
});

describe('the font field', () => {
  it('is a real select listing every font in FONT_FAMILIES, not a datalist - and the format bar has no datalist left', () => {
    const select = screen.getByTitle('Font') as HTMLSelectElement;
    expect(select.tagName).toBe('SELECT');
    expect(Array.from(select.options).map(o => o.value)).toEqual(FONT_FAMILIES);
    expect(formatBarSource).not.toContain('<datalist');
    expect(formatBarSource).not.toContain('list=');
  });
});
