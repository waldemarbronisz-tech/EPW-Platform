import React from 'react';
import { Group, Rect, Path } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { SYMBOL_STROKE } from '../../theme/ScadaTheme';
import { waterStub } from '../site/BandedShading';

// fix/hydraulic-connections commit 5: the tank outline used to fill
// its own full width (0..w) - shrunk to leave room for the krociec/
// kolnierz on its real IN (LEFT)/OUT (RIGHT) terminals, both at h/2.
const H_MARGIN_FRACTION = 0.15;

export const TankSymbol: React.FC<SymbolProps> = ({ obj, state, terminalNetState }) => {
  const w = obj.width;
  const h = obj.height;
  const margin = w * H_MARGIN_FRACTION;
  const bodyLeft = margin;
  const bodyRight = w - margin;
  const bodyWidth = bodyRight - bodyLeft;

  const isFault = state === 'FAULT';
  const isLow = state === 'LOW';
  const isHigh = state === 'HIGH';

  let fillLevel = 0.5; // Normal
  if (isLow) fillLevel = 0.15;
  if (isHigh) fillLevel = 0.85;

  const waterColor = isFault ? '#c0392b' : '#3498db';
  // feat/wire-routing-around-obstacles commit 5: reads each terminal's
  // own net state - this generic (non-MEASURED, no device binding)
  // tank does not qualify for the "aparat MEASURED o rodzaju zbiornik"
  // source rule (NetResolver.ts, scoped to site.rainwater_tank2 only,
  // the one real MEASURED tank in this registry - see raport.md), so
  // its own OUT no longer self-sources from fillLevel either; both
  // terminals are now plain net-state readouts like every other water
  // aparat's.
  const netState = (id: string) => (terminalNetState?.(id) ?? 'INACTIVE') === 'ACTIVE';

  // Tank outline (rounded top and bottom simulation with path)
  const tankPath = `
    M ${bodyLeft} ${h*0.1}
    Q ${w/2} ${-h*0.05} ${bodyRight} ${h*0.1}
    L ${bodyRight} ${h*0.9}
    Q ${w/2} ${h*1.05} ${bodyLeft} ${h*0.9}
    Z
  `;

  return (
    <Group>
      {/* krociec+kolnierz on the real IN (LEFT)/OUT (RIGHT) terminals,
          from the tank's own shrunk walls. */}
      {waterStub(bodyLeft, h / 2, 'L', netState('IN'), w, h)}
      {waterStub(bodyRight, h / 2, 'R', netState('OUT'), w, h)}

      {/* Background/Empty Tank */}
      <Path data={tankPath} fill="#ecf0f1" stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />

      {/* Water Level */}
      <Rect
        x={bodyLeft + 2}
        y={h * (1 - fillLevel)}
        width={bodyWidth - 4}
        height={h * fillLevel - h*0.05}
        fill={waterColor}
        opacity={0.8}
      />

      {/* Level indicators */}
      <Rect x={bodyLeft - 5} y={h*0.15} width={10} height={2} fill="red" />
      <Rect x={bodyLeft - 5} y={h*0.85} width={10} height={2} fill="blue" />

      {isFault && (
        <Rect width={w} height={h} fill="rgba(255, 0, 0, 0.3)" stroke="red" strokeWidth={SYMBOL_STROKE} />
      )}
    </Group>
  );
};
