// feat/workspace: an inactive screen's tile - drawn so it looks exactly
// like the editor it turns into the moment you touch it.
//
// Only one tile holds the real Canvas (the live arrays ARE the active
// screen, project/ScreenContent.ts). Every other tile is this: the same
// sheet, the same grid, the same walls, wires, panels and symbols, at the
// same zoom and pan the screen had when it was last active - or, for a
// screen never opened yet, fitted to its content the same way Canvas
// fits it on first activation. So activating a tile swaps the component
// underneath without anything on screen moving.
//
// It has NO interaction of its own. The first press, scroll or drag into
// a tile makes that tile active (ScreenWorkspace.tsx captures it before
// this stage ever sees it), which is why the layer does not listen at all.

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Stage, Layer, Group, Rect, Shape } from 'react-konva';
import { useStore } from '../store';
import { RoomFloorLayer } from './RoomFloorLayer';
import { WallLayer } from './WallLayer';
import { IlluminanceLayer } from './IlluminanceLayer';
import { ConnectionLine } from './ConnectionLine';
import { FrameElementNode } from './FrameElementNode';
import { MeterElementNode } from './MeterElementNode';
import { SignalPanelElementNode } from './SignalPanelElementNode';
import { GroupCommandElementNode } from './GroupCommandElementNode';
import { SetpointElementNode } from './SetpointElementNode';
import { ObjectLabelRenderer } from './ObjectLabelRenderer';
import { SymbolRenderer } from '../symbols/SymbolRenderer';
import { resolveNets } from '../project/NetResolver';
import { blankScreenContent } from '../project/ScreenContent';
import type { ScreenContent } from '../project/ScreenContent';
import { computeFitView, computePlanBounds, GRID_THIN_BELOW_ZOOM } from '../utils/CanvasView';
import { COLOR_CANVAS_BACKGROUND, COLOR_OUTLINE, FONT_UI } from '../theme/ScadaTheme';

export interface ScreenViewProps {
  screenId: string;
}

const noop = () => {};

export const ScreenView: React.FC<ScreenViewProps> = ({ screenId }) => {
  const activeScreenId = useStore(s => s.activeScreenId);
  const screenContents = useStore(s => s.screenContents);
  const savedView = useStore(s => s.screenViews[screenId]);
  const showIlluminance = useStore(s => s.showIlluminance);
  const canvasConfig = useStore(s => s.canvasConfig);
  const devices = useStore(s => s.devices);

  // The live arrays, used only if this ever renders the active screen.
  const objects = useStore(s => s.objects);
  const connections = useStore(s => s.connections);
  const meters = useStore(s => s.meters);
  const signalPanels = useStore(s => s.signalPanels);
  const frames = useStore(s => s.frames);
  const walls = useStore(s => s.walls);
  const groupCommands = useStore(s => s.groupCommands);
  const setpointPanels = useStore(s => s.setpointPanels);

  const isActive = screenId === activeScreenId;
  const content: ScreenContent = useMemo(
    () => (isActive
      ? {
        ...blankScreenContent(),
        objects, connections, meters, signalPanels, frames, walls, groupCommands, setpointPanels,
        floorMaterial: canvasConfig.floorMaterial,
      }
      : (screenContents[screenId] ?? blankScreenContent())),
    [isActive, objects, connections, meters, signalPanels, frames, walls, groupCommands, setpointPanels,
      canvasConfig.floorMaterial, screenContents, screenId]
  );

  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver(entries => {
      for (const entry of entries) {
        setSize({ width: entry.contentRect.width, height: entry.contentRect.height });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // The screen's own remembered view when it has one; otherwise the same
  // fit Canvas applies on first activation, so nothing jumps.
  const view = useMemo(() => {
    if (savedView) return savedView;
    const bounds = computePlanBounds(content.objects, content.meters, content.connections, content.walls);
    return computeFitView(bounds, size.width, size.height);
  }, [savedView, content, size.width, size.height]);

  const netStateByConnectionId = useMemo(() => {
    const map = new Map<string, 'ACTIVE' | 'INACTIVE'>();
    resolveNets(content.connections, content.objects, devices).forEach(net => {
      net.connectionIds.forEach(id => map.set(id, net.state));
    });
    return map;
  }, [content.connections, content.objects, devices]);

  const sheetWidth = canvasConfig.width || 1920;
  const sheetHeight = canvasConfig.height || 1080;
  const gridSize = canvasConfig.gridSize;
  const onlyMajor = view.zoom < GRID_THIN_BELOW_ZOOM;
  const empty = content.objects.length === 0 && content.walls.length === 0
    && content.connections.length === 0 && content.meters.length === 0
    && content.frames.length === 0 && content.signalPanels.length === 0;

  return (
    // Same class as the editor's own container, so the border, margin and
    // therefore the measured stage size are identical - a few pixels of
    // difference here would make the drawing shift on activation.
    <div ref={containerRef} className="canvas-container" style={{ position: 'relative' }}>
      {size.width > 0 && (
        <Stage
          width={size.width}
          height={size.height}
          scaleX={view.zoom}
          scaleY={view.zoom}
          x={view.panX}
          y={view.panY}
        >
          <Layer listening={false}>
            <Rect x={0} y={0} width={sheetWidth} height={sheetHeight} fill={canvasConfig.background || COLOR_CANVAS_BACKGROUND} />
            {/* The editor's grid, drawn in one shape rather than a Rect
                per line - there can be a dozen of these tiles on screen,
                and several hundred nodes each would be felt. Same
                spacing, weights and opacities as Canvas's own drawGrid. */}
            <Shape
              sceneFunc={(ctx: any) => {
                ctx.setAttr('fillStyle', COLOR_OUTLINE);
                for (let i = 0; i * gridSize <= sheetWidth; i++) {
                  const major = i % 4 === 0;
                  if (onlyMajor && !major) continue;
                  ctx.setAttr('globalAlpha', major ? 0.32 : 0.12);
                  ctx.fillRect(i * gridSize, 0, major ? 1.5 : 1, sheetHeight);
                }
                for (let j = 0; j * gridSize <= sheetHeight; j++) {
                  const major = j % 4 === 0;
                  if (onlyMajor && !major) continue;
                  ctx.setAttr('globalAlpha', major ? 0.32 : 0.12);
                  ctx.fillRect(0, j * gridSize, sheetWidth, major ? 1.5 : 1);
                }
                ctx.setAttr('globalAlpha', 1);
              }}
            />
            <RoomFloorLayer walls={content.walls} objects={content.objects} floorMaterial={content.floorMaterial} />
            {showIlluminance && <IlluminanceLayer walls={content.walls} objects={content.objects} />}
            <WallLayer
              walls={content.walls}
              objects={content.objects}
              selectedWallIds={[]}
              previewMode
              onSelect={noop}
              onDragEnd={noop}
            />
            {content.frames.map(frame => (
              <FrameElementNode key={frame.id} frame={frame} onSelect={noop} onDragEnd={noop} />
            ))}
            {content.connections.map(conn => (
              <ConnectionLine
                key={conn.id}
                conn={conn}
                netState={netStateByConnectionId.get(conn.id) ?? 'INACTIVE'}
                isSelected={false}
                onSelect={noop}
              />
            ))}
            {content.meters.map(meter => (
              <MeterElementNode key={meter.id} meter={meter} devices={devices} onSelect={noop} onDragEnd={noop} />
            ))}
            {content.signalPanels.map(panel => (
              <SignalPanelElementNode key={panel.id} panel={panel} devices={devices} onSelect={noop} onDragEnd={noop} />
            ))}
            {content.groupCommands.map(el => (
              <GroupCommandElementNode key={el.id} el={el} devices={devices} isSelected={false} onSelect={noop} onDragEnd={noop} />
            ))}
            {content.setpointPanels.map(panel => (
              <SetpointElementNode key={panel.id} panel={panel} devices={devices} onSelect={noop} onDragEnd={noop} />
            ))}
            {content.objects.map(obj => (
              <Group
                key={obj.id}
                x={obj.x}
                y={obj.y}
                rotation={obj.rotation || 0}
                scaleX={obj.scaleX || 1}
                scaleY={obj.scaleY || 1}
                visible={obj.visible !== false}
              >
                <SymbolRenderer obj={obj} />
                <ObjectLabelRenderer obj={obj} onChange={noop} />
              </Group>
            ))}
          </Layer>
        </Stage>
      )}

      {empty && (
        <div
          style={{
            position: 'absolute', inset: 0, display: 'flex',
            alignItems: 'center', justifyContent: 'center',
            fontFamily: FONT_UI, color: COLOR_OUTLINE, opacity: 0.6,
            pointerEvents: 'none',
          }}
        >
          This screen is empty - click to start drawing on it.
        </div>
      )}
    </div>
  );
};
