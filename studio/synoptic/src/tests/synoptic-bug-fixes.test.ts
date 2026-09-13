// Bugs found by going through Synoptic as a user (feat/synoptic-modes-and-
// library). Each test would have caught its bug: it fails on the code
// before the fix.

import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import type { SynopticObject } from '../store';
import { ProjectManager } from '../project/ProjectManager';
import { FLOOR_MATERIALS, DEFAULT_FLOOR_MATERIAL } from '../theme/Materials';
import type { FloorMaterialId } from '../theme/Materials';
import { framesInHitOrder } from '../elements/FrameElement';
import { GRID_SIZE } from '../theme/ScadaTheme';

const obj = (id: string, type: string): SynopticObject => ({
  id, type, category: 'X', x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
  visible: true, locked: false, layer: 1, tag: '', description: '',
  color: '', fill: '', border: '', text: '', font: 'Tahoma', fontSize: 13,
  tooltip: '', width: 64, height: 64, customProperties: {},
});

beforeEach(() => {
  ProjectManager.newProject('Bugs');
  useStore.setState({ workMode: 'SYMBOLS' });
});

describe('a plain click replaces the whole selection', () => {
  it('clicking a symbol after a wall no longer leaves the wall selected (Delete used to remove it too)', () => {
    useStore.getState().addRoomWalls({ x: 0, y: 0, width: 320, height: 240 });
    useStore.setState({ objects: [obj('valve', 'water.ball_valve')] });
    const wallId = useStore.getState().walls[0].id;
    useStore.getState().selectWalls([wallId]);
    useStore.getState().selectObjects(['valve']);
    expect(useStore.getState().selectedWallIds).toEqual([]);
    expect(useStore.getState().selectedIds).toEqual(['valve']);

    useStore.getState().deleteObjects(useStore.getState().selectedIds, [], [], [], [], [], [], useStore.getState().selectedWallIds);
    expect(useStore.getState().walls).toHaveLength(4);
  });

  it('clicking a wall after a frame no longer leaves the frame selected, and the other kinds all clear walls', () => {
    useStore.getState().addFrame({ x: 0, y: 0, width: 160, height: 160, titlePosition: 'TOP_LEFT', variant: 'PLAIN' });
    useStore.getState().addRoomWalls({ x: 0, y: 0, width: 320, height: 240 });
    const frameId = useStore.getState().frames[0].id;
    const wallId = useStore.getState().walls[0].id;
    useStore.getState().selectFrames([frameId]);
    useStore.getState().selectWalls([wallId]);
    expect(useStore.getState().selectedFrameIds).toEqual([]);
    for (const select of ['selectConnections', 'selectMeters', 'selectSignalPanels', 'selectFrames', 'selectGroupCommands', 'selectSetpointPanels'] as const) {
      useStore.getState().selectWalls([wallId]);
      useStore.getState()[select](['x']);
      expect(useStore.getState().selectedWallIds, select).toEqual([]);
    }
  });
});

describe('undo and redo', () => {
  it('drop the wall selection like every other selection - the wall may not exist after an undo', () => {
    useStore.getState().addRoomWalls({ x: 0, y: 0, width: 320, height: 240 });
    useStore.getState().selectWalls(useStore.getState().walls.map(w => w.id));
    useStore.getState().undo();
    expect(useStore.getState().walls).toHaveLength(0);
    expect(useStore.getState().selectedWallIds).toEqual([]);
    useStore.getState().selectWalls(['ghost']);
    useStore.getState().redo();
    expect(useStore.getState().selectedWallIds).toEqual([]);
  });
});

describe('save and reopen', () => {
  it('keeps the floor material - it was written to the file and dropped when reading it back', () => {
    const other = (Object.keys(FLOOR_MATERIALS) as FloorMaterialId[]).find(id => id !== DEFAULT_FLOOR_MATERIAL)!;
    useStore.getState().addRoomWalls({ x: 0, y: 0, width: 320, height: 240 });
    useStore.getState().setFloorMaterial(other);
    const saved = ProjectManager.getProjectData()!;
    ProjectManager.newProject('Other');
    expect(useStore.getState().canvasConfig.floorMaterial).toBeUndefined();
    expect(ProjectManager.loadProject(saved, 'plan.epwsyn')).toBe(true);
    expect(useStore.getState().canvasConfig.floorMaterial).toBe(other);
    expect(useStore.getState().walls).toHaveLength(4);
  });
});

describe('copy, paste and duplicate', () => {
  it('a room selected with its walls pastes as a room: four new walls, one grid step away, selected', () => {
    useStore.getState().setWorkMode('ROOMS');
    useStore.getState().addRoomWalls({ x: 0, y: 0, width: 320, height: 240 });
    const original = useStore.getState().walls;
    useStore.getState().selectWalls(original.map(w => w.id));
    useStore.getState().copySelected();
    useStore.getState().paste();
    const walls = useStore.getState().walls;
    expect(walls).toHaveLength(8);
    const pasted = walls.slice(4);
    expect(new Set(pasted.map(w => w.id)).size).toBe(4);
    expect(pasted.every(w => !original.some(o => o.id === w.id))).toBe(true);
    expect(pasted[0].from).toEqual({ x: original[0].from.x + GRID_SIZE, y: original[0].from.y + GRID_SIZE });
    expect(useStore.getState().selectedWallIds).toEqual(pasted.map(w => w.id));
  });

  it('Ctrl+D duplicates selected walls the same way, without touching the clipboard', () => {
    useStore.getState().addRoomWalls({ x: 0, y: 0, width: 320, height: 240 });
    useStore.getState().selectWalls([useStore.getState().walls[0].id]);
    const clipboardBefore = JSON.stringify(useStore.getState().clipboardWalls);
    useStore.getState().duplicateSelected();
    expect(useStore.getState().walls).toHaveLength(5);
    expect(JSON.stringify(useStore.getState().clipboardWalls)).toBe(clipboardBefore);
    useStore.getState().undo();
    expect(useStore.getState().walls).toHaveLength(4);
  });
});

describe('overlapping frames', () => {
  it('a small frame inside a big one stays on top, so both can be clicked', () => {
    const big = { id: 'big', width: 800, height: 600 };
    const small = { id: 'small', width: 160, height: 120 };
    const middle = { id: 'middle', width: 400, height: 300 };
    expect(framesInHitOrder([small, big, middle]).map(f => f.id)).toEqual(['big', 'middle', 'small']);
    expect(framesInHitOrder([big, small]).map(f => f.id)).toEqual(['big', 'small']);
    const a = { id: 'a', width: 100, height: 100 };
    const b = { id: 'b', width: 100, height: 100 };
    expect(framesInHitOrder([a, b]).map(f => f.id)).toEqual(['a', 'b']);
  });
});
