import type { StateCreator } from 'zustand';
import type { AppState } from './appState';
import { syncAnchoredConnections, findAnchorDiscrepancies } from '../utils/WireAnchoring';
import { findAllCollisions } from '../project/WireCollision';
import { getNewCollisionWarnings } from '../utils/WireCollisionWarnings';

// Cap on how many undo/redo snapshots are kept; each entry is a full deep
// copy of objects+connections+meters+signalPanels+frames, so this bounds both memory and undo depth.
const MAX_HISTORY = 100;

// Undo/redo over the five element arrays (elementsSlice.ts) as one
// combined snapshot per saveHistory() call - every action elsewhere that
// mutates the drawing calls get().saveHistory() itself once it's done,
// rather than this slice reacting to changes on its own.
export type HistorySlice = Pick<AppState, 'history' | 'historyIndex' | 'saveHistory' | 'undo' | 'redo'>;

export const createHistorySlice: StateCreator<AppState, [], [], HistorySlice> = (set, get) => ({
  history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [], groupCommands: [], setpointPanels: [] }],
  historyIndex: 0,

  saveHistory: () => {
    // feat/water-management commit 1: every move/rotate/resize/align/
    // distribute action in this codebase converges on calling this
    // function right after mutating `objects` - the one robust, single
    // hook point to re-derive every anchored wire endpoint's position
    // from its terminal's own CURRENT world position, rather than
    // scattering a call across every individual action (moveSelectionBy,
    // rotateSelected, alignSelected, distributeSelected, updateObject,
    // updateObjects, ObjectNode.tsx's onTransformEnd...). Cheap when
    // nothing is actually anchored (syncAnchoredConnections's own early
    // per-connection skip) and a no-op the instant every anchored point
    // already agrees with its terminal.
    const preSync = get();
    const syncedConnections = syncAnchoredConnections(preSync.connections, preSync.objects);
    if (syncedConnections !== preSync.connections) {
      set({ connections: syncedConnections });
    }

    // fix/wiring-and-library-groups commit 3, point (c): a consistency
    // check, not a fix - every anchored point SHOULD already exactly
    // match its own terminal at this point, since the sync right above
    // just ran. If it does not, something moved a connection's points
    // through a path that never went through that sync at all - worth
    // a Messages notice ("cos jeszcze nie dziala"), not a silent gap.
    const { objects: postSyncObjects, connections: postSyncConnections } = get();
    const discrepancies = findAnchorDiscrepancies(postSyncConnections, postSyncObjects);
    if (discrepancies.length > 0) {
      get().addMessage(`[WARNING] ${discrepancies.length} wire endpoint(s) drifted from their own terminal - reconnect them manually.`);
    }

    // feat/wire-routing-around-obstacles commit 1: a wire crossing an
    // apparatus's body is a WARNING, never a blocker (GRANICE) - posted
    // once per (wire, obstacle) occurrence, via this same "one hook
    // point after every mutation" saveHistory already is, rather than a
    // separate render-driven effect that would fire on every hover.
    const { objects: liveObjects, connections: liveConnections, meters: liveMeters, signalPanels: liveSignalPanels, frames: liveFrames, groupCommands: liveGroupCommands, setpointPanels: liveSetpointPanels } = get();
    const allCollisions = findAllCollisions(liveConnections, {
      objects: liveObjects, meters: liveMeters, signalPanels: liveSignalPanels,
      frames: liveFrames, groupCommands: liveGroupCommands, setpointPanels: liveSetpointPanels
    });
    getNewCollisionWarnings(allCollisions).forEach(c => {
      const wireLabel = liveConnections.find(conn => conn.id === c.connectionId)?.medium || 'Wire';
      get().addMessage(`[WARNING] ${wireLabel} wire crosses ${c.obstacle.label} - route it around instead.`);
    });

    const { objects, connections, meters, signalPanels, frames, groupCommands, setpointPanels, history, historyIndex } = get();
    const objectsJson = JSON.stringify(objects);
    const connectionsJson = JSON.stringify(connections);
    const metersJson = JSON.stringify(meters);
    const signalPanelsJson = JSON.stringify(signalPanels);
    const framesJson = JSON.stringify(frames);
    const groupCommandsJson = JSON.stringify(groupCommands);
    const setpointPanelsJson = JSON.stringify(setpointPanels);

    // Skip if nothing actually changed since the last entry (e.g. a field
    // was clicked into and blurred without editing) - don't clutter undo
    // with no-op entries.
    const lastEntry = history[historyIndex];
    if (
      lastEntry &&
      JSON.stringify(lastEntry.objects) === objectsJson &&
      JSON.stringify(lastEntry.connections) === connectionsJson &&
      JSON.stringify(lastEntry.meters || []) === metersJson &&
      JSON.stringify(lastEntry.signalPanels || []) === signalPanelsJson &&
      JSON.stringify(lastEntry.frames || []) === framesJson &&
      JSON.stringify(lastEntry.groupCommands || []) === groupCommandsJson &&
      JSON.stringify(lastEntry.setpointPanels || []) === setpointPanelsJson
    ) {
      return;
    }

    let newHistory = history.slice(0, historyIndex + 1);
    newHistory.push({
      objects: JSON.parse(objectsJson),
      connections: JSON.parse(connectionsJson),
      meters: JSON.parse(metersJson),
      signalPanels: JSON.parse(signalPanelsJson),
      frames: JSON.parse(framesJson),
      groupCommands: JSON.parse(groupCommandsJson),
      setpointPanels: JSON.parse(setpointPanelsJson)
    });

    // Cap history length; drop oldest entries once the cap is exceeded.
    // The freshly pushed entry is always last, so its index after
    // truncation is simply the new array length minus one.
    if (newHistory.length > MAX_HISTORY) {
      newHistory = newHistory.slice(newHistory.length - MAX_HISTORY);
    }

    set({ history: newHistory, historyIndex: newHistory.length - 1, isDirty: true });
  },

  undo: () => {
    const { history, historyIndex } = get();
    if (historyIndex > 0) {
      const prevState = history[historyIndex - 1];
      set({
        historyIndex: historyIndex - 1,
        objects: JSON.parse(JSON.stringify(prevState.objects || [])),
        connections: JSON.parse(JSON.stringify(prevState.connections || [])),
        meters: JSON.parse(JSON.stringify(prevState.meters || [])),
        signalPanels: JSON.parse(JSON.stringify(prevState.signalPanels || [])),
        frames: JSON.parse(JSON.stringify(prevState.frames || [])),
        groupCommands: JSON.parse(JSON.stringify(prevState.groupCommands || [])),
        setpointPanels: JSON.parse(JSON.stringify(prevState.setpointPanels || [])),
        selectedIds: [],
        selectedConnectionIds: [],
        selectedMeterIds: [],
        selectedSignalPanelIds: [],
        selectedFrameIds: [],
        selectedGroupCommandIds: [],
        selectedSetpointPanelIds: [],
        isDirty: true
      });
    }
  },

  redo: () => {
    const { history, historyIndex } = get();
    if (historyIndex < history.length - 1) {
      const nextState = history[historyIndex + 1];
      set({
        historyIndex: historyIndex + 1,
        objects: JSON.parse(JSON.stringify(nextState.objects || [])),
        connections: JSON.parse(JSON.stringify(nextState.connections || [])),
        meters: JSON.parse(JSON.stringify(nextState.meters || [])),
        signalPanels: JSON.parse(JSON.stringify(nextState.signalPanels || [])),
        frames: JSON.parse(JSON.stringify(nextState.frames || [])),
        groupCommands: JSON.parse(JSON.stringify(nextState.groupCommands || [])),
        setpointPanels: JSON.parse(JSON.stringify(nextState.setpointPanels || [])),
        selectedIds: [],
        selectedConnectionIds: [],
        selectedMeterIds: [],
        selectedSignalPanelIds: [],
        selectedFrameIds: [],
        selectedGroupCommandIds: [],
        selectedSetpointPanelIds: [],
        isDirty: true
      });
    }
  },
});
