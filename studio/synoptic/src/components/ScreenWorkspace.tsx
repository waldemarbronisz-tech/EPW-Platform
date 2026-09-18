// feat/workspace: the drawing area - every screen of the project on show
// as a tiled window, and whichever one you work in is the active one.
//
// ONE TILE HOLDS THE EDITOR. The live objects/walls arrays ARE the active
// screen (project/ScreenContent.ts), so only one tile can hold the real
// Canvas; the rest draw their screen through ScreenView. The user never
// has to care: pressing the mouse, scrolling or dragging a symbol into
// ANY tile makes that tile active first, the Canvas moves into it, and
// the lower panel follows. Because every screen keeps its own zoom, pan
// and undo stack (workspaceSlice.ts), the swap is not visible - the tile
// looks exactly the same before and after it becomes live.
//
// Tiles stay in PROJECT order whichever one is active (visibleScreens),
// so windows never trade places under the cursor.

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useStore } from '../store';
import { Canvas } from './Canvas';
import { ScreenView } from './ScreenView';
import {
  FULL_FRAME, frameFromRect, freeTileRects, isFullFrame, rectFromFrame, snapZone, tileRects, visibleScreens,
} from '../project/WorkspaceLayout';
import type { TileFrame, WorkspaceTile } from '../project/WorkspaceLayout';
import {
  COLOR_BEVEL_DARK, COLOR_BEVEL_LIGHT, COLOR_OUTLINE, COLOR_PANEL,
  COLOR_RUN, FONT_SIZE_SMALL, FONT_UI,
} from '../theme/ScadaTheme';

/** The caption strip on each tile. Tall enough to read, short enough not to eat the drawing. */
const CAPTION_HEIGHT = 20;

/** What a caption drag looks like while it is going on: the tile follows the pointer, and the snap target (if the pointer is at an edge) is previewed. */
interface CaptionDrag {
  screenId: string;
  x: number;
  y: number;
  zone: TileFrame | null;
}

const captionStyle = (active: boolean): React.CSSProperties => ({
  height: CAPTION_HEIGHT,
  flex: '0 0 auto',
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  padding: '0 6px',
  boxSizing: 'border-box',
  // The active tile's caption is the one strong colour in the workspace -
  // with four similar rooms tiled, "which one am I working in" has to be
  // answerable without moving the mouse.
  background: active ? COLOR_OUTLINE : COLOR_PANEL,
  color: active ? COLOR_BEVEL_LIGHT : COLOR_OUTLINE,
  fontFamily: FONT_UI,
  fontSize: FONT_SIZE_SMALL,
  fontWeight: active ? 'bold' : 'normal',
  whiteSpace: 'nowrap',
  overflow: 'hidden',
  userSelect: 'none',
});

export const ScreenWorkspace: React.FC = () => {
  const screens = useStore(s => s.screens);
  const activeScreenId = useStore(s => s.activeScreenId);
  const switchScreen = useStore(s => s.switchScreen);
  const layout = useStore(s => s.workspaceLayout);
  const hiddenScreens = useStore(s => s.hiddenScreens);
  const hideScreen = useStore(s => s.hideScreen);
  const simulationRunning = useStore(s => s.simulationRunning);
  const tileFrames = useStore(s => s.tileFrames);
  const setTileFrame = useStore(s => s.setTileFrame);
  const arrangeFreely = useStore(s => s.arrangeFreely);

  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 600 });
  const [drag, setDrag] = useState<CaptionDrag | null>(null);
  // The frame a maximised tile goes back to on the next double-click.
  const restoreRef = useRef<Record<string, TileFrame>>({});

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const observer = new ResizeObserver(entries => {
      for (const entry of entries) {
        setSize({ width: entry.contentRect.width, height: entry.contentRect.height });
      }
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const shown = useMemo(
    () => visibleScreens(hiddenScreens, activeScreenId, layout, screens.map(s => s.id)),
    [hiddenScreens, activeScreenId, layout, screens]
  );

  const tiles = useMemo(() => {
    // `free` falls back to the grid for a screen that has no frame yet.
    const base = tileRects(layout === 'free' ? 'grid' : layout, shown.length, size.width, size.height);
    return layout === 'free' ? freeTileRects(shown, tileFrames, base, size.width, size.height) : base;
  }, [layout, shown, tileFrames, size.width, size.height]);

  const nameOf = (id: string) => screens.find(s => s.id === id)?.name ?? id;
  const multiple = shown.length > 1;

  /** Every shown tile's current place as a frame - what the first drag freezes before the dragged one moves. */
  const currentFrames = (): Record<string, TileFrame> =>
    Object.fromEntries(shown.map((id, index) => [id, frameFromRect(tiles[index], size.width, size.height)]));

  // feat/window-snapping: grab a caption and move the tile; drop at an
  // edge to snap (top = whole area, side = that half, corner = that
  // quarter), drop anywhere else to leave it there. Pointer events on the
  // window, not the caption, so the drag survives the pointer leaving
  // the tile - and the tile itself, which re-renders under the pointer.
  const beginCaptionDrag = (e: React.PointerEvent, screenId: string, tile: WorkspaceTile) => {
    if (e.button !== 0 || !multiple) return;
    const container = containerRef.current;
    if (!container) return;
    e.preventDefault();
    e.stopPropagation();
    const rect = container.getBoundingClientRect();
    const start = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    const state = { x: tile.x, y: tile.y, zone: null as TileFrame | null, moved: false };
    const move = (ev: PointerEvent) => {
      const px = ev.clientX - rect.left;
      const py = ev.clientY - rect.top;
      const dx = px - start.x;
      const dy = py - start.y;
      if (Math.abs(dx) + Math.abs(dy) > 2) state.moved = true;
      state.x = Math.min(Math.max(0, tile.x + dx), Math.max(0, size.width - tile.width));
      state.y = Math.min(Math.max(0, tile.y + dy), Math.max(0, size.height - tile.height));
      state.zone = snapZone(px, py, size.width, size.height);
      setDrag({ screenId, x: state.x, y: state.y, zone: state.zone });
    };
    const up = () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
      setDrag(null);
      if (!state.moved) return;
      const frames = layout === 'free' ? {} : currentFrames();
      const dropped = state.zone
        ?? frameFromRect({ x: state.x, y: state.y, width: tile.width, height: tile.height }, size.width, size.height);
      arrangeFreely({ ...frames, [screenId]: dropped });
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
    setDrag({ screenId, x: tile.x, y: tile.y, zone: null });
  };

  /** Double-click on a caption: the whole area, and back again. */
  const toggleMaximize = (screenId: string, index: number) => {
    if (!multiple) return;
    const current = tileFrames[screenId];
    if (layout === 'free' && isFullFrame(current)) {
      setTileFrame(screenId, restoreRef.current[screenId] ?? { x: 0.1, y: 0.1, width: 0.6, height: 0.6 });
      return;
    }
    restoreRef.current[screenId] = current ?? frameFromRect(tiles[index], size.width, size.height);
    const frames = layout === 'free' ? {} : currentFrames();
    arrangeFreely({ ...frames, [screenId]: FULL_FRAME });
  };

  return (
    <div
      ref={containerRef}
      style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden', background: COLOR_PANEL }}
    >
      {shown.map((screenId, index) => {
        const tile = tiles[index];
        if (!tile) return null;
        const isActive = screenId === activeScreenId;

        // Working in a tile makes it active. Captured on the way DOWN,
        // before the tile's own stage sees the event, and stopped there:
        // the press that activates a tile must not also operate a lamp
        // or start a marquee in the view that is about to be replaced.
        const activate = (e: React.SyntheticEvent) => {
          if (isActive) return;
          // A press on the caption both activates the tile AND may start
          // a drag - so that one is let through to the caption's own
          // handler instead of being stopped here.
          const target = e.target as HTMLElement | null;
          if (!target?.closest?.('[data-tile-caption]')) e.stopPropagation();
          switchScreen(screenId);
        };
        const dragging = drag?.screenId === screenId;
        const left = dragging ? drag!.x : tile.x;
        const top = dragging ? drag!.y : tile.y;

        return (
          <div
            key={screenId}
            onPointerDownCapture={activate}
            onMouseDownCapture={activate}
            onTouchStartCapture={activate}
            onWheelCapture={activate}
            // A symbol dragged from the library over a tile activates it
            // straight away, WITHOUT stopping the event: the Canvas
            // mounts under the cursor while the drag is still going on
            // and receives the drop itself, exactly as if the tile had
            // been active all along.
            onDragEnterCapture={() => { if (!isActive) switchScreen(screenId); }}
            style={{
              position: 'absolute',
              left,
              top,
              width: tile.width,
              height: tile.height,
              // In cascade (and the free arrangement) the panes overlap,
              // and the active one has to be on top - a live editor
              // behind another window is unusable. A tile being dragged
              // is above everything.
              zIndex: dragging ? shown.length + 3 : (isActive ? shown.length + 1 : tile.z + 1),
              opacity: dragging ? 0.85 : 1,
              display: 'flex',
              flexDirection: 'column',
              boxSizing: 'border-box',
              border: multiple
                ? `2px solid ${isActive ? COLOR_OUTLINE : COLOR_BEVEL_DARK}`
                : 'none',
              background: COLOR_PANEL,
              boxShadow: layout === 'cascade' || layout === 'free' ? '3px 3px 8px rgba(0,0,0,0.45)' : 'none',
            }}
          >
            {/* A single tile needs no caption: the screen tabs above
                already name it, and the strip would only cost height. */}
            {multiple && (
              <div
                data-tile-caption="1"
                style={{ ...captionStyle(isActive), cursor: 'move', touchAction: 'none' }}
                title={isActive
                  ? 'Active screen - drag to move, drop at an edge to snap, double-click to maximise'
                  : 'Click to make this screen active - drag to move, drop at an edge to snap'}
                onPointerDown={e => beginCaptionDrag(e, screenId, tile)}
                onDoubleClick={e => { e.stopPropagation(); toggleMaximize(screenId, index); }}
              >
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{nameOf(screenId)}</span>
                {isActive && <span style={{ opacity: 0.85 }}>ACTIVE</span>}
                {isActive && simulationRunning && (
                  <span style={{ color: COLOR_RUN }}>SIMULATION</span>
                )}
                <span style={{ flex: 1 }} />
                {/* Takes the tile off the workspace only. The screen
                    stays in the project and comes back from View. */}
                <button
                  onClick={e => { e.stopPropagation(); hideScreen(screenId); }}
                  onPointerDownCapture={e => e.stopPropagation()}
                  onMouseDownCapture={e => e.stopPropagation()}
                  title="Hide this tile (the screen stays in the project)"
                  style={{ padding: '0 4px', lineHeight: 1 }}
                >
                  x
                </button>
              </div>
            )}

            {/* display:flex, and not merely tidiness. Canvas's own
                container is `.canvas-container { flex: 1 }`, which does
                nothing inside a plain block parent - the container then
                collapsed to a stage sized from its last measurement and
                the two settled at the 600 px default forever. That was
                the dead grey band under the drawing. */}
            <div style={{ flex: 1, minHeight: 0, position: 'relative', display: 'flex' }}>
              {isActive
                ? <Canvas />
                : <ScreenView screenId={screenId} />}
            </div>
          </div>
        );
      })}

      {/* The snap preview: where the dragged tile will land if dropped now. */}
      {drag?.zone && (() => {
        const target = rectFromFrame(drag.zone, size.width, size.height);
        return (
          <div
            data-snap-preview="1"
            style={{
              position: 'absolute',
              left: target.x,
              top: target.y,
              width: target.width,
              height: target.height,
              zIndex: shown.length + 2,
              pointerEvents: 'none',
              boxSizing: 'border-box',
              border: `2px dashed ${COLOR_OUTLINE}`,
              background: 'rgba(0, 0, 128, 0.18)',
            }}
          />
        );
      })()}
    </div>
  );
};
