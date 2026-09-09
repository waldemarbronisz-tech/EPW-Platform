import React, { useState, useEffect } from 'react';
import { Group, Rect, Circle, Arc } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { SYMBOL_STROKE } from '../../theme/ScadaTheme';
import { waterStub } from '../site/BandedShading';

// fix/hydraulic-connections commit 5: the pump body used to fill its
// own full width/height (radius = min(w,h)/2 touches every edge) -
// shrunk to leave room for the krociec/kolnierz on its real IN (LEFT)/
// OUT (RIGHT) terminals - both on h/2, the pump's own vertical center,
// so no recentering is needed here, only shrinking.
const RADIUS_MARGIN_FRACTION = 0.2;

export const PumpSymbol: React.FC<SymbolProps> = ({ obj, state, terminalNetState }) => {
  const w = obj.width;
  const h = obj.height;
  const radius = Math.min(w, h) / 2 * (1 - RADIUS_MARGIN_FRACTION);

  const isRunning = state === 'RUNNING';
  const isFault = state === 'FAULT';
  // feat/wire-routing-around-obstacles commit 5: reads each terminal's
  // own net state, not the pump's own running state.
  const netState = (id: string) => (terminalNetState?.(id) ?? 'INACTIVE') === 'ACTIVE';

  const [angle, setAngle] = useState(0);

  useEffect(() => {
    let animationFrame: number;
    const animate = () => {
      setAngle(prev => (prev + 10) % 360);
      animationFrame = requestAnimationFrame(animate);
    };

    if (isRunning) {
      animationFrame = requestAnimationFrame(animate);
    }

    return () => {
      if (animationFrame) cancelAnimationFrame(animationFrame);
    };
  }, [isRunning]);

  const color = isRunning ? '#2ecc71' : '#95a5a6';

  return (
    <Group>
      {/* fix/hydraulic-connections commit 5: krociec+kolnierz on the
          real IN (LEFT)/OUT (RIGHT) terminals, from the pump body's
          own left/right edges - retires the old decorative "Outlet"
          rect, which was drawn at the TOP and never matched the
          registry's own RIGHT-side OUT terminal at all. */}
      {waterStub(w / 2 - radius, h / 2, 'L', netState('IN'), w, h)}
      {waterStub(w / 2 + radius, h / 2, 'R', netState('OUT'), w, h)}

      {/* Base */}
      <Rect x={w*0.2} y={h*0.8} width={w*0.6} height={h*0.2} fill="#34495e" />

      {/* Main Pump Body */}
      <Circle x={w/2} y={h/2} radius={radius} fill={color} stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />

      {/* Impeller representation */}
      <Group x={w/2} y={h/2} rotation={isRunning ? angle : 0}>
         <Arc x={0} y={0} innerRadius={0} outerRadius={radius*0.8} angle={60} rotation={0} fill="#27ae60" />
         <Arc x={0} y={0} innerRadius={0} outerRadius={radius*0.8} angle={60} rotation={120} fill="#27ae60" />
         <Arc x={0} y={0} innerRadius={0} outerRadius={radius*0.8} angle={60} rotation={240} fill="#27ae60" />
      </Group>

      {isFault && (
        <Rect width={w} height={h} fill="rgba(255, 0, 0, 0.3)" stroke="red" strokeWidth={SYMBOL_STROKE} />
      )}
    </Group>
  );
};
