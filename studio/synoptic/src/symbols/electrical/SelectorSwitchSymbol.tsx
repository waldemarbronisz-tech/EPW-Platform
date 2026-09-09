// feat/selector-symbol-setpoint-alarm: the schematic symbol a SELECTOR
// device (DeviceSchema.ts) can actually be placed as - closing a gap
// left over from that behavior's own first commit, where the device
// itself became fully configurable in the device list with nothing to
// draw on the diagram. A classic 3-position rotary selector knob
// (Hand-Off-Auto, Local-Remote, ...), same drawing conventions as this
// folder's own DisconnectSwitchSymbol.tsx (plain Konva primitives,
// inline hex colors, a dashed-outline FAULT overlay).
//
// This is a PICTOGRAM, not a live readout: like every other symbol in
// this registry, it has no idea what device (if any) it is bound to -
// "Aparat" binding and symbol appearance are deliberately independent
// (see PropertyInspector.tsx's own comment on that). LEFT/CENTER/RIGHT
// are generic positions an engineer picks from the Properties panel's
// preview-state dropdown, not the actual named positions configured on
// a specific SELECTOR device (those live in the device form only).

import React from 'react';
import { Group, Rect, Circle, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { SYMBOL_STROKE } from '../../theme/ScadaTheme';

// Exported so its own invariant (LEFT/RIGHT symmetric around a
// straight-up CENTER) is directly testable without a Konva rendering
// harness - this codebase has none (see raport.md), so a pure constant
// like this is the only piece of a pictogram symbol that CAN be unit
// tested at all (matches DisconnectSwitchSymbol.tsx's own sibling
// components, none of which export anything to test either, having
// nothing this simple to check).
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this constant belongs beside its component.
export const POSITION_ANGLE_DEG: Record<string, number> = { LEFT: -40, CENTER: 0, RIGHT: 40 };

export const SelectorSwitchSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;
  const cx = w / 2;
  const cy = h / 2;
  const radius = Math.min(w, h) * 0.32;
  const isFault = state === 'FAULT';
  const angleDeg = POSITION_ANGLE_DEG[state] ?? POSITION_ANGLE_DEG.CENTER;

  // 0 degrees points straight up; positive angles rotate clockwise
  // (RIGHT), negative counter-clockwise (LEFT) - same convention a
  // clock face or a compass needle uses.
  const tip = (r: number, deg: number) => {
    const rad = (deg * Math.PI) / 180;
    return { x: cx + r * Math.sin(rad), y: cy - r * Math.cos(rad) };
  };

  const pointerTip = tip(radius * 0.9, angleDeg);

  return (
    <Group>
      {/* Invisible hitbox, same convention as DisconnectSwitchSymbol.tsx */}
      <Rect width={w} height={h} fill="transparent" />

      {/* Lead from the symbol's own terminal (TOP) down to the knob body */}
      <Line points={[cx, 0, cx, cy - radius]} stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />

      {/* Knob body */}
      <Circle x={cx} y={cy} radius={radius} fill="#ecf0f1" stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />

      {/* Three position tick marks - always drawn regardless of state,
          exactly like a real selector's fixed panel markings never
          change with the knob itself. */}
      {Object.values(POSITION_ANGLE_DEG).map(deg => {
        const from = tip(radius * 1.05, deg);
        const to = tip(radius * 1.35, deg);
        return <Line key={deg} points={[from.x, from.y, to.x, to.y]} stroke="#2c3e50" strokeWidth={SYMBOL_STROKE * 0.6} />;
      })}

      {/* The pointer itself - which position this instance previews */}
      <Line points={[cx, cy, pointerTip.x, pointerTip.y]} stroke="#2c3e50" strokeWidth={SYMBOL_STROKE} />
      <Circle x={cx} y={cy} radius={radius * 0.12} fill="#2c3e50" />

      {isFault && (
        <Rect x={w * 0.05} y={h * 0.05} width={w * 0.9} height={h * 0.9} stroke="#e74c3c" strokeWidth={SYMBOL_STROKE} dash={[4, 2]} />
      )}
    </Group>
  );
};
