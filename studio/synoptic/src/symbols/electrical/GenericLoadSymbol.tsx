import React from 'react';
import { Group, Rect, Circle, Text } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

export const GenericLoadSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isOn = state === 'ON';
  const isFault = state === 'FAULT';

  return (
    <Group>
      <Rect width={w} height={h} fill="#bdc3c7" stroke="#7f8c8d" strokeWidth={1} cornerRadius={2} />

      {/* Central part */}
      <Circle x={w/2} y={h/2} radius={w*0.3} fill={isOn ? "#f1c40f" : "#95a5a6"} stroke="#2c3e50" strokeWidth={1} />

      {/* 'LOAD' text */}
      <Text
        x={0} y={h/2 - 5}
        width={w}
        text="LOAD"
        fontSize={10}
        fontFamily="sans-serif"
        align="center"
        fill="#2c3e50"
      />

      {isFault && (
        <Rect width={w} height={h} fill="transparent" stroke="#e74c3c" strokeWidth={3} cornerRadius={2} />
      )}
    </Group>
  );
};
