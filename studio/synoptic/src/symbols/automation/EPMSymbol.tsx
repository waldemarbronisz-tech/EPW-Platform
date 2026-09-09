import React, { useState, useEffect } from 'react';
import { Group, Rect, Circle, Text } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

export const EPMSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isRunning = state === 'RUNNING';
  const isFault = state === 'FAULT';

  const [blink, setBlink] = useState(false);
  useEffect(() => {
    let interval: any;
    if (isRunning) {
      interval = setInterval(() => setBlink(b => !b), 1000);
    } else {
      setBlink(false);
    }
    return () => clearInterval(interval);
  }, [isRunning]);

  return (
    <Group>
      <Rect width={w} height={h} fill="#bdc3c7" stroke="#34495e" strokeWidth={1} />
      <Text x={0} y={5} width={w} text="EPM" align="center" fill="#2c3e50" fontSize={12} fontFamily="monospace" fontStyle="bold" />

      {/* Power metering representation */}
      <Rect x={w*0.2} y={h*0.3} width={w*0.6} height={h*0.3} fill="#ecf0f1" stroke="#95a5a6" strokeWidth={1} />
      <Text x={0} y={h*0.4} width={w} text="~" align="center" fill="#2c3e50" fontSize={14} />

      <Circle x={w/2} y={h*0.8} radius={4} fill={blink ? "#f1c40f" : "#7f8c8d"} />

      {isFault && (
        <Rect width={w} height={h} fill="transparent" stroke="#e74c3c" strokeWidth={3} />
      )}
    </Group>
  );
};
