// feat/text-formatting: the text box on the canvas.
//
// Draws the element's own text with its own format (project/
// TextFormatting.ts) - font, size, bold / italic / underline, alignment
// including justified - wrapped inside the box. An empty box shows a
// faint placeholder and a dashed outline so it can still be found and
// clicked; a box with text has no frame at all, like text in a document.
//
// While the box is being edited in place (TextEditOverlay) the canvas
// text is hidden, so the editor and the drawing never show two copies.

import React from 'react';
import { Group, Rect, Text } from 'react-konva';
import type { SynopticObject } from '../../store';
import { useStore } from '../../store';
import {
  konvaFontStyle, textFormatOf, TEXT_BOX_PADDING, TEXT_LINE_HEIGHT,
} from '../../project/TextFormatting';
import { COLOR_OUTLINE } from '../../theme/ScadaTheme';
import { tr } from '../../i18n/tr';

export const TextBoxSymbol: React.FC<{ obj: SynopticObject }> = ({ obj }) => {
  const editing = useStore(s => s.editingTextId === obj.id);
  const format = textFormatOf(obj);
  const empty = !(obj.text || '').trim();
  const innerWidth = Math.max(1, obj.width - TEXT_BOX_PADDING * 2);
  const innerHeight = Math.max(1, obj.height - TEXT_BOX_PADDING * 2);

  return (
    <Group>
      {/* Transparent fill: the whole box is clickable, not just the
          glyphs. The outline only appears while the box is empty. */}
      <Rect
        width={obj.width}
        height={obj.height}
        fill="rgba(0,0,0,0)"
        stroke={COLOR_OUTLINE}
        strokeWidth={empty ? 1 : 0}
        dash={[4, 3]}
        opacity={0.45}
      />
      {!editing && (
        <Text
          x={TEXT_BOX_PADDING}
          y={TEXT_BOX_PADDING}
          width={innerWidth}
          height={innerHeight}
          text={empty ? tr('text.placeholder') : obj.text}
          fontFamily={format.font}
          fontSize={format.fontSize}
          fontStyle={konvaFontStyle(format)}
          textDecoration={format.underline ? 'underline' : ''}
          align={format.align}
          verticalAlign="top"
          wrap="word"
          lineHeight={TEXT_LINE_HEIGHT}
          fill={obj.color || COLOR_OUTLINE}
          opacity={empty ? 0.4 : 1}
          listening={false}
        />
      )}
    </Group>
  );
};
