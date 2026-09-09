import React from 'react';
import { Group, Rect, Path } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

export const PipeElbowSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isFlow = state === 'FLOW';
  const isFault = state === 'FAULT';
  const color = isFlow ? '#3498db' : '#95a5a6';

  // Assuming an elbow connecting bottom to right.
  // The user can rotate it via obj.rotation.
  const pathData = `M ${w/2} ${h} L ${w/2} ${h/2} L ${w} ${h/2}`;

  return (
    <Group>
      <Path
        data={pathData}
        stroke={color}
        strokeWidth={10}
        lineJoin="round"
        lineCap="square"
      />
      <Path
        data={pathData}
        stroke="#34495e"
        strokeWidth={12}
        lineJoin="round"
        lineCap="square"
        globalCompositeOperation="destination-over"
      />

      {isFault && (
        <Rect width={w} height={h} fill="rgba(255, 0, 0, 0.3)" stroke="red" strokeWidth={2} />
      )}
    </Group>
  );
};
