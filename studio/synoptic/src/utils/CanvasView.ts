// feat/editing-and-signal-panel commit 4: pan/zoom math, pure and
// Konva-free (same convention as GridSnap.ts/Terminals.ts/
// WireDrawing.ts) - clamping the zoom range and computing the fit-to-
// content view are both plain arithmetic, no Stage needed to get them
// right.

import type { SynopticObject, SynopticConnection } from '../store';
import type { MeterElement } from '../meter/MeterElement';
import { computeMeterHeight } from '../meter/MeterElement';

export const MIN_ZOOM = 0.25;
export const MAX_ZOOM = 4;

// Below this zoom, the grid draws only its major lines (every 4th one)
// - at 1px apart on screen, every minor line at full density blurs
// into a solid gray plane rather than reading as a grid at all.
export const GRID_THIN_BELOW_ZOOM = 0.5;

export function clampZoom(zoom: number): number {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom));
}

export interface Bounds {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
}

/** The combined bounding box of every object, meter and connection - null when there is nothing to bound at all. */
export function computeContentBounds(objects: SynopticObject[], meters: MeterElement[], connections: SynopticConnection[]): Bounds | null {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  let found = false;

  objects.forEach(obj => {
    const w = obj.width * (obj.scaleX || 1);
    const h = obj.height * (obj.scaleY || 1);
    minX = Math.min(minX, obj.x); minY = Math.min(minY, obj.y);
    maxX = Math.max(maxX, obj.x + w); maxY = Math.max(maxY, obj.y + h);
    found = true;
  });

  meters.forEach(meter => {
    const h = computeMeterHeight(meter);
    minX = Math.min(minX, meter.x); minY = Math.min(minY, meter.y);
    maxX = Math.max(maxX, meter.x + meter.width); maxY = Math.max(maxY, meter.y + h);
    found = true;
  });

  connections.forEach(conn => {
    conn.points.forEach(p => {
      minX = Math.min(minX, p.x); minY = Math.min(minY, p.y);
      maxX = Math.max(maxX, p.x); maxY = Math.max(maxY, p.y);
      found = true;
    });
  });

  return found ? { minX, minY, maxX, maxY } : null;
}

export interface View {
  zoom: number;
  panX: number;
  panY: number;
}

const FIT_PADDING_FRACTION = 0.9; // a little margin around the content, not edge-to-edge

/**
 * The zoom/pan that fits `bounds` inside a viewport of the given size,
 * centered, clamped to [MIN_ZOOM, MAX_ZOOM]. Falls back to 100% zoom,
 * no pan, when there is nothing to fit (bounds is null) or the
 * viewport has no usable size yet.
 */
export function computeFitView(bounds: Bounds | null, viewportWidth: number, viewportHeight: number): View {
  if (!bounds || viewportWidth <= 0 || viewportHeight <= 0) {
    return { zoom: 1, panX: 0, panY: 0 };
  }

  const contentWidth = Math.max(1, bounds.maxX - bounds.minX);
  const contentHeight = Math.max(1, bounds.maxY - bounds.minY);

  const zoom = clampZoom(Math.min(viewportWidth / contentWidth, viewportHeight / contentHeight) * FIT_PADDING_FRACTION);

  const contentCenterX = (bounds.minX + bounds.maxX) / 2;
  const contentCenterY = (bounds.minY + bounds.maxY) / 2;

  return {
    zoom,
    panX: viewportWidth / 2 - contentCenterX * zoom,
    panY: viewportHeight / 2 - contentCenterY * zoom
  };
}
