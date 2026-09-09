import React from 'react';
import { Group, Rect, Path, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { SYMBOL_STROKE } from '../../theme/ScadaTheme';
import { waterStub } from '../site/BandedShading';

// fix/hydraulic-connections commit 5 - see water/ValveSymbol.tsx's own
// comment on the horizontal margin, and water/SolenoidValveSymbol.tsx's
// own comment on why the bow-tie is recentered on h/2 (the TRUE IN/OUT
// terminal height) - this one originally spanned 0..h*0.8 (centered
// off-axis at 0.4h).
const H_MARGIN_FRACTION = 0.2;
const BOWTIE_HALF_HEIGHT_FRACTION = 0.4; // half of the original 0.8h span

export const DrainValveSymbol: React.FC<SymbolProps> = ({ obj, state, terminalNetState }) => {
  const w = obj.width;
  const h = obj.height;
  const margin = w * H_MARGIN_FRACTION;
  const bowTieTop = h / 2 - h * BOWTIE_HALF_HEIGHT_FRACTION;
  const bowTieBottom = h / 2 + h * BOWTIE_HALF_HEIGHT_FRACTION;

  const isOpen = state === 'OPEN';
  const isFault = state === 'FAULT';

  const fillColor = isOpen ? '#e74c3c' : '#7f8c8d';
  // feat/wire-routing-around-obstacles commit 5: reads each terminal's
  // own net state.
  const netState = (id: string) => (terminalNetState?.(id) ?? 'INACTIVE') === 'ACTIVE';

  // Small bow-tie - shrunk horizontally, recentered vertically (see comments above).
  const bowTiePath = `M ${margin} ${bowTieTop} L ${w - margin} ${bowTieBottom} L ${w - margin} ${bowTieTop} L ${margin} ${bowTieBottom} Z`;

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

      {/* Downward drain line indicating discharge */}
      <Line points={[w/2, h*0.4, w/2, h]} stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />
      <Line points={[w*0.3, h, w*0.7, h]} stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />

      {isFault && (
        <Rect width={w} height={h} fill="rgba(255, 0, 0, 0.3)" stroke="red" strokeWidth={SYMBOL_STROKE} />
      )}
    </Group>
  );
};
