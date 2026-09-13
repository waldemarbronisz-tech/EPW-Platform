// feat/text-formatting: typing straight into a text box on the canvas.
//
// A textarea laid exactly over the box, in the box's own font, size,
// weight, style, decoration and alignment, scaled with the view - so
// editing looks like the text itself became editable.
//
// Behaves like a text box in a word processor:
//   - Enter makes a new line; the box grows downward as you type.
//   - Clicking anywhere outside the box keeps the text and ends editing.
//     This is a window-level pointer listener, NOT the textarea's blur:
//     Konva prevents the default action of a mousedown on the canvas, so
//     a click on the drawing never moves focus and a blur-based editor
//     simply stayed open with the text unsaved.
//   - Ctrl+Enter keeps the text too; Escape throws the edit away and
//     puts the box back to its original size.
//   - With one text box selected, Enter or F2 starts editing it.

import React, { useEffect, useRef } from 'react';
import { useStore } from '../store';
import {
  isTextFormattable, textFormatOf, TEXT_BOX_PADDING, TEXT_LINE_HEIGHT,
} from '../project/TextFormatting';
import { fitTextBoxHeight } from '../utils/TextMeasure';
import { COLOR_OUTLINE } from '../theme/ScadaTheme';

export const TextEditOverlay: React.FC = () => {
  const editingId = useStore(s => s.editingTextId);
  const obj = useStore(s => (s.editingTextId ? s.objects.find(o => o.id === s.editingTextId) : undefined));
  const view = useStore(s => s.canvasState);
  const areaRef = useRef<HTMLTextAreaElement>(null);
  const originalHeightRef = useRef(0);
  const doneRef = useRef(false);

  /** Ends editing: keeps `value`, or restores the box when `value` is null. */
  const finish = (value: string | null) => {
    const state = useStore.getState();
    const id = state.editingTextId;
    if (!id || doneRef.current) return;
    doneRef.current = true;
    const current = state.objects.find(o => o.id === id);
    if (current) {
      if (value === null) {
        if (current.height !== originalHeightRef.current) {
          state.updateObject(id, { height: originalHeightRef.current });
        }
      } else {
        const height = Math.max(originalHeightRef.current, fitTextBoxHeight({ ...current, text: value }));
        const textChanged = value !== current.text;
        if (textChanged || height !== originalHeightRef.current) {
          state.updateObject(id, { text: value, height });
          state.saveHistory();
        }
      }
    }
    state.setEditingTextId(null);
  };

  // Start of an edit: remember the size to go back to, focus, caret at the end.
  useEffect(() => {
    if (!editingId) return;
    doneRef.current = false;
    const current = useStore.getState().objects.find(o => o.id === editingId);
    originalHeightRef.current = current ? current.height : 0;
    const area = areaRef.current;
    if (area) {
      area.focus();
      area.setSelectionRange(area.value.length, area.value.length);
    }
  }, [editingId]);

  // A click anywhere outside the box keeps the text.
  useEffect(() => {
    if (!editingId) return;
    const onPointerDown = (e: PointerEvent) => {
      const area = areaRef.current;
      if (area && e.target !== area) finish(area.value);
    };
    window.addEventListener('pointerdown', onPointerDown, true);
    return () => window.removeEventListener('pointerdown', onPointerDown, true);
    // finish reads everything it needs from the store at call time.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editingId]);

  // Enter / F2 on a single selected text box starts editing it.
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Enter' && e.key !== 'F2') return;
      const state = useStore.getState();
      if (state.editingTextId || state.previewMode || state.selectedIds.length !== 1) return;
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT' || target.isContentEditable)) return;
      const selected = state.objects.find(o => o.id === state.selectedIds[0]);
      if (!selected || !isTextFormattable(selected.type)) return;
      e.preventDefault();
      e.stopPropagation();
      state.setEditingTextId(selected.id);
    };
    window.addEventListener('keydown', onKeyDown, true);
    return () => window.removeEventListener('keydown', onKeyDown, true);
  }, []);

  if (!editingId || !obj) return null;

  const format = textFormatOf(obj);
  const zoom = view.zoom;

  return (
    <textarea
      ref={areaRef}
      defaultValue={obj.text || ''}
      spellCheck={false}
      onInput={e => {
        // Grow while typing - no history entry; the edit as a whole is one.
        const value = (e.target as HTMLTextAreaElement).value;
        const state = useStore.getState();
        const current = state.objects.find(o => o.id === obj.id);
        if (!current) return;
        const needed = fitTextBoxHeight({ ...current, text: value });
        if (needed > current.height) state.updateObject(obj.id, { height: needed });
      }}
      onKeyDown={e => {
        // Keys typed here belong to the text, not to the canvas shortcuts.
        e.stopPropagation();
        if (e.key === 'Escape') {
          e.preventDefault();
          finish(null);
        } else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
          e.preventDefault();
          finish((e.target as HTMLTextAreaElement).value);
        }
      }}
      style={{
        position: 'absolute',
        left: view.panX + obj.x * zoom,
        top: view.panY + obj.y * zoom,
        width: obj.width * (obj.scaleX || 1) * zoom,
        height: obj.height * (obj.scaleY || 1) * zoom,
        boxSizing: 'border-box',
        padding: TEXT_BOX_PADDING * zoom,
        margin: 0,
        border: `1px dashed ${COLOR_OUTLINE}`,
        outline: 'none',
        resize: 'none',
        overflow: 'hidden',
        background: 'rgba(255,255,255,0.92)',
        color: obj.color || COLOR_OUTLINE,
        fontFamily: format.font,
        fontSize: format.fontSize * zoom,
        fontWeight: format.bold ? 'bold' : 'normal',
        fontStyle: format.italic ? 'italic' : 'normal',
        textDecoration: format.underline ? 'underline' : 'none',
        textAlign: format.align,
        lineHeight: TEXT_LINE_HEIGHT,
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        zIndex: 20,
      }}
    />
  );
};
