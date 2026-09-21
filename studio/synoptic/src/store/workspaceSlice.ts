import type { StateCreator } from 'zustand';
import type { AppState } from './appState';
import { visibleScreens } from '../project/WorkspaceLayout';

// feat/workspace: every screen of the project on show at once, as tiled
// windows - and whichever one you work in is the active one.
//
// WHAT "ACTIVE" MEANS. The live objects/walls/... arrays ARE the active
// screen (project/ScreenContent.ts), so exactly one tile holds the real
// editor at any moment. The difference from the first version of this
// workspace is that the user never has to think about that: pressing,
// scrolling or dragging a symbol into ANY tile makes it the active one
// first (ScreenWorkspace.tsx), and the lower panel follows it. It reads
// as a set of ordinary windows, each of which is live the moment you
// touch it.
//
// SWITCHING MUST BE INVISIBLE, which is what the two maps below are for.
//   screenViews     - each screen's own zoom and pan. A tile that jumped
//                     to 100% top-left every time it was clicked would
//                     make clicking a tile feel like a reload.
//   screenHistories - each screen's own undo stack. Clicking between
//                     tiles is now constant, and an undo stack that
//                     emptied on every click would be an undo stack
//                     nobody could use. Undo still never crosses from
//                     one screen into another: each screen only ever
//                     gets its own stack back.
//
// All of it is session state - how you are looking at the project, not
// what the project is - so none of it is ever serialized.

export type WorkspaceSlice = Pick<AppState,
  | 'workspaceLayout' | 'hiddenScreens' | 'screenViews' | 'screenHistories' | 'tileFrames'
  | 'canvasViewportSize'
  | 'setWorkspaceLayout' | 'showScreen' | 'hideScreen' | 'setTileFrame' | 'arrangeFreely'
  | 'setCanvasViewportSize'
>;

export const createWorkspaceSlice: StateCreator<AppState, [], [], WorkspaceSlice> = (set, get) => ({
  // Tiled by default: a project with several screens should show them
  // all without anyone having to find a menu first. With one screen the
  // single tile simply fills the area, exactly like the old editor.
  workspaceLayout: 'grid',
  // Screens taken off the workspace by the user. Stored as the HIDDEN
  // ones rather than the shown ones so a new screen appears on its own -
  // adding a screen and then having to go and tick it would be a second
  // step nobody expects.
  hiddenScreens: [],
  screenViews: {},
  screenHistories: {},
  tileFrames: {},

  setWorkspaceLayout: (layout) => set({ workspaceLayout: layout }),
  canvasViewportSize: { width: 0, height: 0 },
  setCanvasViewportSize: (size) => set({ canvasViewportSize: size }),

  // feat/window-snapping: a tile dragged by its caption. The first drag
  // freezes the current automatic arrangement into frames (so the other
  // tiles stay exactly where they were) and switches to `free`.
  setTileFrame: (screenId, frame) => set((state) => ({
    workspaceLayout: 'free',
    tileFrames: { ...state.tileFrames, [screenId]: frame },
  })),

  arrangeFreely: (frames) => set((state) => ({
    workspaceLayout: 'free',
    tileFrames: { ...state.tileFrames, ...frames },
  })),

  showScreen: (screenId) => {
    set((state) => ({ hiddenScreens: state.hiddenScreens.filter(id => id !== screenId) }));
  },

  hideScreen: (screenId) => {
    const state = get();
    if (!state.screens.some(s => s.id === screenId)) return;

    if (screenId === state.activeScreenId) {
      // The active screen can be hidden, but only by handing "active" to
      // another visible tile first - an active screen nobody can see is
      // not a state worth being able to reach. With nothing else on show
      // the request is refused rather than leaving an empty workspace.
      const visible = visibleScreens(state.hiddenScreens, state.activeScreenId, state.workspaceLayout, state.screens.map(s => s.id));
      const next = visible.find(id => id !== screenId);
      if (!next) return;
      state.switchScreen(next);
    }

    set((current) => ({
      hiddenScreens: [...current.hiddenScreens.filter(id => id !== screenId), screenId],
    }));
  },
});
