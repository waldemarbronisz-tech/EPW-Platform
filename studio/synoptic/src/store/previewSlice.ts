// Panel preview: one screen full-window, drawn and framed as the panel
// draws it (no grid, no handles, the runtime frame or everything drawn
// fitted), and operable - a click on an apparatus is a COMMAND:
//   - with Studio's "Na żywo" on (liveValues present) it goes to the
//     controller (queued here, Studio drains the queue through
//     window.__synopticTakeCommands and POSTs /api/v1/commands), and the
//     symbol follows the controller's feedback like any live symbol;
//   - otherwise it operates the simulation (simulationSlice.operateAt),
//     exactly as the editor's own Podgląd does.
// Session state, never serialized, except mainScreenId - the screen the
// panel opens with (SPEC "Widok główny"), which is project data.

import type { StateCreator } from 'zustand';
import type { AppState } from './appState';
import { deviceAsserted } from './liveSlice';

export interface PanelPreviewState {
  /** The screen on show. */
  screenId: string;
  /** The screen that was being edited, to return to on exit. */
  returnScreenId: string;
  /** The editor's own preview mode before entering, to put back. */
  wasPreviewMode: boolean;
}

export interface QueuedCommand {
  deviceId: string;
  action: 'CLOSE' | 'OPEN';
}

export type PreviewSlice = Pick<AppState,
  | 'panelPreview' | 'mainScreenId' | 'pendingCommands' | 'helpRequest'
  | 'enterPanelPreview' | 'exitPanelPreview' | 'setMainScreen' | 'commandAt' | 'takeCommands' | 'requestStudioHelp'
>;

export const createPreviewSlice: StateCreator<AppState, [], [], PreviewSlice> = (set, get) => ({
  panelPreview: null,
  mainScreenId: null,
  pendingCommands: [],
  helpRequest: { topicId: '', nonce: 0 },

  // Inside Studio (window.__EPW_STUDIO_EMBED__) F1 and Help do not open
  // this editor's own window: Studio's one help shows the topic, in
  // Studio's language. Studio reads this through __synopticStudioState.
  requestStudioHelp: (topicId) => set((state) => ({
    helpRequest: { topicId, nonce: state.helpRequest.nonce + 1 },
  })),

  enterPanelPreview: (screenId) => {
    const s = get();
    const known = (id: string | null | undefined) => !!id && s.screens.some(x => x.id === id);
    const target = known(screenId) ? screenId! : known(s.mainScreenId) ? s.mainScreenId! : s.activeScreenId;
    const already = s.panelPreview;
    if (target !== s.activeScreenId) s.switchScreen(target);
    set({
      panelPreview: already
        ? { ...already, screenId: target }
        : { screenId: target, returnScreenId: s.activeScreenId, wasPreviewMode: s.previewMode },
    });
    get().setPreviewMode(true);
  },

  exitPanelPreview: () => {
    const preview = get().panelPreview;
    if (!preview) return;
    set({ panelPreview: null, pendingCommands: [] });
    get().setPreviewMode(preview.wasPreviewMode);
    const s = get();
    if (preview.returnScreenId !== s.activeScreenId && s.screens.some(x => x.id === preview.returnScreenId)) {
      s.switchScreen(preview.returnScreenId);
    }
  },

  setMainScreen: (screenId) => set((state) => ({
    mainScreenId: screenId && state.screens.some(x => x.id === screenId) ? screenId : null,
    isDirty: true,
  })),

  commandAt: (objectId) => {
    const s = get();
    const obj = s.objects.find(o => o.id === objectId);
    const device = obj?.deviceId ? s.devices.find(d => d.id === obj.deviceId) : undefined;
    if (!device || device.behavior !== 'SWITCHED') return null;
    // The opposite of what the controller reports; an unreadable feedback
    // (no live value yet) is treated as open, so the first click closes.
    const asserted = deviceAsserted(device, s.liveValues || {});
    const command: QueuedCommand = { deviceId: device.id, action: asserted ? 'OPEN' : 'CLOSE' };
    set({ pendingCommands: [...s.pendingCommands, command] });
    return command;
  },

  takeCommands: () => {
    const queued = get().pendingCommands;
    if (queued.length) set({ pendingCommands: [] });
    return queued;
  },
});
