import React from 'react';
import { Group, Rect, Circle } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

export const TransformerSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isEnergized = state === 'ENERGIZED';
  const isFault = state === 'FAULT';

  const strokeColor = isEnergized ? 'green' : '#000';
  const strokeWidth = isEnergized ? 2 : 1;

  return (
    <Group>
      <Rect width={w} height={h} fill="transparent" />

      {/* Primary Coil */}
      <Circle
        x={w/2}
        y={h*0.35}
        radius={h*0.25}
        fill="transparent"
        stroke={strokeColor}
        strokeWidth={strokeWidth}
      />
      {/* Secondary Coil */}
      <Circle
        x={w/2}
        y={h*0.65}
        radius={h*0.25}
        fill="transparent"
        stroke={strokeColor}
        strokeWidth={strokeWidth}
      />

      {isFault && (
        <Rect width={w} height={h} fill="rgba(255, 0, 0, 0.3)" stroke="red" strokeWidth={2} />
      )}
    </Group>
  );
};
