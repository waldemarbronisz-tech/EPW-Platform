// Internal-audit fix (Canvas.tsx breakup): moved out of Canvas.tsx
// verbatim, comments included - see ObjectNode.tsx's own header for why.
import React, { useEffect, useRef } from 'react';
import { Circle, Group } from 'react-konva';
import { useStore } from '../../store';
import type { SynopticConnection, WirePoint } from '../../store';
import { ConnectionLine } from '../ConnectionLine';
import type { WireSegmentCollision } from '../ConnectionLine';
import { COLOR_OUTLINE, COLOR_WHITE } from '../../theme/ScadaTheme';
import { snapValue } from '../../utils/GridSnap';
import { snapPointToGrid, reorthogonalizeAfterMove, simplifyCollinearPoints } from '../../utils/WireDrawing';
import { isAltKeyDown } from '../../utils/CanvasInputState';
import type { DragKey, GroupDragApi } from './types';

// A finished wire: draws itself (ConnectionLine), can be dragged whole
// (translating every point, grid-snapped), and - while selected - shows
// a draggable handle at each of its own points so a bend can be grabbed
// and moved without breaking orthogonality (WireDrawing.
// reorthogonalizeAfterMove fixes up its two neighboring segments).
// Alt+click on a segment (not a handle) inserts a brand new bend there.
export const ConnectionNode = ({ conn, netState, isSelected, onSelect, gridSize, onAltClickSegment, groupDrag, collisions, onCollisionHover }: {
  conn: SynopticConnection,
  // feat/water-management commit 2: computed once per Canvas render
  // (resolveNets) and passed straight through to ConnectionLine - see
  // that component's own ConnectionProps comment for why this replaced
  // conn.state as the color source.
  netState: 'ACTIVE' | 'INACTIVE',
  isSelected: boolean,
  onSelect: (multi: boolean) => void,
  gridSize: number,
  onAltClickSegment: (conn: SynopticConnection, worldPoint: WirePoint) => void,
  groupDrag: GroupDragApi,
  // feat/wire-routing-around-obstacles commit 1: see ConnectionLine's
  // own ConnectionProps comment - passed straight through, unchanged.
  collisions?: WireSegmentCollision[],
  onCollisionHover?: (info: { x: number; y: number; label: string } | null) => void,
}) => {
  const moveGroupRef = useRef<any>(null);
  const dragKey: DragKey = `conn:${conn.id}`;

  useEffect(() => {
    groupDrag.registerNode(dragKey, moveGroupRef.current);
  });

  return (
    <React.Fragment>
      <Group
        ref={moveGroupRef}
        draggable={isSelected}
        onDragStart={() => {
          groupDrag.start(dragKey);
        }}
        onDragMove={(e) => {
          const snappedX = snapValue(e.target.x(), gridSize, isAltKeyDown());
          const snappedY = snapValue(e.target.y(), gridSize, isAltKeyDown());
          e.target.x(snappedX);
          e.target.y(snappedY);
          // This move-Group's own x/y already IS a delta from (0,0) -
          // no baseline subtraction needed, unlike an object/meter/
          // panel's absolute position (see GroupDragApi's own comment,
          // in types.ts).
          if (groupDrag.isActive()) {
            groupDrag.follow(snappedX, snappedY);
          }
        }}
        onDragEnd={(e) => {
          const dx = snapValue(e.target.x(), gridSize, isAltKeyDown());
          const dy = snapValue(e.target.y(), gridSize, isAltKeyDown());
          if (groupDrag.isActive()) {
            groupDrag.commit(dx, dy);
          } else if (dx !== 0 || dy !== 0) {
            useStore.getState().updateConnection(conn.id, {
              points: conn.points.map(p => ({ x: p.x + dx, y: p.y + dy }))
            });
            useStore.getState().saveHistory();
          }
          e.target.x(0);
          e.target.y(0);
        }}
      >
        <ConnectionLine
          conn={conn}
          netState={netState}
          isSelected={isSelected}
          collisions={collisions}
          onCollisionHover={onCollisionHover}
          onSelect={(e: any) => {
            if (e?.evt?.altKey) {
              e.cancelBubble = true;
              const stage = e.target.getStage();
              const pos = stage?.getPointerPosition();
              if (!pos) return;
              const { panX, panY, zoom } = useStore.getState().canvasState;
              onAltClickSegment(conn, snapPointToGrid((pos.x - panX) / zoom, (pos.y - panY) / zoom));
              return;
            }
            onSelect(!!e?.evt?.shiftKey);
          }}
        />
      </Group>
      {isSelected && conn.points.map((p, idx) => (
        <Circle
          key={idx}
          x={p.x}
          y={p.y}
          radius={6}
          fill={COLOR_WHITE}
          stroke={COLOR_OUTLINE}
          strokeWidth={1.5}
          draggable
          onDragMove={(e) => {
            e.target.x(snapValue(e.target.x(), gridSize, isAltKeyDown()));
            e.target.y(snapValue(e.target.y(), gridSize, isAltKeyDown()));
          }}
          onDragEnd={(e) => {
            // fix/wiring-and-library-groups commit 2: the identical
            // accumulation this commit fixes for a moved SYMBOL can
            // just as well happen here - a human dragging the same bend
            // point back and forth by hand, repeatedly, through this
            // exact path. Same general-purpose cleanup, same reasoning
            // (WireDrawing.ts's own comment on simplifyCollinearPoints).
            const moved = reorthogonalizeAfterMove(conn.points, idx, { x: e.target.x(), y: e.target.y() });
            const newPoints = simplifyCollinearPoints(moved);
            useStore.getState().updateConnection(conn.id, { points: newPoints });
            useStore.getState().saveHistory();
          }}
        />
      ))}
    </React.Fragment>
  );
};
