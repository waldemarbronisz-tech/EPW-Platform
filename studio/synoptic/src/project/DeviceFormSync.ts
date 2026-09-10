// feat/device-form-from-canvas commit 1 - what happens to placed
// symbols when their bound device is saved through the shared device
// form (App.tsx's own onSave, driven by deviceFormSlice.ts). Pure,
// Konva-free (same convention as DeviceLookup.ts/DeviceBindingValidation.ts).
//
// A SynopticObject's own `designation` field is deliberately NOT a
// live read of its device's designation - it is a separate, directly
// user-editable label field, only ever auto-filled from the device's
// designation ONCE, when a device is first assigned to a symbol whose
// own designation is still empty (see PropertyInspector.tsx's own
// handleDeviceChange comment: "a device is never removed from the
// label once filled, and an already-set designation is never
// overwritten"). Saving a LATER change to the device's own designation
// through this form re-applies that exact same rule, not a new one:
// every symbol bound to this device whose own designation still
// EXACTLY MATCHES what the device's designation was before this save
// (never customized away from it) gets updated to the new value;
// anything the user typed in by hand that differs is left untouched,
// on every symbol, every time - the same "never overwrite a
// customization" guarantee, just checked again on every save instead
// of only the first one.

import type { Device } from './DeviceSchema';
import type { SynopticObject } from '../store/types';

/**
 * Every object-update the store's own updateObjects needs to apply
 * after a device's designation changed - empty when it did not change
 * at all, or when nothing currently matches the old value.
 */
export function syncObjectDesignationsAfterDeviceSave(
  objects: SynopticObject[],
  oldDesignation: string,
  savedDevice: Device
): { id: string; updates: Partial<SynopticObject> }[] {
  if (savedDevice.designation === oldDesignation) return [];
  return objects
    .filter(o => o.deviceId === savedDevice.id && o.designation === oldDesignation)
    .map(o => ({ id: o.id, updates: { designation: savedDevice.designation } }));
}

// feat/device-form-from-canvas commit 3d - the Messages confirmation
// after saving through this form: designation and name, exactly what
// the task asks for, never the device's own id/UUID (utils/ObjectDisplay.ts's
// own header comment states the same "never a raw id/UUID" rule for
// naming an object in a message; this is the same rule for a device).
export function formatDeviceSavedMessage(device: Pick<Device, 'designation' | 'name'>): string {
  return `[INFO] Saved device ${device.designation} (${device.name})`;
}

// fix/inline-device-creation commit 3c - PRZYPISZ ISTNIEJACY's own
// Messages confirmation, same "designation and name, never a raw id"
// rule as formatDeviceSavedMessage above, worded for an assignment
// rather than a save (nothing about the device itself changed).
export function formatDeviceAssignedMessage(device: Pick<Device, 'designation' | 'name'>): string {
  return `[INFO] Assigned device ${device.designation} (${device.name})`;
}

// fix/inline-device-creation commit 3c: the two store-mutation paths
// DeviceFormDialog's own "create or assign" mode ends in - pulled out of
// App.tsx's own onSave/creationContext.onAssignExisting callbacks (which
// would otherwise be untestable inline JSX closures, the same reasoning
// every other *Sync.ts function in this file already follows) so both
// are directly unit-testable against the real store, with no need to
// mount Canvas.tsx (this project has no jsdom canvas backend - see
// rotation-handle-removal.test.ts's own header for why).
//
// Takes only the slice of the store each one actually needs, typed
// structurally rather than importing the whole AppState (this file has
// never depended on store.ts/appState.ts, and importing either just for
// a parameter type would create the exact import cycle store.ts's own
// composition-root comment warns against).
export interface DeviceMutationStore {
  addDevice: (device: Device) => void;
  updateObject: (id: string, updates: { deviceId?: string }) => void;
  saveHistory: () => void;
  addMessage: (text: string) => void;
}

/**
 * UTWORZ NOWY's own save path: the device is created AND immediately
 * assigned to the originating symbol - one undo step (a single
 * saveHistory call after both mutations), one Messages confirmation.
 */
export function createAndAssignDevice(store: DeviceMutationStore, symbolId: string, savedDevice: Device): void {
  store.addDevice(savedDevice);
  store.updateObject(symbolId, { deviceId: savedDevice.id });
  store.saveHistory();
  store.addMessage(formatDeviceSavedMessage(savedDevice));
}

/**
 * PRZYPISZ ISTNIEJACY's own confirm path: nothing is created, only the
 * symbol's own deviceId is set - a missing device (deleted from the
 * registry between opening the list and confirming) is a no-op, not a
 * crash, the same "problem, not a crash" treatment every other dangling
 * reference in this project already gets.
 */
export function assignExistingDeviceById(store: DeviceMutationStore & { devices: Device[] }, symbolId: string, deviceId: string): void {
  const device = store.devices.find(d => d.id === deviceId);
  if (!device) return;
  store.updateObject(symbolId, { deviceId: device.id });
  store.saveHistory();
  store.addMessage(formatDeviceAssignedMessage(device));
}
