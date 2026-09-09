import React from 'react';
import { Group, Rect, Circle, Text } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { SYMBOL_STROKE } from '../../theme/ScadaTheme';

export const HumiditySensorSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isFault = state === 'FAULT';

  return (
    <Group>
      <Circle x={w/2} y={h*0.7} radius={w*0.3} fill="#ecf0f1" stroke="#2980b9" strokeWidth={SYMBOL_STROKE} />
      <Text
        x={0} y={h*0.55}
        width={w}
        text="H"
        fontSize={w*0.3}
        fontFamily="sans-serif"
        align="center"
        fill="#2980b9"
      />
      {isFault && (
        <Rect width={w} height={h} fill="rgba(255, 0, 0, 0.3)" stroke="red" strokeWidth={SYMBOL_STROKE} />
      )}
    </Group>
  );
};
