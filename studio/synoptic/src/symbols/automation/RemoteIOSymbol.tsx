import React, { useState, useEffect } from 'react';
import { Group, Rect, Circle, Text } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

export const RemoteIOSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isRunning = state === 'RUNNING';
  const isFault = state === 'FAULT';

  const [blink, setBlink] = useState(false);
  useEffect(() => {
    let interval: any;
    if (isRunning) {
      interval = setInterval(() => setBlink(b => !b), 800);
    } else {
      setBlink(false);
    }
    return () => clearInterval(interval);
  }, [isRunning]);

  return (
    <Group>
      <Rect width={w} height={h} fill="#7f8c8d" stroke="#2c3e50" strokeWidth={2} cornerRadius={4} />
      <Rect x={w*0.1} y={h*0.2} width={w*0.8} height={h*0.7} fill="#95a5a6" cornerRadius={2} />

      <Text x={5} y={5} text="REM-IO" fill="#2c3e50" fontSize={10} fontFamily="monospace" />

      {/* Status LED */}
      <Circle x={w*0.85} y={10} radius={3} fill={blink ? "#2ecc71" : "#34495e"} />

      {/* IO points representation */}
      <Rect x={w*0.2} y={h*0.3} width={w*0.6} height={h*0.1} fill="#ecf0f1" />
      <Rect x={w*0.2} y={h*0.5} width={w*0.6} height={h*0.1} fill="#ecf0f1" />
      <Rect x={w*0.2} y={h*0.7} width={w*0.6} height={h*0.1} fill="#ecf0f1" />

      {isFault && (
        <Rect width={w} height={h} fill="transparent" stroke="#e74c3c" strokeWidth={3} cornerRadius={4} />
      )}
    </Group>
  );
};
