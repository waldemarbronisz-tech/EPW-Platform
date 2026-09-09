// SCADA-style symbol 9/9: meter panel. Any number of rows, height computed
// automatically from row count (+ optional title), width fixed. Rows are
// passed in as a plain data parameter for now - wiring this to the device
// registry is a separate, later task.

import React from 'react';
import { Group, Line, Rect, Text } from 'react-konva';
import { COLOR_OUTLINE, COLOR_PANEL, COLOR_VALUE_FIELD, FONT_UI, FONT_VALUE, FONT_SIZE_BASE, FONT_SIZE_TITLE } from '../../theme/ScadaTheme';

// No discrete state machine (rows are arbitrary data), same as the wire
// node and label frame symbols - an empty list documents that fact.
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this state list belongs beside its component.
export const METER_STATES: string[] = [];

export interface MeterRow {
  label: string;
  value: string;
  unit: string;
}

export interface MeterSymbolProps {
  width: number;
  title?: string;
  rows: MeterRow[];
}

const METER_PADDING = 10;
const METER_TITLE_HEIGHT = 24;
const METER_ROW_HEIGHT = 24;
const METER_OUTLINE_WIDTH = 4;      // per this symbol's own spec
const VALUE_FIELD_OUTLINE_WIDTH = 2; // per this symbol's own spec

/** Total panel height for a given row count and whether a title is shown. Never throws, including for zero rows. */
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this helper belongs beside its component.
export function getMeterHeight(rowCount: number, hasTitle: boolean): number {
  const safeRowCount = Math.max(0, rowCount);
  const titlePart = hasTitle ? METER_TITLE_HEIGHT : 0;
  return METER_PADDING * 2 + titlePart + safeRowCount * METER_ROW_HEIGHT;
}

export const MeterSymbol: React.FC<MeterSymbolProps> = ({ width, title, rows }) => {
  const hasTitle = !!title;
  const height = getMeterHeight(rows.length, hasTitle);
  const valueFieldWidth = width * 0.42;
  const valueFieldX = width - METER_PADDING - valueFieldWidth;

  return (
    <Group>
      <Rect x={0} y={0} width={width} height={height} fill={COLOR_PANEL} stroke={COLOR_OUTLINE} strokeWidth={METER_OUTLINE_WIDTH} />

      {hasTitle && (
        <>
          <Text x={METER_PADDING} y={METER_PADDING} width={width - METER_PADDING * 2} text={title} fontSize={FONT_SIZE_TITLE} fontFamily={FONT_UI} fontStyle="bold" align="center" fill={COLOR_OUTLINE} />
          <Line points={[0, METER_PADDING + METER_TITLE_HEIGHT - 6, width, METER_PADDING + METER_TITLE_HEIGHT - 6]} stroke={COLOR_OUTLINE} strokeWidth={1} />
        </>
      )}

      {rows.map((row, i) => {
        const rowY = METER_PADDING + (hasTitle ? METER_TITLE_HEIGHT : 0) + i * METER_ROW_HEIGHT;
        return (
          <Group key={`${row.label}-${i}`}>
            <Text x={METER_PADDING} y={rowY + 4} text={row.label} fontSize={FONT_SIZE_BASE} fontFamily={FONT_UI} fontStyle="bold" fill={COLOR_OUTLINE} />
            <Rect x={valueFieldX} y={rowY} width={valueFieldWidth} height={METER_ROW_HEIGHT - 6} fill={COLOR_VALUE_FIELD} stroke={COLOR_OUTLINE} strokeWidth={VALUE_FIELD_OUTLINE_WIDTH} />
            <Text
              x={valueFieldX}
              y={rowY + 4}
              width={valueFieldWidth - 6}
              text={`${row.value} ${row.unit}`}
              fontSize={FONT_SIZE_BASE}
              fontFamily={FONT_VALUE}
              align="right"
              fill={COLOR_OUTLINE}
            />
          </Group>
        );
      })}
    </Group>
  );
};
