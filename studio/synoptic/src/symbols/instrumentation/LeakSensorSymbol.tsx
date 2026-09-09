import React from 'react';
import { Group, Rect, Text } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { SYMBOL_STROKE } from '../../theme/ScadaTheme';

export const LeakSensorSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isActive = state === 'ACTIVE';
  const isFault = state === 'FAULT';

  return (
    <Group>
      <Rect width={w} height={h} fill={isActive ? "#3498db" : "#bdc3c7"} stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} cornerRadius={2} />

      {/* Wave / Water level indicators */}
      <Rect x={w*0.1} y={h*0.7} width={w*0.8} height={h*0.2} fill={isActive ? "#ecf0f1" : "#7f8c8d"} />

      <Text
        x={0} y={h*0.2}
        width={w}
        text="LEAK"
        fontSize={w*0.2}
        fontFamily="sans-serif"
        align="center"
        fill={isActive ? "#ecf0f1" : "#2c3e50"}
      />
      {isFault && (
        <Rect width={w} height={h} fill="rgba(255, 0, 0, 0.3)" stroke="red" strokeWidth={SYMBOL_STROKE} />
      )}
    </Group>
  );
};
