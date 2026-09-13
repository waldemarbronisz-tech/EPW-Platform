// feat/room-plan: fluorescent batten (oprawa jarzeniowa), plan view.
//
// The one luminaire whose SHAPE carries information: it is long, and
// which way it runs matters for how a workshop or garage is lit. Drawn
// as the batten body with the tube(s) inside it - two tubes, the common
// 2 x 36 W fitting - so a lit one reads as a bar of light rather than a
// rectangle that changed colour.
//
// Scale: 120 x 17 cm (Scale.ts) - a real 4 ft batten. Resize it along
// its length for a 60 cm or 150 cm fitting; the tubes follow the body.

import React from 'react';
import { Group, Line, Rect } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { COLOR_OUTLINE, FITTING_BODY, FITTING_BODY_DARK, LIT, symbolStroke } from './BuildingSymbolTheme';

export const FluorescentLuminaireSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;
  const stroke = symbolStroke(w, h);
  const isOn = state === 'ON';

  // Tubes run the long way, whichever way that is - a batten rotated to
  // stand vertical must not end up with tubes across it.
  const horizontal = w >= h;
  const inset = h * 0.22;

  const tube = (offset: number) => (horizontal
    ? [stroke * 1.5, offset, w - stroke * 1.5, offset]
    : [offset, stroke * 1.5, offset, h - stroke * 1.5]);

  const firstTube = horizontal ? inset + h * 0.14 : inset + w * 0.14;
  const secondTube = horizontal ? h - inset - h * 0.14 : w - inset - w * 0.14;
  const tubeWidth = (horizontal ? h : w) * 0.18;

  return (
    <Group>
      {/* The lit spread is a long soft band, matching the fitting. */}
      {isOn && (
        <Rect
          x={-w * 0.12} y={-h * 0.9}
          width={w * 1.24} height={h * 2.8}
          fill={LIT} opacity={0.16} cornerRadius={h * 0.5}
          listening={false}
        />
      )}
      <Rect
        width={w} height={h}
        fill={isOn ? '#FFF6C4' : FITTING_BODY}
        stroke={COLOR_OUTLINE} strokeWidth={stroke}
        cornerRadius={Math.min(w, h) * 0.12}
      />
      <Line points={tube(firstTube)} stroke={isOn ? LIT : FITTING_BODY_DARK} strokeWidth={tubeWidth} lineCap="round" listening={false} />
      <Line points={tube(secondTube)} stroke={isOn ? LIT : FITTING_BODY_DARK} strokeWidth={tubeWidth} lineCap="round" listening={false} />
    </Group>
  );
};
