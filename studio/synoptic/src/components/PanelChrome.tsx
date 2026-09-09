// Shared Konva chrome for the two "panel" elements (MeterElementNode.tsx,
// feat/editing-and-signal-panel commit 6's SignalPanelElementNode.tsx):
// the panel-color background rect, black outline, and (when present) a
// bold centered title with a divider line underneath it - identical
// between the two per their own specs. Renders only this shell; the
// caller wraps it in its own positioned/draggable Group and supplies its
// own row content as children, positioned using getPanelRowLayout below
// so row placement stays in lockstep with the title block's own height.
//
// MeterElementNode.tsx now renders through this rather than its own
// copy of the same Rect/Text/Line - meter-element.test.ts's tests are
// unaffected (this is a rendering-only extraction, no pure logic
// touched), and there is no rendering test to regress since this
// codebase has never had a Konva rendering harness (see raport.md).

import React from 'react';
import { Rect, Text, Line } from 'react-konva';
import {
  PANEL_PADDING_X, PANEL_PADDING_Y, PANEL_ROW_HEIGHT_FACTOR,
  PANEL_TITLE_HEIGHT_FACTOR, PANEL_TITLE_DIVIDER_GAP, PANEL_DEFAULT_FONT_SIZE
} from '../elements/PanelLayout';
import { COLOR_PANEL, COLOR_OUTLINE, COLOR_TEXT, FONT_UI, FONT_SIZE_TITLE } from '../theme/ScadaTheme';

export const PANEL_OUTLINE_WIDTH = 4; // per this element family's own spec, not ScadaTheme's OUTLINE_WIDTH

/**
 * Row height and title-block height for a given font size - what a
 * caller needs to position its own rows under this chrome's title.
 * titleBlockHeight uses the theme's own fixed FONT_SIZE_TITLE (not the
 * passed fontSize) - it MUST stay in lockstep with PanelLayout.ts's
 * computePanelHeight, which makes the exact same choice for the exact
 * same reason (see that function's own comment).
 */
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to; both callers (MeterElementNode.tsx, SignalPanelElementNode.tsx) need it to position their own rows.
export function getPanelRowLayout(fontSize: number, hasTitle: boolean) {
  const size = fontSize || PANEL_DEFAULT_FONT_SIZE;
  return {
    rowHeight: size * PANEL_ROW_HEIGHT_FACTOR,
    titleBlockHeight: hasTitle ? FONT_SIZE_TITLE * PANEL_TITLE_HEIGHT_FACTOR + PANEL_TITLE_DIVIDER_GAP : 0
  };
}

export interface PanelChromeProps {
  width: number;
  height: number;
  title?: string;
  fontSize: number;
  children?: React.ReactNode;
}

export const PanelChrome: React.FC<PanelChromeProps> = ({ width, height, title, fontSize, children }) => {
  const hasTitle = !!title;
  const { titleBlockHeight } = getPanelRowLayout(fontSize, hasTitle);

  return (
    <>
      <Rect width={width} height={height} fill={COLOR_PANEL} stroke={COLOR_OUTLINE} strokeWidth={PANEL_OUTLINE_WIDTH} />
      {hasTitle && (
        <>
          <Text
            x={PANEL_PADDING_X}
            y={PANEL_PADDING_Y}
            width={width - PANEL_PADDING_X * 2}
            text={title}
            fontSize={FONT_SIZE_TITLE}
            fontFamily={FONT_UI}
            fontStyle="bold"
            align="center"
            fill={COLOR_TEXT}
          />
          <Line
            points={[0, PANEL_PADDING_Y + titleBlockHeight - PANEL_TITLE_DIVIDER_GAP / 2, width, PANEL_PADDING_Y + titleBlockHeight - PANEL_TITLE_DIVIDER_GAP / 2]}
            stroke={COLOR_OUTLINE}
            strokeWidth={1}
          />
        </>
      )}
      {children}
    </>
  );
};
