// The medium icons for the wire-drawing selector - electricity and water -
// drawn as the same 16 x 16 pixel pictograms the Studio shell's own
// toolbar uses (studio/shell/icons/generate_icons.py, icon_medium_*).
//
// They replace generic line icons (a thin lightning outline and a
// droplet) that read as "some app" rather than as this platform: the
// user asked for the classic tiles - a red bolt on a raised tile for
// power, a tap with a falling drop for water - and the two toolbars
// sitting one above the other must not show two different pictures of
// the same medium.
//
// Pixel-for-pixel copies of the shell PNGs, kept as rectangles in SVG
// with crispEdges so they stay sharp at any display scaling instead of
// being smeared by image resampling.

import React from 'react';

type Px = [x: number, y: number, w: number, h: number, fill: string];

const WHITE = '#FFFFFF';
const GREY_LIGHT = '#C0C0C0';
const GREY_DARK = '#808080';
const BLACK = '#000000';

/** The raised tile both icons sit on: light face, white top-left edge, dark bottom-right edge. */
function tile(face: string): Px[] {
  return [
    [0, 0, 16, 16, face],
    [0, 0, 16, 1, WHITE],
    [0, 0, 1, 16, WHITE],
    [0, 15, 16, 1, GREY_DARK],
    [15, 0, 1, 16, GREY_DARK],
  ];
}

const ELECTRICAL: Px[] = [
  ...tile('#DEB0B0'),
  // The bolt: a zig-zag from top right to bottom left, red with a dark
  // red rim so it holds its shape on the pink tile.
  [9, 2, 3, 1, '#700000'],
  [8, 3, 3, 1, '#E00000'], [11, 3, 1, 1, '#700000'], [7, 3, 1, 1, '#700000'],
  [7, 4, 3, 1, '#E00000'], [10, 4, 1, 1, '#700000'], [6, 4, 1, 1, '#700000'],
  [6, 5, 3, 1, '#E00000'], [9, 5, 1, 1, '#700000'], [5, 5, 1, 1, '#700000'],
  [5, 6, 6, 1, '#E00000'], [4, 6, 1, 1, '#700000'], [11, 6, 1, 1, '#700000'],
  [4, 7, 6, 1, '#E00000'], [10, 7, 1, 1, '#700000'], [3, 7, 1, 1, '#700000'],
  [7, 8, 2, 1, '#E00000'], [6, 8, 1, 1, '#700000'], [9, 8, 1, 1, '#700000'], [3, 8, 3, 1, '#700000'],
  [6, 9, 2, 1, '#E00000'], [5, 9, 1, 1, '#700000'], [8, 9, 1, 1, '#700000'],
  [5, 10, 2, 1, '#E00000'], [4, 10, 1, 1, '#700000'], [7, 10, 1, 1, '#700000'],
  [4, 11, 2, 1, '#E00000'], [3, 11, 1, 1, '#700000'], [6, 11, 1, 1, '#700000'],
  [3, 12, 2, 1, '#E00000'], [5, 12, 1, 1, '#700000'], [2, 12, 1, 1, '#700000'],
  [2, 13, 2, 1, '#700000'],
];

const WATER: Px[] = [
  ...tile(GREY_LIGHT),
  // Tap handle and stem.
  [9, 2, 5, 1, BLACK],
  [11, 3, 1, 1, BLACK],
  // Tap body, outlined.
  [7, 4, 7, 1, BLACK], [7, 7, 7, 1, BLACK], [7, 4, 1, 4, BLACK], [13, 4, 1, 4, BLACK],
  [8, 5, 5, 2, GREY_DARK],
  // Spout, running left then down.
  [3, 5, 4, 1, BLACK], [3, 5, 1, 5, BLACK], [5, 7, 2, 1, BLACK], [5, 7, 1, 3, BLACK],
  [4, 6, 3, 1, GREY_DARK], [4, 7, 1, 2, GREY_DARK],
  [3, 9, 3, 1, BLACK],
  // The falling drop.
  [4, 10, 1, 2, '#2858E0'],
  [3, 12, 3, 2, '#2858E0'],
  [3, 14, 3, 1, '#1838A0'],
  [3, 12, 1, 1, '#A0C0FF'],
];

function PixelIcon({ pixels, size = 16, title }: { pixels: Px[]; size?: number; title?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" shapeRendering="crispEdges" aria-hidden={title ? undefined : true}>
      {title && <title>{title}</title>}
      {pixels.map(([x, y, w, h, fill], i) => (
        <rect key={i} x={x} y={y} width={w} height={h} fill={fill} />
      ))}
    </svg>
  );
}

export const ElectricalPixelIcon: React.FC<{ size?: number }> = ({ size }) => <PixelIcon pixels={ELECTRICAL} size={size} />;
export const WaterPixelIcon: React.FC<{ size?: number }> = ({ size }) => <PixelIcon pixels={WATER} size={size} />;
