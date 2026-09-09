// Konva rendering for the setpoint panel element (feat/selector-symbol-
// setpoint-alarm). Mirrors MeterElementNode.tsx's own structure closely
// (panel/title/rows, width-only resize, dangling-row warning effect) -
// see that file for the fuller reasoning behind each piece; only what
// is genuinely specific to a WRITABLE point is called out below.
//
// The one deliberate visual difference from the meter's own value
// field: a sunken bevel (dark top/left, light bottom/right) instead of
// a flat outline - the classic Win98 "this is an input, not a
// read-out" cue, the mirror image of GroupCommandElementNode.tsx's own
// raised button bevel (something you press) rather than a new color of
// its own - still every color from ScadaTheme, per this whole
// project's own convention.

import React, { useEffect, useRef } from 'react';
import { Group, Rect, Text, Line } from 'react-konva';
import type { SetpointPanelElement } from '../elements/SetpointElement';
import { computeSetpointHeight, SETPOINT_MIN_WIDTH, SETPOINT_MAX_WIDTH } from '../elements/SetpointElement';
import { computeWidthResizeFromAnchor, getActiveResizeAnchor, setActiveResizeAnchor } from '../utils/ResizeHandles';
import { resolveSetpointRow, getSetpointDanglingRows } from '../elements/SetpointResolver';
import type { Device } from '../project/DeviceSchema';
import { useStore } from '../store';
import { PanelChrome, getPanelRowLayout } from './PanelChrome';
import { PANEL_PADDING_X, PANEL_PADDING_Y } from '../elements/PanelLayout';
import { COLOR_VALUE_FIELD, COLOR_TEXT, COLOR_DE_ENERGIZED, COLOR_ALARM, COLOR_BEVEL_LIGHT, COLOR_BEVEL_DARK, FONT_UI, FONT_VALUE, FONT_SIZE_BASE, GRID_SIZE } from '../theme/ScadaTheme';

const VALUE_FIELD_BEVEL_WIDTH = 2;
const VALUE_FIELD_WIDTH_FRACTION = 0.42; // same fraction the meter's own value field claims
const VALUE_FIELD_INSET_Y = 3;

export interface SetpointElementNodeProps {
  panel: SetpointPanelElement;
  devices: Device[];
  onSelect: (e?: any) => void;
  onDragEnd: (x: number, y: number) => void;
  onDragStart?: () => void;
  onDragMove?: (x: number, y: number) => void;
  onShapeRef?: (node: any) => void;
  onResize?: (x: number, width: number) => void;
}

// Same reasoning as MeterElementNode.tsx's own colorForRow: a preview
// value (not live data) draws in a visibly different shade so it never
// reads as real data for even a second; a dangling device reference
// draws in the alarm color.
function colorForRow(colorKind: 'NORMAL' | 'PREVIEW' | 'MISSING'): string {
  if (colorKind === 'PREVIEW') return COLOR_DE_ENERGIZED;
  if (colorKind === 'MISSING') return COLOR_ALARM;
  return COLOR_TEXT;
}

export const SetpointElementNode: React.FC<SetpointElementNodeProps> = ({ panel, devices, onSelect, onDragEnd, onDragStart, onDragMove, onShapeRef, onResize }) => {
  const fontSize = panel.fontSize || FONT_SIZE_BASE;
  const height = computeSetpointHeight(panel);
  const hasTitle = !!panel.title;
  const { rowHeight, titleBlockHeight } = getPanelRowLayout(fontSize, hasTitle);
  const valueFieldWidth = panel.width * VALUE_FIELD_WIDTH_FRACTION;
  const valueFieldX = panel.width - PANEL_PADDING_X - valueFieldWidth;
  const groupRef = useRef<any>(null);
  useEffect(() => {
    onShapeRef?.(groupRef.current);
  });

  const danglingSignatureRef = useRef<string>('');
  useEffect(() => {
    const issues = getSetpointDanglingRows(panel, devices);
    const signature = issues.map(i => `${i.rowIndex}:${i.deviceId}`).join(',');
    if (signature === danglingSignatureRef.current) return;
    danglingSignatureRef.current = signature;
    const panelName = panel.title || panel.id;
    issues.forEach(issue => {
      useStore.getState().addMessage(
        `[WARNING] Panel nastaw "${panelName}", row ${issue.rowIndex + 1}: device "${issue.deviceId}" not found`
      );
    });
  }, [panel, devices]);

  return (
    <Group
      ref={groupRef}
      x={panel.x}
      y={panel.y}
      draggable
      onClick={onSelect}
      onTap={onSelect}
      onDragStart={() => onDragStart?.()}
      onDragMove={(e) => onDragMove?.(e.target.x(), e.target.y())}
      onDragEnd={(e) => onDragEnd(e.target.x(), e.target.y())}
      onTransformEnd={() => {
        const node = groupRef.current;
        if (!node || !onResize) return;
        const anchor = getActiveResizeAnchor();
        setActiveResizeAnchor(null);
        const rawWidth = panel.width * node.scaleX();
        const resized = anchor && anchor !== 'rotater'
          ? computeWidthResizeFromAnchor(anchor, { x: panel.x, width: panel.width }, rawWidth, GRID_SIZE, SETPOINT_MIN_WIDTH, SETPOINT_MAX_WIDTH)
          : { x: panel.x, width: Math.min(SETPOINT_MAX_WIDTH, Math.max(SETPOINT_MIN_WIDTH, rawWidth)) };
        node.x(resized.x);
        node.scaleX(1);
        node.scaleY(1);
        onResize(resized.x, resized.width);
      }}
    >
      <PanelChrome width={panel.width} height={height} title={panel.title} fontSize={fontSize}>
        {panel.rows.map((row, i) => {
          const rowY = PANEL_PADDING_Y + titleBlockHeight + i * rowHeight;
          const display = resolveSetpointRow(row, devices);
          const fieldY = rowY + VALUE_FIELD_INSET_Y;
          const fieldHeight = rowHeight - VALUE_FIELD_INSET_Y * 2;

          return (
            <Group key={i}>
              <Text
                x={PANEL_PADDING_X}
                y={rowY + (rowHeight - fontSize) / 2}
                width={valueFieldX - PANEL_PADDING_X}
                text={display.label}
                fontSize={fontSize}
                fontFamily={FONT_UI}
                fill={COLOR_TEXT}
                ellipsis
                wrap="none"
              />
              <Rect x={valueFieldX} y={fieldY} width={valueFieldWidth} height={fieldHeight} fill={COLOR_VALUE_FIELD} />
              {/* Sunken bevel: dark top/left, light bottom/right - the
                  mirror image of a raised button (GroupCommandElementNode.tsx),
                  so this reads as "type into me", not "press me". */}
              <Line points={[valueFieldX, fieldY + fieldHeight, valueFieldX, fieldY, valueFieldX + valueFieldWidth, fieldY]} stroke={COLOR_BEVEL_DARK} strokeWidth={VALUE_FIELD_BEVEL_WIDTH} />
              <Line points={[valueFieldX + valueFieldWidth, fieldY, valueFieldX + valueFieldWidth, fieldY + fieldHeight, valueFieldX, fieldY + fieldHeight]} stroke={COLOR_BEVEL_LIGHT} strokeWidth={VALUE_FIELD_BEVEL_WIDTH} />
              <Text
                x={valueFieldX}
                y={rowY + (rowHeight - fontSize) / 2}
                width={valueFieldWidth - 6}
                text={display.valueText}
                fontSize={fontSize}
                fontFamily={FONT_VALUE}
                align="right"
                fill={colorForRow(display.colorKind)}
              />
            </Group>
          );
        })}
      </PanelChrome>
    </Group>
  );
};
