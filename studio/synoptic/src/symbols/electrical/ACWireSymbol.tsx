import React, { useState, useEffect } from 'react';
import { Group, Line, Rect } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

export const ACWireSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isEnergized = state === 'ENERGIZED';
  const isFault = state === 'FAULT';

  const [dashOffset, setDashOffset] = useState(0);

  useEffect(() => {
    let animationFrame: number;
    const animate = () => {
      setDashOffset(prev => (prev - 1) % 20);
      animationFrame = requestAnimationFrame(animate);
    };

    if (isEnergized) {
      animationFrame = requestAnimationFrame(animate);
    }

    return () => {
      if (animationFrame) cancelAnimationFrame(animationFrame);
    };
  }, [isEnergized]);

  return (
    <Group>
      {/* Base wire line */}
      <Line points={[0, h/2, w, h/2]} stroke="#34495e" strokeWidth={h} />

      {/* Energized visual flow */}
      {isEnergized && (
         <Line
           points={[0, h/2, w, h/2]}
           stroke="#e74c3c"
           strokeWidth={h}
           dash={[10, 10]}
           dashOffset={dashOffset}
         />
      )}

      {isFault && (
        <Rect width={w} height={h} fill="transparent" stroke="#c0392b" strokeWidth={2} />
      )}
    </Group>
  );
};
