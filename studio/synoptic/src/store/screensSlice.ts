import type { StateCreator } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import type { AppState } from './appState';
import {
  blankScreenContent, cloneScreenContent, uniqueScreenName,
} from '../project/ScreenContent';
import type { ScreenContent, ScreenInfo } from '../project/ScreenContent';

// feat/multi-screen: the screens of one project, and switching between
// them.
//
// This is the ONE place that knows the invariant ScreenContent.ts's
// header states: the live objects/connections/walls/... arrays ARE the
// active screen. Everything else in the editor keeps reading those
// arrays and never learns that screens exist.
//
// Undo does NOT cross a screen switch. Each screen keeps its OWN undo
// stack (parked in screenHistories when you leave it, handed back when
// you return), and a screen opened for the first time starts with a
// single snapshot of itself - an undo that silently took you back to
// another room and then started reverting edits there would be worse
// than no undo at all.

export type ScreensSlice = Pick<AppState,
  | 'screens' | 'activeScreenId' | 'screenContents'
  | 'addScreen' | 'renameScreen' | 'deleteScreen' | 'switchScreen' | 'captureActiveScreen'
>;

/** The live arrays, as a ScreenContent. */
function liveContent(state: AppState): ScreenContent {
  return {
    objects: state.objects,
    connections: state.connections,
    meters: state.meters,
    signalPanels: state.signalPanels,
    frames: state.frames,
    walls: state.walls,
    groupCommands: state.groupCommands,
    setpointPanels: state.setpointPanels,
    floorMaterial: state.canvasConfig.floorMaterial,
  };
}

/** The store patch that puts one screen's content into the live arrays. */
function applyContent(state: AppState, content: ScreenContent) {
  return {
    objects: content.objects,
    connections: content.connections,
    meters: content.meters,
    signalPanels: content.signalPanels,
    frames: content.frames,
    walls: content.walls,
    groupCommands: content.groupCommands,
    setpointPanels: content.setpointPanels,
    canvasConfig: { ...state.canvasConfig, floorMaterial: content.floorMaterial },
    // Nothing on the incoming screen can be selected yet, and a
    // selection carried over from the previous one would point at
    // objects that are no longer on the canvas.
    selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [],
    selectedSignalPanelIds: [], selectedFrameIds: [], selectedGroupCommandIds: [],
    selectedSetpointPanelIds: [], selectedWallIds: [],
    // Undo starts fresh on the screen you are now looking at.
    history: [{
      objects: cloneScreenContent(content).objects,
      connections: cloneScreenContent(content).connections,
      meters: cloneScreenContent(content).meters,
      signalPanels: cloneScreenContent(content).signalPanels,
      frames: cloneScreenContent(content).frames,
      walls: cloneScreenContent(content).walls,
      circuits: JSON.parse(JSON.stringify(state.circuits)),
      groupCommands: cloneScreenContent(content).groupCommands,
      setpointPanels: cloneScreenContent(content).setpointPanels,
    }],
    historyIndex: 0,
  };
}

/** The view a screen gets before it has ever been looked at. */
const DEFAULT_VIEW = { zoom: 1, panX: 0, panY: 0 };

/**
 * The patch that remembers how the screen being LEFT was being looked at
 * and what its undo stack held - see workspaceSlice.ts for why switching
 * between tiles must lose neither.
 */
function parkView(state: AppState) {
  return {
    screenViews: { ...state.screenViews, [state.activeScreenId]: state.canvasState },
    screenHistories: {
      ...state.screenHistories,
      [state.activeScreenId]: { history: state.history, historyIndex: state.historyIndex },
    },
  };
}

export const createScreensSlice: StateCreator<AppState, [], [], ScreensSlice> = (set, get) => ({
  // A project always has at least one screen. The default is created
  // here rather than lazily, so "how many screens are there" never has
  // a zero answer that every caller would have to special-case.
  screens: [{ id: 'screen-1', name: 'Screen 1' }] as ScreenInfo[],
  activeScreenId: 'screen-1',
  screenContents: {},

  /** Flush the live arrays into the map. Anything that reads ALL screens - saving, above all - must call this first. */
  captureActiveScreen: () => {
    set((state) => ({
      screenContents: {
        ...state.screenContents,
        [state.activeScreenId]: cloneScreenContent(liveContent(state)),
      },
    }));
  },

  addScreen: (name) => {
    const id = uuidv4();
    set((state) => {
      // Default to the next number rather than the bare word, so a
      // second screen is "Screen 2" and not "Screen" sitting next to
      // "Screen 1". uniqueScreenName still guards the case where that
      // number is already taken by a renamed screen.
      const suggested = (name || '').trim() || `Screen ${state.screens.length + 1}`;
      const screenName = uniqueScreenName(state.screens, suggested);
      return {
        // Park the screen being left, then open the new, empty one.
        screenContents: {
          ...state.screenContents,
          [state.activeScreenId]: cloneScreenContent(liveContent(state)),
        },
        screens: [...state.screens, { id, name: screenName }],
        activeScreenId: id,
        isDirty: true,
        ...parkView(state),
        canvasState: DEFAULT_VIEW,
        ...applyContent(state, blankScreenContent()),
      };
    });
  },

  renameScreen: (id, name) => {
    const trimmed = name.trim();
    if (!trimmed) return; // a screen with no name cannot be picked out of a tab bar
    set((state) => ({
      screens: state.screens.map(s => s.id === id ? { ...s, name: trimmed } : s),
      isDirty: true,
    }));
  },

  deleteScreen: (id) => {
    const state = get();
    // The last screen is not deletable: a project with no screens has
    // nothing to draw on, and every caller would need a special case.
    if (state.screens.length <= 1) {
      get().addMessage('[WARNING] The last screen cannot be deleted - a project needs at least one.');
      return;
    }
    const remaining = state.screens.filter(s => s.id !== id);
    const nextActiveId = state.activeScreenId === id ? remaining[0].id : state.activeScreenId;

    set((current) => {
      const contents = { ...current.screenContents };
      // Park the live arrays first if we are standing on a screen that
      // is NOT the one being deleted - otherwise they are about to be
      // replaced by the screen we move to and would be lost.
      if (current.activeScreenId !== id) {
        contents[current.activeScreenId] = cloneScreenContent(liveContent(current));
      }
      delete contents[id];

      const views = { ...current.screenViews };
      const histories = { ...current.screenHistories };
      delete views[id];
      delete histories[id];

      const patch: Partial<AppState> = {
        screens: remaining,
        activeScreenId: nextActiveId,
        screenContents: contents,
        screenViews: views,
        screenHistories: histories,
        hiddenScreens: current.hiddenScreens.filter(h => h !== id),
        isDirty: true,
      };
      // Only reload the canvas when the deleted screen was the one on
      // display; deleting a background screen must not disturb the
      // drawing in front of you.
      if (current.activeScreenId === id) {
        Object.assign(patch, applyContent(current, contents[nextActiveId] ?? blankScreenContent()));
        patch.canvasState = views[nextActiveId] ?? DEFAULT_VIEW;
        if (histories[nextActiveId]) Object.assign(patch, histories[nextActiveId]);
      }
      return patch as never;
    });
  },

  switchScreen: (id) => {
    const state = get();
    if (id === state.activeScreenId) return;
    if (!state.screens.some(s => s.id === id)) return;

    set((current) => {
      const contents = {
        ...current.screenContents,
        [current.activeScreenId]: cloneScreenContent(liveContent(current)),
      };
      return {
        screenContents: contents,
        activeScreenId: id,
        ...parkView(current),
        // The incoming screen's own view, or a neutral one that Canvas
        // then fits to the content the first time the screen is opened.
        canvasState: current.screenViews[id] ?? DEFAULT_VIEW,
        ...applyContent(current, contents[id] ?? blankScreenContent()),
        // Its own undo stack back, when it has one - spread AFTER
        // applyContent, which starts a fresh one.
        ...(current.screenHistories[id] ?? {}),
      } as never;
    });
  },
});
