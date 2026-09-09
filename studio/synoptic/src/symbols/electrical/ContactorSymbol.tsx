import React from 'react';
import { Group, Rect, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

export const ContactorSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isOn = state === 'ON';
  const isFault = state === 'FAULT';

  return (
    <Group>
      {/* Invisible Hitbox */}
      <Rect width={w} height={h} fill="transparent" />

      {/* Lines */}
      <Line points={[w/2, 0, w/2, h*0.3]} stroke="#2c3e50" strokeWidth={2} />
      <Line points={[w/2, h, w/2, h*0.7]} stroke="#2c3e50" strokeWidth={2} />

      {/* Main Contact */}
      {isOn ? (
        <Line points={[w/2, h*0.3, w/2, h*0.7]} stroke="green" strokeWidth={3} />
      ) : (
        <Line points={[w/2, h*0.7, w/2 + w*0.3, h*0.4]} stroke="#2c3e50" strokeWidth={2} />
      )}

      {/* Coil Indicator (Rectangle with diagonal line) */}
      <Rect x={w*0.7} y={h*0.7} width={w*0.2} height={h*0.2} fill={isOn ? "yellow" : "white"} stroke="#2c3e50" strokeWidth={1} />
      <Line points={[w*0.7, h*0.7, w*0.9, h*0.9]} stroke="#2c3e50" strokeWidth={1} />

      {/* Fault indicator */}
      {isFault && (
        <Rect x={w*0.1} y={h*0.1} width={w*0.8} height={h*0.8} stroke="#e74c3c" strokeWidth={2} dash={[4, 2]} />
      )}
    </Group>
  );
};
