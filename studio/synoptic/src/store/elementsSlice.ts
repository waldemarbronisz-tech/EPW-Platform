import type { StateCreator } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import type { AppState } from './appState';
import { releaseAnchorsForDeletedObjects } from '../utils/WireAnchoring';
import { getObstacles } from '../project/WireCollision';
import { isCircuitOn } from './../project/CircuitResolver';
import { circuitSwitchUpdates, isSwitchingSymbol, isSymbolOn, symbolSwitchUpdates } from '../project/CommandRequest';
import { chainsFromWalls } from '../project/WallGeometry';
import { scaleObjectPositions, scaleWalls } from '../project/GroupScale';
import { isOpeningType, seatOpeningInWall } from '../project/WallOpenings';
import { setBinding } from '../project/CircuitBindings';
import { routeAround } from '../project/WireRouter';

// The seven drawing-surface collections (objects/connections/meters/
// signalPanels/frames/groupCommands/setpointPanels) and their CRUD
// actions - this is the data an .epwsyn file actually persists.
// Selection, clipboard, and undo/redo over these same arrays each live
// in their own slice instead.
export type ElementsSlice = Pick<AppState,
  | 'objects' | 'connections' | 'meters' | 'signalPanels' | 'frames' | 'groupCommands' | 'setpointPanels' | 'walls'
  | 'addObject' | 'updateObject' | 'updateObjects'
  | 'addConnection' | 'updateConnection'
  | 'addMeter' | 'updateMeter'
  | 'addSignalPanel' | 'updateSignalPanel'
  | 'addFrame' | 'updateFrame'
  | 'addWall' | 'updateWall' | 'applyWallStyleToRoom' | 'addRoomWalls' | 'toggleCircuitAt'
  | 'scaleSelection'
  | 'circuits' | 'setCircuitDevice'
  | 'addGroupCommand' | 'updateGroupCommand'
  | 'addSetpointPanel' | 'updateSetpointPanel'
  | 'deleteObjects'
  | 'recalculateConnectionRoutes'
>;

export const createElementsSlice: StateCreator<AppState, [], [], ElementsSlice> = (set, get) => ({
  objects: [],
  connections: [],
  meters: [],
  signalPanels: [],
  frames: [],
  walls: [],
  circuits: [],
  groupCommands: [],
  setpointPanels: [],

  addObject: (obj) => {
    set((state) => ({
      objects: [...state.objects, { ...obj, id: uuidv4() }]
    }));
    get().saveHistory();
  },

  updateObject: (id, updates) => {
    set((state) => ({
      objects: state.objects.map(obj =>
        obj.id === id ? { ...obj, ...updates } : obj
      ),
      isDirty: true
    }));
  },

  updateObjects: (updates) => {
    set((state) => {
      let newObjects = [...state.objects];
      updates.forEach(u => {
        newObjects = newObjects.map(obj => obj.id === u.id ? { ...obj, ...u.updates } : obj);
      });
      return { objects: newObjects, isDirty: true };
    });
  },

  addWall: (wall) => {
    set((state) => ({
      walls: [...state.walls, { ...wall, id: uuidv4() }],
      isDirty: true
    }));
    get().saveHistory();
  },

  updateWall: (id, updates) => {
    set((state) => ({
      walls: state.walls.map(w => w.id === id ? { ...w, ...updates } : w),
      isDirty: true
    }));
  },

  setCircuitDevice: (circuit, deviceId) => {
    set((state) => ({ circuits: setBinding(state.circuits, circuit, deviceId), isDirty: true }));
    get().saveHistory();
  },

  addRoomWalls: (rect) => {
    const { wallDrawThickness, wallDrawHeight, wallDrawMaterial } = get();
    const { x, y, width, height } = rect;
    // Corners in order, so the four walls chain end to end and the loop
    // closes exactly - which is what RoomFloors.ts needs to recognise a
    // room and give it a floor.
    const corners = [
      { x, y },
      { x: x + width, y },
      { x: x + width, y: y + height },
      { x, y: y + height },
    ];
    const made = corners.map((from, i) => ({
      id: uuidv4(),
      from,
      to: corners[(i + 1) % corners.length],
      thickness: wallDrawThickness,
      height: wallDrawHeight,
      material: wallDrawMaterial,
    }));
    set((state) => ({ walls: [...state.walls, ...made], isDirty: true }));
    // One entry for the whole room: drawing it was one gesture, so one
    // Ctrl+Z must undo all of it.
    get().saveHistory();
  },

  applyWallStyleToRoom: (wallId) => {
    const { walls } = get();
    const source = walls.find(w => w.id === wallId);
    if (!source) return;
    // The room is the CHAIN this wall belongs to - the same grouping the
    // renderer uses, so "the whole room" means exactly what the drawing
    // shows as one body (or would, once the styles agree).
    const chain = chainsFromWalls(walls).find(c => c.wallIds.includes(wallId));
    if (!chain || chain.wallIds.length < 2) return;
    const ids = new Set(chain.wallIds);
    set((state) => ({
      walls: state.walls.map(w => ids.has(w.id)
        ? { ...w, thickness: source.thickness, height: source.height, material: source.material }
        : w),
      isDirty: true,
    }));
    get().saveHistory();
  },

  // feat/cad-marquee: resize whatever is selected - above all a whole
  // room, selected with a crossing marquee over its walls.
  //
  // GEOMETRY SCALES, OBJECTS MOVE (project/GroupScale.ts's header has
  // the full argument): the walls take the new shape, while the chairs,
  // luminaires and doors inside keep their real-world sizes and are
  // carried to the same relative place. A plan is dimensioned; growing
  // a hall does not grow the chairs in it.
  //
  // ONE history entry for the whole drag, written by the caller when the
  // drag ENDS - not per frame, or a single resize would bury the undo
  // stack under sixty identical entries.
  scaleSelection: (before, after, snapStep) => {
    const { walls, objects, selectedWallIds, selectedIds } = get();
    if (selectedWallIds.length === 0 && selectedIds.length === 0) return;
    if (before.width <= 0 && before.height <= 0) return;

    const snap = snapStep && snapStep > 0
      ? (value: number) => Math.round(value / snapStep) * snapStep
      : (value: number) => value;

    const wallUpdates = scaleWalls(walls, selectedWallIds, before, after, snap);
    const objectUpdates = scaleObjectPositions(objects, selectedIds, before, after, snap);

    set((state) => {
      const byId = new Map(wallUpdates.map(u => [u.id, u.updates]));
      const nextWalls = state.walls.map(w => (byId.has(w.id) ? { ...w, ...byId.get(w.id) } : w));

      const objectById = new Map(objectUpdates.map(u => [u.id, u.updates]));
      const nextObjects = state.objects.map(o => {
        const update = objectById.get(o.id);
        if (!update) return o;
        const moved = { ...o, ...update };
        // An opening's place is only meaningful RELATIVE to its wall, so
        // it is re-seated against the walls in their NEW positions - a
        // door carried by the same proportion as a chair would end up
        // beside its wall rather than in it.
        if (!isOpeningType(moved.type)) return moved;
        const seat = seatOpeningInWall(nextWalls, moved);
        return seat ? { ...moved, ...seat } : moved;
      });

      return { walls: nextWalls, objects: nextObjects, isDirty: true };
    });
  },

  // feat/room-plan: switch the whole circuit the given object belongs
  // to. One history entry for the entire circuit, not one per fixture -
  // a click is a single user action however many luminaires it lights.
  // A no-op (and no history entry at all) for an object with no
  // circuit name, so clicking an unassigned fixture in Podglad mode
  // quietly does nothing rather than silently switching every other
  // unassigned fixture on the screen.
  toggleCircuitAt: (objectId) => {
    const { objects, circuits, devices } = get();
    const target = objects.find(o => o.id === objectId);
    if (!target) return;
    // A breaker or disconnect switch on the schematic is the apparatus
    // itself, not a plan circuit: a click opens or closes it.
    if (isSwitchingSymbol(target.type)) {
      const switched = symbolSwitchUpdates(objects, objectId, !isSymbolOn(target));
      if (switched.length === 0) return;
      get().updateObjects(switched);
      get().saveHistory();
      return;
    }
    const turningOn = !isCircuitOn(objects, target.circuit);
    // THE PLAN AND THE SCHEMATIC MOVE TOGETHER - the fixtures on the
    // plan and every schematic symbol carrying the same aparat, in one
    // set of updates. The rule and the reasoning behind it now live in
    // project/CommandRequest.ts's circuitSwitchUpdates, shared with the
    // simulation's confirmed command: two code paths switching a circuit
    // slightly differently is exactly the divergence nobody notices
    // until the two drawings disagree on site.
    const updates = circuitSwitchUpdates(objects, circuits, devices, target.circuit, turningOn);
    if (updates.length === 0) return;

    get().updateObjects(updates);
    get().saveHistory();
  },

  addConnection: (conn) => {
    set((state) => ({
      connections: [...state.connections, { ...conn, id: uuidv4() }],
      isDirty: true
    }));
    get().saveHistory();
  },

  updateConnection: (id, updates) => {
    set((state) => ({
      connections: state.connections.map(c => c.id === id ? { ...c, ...updates } : c),
      isDirty: true
    }));
  },

  addMeter: (meter) => {
    set((state) => ({
      meters: [...state.meters, { ...meter, id: uuidv4() }]
    }));
    get().saveHistory();
  },

  updateMeter: (id, updates) => {
    set((state) => ({
      meters: state.meters.map(m => m.id === id ? { ...m, ...updates } : m),
      isDirty: true
    }));
  },

  addSignalPanel: (panel) => {
    set((state) => ({
      signalPanels: [...state.signalPanels, { ...panel, id: uuidv4() }]
    }));
    get().saveHistory();
  },

  updateSignalPanel: (id, updates) => {
    set((state) => ({
      signalPanels: state.signalPanels.map(p => p.id === id ? { ...p, ...updates } : p),
      isDirty: true
    }));
  },

  addFrame: (frame) => {
    set((state) => ({
      frames: [...state.frames, { ...frame, id: uuidv4() }]
    }));
    get().saveHistory();
  },

  updateFrame: (id, updates) => {
    set((state) => ({
      frames: state.frames.map(f => f.id === id ? { ...f, ...updates } : f),
      isDirty: true
    }));
  },

  addGroupCommand: (el) => {
    set((state) => ({
      groupCommands: [...state.groupCommands, { ...el, id: uuidv4() }]
    }));
    get().saveHistory();
  },

  updateGroupCommand: (id, updates) => {
    set((state) => ({
      groupCommands: state.groupCommands.map(g => g.id === id ? { ...g, ...updates } : g),
      isDirty: true
    }));
  },

  addSetpointPanel: (panel) => {
    set((state) => ({
      setpointPanels: [...state.setpointPanels, { ...panel, id: uuidv4() }]
    }));
    get().saveHistory();
  },

  updateSetpointPanel: (id, updates) => {
    set((state) => ({
      setpointPanels: state.setpointPanels.map(p => p.id === id ? { ...p, ...updates } : p),
      isDirty: true
    }));
  },

  // Bug fix (node-based wiring rewrite): deleting an object used to
  // cascade-delete every connection whose fromId/toId pointed at it. A
  // connection no longer references any object id at all - it is a free
  // polyline that happens to touch a terminal geometrically - so nothing
  // needs to cascade any more. A wire left dangling by a deleted object
  // simply stops being part of any net; it stays on the canvas exactly
  // like drawing a wire into empty space always could.
  deleteObjects: (ids, connIds = [], meterIds = [], signalPanelIds = [], frameIds = [], groupCommandIds = [], setpointPanelIds = [], wallIds = []) => {
    if (ids.length === 0 && connIds.length === 0 && meterIds.length === 0 && signalPanelIds.length === 0 && frameIds.length === 0 && groupCommandIds.length === 0 && setpointPanelIds.length === 0 && wallIds.length === 0) return;
    // feat/water-management commit 1: deleting a symbol releases every
    // wire endpoint anchored to one of its terminals - the point stays
    // exactly where it was (a free end now), never silently left
    // pointing at an object that no longer exists. `releasedCount`
    // escapes the set() callback via this outer variable (zustand's own
    // set() always runs its updater synchronously, so this is safe -
    // no different from reading `get()` again right after) so the
    // Messages notice below can fire only when something real happened.
    let releasedCount = 0;
    set((state) => {
      const released = releaseAnchorsForDeletedObjects(state.connections, ids);
      releasedCount = released.releasedCount;
      return {
        objects: state.objects.filter(obj => !ids.includes(obj.id)),
        selectedIds: state.selectedIds.filter(id => !ids.includes(id)),
        connections: released.connections.filter(c => !connIds.includes(c.id)),
        selectedConnectionIds: state.selectedConnectionIds.filter(id => !connIds.includes(id)),
        meters: state.meters.filter(m => !meterIds.includes(m.id)),
        selectedMeterIds: state.selectedMeterIds.filter(id => !meterIds.includes(id)),
        signalPanels: state.signalPanels.filter(p => !signalPanelIds.includes(p.id)),
        selectedSignalPanelIds: state.selectedSignalPanelIds.filter(id => !signalPanelIds.includes(id)),
        frames: state.frames.filter(f => !frameIds.includes(f.id)),
        selectedFrameIds: state.selectedFrameIds.filter(id => !frameIds.includes(id)),
        groupCommands: state.groupCommands.filter(g => !groupCommandIds.includes(g.id)),
        selectedGroupCommandIds: state.selectedGroupCommandIds.filter(id => !groupCommandIds.includes(id)),
        setpointPanels: state.setpointPanels.filter(p => !setpointPanelIds.includes(p.id)),
        selectedSetpointPanelIds: state.selectedSetpointPanelIds.filter(id => !setpointPanelIds.includes(id)),
        walls: state.walls.filter(w => !wallIds.includes(w.id)),
        selectedWallIds: state.selectedWallIds.filter(id => !wallIds.includes(id))
      };
    });
    if (releasedCount > 0) {
      get().addMessage(`[INFO] Deleting the symbol released ${releasedCount} wire endpoint(s) - they now float free.`);
    }
    get().saveHistory();
  },

  // feat/wire-routing-around-obstacles commit 3, point (f): recomputes
  // each given connection's own route around the screen's current
  // obstacles - a manual wire (isManualRoute) is left untouched
  // entirely, per point (d). Excludes, per connection, whatever
  // symbol(s) its own endpoints are anchored to (the same rule
  // WireCollision.findAllCollisions already applies while drawing) so
  // a wire is never told its own destination valve is blocking it.
  recalculateConnectionRoutes: (ids) => {
    if (ids.length === 0) return;
    set((state) => {
      const screen = {
        objects: state.objects, meters: state.meters, signalPanels: state.signalPanels,
        frames: state.frames, groupCommands: state.groupCommands, setpointPanels: state.setpointPanels
      };
      const connections = state.connections.map(conn => {
        if (!ids.includes(conn.id) || conn.isManualRoute) return conn;
        if (conn.points.length < 2) return conn;
        const first = conn.points[0];
        const last = conn.points[conn.points.length - 1];
        const excludeIds = [...new Set(conn.points.filter(p => p.anchor).map(p => p.anchor!.symbolId))];
        const obstacles = getObstacles(screen, excludeIds);
        const routed = routeAround(first, last, obstacles, state.canvasConfig.gridSize);
        // The router only ever receives/returns plain {x,y} - reattach
        // each endpoint's own original anchor (if any) onto whichever
        // routed point still lands exactly on it (routeAround always
        // starts/ends exactly at the points it was given).
        const points = routed.map((p, i) => {
          if (i === 0 && p.x === first.x && p.y === first.y && first.anchor) return { ...p, anchor: first.anchor };
          if (i === routed.length - 1 && p.x === last.x && p.y === last.y && last.anchor) return { ...p, anchor: last.anchor };
          return p;
        });
        return { ...conn, points };
      });
      return { connections, isDirty: true };
    });
    get().saveHistory();
  },
});
