// feat/room-plan: pendant luminaire (oprawa wiszaca), plan view.
//
// Seen from above a pendant is its shade - a disc - with the lamp and
// its drop cable at the centre. The two concentric circles are what
// separate it from the flush ceiling fitting: there is a rim above and
// a smaller body below it. Lit, the inner body fills with lamp yellow
// and a soft halo spreads under the shade.
//
// Scale: 35 cm shade (Scale.ts).

import React from 'react';
import { Circle, Group, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { COLOR_OUTLINE, FITTING_BODY, FITTING_BODY_DARK, LIT, symbolStroke } from './BuildingSymbolTheme';

export const PendantLuminaireSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;
  const cx = w / 2;
  const cy = h / 2;
  const stroke = symbolStroke(w, h);
  const outer = Math.min(w, h) / 2 - stroke / 2;
  const inner = outer * 0.52;
  const isOn = state === 'ON';

  return (
    <Group>
      {isOn && (
        <Circle x={cx} y={cy} radius={outer * 1.5} fill={LIT} opacity={0.22} listening={false} />
      )}
      {/* The shade, seen from above. */}
      <Circle
        x={cx} y={cy} radius={outer}
        fill={isOn ? '#FFF3B0' : FITTING_BODY}
        stroke={COLOR_OUTLINE} strokeWidth={stroke}
      />
      {/* Four struts from the rim to the body - the detail that makes
          this read as a hanging fitting rather than a plain disc. */}
      {[0, 90, 180, 270].map(angle => {
        const rad = (angle * Math.PI) / 180;
        return (
          <Line
            key={angle}
            points={[cx + Math.cos(rad) * inner, cy + Math.sin(rad) * inner,
                     cx + Math.cos(rad) * outer, cy + Math.sin(rad) * outer]}
            stroke={FITTING_BODY_DARK}
            strokeWidth={stroke * 0.7}
            listening={false}
          />
        );
      })}
      {/* The lamp itself. */}
      <Circle
        x={cx} y={cy} radius={inner}
        fill={isOn ? LIT : FITTING_BODY_DARK}
        stroke={COLOR_OUTLINE} strokeWidth={stroke * 0.8}
      />
    </Group>
  );
};
