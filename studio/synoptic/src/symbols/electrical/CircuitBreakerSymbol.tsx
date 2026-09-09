import React from 'react';
import { Group, Rect, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { SYMBOL_STROKE } from '../../theme/ScadaTheme';

export const CircuitBreakerSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isClosed = state === 'CLOSED';
  const isTripped = state === 'TRIPPED';
  const isFault = state === 'FAULT';

  return (
    <Group>
      {/* Invisible Hitbox */}
      <Rect width={w} height={h} fill="transparent" />

      {/* Conductors (top and bottom) */}
      <Line points={[w/2, 0, w/2, h*0.3]} stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />
      <Line points={[w/2, h, w/2, h*0.7]} stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />

      {/* Cross mark indicating breaker */}
      <Line points={[w*0.35, h*0.2, w*0.65, h*0.4]} stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />
      <Line points={[w*0.35, h*0.4, w*0.65, h*0.2]} stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />

      {/* Switch Blade */}
      {isClosed ? (
        <Line points={[w/2, h*0.3, w/2, h*0.7]} stroke="green" strokeWidth={SYMBOL_STROKE} />
      ) : isTripped ? (
        <Line points={[w/2, h*0.7, w/2 + w*0.2, h*0.5]} stroke="#f39c12" strokeWidth={SYMBOL_STROKE} />
      ) : (
        <Line points={[w/2, h*0.7, w/2 + w*0.3, h*0.4]} stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />
      )}

      {/* Fault indicator */}
      {isFault && (
        <Rect x={w*0.1} y={h*0.1} width={w*0.8} height={h*0.8} stroke="#e74c3c" strokeWidth={SYMBOL_STROKE} dash={[4, 2]} />
      )}
    </Group>
  );
};
