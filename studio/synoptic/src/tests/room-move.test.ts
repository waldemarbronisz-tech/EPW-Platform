// Reported after the modes stage: "a selected room cannot be moved - it
// selects, but does not react to dragging". In the running editor,
// dragging a wall of a selected room moved that one wall (or, grabbed at
// its midpoint, the resize handle), never the room, and the valve inside
// stayed where it was. Moving an area must take what lies inside along.

import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import type { SynopticObject } from '../store';
import { ProjectManager } from '../project/ProjectManager';
import { areaContents, connectedWallIds, mergeSelections, pointInsideRooms } from '../project/AreaMove';
import canvasSource from '../components/Canvas.tsx?raw';
import wallLayerSource from '../components/WallLayer.tsx?raw';

const obj = (id: string, type: string, x: number, y: number, extra: Partial<SynopticObject> = {}): SynopticObject => ({
  id, type, category: 'X', x, y, rotation: 0, scaleX: 1, scaleY: 1,
  visible: true, locked: false, layer: 1, tag: '', description: '',
  color: '', fill: '', border: '', text: '', font: 'Tahoma', fontSize: 13,
  tooltip: '', width: 48, height: 48, customProperties: {}, ...extra,
});

function roomWithContents() {
  ProjectManager.newProject('Rooms');
  useStore.getState().addRoomWalls({ x: 160, y: 160, width: 480, height: 320 });
  useStore.setState({
    objects: [
      obj('valve', 'water.ball_valve', 320, 288),                 // inside
      obj('pump', 'water.pump', 880, 288),                        // outside
      obj('door', 'building.door', 376, 156, { width: 48, height: 8 }), // set in the top wall
      obj('locked', 'water.tank', 480, 320, { locked: true }),    // inside, but locked
    ],
    connections: [
      { id: 'inside', points: [{ x: 240, y: 240 }, { x: 400, y: 240 }], medium: 'WATER', style: 'NORMAL' } as never,
      { id: 'crossing', points: [{ x: 400, y: 400 }, { x: 900, y: 400 }], medium: 'WATER', style: 'NORMAL' } as never,
    ],
    meters: [{ id: 'm-in', x: 400, y: 380, width: 120, fontSize: 12, rows: [] } as never],
  });
  useStore.getState().saveHistory();
  return useStore.getState().walls.map(w => w.id);
}

beforeEach(() => {
  useStore.setState({ workMode: 'ROOMS' });
});

describe('what lies inside a room', () => {
  it('takes the valve, the door set in its wall, the wire wholly inside and the meter - not the pump, the crossing wire or a locked symbol', () => {
    const wallIds = roomWithContents();
    const inside = areaContents(useStore.getState(), wallIds);
    expect(inside.objectIds.sort()).toEqual(['door', 'valve']);
    expect(inside.connectionIds).toEqual(['inside']);
    expect(inside.meterIds).toEqual(['m-in']);
    expect(inside.wallIds).toEqual([]);
  });

  it('a frame owns what lies inside it too, and a single wall on its own owns nothing', () => {
    ProjectManager.newProject('Frames');
    useStore.setState({ objects: [obj('a', 'water.pump', 100, 100), obj('b', 'water.pump', 600, 100)] });
    useStore.getState().addFrame({ x: 64, y: 64, width: 200, height: 200, titlePosition: 'TOP_LEFT', variant: 'PLAIN' });
    const frameId = useStore.getState().frames[0].id;
    expect(areaContents(useStore.getState(), [], [frameId]).objectIds).toEqual(['a']);
    const wallIds = roomWithContents();
    expect(areaContents(useStore.getState(), [wallIds[0]]).objectIds).toEqual([]);
    expect(connectedWallIds(useStore.getState().walls, wallIds[0]).sort()).toEqual([...wallIds].sort());
  });
});

describe('moving a room', () => {
  it('moves the walls and everything inside by the same step, leaves the outside alone, in ONE undo step', () => {
    const wallIds = roomWithContents();
    const before = useStore.getState();
    const history = before.historyIndex;
    const inside = areaContents(before, wallIds);
    useStore.getState().moveElementsBy(mergeSelections(inside, { ...inside, objectIds: [], connectionIds: [], meterIds: [], wallIds }), 96, 48);

    const s = useStore.getState();
    const at = (id: string) => s.objects.find(o => o.id === id)!;
    expect(s.walls.map(w => w.from)).toEqual(before.walls.map(w => ({ x: w.from.x + 96, y: w.from.y + 48 })));
    expect([at('valve').x, at('valve').y]).toEqual([416, 336]);
    expect([at('door').x, at('door').y]).toEqual([472, 204]);
    expect([at('pump').x, at('pump').y]).toEqual([880, 288]);
    expect([at('locked').x, at('locked').y]).toEqual([480, 320]);
    expect(s.connections.find(c => c.id === 'inside')!.points[0]).toEqual({ x: 336, y: 288 });
    expect(s.connections.find(c => c.id === 'crossing')!.points[0]).toEqual({ x: 400, y: 400 });
    expect(s.meters[0].x).toBe(496);
    expect(s.historyIndex).toBe(history + 1);

    useStore.getState().undo();
    const undone = useStore.getState();
    expect(undone.walls.map(w => w.from)).toEqual(before.walls.map(w => w.from));
    expect(undone.objects.find(o => o.id === 'valve')!.x).toBe(320);
  });

  it('moveSelectionBy (arrow keys) still moves exactly the selection, through the same primitive', () => {
    roomWithContents();
    useStore.getState().selectObjects(['pump']);
    useStore.getState().moveSelectionBy(16, 0);
    expect(useStore.getState().objects.find(o => o.id === 'pump')!.x).toBe(896);
    expect(useStore.getState().objects.find(o => o.id === 'valve')!.x).toBe(320);
  });

  it('the canvas drags a selected room as a whole - live, through moveElementsBy - and a frame drag carries its contents', () => {
    expect(wallLayerSource).toContain('onDragStart');
    expect(wallLayerSource).toContain('onDragMove');
    const areaDrag = canvasSource.slice(canvasSource.indexOf('const startAreaDrag'));
    expect(areaDrag).toContain('areaContents(');
    expect(areaDrag).toContain('moveElementsBy(');
    expect(canvasSource).toContain('groupDrag.start(`frame:${frame.id}`, areaContents(');
  });
});

describe('grabbing a selected room by its floor', () => {
  it('knows the floor of a selected room from outside it, and needs the room selected', () => {
    const wallIds = roomWithContents();
    const walls = useStore.getState().walls;
    expect(pointInsideRooms(walls, wallIds, 400, 320)).toBe(true);
    expect(pointInsideRooms(walls, wallIds, 900, 320)).toBe(false);
    expect(pointInsideRooms(walls, [wallIds[0]], 400, 320)).toBe(false);
    expect(pointInsideRooms(walls, [], 400, 320)).toBe(false);
  });

  it('the canvas starts a room drag from the floor before it would start a marquee, and ends it on release', () => {
    const down = canvasSource.slice(canvasSource.indexOf('const handleMouseDown'));
    expect(down.indexOf('startFloorDrag(pointer)')).toBeGreaterThan(-1);
    expect(down.indexOf('startFloorDrag(pointer)')).toBeLessThan(down.indexOf('clearSelection();'));
    const up = canvasSource.slice(canvasSource.indexOf('const handleMouseUp'));
    expect(up).toContain('moveAreaDrag(point.x - start.x, point.y - start.y, true)');
  });
});
