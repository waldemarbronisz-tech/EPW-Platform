// SCADA-style symbol 4/9: label frame, for marking power feeds and loads
// (e.g. "ZASILANIE / 230V AC", "DOM", "WARSZTAT"). Width hugs the text.
// One port, no states.

import React from 'react';
import { Group, Rect, Text } from 'react-konva';
import { COLOR_OUTLINE, COLOR_PANEL, FONT_UI, FONT_SIZE_TITLE, FONT_SIZE_BASE } from '../../theme/ScadaTheme';

// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this state list belongs beside its component.
export const LABEL_FRAME_STATES: string[] = [];

const PADDING_X = 14;
const PADDING_Y = 10;
// feat/appearance-selection-frames commit 1c: were locally-declared
// 16/12 - now ScadaTheme.ts's own FONT_SIZE_TITLE/FONT_SIZE_BASE (a
// frame's title is explicitly named alongside the meter/panel's own
// in 1c's typography spec). getBoundaryPointWidth's own tests
// (scada-editor.test.ts) only check clamp/relative-size behavior, not
// an exact pixel width, so this shrink is safe - see raport.md.
const TITLE_FONT_SIZE = FONT_SIZE_TITLE;
const DESC_FONT_SIZE = FONT_SIZE_BASE;
const LINE_GAP = 4;
const FRAME_OUTLINE_WIDTH = 4; // per this symbol's own spec, not OUTLINE_WIDTH

/**
 * No real canvas is available at layout time (this runs the same way in
 * tests, without font metrics), so width is estimated from character
 * count rather than measured - close enough for a frame that hugs its
 * text without needing to be pixel-exact.
 */
function estimateTextWidth(text: string, fontSize: number): number {
  return text.length * fontSize * 0.62;
}

// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this helper belongs beside its component.
export function getLabelFrameSize(title: string, description: string): { width: number; height: number } {
  const titleWidth = estimateTextWidth(title, TITLE_FONT_SIZE);
  const descWidth = estimateTextWidth(description, DESC_FONT_SIZE);
  const width = Math.max(titleWidth, descWidth) + PADDING_X * 2;
  const height = PADDING_Y * 2 + TITLE_FONT_SIZE + LINE_GAP + DESC_FONT_SIZE;
  return { width, height };
}

export interface LabelFrameSymbolProps {
  title: string;
  description: string;
  // Optional override for the frame's rendered width - defaults to the
  // organic getLabelFrameSize() width when omitted, so every existing
  // caller is unaffected. Added for BoundaryPointSymbol, which is built
  // on this component but clamps its width to a min/max range.
  width?: number;
}

export const LabelFrameSymbol: React.FC<LabelFrameSymbolProps> = ({ title, description, width: widthOverride }) => {
  const { width: autoWidth, height } = getLabelFrameSize(title, description);
  const width = widthOverride ?? autoWidth;

  return (
    <Group>
      <Rect x={0} y={0} width={width} height={height} fill={COLOR_PANEL} stroke={COLOR_OUTLINE} strokeWidth={FRAME_OUTLINE_WIDTH} />
      <Text x={PADDING_X} y={PADDING_Y} text={title} fontSize={TITLE_FONT_SIZE} fontFamily={FONT_UI} fontStyle="bold" fill={COLOR_OUTLINE} />
      <Text x={PADDING_X} y={PADDING_Y + TITLE_FONT_SIZE + LINE_GAP} text={description} fontSize={DESC_FONT_SIZE} fontFamily={FONT_UI} fill={COLOR_OUTLINE} />
    </Group>
  );
};
