import React from 'react';
import { Group, Rect, Path } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { waterStub } from '../site/BandedShading';

// fix/hydraulic-connections commit 5 - see ValveSymbol.tsx's own
// identical comment on this same margin.
const H_MARGIN_FRACTION = 0.2;

export const GateValveSymbol: React.FC<SymbolProps> = ({ obj, state, terminalNetState }) => {
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
        strokeWidth={1}
      />

      {/* T-shaped handle for gate valve */}
      <Rect x={w/2 - 2} y={isClosed ? h/2 - h*0.4 : h/2 - h*0.8} width={4} height={h*0.4} fill="#2c3e50" />
      <Rect x={w/2 - w*0.2} y={isClosed ? h/2 - h*0.4 : h/2 - h*0.8} width={w*0.4} height={4} fill="#2c3e50" />

      {isFault && (
        <Rect width={w} height={h} fill="rgba(255, 0, 0, 0.3)" stroke="red" strokeWidth={2} />
      )}
    </Group>
  );
};
