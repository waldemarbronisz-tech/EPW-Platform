import React, { useState, useEffect } from 'react';
import { Group, Rect, Circle, Arc } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { SYMBOL_STROKE } from '../../theme/ScadaTheme';

export const FanSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;
  const radius = Math.min(w, h) / 2;

  const isRunning = state === 'RUNNING';
  const isFault = state === 'FAULT';

  const [angle, setAngle] = useState(0);

  useEffect(() => {
    let animationFrame: number;
    const animate = () => {
      setAngle(prev => (prev + 15) % 360);
      animationFrame = requestAnimationFrame(animate);
    };

    if (isRunning) {
      animationFrame = requestAnimationFrame(animate);
    }

    return () => {
      if (animationFrame) cancelAnimationFrame(animationFrame);
    };
  }, [isRunning]);

  return (
    <Group>
      {/* Casing */}
      <Rect width={w} height={h} fill="#bdc3c7" stroke="#7f8c8d" strokeWidth={SYMBOL_STROKE} />
      <Circle x={w/2} y={h/2} radius={radius - 2} fill="#34495e" />

      {/* Blades */}
      <Group x={w/2} y={h/2} rotation={isRunning ? angle : 0}>
         <Arc x={0} y={0} innerRadius={0} outerRadius={radius*0.8} angle={45} rotation={0} fill="#ecf0f1" />
         <Arc x={0} y={0} innerRadius={0} outerRadius={radius*0.8} angle={45} rotation={90} fill="#ecf0f1" />
         <Arc x={0} y={0} innerRadius={0} outerRadius={radius*0.8} angle={45} rotation={180} fill="#ecf0f1" />
         <Arc x={0} y={0} innerRadius={0} outerRadius={radius*0.8} angle={45} rotation={270} fill="#ecf0f1" />
      </Group>

      {isFault && (
        <Rect width={w} height={h} fill="rgba(255, 0, 0, 0.3)" stroke="red" strokeWidth={SYMBOL_STROKE} />
      )}
    </Group>
  );
};
