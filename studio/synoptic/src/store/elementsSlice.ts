import type { StateCreator } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import type { AppState } from './appState';
import { releaseAnchorsForDeletedObjects } from '../utils/WireAnchoring';
import { getObstacles } from '../project/WireCollision';
import { routeAround } from '../project/WireRouter';

// The seven drawing-surface collections (objects/connections/meters/
// signalPanels/frames/groupCommands/setpointPanels) and their CRUD
// actions - this is the data an .epwsyn file actually persists.
// Selection, clipboard, and undo/redo over these same arrays each live
// in their own slice instead.
export type ElementsSlice = Pick<AppState,
  | 'objects' | 'connections' | 'meters' | 'signalPanels' | 'frames' | 'groupCommands' | 'setpointPanels'
  | 'addObject' | 'updateObject' | 'updateObjects'
  | 'addConnection' | 'updateConnection'
  | 'addMeter' | 'updateMeter'
  | 'addSignalPanel' | 'updateSignalPanel'
  | 'addFrame' | 'updateFrame'
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
  deleteObjects: (ids, connIds = [], meterIds = [], signalPanelIds = [], frameIds = [], groupCommandIds = [], setpointPanelIds = []) => {
    if (ids.length === 0 && connIds.length === 0 && meterIds.length === 0 && signalPanelIds.length === 0 && frameIds.length === 0 && groupCommandIds.length === 0 && setpointPanelIds.length === 0) return;
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
        selectedSetpointPanelIds: state.selectedSetpointPanelIds.filter(id => !setpointPanelIds.includes(id))
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
