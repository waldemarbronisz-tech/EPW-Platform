// Konva rendering for the frame element (feat/appearance-selection-
// frames commit 3). PLAIN: outline only, transparent interior - this
// is a requirement, not a preference, per this element's own spec: a
// frame surrounds its contents, it does not hide them. BUILDING: the
// same rectangle, walls just as unfilled, with a gable roof drawn
// above the top edge.
//
// Deliberately its own component, not a case inside SymbolRenderer.tsx
// - a frame is not a symbol (see FrameElement.ts's own header comment,
// same reasoning MeterElementNode/SignalPanelElementNode already
// state for themselves).

import React, { useEffect, useRef } from 'react';
import { Group, Line, Text } from 'react-konva';
import type { FrameElement } from '../elements/FrameElement';
import { FRAME_MIN_SIZE } from '../elements/FrameElement';
import { computeResizeFromAnchor, getActiveResizeAnchor, setActiveResizeAnchor } from '../utils/ResizeHandles';
import { COLOR_OUTLINE, OUTLINE_WIDTH, FONT_UI, FONT_SIZE_TITLE, GRID_SIZE } from '../theme/ScadaTheme';

const TITLE_PADDING_X = 6; // gap between the title text and where the border line resumes on either side
const TITLE_INSET = 12;    // TOP_LEFT's own left margin before the gap starts
const ROOF_HEIGHT_FACTOR = 0.25; // "about a quarter of the frame's own height", per this element's own spec
const ROOF_HATCH_SPACING = 6;
const ROOF_HATCH_OPACITY = 0.35; // "dyskretne" - subtle, not a solid fill

/** Same character-count estimate LabelFrameSymbol.tsx already uses - no real canvas font metrics available at layout time, and a frame's border gap only needs to be roughly right, not pixel-exact. */
function estimateTextWidth(text: string, fontSize: number): number {
  return text.length * fontSize * 0.62;
}

export interface FrameElementNodeProps {
  frame: FrameElement;
  onSelect: (e?: any) => void;
  onDragEnd: (x: number, y: number) => void;
  onDragStart?: () => void;
  onDragMove?: (x: number, y: number) => void;
  onShapeRef?: (node: any) => void;
  // 3f/3g: resize via corner/edge handles (FrameTransformerHandle in
  // Canvas.tsx drives the Transformer itself; this Group's own
  // onTransformEnd is what turns a Transformer's scale back into a
  // real width/height, clamped to the 2-grid-cell minimum - the exact
  // same split of responsibility ObjectNode's own onTransformEnd
  // already uses for a symbol's resize, just baking the scale into
  // width/height instead of keeping a separate scaleX/scaleY (a frame
  // has no native artwork of its own to scale - its width/height ARE
  // its geometry, per this element's own 3a spec).
  onResize?: (x: number, y: number, width: number, height: number) => void;
}

export const FrameElementNode: React.FC<FrameElementNodeProps> = ({ frame, onSelect, onDragEnd, onDragStart, onDragMove, onShapeRef, onResize }) => {
  const { width, height, title, titlePosition, variant } = frame;
  const hasTitle = !!title;

  // The top edge's own gap for the title, "like a switchgear panel's
  // own field label" per this element's spec - two separate line
  // segments instead of one continuous edge, with the title sitting in
  // the space between them, vertically straddling the line the same
  // way a real schematic's panel-field label does. No gap at all (a
  // single unbroken top edge) when there is no title to make room for.
  let gapStart = 0;
  let gapEnd = 0;
  if (hasTitle) {
    const textWidth = estimateTextWidth(title!, FONT_SIZE_TITLE) + TITLE_PADDING_X * 2;
    gapStart = titlePosition === 'TOP_CENTER' ? Math.max(0, (width - textWidth) / 2) : TITLE_INSET;
    gapEnd = Math.min(width, gapStart + textWidth);
  }

  const roofHeight = height * ROOF_HEIGHT_FACTOR;
  const hatchLines: number[] = [];
  if (variant === 'BUILDING') {
    for (let y = -ROOF_HATCH_SPACING; y > -roofHeight; y -= ROOF_HATCH_SPACING) {
      hatchLines.push(y);
    }
  }

  const groupRef = useRef<any>(null);
  useEffect(() => {
    onShapeRef?.(groupRef.current);
  });

  return (
    <Group
      ref={groupRef}
      x={frame.x}
      y={frame.y}
      draggable
      onClick={onSelect}
      onTap={onSelect}
      onDragStart={() => onDragStart?.()}
      onDragMove={(e) => onDragMove?.(e.target.x(), e.target.y())}
      onDragEnd={(e) => onDragEnd(e.target.x(), e.target.y())}
      onTransformEnd={() => {
        const node = groupRef.current;
        if (!node || !onResize) return;
        const anchor = getActiveResizeAnchor();
        setActiveResizeAnchor(null);

        // fix/handles-insert-mode-diodes commit 1: computeResizeFromAnchor
        // keeps the corner/edge OPPOSITE the one dragged exactly fixed
        // (by construction, not by coincidence) and enforces
        // FRAME_MIN_SIZE - the same shared math ObjectNode's own resize
        // uses, so a frame's corner/edge handles behave identically to
        // every other resizable element's own. The ORIGINAL rect comes
        // from the frame prop (the store's own last-committed values),
        // never from node.x()/node.y() - those reflect whatever Konva's
        // Transformer left them at mid-drag, not a clean baseline to
        // compute a fixed corner from. Falls back to the plain scale-
        // based read (frame's own pre-fix behavior) only if somehow no
        // anchor was recorded - should not happen in practice (frames
        // have no rotate handle to confuse this with), kept purely as
        // a safety net.
        const rawWidth = width * node.scaleX();
        const rawHeight = height * node.scaleY();
        const resized = anchor && anchor !== 'rotater'
          ? computeResizeFromAnchor(anchor, { x: frame.x, y: frame.y, width, height }, rawWidth, rawHeight, GRID_SIZE, FRAME_MIN_SIZE)
          : { x: frame.x, y: frame.y, width: Math.max(FRAME_MIN_SIZE, rawWidth), height: Math.max(FRAME_MIN_SIZE, rawHeight) };

        // Konva's own Transformer mutates this node's x/y/scaleX/scaleY
        // directly while the drag is live - when the committed value
        // equals what it already was (the fixed corner, usually),
        // React sees no prop change and never re-applies it, leaving
        // Konva's own live-drag value on screen instead of what was
        // just committed. Reset explicitly, every time, so the node's
        // on-screen state can never drift from the store's - this also
        // is what resets scale back to a clean 1:1 for the next resize,
        // now that width/height are baked into the store fields
        // instead (a frame has no native artwork of its own to scale).
        node.x(resized.x);
        node.y(resized.y);
        node.scaleX(1);
        node.scaleY(1);
        onResize(resized.x, resized.y, resized.width, resized.height);
      }}
    >
      {variant === 'BUILDING' && (
        <>
          {/* Roof tile hatching, clipped to the triangle so the lines
              never spill past its own slanted edges - drawn BEFORE the
              roof's own outline so the outline sits crisply on top. */}
          <Group
            clipFunc={(ctx: any) => {
              ctx.beginPath();
              ctx.moveTo(width / 2, -roofHeight);
              ctx.lineTo(0, 0);
              ctx.lineTo(width, 0);
              ctx.closePath();
            }}
          >
            {hatchLines.map((y, i) => (
              <Line key={i} points={[0, y, width, y]} stroke={COLOR_OUTLINE} strokeWidth={1} opacity={ROOF_HATCH_OPACITY} listening={false} />
            ))}
          </Group>
          <Line
            points={[width / 2, -roofHeight, 0, 0, width, 0]}
            closed
            stroke={COLOR_OUTLINE}
            strokeWidth={OUTLINE_WIDTH}
            fill="transparent"
          />
        </>
      )}

      {/* Walls / plain frame - transparent interior either way, per
          this element's own explicit requirement (never a preference):
          the frame surrounds its contents, it must never hide them. */}
      {hasTitle ? (
        <>
          <Line points={[0, 0, gapStart, 0]} stroke={COLOR_OUTLINE} strokeWidth={OUTLINE_WIDTH} />
          <Line points={[gapEnd, 0, width, 0]} stroke={COLOR_OUTLINE} strokeWidth={OUTLINE_WIDTH} />
        </>
      ) : (
        <Line points={[0, 0, width, 0]} stroke={COLOR_OUTLINE} strokeWidth={OUTLINE_WIDTH} />
      )}
      <Line points={[width, 0, width, height]} stroke={COLOR_OUTLINE} strokeWidth={OUTLINE_WIDTH} />
      <Line points={[width, height, 0, height]} stroke={COLOR_OUTLINE} strokeWidth={OUTLINE_WIDTH} />
      <Line points={[0, height, 0, 0]} stroke={COLOR_OUTLINE} strokeWidth={OUTLINE_WIDTH} />

      {hasTitle && (
        <Text
          x={gapStart + TITLE_PADDING_X}
          y={-FONT_SIZE_TITLE / 2}
          width={gapEnd - gapStart - TITLE_PADDING_X * 2}
          text={title}
          fontSize={FONT_SIZE_TITLE}
          fontFamily={FONT_UI}
          fontStyle="bold"
          align="left"
          fill={COLOR_OUTLINE}
        />
      )}

      {/* An invisible, listening-only fill so the frame's own empty
          interior can still be clicked/selected/dragged - a purely
          outlined shape has no hit area of its own in the middle,
          which would make it unselectable except by clicking its
          border pixel-exactly. This paints nothing (opacity 0), it
          only participates in hit testing. */}
      <Line points={[0, 0, width, 0, width, height, 0, height]} closed fill={COLOR_OUTLINE} opacity={0} />
    </Group>
  );
};
