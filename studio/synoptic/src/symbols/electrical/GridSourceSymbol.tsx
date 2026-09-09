import React from 'react';
import { Group, Rect, Path, Text } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

export const GridSourceSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isEnergized = state === 'ENERGIZED';
  const isFault = state === 'FAULT';

  return (
    <Group>
      <Rect width={w} height={h} fill="#bdc3c7" stroke="#7f8c8d" strokeWidth={1} cornerRadius={5} />

      {/* Tower shape representation */}
      <Path data={`M ${w*0.3} ${h*0.8} L ${w*0.4} ${h*0.2} L ${w*0.6} ${h*0.2} L ${w*0.7} ${h*0.8}`} stroke={isEnergized ? "#e74c3c" : "#2c3e50"} strokeWidth={2} />
      <Path data={`M ${w*0.2} ${h*0.4} L ${w*0.8} ${h*0.4}`} stroke={isEnergized ? "#e74c3c" : "#2c3e50"} strokeWidth={2} />

      <Text
        x={0} y={h*0.8}
        width={w}
        text="GRID"
        fontSize={10}
        fontFamily="monospace"
        align="center"
        fill="#2c3e50"
      />

      {isFault && (
        <Rect width={w} height={h} fill="transparent" stroke="#e74c3c" strokeWidth={3} cornerRadius={5} />
      )}
    </Group>
  );
};
