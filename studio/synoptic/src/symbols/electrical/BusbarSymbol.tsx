import React from 'react';
import { Group, Rect, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';

import { useState, useEffect } from 'react';

export const BusbarSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const isEnergized = state === 'ENERGIZED';
  const isFault = state === 'FAULT';

  const baseColor = isEnergized ? '#e74c3c' : '#7f8c8d';

  const [pulse, setPulse] = useState(1);

  useEffect(() => {
    let animationFrame: number;
    let increasing = true;

    const animate = () => {
      setPulse(p => {
        if (p >= 1) increasing = false;
        if (p <= 0.6) increasing = true;
        return p + (increasing ? 0.02 : -0.02);
      });
      animationFrame = requestAnimationFrame(animate);
    };

    if (isEnergized) {
      animationFrame = requestAnimationFrame(animate);
    } else {
      setPulse(1);
    }

    return () => {
      if (animationFrame) cancelAnimationFrame(animationFrame);
    };
  }, [isEnergized]);

  // A busbar is a thin line (approx 4px) centered in its bounding box.
  // It spans the longest dimension (width or height).
  const isHorizontal = w >= h;

  return (
    <Group>
      {/* Invisible bounding box for easy selection/hover */}
      <Rect width={w} height={h} fill="transparent" />

      {/* The visible busbar line */}
      <Line
        points={isHorizontal ? [0, h/2, w, h/2] : [w/2, 0, w/2, h]}
        stroke={baseColor}
        strokeWidth={4}
        lineCap="square"
      />

      {/* Energy Pulse Overlay */}
      {isEnergized && (
        <Line
          points={isHorizontal ? [0, h/2, w, h/2] : [w/2, 0, w/2, h]}
          stroke="#f1c40f"
          strokeWidth={4}
          lineCap="square"
          opacity={pulse * 0.8}
        />
      )}

      {isFault && (
        <Line
          points={isHorizontal ? [0, h/2, w, h/2] : [w/2, 0, w/2, h]}
          stroke="#c0392b"
          strokeWidth={6}
          lineCap="square"
          dash={[4, 4]}
        />
      )}
    </Group>
  );
};
