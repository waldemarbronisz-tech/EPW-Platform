import React from 'react';
import { Group, Rect, Path, Circle } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { waterStub } from '../site/BandedShading';

// fix/hydraulic-connections commit 5: the bow-tie used to fill the
// object's own full width (0..w), leaving no room at all for a
// krociec/kolnierz on either terminal (IN/LEFT, OUT/RIGHT) - shrunk by
// a 20% margin on each side so both fit.
const H_MARGIN_FRACTION = 0.2;

export const ValveSymbol: React.FC<SymbolProps> = ({ obj, state, terminalNetState }) => {
  const w = obj.width;
  const h = obj.height;
  const margin = w * H_MARGIN_FRACTION;

  const isClosed = state === 'CLOSED';
  const isTransition = state === 'OPENING' || state === 'CLOSING';
  const isFault = state === 'FAULT';

  const fillColor = isClosed ? '#7f8c8d' : (isTransition ? '#f1c40f' : '#2ecc71');
  // feat/wire-routing-around-obstacles commit 5: reads each terminal's
  // own net state, not the valve's own open/closed appearance.
  const netState = (id: string) => (terminalNetState?.(id) ?? 'INACTIVE') === 'ACTIVE';

  // Bow-tie valve geometry - shrunk to leave room for the krociec/
  // kolnierz standard (see H_MARGIN_FRACTION's own comment above).
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

      {/* Center circle/actuator */}
      <Circle
        x={w/2}
        y={h/2}
        radius={h*0.3}
        fill={isClosed ? '#95a5a6' : '#27ae60'}
        stroke="#2c3e50"
        strokeWidth={1}
      />

      {/* Stem position indicating closed or open */}
      <Rect
        x={w/2 - 2}
        y={isClosed ? h/2 - h*0.5 : h/2 - h*0.8}
        width={4}
        height={h*0.5}
        fill="#000"
      />

      {isFault && (
        <Rect width={w} height={h} fill="rgba(255, 0, 0, 0.3)" stroke="red" strokeWidth={2} />
      )}
    </Group>
  );
};
