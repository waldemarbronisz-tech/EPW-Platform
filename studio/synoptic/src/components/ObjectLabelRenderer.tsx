import React, { useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Group, Rect, Text } from 'react-konva';
import { useStore } from '../store';
import type { SynopticObject } from '../store';
import { getSymbolDefinition } from '../symbols/SymbolRegistry';
import { COLOR_OUTLINE, COLOR_WHITE, FONT_UI, FONT_SIZE_BASE, FONT_SIZE_SMALL } from '../theme/ScadaTheme';

interface ObjectLabelRendererProps {
  obj: SynopticObject;
  onChange: (newAttrs: Partial<SynopticObject>) => void;
}

// feat/appearance-selection-frames commit 1c: the primary line
// (designation) is "etykiety obiektow" - FONT_SIZE_BASE. The
// secondary line (name) is the theme's own literal example of
// FONT_SIZE_SMALL's purpose ("druga linia etykiety").
const PRIMARY_FONT_SIZE = FONT_SIZE_BASE;
const SECONDARY_FONT_SIZE = FONT_SIZE_SMALL;
const PADDING_X = 4;
const PADDING_Y = 2;
const LINE_GAP = 1;
const LINE_HEIGHT_FACTOR = 1.15;

// Bug fix (previous task's spec was wrong): a label is only ever drawn
// from user-entered data. There is no placeholder - an unlabeled symbol
// stays unlabeled. The box is also capped at this width; text that
// doesn't fit wraps onto at most two lines and is ellipsis-truncated
// beyond that (Konva's own wrap+ellipsis, not a hand-rolled line-breaker).
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to, for testability without rendering Konva.
export const LABEL_MAX_WIDTH = 160;

/** No real canvas font metrics at layout time - a character-count estimate, same technique as LabelFrameSymbol. */
function estimateTextWidth(text: string, fontSize: number): number {
  return text.length * fontSize * 0.6;
}

/**
 * The label's actual text content, kept as a standalone pure function so
 * it is testable without rendering Konva. Primary line: designation,
 * shown only when the user has actually typed one - NEVER a fallback to
 * the object's id, the type identifier (e.g. 'electrical.rcd') or the
 * auto-generated, type-derived tag. An object with no designation has no
 * primary line at all. Secondary line: name, shown only when toggled on
 * AND non-empty.
 */
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to, for testability without rendering Konva.
export function resolveObjectLabelText(obj: SynopticObject): { primary: string; secondary: string } {
  const showDesignation = obj.showDesignation !== false;
  const showName = obj.showName !== false;
  return {
    primary: showDesignation ? (obj.designation || '') : '',
    secondary: showName ? (obj.name || '') : ''
  };
}

/**
 * Sizing for one line of label text, capped at LABEL_MAX_WIDTH: the width
 * shrinks to fit short text, and text too wide to fit on one line reserves
 * a second line's worth of height instead (Konva's wrap="word" then
 * actually breaks it there, with ellipsis={true} truncating anything
 * beyond that). Returns zero size for empty text so an unused line takes
 * up no space in the label box.
 */
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to, for testability without rendering Konva.
export function measureLabelLine(text: string, fontSize: number, maxWidth: number): { width: number; height: number; lines: 1 | 2 } {
  if (!text) return { width: 0, height: 0, lines: 1 };
  const estWidth = estimateTextWidth(text, fontSize);
  const lineHeight = fontSize * LINE_HEIGHT_FACTOR;
  const lines = estWidth > maxWidth ? 2 : 1;
  return { width: Math.min(estWidth, maxWidth), height: lineHeight * lines, lines };
}

export const ObjectLabelRenderer: React.FC<ObjectLabelRendererProps> = ({ obj, onChange }) => {
  const groupRef = useRef<any>(null);
  const cancelledRef = useRef(false);
  const [editPos, setEditPos] = useState<{ x: number; y: number; width: number } | null>(null);

  const def = getSymbolDefinition(obj.type);
  if (!def || def.isLine || obj.type.startsWith('graphics.') || obj.type.startsWith('measurements.')) {
    return null;
  }

  const showDesignation = obj.showDesignation !== false;
  const showName = obj.showName !== false;

  if (!showDesignation && !showName) return null;

  const { primary: primaryText, secondary: secondaryText } = resolveObjectLabelText(obj);

  if (!primaryText && !secondaryText) return null;

  const w = def.defaultWidth || 80;
  const h = def.defaultHeight || 80;

  let baseX = 0;
  let baseY = 0;
  let align: 'left' | 'center' | 'right' = 'center';
  const margin = 10;

  const pos = obj.labelPosition || 'BOTTOM';

  // Nominal reference frame the label centers/anchors itself in - capped
  // at LABEL_MAX_WIDTH so a wide symbol doesn't stretch it past the
  // required maximum. For TOP/BOTTOM, baseX is always -boxWidth/2 so this
  // frame stays centered on the symbol's own center (x=0 locally)
  // regardless of how wide it ends up.
  const boxWidth = pos === 'LEFT' || pos === 'RIGHT' ? 80 : Math.min(w * 2, LABEL_MAX_WIDTH);

  if (pos === 'TOP') {
    baseX = -boxWidth / 2;
    baseY = -h / 2 - margin - 20;
    align = 'center';
  } else if (pos === 'BOTTOM') {
    baseX = -boxWidth / 2;
    baseY = h / 2 + margin;
    align = 'center';
  } else if (pos === 'LEFT') {
    baseX = -w - boxWidth - margin;
    baseY = -10;
    align = 'right';
  } else if (pos === 'RIGHT') {
    baseX = w / 2 + margin;
    baseY = -10;
    align = 'left';
  }

  const counterRot = -(obj.rotation || 0);

  const maxTextWidth = boxWidth - PADDING_X * 2;
  const primaryLine = measureLabelLine(primaryText, PRIMARY_FONT_SIZE, maxTextWidth);
  const secondaryLine = measureLabelLine(secondaryText, SECONDARY_FONT_SIZE, maxTextWidth);
  const bgWidth = Math.min(boxWidth, Math.max(primaryLine.width, secondaryLine.width) + PADDING_X * 2);
  const bgHeight =
    PADDING_Y * 2 +
    primaryLine.height +
    (primaryText && secondaryText ? LINE_GAP : 0) +
    secondaryLine.height;

  const commitEdit = (value: string) => {
    setEditPos(null);
    onChange({ designation: value });
    useStore.getState().saveHistory();
  };

  const startEditing = (e: any) => {
    e.cancelBubble = true;
    const stage = e.target.getStage();
    const node = groupRef.current;
    if (!stage || !node) return;

    const rect = node.getClientRect({ relativeTo: stage });
    const containerRect = stage.container().getBoundingClientRect();

    setEditPos({
      x: containerRect.left + rect.x,
      y: containerRect.top + rect.y,
      width: Math.max(rect.width, 60)
    });
  };

  return (
    <>
      <Group
        ref={groupRef}
        x={obj.labelOffsetX !== undefined ? obj.labelOffsetX : baseX}
        y={obj.labelOffsetY !== undefined ? obj.labelOffsetY : baseY}
        rotation={counterRot}
        draggable
        onDragStart={(e) => {
          e.cancelBubble = true;
        }}
        onDragEnd={(e) => {
          e.cancelBubble = true;
          onChange({
            labelOffsetX: e.target.x(),
            labelOffsetY: e.target.y()
          });
          // Repositioning the label is a completed user action - commit it
          // as its own single history entry.
          useStore.getState().saveHistory();
        }}
        onClick={(e) => {
          e.cancelBubble = true;
        }}
        onDblClick={startEditing}
        onDblTap={startEditing}
      >
        {/* Light background with a 1px black outline, so the label reads
            against any background it happens to sit over. */}
        <Rect
          x={align === 'right' ? boxWidth - bgWidth : align === 'center' ? (boxWidth - bgWidth) / 2 : 0}
          y={0}
          width={bgWidth}
          height={bgHeight}
          fill={COLOR_WHITE}
          stroke={COLOR_OUTLINE}
          strokeWidth={1}
        />
        {primaryText && (
          <Text
            x={0}
            y={PADDING_Y}
            width={boxWidth}
            height={primaryLine.height}
            text={primaryText}
            align={align}
            fontSize={PRIMARY_FONT_SIZE}
            fontFamily={FONT_UI}
            lineHeight={LINE_HEIGHT_FACTOR}
            wrap="word"
            ellipsis={true}
            fontStyle="bold"
            fill={COLOR_OUTLINE}
          />
        )}
        {secondaryText && (
          <Text
            x={0}
            y={PADDING_Y + (primaryText ? primaryLine.height + LINE_GAP : 0)}
            width={boxWidth}
            height={secondaryLine.height}
            text={secondaryText}
            align={align}
            fontSize={SECONDARY_FONT_SIZE}
            fontFamily={FONT_UI}
            lineHeight={LINE_HEIGHT_FACTOR}
            wrap="word"
            ellipsis={true}
            fill={COLOR_OUTLINE}
          />
        )}
      </Group>

      {editPos && createPortal(
        <input
          type="text"
          defaultValue={obj.designation || ''}
          autoFocus
          style={{
            position: 'fixed',
            left: editPos.x,
            top: editPos.y,
            width: editPos.width,
            zIndex: 10000,
            fontWeight: 'bold',
            fontSize: PRIMARY_FONT_SIZE,
            fontFamily: FONT_UI,
            border: `1px solid ${COLOR_OUTLINE}`,
            background: COLOR_WHITE,
            color: COLOR_OUTLINE,
            padding: '1px 2px'
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              commitEdit((e.target as HTMLInputElement).value);
            } else if (e.key === 'Escape') {
              e.preventDefault();
              cancelledRef.current = true;
              setEditPos(null);
            }
          }}
          onBlur={(e) => {
            if (cancelledRef.current) {
              cancelledRef.current = false;
              return;
            }
            commitEdit(e.target.value);
          }}
        />,
        document.body
      )}
    </>
  );
};
