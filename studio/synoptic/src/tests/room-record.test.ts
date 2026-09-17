// ZADANIA p. 6: the room record. A room's name and location live once,
// in RoomElement, and every wall of the room points at it (roomId) -
// instead of the same two strings sitting on every wall. The rules
// (project/Rooms.ts) and the store paths that touch them: assigning,
// migrating an old file, pruning on delete, copying, undo, save/reopen.
import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import { ProjectManager } from '../project/ProjectManager';
import { ensureRoomForWalls, migrateLegacyRooms, pruneRooms, remapCopiedRooms, roomForWalls } from '../project/Rooms';
import { roomLabels, roomSummary } from '../project/AreaMove';
import type { WallElement } from '../elements/WallElement';

let counter = 0;
const newId = () => `room-${++counter}`;

function square(prefix: string, x: number, y: number, size = 160, extra: Partial<WallElement> = {}): WallElement[] {
  const c = [{ x, y }, { x: x + size, y }, { x: x + size, y: y + size }, { x, y: y + size }];
  return c.map((from, i) => ({ id: `${prefix}${i}`, from, to: c[(i + 1) % 4], thickness: 8, ...extra }));
}

beforeEach(() => {
  counter = 0;
  ProjectManager.newProject('Rooms');
});

describe('Rooms.ts rules', () => {
  it('ensureRoomForWalls stamps the whole wall chain with one new record and reuses it afterwards', () => {
    const walls = [...square('a', 0, 0), ...square('b', 400, 0)];
    const first = ensureRoomForWalls([], walls, ['a0'], newId);       // one wall clicked
    expect(first.rooms).toEqual([{ id: 'room-1', name: '', location: '' }]);
    expect(first.walls.filter(w => w.roomId === 'room-1').map(w => w.id)).toEqual(['a0', 'a1', 'a2', 'a3']);
    expect(first.walls.filter(w => w.id.startsWith('b')).every(w => !w.roomId)).toBe(true);
    const again = ensureRoomForWalls(first.rooms, first.walls, ['a2', 'a3'], newId);
    expect(again.roomId).toBe('room-1');
    expect(again.rooms).toBe(first.rooms);                              // nothing added
    expect(roomForWalls(again.rooms, again.walls, ['a0', 'a1'])).toEqual({ room: first.rooms[0], mixed: false });
    expect(roomForWalls(again.rooms, again.walls, ['a0', 'b0'])).toEqual({ room: null, mixed: true });
    expect(roomForWalls(again.rooms, again.walls, ['b0'])).toEqual({ room: null, mixed: false });
  });

  it('a new record is seeded from the walls\' old per-wall fields', () => {
    const walls = square('a', 0, 0, 160, { roomName: 'Piwnica', roomLocation: 'KOT' });
    const result = ensureRoomForWalls([], walls, ['a0'], newId);
    expect(result.rooms).toEqual([{ id: 'room-1', name: 'Piwnica', location: 'KOT' }]);
  });

  it('migrateLegacyRooms turns each old-style wall group into one record and drops the old fields', () => {
    const walls = [
      ...square('a', 0, 0, 160, { roomName: 'Kotłownia', roomLocation: 'KOT' }),
      ...square('b', 400, 0, 160, { roomName: 'Garaż' }),
      ...square('c', 800, 0),                                            // never named: no record
      { id: 'd0', from: { x: 0, y: 500 }, to: { x: 160, y: 500 }, thickness: 8, roomId: 'kept' } as WallElement,
    ];
    const { walls: migrated, rooms } = migrateLegacyRooms(walls, [{ id: 'kept', name: 'Old', location: '' }], newId);
    expect(rooms).toEqual([
      { id: 'kept', name: 'Old', location: '' },
      { id: 'room-1', name: 'Kotłownia', location: 'KOT' },
      { id: 'room-2', name: 'Garaż', location: '' },
    ]);
    expect(migrated.filter(w => w.id.startsWith('a')).every(w => w.roomId === 'room-1' && !('roomName' in w))).toBe(true);
    expect(migrated.filter(w => w.id.startsWith('b')).every(w => w.roomId === 'room-2')).toBe(true);
    expect(migrated.filter(w => w.id.startsWith('c')).every(w => !w.roomId)).toBe(true);
    expect(migrated.find(w => w.id === 'd0')!.roomId).toBe('kept');
    const untouched = migrateLegacyRooms(square('x', 0, 0), [], newId);
    expect(untouched.rooms).toEqual([]);
  });

  it('pruneRooms drops a record no wall points at; remapCopiedRooms gives copies their own', () => {
    const rooms = [{ id: 'r1', name: 'A', location: '' }, { id: 'r2', name: 'B', location: 'KOT' }];
    const walls = square('a', 0, 0, 160, { roomId: 'r1' });
    expect(pruneRooms(rooms, walls)).toEqual([rooms[0]]);
    const only = [rooms[0]];
    expect(pruneRooms(only, walls)).toBe(only);                       // nothing to drop: same array back
    const copies = square('c', 300, 300, 160, { roomId: 'r1' });
    const remapped = remapCopiedRooms(rooms, copies, newId);
    expect(remapped.rooms).toHaveLength(3);
    expect(remapped.rooms[2]).toEqual({ id: 'room-1', name: 'A', location: '' });
    expect(remapped.walls.every(w => w.roomId === 'room-1')).toBe(true);
  });
});

describe('the store', () => {
  function drawRoom(x = 160, y = 160) {
    useStore.getState().addRoomWalls({ x, y, width: 400, height: 240 });
    return useStore.getState().walls.slice(-4).map(w => w.id);
  }

  it('assignRoomToWalls names the room once; the label and the summary read the record', () => {
    const ids = drawRoom();
    const roomId = useStore.getState().assignRoomToWalls([ids[0]]);
    useStore.getState().updateRoom(roomId, { name: 'Kotłownia', location: 'KOT' });
    const s = useStore.getState();
    expect(s.rooms).toEqual([{ id: roomId, name: 'Kotłownia', location: 'KOT' }]);
    expect(s.walls.every(w => w.roomId === roomId)).toBe(true);
    expect(roomSummary(s.walls, ids, s.rooms)).toMatchObject({ name: 'Kotłownia', location: 'KOT' });
    expect(roomLabels(s.walls, s.rooms)).toEqual([{ x: 360, y: 280, name: 'Kotłownia', location: 'KOT' }]);
    expect(s.assignRoomToWalls(ids.slice(1, 3))).toBe(roomId);
  });

  it('deleting the walls prunes the record, undo brings both back', () => {
    const ids = drawRoom();
    const roomId = useStore.getState().assignRoomToWalls(ids);
    useStore.getState().updateRoom(roomId, { name: 'Garaż' });
    useStore.getState().saveHistory();
    useStore.getState().deleteObjects([], [], [], [], [], [], [], ids);
    expect(useStore.getState().walls).toEqual([]);
    expect(useStore.getState().rooms).toEqual([]);
    useStore.getState().undo();
    expect(useStore.getState().walls).toHaveLength(4);
    expect(useStore.getState().rooms).toEqual([{ id: roomId, name: 'Garaż', location: '' }]);
  });

  it('a pasted room is a second room with the same name, not a second set of walls in the first', () => {
    const ids = drawRoom();
    const roomId = useStore.getState().assignRoomToWalls(ids);
    useStore.getState().updateRoom(roomId, { name: 'Sypialnia' });
    useStore.getState().selectWalls(ids);
    useStore.getState().copySelected();
    useStore.getState().paste();
    const s = useStore.getState();
    expect(s.walls).toHaveLength(8);
    expect(s.rooms).toHaveLength(2);
    expect(s.rooms.map(r => r.name)).toEqual(['Sypialnia', 'Sypialnia']);
    const pasted = s.walls.slice(4);
    expect(new Set(pasted.map(w => w.roomId)).size).toBe(1);
    expect(pasted[0].roomId).not.toBe(roomId);
  });

  it('save and reopen keep the record; an old file with per-wall fields is migrated on open', () => {
    const ids = drawRoom();
    const roomId = useStore.getState().assignRoomToWalls(ids);
    useStore.getState().updateRoom(roomId, { name: 'Kotłownia', location: 'KOT' });
    const saved = JSON.parse(ProjectManager.getProjectData()!);
    expect(saved.rooms).toEqual([{ id: roomId, name: 'Kotłownia', location: 'KOT' }]);
    expect(saved.walls.every((w: WallElement) => w.roomId === roomId)).toBe(true);

    ProjectManager.newProject('Other');
    expect(ProjectManager.loadProject(JSON.stringify(saved), 'plan.epwsyn')).toBe(true);
    expect(useStore.getState().rooms).toEqual([{ id: roomId, name: 'Kotłownia', location: 'KOT' }]);

    const legacy = { ...saved, rooms: undefined,
      walls: saved.walls.map((w: WallElement) => { const { roomId: _r, ...rest } = w; return { ...rest, roomName: 'Stara', roomLocation: 'GAR' }; }) };
    expect(ProjectManager.loadProject(JSON.stringify(legacy), 'old.epwsyn')).toBe(true);
    const s = useStore.getState();
    expect(s.rooms).toHaveLength(1);
    expect(s.rooms[0]).toMatchObject({ name: 'Stara', location: 'GAR' });
    expect(s.walls.every(w => w.roomId === s.rooms[0].id && !('roomName' in w))).toBe(true);
  });
});
