// feat/cad-marquee: the eight handles that resize a whole selection -
// in practice, a whole room.
//
// A room is several walls, and until now nothing could act on them
// together: a wall could be dragged, but the room around it could not be
// made bigger without redrawing it. Select its walls with a crossing
// marquee and this appears around them, behaving the way a resize
// handle behaves everywhere - the opposite edge stays put, corners take
// both axes, edges take one.
//
// WHAT IT DOES NOT DO. It does not scale the objects inside. Geometry
// scales, objects move - project/GroupScale.ts's header has the full
// argument, and it is the difference between a plan and a picture.
//
// The handles are sized in SCREEN pixels, divided back out by the zoom,
// so they stay grabbable at every magnification - a handle that shrinks
// with the drawing is unusable the moment you zoom out to see the whole
// room you meant to resize.

import React, { useRef } from 'react';
import { Group, Rect } from 'react-konva';
import type { ScaleBox } from '../../project/GroupScale';
import { anchorCursor, anchorPoint, RESIZE_ANCHORS, resizeBox } from '../../project/GroupScale';
import { COLOR_OUTLINE, COLOR_WHITE, MARQUEE_DASH } from '../../theme/ScadaTheme';

export interface GroupResizeHandlesProps {
  /** The selection's own bounds, unpadded. */
  bounds: ScaleBox;
  zoom: number;
  /** Grid step to snap the dragged edge to, or 0 for no snapping. */
  snapStep: number;
  /** Called on every frame of the drag, with the box as it was when the drag STARTED and the box now. */
  onResize: (before: ScaleBox, after: ScaleBox) => void;
  /** Called once when the drag ends - where the single history entry is written. */
  onCommit: () => void;
}

/** On-screen size of a handle, before the zoom is divided back out. */
const HANDLE_SCREEN_SIZE = 9;

export const GroupResizeHandles: React.FC<GroupResizeHandlesProps> = ({
  bounds, zoom, snapStep, onResize, onCommit,
}) => {
  // The box as it was when this drag began. Every frame maps from THAT
  // box, not from the previous frame's: mapping from the previous frame
  // would compound rounding on every mouse move, so a room dragged out
  // and back would not come back to where it started.
  const beforeRef = useRef<ScaleBox | null>(null);

  const size = HANDLE_SCREEN_SIZE / Math.max(0.05, zoom);
  const half = size / 2;
  const snap = (value: number) => (snapStep > 0 ? Math.round(value / snapStep) * snapStep : value);

  return (
    <Group>
      {/* The outline of what is about to be resized. Dashed, so it is
          never mistaken for a frame that is actually part of the
          drawing. */}
      <Rect
        x={bounds.x}
        y={bounds.y}
        width={bounds.width}
        height={bounds.height}
        stroke={COLOR_OUTLINE}
        strokeWidth={1.25}
        strokeScaleEnabled={false}
        dash={MARQUEE_DASH}
        listening={false}
      />

      {RESIZE_ANCHORS.map(anchor => {
        const point = anchorPoint(bounds, anchor);
        return (
          <Rect
            key={anchor}
            x={point.x - half}
            y={point.y - half}
            width={size}
            height={size}
            fill={COLOR_WHITE}
            stroke={COLOR_OUTLINE}
            strokeWidth={1}
            strokeScaleEnabled={false}
            draggable
            onMouseEnter={e => {
              const stage = e.target.getStage();
              if (stage) stage.container().style.cursor = anchorCursor(anchor);
            }}
            onMouseLeave={e => {
              const stage = e.target.getStage();
              if (stage) stage.container().style.cursor = 'default';
            }}
            onDragStart={e => {
              // Konva moves a dragged node itself; the handle's place is
              // derived from the bounds instead, so the drag must not
              // also bubble up and pan or rubber-band the canvas.
              e.cancelBubble = true;
              beforeRef.current = { ...bounds };
            }}
            onDragMove={e => {
              e.cancelBubble = true;
              const before = beforeRef.current;
              if (!before) return;
              const node = e.target;
              const pointer = { x: snap(node.x() + half), y: snap(node.y() + half) };
              onResize(before, resizeBox(before, anchor, pointer));
            }}
            onDragEnd={e => {
              e.cancelBubble = true;
              beforeRef.current = null;
              onCommit();
              // The handle is placed from the bounds on the next render;
              // leaving Konva's own drag offset on it would put it a few
              // pixels out until something else moved.
              const stage = e.target.getStage();
              if (stage) stage.container().style.cursor = 'default';
            }}
          />
        );
      })}
    </Group>
  );
};
