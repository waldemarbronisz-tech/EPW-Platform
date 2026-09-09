import React from 'react';
import { Group, Rect, Path, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

export const SPDSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isFault = state === 'FAULT';

  return (
    <Group>
      <Rect width={w} height={h} fill="#bdc3c7" stroke="#7f8c8d" strokeWidth={1} cornerRadius={2} />

      {/* Cartridge representation */}
      <Rect x={w*0.1} y={h*0.2} width={w*0.8} height={h*0.6} fill="#ecf0f1" stroke="#95a5a6" strokeWidth={1} />

      {/* Status indicator window */}
      <Rect x={w*0.3} y={h*0.3} width={w*0.4} height={h*0.15} fill={isFault ? "#e74c3c" : "#2ecc71"} stroke="#34495e" strokeWidth={1} />

      {/* MOV symbol inside */}
      <Line points={[w/2, h*0.5, w/2, h*0.65]} stroke="#2c3e50" strokeWidth={1} />
      <Path data={`M ${w*0.3} ${h*0.65} L ${w*0.7} ${h*0.65} L ${w*0.7} ${h*0.75} L ${w*0.3} ${h*0.75} Z`} stroke="#2c3e50" strokeWidth={1} />
      <Line points={[w*0.3, h*0.75, w*0.7, h*0.65]} stroke="#2c3e50" strokeWidth={1} />

      {isFault && (
        <Rect width={w} height={h} fill="transparent" stroke="#e74c3c" strokeWidth={3} cornerRadius={2} />
      )}
    </Group>
  );
};
