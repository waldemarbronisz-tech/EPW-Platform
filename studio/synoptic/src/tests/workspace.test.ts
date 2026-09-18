// feat/workspace: the multi-screen drawing area and the panel of tools
// beneath it.
//
// Everything checked here is a PURE function again - the tiling
// arithmetic (WorkspaceLayout.ts), the visible-screen rule
// (workspaceSlice.ts) and the compilation checks (ScreenValidation.ts)
// were all written beside their data precisely so they could be verified
// with exact expected values rather than by mounting a workspace and
// measuring pixels. The wiring claims with no runnable harness are
// checked by source scan, the convention this suite already uses.

import { describe, it, expect } from 'vitest';
import {
  fitsComfortably, gridShape, tileRects, visibleScreens, MIN_TILE, TILE_GAP, WORKSPACE_LAYOUTS,
} from '../project/WorkspaceLayout';

import { validateScreen, summarizeValidation } from '../project/ScreenValidation';
import type { SynopticObject } from '../store';
import type { WallElement } from '../elements/WallElement';
import type { Device } from '../project/DeviceSchema';
import { WALL_DEFAULT_THICKNESS } from '../elements/WallElement';

import workspaceSource from '../components/ScreenWorkspace.tsx?raw';
import secondaryPanelSource from '../components/SecondaryPanel.tsx?raw';
import screenViewSource from '../components/ScreenView.tsx?raw';
import canvasSource from '../components/Canvas.tsx?raw';
import viewMenuSource from '../components/ViewMenu.tsx?raw';

const obj = (id: string, type: string, extra: Partial<SynopticObject> = {}): SynopticObject => ({
  id, type, category: 'BUILDING', x: 100, y: 100, rotation: 0, scaleX: 1, scaleY: 1,
  visible: true, locked: false, layer: 0, tag: '', description: '',
  color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
  tooltip: '', width: 32, height: 32, customProperties: {},
  ...extra,
});

const wall = (from: [number, number], to: [number, number]): WallElement => ({
  id: `${from.join(',')}->${to.join(',')}`,
  from: { x: from[0], y: from[1] },
  to: { x: to[0], y: to[1] },
  thickness: WALL_DEFAULT_THICKNESS,
});

/** A square room, drawn as a closed chain so a floor and a lighting grid exist. */
const closedRoom = (): WallElement[] => [
  wall([0, 0], [400, 0]),
  wall([400, 0], [400, 400]),
  wall([400, 400], [0, 400]),
  wall([0, 400], [0, 0]),
];

const switchedDevice = (id: string, overrides: Partial<Device> = {}): Device => ({
  id,
  designation: `-K${id}`,
  name: 'Stycznik',
  behavior: 'SWITCHED',
  kind: 'contactor',
  publishToHa: false,
  feedback: { mode: 'NONE' },
  command: { outputCount: 1, style: 'MAINTAINED', doClose: 'ELA1.DO.1' },
  supervision: { confirmTimeoutMs: 5000, discrepancyAlarm: false },
  safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' },
  switchCounter: false,
  ...overrides,
} as Device);

// ---------------------------------------------------------------------
describe('workspace tiling', () => {
  it('gives the whole area to a single pane, whatever the arrangement asks for', () => {
    for (const layout of WORKSPACE_LAYOUTS) {
      const tiles = tileRects(layout.id, 1, 800, 600);
      expect(tiles).toHaveLength(1);
      expect(tiles[0]).toMatchObject({ x: 0, y: 0, width: 800, height: 600 });
    }
  });

  it('stacks rows full width and columns full height', () => {
    const rows = tileRects('rows', 3, 900, 600);
    expect(rows.map(t => t.width)).toEqual([900, 900, 900]);
    // Three bands plus two gutters must add back up to the height given.
    const totalHeight = rows.reduce((sum, t) => sum + t.height, 0) + TILE_GAP * 2;
    expect(Math.abs(totalHeight - 600)).toBeLessThanOrEqual(3);

    const columns = tileRects('columns', 3, 900, 600);
    expect(columns.map(t => t.height)).toEqual([600, 600, 600]);
    expect(columns[0].y).toBe(0);
    expect(columns[2].x).toBeGreaterThan(columns[1].x);
  });

  it('lays a grid out as squarely as it can, wider than tall when it cannot be square', () => {
    expect(gridShape('grid', 4)).toEqual({ columns: 2, rows: 2 });
    expect(gridShape('grid', 6)).toEqual({ columns: 3, rows: 2 });
    expect(gridShape('grid', 9)).toEqual({ columns: 3, rows: 3 });
  });

  it('stretches a short last row instead of leaving a hole at the end of it', () => {
    // 3 panes in a 2x2 grid: the third is alone on its row and takes the
    // whole width, the way every tiling window manager lays it out.
    const tiles = tileRects('grid', 3, 800, 600);
    expect(tiles[0].width).toBeLessThan(500);
    expect(tiles[2].width).toBe(800);
    expect(tiles[2].x).toBe(0);
  });

  it('never lets a tile fall outside the area it was given', () => {
    for (const layout of WORKSPACE_LAYOUTS) {
      for (const count of [2, 3, 5, 8]) {
        for (const tile of tileRects(layout.id, count, 1000, 700)) {
          expect(tile.x).toBeGreaterThanOrEqual(0);
          expect(tile.y).toBeGreaterThanOrEqual(0);
          expect(tile.x + tile.width).toBeLessThanOrEqual(1000 + 1);
          expect(tile.y + tile.height).toBeLessThanOrEqual(700 + 1);
        }
      }
    }
  });

  it('offsets cascaded panes and keeps them stacked in order', () => {
    const tiles = tileRects('cascade', 4, 1000, 700);
    for (let i = 1; i < tiles.length; i++) {
      expect(tiles[i].x).toBeGreaterThan(tiles[i - 1].x);
      expect(tiles[i].y).toBeGreaterThan(tiles[i - 1].y);
      expect(tiles[i].z).toBeGreaterThan(tiles[i - 1].z);
    }
    // Same size, like sheets of paper on a desk.
    expect(new Set(tiles.map(t => t.width)).size).toBe(1);
  });

  it('still returns every pane asked for in an area too small for them', () => {
    // Clamping the COUNT would mean a screen the user added silently not
    // existing, which is worse than a cramped one.
    const tiles = tileRects('grid', 9, 200, 150);
    expect(tiles).toHaveLength(9);
    expect(fitsComfortably('grid', 9, 200, 150)).toBe(false);
    expect(fitsComfortably('grid', 4, 1200, 800)).toBe(true);
    expect(MIN_TILE).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------
describe('which screens are on show', () => {
  it('shows only the active screen in the single view', () => {
    expect(visibleScreens([], 'a', 'single', ['a', 'b'])).toEqual(['a']);
  });

  it('shows every screen by default - a new screen needs no ticking', () => {
    expect(visibleScreens([], 'a', 'grid', ['a', 'b', 'c'])).toEqual(['a', 'b', 'c']);
  });

  it('keeps PROJECT order whichever screen is active, so tiles never swap places', () => {
    expect(visibleScreens([], 'c', 'grid', ['a', 'b', 'c'])).toEqual(['a', 'b', 'c']);
  });

  it('leaves out hidden screens, but never the active one', () => {
    expect(visibleScreens(['b'], 'a', 'rows', ['a', 'b', 'c'])).toEqual(['a', 'c']);
    expect(visibleScreens(['a'], 'a', 'rows', ['a', 'b'])).toEqual(['a', 'b']);
  });

  it('never tiles a screen that has been deleted', () => {
    expect(visibleScreens([], 'a', 'grid', ['a'])).toEqual(['a']);
  });
});

// ---------------------------------------------------------------------
describe('compilation checks', () => {
  it('reports a fixture that belongs to no circuit as an error', () => {
    const result = validateScreen([obj('l1', 'building.luminaire')], [], [], []);
    expect(result.errors).toBe(1);
    expect(result.runnable).toBe(false);
    expect(result.issues[0].objectId).toBe('l1');
    expect(result.issues[0].message).toContain('circuit');
  });

  it('reports a circuit with no aparat behind it, and names the circuit', () => {
    const result = validateScreen(
      [obj('l1', 'building.luminaire', { circuit: 'OBW_1' })],
      [], [], []
    );
    const issue = result.issues.find(i => i.code.startsWith('circuit-unbound'));
    expect(issue).toBeDefined();
    expect(issue!.severity).toBe('ERROR');
    expect(issue!.circuit).toBe('OBW_1');
  });

  it('reports a binding whose device has been deleted from the registry', () => {
    const result = validateScreen(
      [obj('l1', 'building.luminaire', { circuit: 'OBW_1' })],
      [],
      [{ name: 'OBW_1', deviceId: 'gone' }],
      []
    );
    expect(result.issues.some(i => i.code.startsWith('circuit-dangling'))).toBe(true);
    expect(result.runnable).toBe(false);
  });

  it('does NOT treat a missing feedback as a fault - it is the normal case for lighting', () => {
    // The whole point of CircuitBindings.ts's header: a lamp on a plain
    // DO has nothing to read back, and an editor that alarmed about it
    // would alarm on every healthy installation.
    const result = validateScreen(
      [obj('l1', 'building.luminaire', { circuit: 'OBW_1' })],
      closedRoom(),
      [{ name: 'OBW_1', deviceId: 'K1' }],
      [switchedDevice('K1')]
    );
    expect(result.errors).toBe(0);
    expect(result.runnable).toBe(true);
    const assumed = result.issues.find(i => i.code.startsWith('circuit-assumed'));
    expect(assumed).toBeDefined();
    expect(assumed!.severity).toBe('INFO');
    expect(assumed!.message).toContain('assumed from DO');
  });

  it('warns when one aparat drives two separate circuits', () => {
    const result = validateScreen(
      [
        obj('l1', 'building.luminaire', { circuit: 'OBW_1' }),
        obj('l2', 'building.luminaire', { circuit: 'OBW_2' }),
      ],
      closedRoom(),
      [{ name: 'OBW_1', deviceId: 'K1' }, { name: 'OBW_2', deviceId: 'K1' }],
      [switchedDevice('K1')]
    );
    const shared = result.issues.find(i => i.code.startsWith('device-shared'));
    expect(shared).toBeDefined();
    expect(shared!.severity).toBe('WARNING');
    // A warning is an opinion, not a blocker.
    expect(result.runnable).toBe(true);
  });

  it('warns about an opening that is not seated in any wall', () => {
    const result = validateScreen(
      [obj('d1', 'building.door', { x: 2000, y: 2000, width: 80, height: 16 })],
      closedRoom(), [], []
    );
    expect(result.issues.some(i => i.code.startsWith('opening-loose'))).toBe(true);
  });

  it('warns about walls that do not close, and about a luminaire outside the room', () => {
    const open = [wall([0, 0], [400, 0]), wall([400, 0], [400, 400])];
    expect(validateScreen([], open, [], []).issues.some(i => i.code === 'walls-open')).toBe(true);

    const outside = validateScreen(
      [obj('l1', 'building.luminaire', { circuit: 'OBW_1', x: 5000, y: 5000 })],
      closedRoom(),
      [{ name: 'OBW_1', deviceId: 'K1' }],
      [switchedDevice('K1')]
    );
    expect(outside.issues.some(i => i.code.startsWith('fixture-outside'))).toBe(true);
  });

  it('says so plainly when there is nothing to report', () => {
    expect(summarizeValidation(validateScreen([], [], [], []))).toBe('Build check OK');
    const bad = validateScreen([obj('l1', 'building.luminaire')], [], [], []);
    expect(summarizeValidation(bad)).toContain('1 err.');
  });

  it('leaves furniture entirely alone - a chair is not an unassigned aparat', () => {
    const result = validateScreen(
      [obj('c1', 'building.chair'), obj('t1', 'building.table')],
      closedRoom(), [], []
    );
    expect(result.errors).toBe(0);
  });
});

// ---------------------------------------------------------------------
describe('workspace wiring (source scan)', () => {
  it('puts the real editor in exactly one tile and read-only views in the rest', () => {
    // The live arrays ARE the active screen, so two Canvases over one
    // store would be two editors of the same document.
    expect(workspaceSource).toContain('isActive');
    expect(workspaceSource).toContain('<Canvas />');
    expect(workspaceSource).toContain('<ScreenView screenId={screenId} />');
  });

  it('makes a tile active the moment you work in it, before its stage sees the press', () => {
    expect(workspaceSource).toContain('onPointerDownCapture={activate}');
    expect(workspaceSource).toContain('onMouseDownCapture={activate}');
    expect(workspaceSource).toContain('onWheelCapture={activate}');
    // A dragged symbol activates the tile WITHOUT being stopped, so the
    // freshly mounted Canvas still receives the drop.
    expect(workspaceSource).toContain('onDragEnterCapture');
  });

  it('draws an inactive tile with the same container, sheet and remembered view as the editor', () => {
    expect(screenViewSource).toContain('className="canvas-container"');
    expect(screenViewSource).toContain('screenViews[screenId]');
    expect(screenViewSource).toContain('computePlanBounds');
    expect(screenViewSource).toContain('<Layer listening={false}>');
  });

  it('routes every circuit click on the editor through operateAt', () => {
    expect(canvasSource).toContain('operateAt(objectId)');
    expect(canvasSource).not.toContain('toggleCircuitAt(objectId)');
  });

  it('offers every arrangement in the View menu, from the one list', () => {
    expect(viewMenuSource).toContain('WORKSPACE_LAYOUTS');
    expect(WORKSPACE_LAYOUTS.map(l => l.id)).toEqual(['single', 'rows', 'columns', 'grid', 'cascade', 'free']);
  });

  it('scopes the lower panel to the active screen, and names it', () => {
    expect(secondaryPanelSource).toContain('activeScreenId');
    expect(secondaryPanelSource).toContain('Screen:');
    for (const tab of ['Build check', 'Simulation', 'Lighting', 'Quantities', 'Messages']) {
      expect(secondaryPanelSource).toContain(tab);
    }
  });
});

// feat/window-snapping (user, 2026-09-18): tiles dragged by their caption
// go where they are dropped, and a drop at an edge snaps like Windows.
import {
  FULL_FRAME, frameFromRect, freeTileRects, isFullFrame, rectFromFrame, snapZone, SNAP_MARGIN,
} from '../project/WorkspaceLayout';
import { useStore } from '../store';

describe('window snapping', () => {
  it('snaps the top edge to the whole area, a side to that half and a corner to that quarter', () => {
    expect(snapZone(400, 5, 800, 600)).toEqual(FULL_FRAME);
    expect(snapZone(3, 300, 800, 600)).toEqual({ x: 0, y: 0, width: 0.5, height: 1 });
    expect(snapZone(799, 300, 800, 600)).toEqual({ x: 0.5, y: 0, width: 0.5, height: 1 });
    expect(snapZone(2, 2, 800, 600)).toEqual({ x: 0, y: 0, width: 0.5, height: 0.5 });
    expect(snapZone(798, 598, 800, 600)).toEqual({ x: 0.5, y: 0.5, width: 0.5, height: 0.5 });
    expect(snapZone(400, 598, 800, 600)).toBeNull();                 // the bottom edge alone: nothing
    expect(snapZone(400, SNAP_MARGIN + 1, 800, 600)).toBeNull();     // away from every edge
    expect(snapZone(1, 1, 0, 0)).toBeNull();
  });

  it('keeps a dropped tile inside the area and no smaller than a readable tile', () => {
    expect(frameFromRect({ x: 100, y: 50, width: 400, height: 300 }, 800, 600))
      .toEqual({ x: 0.125, y: 50 / 600, width: 0.5, height: 0.5 });
    const clamped = frameFromRect({ x: 700, y: 550, width: 400, height: 300 }, 800, 600);
    expect(clamped.x + clamped.width).toBeCloseTo(1);
    expect(clamped.y + clamped.height).toBeCloseTo(1);
    const tiny = frameFromRect({ x: 0, y: 0, width: 10, height: 10 }, 800, 600);
    expect(tiny.width * 800).toBe(MIN_TILE);
    expect(rectFromFrame(FULL_FRAME, 800, 600)).toEqual({ x: 0, y: 0, width: 800, height: 600 });
    expect(isFullFrame(FULL_FRAME)).toBe(true);
    expect(isFullFrame({ x: 0, y: 0, width: 0.5, height: 1 })).toBe(false);
  });

  it('places framed tiles by their frames and the rest by the fallback arrangement', () => {
    const fallback = tileRects('grid', 3, 800, 600);
    const tiles = freeTileRects(['a', 'b', 'c'], { b: { x: 0.5, y: 0, width: 0.5, height: 1 } }, fallback, 800, 600);
    expect(tiles[0]).toEqual(fallback[0]);
    expect(tiles[1]).toEqual({ x: 400, y: 0, width: 400, height: 600, z: 1 });
    expect(tiles[2]).toEqual(fallback[2]);
  });

  it('a hand-placed tile switches the store to the free arrangement and keeps the others where they were', () => {
    useStore.setState({ workspaceLayout: 'grid', tileFrames: {} });
    useStore.getState().arrangeFreely({ a: { x: 0, y: 0, width: 0.5, height: 1 }, b: { x: 0.5, y: 0, width: 0.5, height: 1 } });
    expect(useStore.getState().workspaceLayout).toBe('free');
    useStore.getState().setTileFrame('b', FULL_FRAME);
    expect(useStore.getState().tileFrames).toEqual({ a: { x: 0, y: 0, width: 0.5, height: 1 }, b: FULL_FRAME });
    expect(WORKSPACE_LAYOUTS.some(l => l.id === 'free')).toBe(true);
  });

  it('the workspace drags captions on the window and previews the snap target (source scan)', () => {
    expect(workspaceSource).toContain("window.addEventListener('pointermove', move)");
    expect(workspaceSource).toContain('snapZone(px, py, size.width, size.height)');
    expect(workspaceSource).toContain('data-snap-preview');
    expect(workspaceSource).toContain('onDoubleClick={e => { e.stopPropagation(); toggleMaximize(screenId, index); }}');
  });
});
