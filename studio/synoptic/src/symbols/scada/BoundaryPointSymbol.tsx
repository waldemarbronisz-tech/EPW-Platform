// SCADA-style symbol 10/10: boundary point. Marks where a schematic
// begins or ends - a utility feed (ZKP), a well, a branch-off to a sub
// installation (DOM, WARSZTAT, OGROD). Built on the existing Label
// Frame's look (panel-color rect, black outline, two lines of text),
// with exactly one port and a direction arrow added on top of it.

import React from 'react';
import { Group, Line } from 'react-konva';
import { LabelFrameSymbol, getLabelFrameSize } from './LabelFrameSymbol';
import { COLOR_OUTLINE, COLOR_ENERGIZED, COLOR_WATER, VENTILATION_ACTIVE } from '../../theme/ScadaTheme';

export type BoundaryDirection = 'SOURCE' | 'SINK';
export type BoundaryMedium = 'ELECTRICAL' | 'WATER' | 'VENTILATION';
export type BoundaryPortSide = 'TOP' | 'BOTTOM' | 'LEFT' | 'RIGHT';

// No discrete state machine, same as the label frame it is built on.
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this state list belongs beside its component.
export const BOUNDARY_POINT_STATES: string[] = [];

const MIN_WIDTH = 96;  // per this symbol's own spec
const MAX_WIDTH = 220; // per this symbol's own spec
const ARROW_LENGTH = 14;
const ARROW_HALF_WIDTH = 5;
const ARROW_OUTLINE_WIDTH = 1;

/**
 * Frame width: hugs the longer of the label/sublabel, per
 * getLabelFrameSize (the same text-width estimate the plain Label Frame
 * uses), clamped to [MIN_WIDTH, MAX_WIDTH].
 */
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this helper belongs beside its component.
export function getBoundaryPointWidth(label: string, sublabel: string): number {
  const { width } = getLabelFrameSize(label, sublabel);
  return Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, width));
}

/**
 * Where the single port sits, as a fraction of the frame's own box - the
 * same 0..1 convention every other symbol's connectionPoints use, so
 * this plugs directly into GeometryUtils.getAbsolutePortPosition.
 */
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this helper belongs beside its component.
export function getBoundaryPortFraction(side: BoundaryPortSide): { x: number; y: number } {
  switch (side) {
    case 'TOP': return { x: 0.5, y: 0 };
    case 'BOTTOM': return { x: 0.5, y: 1 };
    case 'LEFT': return { x: 0, y: 0.5 };
    case 'RIGHT': return { x: 1, y: 0.5 };
  }
}

export interface BoundaryPointSymbolProps {
  label: string;
  sublabel: string;
  direction: BoundaryDirection;
  medium: BoundaryMedium;
  portSide: BoundaryPortSide;
}

export const BoundaryPointSymbol: React.FC<BoundaryPointSymbolProps> = ({ label, sublabel, direction, medium, portSide }) => {
  const width = getBoundaryPointWidth(label, sublabel);
  const { height } = getLabelFrameSize(label, sublabel);
  const { x: fx, y: fy } = getBoundaryPortFraction(portSide);
  const portX = fx * width;
  const portY = fy * height;

  // Unit vector pointing outward from the frame at this edge.
  let outX = 0, outY = 0;
  if (portSide === 'TOP') outY = -1;
  else if (portSide === 'BOTTOM') outY = 1;
  else if (portSide === 'LEFT') outX = -1;
  else outX = 1;

  // The point further from the frame, along the port's outward axis.
  const outerX = portX + outX * ARROW_LENGTH;
  const outerY = portY + outY * ARROW_LENGTH;

  // SOURCE: arrow points away from the frame, toward the schematic - its
  // tip is the outer point, base (wide end) sits at the port itself.
  // SINK: arrow points into the frame - tip is at the port, base is the
  // outer point.
  const tipX = direction === 'SOURCE' ? outerX : portX;
  const tipY = direction === 'SOURCE' ? outerY : portY;
  const baseX = direction === 'SOURCE' ? portX : outerX;
  const baseY = direction === 'SOURCE' ? portY : outerY;

  // Perpendicular to the outward axis, for the arrowhead's two back corners.
  const perpX = -outY * ARROW_HALF_WIDTH;
  const perpY = outX * ARROW_HALF_WIDTH;

  const arrowColor = medium === 'WATER' ? COLOR_WATER : medium === 'VENTILATION' ? VENTILATION_ACTIVE : COLOR_ENERGIZED;

  return (
    <Group>
      <LabelFrameSymbol title={label} description={sublabel} width={width} />
      <Line
        points={[tipX, tipY, baseX + perpX, baseY + perpY, baseX - perpX, baseY - perpY]}
        closed
        fill={arrowColor}
        stroke={COLOR_OUTLINE}
        strokeWidth={ARROW_OUTLINE_WIDTH}
      />
    </Group>
  );
};
