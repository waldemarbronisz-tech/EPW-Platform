// fix/room-move-and-edit: a room (the walls round it) or a frame is an
// AREA, and an area owns what lies inside it.
//
// Reported after the modes stage: a selected room could not be dragged -
// grabbing a wall moved that one wall (or, at its midpoint, the resize
// handle), never the room - and Properties said "No object selected".
// This file is the pure half of the fix:
//
//   - what lies inside an area, so moving the room takes its symbols,
//     the doors and windows set in its walls, and the wires lying wholly
//     inside it along;
//   - which walls make up one room, so a single wall can hand over to
//     the whole room;
//   - what a room is, for Properties: its outline, size, perimeter,
//     floor area, name and location.
//
// A room's name and location live on its walls (WallElement.roomName /
// roomLocation). A room has no record of its own - it is whatever the
// walls enclose - so its data travels with the walls through save and
// load, undo, copy and paste, exactly as the walls do.

import type { WallElement, WallPoint } from '../elements/WallElement';
import { clampWallThickness, wallLength } from '../elements/WallElement';
import { findClosedRooms } from './RoomFloors';
import { pointInPolygon } from './Illuminance';
import type { SelectionIds } from './WorkModes';
import { PIXELS_PER_METRE } from '../theme/Scale';

export interface AreaScene {
  walls: WallElement[];
  frames: { id: string; x: number; y: number; width: number; height: number }[];
  objects: { id: string; type: string; x: number; y: number; width: number; height: number; scaleX?: number; scaleY?: number; locked?: boolean }[];
  meters: { id: string; x: number; y: number; width: number }[];
  signalPanels: { id: string; x: number; y: number; width: number }[];
  groupCommands: { id: string; x: number; y: number; width: number }[];
  setpointPanels: { id: string; x: number; y: number; width: number }[];
  connections: { id: string; points: { x: number; y: number }[] }[];
}

export interface Box { x: number; y: number; width: number; height: number }

const emptySelection = (): SelectionIds => ({
  objectIds: [], connectionIds: [], meterIds: [], signalPanelIds: [],
  frameIds: [], groupCommandIds: [], setpointPanelIds: [], wallIds: [],
});

/** The outline of the selected walls: min/max of their end points. */
export function wallsBox(walls: WallElement[], wallIds: string[]): Box | null {
  const selected = walls.filter(w => wallIds.includes(w.id));
  if (selected.length === 0) return null;
  const xs = selected.flatMap(w => [w.from.x, w.to.x]);
  const ys = selected.flatMap(w => [w.from.y, w.to.y]);
  const x = Math.min(...xs);
  const y = Math.min(...ys);
  return { x, y, width: Math.max(...xs) - x, height: Math.max(...ys) - y };
}

const rectPolygon = (b: Box): WallPoint[] => [
  { x: b.x, y: b.y }, { x: b.x + b.width, y: b.y }, { x: b.x + b.width, y: b.y + b.height }, { x: b.x, y: b.y + b.height },
];

/** The polygons that count as "inside": every closed room the selected walls form (their bounding box when two or more walls form none), and every selected frame. */
function areaPolygons(scene: AreaScene, wallIds: string[], frameIds: string[]): WallPoint[][] {
  const selectedWalls = scene.walls.filter(w => wallIds.includes(w.id));
  const polygons: WallPoint[][] = findClosedRooms(selectedWalls);
  if (polygons.length === 0 && selectedWalls.length >= 2) {
    const box = wallsBox(scene.walls, wallIds);
    if (box && box.width > 0 && box.height > 0) polygons.push(rectPolygon(box));
  }
  for (const frame of scene.frames) {
    if (frameIds.includes(frame.id)) polygons.push(rectPolygon(frame));
  }
  return polygons;
}

function distanceToSegment(px: number, py: number, a: WallPoint, b: WallPoint): number {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const lengthSquared = dx * dx + dy * dy;
  const t = lengthSquared === 0 ? 0 : Math.max(0, Math.min(1, ((px - a.x) * dx + (py - a.y) * dy) / lengthSquared));
  return Math.hypot(px - (a.x + t * dx), py - (a.y + t * dy));
}

/**
 * Everything that lies inside the selected walls and frames and should
 * move with them: symbols whose centre is inside (a door or window set in
 * one of the walls counts - its centre is ON the wall), panels whose top
 * centre is inside, wires lying wholly inside, and frames inside a room.
 * Locked symbols stay put, as they do for every other move.
 */
export function areaContents(scene: AreaScene, wallIds: string[], frameIds: string[] = []): SelectionIds {
  const result = emptySelection();
  const polygons = areaPolygons(scene, wallIds, frameIds);
  const selectedWalls = scene.walls.filter(w => wallIds.includes(w.id));
  if (polygons.length === 0) return result;

  const inside = (x: number, y: number) =>
    polygons.some(polygon => pointInPolygon(polygon, x, y)) ||
    selectedWalls.some(w => distanceToSegment(x, y, w.from, w.to) <= Math.max(clampWallThickness(w.thickness), 8));

  result.objectIds = scene.objects
    .filter(o => !o.locked && inside(o.x + (o.width * (o.scaleX || 1)) / 2, o.y + (o.height * (o.scaleY || 1)) / 2))
    .map(o => o.id);
  const panelInside = (p: { x: number; y: number; width: number }) => inside(p.x + p.width / 2, p.y + 8);
  result.meterIds = scene.meters.filter(panelInside).map(p => p.id);
  result.signalPanelIds = scene.signalPanels.filter(panelInside).map(p => p.id);
  result.groupCommandIds = scene.groupCommands.filter(panelInside).map(p => p.id);
  result.setpointPanelIds = scene.setpointPanels.filter(panelInside).map(p => p.id);
  result.connectionIds = scene.connections
    .filter(c => c.points.length > 0 && c.points.every(p => polygons.some(polygon => pointInPolygon(polygon, p.x, p.y))))
    .map(c => c.id);
  result.frameIds = scene.frames
    .filter(f => !frameIds.includes(f.id))
    .filter(f => inside(f.x + f.width / 2, f.y + f.height / 2))
    .map(f => f.id);
  return result;
}

/** Two selections merged, without duplicates. */
export function mergeSelections(a: SelectionIds, b: SelectionIds): SelectionIds {
  const merge = (x: string[], y: string[]) => [...new Set([...x, ...y])];
  return {
    objectIds: merge(a.objectIds, b.objectIds),
    connectionIds: merge(a.connectionIds, b.connectionIds),
    meterIds: merge(a.meterIds, b.meterIds),
    signalPanelIds: merge(a.signalPanelIds, b.signalPanelIds),
    frameIds: merge(a.frameIds, b.frameIds),
    groupCommandIds: merge(a.groupCommandIds, b.groupCommandIds),
    setpointPanelIds: merge(a.setpointPanelIds, b.setpointPanelIds),
    wallIds: merge(a.wallIds, b.wallIds),
  };
}

const pointKey = (p: WallPoint) => `${Math.round(p.x)},${Math.round(p.y)}`;

/** Every wall joined to `wallId` through shared corners - the walls of its room. */
export function connectedWallIds(walls: WallElement[], wallId: string): string[] {
  const start = walls.find(w => w.id === wallId);
  if (!start) return [];
  const found = new Set<string>([start.id]);
  const corners = new Set<string>([pointKey(start.from), pointKey(start.to)]);
  let grew = true;
  while (grew) {
    grew = false;
    for (const wall of walls) {
      if (found.has(wall.id)) continue;
      if (corners.has(pointKey(wall.from)) || corners.has(pointKey(wall.to))) {
        found.add(wall.id);
        corners.add(pointKey(wall.from));
        corners.add(pointKey(wall.to));
        grew = true;
      }
    }
  }
  return walls.filter(w => found.has(w.id)).map(w => w.id);
}

function polygonArea(points: WallPoint[]): number {
  let total = 0;
  for (let i = 0; i < points.length; i++) {
    const a = points[i];
    const b = points[(i + 1) % points.length];
    total += a.x * b.y - b.x * a.y;
  }
  return Math.abs(total) / 2;
}

export interface RoomSummary {
  wallCount: number;
  box: Box | null;
  /** Along the walls' centre lines, in metres. */
  perimeterMetres: number;
  /** In square metres; null when the walls do not close into a room. */
  floorAreaSquareMetres: number | null;
  /** The value every wall shares; '' when none is set; null when the walls disagree. */
  name: string | null;
  location: string | null;
}

function commonField(selected: WallElement[], key: 'roomName' | 'roomLocation'): string | null {
  const values = new Set(selected.map(w => w[key] ?? ''));
  return values.size === 1 ? [...values][0] : null;
}

export function roomSummary(walls: WallElement[], wallIds: string[]): RoomSummary {
  const selected = walls.filter(w => wallIds.includes(w.id));
  const rooms = findClosedRooms(selected);
  const metresPerPixel = 1 / PIXELS_PER_METRE;
  return {
    wallCount: selected.length,
    box: wallsBox(walls, wallIds),
    perimeterMetres: selected.reduce((sum, w) => sum + wallLength(w), 0) * metresPerPixel,
    floorAreaSquareMetres: rooms.length > 0
      ? rooms.reduce((sum, room) => sum + polygonArea(room), 0) * metresPerPixel * metresPerPixel
      : null,
    name: commonField(selected, 'roomName'),
    location: commonField(selected, 'roomLocation'),
  };
}

export interface RoomLabel { x: number; y: number; name: string; location: string }

/** One label per room that has a name or a location: its name and location, at the centre of its outline. */
export function roomLabels(walls: WallElement[]): RoomLabel[] {
  const seen = new Set<string>();
  const labels: RoomLabel[] = [];
  for (const wall of walls) {
    if (seen.has(wall.id)) continue;
    const group = connectedWallIds(walls, wall.id);
    group.forEach(id => seen.add(id));
    const summary = roomSummary(walls, group);
    const name = summary.name ?? walls.find(w => group.includes(w.id) && w.roomName)?.roomName ?? '';
    const location = summary.location ?? walls.find(w => group.includes(w.id) && w.roomLocation)?.roomLocation ?? '';
    if (!summary.box || (!name && !location)) continue;
    labels.push({ x: summary.box.x + summary.box.width / 2, y: summary.box.y + summary.box.height / 2, name, location });
  }
  return labels;
}

/**
 * Whether (x, y) lies on the floor of a room the selected walls close.
 * Grabbing a selected room by its floor moves it: a wall is a thin line,
 * and the floor is where people take hold of a room.
 */
export function pointInsideRooms(walls: WallElement[], wallIds: string[], x: number, y: number): boolean {
  if (wallIds.length < 2) return false;
  const rooms = findClosedRooms(walls.filter(w => wallIds.includes(w.id)));
  return rooms.some(room => pointInPolygon(room, x, y));
}
