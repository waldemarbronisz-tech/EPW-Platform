// feat/room-plan: recessed halogen downlight (halogen / oczko), plan view.
//
// The smallest fitting on the plan, and deliberately so - at 17 cm it
// is barely more than a ring with a lamp in it, which is exactly what a
// downlight looks like from below. Drawn as the trim ring plus the lamp
// face, with a tight pool when lit: a downlight throws a narrow cone,
// unlike the pendant's wide spread, and the plan should show that
// difference rather than giving every luminaire the same halo.
//
// Scale: 17 cm trim (Scale.ts).

import React from 'react';
import { Circle, Group } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { COLOR_OUTLINE, FITTING_BODY, FITTING_BODY_DARK, LIT, symbolStroke } from './BuildingSymbolTheme';

export const HalogenLuminaireSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;
  const cx = w / 2;
  const cy = h / 2;
  const stroke = symbolStroke(w, h);
  const trim = Math.min(w, h) / 2 - stroke / 2;
  const isOn = state === 'ON';

  return (
    <Group>
      {isOn && (
        <Circle x={cx} y={cy} radius={trim * 2.4} fill={LIT} opacity={0.24} listening={false} />
      )}
      {/* Trim ring. */}
      <Circle
        x={cx} y={cy} radius={trim}
        fill={FITTING_BODY}
        stroke={COLOR_OUTLINE} strokeWidth={stroke}
      />
      {/* Lamp face, inset inside the trim. */}
      <Circle
        x={cx} y={cy} radius={trim * 0.58}
        fill={isOn ? LIT : FITTING_BODY_DARK}
        stroke={COLOR_OUTLINE} strokeWidth={stroke * 0.6}
      />
    </Group>
  );
};
