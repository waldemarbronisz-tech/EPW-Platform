// feat/live-view (SPEC "Studio - sterownik - połączenie na żywo": "żywe
// stany przy punktach podczas projektowania ekranu"): while Studio's
// "Na żywo" is on, it pushes the controller's tag values in here
// (StudioBridge.setLiveValuesFromStudio) and every device-bound symbol
// draws its LIVE state instead of its preview state - the plan shows
// the installation as it is, without leaving the editor.
//
// Session state, never serialized, never touching the objects: the
// preview states in the document stay what the designer set. Cleared
// (null) the moment live is switched off or the link drops.

import type { StateCreator } from 'zustand';
import type { AppState } from './appState';
import type { SynopticObject } from './types';
import type { Device } from '../project/DeviceSchema';
import { getSymbolDefinition } from '../symbols/SymbolRegistry';

/** The two-state pairs a symbol's allowed states may use; the first that fits decides how a live "asserted" reads. */
const STATE_PAIRS: [string, string][] = [
  ['ON', 'OFF'], ['CLOSED', 'OPEN'], ['LIVE', 'DEAD'], ['ACTIVE', 'INACTIVE'], ['RUNNING', 'STOPPED'],
  ['OPEN', 'CLOSED'],
];

/** Truthy the way a controller tag is: true/1/"1"/"true"/"on". */
export function tagAsserted(value: unknown): boolean | null {
  if (value === null || value === undefined) return null;
  if (typeof value === 'boolean') return value;
  if (typeof value === 'number') return value !== 0;
  if (typeof value === 'string') return ['1', 'true', 'on', 'yes'].includes(value.trim().toLowerCase());
  return null;
}

/**
 * The state a symbol shows for a live "asserted"/"not asserted" reading,
 * or null when its states have no two-state pair to map onto (a symbol
 * with only NORMAL, a meter...). Mirrors runtime's pick_state() closely
 * enough that the panel and the editor agree on what "on" looks like.
 */
export function liveStateFor(type: string, asserted: boolean): string | null {
  const def = getSymbolDefinition(type);
  const allowed = def?.allowedStates ?? [];
  for (const [on, off] of STATE_PAIRS) {
    if (allowed.includes(on) && allowed.includes(off)) return asserted ? on : off;
  }
  return null;
}

/**
 * Whether a device reads "asserted" (closed / on / signalled) from the
 * live values, or null when the values cannot say (a tag missing, a
 * DUAL feedback in disagreement, a behaviour with no two-state reading).
 *   SWITCHED  DUAL   - diClosed true and diOpen false (both true or both
 *                      false is a discrepancy: no answer);
 *             SINGLE - diClosed (inverted when `invert`);
 *             NONE   - the commanded output doClose (what the controller
 *                      is driving is the best the plan can show);
 *   SIGNAL           - its contact `feedback.di` (inverted when `invert`);
 *   SELECTOR, MEASURED, MODULATED - no two-state reading here.
 */
export function deviceAsserted(device: Device, values: Record<string, unknown>): boolean | null {
  const read = (tag: string | undefined) => (tag ? tagAsserted(values[tag]) : null);
  if (device.behavior === 'SWITCHED') {
    const feedback = device.feedback;
    if (feedback.mode === 'DUAL') {
      const closed = read(feedback.diClosed);
      const open = read(feedback.diOpen);
      if (closed === null || open === null || closed === open) return null;
      return closed;
    }
    if (feedback.mode === 'SINGLE') {
      const closed = read(feedback.diClosed);
      if (closed === null) return null;
      return feedback.invert ? !closed : closed;
    }
    return read(device.command.doClose);
  }
  if (device.behavior === 'SIGNAL') {
    const signalled = read(device.feedback.di);
    if (signalled === null) return null;
    return device.feedback.invert ? !signalled : signalled;
  }
  return null;
}

/**
 * {objectId: state} for every object the live values can say something
 * about: an object bound to a device reads the device (deviceAsserted),
 * an object with a plain `tag` reads that tag. Everything else is left
 * to its preview state.
 */
export function liveStatesFor(
  objects: SynopticObject[],
  devices: Device[],
  values: Record<string, unknown>
): Record<string, string> {
  const byId = new Map(devices.map(d => [d.id, d]));
  const out: Record<string, string> = {};
  for (const obj of objects) {
    const device = obj.deviceId ? byId.get(obj.deviceId) : undefined;
    const asserted = device ? deviceAsserted(device, values) : (obj.tag ? tagAsserted(values[obj.tag]) : null);
    if (asserted === null) continue;
    const state = liveStateFor(obj.type, asserted);
    if (state) out[obj.id] = state;
  }
  return out;
}

export type LiveSlice = Pick<AppState, 'liveValues' | 'liveStates' | 'setLiveValues'>;

export const createLiveSlice: StateCreator<AppState, [], [], LiveSlice> = (set, get) => ({
  liveValues: null,
  liveStates: {},

  setLiveValues: (values) => {
    if (!values) {
      set({ liveValues: null, liveStates: {} });
      return;
    }
    const { objects, devices } = get();
    set({ liveValues: values, liveStates: liveStatesFor(objects, devices, values) });
  },
});
