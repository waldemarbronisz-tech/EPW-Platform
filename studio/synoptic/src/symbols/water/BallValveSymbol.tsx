import React from 'react';
import { Group, Rect, Path, Circle } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { SYMBOL_STROKE } from '../../theme/ScadaTheme';
import { waterStub } from '../site/BandedShading';

// fix/hydraulic-connections commit 5 - see water/ValveSymbol.tsx's own
// identical comment on this same margin.
const H_MARGIN_FRACTION = 0.2;

export const BallValveSymbol: React.FC<SymbolProps> = ({ obj, state, terminalNetState }) => {
  const w = obj.width;
  const h = obj.height;
  const margin = w * H_MARGIN_FRACTION;

  const isClosed = state === 'CLOSED';
  const isTransition = state === 'OPENING' || state === 'CLOSING';
  const isFault = state === 'FAULT';

  const fillColor = isClosed ? '#7f8c8d' : (isTransition ? '#f1c40f' : '#2ecc71');
  // feat/wire-routing-around-obstacles commit 5: reads each terminal's
  // own net state.
  const netState = (id: string) => (terminalNetState?.(id) ?? 'INACTIVE') === 'ACTIVE';

  // Bow-tie valve geometry - shrunk to leave room for the krociec/kolnierz.
  const bowTiePath = `M ${margin} 0 L ${w - margin} ${h} L ${w - margin} 0 L ${margin} ${h} Z`;

  return (
    <Group>
      {waterStub(margin, h / 2, 'L', netState('IN'), w, h)}
      {waterStub(w - margin, h / 2, 'R', netState('OUT'), w, h)}
      <Path
        data={bowTiePath}
        fill={fillColor}
        stroke="#2c3e50"
        strokeWidth={SYMBOL_STROKE}
      />

      {/* Circle center with lever handle */}
      <Circle x={w/2} y={h/2} radius={w*0.15} fill="#ecf0f1" stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />

      {/* Lever handle */}
      {isClosed ? (
        // Perpendicular
        <Rect x={w/2 - 2} y={h/2 - h*0.4} width={4} height={h*0.4} fill="#e74c3c" />
      ) : (
        // Parallel
        <Rect x={w/2 - w*0.3} y={h/2 - 2} width={w*0.3} height={4} fill="#27ae60" />
      )}

      {isFault && (
        <Rect width={w} height={h} fill="rgba(255, 0, 0, 0.3)" stroke="red" strokeWidth={SYMBOL_STROKE} />
      )}
    </Group>
  );
};
