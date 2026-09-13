// feat/room-plan: the schedule - what a drawn room actually contains.
//
// Every number here is DERIVED from the drawing, never entered
// alongside it. That is the whole value: a schedule you type by hand is
// a second source of truth that starts drifting the moment someone
// moves a wall, whereas this cannot disagree with the plan because it
// IS the plan, counted.
//
// It is possible at all because the plan symbols are to scale
// (theme/Scale.ts) and walls carry a real height: 14 metres of 12 cm
// brick at 2.5 m is a real quantity, not a pixel measurement dressed up
// as one.
//
// Pure functions only, no store and no Konva - the same contract every
// other module in this folder keeps.

import type { WallElement } from '../elements/WallElement';
import { clampWallHeight, wallLength } from '../elements/WallElement';
import type { SynopticObject } from '../store';
import type { Device } from './DeviceSchema';
import { findClosedRooms } from './RoomFloors';
import { pointInPolygon } from './Illuminance';
import { listCircuits, objectsInCircuit } from './CircuitResolver';
import { describeCircuitBinding, describeCircuitFeedback, circuitStateIsAssumed } from './CircuitBindings';
import type { CircuitBinding } from './CircuitBindings';
import { getWallMaterial, getFloorMaterial } from '../theme/Materials';
import { computeIlluminanceGrid, PHOTOMETRY } from './Illuminance';
import type { FloorMaterialId } from '../theme/Materials';
import { pxToCm } from '../theme/Scale';
import { getSymbolDefinition } from '../symbols/SymbolRegistry';

/** Square metres for an area given in square canvas pixels. */
function pxAreaToSquareMetres(areaPx: number): number {
  const side = pxToCm(1) / 100; // metres per pixel
  return areaPx * side * side;
}

/** Metres for a length in canvas pixels. */
function pxToMetres(px: number): number {
  return pxToCm(px) / 100;
}

export interface WallTakeoffRow {
  material: string;
  materialLabel: string;
  /** Total run, in metres. */
  length: number;
  /** Wall face area, in square metres - length x height, counting ONE face. */
  area: number;
  /** The height these walls are, in metres. Absent when the group mixes heights. */
  height: number | null;
  count: number;
}

export interface LightingTakeoffRow {
  /** 1-based, matching the order rooms come back from RoomFloors. */
  room: number;
  /** Square metres - so the figures can be read per area. */
  area: number;
  average: number;
  min: number;
  max: number;
  uniformity: number;
  /** Installed luminaire flux in the room, in lumens - what the fittings add up to. */
  installedFlux: number;
  /** Installed load per square metre [lm/m2] - the crude but useful density figure. */
  fluxDensity: number;
}

export interface FloorTakeoffRow {
  materialLabel: string;
  /** Square metres. */
  area: number;
  rooms: number;
}

export interface FixtureTakeoffRow {
  type: string;
  label: string;
  count: number;
}

export interface CircuitTakeoffRow {
  name: string;
  fixtures: number;
  /** 'K1 -> ELA1.DO.3', or 'nie powiazany'. */
  binding: string;
  wired: boolean;
  /** How the state is confirmed - or that it is not. See CircuitBindings. */
  feedback: string;
  /** True when the state shown is taken from the command rather than read back. Normal for lighting. */
  assumed: boolean;
}

export interface RoomTakeoff {
  walls: WallTakeoffRow[];
  floors: FloorTakeoffRow[];
  fixtures: FixtureTakeoffRow[];
  circuits: CircuitTakeoffRow[];
  /** Empty when nothing is lit - the calculation only answers for a room with its lights on. */
  lighting: LightingTakeoffRow[];
  totals: {
    wallLength: number;
    wallArea: number;
    floorArea: number;
    fixtures: number;
    /** Circuits that have no device behind them - the number worth acting on. */
    unwiredCircuits: number;
  };
}

/** The shoelace area of a polygon, always positive. */
function polygonArea(points: { x: number; y: number }[]): number {
  let total = 0;
  for (let i = 0; i < points.length; i++) {
    const a = points[i];
    const b = points[(i + 1) % points.length];
    total += a.x * b.y - b.x * a.y;
  }
  return Math.abs(total) / 2;
}

export function buildRoomTakeoff(
  walls: WallElement[],
  objects: SynopticObject[],
  circuits: CircuitBinding[],
  devices: Device[],
  floorMaterial: FloorMaterialId | undefined
): RoomTakeoff {
  // ---- walls, grouped by material ----------------------------------------
  const wallGroups = new Map<string, { length: number; area: number; heights: Set<number>; count: number }>();
  for (const wall of walls) {
    const material = getWallMaterial(wall.material);
    const height = clampWallHeight(wall.height);
    const length = wallLength(wall);
    const group = wallGroups.get(material.id) ?? { length: 0, area: 0, heights: new Set<number>(), count: 0 };
    group.length += length;
    group.area += length * height;
    group.heights.add(height);
    group.count += 1;
    wallGroups.set(material.id, group);
  }

  const wallRows: WallTakeoffRow[] = [...wallGroups.entries()].map(([id, g]) => ({
    material: id,
    materialLabel: getWallMaterial(id as never).label,
    length: pxToMetres(g.length),
    area: pxAreaToSquareMetres(g.area),
    // A single height for the group, or null when they differ - a
    // schedule must not average two different walls into a number that
    // describes neither.
    height: g.heights.size === 1 ? pxToMetres([...g.heights][0]) : null,
    count: g.count,
  })).sort((a, b) => b.length - a.length);

  // ---- floors -------------------------------------------------------------
  const rooms = findClosedRooms(walls);
  const floorArea = rooms.reduce((sum, room) => sum + pxAreaToSquareMetres(polygonArea(room)), 0);
  const floorRows: FloorTakeoffRow[] = rooms.length === 0 ? [] : [{
    materialLabel: getFloorMaterial(floorMaterial).label,
    area: floorArea,
    rooms: rooms.length,
  }];

  // ---- fixtures -----------------------------------------------------------
  const fixtureCounts = new Map<string, number>();
  for (const obj of objects) {
    if (!obj.type.startsWith('building.')) continue;
    fixtureCounts.set(obj.type, (fixtureCounts.get(obj.type) ?? 0) + 1);
  }
  const fixtureRows: FixtureTakeoffRow[] = [...fixtureCounts.entries()].map(([type, count]) => ({
    type,
    label: getSymbolDefinition(type)?.label ?? type,
    count,
  })).sort((a, b) => a.label.localeCompare(b.label));

  // ---- circuits -----------------------------------------------------------
  const circuitRows: CircuitTakeoffRow[] = listCircuits(objects).map(name => {
    const binding = describeCircuitBinding(circuits, devices, name);
    return {
      name,
      fixtures: objectsInCircuit(objects, name).length,
      binding,
      wired: binding !== 'not bound',
      feedback: describeCircuitFeedback(circuits, devices, name),
      assumed: circuitStateIsAssumed(circuits, devices, name),
    };
  });

  // ---- lighting -----------------------------------------------------------
  // Computed per room from the SAME function the false-colour view
  // draws, so the schedule and the picture can never disagree about a
  // figure. Rooms with no light at all are left out: "0 lx everywhere"
  // is not a result worth a row.
  const lightingRows: LightingTakeoffRow[] = [];
  rooms.forEach((room, index) => {
    const grid = computeIlluminanceGrid(room, objects);
    if (grid.stats.max <= 0) return;
    const area = pxAreaToSquareMetres(polygonArea(room));
    // Only the fittings actually inside THIS room count toward its
    // installed flux - a lamp in the next room does not belong in this
    // room's density figure even though its light may reach across.
    let installedFlux = 0;
    for (const obj of objects) {
      const photometry = PHOTOMETRY[obj.type];
      if (!photometry) continue;
      if (obj.editor?.preview_state !== 'ON') continue;
      if (!pointInPolygon(room, obj.x + obj.width / 2, obj.y + obj.height / 2)) continue;
      installedFlux += photometry.flux;
    }
    lightingRows.push({
      room: index + 1,
      area,
      average: grid.stats.average,
      min: grid.stats.min,
      max: grid.stats.max,
      uniformity: grid.stats.uniformity,
      installedFlux,
      fluxDensity: area > 0 ? installedFlux / area : 0,
    });
  });

  return {
    walls: wallRows,
    floors: floorRows,
    fixtures: fixtureRows,
    circuits: circuitRows,
    lighting: lightingRows,
    totals: {
      wallLength: wallRows.reduce((s, r) => s + r.length, 0),
      wallArea: wallRows.reduce((s, r) => s + r.area, 0),
      floorArea,
      fixtures: fixtureRows.reduce((s, r) => s + r.count, 0),
      unwiredCircuits: circuitRows.filter(r => !r.wired).length,
    },
  };
}

/** The schedule as tab-separated text, for pasting into a spreadsheet or an e-mail. */
export function takeoffToText(takeoff: RoomTakeoff): string {
  const lines: string[] = [];
  const n = (value: number, digits = 2) => value.toFixed(digits).replace('.', ',');

  lines.push('WALLS');
  lines.push('Material\tSegments\tLength [m]\tHeight [m]\tFace area [m2]');
  for (const row of takeoff.walls) {
    lines.push(`${row.materialLabel}\t${row.count}\t${n(row.length)}\t${row.height === null ? 'mixed' : n(row.height)}\t${n(row.area)}`);
  }
  lines.push(`TOTAL\t\t${n(takeoff.totals.wallLength)}\t\t${n(takeoff.totals.wallArea)}`);

  lines.push('');
  lines.push('FLOOR');
  lines.push('Material\tRooms\tArea [m2]');
  for (const row of takeoff.floors) {
    lines.push(`${row.materialLabel}\t${row.rooms}\t${n(row.area)}`);
  }

  lines.push('');
  lines.push('ITEMS');
  lines.push('Item\tQty');
  for (const row of takeoff.fixtures) {
    lines.push(`${row.label}\t${row.count}`);
  }

  if (takeoff.lighting.length > 0) {
    lines.push('');
    lines.push('LIGHTING (direct component)');
    lines.push('Room	Area [m2]	E avg [lx]	E min [lx]	E max [lx]	Uniformity	Flux [lm]	Density [lm/m2]');
    for (const row of takeoff.lighting) {
      lines.push(`${row.room}	${n(row.area)}	${Math.round(row.average)}	${Math.round(row.min)}	${Math.round(row.max)}	${n(row.uniformity)}	${Math.round(row.installedFlux)}	${Math.round(row.fluxDensity)}`);
    }
  }

  lines.push('');
  lines.push('CIRCUITS');
  lines.push('Circuit\tLoads\tControl	Feedback');
  for (const row of takeoff.circuits) {
    lines.push(`${row.name}\t${row.fixtures}\t${row.binding}	${row.feedback}`);
  }

  return lines.join('\n');
}
