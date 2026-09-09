import React, { useState, useEffect } from 'react';
import { Group, Line, Rect } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

export const ThreePhaseLineSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
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

  // Three parallel lines representing L1, L2, L3
  const y1 = h * 0.2;
  const y2 = h * 0.5;
  const y3 = h * 0.8;
  const strokeW = h * 0.2;

  return (
    <Group>
      <Line points={[0, y1, w, y1]} stroke="#2c3e50" strokeWidth={strokeW} />
      <Line points={[0, y2, w, y2]} stroke="#2c3e50" strokeWidth={strokeW} />
      <Line points={[0, y3, w, y3]} stroke="#2c3e50" strokeWidth={strokeW} />

      {isEnergized && (
        <Group>
           <Line points={[0, y1, w, y1]} stroke="#c0392b" strokeWidth={strokeW} dash={[10, 10]} dashOffset={dashOffset} />
           <Line points={[0, y2, w, y2]} stroke="#c0392b" strokeWidth={strokeW} dash={[10, 10]} dashOffset={dashOffset} />
           <Line points={[0, y3, w, y3]} stroke="#c0392b" strokeWidth={strokeW} dash={[10, 10]} dashOffset={dashOffset} />
        </Group>
      )}

      {/* 3 phase slash indicator */}
      <Line points={[w/2 - 5, h*0.1, w/2 + 5, h*0.9]} stroke="#2c3e50" strokeWidth={1} />
      <Line points={[w/2 - 1, h*0.1, w/2 + 9, h*0.9]} stroke="#2c3e50" strokeWidth={1} />
      <Line points={[w/2 + 3, h*0.1, w/2 + 13, h*0.9]} stroke="#2c3e50" strokeWidth={1} />

      {isFault && (
        <Rect width={w} height={h} fill="transparent" stroke="#e74c3c" strokeWidth={2} />
      )}
    </Group>
  );
};
