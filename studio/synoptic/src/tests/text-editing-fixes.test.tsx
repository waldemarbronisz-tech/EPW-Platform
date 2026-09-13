/** @vitest-environment jsdom */
// Text editing in Synoptic, walked through in the running editor with real
// mouse and keyboard (studio/synoptic REPORT): typing, Polish letters,
// several lines, click-away, double-click, Esc, Enter, F2, Ctrl+Enter and
// formatting all worked. What did not, and is pinned here:
//
//   - Ctrl+Z / Ctrl+Y did nothing after an edit - the editor had no undo
//     key at all;
//   - a fresh text box closed with no text stayed on the screen as a grey
//     "Text" placeholder - junk that still took clicks;
//   - that placeholder was an English word written into the symbol.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, cleanup, fireEvent, act } from '@testing-library/react';
import { useStore } from '../store';
import type { SynopticObject } from '../store';
import { TextEditOverlay } from '../components/TextEditOverlay';
import { TEXT_BOX_TYPE } from '../project/TextFormatting';
import { editorShortcut } from '../utils/EditorShortcuts';
import { insertTextBox } from '../components/insertTextBox';
import { setLanguage, tr } from '../i18n/tr';
import textBoxSource from '../symbols/scada/TextBoxSymbol.tsx?raw';
import canvasSource from '../components/Canvas.tsx?raw';

const box = (id: string, text: string): SynopticObject => ({
  id, type: TEXT_BOX_TYPE, category: 'SCADA', x: 80, y: 80, rotation: 0, scaleX: 1, scaleY: 1,
  visible: true, locked: false, layer: 1, tag: '', description: '',
  color: '', fill: '', border: '', text, font: 'Tahoma', fontSize: 13,
  tooltip: '', width: 240, height: 48, customProperties: {},
});

const area = () => document.querySelector('textarea') as HTMLTextAreaElement;
const textOf = (id: string) => useStore.getState().objects.find(o => o.id === id)?.text;

beforeEach(() => {
  setLanguage('en');
  useStore.setState({
    objects: [], connections: [], meters: [], signalPanels: [], frames: [], walls: [], circuits: [],
    groupCommands: [], setpointPanels: [],
    history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [], walls: [], circuits: [], groupCommands: [], setpointPanels: [] }],
    historyIndex: 0,
    editingTextId: null,
    canvasState: { zoom: 1, panX: 0, panY: 0 },
    previewMode: false,
    workMode: 'SYMBOLS',
  });
});
afterEach(cleanup);

describe('a text box left empty is removed, not left behind', () => {
  it('Esc on a freshly inserted, still empty box removes it', () => {
    act(() => { insertTextBox(); });
    render(<TextEditOverlay />);
    expect(useStore.getState().objects).toHaveLength(1);
    fireEvent.keyDown(area(), { key: 'Escape' });
    expect(useStore.getState().objects).toHaveLength(0);
    expect(useStore.getState().editingTextId).toBeNull();
  });

  it('clicking away from a box whose text was erased removes it, and Ctrl+Z brings it back', () => {
    act(() => {
      useStore.getState().addObject(box('ignored', 'Boiler room'));
    });
    const id = useStore.getState().objects[0].id;
    act(() => { useStore.getState().setEditingTextId(id); });
    render(<TextEditOverlay />);
    area().value = '   ';
    act(() => { window.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true })); });
    expect(useStore.getState().objects).toHaveLength(0);
    act(() => { useStore.getState().undo(); });
    expect(useStore.getState().objects.map(o => o.text)).toEqual(['Boiler room']);
  });

  it('Esc on a box that already had text keeps the box and its text', () => {
    act(() => { useStore.getState().addObject(box('ignored', 'Pumps')); });
    const id = useStore.getState().objects[0].id;
    act(() => { useStore.getState().setEditingTextId(id); });
    render(<TextEditOverlay />);
    area().value = 'Pumps and more';
    fireEvent.keyDown(area(), { key: 'Escape' });
    expect(textOf(id)).toBe('Pumps');
  });
});

describe('undo after an edit', () => {
  it('a committed edit is one undo step: Ctrl+Z restores the text before it, Ctrl+Y the edit', () => {
    act(() => { useStore.getState().addObject(box('ignored', 'Kotłownia')); });
    const id = useStore.getState().objects[0].id;
    act(() => { useStore.getState().setEditingTextId(id); });
    render(<TextEditOverlay />);
    area().value = 'Kotłownia ąęśćżźńół\nPompy';
    fireEvent.keyDown(area(), { key: 'Enter', ctrlKey: true });
    expect(textOf(id)).toBe('Kotłownia ąęśćżźńół\nPompy');

    const undoKey = editorShortcut({ key: 'z', ctrlKey: true });
    expect(undoKey).toEqual({ kind: 'undo' });
    act(() => { useStore.getState().undo(); });
    expect(textOf(id)).toBe('Kotłownia');
    expect(editorShortcut({ key: 'y', ctrlKey: true })).toEqual({ kind: 'redo' });
    expect(editorShortcut({ key: 'Z', ctrlKey: true, shiftKey: true })).toEqual({ kind: 'redo' });
    act(() => { useStore.getState().redo(); });
    expect(textOf(id)).toBe('Kotłownia ąęśćżźńół\nPompy');
    expect(useStore.getState().isDirty).toBe(true);
  });

  it('the canvas handles those keys - and only when no text field has the keyboard', () => {
    const handler = canvasSource.slice(canvasSource.indexOf('const handleKeyDown'));
    const typingGuard = handler.indexOf('if (isTypingInField()) return;');
    const shortcut = handler.indexOf('editorShortcut(e)');
    const escape = handler.indexOf("if (e.key === 'Escape')");
    expect(typingGuard).toBeGreaterThan(-1);
    expect(shortcut).toBeGreaterThan(typingGuard);
    expect(escape).toBeGreaterThan(shortcut);
    expect(handler).toContain("if (shortcut.kind === 'undo') s.undo();");
  });
});

describe('the placeholder and the mode', () => {
  it('the empty-box placeholder is translated, not an English word in the symbol', () => {
    expect(textBoxSource).toContain("tr('text.placeholder')");
    expect(textBoxSource).not.toContain("'Text'");
    expect(tr('text.placeholder', undefined, 'en')).toBe('Text');
    expect(tr('text.placeholder', undefined, 'pl')).toBe('Tekst');
  });

  it('inserting a text box puts the editor in the ANNOTATIONS mode, where the box can be selected', () => {
    act(() => { insertTextBox(); });
    expect(useStore.getState().workMode).toBe('ANNOTATIONS');
    expect(useStore.getState().editingTextId).toBe(useStore.getState().objects[0].id);
  });
});
