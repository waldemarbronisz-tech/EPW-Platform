import React from 'react';
import { Group, Rect, Path, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { SYMBOL_STROKE } from '../../theme/ScadaTheme';
import { waterStub } from '../site/BandedShading';

// fix/hydraulic-connections commit 5: the funnel's own top-left corner
// used to sit right at x=0, leaving no room for a krociec/kolnierz on
// its one real terminal (IN, LEFT, at h/2) - nudged in by a margin so
// it fits. The funnel's own left wall at y=h/2 (where LEFT_WALL_AT_HALF
// lands, by linear interpolation between the nudged top-left corner
// and the unchanged bottom-left corner) is where the krociec starts.
const TOP_LEFT_MARGIN_FRACTION = 0.15;

export const DrainSymbol: React.FC<SymbolProps> = ({ obj, state, terminalNetState }) => {
  const w = obj.width;
  const h = obj.height;
  const topLeftX = w * TOP_LEFT_MARGIN_FRACTION;
  const bottomLeftX = w * 0.3;
  const leftWallAtHalf = topLeftX + (bottomLeftX - topLeftX) * 0.5;

  const isFault = state === 'FAULT';
  // feat/wire-routing-around-obstacles commit 5: reads its own net state.
  const inLive = (terminalNetState?.('IN') ?? 'INACTIVE') === 'ACTIVE';

  return (
    <Group>
      {waterStub(leftWallAtHalf, h / 2, 'L', inLive, w, h)}
      {/* Funnel/drain shape */}
      <Path data={`M ${topLeftX} 0 L ${w} 0 L ${w*0.7} ${h} L ${bottomLeftX} ${h} Z`} fill="#95a5a6" stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />

      {/* Grate lines */}
      <Line points={[w*0.2, h*0.2, w*0.8, h*0.2]} stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />
      <Line points={[w*0.3, h*0.5, w*0.7, h*0.5]} stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />
      <Line points={[w*0.4, h*0.8, w*0.6, h*0.8]} stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />

      {isFault && (
        <Rect width={w} height={h} fill="rgba(255, 0, 0, 0.3)" stroke="red" strokeWidth={SYMBOL_STROKE} />
      )}
    </Group>
  );
};
