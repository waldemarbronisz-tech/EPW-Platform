// fix/font-size-list: the font size box of the format bar - an editable
// field WITH a list, the way a word processor has it.
//
// It used to be <input list> with a <datalist>. A datalist is typing
// suggestions, not a list to choose from: the browser filters it by what is
// in the field, so with "13" in the box the only size it offered was 13. It
// had the arrow of a drop-down and behaved like autocomplete, and the only
// conclusion to draw was that there were no other sizes.
//
// Here the arrow opens a list of EVERY size in FONT_SIZES, whatever the
// field holds, and a click on one applies it. The field stays editable: a
// size that is not on the list (6..400) is typed and applied with Enter or
// by leaving the field. Alt+Down or F4 opens the list from the keyboard,
// Up/Down step to the neighbouring size, Escape closes the list or drops
// what was typed.
//
// The list is positioned against the window (position: fixed), so no panel
// the format bar sits in can clip it.

import React, { useEffect, useRef, useState } from 'react';
import { clampFontSize, FONT_SIZES, stepFontSize } from '../project/TextFormatting';
import { tr } from '../i18n/tr';

interface FontSizeComboProps {
  /** The size the selection shares, or null when it is mixed. */
  value: number | null;
  disabled: boolean;
  onCommit: (size: number) => void;
}

export const FontSizeCombo: React.FC<FontSizeComboProps> = ({ value, disabled, onCommit }) => {
  const [draft, setDraft] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [place, setPlace] = useState<{ left: number; top: number; width: number }>({ left: 0, top: 0, width: 0 });
  const boxRef = useRef<HTMLSpanElement>(null);

  const commitText = (text: string) => {
    setDraft(null);
    const trimmed = String(text).trim();
    const size = Number(trimmed.replace(',', '.'));
    if (trimmed === '' || !Number.isFinite(size) || size <= 0) return;
    onCommit(clampFontSize(size));
  };

  const openList = () => {
    const rect = boxRef.current?.getBoundingClientRect();
    if (rect) setPlace({ left: rect.left, top: rect.bottom, width: rect.width });
    setOpen(true);
  };

  // A press anywhere outside the box and its list closes the list.
  useEffect(() => {
    if (!open) return;
    const close = (e: PointerEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener('pointerdown', close, true);
    return () => window.removeEventListener('pointerdown', close, true);
  }, [open]);

  return (
    <span ref={boxRef} className="format-combo">
      <input
        title="Font size"
        aria-label={tr('format.font_size')}
        disabled={disabled}
        value={draft ?? String(value ?? '')}
        onFocus={e => e.currentTarget.select()}
        onChange={e => setDraft(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter') {
            commitText(e.currentTarget.value);
            setOpen(false);
            e.currentTarget.blur();
          } else if (e.key === 'Escape') {
            if (open) setOpen(false);
            else { setDraft(null); e.currentTarget.blur(); }
          } else if (e.key === 'F4' || (e.altKey && e.key === 'ArrowDown')) {
            e.preventDefault();
            if (open) setOpen(false); else openList();
          } else if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
            e.preventDefault();
            setDraft(null);
            onCommit(stepFontSize(value, e.key === 'ArrowUp' ? 1 : -1));
          }
          e.stopPropagation();
        }}
        onBlur={() => { if (draft !== null) commitText(draft); }}
        style={{ width: 40 }}
      />
      <button
        type="button"
        className="format-combo-toggle"
        title={tr('format.show_sizes')}
        aria-haspopup="listbox"
        aria-expanded={open}
        disabled={disabled}
        // Keep the focus where it is: the list must not take a pending
        // edit's keyboard away.
        onMouseDown={e => e.preventDefault()}
        onClick={() => (open ? setOpen(false) : openList())}
      >
        ▾
      </button>
      {open && (
        <div
          role="listbox"
          aria-label={tr('format.font_size')}
          data-list="font-sizes"
          className="format-combo-list"
          style={{ position: 'fixed', left: place.left, top: place.top, minWidth: place.width }}
        >
          {FONT_SIZES.map(size => (
            <div
              key={size}
              role="option"
              aria-selected={value === size}
              className={value === size ? 'format-combo-option format-combo-option-current' : 'format-combo-option'}
              onMouseDown={e => {
                e.preventDefault();
                setDraft(null);
                setOpen(false);
                onCommit(size);
              }}
            >
              {size}
            </div>
          ))}
        </div>
      )}
    </span>
  );
};
