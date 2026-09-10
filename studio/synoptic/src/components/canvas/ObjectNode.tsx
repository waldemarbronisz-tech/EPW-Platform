// Internal-audit fix (Canvas.tsx breakup): moved out of Canvas.tsx
// verbatim, comments included - see that file's own history for context.
// This was one of five components Canvas.tsx defined at module scope
// before ever getting to the ~1000-line Canvas component itself; pulling
// them into their own files (this one, ConnectionNode.tsx,
// TransformerHandles.tsx) is a pure move, no behavior change.
import { useEffect, useRef, useState } from 'react';
import { Circle, Group, Rect } from 'react-konva';
import { useStore } from '../../store';
import type { SynopticObject } from '../../store';
import { SymbolRenderer } from '../../symbols/SymbolRenderer';
import { COLOR_OUTLINE, COLOR_WATER, TERMINAL_DIMMED_COLOR, TERMINAL_HIGHLIGHT_COLOR, TERMINAL_RADIUS, TERMINAL_RADIUS_HIGHLIGHTED } from '../../theme/ScadaTheme';
import { snapValue } from '../../utils/GridSnap';
import { getObjectTerminals } from '../../utils/Terminals';
import { getHoverHitRect } from '../../utils/TerminalReach';
import { areMediaCompatible } from '../../project/NetResolver';
import type { Medium } from '../../project/NetResolver';
import { computeResizeFromAnchor, getActiveResizeAnchor, setActiveResizeAnchor } from '../../utils/ResizeHandles';
import { isAltKeyDown } from '../../utils/CanvasInputState';
import { describeObject } from '../../utils/ObjectDisplay';
import type { DragKey, GroupDragApi } from './types';

// feat/device-form-from-canvas: double-click on a symbol opens its own
// device's configuration form - a THIRD, separate double-click meaning
// on the canvas, alongside Canvas.tsx's own wire-finish (attached to
// the Stage) and ObjectLabelRenderer.tsx's own edit-in-place (attached
// to the label's own, structurally unrelated Group - labels render in
// a completely separate pass/Konva subtree, see Canvas.tsx's own
// "Layer 6, labels" comment, so a click there never reaches this
// handler at all). The one real overlap to guard is the wire tool: a
// double-click that lands on a symbol WHILE the wire tool is armed
// must still finish the wire, not open a form - checked first, and
// deliberately conservative (skips this handler whenever the tool is
// armed at all, not only mid-polyline, since Canvas.tsx's own
// drawingPointsRef is a local ref this component has no access to
// anyway - erring towards "let the existing, tested behavior win"
// rather than trying to special-case "armed but not yet started").
//
// fix/inline-device-creation commit 3: a device-less symbol used to
// just post a Messages notice here (feat/device-form-from-canvas commit
// 1) - it now opens DeviceFormDialog's own "create or assign" mode
// instead (openDeviceCreateOrAssignForm), carrying the symbol's own id
// and type for the behavior/id/designation suggestions and for the
// PRZYPISZ ISTNIEJACY device list's own behavior pre-filter.
// oxlint-disable-next-line react/only-export-components -- kept beside the component it belongs to, for testability without rendering Konva (same convention ObjectLabelRenderer.tsx's own resolveObjectLabelText/measureLabelLine already use).
export function handleSymbolDblClick(e: { cancelBubble: boolean }, obj: SynopticObject) {
  if (useStore.getState().isDrawingConnection) return;
  e.cancelBubble = true;
  if (!obj.deviceId) {
    useStore.getState().openDeviceCreateOrAssignForm(obj.id, obj.type, `Diagram, symbol ${describeObject(obj)}`);
    return;
  }
  useStore.getState().openDeviceForm(obj.deviceId, `Diagram, symbol ${describeObject(obj)}`);
}

// isSelected is no longer a prop here (commit 5) - the Transformer that
// used to read it moved out to its own top-level pass (
// ObjectTransformerHandle, in TransformerHandles.tsx) and nothing else in
// this component's own rendering depends on selection state.
export const ObjectNode = ({ obj, onSelect, onChange, gridSize, onShapeRef, groupDrag, forceShowTerminals, highlightedTerminalId, drawingMedium }: {
  gridSize: number,
  obj: SynopticObject,
  // Receives the raw Konva event (onClick={onSelect} forwards it
  // positionally) so the caller can read Shift for multi-select - see
  // Canvas.tsx's own call site.
  onSelect: (e?: any) => void,
  onChange: (newAttrs: Partial<SynopticObject>) => void,
  // Layers (commit 5): the Transformer for a selected object is no
  // longer rendered here - it moves to its own top-level pass
  // (ObjectTransformerHandle) so a selection's resize handles always
  // draw ABOVE every symbol, never just above this one object's own.
  // This reports the Group's own Konva node up to Canvas so that later
  // pass can still attach a Transformer to it.
  onShapeRef: (id: string, node: any) => void,
  groupDrag: GroupDragApi,
  // fix/wiring-and-library-groups commit 1, usterka 1d: while the wire
  // tool is armed, Canvas.tsx computes which objects have a terminal
  // within WIRE_NEARBY_TERMINAL_RADIUS of the live cursor - this object
  // shows its terminals whenever it is one of them, with no individual
  // hover needed at all. Both optional/undefined outside wire-drawing
  // mode (every other caller of ObjectNode - there is only one - simply
  // omits them, same as any other optional prop).
  forceShowTerminals?: boolean,
  // usterka 1e/1f: which of THIS object's own terminals (if any) is the
  // one the cursor/magnetism would actually hit right now - drawn
  // bigger, in a different color, so the user knows before clicking.
  highlightedTerminalId?: string | null,
  // feat/tank-language-and-media commit 1: the medium of the wire
  // currently being drawn, or undefined/null when the wire tool is not
  // armed at all. Any of THIS object's own terminals whose medium
  // differs draws dimmed instead - never highlighted, regardless of
  // highlightedTerminalId (Canvas.tsx's own medium-aware search never
  // picks one anyway, but this stays correct even if it somehow did).
  drawingMedium?: Medium | null,
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const shapeRef = useRef<any>(null);
  const dragKey: DragKey = `obj:${obj.id}`;

  useEffect(() => {
    onShapeRef(obj.id, shapeRef.current);
    groupDrag.registerNode(dragKey, shapeRef.current);
  });

  // Node-based wiring model: a symbol has terminals now, not ports - see
  // utils/Terminals.ts. The old click-a-port-to-drag-a-wire interaction
  // (onPortMouseDown/Up/Click, the busbar's dynamic-port onMouseUp
  // special case) is gone entirely; a terminal is purely a visual hint
  // now (shown on hover, or forced while the wire tool is nearby - see
  // TerminalReach.ts) of where a freehand-drawn wire actually needs to
  // end to connect - simply sharing that grid point.
  const terminals = getObjectTerminals(obj);
  const showTerminals = isHovered || !!forceShowTerminals;
  // usterka 1a/1b/1c: the Group's own hover hit-test used to be the
  // UNION OF ITS CHILDREN'S OWN DRAWN INK (Konva's default, per-shape
  // hit canvas) - a terminal dot sits ON a symbol's own edge and often
  // pokes past whatever thin strokes actually get drawn there, so
  // moving the cursor TOWARD a dot routinely left the real hit area
  // before the cursor ever reached it. This invisible Rect, padded well
  // past every terminal on every side (getHoverHitRect/
  // TERMINAL_HOVER_MARGIN), replaces that with one generous, uniform
  // hit area for the whole symbol - the same "invisible full-bounds
  // Rect as the actual hit source" fix DripLineSymbol.tsx's own
  // clickability bug used (feat/water-management), applied here at the
  // ObjectNode level so every symbol gets it, not just one.
  const hoverRect = getHoverHitRect(obj.width, obj.height);

  return (
      <Group
        ref={shapeRef}
        x={obj.x}
        y={obj.y}
        rotation={obj.rotation || 0}
        scaleX={obj.scaleX || 1}
        scaleY={obj.scaleY || 1}
        draggable={!obj.locked}
        visible={obj.visible !== false}
        onClick={onSelect}
        onTap={onSelect}
        onDblClick={(e) => handleSymbolDblClick(e, obj)}
        onDblTap={(e) => handleSymbolDblClick(e, obj)}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onDragStart={() => {
          // Alt+drag (commit 2): a copy is left behind at THIS exact
          // spot the instant the drag starts, unselected and with no
          // history entry of its own - the object actually under the
          // cursor then keeps moving as an ordinary drag would, so the
          // eventual onDragEnd's saveHistory() covers the new copy and
          // the move together as one undo step.
          if (isAltKeyDown()) {
            useStore.getState().duplicateObjectInPlace(obj.id);
          }
          groupDrag.start(dragKey);
        }}
        onDragMove={(e) => {
          // Snap during drag for visual feedback (doesn't mutate store yet).
          // Held Alt bypasses this exactly as it bypasses the final snap
          // on release, so the preview matches where the object will land.
          const snappedX = snapValue(e.target.x(), gridSize, isAltKeyDown());
          const snappedY = snapValue(e.target.y(), gridSize, isAltKeyDown());
          e.target.x(snappedX);
          e.target.y(snappedY);
          if (groupDrag.isActive()) {
            groupDrag.follow(snappedX - obj.x, snappedY - obj.y);
          }
        }}
        onDragEnd={(e) => {
          const finalX = snapValue(e.target.x(), gridSize, isAltKeyDown());
          const finalY = snapValue(e.target.y(), gridSize, isAltKeyDown());
          if (groupDrag.isActive()) {
            // The whole selection moves together, one history entry
            // (moveSelectionBy's own) - not this object's own onChange.
            groupDrag.commit(finalX - obj.x, finalY - obj.y);
          } else {
            // Push final position, then commit exactly one history entry
            // for the whole drag (updateObject itself no longer touches
            // history).
            onChange({ x: finalX, y: finalY });
            useStore.getState().saveHistory();
          }
        }}
        onTransformEnd={() => {
          const node = shapeRef.current;
          const anchor = getActiveResizeAnchor();
          setActiveResizeAnchor(null);

          // fix/handles-insert-mode-diodes commit 1: a genuine resize
          // (one of the 8 corner/edge anchors, not the rotate handle)
          // goes through computeResizeFromAnchor - grid-snapped,
          // minimum-clamped (GRID_SIZE, the closest this app has to a
          // universal "a symbol's own minimum" - no dedicated constant
          // exists for symbols the way FRAME_MIN_SIZE/METER_MIN_WIDTH
          // do), and guaranteed to keep the OPPOSITE corner/edge fixed
          // by construction. Only handled for an unrotated object - see
          // this file's own note above computeResizeFromAnchor's import
          // for why a rotated resize falls back to the older,
          // independently-snapped x/y instead.
          if (anchor && anchor !== 'rotater' && !(obj.rotation || 0)) {
            const rawWidth = obj.width * node.scaleX();
            const rawHeight = obj.height * node.scaleY();
            const resized = computeResizeFromAnchor(
              anchor,
              { x: obj.x, y: obj.y, width: obj.width, height: obj.height },
              rawWidth, rawHeight, gridSize, gridSize, gridSize, !isAltKeyDown()
            );
            // Konva's own Transformer mutates this node's x/y/scaleX/
            // scaleY directly and imperatively while the drag is live -
            // when the committed value happens to equal what it already
            // was (the fixed corner, by design, usually does), React
            // sees no prop change and never re-applies it, leaving
            // Konva's own live-drag value on screen instead of the
            // value just committed to the store. Set explicitly so the
            // node's on-screen state can never drift from the store's.
            const newScaleX = resized.width / obj.width;
            const newScaleY = resized.height / obj.height;
            node.x(resized.x);
            node.y(resized.y);
            node.scaleX(newScaleX);
            node.scaleY(newScaleY);
            onChange({
              x: resized.x,
              y: resized.y,
              rotation: 0,
              scaleX: newScaleX,
              scaleY: newScaleY,
            });
            useStore.getState().saveHistory();
            return;
          }

          const scaleX = node.scaleX();
          const scaleY = node.scaleY();

          onChange({
            x: snapValue(node.x(), gridSize, isAltKeyDown()),
            y: snapValue(node.y(), gridSize, isAltKeyDown()),
            rotation: node.rotation(),
            scaleX: Math.max(0.1, scaleX),
            scaleY: Math.max(0.1, scaleY),
          });
          useStore.getState().saveHistory();
        }}
      >
        {/* usterka 1a/1b/1c: an invisible hit area, padded past every
            terminal in every direction - see this component's own
            comment above hoverRect. Listens (no listening={false}) so
            it is what actually keeps onMouseEnter/onMouseLeave (and
            ordinary clicks) firing while the cursor crosses it; fully
            transparent, so it changes nothing about how the symbol
            looks. First child, purely so it never visually overlaps
            anything drawn on top of it (moot either way, since it is
            invisible - kept first for the same "background first"
            convention DripLineSymbol.tsx's own hit rect already set). */}
        <Rect x={hoverRect.x} y={hoverRect.y} width={hoverRect.width} height={hoverRect.height} fill="transparent" />

        <SymbolRenderer obj={obj} />

        {/* Terminals: shown on hover, OR forced by Canvas.tsx while the
            wire tool is armed and this object has one within reach of
            the cursor (usterka 1d). The one matching
            highlightedTerminalId (usterka 1e/1f - the terminal the
            cursor/magnetism would actually hit right now) draws bigger,
            in a different color, than the rest.
            feat/tank-language-and-media commit 1: a terminal whose own
            medium differs from the wire currently being drawn is
            "wygaszony" - dimmed, and never eligible to be the
            highlighted one (Canvas.tsx's own medium-aware search never
            hands us its id anyway, but this stays correct regardless). */}
        {showTerminals && terminals.map((t) => {
          const incompatible = !!drawingMedium && !areMediaCompatible(t.medium, drawingMedium);
          const isHighlighted = !incompatible && !!highlightedTerminalId && t.id === highlightedTerminalId;
          return (
            <Circle
              key={`term-${t.id}`}
              x={t.x}
              y={t.y}
              radius={isHighlighted ? TERMINAL_RADIUS_HIGHLIGHTED : TERMINAL_RADIUS}
              fill={incompatible ? TERMINAL_DIMMED_COLOR : (isHighlighted ? TERMINAL_HIGHLIGHT_COLOR : COLOR_WATER)}
              stroke={COLOR_OUTLINE}
              strokeWidth={1}
              listening={false}
            />
          );
        })}
      </Group>
  );
};
