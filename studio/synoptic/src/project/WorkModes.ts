// feat/synoptic-modes: work modes - SYMBOLS, ROOMS, CONNECTIONS, ANNOTATIONS.
//
// The library is a catalogue of things you INSERT; drawing is a TOOL you
// work with. Before modes the two were mixed (the wall and wire tools sat
// between the valves in the library) and every click could land on
// anything: drawing a room round a boiler house picked up the valve under
// the cursor.
//
// A mode decides what a click can reach. Everything else stays on screen
// at full strength - you draw a room AROUND the devices, so you have to
// see them - it just does not take clicks, marquee selection or Ctrl+A.
//
// Pure: no store, no Konva. Canvas and the store ask this file.

import { tr } from '../i18n/tr';

export type WorkMode = 'SYMBOLS' | 'ROOMS' | 'CONNECTIONS' | 'ANNOTATIONS';

/** In switcher order - the order of the Ctrl+1..4 shortcuts. */
export const WORK_MODES: WorkMode[] = ['SYMBOLS', 'ROOMS', 'CONNECTIONS', 'ANNOTATIONS'];

export const DEFAULT_WORK_MODE: WorkMode = 'SYMBOLS';

/** Ctrl+1..4, in switcher order. Ctrl+0 and Ctrl+9 are the zoom keys beside them, and plain 1/2/3 already pick the wire medium. */
export const WORK_MODE_SHORTCUTS: Record<WorkMode, string> = {
  SYMBOLS: 'Ctrl+1',
  ROOMS: 'Ctrl+2',
  CONNECTIONS: 'Ctrl+3',
  ANNOTATIONS: 'Ctrl+4',
};

/** Every kind of element on a screen, as far as clicking is concerned. */
export type ElementKind =
  | 'symbol' | 'annotation'
  | 'wall' | 'frame'
  | 'connection'
  | 'meter' | 'signalPanel' | 'groupCommand' | 'setpointPanel';

/** Objects that are descriptions rather than installation: text, labels and plain shapes. */
const ANNOTATION_TYPES = new Set([
  'scada.text_box',
  'scada.label_frame',
  'graphics.text',
  'graphics.rectangle',
  'graphics.circle',
]);

export function isAnnotationType(type: string): boolean {
  return ANNOTATION_TYPES.has(type);
}

/** Which kind an object (an entry of `objects`) is. */
export function objectKind(type: string): 'symbol' | 'annotation' {
  return isAnnotationType(type) ? 'annotation' : 'symbol';
}

const MODE_KINDS: Record<WorkMode, ElementKind[]> = {
  // Meters, signal panels, command buttons and setpoint panels are
  // inserted from the library like symbols and bound to devices like
  // symbols - they belong with them.
  SYMBOLS: ['symbol', 'meter', 'signalPanel', 'groupCommand', 'setpointPanel'],
  // Walls, and the frames that outline a room or a building.
  ROOMS: ['wall', 'frame'],
  CONNECTIONS: ['connection'],
  ANNOTATIONS: ['annotation'],
};

/** Whether elements of `kind` take clicks and selection in `mode`. */
export function isKindActive(mode: WorkMode, kind: ElementKind): boolean {
  return MODE_KINDS[mode].includes(kind);
}

/** The mode in which elements of `kind` can be edited. */
export function modeForKind(kind: ElementKind): WorkMode {
  return WORK_MODES.find(mode => MODE_KINDS[mode].includes(kind)) ?? DEFAULT_WORK_MODE;
}

/** The mode a keyboard event switches to (Ctrl+1..4), or null. */
export function modeFromShortcut(event: { key: string; ctrlKey: boolean; metaKey?: boolean; altKey?: boolean; shiftKey?: boolean }): WorkMode | null {
  if (!(event.ctrlKey || event.metaKey) || event.altKey || event.shiftKey) return null;
  const index = ['1', '2', '3', '4'].indexOf(event.key);
  return index >= 0 ? WORK_MODES[index] : null;
}

export interface SelectionIds {
  objectIds: string[];
  connectionIds: string[];
  meterIds: string[];
  signalPanelIds: string[];
  frameIds: string[];
  groupCommandIds: string[];
  setpointPanelIds: string[];
  wallIds: string[];
}

/** `selection` with everything the mode cannot reach dropped - what a marquee, Ctrl+A or a mode switch may leave selected. */
export function restrictSelectionToMode(
  selection: SelectionIds,
  objects: { id: string; type: string }[],
  mode: WorkMode
): SelectionIds {
  const typeOf = new Map(objects.map(o => [o.id, o.type]));
  const keep = (kind: ElementKind, ids: string[]) => (isKindActive(mode, kind) ? ids : []);
  return {
    objectIds: selection.objectIds.filter(id => {
      const type = typeOf.get(id);
      return type !== undefined && isKindActive(mode, objectKind(type));
    }),
    connectionIds: keep('connection', selection.connectionIds),
    meterIds: keep('meter', selection.meterIds),
    signalPanelIds: keep('signalPanel', selection.signalPanelIds),
    frameIds: keep('frame', selection.frameIds),
    groupCommandIds: keep('groupCommand', selection.groupCommandIds),
    setpointPanelIds: keep('setpointPanel', selection.setpointPanelIds),
    wallIds: keep('wall', selection.wallIds),
  };
}

/** The drawing tools and the mode each one works in. Arming a tool switches to its mode. */
export const TOOL_MODE = {
  wire: 'CONNECTIONS',
  wall: 'ROOMS',
  room: 'ROOMS',
  frame: 'ROOMS',
  textBox: 'ANNOTATIONS',
} as const satisfies Record<string, WorkMode>;

/** The switcher button's tooltip: name, shortcut and what can be selected. */
export function workModeTitle(mode: WorkMode): string {
  return tr('mode.switch_title', {
    name: tr(`mode.${mode}`),
    shortcut: WORK_MODE_SHORTCUTS[mode],
    what: tr(`mode.what.${mode}`),
  });
}
