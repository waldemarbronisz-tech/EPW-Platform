import React from 'react';
import { Group, Rect, Path, Line, Circle } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

export const RelaySymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isOn = state === 'ON';
  const isFault = state === 'FAULT';

  return (
    <Group>
      {/* 3D Base Box */}
      <Rect width={w} height={h} fill="#bdc3c7" stroke="#7f8c8d" strokeWidth={1} />
      <Path data={`M 0 0 L ${w} 0 L ${w-2} 2 L 2 2 Z`} fill="#ecf0f1" />
      <Path data={`M 0 0 L 2 2 L 2 ${h-2} L 0 ${h} Z`} fill="#ecf0f1" />
      <Path data={`M ${w} ${h} L 0 ${h} L 2 ${h-2} L ${w-2} ${h-2} Z`} fill="#95a5a6" />
      <Path data={`M ${w} ${h} L ${w-2} ${h-2} L ${w-2} 2 L ${w} 0 Z`} fill="#95a5a6" />

      <Circle x={w/2} y={h*0.2} radius={2} fill="#2c3e50" />
      <Circle x={w/2} y={h*0.8} radius={2} fill="#2c3e50" />

      {/* Switch element */}
      {isOn ? (
        <Line points={[w/2, h*0.2, w/2, h*0.8]} stroke="#27ae60" strokeWidth={2} />
      ) : (
        <Line points={[w/2, h*0.8, w*0.8, h*0.4]} stroke="#2c3e50" strokeWidth={2} />
      )}

      {/* Coil symbol rect */}
      <Rect x={w*0.1} y={h*0.7} width={w*0.2} height={h*0.2} stroke="#2c3e50" strokeWidth={1} />
      <Line points={[w*0.1, h*0.7, w*0.3, h*0.9]} stroke="#2c3e50" strokeWidth={1} />

      {isFault && (
        <Rect width={w} height={h} fill="transparent" stroke="#e74c3c" strokeWidth={2} />
      )}
    </Group>
  );
};
