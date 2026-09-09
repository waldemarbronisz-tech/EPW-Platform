import React from 'react';
import { Group, Rect } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

export const CableTraySymbol: React.FC<SymbolProps> = ({ obj }) => {
  const w = obj.width;
  const h = obj.height;

  // Render a ladder-style cable tray segment
  const rungs = [];
  const rungSpacing = 20;
  for(let i = rungSpacing; i < w; i += rungSpacing) {
    rungs.push(<Rect key={i} x={i} y={0} width={2} height={h} fill="#95a5a6" />);
  }

  return (
    <Group>
      <Rect width={w} height={4} y={0} fill="#7f8c8d" />
      <Rect width={w} height={4} y={h-4} fill="#7f8c8d" />
      {rungs}
    </Group>
  );
};
