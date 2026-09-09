import React from 'react';
import { Group, Rect, Text } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { COLOR_PANEL, COLOR_OUTLINE, COLOR_VALUE_FIELD, COLOR_TEXT, COLOR_ALARM, FONT_UI, FONT_VALUE, FONT_SIZE_BASE, FONT_SIZE_SMALL } from '../../theme/ScadaTheme';

// Bug fix: this legacy symbol still painted its own pre-SCADA colors
// (dark bezel, black LED background, green phosphor text) instead of the
// retro-industrial palette every other symbol now uses. Colors only -
// same rects, same value/format logic, same fault indicator, unchanged.
const PANEL_OUTLINE_WIDTH = 4;       // per this symbol's own spec, matches MeterSymbol's convention
const LABEL_OUTLINE_WIDTH = 1;
const VALUE_FIELD_OUTLINE_WIDTH = 2; // per this symbol's own spec
const FAULT_OUTLINE_WIDTH = 3;

export const MeasurementDisplaySymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;

  const value = obj.editor?.preview_value || "---";
  const unit = obj.editor?.unit || "";
  const format = obj.editor?.format || "";

  // Attempt formatting if possible and value is numeric
  let displayString = `${value} ${unit}`;

  if (format && !isNaN(Number(value))) {
    try {
      const num = Number(value);
      if (format.includes(".")) {
         const decimals = format.split(".")[1].length;
         displayString = `${num.toFixed(decimals)} ${unit}`;
      }
    } catch {
      // fallback
    }
  }

  const isFault = state === 'FAULT';

  return (
    <Group>
      {/* Flat panel background with a black outline - retro SCADA palette, no bezel/gradient. */}
      <Rect width={w} height={h} fill={COLOR_PANEL} stroke={COLOR_OUTLINE} strokeWidth={PANEL_OUTLINE_WIDTH} />

      {/* Label area (top) */}
      <Rect x={4} y={4} width={w-8} height={14} fill={COLOR_PANEL} stroke={COLOR_OUTLINE} strokeWidth={LABEL_OUTLINE_WIDTH} />
      <Text
        x={6} y={6}
        width={w-12} height={10}
        text={obj.tag || obj.text || "SENSOR"}
        fontSize={FONT_SIZE_SMALL}
        fontFamily={FONT_UI}
        fill={COLOR_TEXT}
        align="center"
      />

      {/* Value field area - fixed-width font, per the SCADA value-field convention. */}
      <Rect x={4} y={20} width={w-8} height={h-24} fill={COLOR_VALUE_FIELD} stroke={COLOR_OUTLINE} strokeWidth={VALUE_FIELD_OUTLINE_WIDTH} />
      <Text
        x={8} y={24}
        width={w-16} height={h-32}
        text={displayString}
        fontSize={FONT_SIZE_BASE}
        fontFamily={FONT_VALUE}
        fill={COLOR_TEXT}
        align="right"
        verticalAlign="middle"
      />

      {isFault && (
        <Rect width={w} height={h} fill="transparent" stroke={COLOR_ALARM} strokeWidth={FAULT_OUTLINE_WIDTH} />
      )}
    </Group>
  );
};
