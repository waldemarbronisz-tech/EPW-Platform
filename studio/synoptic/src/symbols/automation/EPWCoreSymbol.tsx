import React, { useState, useEffect } from 'react';
import { Group, Rect, Circle, Text } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

export const EPWCoreSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isRunning = state === 'RUNNING';
  const isFault = state === 'FAULT';

  const [blink, setBlink] = useState(false);
  useEffect(() => {
    let interval: any;
    if (isRunning) {
      interval = setInterval(() => setBlink(b => !b), 500);
    } else {
      setBlink(false);
    }
    return () => clearInterval(interval);
  }, [isRunning]);

  return (
    <Group>
      {/* 3D hardware module shape */}
      <Rect width={w} height={h} fill="#2c3e50" stroke="#34495e" strokeWidth={2} cornerRadius={4} />
      <Rect x={4} y={4} width={w-8} height={20} fill="#34495e" cornerRadius={2} />

      <Text x={8} y={8} text="EPW CORE" fill="#ecf0f1" fontSize={12} fontFamily="monospace" fontStyle="bold" />

      {/* Network / Status LEDs */}
      <Circle x={w*0.8} y={14} radius={3} fill={isRunning ? "#2ecc71" : "#7f8c8d"} />
      <Circle x={w*0.9} y={14} radius={3} fill={blink ? "#3498db" : "#7f8c8d"} />

      {/* Internal block details */}
      <Rect x={w*0.1} y={h*0.4} width={w*0.8} height={h*0.5} fill="#34495e" />
      <Rect x={w*0.15} y={h*0.5} width={w*0.7} height={h*0.3} fill="#2c3e50" />
      <Text x={w*0.2} y={h*0.6} text="CPU" fill="#7f8c8d" fontSize={10} fontFamily="monospace" />

      {isFault && (
        <Rect width={w} height={h} fill="transparent" stroke="#e74c3c" strokeWidth={3} cornerRadius={4} />
      )}
    </Group>
  );
};
