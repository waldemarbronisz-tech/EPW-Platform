// EPW Studio's one icon look, in the Synoptic editor.
//
// Every icon in EPW Studio is the same 16 x 16 pixel pictogram on a raised
// tile - the Studio shell toolbar, Logic Studio's toolbars and this editor's
// own bars all show the same pictures. The pixels come from the shell's
// generated PNGs (studio/shell/icons/generate_icons.py writes
// studioIconData.ts next to this file), drawn as crisp SVG rectangles so
// they stay sharp at any display scaling.

import React, { useMemo } from 'react';
import { STUDIO_ICONS } from './studioIconData';

type Run = [x: number, y: number, width: number, color: string];

const parsed = new Map<string, Run[]>();

function runsFor(name: string): Run[] {
  const cached = parsed.get(name);
  if (cached) return cached;
  const runs: Run[] = (STUDIO_ICONS[name] || '')
    .split(';')
    .filter(Boolean)
    .map(part => {
      const [x, y, w, c] = part.split(',');
      return [Number(x), Number(y), Number(w), `#${c}`];
    });
  parsed.set(name, runs);
  return runs;
}

export const StudioIcon: React.FC<{ name: string; size?: number }> = ({ name, size = 16 }) => {
  const runs = useMemo(() => runsFor(name), [name]);
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" shapeRendering="crispEdges" aria-hidden="true">
      {runs.map(([x, y, w, color], i) => (
        <rect key={i} x={x} y={y} width={w} height={1} fill={color} />
      ))}
    </svg>
  );
};
