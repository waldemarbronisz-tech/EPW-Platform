import React from 'react';
import { Group, Path, Line } from 'react-konva';
import type { SynopticConnection } from '../store';
import {
  COLOR_DE_ENERGIZED, COLOR_ENERGIZED, COLOR_WATER, COLOR_WATER_INACTIVE,
  VENTILATION_ACTIVE, VENTILATION_INACTIVE,
  CONDUCTOR_WIDTH, COLOR_OUTLINE, BUSBAR_HEIGHT,
  COLOR_ALARM, WIRE_COLLISION_MARK_WIDTH, WIRE_COLLISION_MARK_DASH
} from '../theme/ScadaTheme';

// feat/wire-routing-around-obstacles commit 1: which of this wire's own
// segments (by index into conn.points) currently cross an obstacle, and
// that obstacle's own human-readable label - for the dashed alarm-color
// marking drawn ON TOP of the wire (never replacing its own state
// color) and the hover tooltip naming what it crosses.
export interface WireSegmentCollision {
  segmentIndex: number;
  obstacleLabel: string;
}

export interface ConnectionProps {
  conn: SynopticConnection;
  // feat/water-management commit 2: a wire's own state is no longer a
  // manual per-connection setting (Properties dropped that field
  // entirely) - it is now the RESULT of whether its net touches an
  // active source, computed once per Canvas render (resolveNets) and
  // passed down here, same as junctionPoints already is. conn.state
  // itself still exists in the data (optional, for a file saved before
  // this commit), but is never read for drawing any more.
  netState: 'ACTIVE' | 'INACTIVE';
  isSelected: boolean;
  // Receives the raw Konva event so a caller can tell an Alt+click
  // (insert a bend on this segment, per usterka B) apart from a plain
  // click (select).
  onSelect: (e?: any) => void;
  // Empty/undefined for the overwhelming majority of wires (no
  // collision at all) - a plain array, not a Set, since it is always
  // small and only ever iterated, never looked up by index.
  collisions?: WireSegmentCollision[];
  // Fires with a canvas-space anchor point and the obstacle's label on
  // hover-in, and with null on hover-out - Canvas.tsx owns the actual
  // tooltip element (a single one for the whole canvas, not one per
  // wire).
  onCollisionHover?: (info: { x: number; y: number; label: string } | null) => void;
}

/**
 * Node-based wiring: a connection is drawn straight through its own
 * points array - no port lookup, no object references at all. This is
 * the entire router now (the freehand drawing tool in Canvas.tsx is
 * what enforces every segment being horizontal or vertical, at the
 * moment a point is added - there is nothing left to compute here).
 */
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to; Canvas.tsx reuses it for the in-progress drawing preview.
export function pathFromPoints(points: { x: number; y: number }[]): string {
  if (points.length === 0) return '';
  return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
}

/**
 * Color carries medium and net state, and nothing else - every medium
 * now has its own ACTIVE/INACTIVE pair (feat/water-management commit
 * 2 gave water the split it never had before; it used to always read
 * as plain COLOR_WATER regardless of state).
 */
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to; testable in isolation without a Konva/Stage tree.
export function getConductorCoreColor(medium: SynopticConnection['medium'], netState: 'ACTIVE' | 'INACTIVE'): string {
  if (medium === 'WATER') return netState === 'ACTIVE' ? COLOR_WATER : COLOR_WATER_INACTIVE;
  if (medium === 'VENTILATION') return netState === 'ACTIVE' ? VENTILATION_ACTIVE : VENTILATION_INACTIVE;
  return netState === 'ACTIVE' ? COLOR_ENERGIZED : COLOR_DE_ENERGIZED;
}

export const ConnectionLine: React.FC<ConnectionProps> = ({ conn, netState, isSelected, onSelect, collisions, onCollisionHover }) => {
  if (!conn.points || conn.points.length < 2) return null;

  const path = pathFromPoints(conn.points);
  const coreColor = getConductorCoreColor(conn.medium, netState);

  // A busbar/manifold is just a much thicker wire (style BUS) - not a
  // symbol any more. Touchable anywhere along its length because
  // NetResolver treats any point ON its segment, not just its two ends,
  // as touching it.
  const coreWidth = conn.style === 'BUS' ? BUSBAR_HEIGHT : CONDUCTOR_WIDTH;

  return (
    <Group onClick={onSelect} onTap={onSelect}>
      {/* Invisible hit area for easier selection */}
      <Path data={path} stroke="transparent" strokeWidth={coreWidth + 10} />

      {/* One solid line per wire, in the colour of its medium and state
          (user request: connections must merge into one line). The old
          four-pass "pipe" - dark outline, shadow, highlight - drew a
          border round every wire, so two wires meeting at a tee or a
          busbar showed their separate rounded ends instead of joining.
          Same colour + round caps and joins = wires that touch read as
          one conductor. A selected wire gets a soft halo underneath
          rather than a border of its own. */}
      {isSelected && (
        <Path data={path} stroke={COLOR_OUTLINE} strokeWidth={coreWidth + 8} opacity={0.3} lineCap="round" lineJoin="round" listening={false} />
      )}
      <Path data={path} stroke={coreColor} strokeWidth={coreWidth} lineCap="round" lineJoin="round" />
      {/* feat/wire-routing-around-obstacles commit 1: a colliding
          segment's own dashed alarm-color marking, drawn on top of
          everything above - ADDED to the wire's own state color, never
          replacing it (GRANICE: a collision is a warning, the wire
          still works and still shows its real state). A Konva Line,
          not a Path: pipe-rendering-houston.test.ts counts this file's
          Path elements. */}
      {(collisions || []).map((c, i) => {
        const a = conn.points[c.segmentIndex];
        const b = conn.points[c.segmentIndex + 1];
        if (!a || !b) return null;
        const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
        return (
          <Line
            key={i}
            points={[a.x, a.y, b.x, b.y]}
            stroke={COLOR_ALARM}
            strokeWidth={WIRE_COLLISION_MARK_WIDTH}
            dash={WIRE_COLLISION_MARK_DASH}
            onMouseEnter={() => onCollisionHover?.({ x: mid.x, y: mid.y, label: c.obstacleLabel })}
            onMouseLeave={() => onCollisionHover?.(null)}
          />
        );
      })}
    </Group>
  );
};
