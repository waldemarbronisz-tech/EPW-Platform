import React from 'react';
import { Group, Rect, Path, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { SYMBOL_STROKE } from '../../theme/ScadaTheme';

export const HeaterSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isHeating = state === 'HEATING';
  const isFault = state === 'FAULT';

  return (
    <Group>
      {/* Outer casing */}
      <Rect width={w} height={h} fill="#bdc3c7" stroke="#7f8c8d" strokeWidth={SYMBOL_STROKE} cornerRadius={4} />

      {/* Grill / Heating elements */}
      <Rect x={w*0.1} y={h*0.2} width={w*0.8} height={h*0.6} fill="#34495e" />

      <Line points={[w*0.2, h*0.3, w*0.8, h*0.3]} stroke={isHeating ? "#e74c3c" : "#95a5a6"} strokeWidth={SYMBOL_STROKE} />
      <Line points={[w*0.2, h*0.5, w*0.8, h*0.5]} stroke={isHeating ? "#e74c3c" : "#95a5a6"} strokeWidth={SYMBOL_STROKE} />
      <Line points={[w*0.2, h*0.7, w*0.8, h*0.7]} stroke={isHeating ? "#e74c3c" : "#95a5a6"} strokeWidth={SYMBOL_STROKE} />

      {/* Heat waves indication if active */}
      {isHeating && (
        <Group>
           <Path data={`M ${w*0.3} -10 Q ${w*0.4} -20 ${w*0.3} -30`} stroke="#e74c3c" strokeWidth={SYMBOL_STROKE} />
           <Path data={`M ${w*0.5} -10 Q ${w*0.6} -20 ${w*0.5} -30`} stroke="#e74c3c" strokeWidth={SYMBOL_STROKE} />
           <Path data={`M ${w*0.7} -10 Q ${w*0.8} -20 ${w*0.7} -30`} stroke="#e74c3c" strokeWidth={SYMBOL_STROKE} />
        </Group>
      )}

      {isFault && (
        <Rect width={w} height={h} fill="transparent" stroke="#c0392b" strokeWidth={SYMBOL_STROKE} cornerRadius={4} />
      )}
    </Group>
  );
};
