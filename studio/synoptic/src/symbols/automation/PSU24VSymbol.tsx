import React from 'react';
import { Group, Rect, Circle, Text } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

export const PSU24VSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isOn = state === 'ON';
  const isFault = state === 'FAULT';

  return (
    <Group>
      <Rect width={w} height={h} fill="#bdc3c7" stroke="#34495e" strokeWidth={1} cornerRadius={2} />

      <Text x={0} y={h*0.1} width={w} text="PSU" align="center" fill="#2c3e50" fontSize={10} fontFamily="monospace" fontStyle="bold" />
      <Text x={0} y={h*0.3} width={w} text="24V" align="center" fill="#27ae60" fontSize={12} fontFamily="monospace" fontStyle="bold" />

      {/* Vents representation */}
      <Rect x={w*0.2} y={h*0.6} width={w*0.6} height={2} fill="#7f8c8d" />
      <Rect x={w*0.2} y={h*0.7} width={w*0.6} height={2} fill="#7f8c8d" />
      <Rect x={w*0.2} y={h*0.8} width={w*0.6} height={2} fill="#7f8c8d" />

      {/* DC OK LED */}
      <Circle x={w*0.8} y={h*0.15} radius={3} fill={isOn ? "#2ecc71" : "#7f8c8d"} />

      {isFault && (
        <Rect width={w} height={h} fill="transparent" stroke="#e74c3c" strokeWidth={3} cornerRadius={2} />
      )}
    </Group>
  );
};
