import React from 'react';
import { Group, Rect, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

export const FuseSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isBlown = state === 'BLOWN';

  return (
    <Group>
      <Rect width={w} height={h} fill="transparent" />

      {/* Terminals */}
      <Line points={[w/2, 0, w/2, h*0.2]} stroke="#2c3e50" strokeWidth={2} />
      <Line points={[w/2, h, w/2, h*0.8]} stroke="#2c3e50" strokeWidth={2} />

      {/* Fuse Box */}
      <Rect x={w*0.2} y={h*0.2} width={w*0.6} height={h*0.6} fill="#ecf0f1" stroke="#2c3e50" strokeWidth={1} />

      {/* Internal fuse wire */}
      {isBlown ? (
        <Group>
           <Line points={[w/2, h*0.2, w/2, h*0.4]} stroke="#e74c3c" strokeWidth={2} />
           <Line points={[w/2, h*0.8, w/2, h*0.6]} stroke="#e74c3c" strokeWidth={2} />
        </Group>
      ) : (
        <Line points={[w/2, h*0.2, w/2, h*0.8]} stroke="#2c3e50" strokeWidth={2} />
      )}
    </Group>
  );
};
