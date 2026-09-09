import type { StateCreator } from 'zustand';
import type { LocationEntry, CardEntry } from '../project/DeviceSchema';
import type { AppState } from './appState';

// The device registry's other two lists (DeviceSchema.ts's own
// DeviceRegistry shape: locations, cards, devices) plus every CRUD
// action over all three. `devices` itself is still INITIALIZED in
// projectSlice.ts (it predates this slice, from the meter-element task)
// - its own array lives there, this slice's actions simply read/write
// it through the same `set`/`get` every slice shares against the whole
// AppState, exactly like historySlice.ts already reaches into fields
// elementsSlice.ts initializes.
//
// None of locations/cards/devices participate in undo/redo - the same,
// already-established treatment `devices` itself has had since it was
// first added: a project-wide registry, not drawing content, the same
// category as projectMetadata/canvasConfig.
export type DeviceRegistrySlice = Pick<AppState,
  | 'locations' | 'cards'
  | 'addLocation' | 'updateLocation' | 'deleteLocation'
  | 'addCard' | 'updateCard' | 'deleteCard'
  | 'addDevice' | 'updateDevice' | 'deleteDevice'
>;

export const createDeviceRegistrySlice: StateCreator<AppState, [], [], DeviceRegistrySlice> = (set) => ({
  locations: [] as LocationEntry[],
  cards: [] as CardEntry[],

  addLocation: (entry) => set((state) => ({ locations: [...state.locations, entry], isDirty: true })),
  updateLocation: (code, entry) => set((state) => ({
    locations: state.locations.map(l => l.code === code ? entry : l),
    isDirty: true
  })),
  deleteLocation: (code) => set((state) => ({
    locations: state.locations.filter(l => l.code !== code),
    isDirty: true
  })),

  addCard: (entry) => set((state) => ({ cards: [...state.cards, entry], isDirty: true })),
  updateCard: (id, entry) => set((state) => ({
    cards: state.cards.map(c => c.id === id ? entry : c),
    isDirty: true
  })),
  deleteCard: (id) => set((state) => ({
    cards: state.cards.filter(c => c.id !== id),
    isDirty: true
  })),

  addDevice: (device) => set((state) => ({ devices: [...state.devices, device], isDirty: true })),
  updateDevice: (id, device) => set((state) => ({
    devices: state.devices.map(d => d.id === id ? device : d),
    isDirty: true
  })),
  deleteDevice: (id) => set((state) => ({
    devices: state.devices.filter(d => d.id !== id),
    isDirty: true
  })),
});
