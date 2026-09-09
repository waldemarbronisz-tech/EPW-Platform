import React from 'react';
import { Group, Rect, Text } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

export const ELAInputsSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;
  const isFault = state === 'FAULT';

  return (
    <Group>
      <Rect width={w} height={h} fill="#bdc3c7" stroke="#34495e" strokeWidth={1} />
      <Text x={0} y={5} width={w} text="ELA" align="center" fill="#2c3e50" fontSize={12} fontFamily="monospace" fontStyle="bold" />
      <Text x={0} y={18} width={w} text="IN" align="center" fill="#e74c3c" fontSize={10} fontFamily="monospace" />

      <Rect x={w*0.2} y={h*0.4} width={w*0.6} height={h*0.5} fill="#ecf0f1" stroke="#95a5a6" strokeWidth={1} />

      {isFault && (
        <Rect width={w} height={h} fill="transparent" stroke="#e74c3c" strokeWidth={3} />
      )}
    </Group>
  );
};
