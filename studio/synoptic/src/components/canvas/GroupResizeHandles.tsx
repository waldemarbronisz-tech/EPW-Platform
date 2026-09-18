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
//
// PRECISION (user, 2026-09-18: "rozciąganie pokoju działa
// nieprecyzyjnie"). The first version let Konva DRAG the handle node and
// read the node's own position as the pointer. Every frame the store
// changed the bounds, React put the handle back at the new anchor, and
// Konva's drag offset then fought that placement - the handle lagged and
// jittered behind the mouse, and the edge never landed exactly where the
// pointer was. Now the handle is not draggable at all: a press starts a
// resize, the POINTER's own position (mapped through the stage's pan and
// zoom, GroupScale.canvasPointFromClient) is what the edge follows, and
// the window sees every move and the release - so the drag also
// survives the pointer leaving the stage.

import React, { useRef } from 'react';
import { Group, Rect } from 'react-konva';
import type { ScaleBox } from '../../project/GroupScale';
import {
  anchorCursor, anchorPoint, canvasPointFromClient, RESIZE_ANCHORS, resizeBox,
} from '../../project/GroupScale';
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
  // The latest callbacks, so the window listeners registered at press
  // time never call a stale render's closures.
  const callbacksRef = useRef({ onResize, onCommit, snapStep });
  callbacksRef.current = { onResize, onCommit, snapStep };

  const size = HANDLE_SCREEN_SIZE / Math.max(0.05, zoom);
  const half = size / 2;

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
            onMouseEnter={e => {
              const stage = e.target.getStage();
              if (stage) stage.container().style.cursor = anchorCursor(anchor);
            }}
            onMouseLeave={e => {
              if (beforeRef.current) return;               // mid-drag: keep the resize cursor
              const stage = e.target.getStage();
              if (stage) stage.container().style.cursor = 'default';
            }}
            onMouseDown={e => {
              if (e.evt.button !== 0) return;
              // The press must not also bubble up and start a marquee or
              // a pan on the stage.
              e.cancelBubble = true;
              e.evt.preventDefault();
              const stage = e.target.getStage();
              if (!stage) return;
              const before = { ...bounds };
              beforeRef.current = before;
              const container = stage.container();
              container.style.cursor = anchorCursor(anchor);

              const move = (ev: MouseEvent) => {
                const rect = container.getBoundingClientRect();
                const step = callbacksRef.current.snapStep;
                const snap = (value: number) => (step > 0 ? Math.round(value / step) * step : value);
                const pointer = canvasPointFromClient(
                  ev.clientX, ev.clientY, rect.left, rect.top, stage.x(), stage.y(), stage.scaleX() || 1,
                );
                callbacksRef.current.onResize(before, resizeBox(before, anchor, { x: snap(pointer.x), y: snap(pointer.y) }));
              };
              const up = () => {
                window.removeEventListener('mousemove', move);
                window.removeEventListener('mouseup', up);
                beforeRef.current = null;
                container.style.cursor = 'default';
                callbacksRef.current.onCommit();
              };
              window.addEventListener('mousemove', move);
              window.addEventListener('mouseup', up);
            }}
          />
        );
      })}
    </Group>
  );
};
