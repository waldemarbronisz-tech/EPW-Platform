import type { StateCreator } from 'zustand';
import { COLOR_CANVAS_BACKGROUND, GRID_SIZE } from '../theme/ScadaTheme';
import type { Device } from '../project/DeviceSchema';
import type { CanvasState, Message } from './types';
import type { AppState } from './appState';

// Project-level state: metadata, the file this project is saved to,
// dirty/messages, and the read-only device list - none of it touches the
// drawing itself (objects/connections/...), which lives in elementsSlice.
export type ProjectSlice = Pick<AppState,
  | 'projectMetadata' | 'canvasConfig' | 'projectName' | 'fileName' | 'fileHandle'
  | 'isDirty' | 'messages' | 'devices'
  | 'setProjectName' | 'setFileName' | 'setFileHandle' | 'setDirty' | 'addMessage' | 'setCanvasState'
  | 'screenKind' | 'setScreenKind'
>;

export const createProjectSlice: StateCreator<AppState, [], [], ProjectSlice> = (set) => ({
  projectMetadata: {
    description: "",
    created_at: new Date().toISOString(),
    modified_at: new Date().toISOString()
  },
  canvasConfig: {
    width: 1920,
    height: 1080,
    background: COLOR_CANVAS_BACKGROUND,
    gridSize: GRID_SIZE
  },
  projectName: 'New Project',
  fileName: null,
  fileHandle: null,
  isDirty: false,
  messages: [],
  devices: [] as Device[],

  // chore/remove-isometric-plan-mode: SCHEMATIC is the only value left -
  // see appState.ts's own comment on this field for why it stays at
  // all. Previously lived in its own planSlice.ts, alongside the now-
  // removed isometric PLAN mode's placed-object/terrain state; folded
  // in here since it is genuinely project-level metadata, same as
  // projectName/canvasConfig above.
  screenKind: 'SCHEMATIC',
  setScreenKind: (kind) => set({ screenKind: kind }),

  setProjectName: (name) => set({ projectName: name, isDirty: true }),
  setFileName: (name) => set({ fileName: name }),
  setFileHandle: (handle) => set({ fileHandle: handle }),
  setDirty: (dirty) => set({ isDirty: dirty }),
  addMessage: (text) => {
    let type: 'info' | 'error' | 'warning' = 'info';
    if (text.startsWith('[ERROR]')) type = 'error';
    if (text.startsWith('[WARNING]')) type = 'warning';

    const msg: Message = {
      id: Date.now().toString() + Math.random().toString(),
      type,
      text: text.replace(/\[.*?\]\s*/, ''),
      time: new Date().toLocaleTimeString()
    };
    set(state => ({ messages: [...state.messages, msg] }));
  },

  setCanvasState: (state) => set((prev) => ({
    canvasState: { ...prev.canvasState, ...state } as CanvasState
  })),
});
