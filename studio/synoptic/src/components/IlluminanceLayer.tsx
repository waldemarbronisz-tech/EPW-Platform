// feat/room-lighting: the false-colour illuminance map and its isolux
// contours - the DIALux view of a room.
//
// Everything drawn here comes from project/Illuminance.ts, which is a
// real photometric calculation (inverse-square and cosine laws over a
// cosine-power distribution), not a glow. The pools of light the floor
// layer draws are decoration and stay decoration; this is the
// measurement, and it is off by default because a plan is not always
// being read as a lighting design.
//
// RASTER, not polygons. The map is built as a tiny offscreen canvas -
// one pixel per grid point - and drawn scaled up. The browser's own
// bilinear filtering then does the interpolation between grid points
// for free, which is both faster and smoother than emitting a few
// thousand Konva rectangles.

import React, { useMemo } from 'react';
import { Group, Image as KonvaImage, Line, Text } from 'react-konva';
import type { WallElement } from '../elements/WallElement';
import type { SynopticObject } from '../store';
import { findClosedRooms } from '../project/RoomFloors';
import {
  computeIlluminanceGrid, contourAt, falseColour, isoluxLevelsFor,
} from '../project/Illuminance';
import type { IlluminanceGrid } from '../project/Illuminance';
import { FONT_UI } from '../theme/ScadaTheme';

export interface IlluminanceLayerProps {
  walls: WallElement[];
  objects: SynopticObject[];
  /** Shared across every room so two rooms on one screen are directly comparable. Null lets each room scale to itself. */
  scaleMax?: number | null;
  showContours?: boolean;
}

/** The raster for one grid, as a canvas element ready for Konva. Null in an environment with no DOM. */
function buildRaster(grid: IlluminanceGrid, max: number): HTMLCanvasElement | null {
  if (typeof document === 'undefined' || max <= 0) return null;
  const canvas = document.createElement('canvas');
  canvas.width = grid.columns;
  canvas.height = grid.rows;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  const image = ctx.createImageData(grid.columns, grid.rows);
  for (let i = 0; i < grid.values.length; i++) {
    const lux = grid.values[i];
    const offset = i * 4;
    if (Number.isNaN(lux)) {
      // Outside the room: fully transparent, so the floor shows through
      // rather than the map bleeding past the walls.
      image.data[offset + 3] = 0;
      continue;
    }
    const [r, g, b] = falseColour(lux / max);
    image.data[offset] = r;
    image.data[offset + 1] = g;
    image.data[offset + 2] = b;
    image.data[offset + 3] = 255;
  }
  ctx.putImageData(image, 0, 0);
  return canvas;
}

const RASTER_OPACITY = 0.82;
const CONTOUR_COLOR = '#FFFFFF';
const CONTOUR_OPACITY = 0.55;
const LABEL_COLOR = '#FFFFFF';

export const IlluminanceLayer: React.FC<IlluminanceLayerProps> = ({
  walls, objects, scaleMax = null, showContours = true,
}) => {
  const rooms = useMemo(() => findClosedRooms(walls), [walls]);

  // The calculation is the expensive part of this component, so it is
  // memoised on exactly what it depends on. Objects change on every
  // drag, but a drag that moves a chair does not change the lighting -
  // that is accepted: recomputing a few hundred grid points is
  // milliseconds, and tracking which objects are luminaires to memoise
  // more finely would be a cache that can go stale.
  const grids = useMemo(
    () => rooms.map(room => ({ room, grid: computeIlluminanceGrid(room, objects) })),
    [rooms, objects]
  );

  if (grids.length === 0) return null;

  const overallMax = scaleMax ?? Math.max(1, ...grids.map(g => g.grid.stats.max));

  return (
    <Group listening={false}>
      {grids.map(({ room, grid }, roomIndex) => {
        const raster = buildRaster(grid, overallMax);
        const levels = showContours ? isoluxLevelsFor(grid.stats.max) : [];

        return (
          <Group
            key={`lux-${roomIndex}`}
            listening={false}
            // Clipped to the room, so the raster's own edge pixels - which
            // are half a grid step wide - never spill onto a wall.
            clipFunc={(ctx: any) => {
              ctx.beginPath();
              ctx.moveTo(room[0].x, room[0].y);
              for (let i = 1; i < room.length; i++) ctx.lineTo(room[i].x, room[i].y);
              ctx.closePath();
            }}
          >
            {raster && (
              <KonvaImage
                image={raster as unknown as HTMLImageElement}
                // Offset by half a step: each raster pixel is CENTRED on
                // its grid point, not starting at it.
                x={grid.originX - grid.step / 2}
                y={grid.originY - grid.step / 2}
                width={grid.columns * grid.step}
                height={grid.rows * grid.step}
                opacity={RASTER_OPACITY}
                listening={false}
              />
            )}

            {levels.map(level => {
              const segments = contourAt(grid, level);
              if (segments.length === 0) return null;
              return (
                <Group key={`iso-${level}`} listening={false}>
                  {segments.map((s, i) => (
                    <Line
                      key={i}
                      points={[s.x1, s.y1, s.x2, s.y2]}
                      stroke={CONTOUR_COLOR}
                      strokeWidth={1}
                      opacity={CONTOUR_OPACITY}
                      listening={false}
                    />
                  ))}
                  {/* One label per contour, on its first segment. Labelling
                      every segment would bury the map in numbers; labelling
                      none would leave the lines meaningless. */}
                  <Text
                    x={segments[0].x1 + 2}
                    y={segments[0].y1 - 12}
                    text={`${level}`}
                    fontSize={10}
                    fontFamily={FONT_UI}
                    fill={LABEL_COLOR}
                    opacity={0.9}
                    listening={false}
                  />
                </Group>
              );
            })}
          </Group>
        );
      })}
    </Group>
  );
};

