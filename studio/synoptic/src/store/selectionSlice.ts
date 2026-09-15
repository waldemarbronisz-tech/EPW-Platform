import type { StateCreator } from 'zustand';
import { moveWall } from '../elements/WallElement';
import { restrictSelectionToMode } from '../project/WorkModes';
import type { AppState } from './appState';

// The seven parallel "selected ids" arrays (one per element kind - see
// elementsSlice.ts) and every action that reads or replaces them,
// including the rubber-band's cross-kind selectMixed and arrow-key
// moveSelectionBy.
export type SelectionSlice = Pick<AppState,
  | 'selectedIds' | 'selectedConnectionIds' | 'selectedMeterIds' | 'selectedSignalPanelIds' | 'selectedFrameIds' | 'selectedGroupCommandIds' | 'selectedSetpointPanelIds' | 'selectedWallIds'
  | 'selectObjects' | 'selectConnections' | 'selectMeters' | 'selectSignalPanels' | 'selectFrames' | 'selectGroupCommands' | 'selectSetpointPanels' | 'selectWalls'
  | 'selectMixed' | 'selectAll' | 'clearSelection' | 'moveSelectionBy' | 'moveElementsBy'
>;

export const createSelectionSlice: StateCreator<AppState, [], [], SelectionSlice> = (set, get) => ({
  selectedIds: [],
  selectedConnectionIds: [],
  selectedMeterIds: [],
  selectedSignalPanelIds: [],
  selectedFrameIds: [],
  selectedWallIds: [],
  selectedGroupCommandIds: [],
  selectedSetpointPanelIds: [],

  // multi (Shift held, commit 3) toggles WITHIN this one kind's array
  // and leaves the other kinds' current selection untouched - that
  // is what lets a Shift+click build a selection spanning objects,
  // connections, meters and signal panels together, one click at a
  // time. A plain click (multi false) still replaces the whole
  // selection with just this one kind, same as before.
  selectObjects: (ids, multi = false) => set((state) => {
    if (multi) {
      const newSelection = [...state.selectedIds];
      ids.forEach(id => {
        const index = newSelection.indexOf(id);
        if (index >= 0) newSelection.splice(index, 1);
        else newSelection.push(id);
      });
      return { selectedIds: newSelection };
    }
    // A plain click replaces the WHOLE selection - every kind, walls and
    // frames included (they used to survive a click on anything else,
    // and Delete then removed them too).
    return { selectedIds: ids, selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: [], selectedWallIds: [] };
  }),

  selectConnections: (ids, multi = false) => set((state) => {
    if (multi) {
      const newSelection = [...state.selectedConnectionIds];
      ids.forEach(id => {
        const index = newSelection.indexOf(id);
        if (index >= 0) newSelection.splice(index, 1);
        else newSelection.push(id);
      });
      return { selectedConnectionIds: newSelection };
    }
    // A plain click replaces the WHOLE selection - every kind, walls and
    // frames included (they used to survive a click on anything else,
    // and Delete then removed them too).
    return { selectedConnectionIds: ids, selectedIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: [], selectedWallIds: [] };
  }),

  selectMeters: (ids, multi = false) => set((state) => {
    if (multi) {
      const newSelection = [...state.selectedMeterIds];
      ids.forEach(id => {
        const index = newSelection.indexOf(id);
        if (index >= 0) newSelection.splice(index, 1);
        else newSelection.push(id);
      });
      return { selectedMeterIds: newSelection };
    }
    // A plain click replaces the WHOLE selection - every kind, walls and
    // frames included (they used to survive a click on anything else,
    // and Delete then removed them too).
    return { selectedMeterIds: ids, selectedIds: [], selectedConnectionIds: [], selectedSignalPanelIds: [], selectedFrameIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: [], selectedWallIds: [] };
  }),

  selectSignalPanels: (ids, multi = false) => set((state) => {
    if (multi) {
      const newSelection = [...state.selectedSignalPanelIds];
      ids.forEach(id => {
        const index = newSelection.indexOf(id);
        if (index >= 0) newSelection.splice(index, 1);
        else newSelection.push(id);
      });
      return { selectedSignalPanelIds: newSelection };
    }
    // A plain click replaces the WHOLE selection - every kind, walls and
    // frames included (they used to survive a click on anything else,
    // and Delete then removed them too).
    return { selectedSignalPanelIds: ids, selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedFrameIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: [], selectedWallIds: [] };
  }),

  selectWalls: (ids, multi = false) => set((state) => {
    if (multi) {
      const newSelection = [...state.selectedWallIds];
      ids.forEach(id => {
        const i = newSelection.indexOf(id);
        if (i >= 0) newSelection.splice(i, 1);
        else newSelection.push(id);
      });
      return { selectedWallIds: newSelection };
    }
    // A plain click replaces the WHOLE selection - every kind, walls and
    // frames included (they used to survive a click on anything else,
    // and Delete then removed them too).
    return { selectedWallIds: ids, selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: [] };
  }),

  selectFrames: (ids, multi = false) => set((state) => {
    if (multi) {
      const newSelection = [...state.selectedFrameIds];
      ids.forEach(id => {
        const index = newSelection.indexOf(id);
        if (index >= 0) newSelection.splice(index, 1);
        else newSelection.push(id);
      });
      return { selectedFrameIds: newSelection };
    }
    // A plain click replaces the WHOLE selection - every kind, walls and
    // frames included (they used to survive a click on anything else,
    // and Delete then removed them too).
    return { selectedFrameIds: ids, selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: [], selectedWallIds: [] };
  }),

  selectGroupCommands: (ids, multi = false) => set((state) => {
    if (multi) {
      const newSelection = [...state.selectedGroupCommandIds];
      ids.forEach(id => {
        const index = newSelection.indexOf(id);
        if (index >= 0) newSelection.splice(index, 1);
        else newSelection.push(id);
      });
      return { selectedGroupCommandIds: newSelection };
    }
    // A plain click replaces the WHOLE selection - every kind, walls and
    // frames included (they used to survive a click on anything else,
    // and Delete then removed them too).
    return { selectedGroupCommandIds: ids, selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [], selectedSetpointPanelIds: [], selectedWallIds: [] };
  }),

  selectSetpointPanels: (ids, multi = false) => set((state) => {
    if (multi) {
      const newSelection = [...state.selectedSetpointPanelIds];
      ids.forEach(id => {
        const index = newSelection.indexOf(id);
        if (index >= 0) newSelection.splice(index, 1);
        else newSelection.push(id);
      });
      return { selectedSetpointPanelIds: newSelection };
    }
    // A plain click replaces the WHOLE selection - every kind, walls and
    // frames included (they used to survive a click on anything else,
    // and Delete then removed them too).
    return { selectedSetpointPanelIds: ids, selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [], selectedGroupCommandIds: [], selectedWallIds: [] };
  }),

  // The rubber-band (commit 3, feat/editing-and-signal-panel) selects
  // across all five kinds at once (frames joined in commit 2, feat/
  // appearance-selection-frames), in a single atomic replace - calling
  // the per-kind actions above in sequence would not work here, since
  // a plain (non-multi) call to any one of them clears the others.
  selectMixed: (selection) => set({
    selectedIds: selection.objectIds || [],
    selectedConnectionIds: selection.connectionIds || [],
    selectedMeterIds: selection.meterIds || [],
    selectedSignalPanelIds: selection.signalPanelIds || [],
    selectedFrameIds: selection.frameIds || [],
    selectedWallIds: selection.wallIds || [],
    selectedGroupCommandIds: selection.groupCommandIds || [],
    selectedSetpointPanelIds: selection.setpointPanelIds || []
  }),

  // Ctrl+A takes everything on the current screen, whatever the work
  // mode - editing is mode-independent (WorkModes.ts header);
  // restrictSelectionToMode() is kept in the chain as the one place that
  // rule lives, today it excludes nothing.
  selectAll: () => {
    const { objects, connections, meters, signalPanels, frames, groupCommands, setpointPanels, walls, workMode } = get();
    const reachable = restrictSelectionToMode({
      objectIds: objects.map(o => o.id),
      connectionIds: connections.map(c => c.id),
      meterIds: meters.map(m => m.id),
      signalPanelIds: signalPanels.map(p => p.id),
      frameIds: frames.map(f => f.id),
      groupCommandIds: groupCommands.map(g => g.id),
      setpointPanelIds: setpointPanels.map(p => p.id),
      wallIds: walls.map(w => w.id),
    }, objects, workMode);
    set({
      selectedIds: reachable.objectIds,
      selectedConnectionIds: reachable.connectionIds,
      selectedMeterIds: reachable.meterIds,
      selectedSignalPanelIds: reachable.signalPanelIds,
      selectedFrameIds: reachable.frameIds,
      selectedWallIds: reachable.wallIds,
      selectedGroupCommandIds: reachable.groupCommandIds,
      selectedSetpointPanelIds: reachable.setpointPanelIds
    });
  },

  clearSelection: () => set({ selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: [], selectedWallIds: [] }),

  // Arrow keys: the current selection, through the same primitive a room
  // drag uses.
  moveSelectionBy: (dx, dy) => {
    const s = get();
    get().moveElementsBy({
      objectIds: s.selectedIds,
      connectionIds: s.selectedConnectionIds,
      meterIds: s.selectedMeterIds,
      signalPanelIds: s.selectedSignalPanelIds,
      frameIds: s.selectedFrameIds,
      groupCommandIds: s.selectedGroupCommandIds,
      setpointPanelIds: s.selectedSetpointPanelIds,
      wallIds: s.selectedWallIds,
    }, dx, dy);
  },

  // Locked objects are skipped, same as an ordinary drag already refuses
  // to move them - a move is not a back door around a lock. A single set()
  // call, then one saveHistory() - one history entry per move, not per
  // moved item (a live drag passes saveHistory=false and saves once when
  // it ends).
  moveElementsBy: (selection, dx, dy, saveHistory = true) => {
    const { objectIds: ids, meterIds, connectionIds, signalPanelIds, frameIds, groupCommandIds, setpointPanelIds, wallIds } = selection;
    const nothing = [ids, meterIds, connectionIds, signalPanelIds, frameIds, groupCommandIds, setpointPanelIds, wallIds].every(list => list.length === 0);
    if (nothing || (dx === 0 && dy === 0)) return;
    set((state) => ({
      objects: state.objects.map(o => (ids.includes(o.id) && !o.locked) ? { ...o, x: o.x + dx, y: o.y + dy } : o),
      meters: state.meters.map(m => meterIds.includes(m.id) ? { ...m, x: m.x + dx, y: m.y + dy } : m),
      signalPanels: state.signalPanels.map(p => signalPanelIds.includes(p.id) ? { ...p, x: p.x + dx, y: p.y + dy } : p),
      frames: state.frames.map(f => frameIds.includes(f.id) ? { ...f, x: f.x + dx, y: f.y + dy } : f),
      // A wall has no x/y of its own - both endpoints move together
      // (moveWall), which is the only way it cannot deform.
      walls: state.walls.map(w => wallIds.includes(w.id) ? { ...w, ...moveWall(w, dx, dy) } : w),
      groupCommands: state.groupCommands.map(g => groupCommandIds.includes(g.id) ? { ...g, x: g.x + dx, y: g.y + dy } : g),
      setpointPanels: state.setpointPanels.map(p => setpointPanelIds.includes(p.id) ? { ...p, x: p.x + dx, y: p.y + dy } : p),
      // A moved wire keeps a point's anchor only when the anchor's own
      // symbol moves with it; otherwise the point is detached, as a
      // manual move of an anchored point always has been.
      connections: state.connections.map(c => connectionIds.includes(c.id)
        ? { ...c, points: c.points.map(p => {
            if (p.anchor && !ids.includes(p.anchor.symbolId)) {
              const { anchor: _anchor, ...rest } = p;
              return { ...rest, x: p.x + dx, y: p.y + dy };
            }
            return { ...p, x: p.x + dx, y: p.y + dy };
          }) }
        : c),
      isDirty: true,
    }));
    if (saveHistory) get().saveHistory();
  },
});
