// fix/wiring-and-library-groups commit 1 - usterka 1: "zaciski znikaja
// przy probie ich kliknieca". Pure, Konva-free geometry (safe under
// Vitest, same convention every other utils/*.ts file already follows)
// behind three things this fix needs: a padded hover hit-rect so a
// terminal dot poking past a symbol's own edge stays reachable (a/b/c
// of this commit's own spec), which terminals count as "nearby" while
// a wire is being drawn (d), and which single terminal the cursor/
// magnetism would actually hit right now (e/f).

import type { SynopticObject, WirePoint } from '../store';
import { getAllWorldTerminals, type WorldTerminal } from './Terminals';
import { snapPointToGrid } from './WireDrawing';
import { TERMINAL_HOVER_MARGIN, WIRE_NEARBY_TERMINAL_RADIUS, WIRE_TERMINAL_SNAP_DISTANCE } from '../theme/ScadaTheme';

export interface HoverHitRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * A symbol's own hover hit-rect, in its own LOCAL coordinates (the same
 * space its terminals' x/y already live in - see Terminals.ts's
 * getObjectTerminals) - padded by `margin` on every side so a terminal
 * sitting on the symbol's own edge (always true - see
 * getTerminalOffsetForSide) stays inside it with real room to spare,
 * not flush against it. Defaults to TERMINAL_HOVER_MARGIN (ScadaTheme),
 * which this task's own spec derives as "at least three times the
 * terminal dot's own radius".
 */
export function getHoverHitRect(width: number, height: number, margin: number = TERMINAL_HOVER_MARGIN): HoverHitRect {
  return { x: -margin, y: -margin, width: width + margin * 2, height: height + margin * 2 };
}

/** Euclidean distance between two world points. */
function distance(a: { x: number; y: number }, b: { x: number; y: number }): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

/**
 * Every terminal (of any object) within `radius` world units of
 * `cursor` - what usterka 1d asks for: while the wire tool is armed,
 * every nearby symbol's terminals stay visible without the cursor
 * having to individually hover each one first. Defaults to
 * WIRE_NEARBY_TERMINAL_RADIUS (four grid cells, this task's own spec).
 */
export function getNearbyTerminals(objects: SynopticObject[], cursor: { x: number; y: number }, radius: number = WIRE_NEARBY_TERMINAL_RADIUS): WorldTerminal[] {
  return getAllWorldTerminals(objects).filter(t => distance(t, cursor) <= radius);
}

/**
 * The single closest terminal to `cursor`, but only when it is closer
 * than `maxDistance` - null otherwise (never "the nearest regardless of
 * how far away it is"). Used for two things together, deliberately the
 * same function for both: which terminal to draw highlighted (usterka
 * 1e - bigger radius, different color, "the user should know which one
 * they will hit"), and which terminal a wire endpoint actually snaps to
 * (usterka 1f) - the same "which one would clicking now hit" question,
 * asked once. Defaults to WIRE_TERMINAL_SNAP_DISTANCE (half a grid
 * cell, this task's own spec) - strictly less than, per that spec's own
 * wording ("mniejsza niz polowa oczka siatki").
 */
export function findNearestTerminal(objects: SynopticObject[], cursor: { x: number; y: number }, maxDistance: number = WIRE_TERMINAL_SNAP_DISTANCE, requiredMedium?: WorldTerminal['medium']): WorldTerminal | null {
  let best: WorldTerminal | null = null;
  let bestDist = Infinity;
  for (const t of getAllWorldTerminals(objects)) {
    // feat/tank-language-and-media commit 1: excludes every terminal of
    // a different medium from this search entirely - while a wire is
    // being drawn, a terminal of another medium never highlights and
    // never attracts the live preview/magnetism (usterka a).
    if (requiredMedium && t.medium !== requiredMedium) continue;
    const d = distance(t, cursor);
    if (d < maxDistance && d < bestDist) {
      bestDist = d;
      best = t;
    }
  }
  return best;
}

/**
 * usterka 1f, the actual endpoint a wire lands on: a raw (un-snapped)
 * world position closer than WIRE_TERMINAL_SNAP_DISTANCE to a terminal
 * lands EXACTLY on that terminal's own coordinate; otherwise falls back
 * to the plain nearest grid node, same as before this fix. One function
 * for both Canvas.tsx's own point placement (finishDrawing's click, the
 * live preview) and this file's own tests - not two copies of the same
 * rule.
 */
export function snapToTerminalOrGrid(worldX: number, worldY: number, objects: SynopticObject[], drawnMedium?: WorldTerminal['medium']): WirePoint {
  // feat/tank-language-and-media commit 1: `drawnMedium`, passed only
  // while the wire tool is actually armed, makes this magnetism
  // medium-aware - see findNearestTerminal's own comment above. A
  // terminal of a different medium still sits on a grid node like any
  // other, so a precise-enough click can still land exactly on it
  // (falling through to the plain grid-snap below); it simply never
  // gets pulled toward one the way a same-medium terminal does.
  const nearest = findNearestTerminal(objects, { x: worldX, y: worldY }, WIRE_TERMINAL_SNAP_DISTANCE, drawnMedium);
  if (nearest) return { x: nearest.x, y: nearest.y };
  return snapPointToGrid(worldX, worldY);
}
