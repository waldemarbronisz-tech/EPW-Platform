import React, { useState, useEffect } from 'react';
import { Group, Rect, Circle, Text } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

export const PLCSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
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
      {/* Chassis */}
      <Rect width={w} height={h} fill="#34495e" stroke="#2c3e50" strokeWidth={2} cornerRadius={4} />
      <Rect x={w*0.05} y={h*0.2} width={w*0.9} height={h*0.7} fill="#2c3e50" cornerRadius={2} />

      {/* Label */}
      <Text x={5} y={5} text="PLC" fill="#ecf0f1" fontSize={12} fontFamily="monospace" />

      {/* Status LEDs */}
      <Circle x={w*0.8} y={10} radius={3} fill={isRunning ? "#2ecc71" : "#7f8c8d"} />
      <Circle x={w*0.9} y={10} radius={3} fill={blink ? "#f1c40f" : "#7f8c8d"} />

      {/* IO blocks representation */}
      <Rect x={w*0.1} y={h*0.3} width={w*0.3} height={h*0.5} fill="#7f8c8d" />
      <Rect x={w*0.5} y={h*0.3} width={w*0.3} height={h*0.5} fill="#7f8c8d" />

      {isFault && (
        <Rect width={w} height={h} fill="transparent" stroke="#e74c3c" strokeWidth={3} cornerRadius={4} />
      )}
    </Group>
  );
};
