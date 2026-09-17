// Stand-in for the editor's zustand store (src/store), for the handful
// of symbol components that read it: TextBoxSymbol asks whether it is
// being edited (never, here), the site water symbols read the device
// registry (empty here - a symbol's base geometry never depends on which
// devices exist). Both a hook call `useStore(selector)` and
// `useStore.getState()` are served from the same frozen snapshot.
const SNAPSHOT = {
  editingTextId: null,
  devices: [],
  objects: [],
  connections: [],
  meters: [],
  signalPanels: [],
  frames: [],
  walls: [],
  groupCommands: [],
  setpointPanels: [],
  language: 'en',
};
export function useStore(selector) {
  return typeof selector === 'function' ? selector(SNAPSHOT) : SNAPSHOT;
}
useStore.getState = () => SNAPSHOT;
useStore.setState = () => {};
useStore.subscribe = () => () => {};
export default useStore;
