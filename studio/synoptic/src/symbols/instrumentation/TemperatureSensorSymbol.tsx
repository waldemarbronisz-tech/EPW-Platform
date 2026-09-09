import React from 'react';
import { Group, Rect, Circle, Line, Text } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { SYMBOL_STROKE } from '../../theme/ScadaTheme';

export const TemperatureSensorSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isFault = state === 'FAULT';

  return (
    <Group>
      {/* Sensor body (thermometer shape) */}
      <Rect x={w*0.3} y={h*0.1} width={w*0.4} height={h*0.6} fill="#ecf0f1" stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} cornerRadius={10} />
      <Circle x={w/2} y={h*0.8} radius={w*0.3} fill="#ecf0f1" stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />

      {/* Mercury/Liquid level */}
      <Circle x={w/2} y={h*0.8} radius={w*0.2} fill="#e74c3c" />
      <Rect x={w*0.4} y={h*0.4} width={w*0.2} height={h*0.4} fill="#e74c3c" />

      {/* T Label */}
      <Text
        x={w} y={h*0.2}
        text="T"
        fontSize={14}
        fontFamily="sans-serif"
        fill="#2c3e50"
      />

      {/* Measurement marks */}
      <Line points={[w*0.6, h*0.2, w*0.7, h*0.2]} stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />
      <Line points={[w*0.6, h*0.4, w*0.7, h*0.4]} stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />
      <Line points={[w*0.6, h*0.6, w*0.7, h*0.6]} stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />

      {isFault && (
        <Rect width={w} height={h} fill="rgba(255, 0, 0, 0.3)" stroke="red" strokeWidth={SYMBOL_STROKE} />
      )}
    </Group>
  );
};
