import React from 'react';
import { Group, Path, Line } from 'react-konva';
import type { SynopticConnection } from '../store';
import {
  COLOR_DE_ENERGIZED, COLOR_DE_ENERGIZED_LIGHT, COLOR_DE_ENERGIZED_DARK,
  COLOR_ENERGIZED, COLOR_ENERGIZED_LIGHT, COLOR_ENERGIZED_DARK,
  COLOR_WATER, COLOR_WATER_LIGHT, COLOR_WATER_DARK,
  COLOR_WATER_INACTIVE, COLOR_WATER_INACTIVE_LIGHT, COLOR_WATER_INACTIVE_DARK,
  VENTILATION_ACTIVE, VENTILATION_ACTIVE_LIGHT, VENTILATION_ACTIVE_DARK,
  VENTILATION_INACTIVE, VENTILATION_INACTIVE_LIGHT, VENTILATION_INACTIVE_DARK,
  CONDUCTOR_OUTLINE, CONDUCTOR_WIDTH,
  CONDUCTOR_HIGHLIGHT_WIDTH, CONDUCTOR_HIGHLIGHT_OFFSET_X, CONDUCTOR_HIGHLIGHT_OFFSET_Y,
  CONDUCTOR_SHADOW_WIDTH, CONDUCTOR_SHADOW_OFFSET_X, CONDUCTOR_SHADOW_OFFSET_Y, CONDUCTOR_SHADOW_OPACITY,
  COLOR_OUTLINE, COLOR_WHITE, BUSBAR_HEIGHT,
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

/**
 * The light/dark companions of the core color above, for the Houston-
 * style highlight/shadow passes below - see ScadaTheme.ts's own
 * comment on each pair for exactly where it came from.
 */
function getConductorShadeColors(medium: SynopticConnection['medium'], netState: 'ACTIVE' | 'INACTIVE'): { light: string; dark: string } {
  if (medium === 'WATER') {
    return netState === 'ACTIVE'
      ? { light: COLOR_WATER_LIGHT, dark: COLOR_WATER_DARK }
      : { light: COLOR_WATER_INACTIVE_LIGHT, dark: COLOR_WATER_INACTIVE_DARK };
  }
  if (medium === 'VENTILATION') {
    return netState === 'ACTIVE'
      ? { light: VENTILATION_ACTIVE_LIGHT, dark: VENTILATION_ACTIVE_DARK }
      : { light: VENTILATION_INACTIVE_LIGHT, dark: VENTILATION_INACTIVE_DARK };
  }
  return netState === 'ACTIVE'
    ? { light: COLOR_ENERGIZED_LIGHT, dark: COLOR_ENERGIZED_DARK }
    : { light: COLOR_DE_ENERGIZED_LIGHT, dark: COLOR_DE_ENERGIZED_DARK };
}

export const ConnectionLine: React.FC<ConnectionProps> = ({ conn, netState, isSelected, onSelect, collisions, onCollisionHover }) => {
  if (!conn.points || conn.points.length < 2) return null;

  const path = pathFromPoints(conn.points);
  const coreColor = getConductorCoreColor(conn.medium, netState);
  const { light: highlightColor, dark: shadowColor } = getConductorShadeColors(conn.medium, netState);

  // A busbar/manifold is just a much thicker wire (style BUS) - not a
  // symbol any more. Touchable anywhere along its length because
  // NetResolver treats any point ON its segment, not just its two ends,
  // as touching it.
  const coreWidth = conn.style === 'BUS' ? BUSBAR_HEIGHT : CONDUCTOR_WIDTH;
  const outlineWidth = coreWidth + CONDUCTOR_OUTLINE;

  return (
    <Group onClick={onSelect} onTap={onSelect}>
      {/* Invisible hit area for easier selection */}
      <Path data={path} stroke="transparent" strokeWidth={outlineWidth + 10} />

      {/* Houston-style four-pass pipe (feat/water-management commit 3,
          docs/EPW_gospodarka_wodna_referencja.py's own pipe_seg): outline,
          fill, shadow, highlight, all on ONE path per pass - lineCap/
          lineJoin "round" (not the old "butt"/"miter") is what makes a
          bend draw its own rounded elbow with no separate symbol
          needed, for every medium, not only water. Selection still
          reads as a white outline instead of the usual black one - a
          geometric/palette-only cue, not an invented color. */}
      <Path data={path} stroke={isSelected ? COLOR_WHITE : COLOR_OUTLINE} strokeWidth={outlineWidth} lineCap="round" lineJoin="round" />
      <Path data={path} stroke={coreColor} strokeWidth={coreWidth} lineCap="round" lineJoin="round" />
      {/* Shadow: offset down-right, narrow, semi-transparent - drawn
          BEFORE the highlight so the highlight (fully opaque) always
          reads on top at a corner where the two might otherwise overlap. */}
      <Path
        data={path} stroke={shadowColor} strokeWidth={CONDUCTOR_SHADOW_WIDTH}
        lineCap="round" lineJoin="round" opacity={CONDUCTOR_SHADOW_OPACITY}
        x={CONDUCTOR_SHADOW_OFFSET_X} y={CONDUCTOR_SHADOW_OFFSET_Y}
        listening={false}
      />
      {/* Highlight: offset up-left, narrow, fully opaque. */}
      <Path
        data={path} stroke={highlightColor} strokeWidth={CONDUCTOR_HIGHLIGHT_WIDTH}
        lineCap="round" lineJoin="round"
        x={CONDUCTOR_HIGHLIGHT_OFFSET_X} y={CONDUCTOR_HIGHLIGHT_OFFSET_Y}
        listening={false}
      />
      {/* feat/wire-routing-around-obstacles commit 1: a colliding
          segment's own dashed alarm-color marking, drawn on top of
          everything above - ADDED to the wire's own state color, never
          replacing it (GRANICE: a collision is a warning, the wire
          still works and still shows its real state). A Konva Line,
          deliberately not a fifth Path element - pipe-rendering-
          houston.test.ts's own source scan counts the Path elements
          this file uses (one hit-area pass plus the four real Houston
          passes above) and their round caps/joins; this marking is
          neither of those four passes and must not be counted as one. */}
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
