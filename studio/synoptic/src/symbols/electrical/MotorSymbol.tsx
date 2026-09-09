import React from 'react';
import { Group, Rect, Circle, Text } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { SYMBOL_STROKE } from '../../theme/ScadaTheme';

export const MotorSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isRunning = state === 'RUNNING';
  const isFault = state === 'FAULT';

  return (
    <Group>
      <Rect width={w} height={h} fill="#bdc3c7" stroke="#7f8c8d" strokeWidth={SYMBOL_STROKE} cornerRadius={5} />

      {/* Central circular part */}
      <Circle x={w/2} y={h/2} radius={w*0.35} fill={isRunning ? "#2ecc71" : "#95a5a6"} stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />

      {/* 'M' text */}
      <Text
        x={0} y={h*0.35}
        width={w}
        text="M"
        fontSize={w*0.3}
        fontFamily="sans-serif"
        align="center"
        fill="#2c3e50"
      />

      {isFault && (
        <Rect width={w} height={h} fill="transparent" stroke="#e74c3c" strokeWidth={SYMBOL_STROKE} cornerRadius={5} />
      )}
    </Group>
  );
};
