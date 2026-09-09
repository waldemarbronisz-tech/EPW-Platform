import React from 'react';
import { Group, Rect, Circle } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

export const TerminalSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isFault = state === 'FAULT';

  return (
    <Group>
      <Rect width={w} height={h} fill="#ecf0f1" stroke="#2c3e50" strokeWidth={1} />
      <Circle x={w/2} y={h/2} radius={w*0.25} fill="#7f8c8d" />
      <Circle x={w/2} y={h/2} radius={w*0.1} fill="#2c3e50" />

      {isFault && (
        <Rect width={w} height={h} fill="rgba(255, 0, 0, 0.5)" stroke="red" strokeWidth={2} />
      )}
    </Group>
  );
};
