import type { StateCreator } from 'zustand';
import type { AppState } from './appState';

// The seven parallel "selected ids" arrays (one per element kind - see
// elementsSlice.ts) and every action that reads or replaces them,
// including the rubber-band's cross-kind selectMixed and arrow-key
// moveSelectionBy.
export type SelectionSlice = Pick<AppState,
  | 'selectedIds' | 'selectedConnectionIds' | 'selectedMeterIds' | 'selectedSignalPanelIds' | 'selectedFrameIds' | 'selectedGroupCommandIds' | 'selectedSetpointPanelIds'
  | 'selectObjects' | 'selectConnections' | 'selectMeters' | 'selectSignalPanels' | 'selectFrames' | 'selectGroupCommands' | 'selectSetpointPanels'
  | 'selectMixed' | 'selectAll' | 'clearSelection' | 'moveSelectionBy'
>;

export const createSelectionSlice: StateCreator<AppState, [], [], SelectionSlice> = (set, get) => ({
  selectedIds: [],
  selectedConnectionIds: [],
  selectedMeterIds: [],
  selectedSignalPanelIds: [],
  selectedFrameIds: [],
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
    return { selectedIds: ids, selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: [] };
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
    return { selectedConnectionIds: ids, selectedIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: [] };
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
    return { selectedMeterIds: ids, selectedIds: [], selectedConnectionIds: [], selectedSignalPanelIds: [], selectedFrameIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: [] };
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
    return { selectedSignalPanelIds: ids, selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedFrameIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: [] };
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
    return { selectedFrameIds: ids, selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: [] };
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
    return { selectedGroupCommandIds: ids, selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [], selectedSetpointPanelIds: [] };
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
    return { selectedSetpointPanelIds: ids, selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [], selectedGroupCommandIds: [] };
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
    selectedGroupCommandIds: selection.groupCommandIds || [],
    selectedSetpointPanelIds: selection.setpointPanelIds || []
  }),

  selectAll: () => {
    const { objects, connections, meters, signalPanels, frames, groupCommands, setpointPanels } = get();
    set({
      selectedIds: objects.map(o => o.id),
      selectedConnectionIds: connections.map(c => c.id),
      selectedMeterIds: meters.map(m => m.id),
      selectedSignalPanelIds: signalPanels.map(p => p.id),
      selectedFrameIds: frames.map(f => f.id),
      selectedGroupCommandIds: groupCommands.map(g => g.id),
      selectedSetpointPanelIds: setpointPanels.map(p => p.id)
    });
  },

  clearSelection: () => set({ selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: [] }),

  // Locked objects are skipped, same as an ordinary drag already
  // refuses to move them (draggable={!obj.locked} in Canvas.tsx) -
  // arrow-key movement is not a back door around a lock. Meters and
  // connections have no lock flag of their own, so every selected one
  // of those always moves. A single set() call, then one saveHistory()
  // - one history entry per keypress, not per moved item.
  moveSelectionBy: (dx, dy) => {
    const { selectedIds, selectedMeterIds, selectedConnectionIds, selectedSignalPanelIds, selectedFrameIds, selectedGroupCommandIds, selectedSetpointPanelIds } = get();
    if (selectedIds.length === 0 && selectedMeterIds.length === 0 && selectedConnectionIds.length === 0 && selectedSignalPanelIds.length === 0 && selectedFrameIds.length === 0 && selectedGroupCommandIds.length === 0 && selectedSetpointPanelIds.length === 0) return;
    set((state) => ({
      objects: state.objects.map(o => (selectedIds.includes(o.id) && !o.locked) ? { ...o, x: o.x + dx, y: o.y + dy } : o),
      meters: state.meters.map(m => selectedMeterIds.includes(m.id) ? { ...m, x: m.x + dx, y: m.y + dy } : m),
      signalPanels: state.signalPanels.map(p => selectedSignalPanelIds.includes(p.id) ? { ...p, x: p.x + dx, y: p.y + dy } : p),
      frames: state.frames.map(f => selectedFrameIds.includes(f.id) ? { ...f, x: f.x + dx, y: f.y + dy } : f),
      groupCommands: state.groupCommands.map(g => selectedGroupCommandIds.includes(g.id) ? { ...g, x: g.x + dx, y: g.y + dy } : g),
      setpointPanels: state.setpointPanels.map(p => selectedSetpointPanelIds.includes(p.id) ? { ...p, x: p.x + dx, y: p.y + dy } : p),
      // fix/wiring-and-library-groups commit 3: a selected connection's
      // own points used to be shifted by the plain (dx,dy) vector as a
      // bare {x,y} literal - silently dropping any `anchor` field along
      // the way, with no message, no matter WHY the point was moving.
      // That is correct ONLY when this same group move is deliberately
      // detaching the wire from a terminal it is not moving together
      // with (its own anchor's symbol id is not part of THIS move) -
      // the same "manually moving an anchored point breaks the anchor"
      // rule ConnectionNode.tsx's own per-point drag already applies,
      // now extended to this coarser, whole-connection move. When the
      // anchor's OWN symbol IS moving together with it (selectedIds
      // includes it too - e.g. a rubber-band selection spanning both a
      // symbol and its own wire), the point keeps its anchor: both move
      // by the identical vector, so the numbers agree either way, and
      // the very next saveHistory's own syncAnchoredConnections simply
      // confirms it rather than fighting a stale, silently-broken one
      // the next time the symbol alone moves.
      connections: state.connections.map(c => selectedConnectionIds.includes(c.id)
        ? { ...c, points: c.points.map(p => {
            if (p.anchor && !selectedIds.includes(p.anchor.symbolId)) {
              const { anchor: _anchor, ...rest } = p;
              return { ...rest, x: p.x + dx, y: p.y + dy };
            }
            return { ...p, x: p.x + dx, y: p.y + dy };
          }) }
        : c)
    }));
    get().saveHistory();
  },
});
