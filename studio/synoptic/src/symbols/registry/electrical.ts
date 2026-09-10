import type { SymbolDefinition } from '../SymbolRegistry';

// Object Library trim (node-based wiring task, part E): only Circuit
// Breaker, Disconnect Switch, Motor, Indicator Lamp and Earth stay
// visible from this file's 15 symbols. The other 10 (plus the busbar,
// which is not a symbol at all any more - a bus is now a wire style)
// get hiddenFromLibrary: true - still fully defined, still render
// correctly for an already-placed instance, just not draggable from the
// Toolbox.
//
// feat/media-and-proportions part A2: defaultWidth/defaultHeight of the
// 5 kept symbols above are now GRID_SIZE (16) multiples (they were not
// before - e.g. 40, 30, 60). Each symbol's own artwork draws itself
// from obj.width/obj.height using fixed fractions (w/2, h*0.3, ...), so
// resizing the default changes the rendered proportions too.
// Hidden symbols below (contactor, transformer, ...) are untouched:
// they are not part of the 22 this task's A2 applies to.
//
// feat/editing-and-signal-panel commit 1: terminals no longer carry a
// raw x/y at all - just a side (TOP/BOTTOM/LEFT/RIGHT), resolved
// against the object's own current width/height by
// utils/Terminals.ts's getTerminalOffsetForSide, always landing dead
// center on that edge. This also tightened defaultWidth/defaultHeight
// further, from any GRID_SIZE multiple to an EVEN one (32/64/96/...,
// not 16 or 48) - w/2 and h/2 must themselves be grid-aligned for the
// terminal (always at exactly w/2 or h/2 now) to land on a grid node.
// circuit_breaker/disconnect_switch/earth move from 48 to 64; motor
// and indicator_lamp were already even multiples and are untouched.
export const electricalSymbols: Record<string, SymbolDefinition> = {
  'electrical.circuit_breaker': {
    type: 'electrical.circuit_breaker',
    label: 'Circuit Breaker',
    category: 'Electrical',
    defaultWidth: 64,
    defaultHeight: 64,
    allowedStates: ['OPEN', 'CLOSED', 'TRIPPED', 'FAULT'],
    defaultState: 'OPEN',
    connectionPoints: [{id: 'IN', x: 0.5, y: 0, domain: 'electrical', direction: 'passive'}, {id: 'OUT', x: 0.5, y: 1, domain: 'electrical', direction: 'passive'}],
    terminals: [{ id: 'IN', side: 'TOP', medium: 'ELECTRICAL' }, { id: 'OUT', side: 'BOTTOM', medium: 'ELECTRICAL' }]
  },
  'electrical.disconnect_switch': {
    type: 'electrical.disconnect_switch',
    label: 'Disconnect Switch',
    category: 'Electrical',
    defaultWidth: 64,
    defaultHeight: 64,
    allowedStates: ['OPEN', 'CLOSED', 'FAULT'],
    defaultState: 'OPEN',
    connectionPoints: [{id: 'IN', x: 0.5, y: 0, domain: 'electrical', direction: 'passive'}, {id: 'OUT', x: 0.5, y: 1, domain: 'electrical', direction: 'passive'}],
    terminals: [{ id: 'IN', side: 'TOP', medium: 'ELECTRICAL' }, { id: 'OUT', side: 'BOTTOM', medium: 'ELECTRICAL' }]
  },
  'electrical.contactor': {
    type: 'electrical.contactor',
    label: 'Contactor',
    category: 'Electrical',
    defaultWidth: 40,
    defaultHeight: 40,
    allowedStates: ['OFF', 'ON', 'FAULT'],
    defaultState: 'OFF',
    connectionPoints: [{id: 'IN', x: 0.5, y: 0, domain: 'electrical', direction: 'passive'}, {id: 'OUT', x: 0.5, y: 1, domain: 'electrical', direction: 'passive'}, {id: 'COIL', x: 0.8, y: 0.8, domain: 'electrical', direction: 'passive'}],
    hiddenFromLibrary: true
  },
  'electrical.transformer': {
    type: 'electrical.transformer',
    label: 'Transformer',
    category: 'Electrical',
    defaultWidth: 60,
    defaultHeight: 60,
    allowedStates: ['NORMAL', 'ENERGIZED', 'FAULT'],
    defaultState: 'NORMAL',
    connectionPoints: [{id: 'PRIMARY', x: 0.5, y: 0, domain: 'electrical', direction: 'passive'}, {id: 'SECONDARY', x: 0.5, y: 1, domain: 'electrical', direction: 'passive'}],
    hiddenFromLibrary: true
  },
  'electrical.relay': {
    type: 'electrical.relay',
    label: 'Relay',
    category: 'Electrical',
    defaultWidth: 40,
    defaultHeight: 40,
    allowedStates: ['OFF', 'ON', 'FAULT'],
    defaultState: 'OFF',
    connectionPoints: [{id: 'IN', x: 0.5, y: 0, domain: 'electrical', direction: 'passive'}, {id: 'OUT', x: 0.5, y: 1, domain: 'electrical', direction: 'passive'}, {id: 'COIL', x: 0.2, y: 0.8, domain: 'electrical', direction: 'passive'}],
    hiddenFromLibrary: true
  },
  'electrical.fuse': {
    type: 'electrical.fuse',
    label: 'Fuse',
    category: 'Electrical',
    defaultWidth: 20,
    defaultHeight: 40,
    allowedStates: ['NORMAL', 'BLOWN'],
    defaultState: 'NORMAL',
    connectionPoints: [{id: 'IN', x: 0.5, y: 0, domain: 'electrical', direction: 'passive'}, {id: 'OUT', x: 0.5, y: 1, domain: 'electrical', direction: 'passive'}],
    hiddenFromLibrary: true
  },
  'electrical.busbar': {
    type: 'electrical.busbar',
    label: 'Busbar',
    category: 'Electrical',
    defaultWidth: 200,
    defaultHeight: 10,
    allowedStates: ['DEENERGIZED', 'ENERGIZED', 'FAULT'],
    defaultState: 'DEENERGIZED',
    isLine: true,
    // A busbar is a wire style (SynopticConnection.style === 'BUS') now,
    // not a symbol - hidden regardless of the old supportsDynamicPorts
    // mechanism, which the node-based wiring model no longer uses.
    supportsDynamicPorts: true,
    hiddenFromLibrary: true
  },
  'electrical.indicator_lamp': {
    type: 'electrical.indicator_lamp',
    label: 'Indicator Lamp',
    category: 'Electrical',
    defaultWidth: 32,
    defaultHeight: 32,
    allowedStates: ['OFF', 'ON', 'BLINK', 'FAULT'],
    defaultState: 'OFF',
    connectionPoints: [{id: 'IN', x: 0.5, y: 0, domain: 'electrical', direction: 'passive'}],
    terminals: [{ id: 'IN', side: 'TOP', medium: 'ELECTRICAL' }]
  },
  'electrical.generator': {
    type: 'electrical.generator',
    label: 'Generator',
    category: 'Electrical',
    defaultWidth: 60,
    defaultHeight: 60,
    allowedStates: ['OFF', 'RUNNING', 'FAULT'],
    defaultState: 'OFF',
    connectionPoints: [{id: 'OUT', x: 0.5, y: 0, domain: 'electrical', direction: 'passive'}],
    hiddenFromLibrary: true
  },
  'electrical.grid_source': {
    type: 'electrical.grid_source',
    label: 'Grid Source',
    category: 'Electrical',
    defaultWidth: 60,
    defaultHeight: 60,
    allowedStates: ['ENERGIZED', 'DEENERGIZED', 'FAULT'],
    defaultState: 'ENERGIZED',
    connectionPoints: [{id: 'OUT', x: 0.5, y: 1, domain: 'electrical', direction: 'passive'}],
    hiddenFromLibrary: true
  },
  'electrical.motor': {
    type: 'electrical.motor',
    label: 'Motor',
    category: 'Electrical',
    defaultWidth: 64,
    defaultHeight: 64,
    allowedStates: ['OFF', 'RUNNING', 'FAULT'],
    defaultState: 'OFF',
    connectionPoints: [{id: 'IN', x: 0.5, y: 0, domain: 'electrical', direction: 'passive'}],
    terminals: [{ id: 'IN', side: 'TOP', medium: 'ELECTRICAL' }]
  },
  'electrical.generic_load': {
    type: 'electrical.generic_load',
    label: 'Generic Load',
    category: 'Electrical',
    defaultWidth: 40,
    defaultHeight: 40,
    allowedStates: ['OFF', 'ON', 'FAULT'],
    defaultState: 'OFF',
    connectionPoints: [{id: 'IN', x: 0.5, y: 0, domain: 'electrical', direction: 'passive'}],
    hiddenFromLibrary: true
  },
  'electrical.terminal': {
    type: 'electrical.terminal',
    label: 'Terminal',
    category: 'Electrical',
    defaultWidth: 20,
    defaultHeight: 20,
    allowedStates: ['NORMAL', 'FAULT'],
    defaultState: 'NORMAL',
    connectionPoints: [{id: 'IN', x: 0.5, y: 0, domain: 'electrical', direction: 'passive'}, {id: 'OUT', x: 0.5, y: 1, domain: 'electrical', direction: 'passive'}],
    hiddenFromLibrary: true
  },
  'electrical.rcd': {
    type: 'electrical.rcd',
    label: 'RCD / RCCB',
    category: 'Electrical',
    defaultWidth: 60,
    defaultHeight: 60,
    allowedStates: ['CLOSED', 'OPEN', 'TRIPPED', 'FAULT'],
    defaultState: 'CLOSED',
    connectionPoints: [{id: 'IN', x: 0.5, y: 0, domain: 'electrical', direction: 'passive'}, {id: 'OUT', x: 0.5, y: 1, domain: 'electrical', direction: 'passive'}],
    hiddenFromLibrary: true
  },
  'electrical.spd': {
    type: 'electrical.spd',
    label: 'SPD',
    category: 'Electrical',
    defaultWidth: 40,
    defaultHeight: 60,
    allowedStates: ['NORMAL', 'FAULT'],
    defaultState: 'NORMAL',
    connectionPoints: [{id: 'IN', x: 0.5, y: 0, domain: 'electrical', direction: 'passive'}, {id: 'GND', x: 0.5, y: 1, domain: 'electrical', direction: 'passive'}],
    hiddenFromLibrary: true
  },
  'electrical.cable_tray': {
    type: 'electrical.cable_tray',
    label: 'Cable Tray',
    category: 'Electrical',
    defaultWidth: 100,
    defaultHeight: 20,
    allowedStates: ['NORMAL'],
    defaultState: 'NORMAL',
    hiddenFromLibrary: true
  },
  'electrical.earth': {
    type: 'electrical.earth',
    label: 'Earth',
    category: 'Electrical',
    defaultWidth: 64,
    defaultHeight: 64,
    allowedStates: ['NORMAL', 'FAULT'],
    defaultState: 'NORMAL',
    connectionPoints: [{id: 'GND', x: 0.5, y: 0, domain: 'electrical', direction: 'passive'}],
    terminals: [{ id: 'GND', side: 'TOP', medium: 'ELECTRICAL' }]
  },
  // feat/selector-symbol-setpoint-alarm: the schematic symbol for a
  // SELECTOR device (DeviceSchema.ts) - a physical Hand-Off-Auto-style
  // rotary switch. LEFT/CENTER/RIGHT are generic preview positions
  // (SelectorSwitchSymbol.tsx's own header explains why, not the
  // specific position names configured on any one device); kept
  // visible in the Toolbox unlike most of this file's own hidden
  // symbols, since - like Indicator Lamp/Circuit Breaker/Disconnect
  // Switch above - it has no more specific dedicated toolbox entry
  // anywhere else to draw from.
  'electrical.selector_switch': {
    type: 'electrical.selector_switch',
    label: 'Selector Switch',
    category: 'Electrical',
    defaultWidth: 64,
    defaultHeight: 64,
    allowedStates: ['LEFT', 'CENTER', 'RIGHT', 'FAULT'],
    defaultState: 'CENTER',
    connectionPoints: [{id: 'IN', x: 0.5, y: 0, domain: 'electrical', direction: 'passive'}],
    terminals: [{ id: 'IN', side: 'TOP', medium: 'ELECTRICAL' }]
  },

  // fix/hydraulic-connections commit 7: seven site-lighting/alarm
  // objects, relocated here from registry/site.ts (TEREN) - grouped by
  // DOMAIN now (they are electrical fixtures, not site infrastructure),
  // not by when they were first registered. This is a registry-entry
  // move only, per this task's own explicit "NIE przepisywanie
  // komponentow" - every field is unchanged except `category`, and the
  // `type` string itself deliberately KEEPS its original 'site.*'
  // prefix (not renamed to 'electrical.*'): a saved project references
  // an object by this exact string (ProjectSchema.ts's own
  // getSymbolDefinition(obj.type) lookup), and SymbolRenderer.tsx's own
  // switch-case dispatches on it too - renaming it would silently break
  // both for zero functional gain, since nothing in this app ever infers
  // a symbol's category FROM its type string. Same reasoning applies
  // to every other file this commit moves an entry into.
  'site.lamp_post_double': {
    type: 'site.lamp_post_double',
    label: 'Lamp Post (Double)',
    category: 'Electrical',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [{ id: 'ZASILANIE', side: 'BOTTOM', medium: 'ELECTRICAL' }]
  },
  'site.lamp_post_single': {
    type: 'site.lamp_post_single',
    label: 'Lamp Post (Single)',
    category: 'Electrical',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [{ id: 'ZASILANIE', side: 'BOTTOM', medium: 'ELECTRICAL' }]
  },
  'site.halogen': {
    type: 'site.halogen',
    label: 'Halogen',
    category: 'Electrical',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [{ id: 'ZASILANIE', side: 'BOTTOM', medium: 'ELECTRICAL' }]
  },
  'site.garden_light': {
    type: 'site.garden_light',
    label: 'Garden Light Post',
    category: 'Electrical',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [{ id: 'ZASILANIE', side: 'BOTTOM', medium: 'ELECTRICAL' }]
  },
  'site.cable_junction': {
    type: 'site.cable_junction',
    label: 'Cable Junction',
    category: 'Electrical',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [{ id: 'ZASILANIE', side: 'BOTTOM', medium: 'ELECTRICAL' }]
  },
  'site.alarm_beacon': {
    type: 'site.alarm_beacon',
    label: 'Alarm Beacon',
    category: 'Electrical',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [{ id: 'ZASILANIE', side: 'BOTTOM', medium: 'ELECTRICAL' }]
  },
  'site.alarm_horn': {
    type: 'site.alarm_horn',
    label: 'Alarm Horn',
    category: 'Electrical',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [{ id: 'ZASILANIE', side: 'BOTTOM', medium: 'ELECTRICAL' }]
  },
};
