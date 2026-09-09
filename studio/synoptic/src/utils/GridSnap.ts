// Grid-snap logic for symbol/connection placement, kept separate from
// Canvas.tsx (which pulls in react-konva) so it can be unit tested without
// importing anything Konva-related.

import { useStore } from '../store';

/**
 * True when a placement should snap to the grid right now: the
 * persistent View-menu toggle, unless Alt is currently held. Takes
 * altKey explicitly rather than reading tracked key state itself, so it
 * stays a pure function of its inputs - callers pass either the
 * continuously-tracked Alt flag (Canvas.tsx) or, where a native event is
 * directly at hand (e.g. the HTML5 drop event), that event's own altKey.
 */
export function shouldSnapToGrid(altKey: boolean): boolean {
  return useStore.getState().snapToGridEnabled && !altKey;
}

export function snapValue(value: number, gridSize: number, altKey: boolean): number {
  return shouldSnapToGrid(altKey) ? Math.round(value / gridSize) * gridSize : value;
}
