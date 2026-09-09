// SCADA-style symbol 3/9: wire node (a branch/tap point on a conductor
// run). No states, no parameters.

import React from 'react';
import { Circle } from 'react-konva';
import { COLOR_OUTLINE } from '../../theme/ScadaTheme';

// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this constant belongs beside its component.
export const WIRE_NODE_STATES: string[] = [];

export const WireNodeSymbol: React.FC = () => (
  <Circle x={75} y={75} radius={8} fill={COLOR_OUTLINE} />
);
