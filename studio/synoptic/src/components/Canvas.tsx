import React, { useRef, useEffect, useState } from 'react';
import { Stage, Layer, Rect, Circle, Group, Path, Text } from 'react-konva';
import { useStore } from '../store';
import type { SynopticConnection, WirePoint } from '../store';
import { getSymbolDefinition } from '../symbols/SymbolRegistry';
import { pathFromPoints, getConductorCoreColor } from './ConnectionLine';
import type { WireSegmentCollision } from './ConnectionLine';
import { findAllCollisions } from '../project/WireCollision';
import { ObjectLabelRenderer } from './ObjectLabelRenderer';
import { COLOR_ALARM, COLOR_CANVAS_BACKGROUND, COLOR_LAMP_LIT, COLOR_OUTLINE, COLOR_PANEL, COLOR_WATER, COLOR_WHITE, CONDUCTOR_WIDTH, FONT_SIZE_BASE, FONT_SIZE_SMALL, FONT_UI, WIRE_TERMINAL_SNAP_DISTANCE } from '../theme/ScadaTheme';
import { snapValue } from '../utils/GridSnap';
import {
  snapPointToGrid, appendWirePoint, removeLastWirePoint,
  insertBendOnSegment, nearestPointOnPolyline, simplifyCollinearPoints
} from '../utils/WireDrawing';
import { resolveNets, getJunctionPoints, findMediaConflictAtPoint } from '../project/NetResolver';
import type { MediaConflict } from '../project/NetResolver';
import { MediaMismatchDialog, mediaConflictMessage } from './MediaMismatchDialog';
import { getObstacles } from '../project/WireCollision';
import { routeAround } from '../project/WireRouter';
import { describeObject } from '../utils/ObjectDisplay';
import { attachAnchorsToNewPoints, findTerminalAt } from '../utils/WireAnchoring';
import { getNearbyTerminals, findNearestTerminal, snapToTerminalOrGrid } from '../utils/TerminalReach';
import { isSymbolDeviceMissing } from '../project/DeviceBindingValidation';
import { isSymbolInterlocked } from '../project/InterlockIndicator';
import { WireNodeSymbol } from '../symbols/scada/WireNodeSymbol';
import { MeterElementNode } from './MeterElementNode';
import { computeMeterHeight } from '../meter/MeterElement';
import { SignalPanelElementNode } from './SignalPanelElementNode';
import { computeSignalPanelHeight } from '../elements/SignalPanelElement';
import { GroupCommandElementNode } from './GroupCommandElementNode';
import { computeGroupCommandHeight } from '../elements/GroupCommandElement';
import { SetpointElementNode } from './SetpointElementNode';
import { computeSetpointHeight } from '../elements/SetpointElement';
import { isObjectFullyInBox, isMeterFullyInBox, isConnectionFullyInBox, mergeSelectionAdditive } from '../utils/SelectionBox';
import { clampZoom, computeContentBounds, computeFitView, GRID_THIN_BELOW_ZOOM } from '../utils/CanvasView';
import { FrameElementNode } from './FrameElementNode';
import { computeFrameRectFromDrag } from '../elements/FrameElement';
import { shouldExitInsertModeAfterPlacing } from '../utils/InsertMode';
import { isAltKeyDown, isSpaceKeyDown, setAltKeyDown, setSpaceKeyDown } from '../utils/CanvasInputState';
import type { DragKey, GroupDragApi } from './canvas/types';
import { ObjectNode } from './canvas/ObjectNode';
import { ConnectionNode } from './canvas/ConnectionNode';
import { ObjectTransformerHandle, FrameTransformerHandle, WidthOnlyTransformerHandle } from './canvas/TransformerHandles';

// Internal-audit fix (god-file breakup): this file used to define five
// sub-components (ObjectNode, ObjectTransformerHandle,
// FrameTransformerHandle, WidthOnlyTransformerHandle, ConnectionNode) at
// module scope before ever getting to the Canvas component itself - all
// five, plus the DragKey/GroupDragApi types and the isAltPressed/
// isSpacePressed module state they (and Canvas below) all share, now
// live in ./canvas/ and ../utils/CanvasInputState.ts instead. This is a
// pure move: every one of those five components is unchanged, comments
// included - see their own files for the reasoning that used to sit
// here. What follows is only the Canvas component itself.

export const Canvas: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<any>(null);
  // Layers (commit 5): every ObjectNode reports its own Konva Group node
  // here (see ObjectNode's onShapeRef) so the separate, later-drawn
  // selection/handles pass (ObjectTransformerHandle) can still attach a
  // Transformer to the right node without owning a ref to it directly -
  // a plain mutable Map, not React state: a Konva node reference itself
  // never needs to trigger a re-render when it changes.
  const objectShapeRefs = useRef<Map<string, any>>(new Map());
  const registerObjectShapeRef = (id: string, node: any) => {
    objectShapeRefs.current.set(id, node);
  };
  // Same reasoning, for a frame's own resize handles (commit 3: 3f
  // requires a frame to be resizable via corner/edge handles, same
  // mechanism as a symbol's own Transformer).
  const frameShapeRefs = useRef<Map<string, any>>(new Map());
  const registerFrameShapeRef = (id: string, node: any) => {
    frameShapeRefs.current.set(id, node);
  };
  const canvasConfig = useStore(state => state.canvasConfig);
  const gridSize = canvasConfig.gridSize;
  const { objects, selectedIds, selectObjects, clearSelection, addObject, updateObject, canvasState, setCanvasState } = useStore();
  const { meters, selectedMeterIds, selectMeters, updateMeter, devices } = useStore();
  const { signalPanels, selectedSignalPanelIds, selectSignalPanels, updateSignalPanel } = useStore();
  const { frames, selectedFrameIds, selectFrames, addFrame, updateFrame, isDrawingFrame, drawingFrameVariant, frameToolContinuous, setDrawingFrameMode } = useStore();
  const { groupCommands, selectedGroupCommandIds, selectGroupCommands, updateGroupCommand } = useStore();
  const { setpointPanels, selectedSetpointPanelIds, selectSetpointPanels, updateSetpointPanel } = useStore();
  const { selectMixed } = useStore();
  const [size, setSize] = useState({ width: 800, height: 600 });
  // Mirrors `size` for the keydown handler below (registered once,
  // empty deps) - the same drawingPointsRef pattern already used
  // elsewhere in this file so that closure always reads the CURRENT
  // container size, not whatever it was when the effect first ran.
  const sizeRef = useRef(size);
  useEffect(() => { sizeRef.current = size; }, [size]);

  // Selection Rect
  const [selectionBox, setSelectionBox] = useState<{ x: number, y: number, width: number, height: number } | null>(null);
  const selectionStartRef = useRef<{ x: number, y: number } | null>(null);

  // Panning
  const isPanningRef = useRef(false);
  const lastPanPosRef = useRef({ x: 0, y: 0 });

  // Freehand wire drawing (usterka B): points already placed, and the
  // live (grid-snapped) cursor position for the preview segment. A ref
  // mirrors the state so the window-level keydown handler (registered
  // once) always reads the current points, never a stale closure.
  const [drawingPoints, setDrawingPoints] = useState<WirePoint[] | null>(null);
  const [drawingPreview, setDrawingPreview] = useState<WirePoint | null>(null);
  // feat/wire-routing-around-obstacles commit 1: which colliding
  // segment (if any) the cursor is currently hovering, for the small
  // tooltip naming the obstacle - one piece of state for the whole
  // canvas, not one per wire (ConnectionLine's own onCollisionHover
  // reports into this).
  const [collisionTooltip, setCollisionTooltip] = useState<{ x: number; y: number; label: string } | null>(null);
  // feat/tank-language-and-media commit 1: set the instant a wire
  // endpoint would land on a terminal/wire of an incompatible medium -
  // the connection is never created; closing the dialog just clears
  // this, drawing stays exactly as armed as it was (usterka b/c/point 5).
  const [mediaConflict, setMediaConflict] = useState<MediaConflict | null>(null);
  const drawingPointsRef = useRef<WirePoint[] | null>(null);
  useEffect(() => { drawingPointsRef.current = drawingPoints; }, [drawingPoints]);

  // isDrawingConnection/setDrawingMode is the same store pair the old
  // click-two-ports tool used, repurposed (not renamed) for the freehand
  // wire tool - Toolbar.tsx's existing "Rysuj polaczenie" button already
  // toggles it; Canvas.tsx only needs to read it here. drawingMedium/
  // drawingStyle (part C) are the toolbar's medium/style selector -
  // every new wire is drawn with whichever is currently chosen.
  const { connections, selectedConnectionIds, selectConnections, isDrawingConnection, drawingMedium, wireRoutingMode } = useStore();

  // Group move (commit 2c) - see GroupDragApi's own comment (canvas/
  // types.ts) for the full reasoning. dragNodeRefs is a plain mutable
  // Map, not React state, for the same reason objectShapeRefs above is
  // one: a Konva node reference never needs to trigger a re-render when
  // it changes. groupDragRef tracks the in-progress drag itself (which
  // element started it, and every key that must follow it) - also not
  // React state, since it only ever needs to be read/written from Konva
  // event handlers mid-gesture, never from a render.
  const dragNodeRefs = useRef<Map<DragKey, any>>(new Map());
  const groupDragRef = useRef<{ leaderKey: DragKey; keys: DragKey[] } | null>(null);

  const getSelectionKeys = (): DragKey[] => [
    ...selectedIds.map(id => `obj:${id}`),
    ...selectedMeterIds.map(id => `meter:${id}`),
    ...selectedSignalPanelIds.map(id => `panel:${id}`),
    ...selectedFrameIds.map(id => `frame:${id}`),
    ...selectedGroupCommandIds.map(id => `groupcmd:${id}`),
    ...selectedSetpointPanelIds.map(id => `setpoint:${id}`),
    ...selectedConnectionIds.map(id => `conn:${id}`)
  ];

  const groupDrag: GroupDragApi = {
    registerNode: (key, node) => {
      if (node) dragNodeRefs.current.set(key, node);
      else dragNodeRefs.current.delete(key);
    },
    start: (key) => {
      const keys = getSelectionKeys();
      groupDragRef.current = (keys.length > 1 && keys.includes(key)) ? { leaderKey: key, keys } : null;
    },
    isActive: () => !!groupDragRef.current,
    follow: (dx, dy) => {
      const g = groupDragRef.current;
      if (!g) return;
      g.keys.forEach(key => {
        if (key === g.leaderKey) return;
        const node = dragNodeRefs.current.get(key);
        if (!node) return;
        if (key.startsWith('conn:')) {
          // A connection's move-Group IS the delta - see this type's
          // own comment.
          node.x(dx);
          node.y(dy);
          return;
        }
        const id = key.slice(key.indexOf(':') + 1);
        const source = key.startsWith('obj:') ? objects.find(o => o.id === id)
          : key.startsWith('meter:') ? meters.find(m => m.id === id)
          : key.startsWith('panel:') ? signalPanels.find(p => p.id === id)
          : key.startsWith('frame:') ? frames.find(f => f.id === id)
          : key.startsWith('groupcmd:') ? groupCommands.find(g => g.id === id)
          : setpointPanels.find(p => p.id === id);
        if (!source) return;
        node.x(source.x + dx);
        node.y(source.y + dy);
      });
    },
    commit: (dx, dy) => {
      const g = groupDragRef.current;
      if (!g) return;
      useStore.getState().moveSelectionBy(dx, dy);
      // A follower connection's move-Group has no store-driven x/y at
      // all (see ConnectionNode) - the store update alone will not put
      // it back to neutral, so it must be reset by hand, the same way
      // its own solo drag already resets itself after every commit.
      g.keys.forEach(key => {
        if (!key.startsWith('conn:')) return;
        const node = dragNodeRefs.current.get(key);
        if (node) { node.x(0); node.y(0); }
      });
      groupDragRef.current = null;
    }
  };

  const toCanvasPoint = (stagePos: { x: number; y: number }): WirePoint => {
    const scale = canvasState.zoom;
    return snapPointToGrid((stagePos.x - canvasState.panX) / scale, (stagePos.y - canvasState.panY) / scale);
  };

  // usterka 1f: while drawing a wire, a raw cursor position closer than
  // half a grid cell to some terminal snaps to that terminal's own
  // EXACT coordinate instead of the plain nearest grid node - without
  // this, landing on a terminal means aiming for its precise pixel, not
  // just getting close. Scoped to wire-drawing only (finishDrawing's
  // point placement, and the live preview below) - toCanvasPoint itself
  // is untouched, so frame-drawing/box-select keep their own plain
  // grid-snap exactly as before.
  const toWirePoint = (stagePos: { x: number; y: number }): WirePoint => {
    const scale = canvasState.zoom;
    const worldX = (stagePos.x - canvasState.panX) / scale;
    const worldY = (stagePos.y - canvasState.panY) / scale;
    // feat/tank-language-and-media commit 1: medium-aware magnetism -
    // only while the wire tool is actually armed (isDrawingConnection),
    // reading the CURRENT drawingMedium straight from the store rather
    // than this render's own closed-over value, same reasoning as
    // every other useStore.getState() read in this file's own wire-
    // drawing code.
    const drawnMedium = isDrawingConnection ? useStore.getState().drawingMedium : undefined;
    return snapToTerminalOrGrid(worldX, worldY, objects, drawnMedium);
  };

  // feat/wire-routing-around-obstacles commit 3, point (c): extracted
  // from the old finishDrawing (which just read drawingPointsRef.current
  // itself) so the OMIJAJ mode's own auto-finish-on-terminal-hit
  // (handleMouseDown below) can commit a freshly computed FULL route
  // immediately, without waiting a render for drawingPointsRef to catch
  // up to a state update that has not committed yet.
  const commitWire = (points: WirePoint[] | null) => {
    setDrawingPoints(null);
    setDrawingPreview(null);
    if (!points || points.length < 2) return;

    // Read medium/style straight from the store rather than this
    // render's destructured drawingMedium/drawingStyle: the window
    // keydown handler below registers this function once (empty deps),
    // so a value captured from render-scope would go stale the moment
    // the toolbar's selector changes after mount - the same reason
    // drawingPointsRef exists instead of just closing over drawingPoints.
    const { drawingMedium: medium, drawingStyle: style } = useStore.getState();
    // feat/water-management commit 1: a point that landed exactly on a
    // terminal at the moment of creation remembers it - checked once,
    // here, against the object list as it stands right now (never
    // re-checked later; see WireAnchoring.ts's own header).
    const anchoredPoints = attachAnchorsToNewPoints(points, useStore.getState().objects);
    // feat/water-management commit 2: state is no longer set here at
    // all - it is a computed, read-only property of the net this wire
    // ends up joining (NetResolver.ts), never a value the wire itself
    // carries at creation time.
    useStore.getState().addConnection({ points: anchoredPoints, medium, style });
    useStore.getState().saveHistory();

    // Readable, UUID-free feedback: if the new wire actually touches a
    // terminal - possibly by landing on the MIDDLE of another wire's
    // segment, e.g. tapping into a busbar - name what it joined.
    const store = useStore.getState();
    const justAdded = store.connections[store.connections.length - 1];
    const nets = resolveNets(store.connections, store.objects);
    const net = nets.find(n => n.connectionIds.includes(justAdded.id));
    if (net && net.terminals.length > 0) {
      const uniqueObjIds = [...new Set(net.terminals.map(t => t.objId))];
      const names = uniqueObjIds.map(id => describeObject(store.objects.find(o => o.id === id))).join(', ');
      store.addMessage(`[INFO] Wire connected: ${names}`);
    } else {
      store.addMessage('[INFO] Wire drawn (not touching any terminal yet)');
    }
  };

  const finishDrawing = () => commitWire(drawingPointsRef.current);

  // feat/wire-routing-around-obstacles commit 3: which symbol(s) an
  // in-progress OMIJAJ route must not treat as an obstacle - the one
  // this whole wire STARTED from (if it started on a terminal) and
  // whatever terminal the CURRENT click is landing on (its destination),
  // exactly the same "a wire is never its own obstacle" rule commit 1
  // already applies to a finished wire's own two ends.
  const routingExcludeIds = (firstPoint: WirePoint | undefined, clickPoint: WirePoint): string[] => {
    const ids = new Set<string>();
    if (firstPoint) {
      const startTerminal = findTerminalAt(objects, firstPoint.x, firstPoint.y);
      if (startTerminal) ids.add(startTerminal.symbolId);
    }
    const endTerminal = findTerminalAt(objects, clickPoint.x, clickPoint.y);
    if (endTerminal) ids.add(endTerminal.symbolId);
    return [...ids];
  };

  const routingScreen = { objects, meters, signalPanels, frames, groupCommands, setpointPanels };

  // Grid-snap Alt bypass, tracked once, globally, for the whole canvas -
  // plus the wire-drawing tool's own keyboard shortcuts (Enter finishes,
  // Escape cancels the whole in-progress wire, Backspace undoes the last
  // bend, 1/2/3 pick the medium a new wire is drawn with - part C, same
  // three choices as the toolbar's selector), registered once so they
  // always see the latest drawing state through the ref above rather
  // than a stale closure.
  useEffect(() => {
    const isTypingInField = () => {
      const el = document.activeElement as HTMLElement | null;
      return !!el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable);
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Alt') setAltKeyDown(true);
      if (isTypingInField()) return;
      if (e.key === 'Escape') {
        // fix/handles-insert-mode-diodes commit 2: Escape exits insert
        // mode back to select. Cancels any in-progress wire polyline
        // first (existing behavior - the wire tool otherwise still
        // stays continuous by default), THEN turns off the wire tool
        // and/or the frame/building tool if either is currently armed.
        // Only when neither applied (nothing was in insert mode to
        // begin with) does Escape fall back to its plain, older
        // behavior of just clearing the current selection.
        const s = useStore.getState();
        const wasMidDraw = !!drawingPointsRef.current;
        const wasInsertMode = s.isDrawingConnection || s.isDrawingFrame;
        if (wasMidDraw) {
          setDrawingPoints(null);
          setDrawingPreview(null);
        }
        if (s.isDrawingConnection) s.setDrawingMode(false);
        if (s.isDrawingFrame) s.setDrawingFrameMode(false);
        if (!wasMidDraw && !wasInsertMode) {
          s.clearSelection();
        }
      } else if (e.key === 'Enter' && drawingPointsRef.current) {
        finishDrawing();
      } else if (e.key === 'Backspace' && drawingPointsRef.current) {
        e.preventDefault();
        setDrawingPoints(prev => (prev ? removeLastWirePoint(prev) : prev));
      } else if (e.key === 'Delete' || e.key === 'Backspace') {
        // Reads the CURRENT selection from the store rather than this
        // render's destructured selectedIds/selectedConnectionIds/
        // selectedMeterIds - this handler is registered once (empty
        // deps below), so a value closed over from render-scope would
        // go stale the moment the selection changes after mount, the
        // same reasoning behind every other useStore.getState() call
        // already in this effect.
        e.preventDefault();
        const s = useStore.getState();
        s.deleteObjects(s.selectedIds, s.selectedConnectionIds, s.selectedMeterIds, s.selectedSignalPanelIds, s.selectedFrameIds, s.selectedGroupCommandIds, s.selectedSetpointPanelIds);
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'a') {
        // Select everything on the current screen - objects,
        // connections and meters together.
        e.preventDefault();
        useStore.getState().selectAll();
      } else if (e.key === 'ArrowUp' || e.key === 'ArrowDown' || e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        // One grid cell per press, ten with Shift held - one history
        // entry per keypress (moveSelectionBy itself calls saveHistory
        // exactly once), including on a held-key auto-repeat, where
        // every repeat is its own keydown event and so its own press.
        e.preventDefault();
        const step = gridSize * (e.shiftKey ? 10 : 1);
        const dx = e.key === 'ArrowLeft' ? -step : e.key === 'ArrowRight' ? step : 0;
        const dy = e.key === 'ArrowUp' ? -step : e.key === 'ArrowDown' ? step : 0;
        useStore.getState().moveSelectionBy(dx, dy);
      } else if (e.key === '1') {
        useStore.getState().setDrawingMedium('ELECTRICAL');
      } else if (e.key === '2') {
        useStore.getState().setDrawingMedium('WATER');
      } else if (e.key === '3') {
        useStore.getState().setDrawingMedium('VENTILATION');
      } else if (e.key.toLowerCase() === 'r') {
        // fix/inline-device-creation commit 1: R rotates the current
        // selection 90 degrees clockwise, Shift+R counter-clockwise.
        // Added alongside this commit's own removal of the free-rotation
        // handle (rotateEnabled on ObjectTransformerHandle) so rotation stays fully reachable
        // without it - Toolbar's Rotate Left/Right buttons and
        // Properties' own Rotation field both already called
        // rotateSelected; this is simply a third, keyboard, path to the
        // same action. rotateSelected itself is a no-op when nothing is
        // selected, so no guard is needed here.
        useStore.getState().rotateSelected(e.shiftKey ? 'ccw' : 'cw');
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'c') {
        // Commit 2: copy the current selection (objects, connections
        // and meters together, whatever is currently non-empty).
        e.preventDefault();
        useStore.getState().copySelected();
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'v') {
        // Paste, offset by exactly one grid cell right and down.
        e.preventDefault();
        useStore.getState().paste();
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'd') {
        // Duplicate the current selection in place, same offset as
        // paste, without touching the clipboard.
        e.preventDefault();
        useStore.getState().duplicateSelected();
      } else if ((e.ctrlKey || e.metaKey) && e.key === '0') {
        // Restores the SCALE only - pan is left exactly where it is.
        e.preventDefault();
        useStore.getState().setCanvasState({ zoom: 1 });
      } else if ((e.ctrlKey || e.metaKey) && e.key === '9') {
        // Fit the whole project's content into the current viewport.
        e.preventDefault();
        const s = useStore.getState();
        const bounds = computeContentBounds(s.objects, s.meters, s.connections);
        const view = computeFitView(bounds, sizeRef.current.width, sizeRef.current.height);
        s.setCanvasState(view);
      } else if (e.key === ' ') {
        // Held Space (commit 4): the cursor turns into a hand, and a
        // left-button drag pans - guarded behind isTypingInField()
        // (checked above, unlike Alt) since typing a space is common
        // and must not put the canvas into pan mode.
        setSpaceKeyDown(true);
        if (containerRef.current && !isPanningRef.current) containerRef.current.style.cursor = 'grab';
      }
    };
    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.key === 'Alt') setAltKeyDown(false);
      if (e.key === ' ') {
        setSpaceKeyDown(false);
        if (containerRef.current && !isPanningRef.current) containerRef.current.style.cursor = 'default';
      }
    };
    // Also cleared on window blur - Alt/Space released outside the
    // window (e.g. while alt-tabbing) would otherwise never fire their
    // own keyup here.
    const handleBlur = () => {
      setAltKeyDown(false);
      setSpaceKeyDown(false);
      if (containerRef.current && !isPanningRef.current) containerRef.current.style.cursor = 'default';
    };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    window.addEventListener('blur', handleBlur);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      window.removeEventListener('blur', handleBlur);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;

    const observer = new ResizeObserver((entries) => {
      for (let entry of entries) {
        setSize({
          width: entry.contentRect.width,
          height: entry.contentRect.height
        });
      }
    });

    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
    };
  }, []);

  const handleWheel = (e: any) => {
    e.evt.preventDefault();
    const scaleBy = 1.1;
    const stage = e.target.getStage();
    const oldScale = stage.scaleX();

    const mousePointTo = {
      x: stage.getPointerPosition().x / oldScale - stage.x() / oldScale,
      y: stage.getPointerPosition().y / oldScale - stage.y() / oldScale,
    };

    // Clamped to [MIN_ZOOM, MAX_ZOOM] (25%-400%) rather than simply
    // refused past the edge - so scrolling hard against the limit still
    // lands exactly on 25% or 400%, not on whatever the previous step
    // happened to stop at.
    const newScale = clampZoom(e.evt.deltaY < 0 ? oldScale * scaleBy : oldScale / scaleBy);

    setCanvasState({
      zoom: newScale,
      panX: -(mousePointTo.x - stage.getPointerPosition().x / newScale) * newScale,
      panY: -(mousePointTo.y - stage.getPointerPosition().y / newScale) * newScale
    });
  };

  const handleMouseDown = (e: any) => {
    // Middle-button pan (unchanged), or a left-button drag while Space
    // is held (commit 4) - the same panning gesture either way.
    if (e.evt.button === 1 || (isSpaceKeyDown() && e.evt.button === 0)) {
      isPanningRef.current = true;
      lastPanPosRef.current = { x: e.evt.clientX, y: e.evt.clientY };
      if (containerRef.current) containerRef.current.style.cursor = 'grabbing';
      return;
    }

    if (isDrawingConnection) {
      // Every click while the wire tool is active places a point - it
      // does not matter what is underneath (empty canvas or an object),
      // a wire lands wherever the click itself snapped to.
      const pos = e.target.getStage().getPointerPosition();
      if (!pos) return;
      const point = toWirePoint(pos);

      // feat/tank-language-and-media commit 1, points (b)/(c): reject
      // landing on - or touching the middle of - a terminal or wire of
      // an incompatible medium, BEFORE placing anything. Checked on
      // EVERY click (not only the final one that would finish the
      // wire): starting a wire on the wrong medium's terminal is
      // exactly as wrong as ending one there. The connection is never
      // created and drawing stays armed - only this one click is
      // refused (usterka b/e).
      const drawnMedium = useStore.getState().drawingMedium;
      const conflict = findMediaConflictAtPoint(point, objects, connections, drawnMedium);
      if (conflict) {
        setMediaConflict(conflict);
        useStore.getState().addMessage(mediaConflictMessage(conflict));
        return;
      }

      // feat/wire-routing-around-obstacles commit 3, points (b)/(c): in
      // OMIJAJ mode a click places the WHOLE computed route from the
      // last point to here, not a single point - and finishes the wire
      // right then if the click landed on a terminal (findNearestTerminal,
      // same magnetism toWirePoint's own snap already used to place
      // `point` exactly on it). PROSTO mode is entirely unchanged below.
      if (useStore.getState().wireRoutingMode === 'AVOID') {
        const prevPoints = drawingPointsRef.current || [];
        let fullPoints: WirePoint[];
        if (prevPoints.length === 0) {
          fullPoints = [point];
        } else {
          const last = prevPoints[prevPoints.length - 1];
          const excludeIds = routingExcludeIds(prevPoints[0], point);
          const obstacles = getObstacles(routingScreen, excludeIds);
          const routed = routeAround(last, point, obstacles, gridSize);
          fullPoints = simplifyCollinearPoints([...prevPoints, ...routed.slice(1)]);
        }
        const landedOnTerminal = prevPoints.length > 0 && !!findNearestTerminal(objects, point);
        if (landedOnTerminal) {
          commitWire(fullPoints);
        } else {
          setDrawingPoints(fullPoints);
        }
        return;
      }

      setDrawingPoints(prev => appendWirePoint(prev || [], point));
      return;
    }

    if (isDrawingFrame) {
      // A frame is dragged out like a rectangle tool, on any point -
      // same "doesn't matter what's underneath" reasoning as the wire
      // tool above. Reuses the same start/box tracking the rubber-band
      // selection itself uses (selectionStartRef/selectionBox) - the
      // two gestures are geometrically identical (drag a corner to a
      // corner), only what happens on release differs (see
      // handleMouseUp), so there is no need for a second, parallel set
      // of refs just to tell them apart.
      const pos = e.target.getStage().getPointerPosition();
      if (!pos) return;
      const { x: startX, y: startY } = toCanvasPoint(pos);
      selectionStartRef.current = { x: startX, y: startY };
      setSelectionBox({ x: startX, y: startY, width: 0, height: 0 });
      return;
    }

    // Check if clicking on empty stage
    const clickedOnEmpty = e.target === e.target.getStage() || e.target.name() === 'grid';
    if (clickedOnEmpty) {
      if (!e.evt.shiftKey) {
        clearSelection();
      }

      const pos = e.target.getStage().getPointerPosition();
      const scale = canvasState.zoom;
      const stageX = canvasState.panX;
      const stageY = canvasState.panY;

      const startX = (pos.x - stageX) / scale;
      const startY = (pos.y - stageY) / scale;

      selectionStartRef.current = { x: startX, y: startY };
      setSelectionBox({ x: startX, y: startY, width: 0, height: 0 });
    }
  };

  const handleMouseMove = (e: any) => {
    // usterka 1d/1e/1f: tracked from the moment the wire tool is armed
    // (not only once drawingPointsRef.current has a first point) - the
    // very FIRST point placed needs nearby-terminal visibility and
    // magnetism exactly as much as every point after it. The rubber-
    // band preview line itself (drawingPoints && drawingPoints.length >
    // 0, further down) already stays gated on having at least one point
    // - this only widens what drives the terminal-reach computation
    // below, not that preview line.
    if (isDrawingConnection) {
      const pos = e.target.getStage()?.getPointerPosition();
      if (pos) setDrawingPreview(toWirePoint(pos));
    }

    if (isPanningRef.current) {
      const dx = e.evt.clientX - lastPanPosRef.current.x;
      const dy = e.evt.clientY - lastPanPosRef.current.y;

      setCanvasState({
        panX: canvasState.panX + dx,
        panY: canvasState.panY + dy
      });
      lastPanPosRef.current = { x: e.evt.clientX, y: e.evt.clientY };
      return;
    }

    if (!selectionStartRef.current) return;

    const pos = e.target.getStage().getPointerPosition();
    const scale = canvasState.zoom;
    const stageX = canvasState.panX;
    const stageY = canvasState.panY;

    const curX = (pos.x - stageX) / scale;
    const curY = (pos.y - stageY) / scale;

    const startX = selectionStartRef.current.x;
    const startY = selectionStartRef.current.y;

    setSelectionBox({
      x: Math.min(startX, curX),
      y: Math.min(startY, curY),
      width: Math.abs(curX - startX),
      height: Math.abs(curY - startY)
    });
  };

  const handleMouseUp = (e: any) => {
    if (e.evt.button === 1 || isPanningRef.current) {
      isPanningRef.current = false;
      if (containerRef.current) containerRef.current.style.cursor = 'default';
      return;
    }

    if (isDrawingConnection) {
      return;
    }

    if (isDrawingFrame) {
      // Finalize the dragged rectangle into a real frame - 3g's own
      // minimum-size clamp lives in computeFrameRectFromDrag itself, so
      // a drag too small to register (a stray click, essentially) still
      // creates a real, minimum-size frame, never a zero-size one.
      if (selectionBox) {
        // selectionBox is already the normalized (min-x/min-y, width,
        // height) rectangle handleMouseMove built from the two drag
        // corners - its own two opposite corners are exactly the two
        // points computeFrameRectFromDrag needs, however the drag
        // itself was oriented.
        const rect = computeFrameRectFromDrag(selectionBox.x, selectionBox.y, selectionBox.x + selectionBox.width, selectionBox.y + selectionBox.height);
        addFrame({ ...rect, titlePosition: 'TOP_LEFT', variant: drawingFrameVariant });
        const newest = useStore.getState().frames[useStore.getState().frames.length - 1];
        if (newest) selectFrames([newest.id], false);

        // fix/handles-insert-mode-diodes commit 2: return to select
        // mode after placing ONE frame/building - the previous
        // behavior left the tool armed forever, so every further click
        // silently placed another element. Shift held when the tool
        // was chosen (frameToolContinuous, set by Toolbar.tsx's own
        // onClick) keeps it armed instead, for placing several in a
        // row.
        if (shouldExitInsertModeAfterPlacing(frameToolContinuous)) {
          setDrawingFrameMode(false);
        }
      }
      selectionStartRef.current = null;
      setSelectionBox(null);
      return;
    }

    if (selectionStartRef.current && selectionBox) {
      // Rubber-band selection (commit 3, extended in commit 6 to signal
      // panels, and in commit 2/feat-appearance-selection-frames to
      // frames): everything lying ENTIRELY within the box - objects,
      // connections, meters, signal panels and frames together, not
      // just whichever kind happens to be found first. Something
      // poking out past the box's edge is left unselected.
      // isMeterFullyInBox's own signature ({x,y,width} + a separately-
      // computed height) is already generic enough to reuse as-is for
      // a signal panel - no new isSignalPanelFullyInBox needed, just
      // its own height math. A frame has x/y/width/height directly, so
      // isObjectFullyInBox (built for a SynopticObject, but only ever
      // reads those four fields plus optional scale) is reusable for
      // it exactly as it stands - no new isFrameFullyInBox either.
      const box = selectionBox;
      const objectIds = objects.filter(obj => isObjectFullyInBox(obj, box)).map(o => o.id);
      const meterIds = meters.filter(m => isMeterFullyInBox(m, computeMeterHeight(m), box)).map(m => m.id);
      const signalPanelIds = signalPanels.filter(p => isMeterFullyInBox(p, computeSignalPanelHeight(p), box)).map(p => p.id);
      const frameIds = frames.filter(f => isObjectFullyInBox(f, box)).map(f => f.id);
      // A group command button has a fixed, computed height (never a
      // field of its own) exactly like a meter/signal panel - reuses
      // isMeterFullyInBox's own {x,y,width}+height signature, no new helper.
      const groupCommandIds = groupCommands.filter(g => isMeterFullyInBox(g, computeGroupCommandHeight(), box)).map(g => g.id);
      const setpointPanelIds = setpointPanels.filter(p => isMeterFullyInBox(p, computeSetpointHeight(p), box)).map(p => p.id);
      const connectionIds = connections.filter(c => isConnectionFullyInBox(c, box)).map(c => c.id);

      if (objectIds.length > 0 || meterIds.length > 0 || signalPanelIds.length > 0 || frameIds.length > 0 || groupCommandIds.length > 0 || setpointPanelIds.length > 0 || connectionIds.length > 0) {
        if (e.evt.shiftKey) {
          // Shift+drag adds to whatever was already selected, per kind.
          selectMixed(mergeSelectionAdditive(
            { objectIds: selectedIds, connectionIds: selectedConnectionIds, meterIds: selectedMeterIds, signalPanelIds: selectedSignalPanelIds, frameIds: selectedFrameIds, groupCommandIds: selectedGroupCommandIds, setpointPanelIds: selectedSetpointPanelIds },
            { objectIds, connectionIds, meterIds, signalPanelIds, frameIds, groupCommandIds, setpointPanelIds }
          ));
        } else {
          selectMixed({ objectIds, connectionIds, meterIds, signalPanelIds, frameIds, groupCommandIds, setpointPanelIds });
        }
      }
      // An empty box selects nothing new - a non-shift click already
      // cleared any previous selection back in handleMouseDown.
    }

    selectionStartRef.current = null;
    setSelectionBox(null);
  };

  const handleDblClick = () => {
    if (isDrawingConnection && drawingPointsRef.current) {
      finishDrawing();
    }
  };

  const handleAltClickSegment = (conn: SynopticConnection, worldPoint: WirePoint) => {
    const nearest = nearestPointOnPolyline(conn.points, worldPoint);
    if (!nearest) return;
    const newPoints = insertBendOnSegment(conn.points, nearest.segmentIndex, nearest.point);
    // feat/wire-routing-around-obstacles commit 3, point (d): placing
    // your own bend switches this wire into manual mode for good - the
    // PRZELICZ TRASE command (recalculateConnectionRoutes) skips any
    // connection with this flag set, forever after.
    useStore.getState().updateConnection(conn.id, { points: newPoints, isManualRoute: true });
    useStore.getState().saveHistory();
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const junctionPoints = getJunctionPoints(connections, objects);

  // usterka 1d/1e/1f: while the wire tool is armed, every object with a
  // terminal within reach of the live cursor shows its terminals
  // without needing individual hover (nearbyTerminalObjIds), and the
  // single terminal magnetism would actually snap to right now is
  // highlighted (highlightedTerminal) - both plain per-render
  // computations, the same "no memoization" convention
  // junctionPoints/netStateByConnectionId above already use. null
  // (rather than an empty Set/no match) specifically means "not
  // currently drawing a wire", not "drawing, but nothing nearby".
  const wireCursorPos = isDrawingConnection ? drawingPreview : null;
  const nearbyTerminalObjIds = wireCursorPos ? new Set(getNearbyTerminals(objects, wireCursorPos).map(t => t.objId)) : null;
  // feat/tank-language-and-media commit 1: medium-aware - the
  // magnetism/highlight can only ever land on a terminal that shares
  // the wire's own medium (usterka a). A terminal of a different
  // medium is still SHOWN (nearbyTerminalObjIds above is unaffected),
  // just dimmed and never this one.
  const highlightedTerminal = wireCursorPos ? findNearestTerminal(objects, wireCursorPos, WIRE_TERMINAL_SNAP_DISTANCE, drawingMedium) : null;

  // feat/water-management commit 2: a wire's own color is now the
  // RESULT of its net's state (isSourceActive), never a per-connection
  // setting - computed once per render, here, the same "plain inline
  // call, no memoization" convention junctionPoints above already
  // uses, then looked up per connection below by id.
  const netStateByConnectionId = new Map<string, 'ACTIVE' | 'INACTIVE'>();
  resolveNets(connections, objects, devices).forEach(net => {
    net.connectionIds.forEach(id => netStateByConnectionId.set(id, net.state));
  });

  // feat/wire-routing-around-obstacles commit 1: which of each wire's
  // own segments currently cross an obstacle - recomputed every render
  // (cheap, purely geometric, same "no memoization" convention every
  // other per-render map on this page already uses), then handed to
  // each ConnectionNode for its own dashed marking. The one-time
  // Messages warning is a SEPARATE path (historySlice.ts's own
  // saveHistory, gated by getNewCollisionWarnings so it does not fire
  // on every render) - this map only ever drives what is drawn.
  const collisionsByConnectionId = new Map<string, WireSegmentCollision[]>();
  findAllCollisions(connections, { objects, meters, signalPanels, frames, groupCommands, setpointPanels }).forEach(c => {
    const list = collisionsByConnectionId.get(c.connectionId) || [];
    list.push({ segmentIndex: c.segmentIndex, obstacleLabel: c.obstacle.label });
    collisionsByConnectionId.set(c.connectionId, list);
  });

  // feat/wire-routing-around-obstacles commit 3, point (b): in OMIJAJ
  // mode the in-progress wire's own live preview shows the ROUTE the
  // next click would actually place, not a straight line to the
  // cursor - the user sees which way it will go before committing to
  // it. PROSTO mode is unchanged (a plain straight preview segment).
  const drawingPreviewPoints: WirePoint[] | null = (() => {
    if (!drawingPoints || drawingPoints.length === 0) return null;
    if (!drawingPreview) return drawingPoints;
    if (wireRoutingMode === 'AVOID') {
      const last = drawingPoints[drawingPoints.length - 1];
      const excludeIds = routingExcludeIds(drawingPoints[0], drawingPreview);
      const obstacles = getObstacles(routingScreen, excludeIds);
      const routed = routeAround(last, drawingPreview, obstacles, gridSize);
      return [...drawingPoints, ...routed.slice(1)];
    }
    return [...drawingPoints, drawingPreview];
  })();

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (!stageRef.current || !containerRef.current) return;

    const dataStr = e.dataTransfer.getData('application/reactflow');
    if (!dataStr) return;

    const data = JSON.parse(dataStr);

    // Get pointer position relative to the container, and translate it to stage coordinates
    const containerRect = containerRef.current.getBoundingClientRect();
    const pos = {
      x: e.clientX - containerRect.left,
      y: e.clientY - containerRect.top
    };

    const scale = canvasState.zoom;
    const stageX = canvasState.panX;
    const stageY = canvasState.panY;

    let x = (pos.x - stageX) / scale;
    let y = (pos.y - stageY) / scale;

    // Snap to grid unless the persistent toggle is off or Alt is held.
    // e.altKey (the native DragEvent's own modifier state) is combined
    // with the tracked flag - a drag-and-drop gesture can be less
    // reliable about delivering keydown/keyup than a plain mouse drag on
    // some platforms.
    x = snapValue(x, gridSize, isAltKeyDown() || e.altKey);
    y = snapValue(y, gridSize, isAltKeyDown() || e.altKey);

    const def = getSymbolDefinition(data.type);
    const width = def?.defaultWidth || 80;
    const height = def?.defaultHeight || 80;

    addObject({
      type: data.type,
      category: data.category,
      x, y,
      width, height,
      rotation: 0,
      scaleX: 1,
      scaleY: 1,
      visible: true,
      locked: false,
      layer: 1,
      tag: `${data.type.replace(/\s+/g, '')}_1`,
      description: '',
      color: '#000000',
      fill: '#c0c0c0',
      border: '#000000',
      text: def?.label || data.type,
      font: FONT_UI,
      fontSize: FONT_SIZE_BASE,
      editor: {
        preview_state: def?.defaultState || ''
      },
      tooltip: '',
      customProperties: {}
    });
  };

  // Draw Grid: discreet minor lines every gridSize, a more pronounced
  // major line every 4th one - both darker than the canvas background,
  // both plain COLOR_OUTLINE at different opacities (no separate "grid
  // color" invented outside ScadaTheme).
  const drawGrid = () => {
    const lines = [];
    const width = useStore.getState().canvasConfig.width;
    const height = useStore.getState().canvasConfig.height;
    const minorOpacity = 0.12;
    const majorOpacity = 0.32;
    // Below GRID_THIN_BELOW_ZOOM (commit 4), only the major (every 4th)
    // line draws at all - at that scale every minor line packed this
    // close together on screen blurs into a solid gray plane instead of
    // reading as a grid.
    const onlyMajor = canvasState.zoom < GRID_THIN_BELOW_ZOOM;

    for (let i = 0; i * gridSize <= width; i++) {
      const isMajor = i % 4 === 0;
      if (onlyMajor && !isMajor) continue;
      lines.push(
        <Rect
          key={`v${i}`}
          x={i * gridSize}
          y={0}
          width={isMajor ? 1.5 : 1}
          height={height}
          fill={COLOR_OUTLINE}
          opacity={isMajor ? majorOpacity : minorOpacity}
          name="grid"
        />
      );
    }
    for (let j = 0; j * gridSize <= height; j++) {
      const isMajor = j % 4 === 0;
      if (onlyMajor && !isMajor) continue;
      lines.push(
        <Rect
          key={`h${j}`}
          x={0}
          y={j * gridSize}
          width={width}
          height={isMajor ? 1.5 : 1}
          fill={COLOR_OUTLINE}
          opacity={isMajor ? majorOpacity : minorOpacity}
          name="grid"
        />
      );
    }
    return lines;
  };

  // Shared group outline (commit 2f): when more than one element is
  // selected, across any mix of the four kinds, a single rectangle
  // drawn around the whole group's combined bounds - the same "this is
  // one selection" affordance a graphics program gives. A single
  // selected element already has its own outline (Transformer handles,
  // or one of the dashed rects above) - this only draws once there is
  // more than one item to show as a group. Ignores object rotation
  // (an axis-aligned box, not each object's own rotated bounds) - the
  // same simplification isObjectFullyInBox already makes for the
  // rubber-band box itself.
  const selectedTotalCount = selectedIds.length + selectedMeterIds.length + selectedSignalPanelIds.length + selectedFrameIds.length + selectedGroupCommandIds.length + selectedSetpointPanelIds.length + selectedConnectionIds.length;
  const selectionGroupBounds = (() => {
    if (selectedTotalCount <= 1) return null;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    const extend = (x1: number, y1: number, x2: number, y2: number) => {
      minX = Math.min(minX, x1, x2);
      minY = Math.min(minY, y1, y2);
      maxX = Math.max(maxX, x1, x2);
      maxY = Math.max(maxY, y1, y2);
    };
    objects.filter(o => selectedIds.includes(o.id)).forEach(o => extend(o.x, o.y, o.x + o.width, o.y + o.height));
    meters.filter(m => selectedMeterIds.includes(m.id)).forEach(m => extend(m.x, m.y, m.x + m.width, m.y + computeMeterHeight(m)));
    signalPanels.filter(p => selectedSignalPanelIds.includes(p.id)).forEach(p => extend(p.x, p.y, p.x + p.width, p.y + computeSignalPanelHeight(p)));
    frames.filter(f => selectedFrameIds.includes(f.id)).forEach(f => extend(f.x, f.y, f.x + f.width, f.y + f.height));
    groupCommands.filter(g => selectedGroupCommandIds.includes(g.id)).forEach(g => extend(g.x, g.y, g.x + g.width, g.y + computeGroupCommandHeight()));
    setpointPanels.filter(p => selectedSetpointPanelIds.includes(p.id)).forEach(p => extend(p.x, p.y, p.x + p.width, p.y + computeSetpointHeight(p)));
    connections.filter(c => selectedConnectionIds.includes(c.id)).forEach(c => c.points.forEach(pt => extend(pt.x, pt.y, pt.x, pt.y)));
    if (!Number.isFinite(minX)) return null;
    const padding = 8;
    return { x: minX - padding, y: minY - padding, width: (maxX - minX) + padding * 2, height: (maxY - minY) + padding * 2 };
  })();

  return (
    <div
      className="canvas-container"
      ref={containerRef}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <Stage
        width={size.width}
        height={size.height}
        ref={stageRef}
        scaleX={canvasState.zoom}
        scaleY={canvasState.zoom}
        x={canvasState.panX}
        y={canvasState.panY}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onDblClick={handleDblClick}
        onDblTap={handleDblClick}
        // fix/handles-insert-mode-diodes commit 2: the cursor differs
        // from the select cursor for the WHOLE time an insert tool is
        // armed (isDrawingFrame included, not just isDrawingConnection
        // as before) - not only once a drag is already underway.
        style={{ cursor: (isDrawingConnection || isDrawingFrame) ? 'crosshair' : (selectionStartRef.current ? 'crosshair' : 'default') }}
      >
        <Layer>
          {/* feat/appearance-selection-frames commit 2: both background
              rects need name="grid" too, not just the grid LINES drawn
              over them - handleMouseDown's own clickedOnEmpty check
              treats that name as "this is empty canvas, not an
              object", and grid lines cover only a sliver of the
              canvas's actual area (1-1.5px wide, GRID_SIZE apart) - an
              ordinary click almost always lands on one of these two
              rects instead, which had no name at all, so rubber-band
              selection could only ever start by landing exactly on a
              grid line. Confirmed by eye in the running app before this
              fix: dragging a marquee from ordinary empty space selected
              nothing. */}
          <Rect x={0} y={0} width={useStore.getState().canvasConfig.width} height={useStore.getState().canvasConfig.height} fill={useStore.getState().canvasConfig.background} name="grid" />
          <Rect x={0} y={0} width={canvasConfig.width || 1920} height={canvasConfig.height || 1080} fill={canvasConfig.background || COLOR_CANVAS_BACKGROUND} name="grid" />
          {drawGrid()}
        </Layer>
        <Layer>
          {/* The frame element (commit 3): pure background graphic, no
              terminals, no state - drawn first in this Layer so it sits
              BELOW every wire and symbol that follows (3e: "warstwa
              podkladu"), while still being above the grid/canvas
              background Layer above. A symbol placed inside a frame's
              own bounds draws later in this same Layer, so it is
              visible above the frame, per that same requirement. */}
          {/* feat/site-objects-2d commit 4: SURFACE objects (trawa,
              droga - SymbolDefinition.isSurface) are real objects[]
              entries, not a separate array like frames - but they must
              still draw in this same "warstwa podkladu" position,
              BELOW every wire and ordinary symbol (mandatory test 9;
              PRZED ZGLOSZENIEM point 6, "a symbol placed on the grass
              must appear above it"), exactly like FrameElementNode
              just above. Drawn here, in registration (array) order -
              not sorted by zIndex, the same "first drawn = furthest
              back" rule frames themselves already follow - and then
              excluded from the ordinary objects.map pass below so
              nothing renders twice. */}
          {objects.filter((obj) => getSymbolDefinition(obj.type)?.isSurface).map((obj) => (
            <ObjectNode
              key={obj.id}
              obj={obj}
              onSelect={(e: any) => selectObjects([obj.id], !!e?.evt?.shiftKey)}
              onChange={(newAttrs) => updateObject(obj.id, newAttrs)}
              gridSize={gridSize}
              onShapeRef={registerObjectShapeRef}
              groupDrag={groupDrag}
              forceShowTerminals={!!nearbyTerminalObjIds?.has(obj.id)}
              highlightedTerminalId={highlightedTerminal?.objId === obj.id ? highlightedTerminal.terminalId : null}
              drawingMedium={isDrawingConnection ? drawingMedium : null}
            />
          ))}
          {frames.map((frame) => (
            <FrameElementNode
              key={frame.id}
              frame={frame}
              onSelect={(e: any) => selectFrames([frame.id], !!e?.evt?.shiftKey)}
              onShapeRef={(node) => { groupDrag.registerNode(`frame:${frame.id}`, node); registerFrameShapeRef(frame.id, node); }}
              onDragStart={() => {
                if (isAltKeyDown()) useStore.getState().duplicateFrameInPlace(frame.id);
                groupDrag.start(`frame:${frame.id}`);
              }}
              onDragMove={(x, y) => {
                if (groupDrag.isActive()) groupDrag.follow(x - frame.x, y - frame.y);
              }}
              onDragEnd={(x, y) => {
                const finalX = snapValue(x, gridSize, isAltKeyDown());
                const finalY = snapValue(y, gridSize, isAltKeyDown());
                if (groupDrag.isActive()) {
                  groupDrag.commit(finalX - frame.x, finalY - frame.y);
                } else {
                  updateFrame(frame.id, { x: finalX, y: finalY });
                  useStore.getState().saveHistory();
                }
              }}
              onResize={(x, y, width, height) => {
                // fix/handles-insert-mode-diodes commit 1: x/y/width/
                // height arrive already grid-snapped and fixed-corner-
                // correct (FrameElementNode's own onTransformEnd calls
                // computeResizeFromAnchor) - re-snapping x/y and width/
                // height independently here, the way this used to work,
                // would risk shifting the corner that resize is
                // supposed to hold exactly still. Passed straight
                // through.
                updateFrame(frame.id, { x, y, width, height });
                useStore.getState().saveHistory();
              }}
            />
          ))}
          {/* Node-based wiring model: a connection draws itself straight
              through its own points array now - no from/to object lookup
              needed here at all (that whole indirection is gone). A
              finished wire can be selected, dragged as a whole, or have
              one of its own bends grabbed and moved (ConnectionNode). */}
          {connections.map(conn => (
            <ConnectionNode
              key={conn.id}
              conn={conn}
              netState={netStateByConnectionId.get(conn.id) ?? 'INACTIVE'}
              isSelected={selectedConnectionIds.includes(conn.id)}
              onSelect={(multi: boolean) => selectConnections([conn.id], multi)}
              gridSize={gridSize}
              onAltClickSegment={handleAltClickSegment}
              groupDrag={groupDrag}
              collisions={collisionsByConnectionId.get(conn.id)}
              onCollisionHover={setCollisionTooltip}
            />
          ))}
          {/* In-progress wire preview: a thin line through every point
              placed so far plus the live (grid-snapped) cursor position
              - thinner than the real conductor (not a committed
              connection yet), but already colored by the toolbar's
              selected medium (part C) so what is about to be drawn is
              visible before it lands. */}
          {drawingPoints && drawingPoints.length > 0 && (
            <>
              <Path
                data={pathFromPoints(drawingPreviewPoints || drawingPoints)}
                stroke={getConductorCoreColor(drawingMedium, 'ACTIVE')}
                strokeWidth={CONDUCTOR_WIDTH / 2}
                lineCap="round"
                lineJoin="round"
                listening={false}
              />
              {drawingPoints.map((p, idx) => (
                <Circle key={idx} x={p.x} y={p.y} radius={4} fill={getConductorCoreColor(drawingMedium, 'ACTIVE')} listening={false} />
              ))}
            </>
          )}
          {[...objects].filter((obj) => !getSymbolDefinition(obj.type)?.isSurface).sort((a, b) => (a.zIndex || 0) - (b.zIndex || 0)).map((obj) => (
            <ObjectNode
              key={obj.id}
              obj={obj}
              onSelect={(e: any) => selectObjects([obj.id], !!e?.evt?.shiftKey)}
              onChange={(newAttrs) => updateObject(obj.id, newAttrs)}
              gridSize={gridSize}
              onShapeRef={registerObjectShapeRef}
              groupDrag={groupDrag}
              forceShowTerminals={!!nearbyTerminalObjIds?.has(obj.id)}
              highlightedTerminalId={highlightedTerminal?.objId === obj.id ? highlightedTerminal.terminalId : null}
              drawingMedium={isDrawingConnection ? drawingMedium : null}
            />
          ))}
          {/* Topology junctions (layer 4 - deliberately ABOVE symbols,
              not below as the task's own layer list literally orders
              them): a wire node (from the SCADA library) wherever 3+
              segments, or 2 segments and a terminal, meet at one grid
              point - computed purely from geometry by NetResolver.
              getJunctionPoints. A junction routinely lands exactly at a
              terminal, which is often inside the object's own drawn
              shape, and painting it underneath would leave it
              invisible, hidden by the object itself - this deliberate
              deviation preserves that earlier fix; see raport.md. */}
          {junctionPoints.map((j, idx) => (
            <Group key={`junc-${idx}`} x={j.x - 75} y={j.y - 75} listening={false}>
              <WireNodeSymbol />
            </Group>
          ))}
          {/* The meter element (feat/meter-element): its own array, not
              a symbol - see MeterElement.ts's own header comment. Layer
              5 - after every symbol and junction, before labels. */}
          {meters.map((meter) => (
            <MeterElementNode
              key={meter.id}
              meter={meter}
              devices={devices}
              onSelect={(e: any) => selectMeters([meter.id], !!e?.evt?.shiftKey)}
              onShapeRef={(node) => groupDrag.registerNode(`meter:${meter.id}`, node)}
              onDragStart={() => {
                if (isAltKeyDown()) useStore.getState().duplicateMeterInPlace(meter.id);
                groupDrag.start(`meter:${meter.id}`);
              }}
              onDragMove={(x, y) => {
                if (groupDrag.isActive()) groupDrag.follow(x - meter.x, y - meter.y);
              }}
              onDragEnd={(x, y) => {
                const finalX = snapValue(x, gridSize, isAltKeyDown());
                const finalY = snapValue(y, gridSize, isAltKeyDown());
                if (groupDrag.isActive()) {
                  groupDrag.commit(finalX - meter.x, finalY - meter.y);
                } else {
                  updateMeter(meter.id, { x: finalX, y: finalY });
                  useStore.getState().saveHistory();
                }
              }}
              onResize={(x, width) => {
                // x/width already grid-snapped and clamped
                // (MeterElementNode's own onTransformEnd) - passed
                // straight through, same reasoning as the frame's own
                // onResize above.
                updateMeter(meter.id, { x, width });
                useStore.getState().saveHistory();
              }}
            />
          ))}
          {/* The signal panel element (commit 6): same mechanism as the
              meter, its own array - see elements/SignalPanelElement.ts.
              Same layer 5 as the meter. */}
          {signalPanels.map((panel) => (
            <SignalPanelElementNode
              key={panel.id}
              panel={panel}
              devices={devices}
              onSelect={(e: any) => selectSignalPanels([panel.id], !!e?.evt?.shiftKey)}
              onShapeRef={(node) => groupDrag.registerNode(`panel:${panel.id}`, node)}
              onDragStart={() => {
                if (isAltKeyDown()) useStore.getState().duplicateSignalPanelInPlace(panel.id);
                groupDrag.start(`panel:${panel.id}`);
              }}
              onDragMove={(x, y) => {
                if (groupDrag.isActive()) groupDrag.follow(x - panel.x, y - panel.y);
              }}
              onDragEnd={(x, y) => {
                const finalX = snapValue(x, gridSize, isAltKeyDown());
                const finalY = snapValue(y, gridSize, isAltKeyDown());
                if (groupDrag.isActive()) {
                  groupDrag.commit(finalX - panel.x, finalY - panel.y);
                } else {
                  updateSignalPanel(panel.id, { x: finalX, y: finalY });
                  useStore.getState().saveHistory();
                }
              }}
              onResize={(x, width) => {
                updateSignalPanel(panel.id, { x, width });
                useStore.getState().saveHistory();
              }}
            />
          ))}
          {/* The group command button (feat/control-elements commit 2):
              same mechanism as the meter/signal panel, its own array -
              see elements/GroupCommandElement.ts. No onResize (fixed-size
              button - see that file's own header for why). */}
          {groupCommands.map((el) => (
            <GroupCommandElementNode
              key={el.id}
              el={el}
              devices={devices}
              isSelected={selectedGroupCommandIds.includes(el.id)}
              onSelect={(e: any) => selectGroupCommands([el.id], !!e?.evt?.shiftKey)}
              onShapeRef={(node) => groupDrag.registerNode(`groupcmd:${el.id}`, node)}
              onDragStart={() => {
                if (isAltKeyDown()) useStore.getState().duplicateGroupCommandInPlace(el.id);
                groupDrag.start(`groupcmd:${el.id}`);
              }}
              onDragMove={(x, y) => {
                if (groupDrag.isActive()) groupDrag.follow(x - el.x, y - el.y);
              }}
              onDragEnd={(x, y) => {
                const finalX = snapValue(x, gridSize, isAltKeyDown());
                const finalY = snapValue(y, gridSize, isAltKeyDown());
                if (groupDrag.isActive()) {
                  groupDrag.commit(finalX - el.x, finalY - el.y);
                } else {
                  updateGroupCommand(el.id, { x: finalX, y: finalY });
                  useStore.getState().saveHistory();
                }
              }}
            />
          ))}
          {/* The setpoint panel element (feat/selector-symbol-setpoint-alarm):
              same mechanism as the meter/signal panel, for MODULATED
              devices instead of MEASURED ones - see
              elements/SetpointElement.ts. */}
          {setpointPanels.map((panel) => (
            <SetpointElementNode
              key={panel.id}
              panel={panel}
              devices={devices}
              onSelect={(e: any) => selectSetpointPanels([panel.id], !!e?.evt?.shiftKey)}
              onShapeRef={(node) => groupDrag.registerNode(`setpoint:${panel.id}`, node)}
              onDragStart={() => {
                if (isAltKeyDown()) useStore.getState().duplicateSetpointPanelInPlace(panel.id);
                groupDrag.start(`setpoint:${panel.id}`);
              }}
              onDragMove={(x, y) => {
                if (groupDrag.isActive()) groupDrag.follow(x - panel.x, y - panel.y);
              }}
              onDragEnd={(x, y) => {
                const finalX = snapValue(x, gridSize, isAltKeyDown());
                const finalY = snapValue(y, gridSize, isAltKeyDown());
                if (groupDrag.isActive()) {
                  groupDrag.commit(finalX - panel.x, finalY - panel.y);
                } else {
                  updateSetpointPanel(panel.id, { x: finalX, y: finalY });
                  useStore.getState().saveHistory();
                }
              }}
              onResize={(x, width) => {
                updateSetpointPanel(panel.id, { x, width });
                useStore.getState().saveHistory();
              }}
            />
          ))}
          {/* Layer 6, labels: a SEPARATE pass over every object, drawn
              after every symbol/junction/meter so a label never falls
              under another object's own shape - each wrapped in its own
              Group carrying the exact same x/y/rotation/scale transform
              ObjectNode's own Group already applies (ObjectLabelRenderer's
              own local coordinates and rotation-cancelling math are
              unchanged, only which Group they are nested inside). */}
          {objects.map((obj) => (
            <Group
              key={`label-${obj.id}`}
              x={obj.x}
              y={obj.y}
              rotation={obj.rotation || 0}
              scaleX={obj.scaleX || 1}
              scaleY={obj.scaleY || 1}
              visible={obj.visible !== false}
            >
              <ObjectLabelRenderer obj={obj} onChange={(newAttrs) => updateObject(obj.id, newAttrs)} />
            </Group>
          ))}
          {/* feat/device-list-ui commit 5: a symbol whose Aparat points
              at a device id no longer in the registry still renders
              completely normally (its own symbol/label above is
              unaffected) - this only adds a dashed alarm-colored outline
              on top, the same "problem, not a crash" treatment
              validateDeviceRegistry itself uses for a bad file. */}
          {objects.filter(obj => isSymbolDeviceMissing(obj, devices)).map(obj => (
            // Same Group transform ObjectNode's own shape uses (x/y is
            // the object's top-left, rotation pivots there too - see
            // utils/Terminals.ts's own getTerminalWorldPosition comment)
            // so this outline always tracks the real symbol exactly,
            // rotated/scaled or not.
            <Group key={`device-missing-${obj.id}`} x={obj.x} y={obj.y} rotation={obj.rotation || 0} scaleX={obj.scaleX || 1} scaleY={obj.scaleY || 1} listening={false}>
              <Rect
                width={obj.width}
                height={obj.height}
                stroke={COLOR_ALARM}
                strokeWidth={2}
                dash={[6, 4]}
                fill="transparent"
              />
            </Group>
          ))}
          {/* feat/control-elements commit 3: a symbol bound to a
              SWITCHED device with a configured interlock description
              gets a small badge at its own top-right corner - purely a
              "this command can be refused, see the device form for why"
              flag, never live logic (see InterlockIndicator.ts's own
              header). Same Group transform as the device-missing
              outline above, so it always tracks the real symbol. A
              filled circle + "!" glyph rather than a borrowed icon
              font's path data - crisp at any zoom, no external asset. */}
          {objects.filter(obj => isSymbolInterlocked(obj, devices)).map(obj => (
            <Group key={`interlock-${obj.id}`} x={obj.x} y={obj.y} rotation={obj.rotation || 0} scaleX={obj.scaleX || 1} scaleY={obj.scaleY || 1} listening={false}>
              <Circle
                x={obj.width - 7}
                y={7}
                radius={7}
                fill={COLOR_LAMP_LIT}
                stroke={COLOR_OUTLINE}
                strokeWidth={1}
              />
              <Text
                x={obj.width - 11}
                y={0}
                width={8}
                height={14}
                text="!"
                fontSize={FONT_SIZE_SMALL}
                fontFamily={FONT_UI}
                fontStyle="bold"
                fill={COLOR_OUTLINE}
                align="center"
                verticalAlign="middle"
              />
            </Group>
          ))}
          {/* Layer 7, selection and handles - always topmost. The
              in-progress wire's own preview stays in layer 2 (przewody)
              above, since it is a wire, not a selection. */}
          {selectedIds.filter(id => {
            const obj = objects.find(o => o.id === id);
            return obj && !obj.locked;
          }).map((id) => (
            <ObjectTransformerHandle
              key={`tr-${id}`}
              node={objectShapeRefs.current.get(id)}
            />
          ))}
          {/* fix/handles-insert-mode-diodes commit 1: a plain dashed
              Rect used to be the whole selection indicator for a meter
              or signal panel - now WidthOnlyTransformerHandle (its own
              Transformer already draws that same dashed border) so
              there is something to actually grab and resize width
              with. Reuses dragNodeRefs (the SAME map groupDrag's own
              registerNode already populates via each element's own
              onShapeRef below) rather than a second, parallel ref map
              just for this. */}
          {selectedMeterIds.map((id) => (
            <WidthOnlyTransformerHandle
              key={`meter-tr-${id}`}
              node={dragNodeRefs.current.get(`meter:${id}`)}
            />
          ))}
          {selectedSignalPanelIds.map((id) => (
            <WidthOnlyTransformerHandle
              key={`panel-tr-${id}`}
              node={dragNodeRefs.current.get(`panel:${id}`)}
            />
          ))}
          {selectedSetpointPanelIds.map((id) => (
            <WidthOnlyTransformerHandle
              key={`setpoint-tr-${id}`}
              node={dragNodeRefs.current.get(`setpoint:${id}`)}
            />
          ))}
          {selectedFrameIds.map((id) => (
            <FrameTransformerHandle
              key={`frame-tr-${id}`}
              node={frameShapeRefs.current.get(id)}
            />
          ))}
          {selectionGroupBounds && (
            <Rect
              x={selectionGroupBounds.x}
              y={selectionGroupBounds.y}
              width={selectionGroupBounds.width}
              height={selectionGroupBounds.height}
              stroke={COLOR_WHITE}
              strokeWidth={1.5}
              dash={[10, 6]}
              fill="transparent"
              listening={false}
            />
          )}
          {selectionBox && (
            <Rect
              x={selectionBox.x}
              y={selectionBox.y}
              width={selectionBox.width}
              height={selectionBox.height}
              fill={COLOR_WATER}
              fillOpacity={0.25}
              stroke={COLOR_WATER}
              strokeWidth={1}
            />
          )}
          {/* feat/wire-routing-around-obstacles commit 1: the hover
              tooltip naming which obstacle a marked segment crosses -
              a plain Rect+Text pair sized to the text, anchored just
              above the hovered segment's own midpoint. */}
          {collisionTooltip && (
            <Group x={collisionTooltip.x} y={collisionTooltip.y - 28} listening={false}>
              <Rect
                width={Math.max(60, collisionTooltip.label.length * 7 + 16)}
                height={20}
                offsetX={Math.max(60, collisionTooltip.label.length * 7 + 16) / 2}
                fill={COLOR_PANEL}
                stroke={COLOR_ALARM}
                strokeWidth={1.5}
                cornerRadius={3}
              />
              <Text
                text={collisionTooltip.label}
                width={Math.max(60, collisionTooltip.label.length * 7 + 16)}
                height={20}
                offsetX={Math.max(60, collisionTooltip.label.length * 7 + 16) / 2}
                align="center"
                verticalAlign="middle"
                fontSize={FONT_SIZE_SMALL}
                fontFamily={FONT_UI}
                fill={COLOR_OUTLINE}
              />
            </Group>
          )}
        </Layer>
      </Stage>
      {/* feat/tank-language-and-media commit 1, point (b): a plain HTML
          overlay (not a Konva node - Canvas's own outer div, not the
          Stage) so it renders exactly like every other modal in this
          app (AddLocationDialog.tsx's own convention). */}
      {mediaConflict && <MediaMismatchDialog conflict={mediaConflict} onClose={() => setMediaConflict(null)} />}
    </div>
  );
};
