import type { StateCreator } from 'zustand';
import type { AppState } from './appState';
import { loadRecent, recordRecent, saveRecent } from '../project/RecentSymbols';

// feat/library-recent-and-search: which symbols were reached for most
// recently, so the library can put them first.
//
// Session state that OUTLIVES the session, which is why it is not simply
// a useState in the Toolbox: the list is read back at startup
// (project/RecentSymbols.ts) and written on every use, and a component
// that unmounts must not be where that lives. It is never part of a
// project file - it describes the person drawing, not the drawing.
export type LibrarySlice = Pick<AppState, 'recentSymbols' | 'recordSymbolUse'>;

export const createLibrarySlice: StateCreator<AppState, [], [], LibrarySlice> = (set) => ({
  recentSymbols: loadRecent(),

  recordSymbolUse: (type) => {
    set((state) => {
      const next = recordRecent(state.recentSymbols, type);
      // Written through on every change rather than on some later flush:
      // there is no "close the library" moment to hang a save on, and
      // the editor can be closed at any point.
      saveRecent(next);
      return { recentSymbols: next };
    });
  },
});
