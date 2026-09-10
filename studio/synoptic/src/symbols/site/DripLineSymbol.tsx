// feat/water-management commit 5 - "12. Linia kroplujaca" (linia_krop)
// from docs/EPW_gospodarka_wodna_referencja.py's own linia_krop(on).
// Pure graphics - no tag. "Rozciagana wzdluz, jak powierzchnia" (this
// task's own wording) - adjustable size, the SAME real-size-aware,
// inverse-scale-Group technique GrassSymbol.tsx/ConcreteRoadSymbol.tsx
// (feat/site-objects-2d commit 4) already established for a symbol
// whose own internal geometry must recompute for whatever size it is
// actually stretched to, rather than stretching one fixed drawing -
// deliberately NOT marked isSurface, though: that flag exists so grass/
// road draw in their own BACKGROUND pass, below every ordinary symbol
// (Canvas.tsx) - nothing in this task asks other objects to draw above
// a drip line the way they do above grass, and a drip line sits on the
// same visual level as a sprinkler head, not beneath it.
//
// Only the horizontal axis (dripper count/spacing) is recomputed for
// the real width - the vertical layout (pipe/dripper/drop/moisture-
// ellipse y-positions) stays exactly at the reference's own fixed
// values, the same "only vary what the task actually asks to be
// resizable" precedent ConcreteRoadSymbol.tsx's own joints/dashes
// already set (those vary with width only too, never height).

import React from 'react';
import { Group, Rect, Path, Ellipse } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { objectPipeSegment, waterStub } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import { COLOR_OUTLINE, SITE_DGREY, SITE_BLUE } from '../../theme/ScadaTheme';

export type DripLineState = 'ON' | 'OFF';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as every other site/ symbol.
export const DRIP_LINE_STATES: DripLineState[] = ['ON', 'OFF'];

// docs/EPW_gospodarka_wodna_referencja.py's own linia_krop(on): 4
// drippers at x=24,48,72,96 - a 24-unit spacing, first dripper 18
// units in from the pipe's own start (x=6). Reused as the TARGET
// spacing/margin for an arbitrary real width, rather than a fixed count.
const DRIPPER_MARGIN = 20;
const DRIPPER_SPACING = 24;

/** Pure function of width alone - same width always gives the same dripper x-positions, evenly spanning it (no randomness needed here at all: the reference's own layout is already perfectly regular). */
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to, for testability without rendering Konva (same convention SurfaceGeometry.ts's own siblings use).
export function computeDripperPositions(width: number): number[] {
  const usable = Math.max(0, width - DRIPPER_MARGIN * 2);
  const count = Math.max(1, Math.round(usable / DRIPPER_SPACING) + 1);
  if (count === 1) return [width / 2];
  const actualSpacing = usable / (count - 1);
  return Array.from({ length: count }, (_, i) => DRIPPER_MARGIN + i * actualSpacing);
}

export const DripLineSymbol: React.FC<SymbolProps> = ({ obj, state, terminalNetState }) => {
  const on = resolveSiteState(state, DRIP_LINE_STATES, 'OFF') === 'ON';
  const wlotLive = (terminalNetState?.('WLOT') ?? 'INACTIVE') === 'ACTIVE';
  const scaleX = obj.scaleX || 1;
  const scaleY = obj.scaleY || 1;
  const realWidth = obj.width * scaleX;
  const realHeight = obj.height * scaleY;
  const drippers = computeDripperPositions(realWidth);

  return (
    <Group scaleX={1 / scaleX} scaleY={1 / scaleY}>
      {/* A thin pipe plus a few small dripper rects leaves most of the
          object's own declared bounds empty - without a real (if
          invisible) shape spanning the whole area, clicking anywhere
          that is not exactly on the pipe or a dripper would miss the
          object entirely, unlike every other symbol in this library
          (found live, via Playwright, while checking this task's own
          checklist - not assumed). */}
      <Rect x={0} y={0} width={realWidth} height={realHeight} fill="transparent" />
      {/* fix/hydraulic-connections commit 5: krociec+kolnierz at the
          one real terminal (WLOT, LEFT) - the true terminal height is
          realHeight/2 (48 at the default size), not the old fixed 44.
          The right END of the drawn pipe is NOT a terminal at all (a
          drip line has only one) so it stays a plain open pipe end,
          same as before, just at the corrected height. canvasWidth/
          Height passed as realWidth/realHeight, not the fixed 128x96
          every other water object uses - this is the one object whose
          own "canvas" is genuinely adjustable. */}
      {waterStub(20, realHeight / 2, 'L', wlotLive, realWidth, realHeight, { width: 11 })}
      {objectPipeSegment([{ x: 20, y: realHeight / 2 }, { x: realWidth - 6, y: realHeight / 2 }], on, { width: 11 })}
      {drippers.map(x => (
        <Group key={x} listening={false}>
          <Rect x={x - 4} y={54} width={8} height={7} fill={SITE_DGREY.base} stroke={COLOR_OUTLINE} strokeWidth={1.8} />
          {on && (
            <>
              <Path data={`M${x},64 q3,7 0,11 q-3,-4 0,-11 Z`} fill={SITE_BLUE.base} stroke={COLOR_OUTLINE} strokeWidth={1.5} />
              <Ellipse x={x} y={88} radiusX={9} radiusY={3.5} fill={SITE_BLUE.base} opacity={0.45} />
            </>
          )}
        </Group>
      ))}
    </Group>
  );
};
