// The room record (ZADANIA p. 6, "Pokój nie ma własnego rekordu"): a room
// is still what its walls enclose - geometry never lives here - but its
// NAME and LOCATION now live once, in a RoomElement, and every wall of
// the room points at it through `roomId`. Before this the two strings
// sat on each wall separately (roomName/roomLocation), had to be kept
// equal by hand and read as "(different)" the moment they were not.
//
// Pure functions over plain arrays, no store access, so the slices,
// the inspector, the file loader and the tests all share one rule set:
//   - roomForWalls()      which record a selection of walls belongs to
//   - ensureRoomForWalls() the record to edit, created on first use and
//                          stamped on every wall joined to the selection
//   - migrateLegacyRooms() an older file's per-wall fields -> records
//   - pruneRooms()         records no wall points at any more
//   - remapCopiedRooms()   pasted/duplicated walls get their own record
//   (the floor label itself is AreaMove.roomLabels(), fed from these records)
import type { WallElement } from '../elements/WallElement';
import type { RoomElement } from '../elements/RoomElement';
import { connectedWallIds } from './AreaMove';

export interface RoomLookup {
  room: RoomElement | null;   // the one record every selected wall shares
  mixed: boolean;             // the selected walls point at different records
}

/** The record the selected walls share - null when none of them has one, `mixed` when they disagree. */
export function roomForWalls(rooms: RoomElement[], walls: WallElement[], wallIds: string[]): RoomLookup {
  const selected = walls.filter(w => wallIds.includes(w.id));
  const ids = new Set(selected.map(w => w.roomId ?? ''));
  if (ids.size > 1) return { room: null, mixed: true };
  const [only] = [...ids];
  if (!only) return { room: null, mixed: false };
  return { room: rooms.find(r => r.id === only) ?? null, mixed: false };
}

/**
 * The record to edit for these walls. Every wall joined to the
 * selection (the whole chain, not just the clicked ones) gets the same
 * roomId, so a name typed once names the room, not two of its walls.
 * An existing shared record is reused; otherwise the first record any
 * of the walls points at is adopted, else a new one is created.
 */
export function ensureRoomForWalls(
  rooms: RoomElement[], walls: WallElement[], wallIds: string[], newId: () => string,
): { rooms: RoomElement[]; walls: WallElement[]; roomId: string } {
  const group = new Set<string>();
  for (const id of wallIds) connectedWallIds(walls, id).forEach(g => group.add(g));
  const members = walls.filter(w => group.has(w.id));
  const existing = members.map(w => w.roomId).find(id => id && rooms.some(r => r.id === id));
  let nextRooms = rooms;
  let roomId = existing ?? '';
  if (!roomId) {
    // A wall may still carry the pre-record fields: seed the record from them.
    const seed = members.find(w => w.roomName || w.roomLocation);
    roomId = newId();
    nextRooms = [...rooms, { id: roomId, name: seed?.roomName ?? '', location: seed?.roomLocation ?? '' }];
  }
  const nextWalls = walls.map(w => (group.has(w.id) && w.roomId !== roomId ? { ...w, roomId } : w));
  return { rooms: nextRooms, walls: nextWalls, roomId };
}

/**
 * A file saved before the record existed carries roomName/roomLocation
 * on its walls: every connected group of such walls becomes one record
 * (the first non-empty name/location wins), the walls point at it and
 * the old fields are dropped. Walls that already have a roomId are left
 * alone; nothing happens for a file without the old fields.
 */
export function migrateLegacyRooms(
  walls: WallElement[], rooms: RoomElement[], newId: () => string,
): { walls: WallElement[]; rooms: RoomElement[] } {
  const legacy = walls.filter(w => !w.roomId && (w.roomName || w.roomLocation));
  if (legacy.length === 0) return { walls, rooms };
  let nextRooms = [...rooms];
  let nextWalls = walls;
  const done = new Set<string>();
  for (const wall of legacy) {
    if (done.has(wall.id)) continue;
    const group = connectedWallIds(nextWalls, wall.id);
    group.forEach(id => done.add(id));
    const members = nextWalls.filter(w => group.includes(w.id));
    const name = members.map(w => w.roomName).find(Boolean) ?? '';
    const location = members.map(w => w.roomLocation).find(Boolean) ?? '';
    const roomId = newId();
    nextRooms.push({ id: roomId, name, location });
    nextWalls = nextWalls.map(w => {
      if (!group.includes(w.id)) return w;
      const { roomName: _n, roomLocation: _l, ...rest } = w;
      return { ...rest, roomId };
    });
  }
  return { walls: nextWalls, rooms: nextRooms };
}

/** Records no wall refers to any more (all its walls deleted). */
export function pruneRooms(rooms: RoomElement[], walls: WallElement[]): RoomElement[] {
  const used = new Set(walls.map(w => w.roomId).filter(Boolean));
  const kept = rooms.filter(r => used.has(r.id));
  return kept.length === rooms.length ? rooms : kept;
}

/**
 * Copies of walls must not join the original's record - a pasted room
 * is a second room. Each distinct roomId among the copies gets a fresh
 * record with the same name/location.
 */
export function remapCopiedRooms(
  rooms: RoomElement[], copies: WallElement[], newId: () => string,
): { rooms: RoomElement[]; walls: WallElement[] } {
  const mapping = new Map<string, string>();
  const added: RoomElement[] = [];
  const walls = copies.map(w => {
    if (!w.roomId) return w;
    let target = mapping.get(w.roomId);
    if (!target) {
      const source = rooms.find(r => r.id === w.roomId);
      target = newId();
      mapping.set(w.roomId, target);
      added.push({ id: target, name: source?.name ?? '', location: source?.location ?? '' });
    }
    return { ...w, roomId: target };
  });
  return { rooms: added.length ? [...rooms, ...added] : rooms, walls };
}
