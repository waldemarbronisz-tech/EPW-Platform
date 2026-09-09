import { create } from 'zustand';
import { createProjectSlice } from './store/projectSlice';
import { createToolsSlice } from './store/toolsSlice';
import { createElementsSlice } from './store/elementsSlice';
import { createSelectionSlice } from './store/selectionSlice';
import { createClipboardSlice } from './store/clipboardSlice';
import { createHistorySlice } from './store/historySlice';
import { createLayoutSlice } from './store/layoutSlice';
import { createDeviceRegistrySlice } from './store/deviceRegistrySlice';
import { createHelpSlice } from './store/helpSlice';
import { createDeviceFormSlice } from './store/deviceFormSlice';
import type { AppState } from './store/appState';

// Internal-audit fix (god-file breakup): this file used to hold the
// entire ~926-line store - every type, every field, every action - in
// one place. The shape types now live in ./store/types.ts, the combined
// AppState interface in ./store/appState.ts, and the implementation is
// split by concern into ./store/*Slice.ts files, following Zustand's own
// documented "slices" pattern (each slice is typed as
// StateCreator<AppState, [], [], ItsOwnSlice>, so cross-slice get()/set()
// calls - e.g. every elementsSlice action ending in get().saveHistory(),
// which lives in historySlice - still type-check against the full store).
//
// This file is now just the composition root, and re-exports every type
// the rest of the app already imports from here (`from '../store'` /
// `from './store'`, ~40 call sites) so none of them need to change.
export type { AppState } from './store/appState';
export type {
  CanvasState,
  HistorySnapshot,
  Message,
  ScreenKind,
  SynopticConnection,
  SynopticObject,
  WirePoint,
  WirePointAnchor,
} from './store/types';

export const useStore = create<AppState>()((...a) => ({
  ...createProjectSlice(...a),
  ...createToolsSlice(...a),
  ...createElementsSlice(...a),
  ...createSelectionSlice(...a),
  ...createClipboardSlice(...a),
  ...createHistorySlice(...a),
  ...createLayoutSlice(...a),
  ...createDeviceRegistrySlice(...a),
  ...createHelpSlice(...a),
  ...createDeviceFormSlice(...a),
}));
