// feat/room-plan: walls, floors, circuits and the plan symbols.
//
// Everything verified here is a PURE function, deliberately: the wall
// geometry, the room-loop detection and the circuit switching were all
// written as pure modules beside their data (WallElement.ts,
// RoomFloors.ts, CircuitResolver.ts) precisely so they could be checked
// with exact expected values instead of by mounting a canvas. The
// handful of wiring claims that have no runnable harness are checked by
// source scan, the same convention frame-element.test.ts already
// established for exactly that gap.

import { describe, it, expect } from 'vitest';
import {
  clampWallThickness, clampWallHeight, computeWallFaces, distanceToWall,
  isDegenerateWall, moveWall, wallBounds, wallLength,
  WALL_DEFAULT_HEIGHT, WALL_DEFAULT_THICKNESS, WALL_MAX_HEIGHT, WALL_MAX_THICKNESS,
  WALL_MIN_LENGTH, WALL_MIN_THICKNESS, WALL_VIEW_FORESHORTENING, drawnWallHeight,
} from '../elements/WallElement';
import { cm } from '../theme/Scale';
import type { WallElement } from '../elements/WallElement';
import { findClosedRooms, roomToPoints } from '../project/RoomFloors';
import {
  isCircuitOn, isCircuitOperable, listCircuits, normalizeCircuitName,
  objectsInCircuit, setCircuitUpdates, toggleCircuitUpdates,
} from '../project/CircuitResolver';
import type { SynopticObject } from '../store';
import { SYMBOL_REGISTRY } from '../symbols/SymbolRegistry';
import { shade, wallFaceTones, WALL_MATERIALS, FLOOR_MATERIALS } from '../theme/Materials';

import canvasSource from '../components/Canvas.tsx?raw';
import toolboxSource from '../components/Toolbox.tsx?raw';
import toolbarSource from '../components/Toolbar.tsx?raw';
import buildingRegistrySource from '../symbols/registry/building.ts?raw';

const wall = (from: [number, number], to: [number, number], extra: Partial<WallElement> = {}): WallElement => ({
  id: `${from.join(',')}->${to.join(',')}`,
  from: { x: from[0], y: from[1] },
  to: { x: to[0], y: to[1] },
  thickness: WALL_DEFAULT_THICKNESS,
  ...extra,
});

const obj = (id: string, type: string, circuit: string | undefined, state?: string): SynopticObject => ({
  id, type, category: 'BUILDING', x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
  visible: true, locked: false, layer: 0, circuit, tag: '', description: '',
  color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
  tooltip: '', width: 32, height: 32, customProperties: {},
  editor: state === undefined ? undefined : { preview_state: state },
});

describe('wall geometry', () => {
  it('clamps thickness into range and survives a non-finite value', () => {
    expect(clampWallThickness(1)).toBe(WALL_MIN_THICKNESS);
    expect(clampWallThickness(9999)).toBe(WALL_MAX_THICKNESS);
    expect(clampWallThickness(Number.NaN)).toBe(WALL_DEFAULT_THICKNESS);
  });

  it('clamps height, treating an absent value as the default rather than zero', () => {
    expect(clampWallHeight(undefined)).toBe(WALL_DEFAULT_HEIGHT);
    expect(clampWallHeight(9999)).toBe(WALL_MAX_HEIGHT);
    expect(clampWallHeight(0)).toBe(0); // an explicit flat wall stays flat
  });

  it('stores a REAL height and paints a foreshortened one', () => {
    // The stored number is a real 2.5 m storey - that is what a
    // schedule counts. What gets painted is deliberately less, because
    // this projection has no perspective to make a full-height wall
    // recede; see WALL_VIEW_FORESHORTENING's own note.
    expect(WALL_DEFAULT_HEIGHT).toBe(cm(250));
    expect(drawnWallHeight(cm(250))).toBeCloseTo(cm(250) * WALL_VIEW_FORESHORTENING);
    expect(drawnWallHeight(cm(250))).toBeLessThan(cm(250));
    // A flat wall stays flat - nothing is painted at all.
    expect(drawnWallHeight(0)).toBe(0);
  });

  it('treats a drag shorter than one grid cell as no wall at all', () => {
    expect(isDegenerateWall({ x: 0, y: 0 }, { x: WALL_MIN_LENGTH - 1, y: 0 })).toBe(true);
    expect(isDegenerateWall({ x: 0, y: 0 }, { x: WALL_MIN_LENGTH, y: 0 })).toBe(false);
  });

  it('moves both endpoints together, so a drag can never deform a wall', () => {
    const w = wall([10, 10], [40, 10]);
    const moved = moveWall(w, 5, -3);
    expect(moved.from).toEqual({ x: 15, y: 7 });
    expect(moved.to).toEqual({ x: 45, y: 7 });
    expect(wallLength(moved)).toBeCloseTo(wallLength(w));
  });

  it('bounds cover the painted body, not just the centre line', () => {
    const w = wall([10, 10], [40, 10], { thickness: 8 });
    expect(wallBounds(w)).toEqual({ x: 6, y: 6, width: 38, height: 8 });
  });

  it('measures distance to the SEGMENT, not to its infinite line', () => {
    const w = wall([0, 0], [100, 0]);
    expect(distanceToWall(w, 50, 10)).toBeCloseTo(10);
    // A point far beyond the end cap is far from the wall, even though
    // it sits exactly on the line the wall lies along.
    expect(distanceToWall(w, 500, 0)).toBeCloseTo(400);
  });
});

describe('wall 2.5D extrusion (computeWallFaces)', () => {
  it('keeps the footprint on the floor and lifts only the top face', () => {
    // `height` is the wall's REAL height; what is painted is that
    // height foreshortened (drawnWallHeight), so the expected lift is
    // derived from the same function the renderer uses rather than
    // hard-coded - the projection's constant is a tuning value and this
    // test is about the geometry, not about its current setting.
    const height = cm(250);
    const lift = drawnWallHeight(height);
    const faces = computeWallFaces({ from: { x: 0, y: 100 }, to: { x: 100, y: 100 }, thickness: 10, height });
    // Base spans the wall's own half-thickness either side of y=100.
    expect(faces.base).toEqual([0, 105, 100, 105, 100, 95, 0, 95]);
    // Top is exactly the base, lifted - proving the extrusion never
    // moves a plan coordinate sideways (the removed isometric PLAN mode
    // is precisely what this must not become).
    expect(faces.top).toEqual([0, 105 - lift, 100, 105 - lift, 100, 95 - lift, 0, 95 - lift]);
  });

  it('draws the face nearer the viewer - the long edge with the greater y', () => {
    const height = cm(250);
    const lift = drawnWallHeight(height);
    const faces = computeWallFaces({ from: { x: 0, y: 100 }, to: { x: 100, y: 100 }, thickness: 10, height });
    // y=105 is the lower (nearer) edge; the side face rises from it.
    expect(faces.side).toEqual([0, 105, 100, 105, 100, 105 - lift, 0, 105 - lift]);
  });

  it('emits no side face for a flat wall, so height 0 stays a plain plan', () => {
    const faces = computeWallFaces({ from: { x: 0, y: 0 }, to: { x: 50, y: 0 }, thickness: 6, height: 0 });
    expect(faces.side).toEqual([]);
    expect(faces.base.length).toBe(8);
  });

  it('returns empty faces for a zero-length wall instead of dividing by zero', () => {
    const faces = computeWallFaces({ from: { x: 5, y: 5 }, to: { x: 5, y: 5 }, thickness: 8, height: 40 });
    expect(faces).toEqual({ base: [], top: [], side: [] });
    expect(faces.base.every(Number.isFinite)).toBe(true);
  });
});

describe('room floors (findClosedRooms)', () => {
  it('fills a four-wall rectangle', () => {
    const rooms = findClosedRooms([
      wall([0, 0], [100, 0]), wall([100, 0], [100, 80]),
      wall([100, 80], [0, 80]), wall([0, 80], [0, 0]),
    ]);
    expect(rooms).toHaveLength(1);
    expect(rooms[0]).toHaveLength(4);
    expect(roomToPoints(rooms[0])).toHaveLength(8);
  });

  it('fills an L-shaped room (six walls)', () => {
    const rooms = findClosedRooms([
      wall([0, 0], [100, 0]), wall([100, 0], [100, 50]),
      wall([100, 50], [50, 50]), wall([50, 50], [50, 100]),
      wall([50, 100], [0, 100]), wall([0, 100], [0, 0]),
    ]);
    expect(rooms).toHaveLength(1);
    expect(rooms[0]).toHaveLength(6);
  });

  it('fills nothing while the room is still open - the normal mid-drawing state', () => {
    expect(findClosedRooms([
      wall([0, 0], [100, 0]), wall([100, 0], [100, 80]), wall([100, 80], [0, 80]),
    ])).toEqual([]);
  });

  it('refuses to guess at a T-junction rather than filling the wrong area', () => {
    // A closed square plus a stub off one corner: the stub makes that
    // corner degree-3, so the shape is ambiguous and gets no floor.
    const rooms = findClosedRooms([
      wall([0, 0], [100, 0]), wall([100, 0], [100, 80]),
      wall([100, 80], [0, 80]), wall([0, 80], [0, 0]),
      wall([0, 0], [-50, 0]),
    ]);
    expect(rooms).toEqual([]);
  });

  it('finds two separate rooms drawn on one screen', () => {
    const rooms = findClosedRooms([
      wall([0, 0], [50, 0]), wall([50, 0], [50, 50]), wall([50, 50], [0, 50]), wall([0, 50], [0, 0]),
      wall([200, 0], [250, 0]), wall([250, 0], [250, 50]), wall([250, 50], [200, 50]), wall([200, 50], [200, 0]),
    ]);
    expect(rooms).toHaveLength(2);
  });

  it('ignores a zero-length wall instead of looping forever on its self-edge', () => {
    const rooms = findClosedRooms([
      wall([0, 0], [100, 0]), wall([100, 0], [100, 80]),
      wall([100, 80], [0, 80]), wall([0, 80], [0, 0]),
      wall([500, 500], [500, 500]),
    ]);
    expect(rooms).toHaveLength(1);
  });
});

describe('circuits (CircuitResolver)', () => {
  it('knows which symbol types a circuit can switch', () => {
    expect(isCircuitOperable('building.luminaire')).toBe(true);
    expect(isCircuitOperable('building.socket_outlet')).toBe(true);
    expect(isCircuitOperable('electrical.circuit_breaker')).toBe(false);
  });

  it('treats case and surrounding space as the same circuit', () => {
    expect(normalizeCircuitName(' obw_1 ')).toBe('OBW_1');
    const objects = [obj('a', 'building.luminaire', 'obw_1'), obj('b', 'building.luminaire', 'OBW_1')];
    expect(objectsInCircuit(objects, 'Obw_1')).toHaveLength(2);
  });

  it('never treats "no circuit" as a circuit, so one click cannot switch every loose fixture', () => {
    const objects = [obj('a', 'building.luminaire', undefined), obj('b', 'building.luminaire', '')];
    expect(objectsInCircuit(objects, '')).toEqual([]);
    expect(objectsInCircuit(objects, undefined)).toEqual([]);
    expect(toggleCircuitUpdates(objects, undefined)).toEqual([]);
  });

  it('lists each circuit once, in first-seen order', () => {
    expect(listCircuits([
      obj('a', 'building.luminaire', 'OBW_2'),
      obj('b', 'building.socket_outlet', 'OBW_1'),
      obj('c', 'building.luminaire', 'obw_2'),
    ])).toEqual(['OBW_2', 'OBW_1']);
  });

  it('switches a whole circuit at once, in each symbol type own vocabulary', () => {
    const objects = [
      obj('lamp', 'building.luminaire', 'OBW_1', 'OFF'),
      obj('socket', 'building.socket_outlet', 'OBW_1', 'DEAD'),
      obj('other', 'building.luminaire', 'OBW_2', 'OFF'),
    ];
    const updates = setCircuitUpdates(objects, 'OBW_1', true);
    expect(updates).toHaveLength(2);
    expect(updates.find(u => u.id === 'lamp')!.updates.editor!.preview_state).toBe('ON');
    expect(updates.find(u => u.id === 'socket')!.updates.editor!.preview_state).toBe('LIVE');
  });

  it('converges a half-on circuit to OFF rather than flipping each fixture independently', () => {
    const objects = [
      obj('a', 'building.luminaire', 'OBW_1', 'ON'),
      obj('b', 'building.luminaire', 'OBW_1', 'OFF'),
    ];
    expect(isCircuitOn(objects, 'OBW_1')).toBe(true);
    const updates = toggleCircuitUpdates(objects, 'OBW_1');
    expect(updates.map(u => u.updates.editor!.preview_state)).toEqual(['OFF', 'OFF']);
  });

  it('keeps the rest of the editor block when switching', () => {
    const lamp = obj('a', 'building.luminaire', 'OBW_1', 'OFF');
    lamp.editor = { preview_state: 'OFF', unit: 'lx', preview_value: '42' };
    const updates = setCircuitUpdates([lamp], 'OBW_1', true);
    expect(updates[0].updates.editor).toEqual({ preview_state: 'ON', unit: 'lx', preview_value: '42' });
  });
});

describe('plan symbols', () => {
  it('registers both building symbols in their own visible category', () => {
    for (const type of ['building.luminaire', 'building.socket_outlet']) {
      const def = SYMBOL_REGISTRY[type];
      expect(def, type).toBeDefined();
      expect(def.category).toBe('BUILDING');
      expect(def.hiddenFromLibrary).toBeFalsy();
    }
  });

  it('declares NO terminals - a fixture is driven by its circuit, never by a wire touching it', () => {
    // This is the whole reason the circuit model can coexist with
    // NetResolver's geometric nets without one symbol having two
    // competing ideas of "energized". See registry/building.ts.
    for (const type of ['building.luminaire', 'building.socket_outlet']) {
      expect(SYMBOL_REGISTRY[type].terminals ?? [], type).toEqual([]);
    }
    expect(buildingRegistrySource).toContain('NO TERMINALS');
  });

  it('leaves the schematic socket and panel lamp untouched', () => {
    expect(SYMBOL_REGISTRY['scada.socket']).toBeDefined();
    expect(SYMBOL_REGISTRY['electrical.indicator_lamp']).toBeDefined();
  });
});

describe('materials', () => {
  it('shades a color without leaving the byte range, and passes bad input through', () => {
    expect(shade('#808080', 2)).toBe('#ffffff');
    expect(shade('#808080', 0)).toBe('#000000');
    expect(shade('not-a-color', 1.2)).toBe('not-a-color');
  });

  it('derives three distinct wall tones from one material', () => {
    const tones = wallFaceTones(WALL_MATERIALS.cegla);
    expect(new Set([tones.top, tones.side, tones.base]).size).toBe(3);
  });

  it('offers the floor materials that were asked for', () => {
    expect(Object.keys(FLOOR_MATERIALS)).toEqual(expect.arrayContaining(['osb', 'parkiet', 'wykladzina']));
  });
});

describe('wiring (source scan - no runnable harness for these)', () => {
  it('draws the floor and walls BELOW the frames pass, so fixtures sit on top', () => {
    const floorAt = canvasSource.indexOf('<RoomFloorLayer');
    // Anchored on the COMPONENT, not on how the array is iterated:
    // the first version of this test matched 'walls.map(' and broke
    // the moment depth-sorting turned it into a sort().map() chain,
    // while the render order it exists to check was unchanged.
    const wallsAt = canvasSource.indexOf('<WallLayer');
    const framesAt = canvasSource.indexOf('framesInHitOrder(frames).map(');
    expect(floorAt).toBeGreaterThan(-1);
    expect(floorAt).toBeLessThan(wallsAt);
    expect(wallsAt).toBeLessThan(framesAt);
  });

  it('routes a Podglad click to the circuit instead of to selection', () => {
    expect(canvasSource).toContain('toggleCircuitAt');
    expect(canvasSource).toContain('if (previewMode)');
  });

  // feat/synoptic-modes: the library is a catalogue of things you insert;
  // the wall tool is a tool, and lives in the ROOMS work mode.
  it('puts the wall TOOL in the ROOMS work mode of the toolbar, not in the Object Library', () => {
    expect(toolbarSource).toContain('cmd="draw_wall"');
    expect(toolbarSource).toContain('setDrawingWallMode');
    expect(toolboxSource).not.toContain('setDrawingWallMode');
  });
});
