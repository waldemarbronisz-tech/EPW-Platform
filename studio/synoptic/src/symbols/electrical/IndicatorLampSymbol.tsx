import React, { useState, useEffect } from 'react';
import { Group, Circle, Rect } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { SYMBOL_STROKE } from '../../theme/ScadaTheme';

export const IndicatorLampSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;
  const radius = Math.min(w, h) / 2;

  const [blinkOn, setBlinkOn] = useState(true);

  useEffect(() => {
    let interval: any;
    if (state === 'BLINK') {
      interval = setInterval(() => setBlinkOn(b => !b), 500);
    } else {
      setBlinkOn(true);
    }
    return () => clearInterval(interval);
  }, [state]);

  const isOn = state === 'ON' || (state === 'BLINK' && blinkOn);
  const isFault = state === 'FAULT';

  const fillColor = isOn ? (obj.fill || 'green') : 'gray';

  return (
    <Group>
      <Circle
        x={w/2}
        y={h/2}
        radius={radius}
        fill={fillColor}
        stroke="#000"
        strokeWidth={SYMBOL_STROKE}
      />

      {isFault && (
        <Rect width={w} height={h} fill="rgba(255, 0, 0, 0.3)" stroke="red" strokeWidth={SYMBOL_STROKE} />
      )}
    </Group>
  );
};
