import React from 'react';
import { Group, Rect, Path, Line, Text } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

export const RCDSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isClosed = state === 'CLOSED';
  const isTripped = state === 'TRIPPED';
  const isFault = state === 'FAULT';

  return (
    <Group>
      <Rect width={w} height={h} fill="#bdc3c7" stroke="#7f8c8d" strokeWidth={1} cornerRadius={2} />
      <Path data={`M 0 0 L ${w} 0 L ${w-4} 4 L 4 4 Z`} fill="#ecf0f1" />
      <Path data={`M 0 0 L 4 4 L 4 ${h-4} L 0 ${h} Z`} fill="#ecf0f1" />

      {/* Test Button */}
      <Rect x={w*0.7} y={h*0.1} width={w*0.2} height={h*0.2} fill="#e74c3c" stroke="#c0392b" strokeWidth={1} />
      <Text x={w*0.7} y={h*0.1} width={w*0.2} height={h*0.2} text="T" fontSize={8} align="center" verticalAlign="middle" fill="#fff" />

      {/* Switch Handle */}
      {isClosed ? (
        <Rect x={w*0.2} y={h*0.2} width={w*0.3} height={h*0.3} fill="#c0392b" />
      ) : isTripped ? (
        <Rect x={w*0.2} y={h*0.35} width={w*0.3} height={h*0.3} fill="#f1c40f" />
      ) : (
        <Rect x={w*0.2} y={h*0.5} width={w*0.3} height={h*0.3} fill="#27ae60" />
      )}

      {/* Internal toroid schematic representation */}
      <Path data={`M ${w*0.6} ${h*0.5} Q ${w*0.8} ${h*0.5} ${w*0.8} ${h*0.7} Q ${w*0.8} ${h*0.9} ${w*0.6} ${h*0.9}`} stroke="#2c3e50" strokeWidth={1} />
      <Line points={[w*0.7, h*0.5, w*0.7, h*0.9]} stroke="#2c3e50" strokeWidth={1} dash={[2,2]} />

      {isFault && (
        <Rect width={w} height={h} fill="transparent" stroke="#e74c3c" strokeWidth={3} cornerRadius={2} />
      )}
    </Group>
  );
};
