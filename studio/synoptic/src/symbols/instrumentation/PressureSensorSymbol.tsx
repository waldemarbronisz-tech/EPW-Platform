import React from 'react';
import { Group, Rect, Circle, Text } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { SYMBOL_STROKE } from '../../theme/ScadaTheme';

export const PressureSensorSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isFault = state === 'FAULT';

  return (
    <Group>
      <Circle x={w/2} y={h/2} radius={w*0.4} fill="#ecf0f1" stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />
      <Text
        x={0} y={h*0.3}
        width={w}
        text="P"
        fontSize={w*0.4}
        fontFamily="sans-serif"
        align="center"
        fill="#2c3e50"
      />
      {isFault && (
        <Rect width={w} height={h} fill="rgba(255, 0, 0, 0.3)" stroke="red" strokeWidth={SYMBOL_STROKE} />
      )}
    </Group>
  );
};
