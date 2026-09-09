// feat/editing-and-signal-panel commit 3: rubber-band selection
// containment checks. Pure, Konva-free (same convention as GridSnap.ts/
// Terminals.ts/WireDrawing.ts) - an element is selected only if it lies
// ENTIRELY within the box, never on a partial overlap: an element
// poking out past the box's edge is left unselected, on purpose.

export interface Box {
  x: number;
  y: number;
  width: number;
  height: number;
}

export function isObjectFullyInBox(obj: { x: number; y: number; width: number; height: number; scaleX?: number; scaleY?: number }, box: Box): boolean {
  const w = obj.width * (obj.scaleX || 1);
  const h = obj.height * (obj.scaleY || 1);
  return obj.x >= box.x && obj.y >= box.y && obj.x + w <= box.x + box.width && obj.y + h <= box.y + box.height;
}

/** height is the meter's own COMPUTED height (MeterElement.ts's computeMeterHeight) - a meter carries no height field of its own to read here. */
export function isMeterFullyInBox(meter: { x: number; y: number; width: number }, height: number, box: Box): boolean {
  return meter.x >= box.x && meter.y >= box.y && meter.x + meter.width <= box.x + box.width && meter.y + height <= box.y + box.height;
}

export function isConnectionFullyInBox(conn: { points: { x: number; y: number }[] }, box: Box): boolean {
  if (conn.points.length === 0) return false;
  return conn.points.every(p => p.x >= box.x && p.y >= box.y && p.x <= box.x + box.width && p.y <= box.y + box.height);
}

export interface MixedSelection {
  objectIds: string[];
  connectionIds: string[];
  meterIds: string[];
  signalPanelIds: string[];
  frameIds: string[];
  groupCommandIds: string[];
  setpointPanelIds: string[];
}

/**
 * feat/appearance-selection-frames commit 2d: what a Shift+drag rubber-
 * band adds to an existing selection - every id newly found inside the
 * box, unioned into whatever was already selected, per kind,
 * duplicate-free. Extracted out of Canvas.tsx's own handleMouseUp (the
 * same reason every other pure piece of rubber-band logic in this file
 * already lives here, not inline in the component) so this specific
 * "Shift adds instead of replacing" rule is directly testable without
 * a Konva rendering harness.
 */
export function mergeSelectionAdditive(existing: MixedSelection, found: Partial<MixedSelection>): MixedSelection {
  return {
    objectIds: [...new Set([...existing.objectIds, ...(found.objectIds || [])])],
    connectionIds: [...new Set([...existing.connectionIds, ...(found.connectionIds || [])])],
    meterIds: [...new Set([...existing.meterIds, ...(found.meterIds || [])])],
    signalPanelIds: [...new Set([...existing.signalPanelIds, ...(found.signalPanelIds || [])])],
    frameIds: [...new Set([...existing.frameIds, ...(found.frameIds || [])])],
    groupCommandIds: [...new Set([...existing.groupCommandIds, ...(found.groupCommandIds || [])])],
    setpointPanelIds: [...new Set([...existing.setpointPanelIds, ...(found.setpointPanelIds || [])])]
  };
}
