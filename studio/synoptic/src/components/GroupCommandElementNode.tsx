// Konva rendering for the group command button (feat/control-elements
// commit 2). A fixed-height raised button - COLOR_PANEL fill with a
// classic bevel (light top/left, dark bottom/right edges, the same
// COLOR_BEVEL_LIGHT/COLOR_BEVEL_DARK pair PanelChrome's sibling
// elements never needed but ScadaTheme has always carried) - with its
// own label centered on it. No width-resize handle: this element is
// small and single-purpose enough that a numeric width field in
// Properties (mirrors SignalPanelElementNode.tsx's own convention) is
// enough; see GroupCommandElement.ts's own header for why there is no
// onResize here at all, unlike the meter/signal panel.

import React, { useEffect, useRef } from 'react';
import { Group, Rect, Text, Line } from 'react-konva';
import type { GroupCommandElement } from '../elements/GroupCommandElement';
import { computeGroupCommandHeight } from '../elements/GroupCommandElement';
import { getGroupCommandDanglingMembers } from '../elements/GroupCommandResolver';
import type { Device } from '../project/DeviceSchema';
import { useStore } from '../store';
import { COLOR_PANEL, COLOR_OUTLINE, COLOR_TEXT, COLOR_BEVEL_LIGHT, COLOR_BEVEL_DARK, FONT_UI, FONT_SIZE_BASE } from '../theme/ScadaTheme';

export interface GroupCommandElementNodeProps {
  el: GroupCommandElement;
  devices: Device[];
  isSelected: boolean;
  onSelect: (e?: any) => void;
  onDragEnd: (x: number, y: number) => void;
  onDragStart?: () => void;
  onDragMove?: (x: number, y: number) => void;
  onShapeRef?: (node: any) => void;
}

export const GroupCommandElementNode: React.FC<GroupCommandElementNodeProps> = ({ el, devices, isSelected, onSelect, onDragEnd, onDragStart, onDragMove, onShapeRef }) => {
  const height = computeGroupCommandHeight();
  const groupRef = useRef<any>(null);
  useEffect(() => {
    onShapeRef?.(groupRef.current);
  });

  // Same dedup-by-signature pattern as SignalPanelElementNode.tsx's own
  // dangling-row effect - a dangling member is a warning, raised once
  // per change, never spammed on every re-render.
  const danglingSignatureRef = useRef<string>('');
  useEffect(() => {
    const issues = getGroupCommandDanglingMembers(el, devices);
    const signature = issues.map(i => i.deviceId).join(',');
    if (signature === danglingSignatureRef.current) return;
    danglingSignatureRef.current = signature;
    const buttonName = el.label || el.id;
    issues.forEach(issue => {
      useStore.getState().addMessage(
        `[WARNING] Przycisk grupowy "${buttonName}": aparat "${issue.deviceId}" nie znaleziony lub nie jest typu SWITCHED`
      );
    });
  }, [el, devices]);

  return (
    <Group
      ref={groupRef}
      x={el.x}
      y={el.y}
      draggable
      onClick={onSelect}
      onTap={onSelect}
      onDragStart={() => onDragStart?.()}
      onDragMove={(e) => onDragMove?.(e.target.x(), e.target.y())}
      onDragEnd={(e) => onDragEnd(e.target.x(), e.target.y())}
    >
      <Rect width={el.width} height={height} fill={COLOR_PANEL} stroke={COLOR_OUTLINE} strokeWidth={1} />
      {/* Classic raised-button bevel: light edges top/left, dark edges bottom/right. */}
      <Line points={[1, height - 2, 1, 1, el.width - 1, 1]} stroke={COLOR_BEVEL_LIGHT} strokeWidth={1.5} />
      <Line points={[el.width - 1, 1, el.width - 1, height - 1, 1, height - 1]} stroke={COLOR_BEVEL_DARK} strokeWidth={1.5} />
      <Text
        x={0}
        y={0}
        width={el.width}
        height={height}
        text={el.label || '(brak opisu)'}
        fontSize={FONT_SIZE_BASE}
        fontFamily={FONT_UI}
        fill={COLOR_TEXT}
        align="center"
        verticalAlign="middle"
        ellipsis
        wrap="none"
        padding={4}
      />
      {isSelected && (
        <Rect
          x={-3} y={-3}
          width={el.width + 6}
          height={height + 6}
          stroke={COLOR_OUTLINE}
          strokeWidth={1}
          dash={[4, 3]}
          fill="transparent"
          listening={false}
        />
      )}
    </Group>
  );
};
