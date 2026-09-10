// feat/site-objects-2d commit 4 - "14. Trawa/Grass" from docs/EPW_
// rysunki_referencja.py's own trawa(on). States ON (green,
// SITE_GRASS) / OFF (yellowed, SITE_GRASS_DIM). A SURFACE, not a
// fixed-size icon like the other 15 TEREN objects - see this file's own
// sibling SurfaceGeometry.ts for the full reasoning on why a surface
// does NOT use SITE_CANVAS_SCALE the way every other site/ component
// does, and why this component reads the object's REAL on-canvas size
// rather than a fixed reference coordinate space.
//
// The inverse-scale Group below is the one piece of that reasoning
// that lives here rather than in SurfaceGeometry.ts: ObjectNode.tsx's
// own generic resize-by-handle mechanism (shared by every symbol in
// this app) changes obj.scaleX/obj.scaleY on the OUTER Group it wraps
// every symbol in - never obj.width/obj.height. Multiplying the two
// back out (obj.width*scaleX) recovers the real size to draw the
// texture for; dividing back out by that same scale here cancels the
// outer Group's own scale exactly, so what finally reaches the screen
// is this component's own undistorted, real-pixel-unit drawing - not
// that drawing stretched a second time on top of itself.

import React from 'react';
import { Group, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedRect } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import { computeGrassDashes } from './SurfaceGeometry';
import { SITE_GRASS, SITE_GRASS_DIM, SITE_BAND_WIDTH_WIDE, SITE_TEXTURE_LINE_WIDTH } from '../../theme/ScadaTheme';

export type GrassState = 'ON' | 'OFF';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as scada/ symbols.
export const GRASS_STATES: GrassState[] = ['ON', 'OFF'];

export const GrassSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const on = resolveSiteState(state, GRASS_STATES, 'OFF') === 'ON';
  const triad = on ? SITE_GRASS : SITE_GRASS_DIM;

  const scaleX = obj.scaleX || 1;
  const scaleY = obj.scaleY || 1;
  const realWidth = obj.width * scaleX;
  const realHeight = obj.height * scaleY;
  const dashes = computeGrassDashes(realWidth, realHeight);

  return (
    <Group scaleX={1 / scaleX} scaleY={1 / scaleY}>
      {bandedRect(0, 0, realWidth, realHeight, triad, { band: SITE_BAND_WIDTH_WIDE })}
      {/* Each dash is a small two-tone blade-of-grass mark, docs/EPW_
          rysunki_referencja.py's own trawa(on) pair of short lines per
          spot (light one leaning left, dark one leaning right) - a
          fixed mark size regardless of the surface's own overall size,
          same as a real texture tiling more densely, not stretching. */}
      {dashes.map((d, i) => (
        <Group key={i} listening={false}>
          <Line points={[d.x, d.y, d.x - 2, d.y - 7]} stroke={triad.light} strokeWidth={SITE_TEXTURE_LINE_WIDTH} lineCap="round" />
          <Line points={[d.x + 3, d.y, d.x + 4, d.y - 6]} stroke={triad.dark} strokeWidth={SITE_TEXTURE_LINE_WIDTH} lineCap="round" />
        </Group>
      ))}
    </Group>
  );
};
