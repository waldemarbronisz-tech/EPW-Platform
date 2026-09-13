// feat/text-formatting: the Word-style formatting bar.
//
// One strip, grouped the way a word processor groups it:
//   [Insert text box] | Style | Font | Size | B I U | left centre right justify
// It acts on every selected text element at once and shows what they
// have in common - a blank box means the selection is mixed. With no
// text selected the bar stays usable, as in a word processor: what you
// pick becomes the format of the next text box you insert.

import React, { useMemo } from 'react';
import { StudioIcon } from './icons/StudioIcon';
import { useStore } from '../store';
import type { SynopticObject } from '../store';
import { FONT_SIZE_BASE, FONT_UI } from '../theme/ScadaTheme';
import {
  commonTextFormat, FONT_FAMILIES, isTextFormattable, TEXT_BOX_TYPE, stepFontSize, styleUpdates, TEXT_STYLES,
} from '../project/TextFormatting';
import type { TextAlign, TextStyleId } from '../project/TextFormatting';
import { insertTextBox } from './insertTextBox';
import { FontSizeCombo } from './FontSizeCombo';
import { fitTextBoxHeight } from '../utils/TextMeasure';
import { tr } from '../i18n/tr';

const ALIGNMENTS: { id: TextAlign; title: string; icon: string }[] = [
  { id: 'left', title: 'Align text left', icon: 'text_align_left' },
  { id: 'center', title: 'Center text', icon: 'text_align_center' },
  { id: 'right', title: 'Align text right', icon: 'text_align_right' },
  { id: 'justify', title: 'Justify text', icon: 'text_align_justify' },
];

export const FormatBar: React.FC = () => {
  const objects = useStore(s => s.objects);
  const selectedIds = useStore(s => s.selectedIds);
  const previewMode = useStore(s => s.previewMode);
  const nextTextFormat = useStore(s => s.nextTextFormat);

  const targets = useMemo(
    // fix/text-size: every selected element that carries text - a text
    // box, a label frame, the label of a symbol. It used to be text boxes
    // only, so with a symbol or a label frame selected the bar showed the
    // default 13 and edited nothing but the NEXT text box.
    () => objects.filter(o => selectedIds.includes(o.id)),
    [objects, selectedIds]
  );
  // Nothing selected: show (and edit) the format the next text box gets.
  const common = commonTextFormat(targets.length > 0
    ? targets
    : [{ type: TEXT_BOX_TYPE, font: FONT_UI, fontSize: FONT_SIZE_BASE, textAlign: 'left', textStyle: 'normal', ...nextTextFormat } as SynopticObject]);
  const enabled = !previewMode;

  const apply = (updates: Partial<SynopticObject>) => {
    if (!enabled) return;
    const state = useStore.getState();
    if (targets.length === 0) {
      state.setNextTextFormat(updates);
      return;
    }
    // A larger font or a new style can need more height - the box grows
    // to fit instead of clipping the last lines.
    state.updateObjects(targets.map(o => {
      const needed = isTextFormattable(o.type) ? fitTextBoxHeight({ ...o, ...updates }) : o.height;
      return { id: o.id, updates: needed > o.height ? { ...updates, height: needed } : updates };
    }));
    state.saveHistory();
  };

  const toggle = (key: 'fontBold' | 'fontItalic' | 'fontUnderline', current: boolean | null) => {
    // Mixed selections become "on", as in a word processor.
    apply({ [key]: current !== true } as Partial<SynopticObject>);
  };

  const pressed = (on: boolean | null) => (on === true ? ' format-bar-pressed' : '');

  return (
    <div className="format-bar" aria-label="Text formatting">
      <div className="format-bar-group">
        <button
          className="format-bar-wide"
          title="Insert a text box and start typing"
          onClick={insertTextBox}
          disabled={previewMode}
        >
          <StudioIcon name="text_box" />
          <span>Text box</span>
        </button>
      </div>

      <div className="format-bar-divider" />

      <div className="format-bar-group">
        <select
          title="Paragraph style"
          disabled={!enabled}
          value={common.style ?? ''}
          onChange={e => apply(styleUpdates(e.target.value as TextStyleId))}
          style={{ width: 96 }}
        >
          {common.style === null && <option value="" />}
          {TEXT_STYLES.map(style => <option key={style.id} value={style.id}>{style.label}</option>)}
        </select>

        <select
          title="Font"
          disabled={!enabled}
          value={common.font ?? ''}
          onChange={e => apply({ font: e.target.value })}
          style={{ width: 132 }}
        >
          {common.font === null && <option value="" />}
          {common.font !== null && !FONT_FAMILIES.includes(common.font) && (
            <option value={common.font}>{common.font}</option>
          )}
          {FONT_FAMILIES.map(font => (
            <option key={font} value={font} style={{ fontFamily: font }}>{font}</option>
          ))}
        </select>

        {/* An editable size box WITH a list of every size - not a datalist,
            which only suggests what matches the text already in the box
            (see FontSizeCombo.tsx). */}
        <FontSizeCombo value={common.fontSize} disabled={!enabled} onCommit={size => apply({ fontSize: size })} />
        <button title="Increase font size" disabled={!enabled} onClick={() => apply({ fontSize: stepFontSize(common.fontSize, 1) })}>
          <span className="format-bar-size-step">A+</span>
        </button>
        <button title="Decrease font size" disabled={!enabled} onClick={() => apply({ fontSize: stepFontSize(common.fontSize, -1) })}>
          <span className="format-bar-size-step">A-</span>
        </button>
      </div>

      <div className="format-bar-divider" />

      <div className="format-bar-group">
        <button title="Bold" className={pressed(common.bold)} disabled={!enabled} onClick={() => toggle('fontBold', common.bold)}>
          <StudioIcon name="text_bold" />
        </button>
        <button title="Italic" className={pressed(common.italic)} disabled={!enabled} onClick={() => toggle('fontItalic', common.italic)}>
          <StudioIcon name="text_italic" />
        </button>
        <button title="Underline" className={pressed(common.underline)} disabled={!enabled} onClick={() => toggle('fontUnderline', common.underline)}>
          <StudioIcon name="text_underline" />
        </button>
      </div>

      <div className="format-bar-divider" />

      <div className="format-bar-group">
        {ALIGNMENTS.map(({ id, title, icon }) => (
          <button
            key={id}
            title={title}
            className={pressed(common.align === id ? true : null)}
            disabled={!enabled}
            onClick={() => apply({ textAlign: id })}
          >
            <StudioIcon name={icon} />
          </button>
        ))}
      </div>

      <div className="format-bar-divider" />

      <div className="format-bar-group">
        <input
          type="color"
          title={tr('format.text_color')}
          aria-label={tr('format.text_color')}
          disabled={!enabled}
          value={common.color ?? '#000000'}
          onChange={e => apply({ textColor: e.target.value })}
          style={{ width: 32, height: 22, padding: 0 }}
        />
      </div>
    </div>
  );
};
