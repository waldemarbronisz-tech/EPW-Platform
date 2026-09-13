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
import { tileRects, visibleScreens } from '../project/WorkspaceLayout';
import {
  COLOR_BEVEL_DARK, COLOR_BEVEL_LIGHT, COLOR_OUTLINE, COLOR_PANEL,
  COLOR_RUN, FONT_SIZE_SMALL, FONT_UI,
} from '../theme/ScadaTheme';

/** The caption strip on each tile. Tall enough to read, short enough not to eat the drawing. */
const CAPTION_HEIGHT = 20;

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

  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 600 });

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

  const tiles = useMemo(
    () => tileRects(layout, shown.length, size.width, size.height),
    [layout, shown.length, size.width, size.height]
  );

  const nameOf = (id: string) => screens.find(s => s.id === id)?.name ?? id;
  const multiple = shown.length > 1;

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
          e.stopPropagation();
          switchScreen(screenId);
        };

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
              left: tile.x,
              top: tile.y,
              width: tile.width,
              height: tile.height,
              // In cascade the panes overlap, and the active one has to
              // be on top - a live editor behind another window is
              // unusable.
              zIndex: isActive ? shown.length + 1 : tile.z + 1,
              display: 'flex',
              flexDirection: 'column',
              boxSizing: 'border-box',
              border: multiple
                ? `2px solid ${isActive ? COLOR_OUTLINE : COLOR_BEVEL_DARK}`
                : 'none',
              background: COLOR_PANEL,
              boxShadow: layout === 'cascade' ? '3px 3px 8px rgba(0,0,0,0.45)' : 'none',
            }}
          >
            {/* A single tile needs no caption: the screen tabs above
                already name it, and the strip would only cost height. */}
            {multiple && (
              <div
                style={captionStyle(isActive)}
                title={isActive ? 'Active screen' : 'Click to make this screen active'}
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
    </div>
  );
};
