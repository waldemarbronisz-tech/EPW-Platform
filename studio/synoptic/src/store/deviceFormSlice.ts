import type { StateCreator } from 'zustand';
import type { AppState } from './appState';

// feat/device-form-from-canvas: openDeviceForm is THE shared function
// this whole task exists to build - every place an aparat is visible
// (a schematic symbol's own double-click, Properties' Aparat row, a
// meter/signal-panel row's double-click, a wizard row's double-click,
// and Lista aparatow's own Edytuj button) calls this and only this to
// open the device's configuration form. It never opens a form of its
// own - App.tsx renders the SAME DeviceFormDialog component Lista
// aparatow itself has always used, driven by nothing but the
// deviceFormRequest field this slice owns.
//
// The one check every caller gets for free, in this one place: a
// deviceId that does not resolve to a real device never opens an empty
// form - it reports a Messages warning naming the missing id and
// leaves deviceFormRequest untouched (still whatever it was before -
// null, if nothing else was already open).
export type DeviceFormSlice = Pick<AppState,
  | 'deviceFormRequest' | 'openDeviceForm' | 'closeDeviceForm'
  | 'deviceCreateOrAssignRequest' | 'openDeviceCreateOrAssignForm' | 'closeDeviceCreateOrAssignForm'
>;

export const createDeviceFormSlice: StateCreator<AppState, [], [], DeviceFormSlice> = (set, get) => ({
  deviceFormRequest: null,
  deviceCreateOrAssignRequest: null,

  openDeviceForm: (deviceId, sourceContext) => {
    const device = get().devices.find(d => d.id === deviceId);
    if (!device) {
      get().addMessage(`[WARNING] Nie znaleziono aparatu '${deviceId}' - nie mozna otworzyc formularza konfiguracji.`);
      return;
    }
    // Mutually exclusive with the create-or-assign request below - a
    // symbol is either bound to a real device (this path) or not (that
    // one), never both at once.
    set({ deviceFormRequest: { deviceId, sourceContext }, deviceCreateOrAssignRequest: null });
  },

  closeDeviceForm: () => set({ deviceFormRequest: null }),

  // fix/inline-device-creation commit 3: opened by ObjectNode.tsx's own
  // handleSymbolDblClick when the double-clicked symbol has no deviceId
  // yet - no existence check needed (symbolId is always the object that
  // was just clicked, not a possibly-stale reference).
  openDeviceCreateOrAssignForm: (symbolId, symbolType, sourceContext) => {
    set({ deviceCreateOrAssignRequest: { symbolId, symbolType, sourceContext }, deviceFormRequest: null });
  },

  closeDeviceCreateOrAssignForm: () => set({ deviceCreateOrAssignRequest: null }),
});
