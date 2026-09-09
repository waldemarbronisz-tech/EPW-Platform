import React from 'react';
import { Group, Rect, Path } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { SYMBOL_STROKE } from '../../theme/ScadaTheme';
import { waterStub } from '../site/BandedShading';

// fix/hydraulic-connections commit 5 - see water/ValveSymbol.tsx's own
// identical comment on this same margin. The TRUE IN/OUT terminal
// height is ALWAYS h/2 (getTerminalOffsetForSide's own, fixed LEFT/
// RIGHT rule - never the bow-tie's own visual midpoint) - the bow-tie
// itself used to span h*0.3..h (centered off-axis at 0.65h, not 0.5h)
// so it is recentered on h/2 here too, keeping its own height (0.7h)
// unchanged - only its position shifts.
const H_MARGIN_FRACTION = 0.2;
const BOWTIE_HALF_HEIGHT_FRACTION = 0.35; // half of the original 0.7h span

export const SolenoidValveSymbol: React.FC<SymbolProps> = ({ obj, state, terminalNetState }) => {
  const w = obj.width;
  const h = obj.height;
  const margin = w * H_MARGIN_FRACTION;
  const bowTieTop = h / 2 - h * BOWTIE_HALF_HEIGHT_FRACTION;
  const bowTieBottom = h / 2 + h * BOWTIE_HALF_HEIGHT_FRACTION;

  const isClosed = state === 'CLOSED';
  const isTransition = state === 'OPENING' || state === 'CLOSING';
  const isFault = state === 'FAULT';

  const fillColor = isClosed ? '#7f8c8d' : (isTransition ? '#f1c40f' : '#2ecc71');
  // feat/wire-routing-around-obstacles commit 5: reads each terminal's
  // own net state.
  const netState = (id: string) => (terminalNetState?.(id) ?? 'INACTIVE') === 'ACTIVE';

  // Bow-tie valve geometry - shrunk horizontally to leave room for the
  // krociec/kolnierz, and recentered vertically on the true terminal
  // height (see BOWTIE_HALF_HEIGHT_FRACTION's own comment above).
  const bowTiePath = `M ${margin} ${bowTieTop} L ${w - margin} ${bowTieBottom} L ${w - margin} ${bowTieTop} L ${margin} ${bowTieBottom} Z`;

  return (
    <Group>
      {waterStub(margin, h / 2, 'L', netState('IN'), w, h)}
      {waterStub(w - margin, h / 2, 'R', netState('OUT'), w, h)}
      {/* Solenoid Coil Box */}
      <Rect x={w*0.3} y={0} width={w*0.4} height={h*0.4} fill="#2980b9" stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />

      {/* Actuator stem */}
      <Rect x={w/2 - 2} y={h*0.4} width={4} height={h*0.25} fill="#2c3e50" />

      {/* Valve body */}
      <Path
        data={bowTiePath}
        fill={fillColor}
        stroke="#2c3e50"
        strokeWidth={SYMBOL_STROKE}
      />

      {isFault && (
        <Rect width={w} height={h} fill="rgba(255, 0, 0, 0.3)" stroke="red" strokeWidth={SYMBOL_STROKE} />
      )}
    </Group>
  );
};
