// feat/editing-and-signal-panel commit 4: pan/zoom math, pure and
// Konva-free (same convention as GridSnap.ts/Terminals.ts/
// WireDrawing.ts) - clamping the zoom range and computing the fit-to-
// content view are both plain arithmetic, no Stage needed to get them
// right.

import type { RuntimeViewport } from '../project/RuntimeViewport';
import type { SynopticObject, SynopticConnection } from '../store';
import type { MeterElement } from '../meter/MeterElement';
import { computeMeterHeight } from '../meter/MeterElement';
import type { WallElement } from '../elements/WallElement';
import { drawnWallHeight } from '../elements/WallElement';

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

/**
 * computeContentBounds plus the walls - what "fit the plan" has to fit.
 *
 * A floor plan is mostly walls, and a fit that ignored them zoomed in on
 * the lamps and cut the room in half. Each wall counts with its own
 * thickness and with the height it is DRAWN at, since the foreshortened
 * wall body rises above its footprint on screen (WallElement.ts).
 */
export function computePlanBounds(
  objects: SynopticObject[],
  meters: MeterElement[],
  connections: SynopticConnection[],
  walls: WallElement[]
): Bounds | null {
  let bounds = computeContentBounds(objects, meters, connections);
  for (const wall of walls) {
    const half = (wall.thickness || 0) / 2;
    const lift = drawnWallHeight(wall.height);
    const box = {
      minX: Math.min(wall.from.x, wall.to.x) - half,
      minY: Math.min(wall.from.y, wall.to.y) - half - lift,
      maxX: Math.max(wall.from.x, wall.to.x) + half,
      maxY: Math.max(wall.from.y, wall.to.y) + half,
    };
    bounds = bounds
      ? {
        minX: Math.min(bounds.minX, box.minX),
        minY: Math.min(bounds.minY, box.minY),
        maxX: Math.max(bounds.maxX, box.maxX),
        maxY: Math.max(bounds.maxY, box.maxY),
      }
      : box;
  }
  return bounds;
}

export interface View {
  zoom: number;
  panX: number;
  panY: number;
}

const FIT_PADDING_FRACTION = 0.9; // a little margin around the content, not edge-to-edge

/**
 * The view the PANEL uses for a screen (runtime's screen_widget.view_rect):
 * the runtime frame fitted edge to edge when there is one, else everything
 * drawn with a small margin, else nothing to fit (100%, no pan).
 */
export function computePanelView(
  viewport: RuntimeViewport | undefined,
  planBounds: Bounds | null,
  viewportWidth: number,
  viewportHeight: number,
): View {
  if (viewport) {
    const bounds = { minX: viewport.x, minY: viewport.y, maxX: viewport.x + viewport.width, maxY: viewport.y + viewport.height };
    return computeFitView(bounds, viewportWidth, viewportHeight, 0.99);
  }
  return computeFitView(planBounds, viewportWidth, viewportHeight, 0.92);
}

/** The canvas rectangle a viewport of the given size shows under `view` - what "Runtime frame: what I see now" records, whole pixels. */
export function visibleCanvasRect(view: View, viewportWidth: number, viewportHeight: number): RuntimeViewport {
  const zoom = view.zoom > 0 ? view.zoom : 1;
  const whole = (n: number) => Math.round(n) || 0;   // never -0 in a file
  return {
    x: whole(-view.panX / zoom),
    y: whole(-view.panY / zoom),
    width: Math.max(1, whole(viewportWidth / zoom)),
    height: Math.max(1, whole(viewportHeight / zoom)),
  };
}

/**
 * The zoom/pan that fits `bounds` inside a viewport of the given size,
 * centered, clamped to [MIN_ZOOM, MAX_ZOOM]. Falls back to 100% zoom,
 * no pan, when there is nothing to fit (bounds is null) or the
 * viewport has no usable size yet.
 */
export function computeFitView(bounds: Bounds | null, viewportWidth: number, viewportHeight: number,
                               padding: number = FIT_PADDING_FRACTION): View {
  if (!bounds || viewportWidth <= 0 || viewportHeight <= 0) {
    return { zoom: 1, panX: 0, panY: 0 };
  }

  const contentWidth = Math.max(1, bounds.maxX - bounds.minX);
  const contentHeight = Math.max(1, bounds.maxY - bounds.minY);

  const zoom = clampZoom(Math.min(viewportWidth / contentWidth, viewportHeight / contentHeight) * padding);

  const contentCenterX = (bounds.minX + bounds.maxX) / 2;
  const contentCenterY = (bounds.minY + bounds.maxY) / 2;

  return {
    zoom,
    panX: viewportWidth / 2 - contentCenterX * zoom,
    panY: viewportHeight / 2 - contentCenterY * zoom
  };
}
