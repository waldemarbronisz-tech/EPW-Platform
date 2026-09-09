import React from 'react';
import { Group, Rect, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

import { useState, useEffect } from 'react';

export const PipeSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isFlow = state === 'FLOW';
  const isFault = state === 'FAULT';

  const color = isFlow ? '#3498db' : '#95a5a6';

  const [dashOffset, setDashOffset] = useState(0);

  useEffect(() => {
    let animationFrame: number;
    const animate = () => {
      setDashOffset(prev => (prev - 1) % 20); // Move backwards for forward flow effect
      animationFrame = requestAnimationFrame(animate);
    };

    if (isFlow) {
      animationFrame = requestAnimationFrame(animate);
    }

    return () => {
      if (animationFrame) cancelAnimationFrame(animationFrame);
    };
  }, [isFlow]);

  return (
    <Group>
      {/* Main pipe body */}
      <Rect width={w} height={h} fill={color} stroke="#2c3e50" strokeWidth={2} />

      {/* Flow indicator line if horizontal pipe is thick enough */}
      {isFlow && h >= 10 && (
         <Line
           points={[w*0.05, h/2, w*0.95, h/2]}
           stroke="#ecf0f1"
           strokeWidth={2}
           dash={[10, 10]}
           dashOffset={dashOffset}
         />
      )}

      {isFault && (
        <Rect width={w} height={h} fill="transparent" stroke="#e74c3c" strokeWidth={2} />
      )}
    </Group>
  );
};
