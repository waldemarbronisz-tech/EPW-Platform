// feat/room-plan: flush ceiling luminaire (plafon), plan view.
//
// Why a separate symbol from electrical.indicator_lamp: that one is a
// panel signal lamp (a filled circle meaning "this state is true") on a
// single-line schematic. This is a light FITTING seen from above,
// placed inside a room outline - a different drawing, in a different
// kind of drawing. Both keep their meaning; neither is a worse version
// of the other.
//
// Drawn as a real fitting rather than as the bare crossed circle of the
// textbook plan symbol: the trim ring, the diffuser inside it, and four
// short marks on the rim. The cross alone is unambiguous on a printed
// plan, but on a lit, shaded, coloured screen drawing it read as a
// crosshair - a target, not a lamp.
//
// Scale: 30 cm (Scale.ts).
//
// NO TERMINALS, deliberately - see registry/building.ts's own header.
// A luminaire is energized by its CIRCUIT (obj.circuit), never by a
// wire touching it.

import React from 'react';
import { Circle, Group, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { COLOR_OUTLINE, FITTING_BODY, FITTING_BODY_DARK, LIT, symbolStroke } from './BuildingSymbolTheme';

export type LuminaireState = 'ON' | 'OFF';
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this state list belongs beside its component.
export const LUMINAIRE_STATES: LuminaireState[] = ['ON', 'OFF'];

export const LuminaireSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;
  const cx = w / 2;
  const cy = h / 2;
  // Stroke scales with the symbol: the platform's own SYMBOL_STROKE (5)
  // is sized for the large schematic glyphs and swallows a 24 px plan
  // fitting whole - seen on a real render, where a lit luminaire came
  // out as a near-black blob.
  const stroke = symbolStroke(w, h);
  const trim = Math.min(w, h) / 2 - stroke / 2;
  const diffuser = trim * 0.72;
  const isOn = state === 'ON';

  return (
    <Group>
      {isOn && (
        <Circle x={cx} y={cy} radius={trim * 1.9} fill={LIT} opacity={0.24} listening={false} />
      )}
      {/* Trim ring. */}
      <Circle
        x={cx} y={cy} radius={trim}
        fill={FITTING_BODY}
        stroke={COLOR_OUTLINE} strokeWidth={stroke}
      />
      {/* Diffuser - the part that actually lights up. */}
      <Circle
        x={cx} y={cy} radius={diffuser}
        fill={isOn ? LIT : FITTING_BODY_DARK}
        stroke={COLOR_OUTLINE} strokeWidth={stroke * 0.6}
      />
      {/* Four rim marks: the fixing points, and what keeps a trace of
          the conventional crossed-circle reading. */}
      {[0, 90, 180, 270].map(angle => {
        const rad = (angle * Math.PI) / 180;
        return (
          <Line
            key={angle}
            points={[
              cx + Math.cos(rad) * diffuser, cy + Math.sin(rad) * diffuser,
              cx + Math.cos(rad) * trim, cy + Math.sin(rad) * trim,
            ]}
            stroke={COLOR_OUTLINE}
            strokeWidth={stroke * 0.7}
            listening={false}
          />
        );
      })}
    </Group>
  );
};
