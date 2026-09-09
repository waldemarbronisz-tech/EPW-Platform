import React from 'react';
import { Group, Rect, Circle, Text } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

export const GeneratorSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isRunning = state === 'RUNNING';
  const isFault = state === 'FAULT';

  return (
    <Group>
      <Rect width={w} height={h} fill="#bdc3c7" stroke="#7f8c8d" strokeWidth={1} cornerRadius={5} />

      {/* Central circular part */}
      <Circle x={w/2} y={h/2} radius={w*0.35} fill={isRunning ? "#f1c40f" : "#95a5a6"} stroke="#2c3e50" strokeWidth={2} />

      {/* 'G' text */}
      <Text
        x={0} y={h*0.35}
        width={w}
        text="G"
        fontSize={w*0.3}
        fontFamily="sans-serif"
        align="center"
        fill="#2c3e50"
      />

      {isFault && (
        <Rect width={w} height={h} fill="transparent" stroke="#e74c3c" strokeWidth={3} cornerRadius={5} />
      )}
    </Group>
  );
};
