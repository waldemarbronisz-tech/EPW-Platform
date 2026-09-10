import type { SymbolDefinition } from '../SymbolRegistry';

// Object Library trim (part E): Pump, Tank, Solenoid Valve, Ball Valve,
// Drain Valve and Drain stay visible; Valve and Gate Valve are hidden
// (redundant with Ball/Solenoid/Gate variants already covering the
// visible set). See electrical.ts's header comment for the terminals
// convention (part A2's GRID_SIZE-multiple dims, and commit 1's
// side-only terminals on an EVEN GRID_SIZE multiple).
export const waterSymbols: Record<string, SymbolDefinition> = {
  'water.valve': {
    type: 'water.valve',
    label: 'Valve',
    category: 'Water',
    defaultWidth: 50,
    defaultHeight: 40,
    allowedStates: ['CLOSED', 'OPENING', 'OPEN', 'CLOSING', 'FAULT'],
    defaultState: 'CLOSED',
    connectionPoints: [{id: 'IN', x: 0, y: 0.5, domain: 'water', direction: 'in'}, {id: 'OUT', x: 1, y: 0.5, domain: 'water', direction: 'out'}],
    hiddenFromLibrary: true
  },
  'water.pump': {
    type: 'water.pump',
    label: 'Pump',
    category: 'Water',
    defaultWidth: 64,
    defaultHeight: 64,
    allowedStates: ['OFF', 'RUNNING', 'FAULT'],
    defaultState: 'OFF',
    connectionPoints: [{id: 'IN', x: 0, y: 0.5, domain: 'water', direction: 'in'}, {id: 'OUT', x: 1, y: 0.5, domain: 'water', direction: 'out'}],
    terminals: [{ id: 'IN', side: 'LEFT', medium: 'WATER' }, { id: 'OUT', side: 'RIGHT', medium: 'WATER' }]
  },
  'water.tank': {
    type: 'water.tank',
    label: 'Tank',
    category: 'Water',
    defaultWidth: 96,
    defaultHeight: 128,
    allowedStates: ['NORMAL', 'LOW', 'HIGH', 'FAULT'],
    defaultState: 'NORMAL',
    connectionPoints: [{id: 'IN', x: 0, y: 0.5, domain: 'water', direction: 'in'}, {id: 'OUT', x: 1, y: 0.5, domain: 'water', direction: 'out'}],
    terminals: [{ id: 'IN', side: 'LEFT', medium: 'WATER' }, { id: 'OUT', side: 'RIGHT', medium: 'WATER' }]
  },
  'water.gate_valve': {
    type: 'water.gate_valve',
    label: 'Gate Valve',
    category: 'Water',
    defaultWidth: 50,
    defaultHeight: 40,
    allowedStates: ['CLOSED', 'OPENING', 'OPEN', 'CLOSING', 'FAULT'],
    defaultState: 'CLOSED',
    connectionPoints: [{id: 'IN', x: 0, y: 0.5, domain: 'water', direction: 'in'}, {id: 'OUT', x: 1, y: 0.5, domain: 'water', direction: 'out'}],
    hiddenFromLibrary: true
  },
  'water.ball_valve': {
    type: 'water.ball_valve',
    label: 'Ball Valve',
    category: 'Water',
    defaultWidth: 64,
    defaultHeight: 64,
    allowedStates: ['CLOSED', 'OPENING', 'OPEN', 'CLOSING', 'FAULT'],
    defaultState: 'CLOSED',
    connectionPoints: [{id: 'IN', x: 0, y: 0.5, domain: 'water', direction: 'in'}, {id: 'OUT', x: 1, y: 0.5, domain: 'water', direction: 'out'}],
    terminals: [{ id: 'IN', side: 'LEFT', medium: 'WATER' }, { id: 'OUT', side: 'RIGHT', medium: 'WATER' }]
  },
  'water.solenoid_valve': {
    type: 'water.solenoid_valve',
    label: 'Solenoid Valve',
    category: 'Water',
    defaultWidth: 64,
    defaultHeight: 64,
    allowedStates: ['CLOSED', 'OPENING', 'OPEN', 'CLOSING', 'FAULT'],
    defaultState: 'CLOSED',
    connectionPoints: [{id: 'IN', x: 0, y: 0.5, domain: 'water', direction: 'in'}, {id: 'OUT', x: 1, y: 0.5, domain: 'water', direction: 'out'}],
    terminals: [{ id: 'IN', side: 'LEFT', medium: 'WATER' }, { id: 'OUT', side: 'RIGHT', medium: 'WATER' }]
  },
  'water.drain_valve': {
    type: 'water.drain_valve',
    label: 'Drain Valve',
    category: 'Water',
    defaultWidth: 64,
    defaultHeight: 64,
    allowedStates: ['CLOSED', 'OPEN', 'FAULT'],
    defaultState: 'CLOSED',
    connectionPoints: [{id: 'IN', x: 0, y: 0.5, domain: 'water', direction: 'in'}, {id: 'OUT', x: 1, y: 0.5, domain: 'water', direction: 'out'}],
    terminals: [{ id: 'IN', side: 'LEFT', medium: 'WATER' }, { id: 'OUT', side: 'RIGHT', medium: 'WATER' }]
  },
  'water.drain': {
    type: 'water.drain',
    label: 'Drain',
    category: 'Water',
    defaultWidth: 64,
    defaultHeight: 32,
    allowedStates: ['NORMAL', 'FAULT'],
    defaultState: 'NORMAL',
    connectionPoints: [{id: 'IN', x: 0, y: 0.5, domain: 'water', direction: 'in'}, {id: 'OUT', x: 1, y: 0.5, domain: 'water', direction: 'out'}],
    terminals: [{ id: 'IN', side: 'LEFT', medium: 'WATER' }]
  },

  // fix/hydraulic-connections commit 7: fifteen objects relocated here
  // from registry/site.ts (TEREN) - four originally from feat/site-
  // objects-2d (rain tank, sewage plant, water manhole, garden
  // sprinkler), plus all twelve of feat/water-management's own new
  // objects (the tank included). Registry-entry move only, `type`
  // strings unchanged (see electrical.ts's own header comment on this
  // same commit for the full reasoning) - only `category` changes,
  // here to 'Water'. site.rainwater_tank2's own terminals reflect
  // fix/hydraulic-connections commit 6's rework (DOPLYW/ODPLYW, not
  // the older single WYLOT) - this move carries that shape forward
  // unchanged, it does not revert it.
  // fix/tank-language-and-media commit 3: the duplicate rainwater tank
  // - this was the OLDER of two identically-labeled tanks in the
  // library (the other being site.rainwater_tank2, which has a real
  // water-level display and a percent field this one never had).
  // hiddenFromLibrary, never deleted - RainTankSymbol.tsx stays in the
  // codebase (GRANICE), and any ALREADY-PLACED instance of this exact
  // type in an existing project still renders correctly
  // (getSymbolDefinition stays unfiltered) - only the Object Library's
  // own list (getSymbolsByCategory) no longer offers it for new
  // placement, the same retirement convention water.valve/
  // water.gate_valve above already use.
  'site.rain_tank': {
    type: 'site.rain_tank',
    label: 'Rainwater Tank',
    category: 'Water',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [{ id: 'KROCIEC', side: 'RIGHT', medium: 'WATER' }],
    hiddenFromLibrary: true
  },
  'site.sewage_plant': {
    type: 'site.sewage_plant',
    label: 'Sewage Treatment Plant',
    category: 'Water',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [
      { id: 'WLOT', side: 'LEFT', medium: 'WATER' },
      { id: 'WYLOT', side: 'RIGHT', medium: 'WATER' }
    ]
  },
  'site.water_manhole': {
    type: 'site.water_manhole',
    label: 'Water Connection Manhole',
    category: 'Water',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [{ id: 'PRZYLACZE', side: 'BOTTOM', medium: 'WATER' }]
  },
  'site.garden_sprinkler': {
    type: 'site.garden_sprinkler',
    label: 'Garden Watering Post',
    category: 'Water',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [{ id: 'WODA', side: 'BOTTOM', medium: 'WATER' }]
  },
  'site.rainwater_tank2': {
    type: 'site.rainwater_tank2',
    label: 'Rainwater Tank',
    category: 'Water',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['LOW', 'MEDIUM', 'HIGH'],
    defaultState: 'LOW',
    // fix/tank-language-and-media commit 2, point (a): ODPLYW moves
    // from the RIGHT edge to the BOTTOM edge - water drains
    // gravitationally from the shell's own floor, not sideways out of
    // its wall. DOPLYW is unaffected.
    terminals: [
      { id: 'DOPLYW', side: 'LEFT', medium: 'WATER' },
      { id: 'ODPLYW', side: 'BOTTOM', medium: 'WATER' }
    ]
  },
  'site.water_selector_valve_switched': {
    type: 'site.water_selector_valve_switched',
    label: 'Three-Way Switching Valve',
    category: 'Water',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['A', 'B'],
    defaultState: 'A',
    terminals: [
      { id: 'WLOT', side: 'LEFT', medium: 'WATER' },
      { id: 'WYLOT_A', side: 'RIGHT', medium: 'WATER' },
      { id: 'WYLOT_B', side: 'BOTTOM', medium: 'WATER' }
    ]
  },
  'site.water_selector_valve_3pos': {
    type: 'site.water_selector_valve_3pos',
    label: 'Three-Way Selector Valve',
    category: 'Water',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['A', 'CLOSED', 'B'],
    defaultState: 'CLOSED',
    terminals: [
      { id: 'WLOT', side: 'LEFT', medium: 'WATER' },
      { id: 'WYLOT_A', side: 'RIGHT', medium: 'WATER' },
      { id: 'WYLOT_B', side: 'BOTTOM', medium: 'WATER' }
    ]
  },
  'site.check_valve': {
    type: 'site.check_valve',
    label: 'Check Valve',
    category: 'Water',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [
      { id: 'WLOT', side: 'LEFT', medium: 'WATER' },
      { id: 'WYLOT', side: 'RIGHT', medium: 'WATER' }
    ]
  },
  'site.water_filter': {
    type: 'site.water_filter',
    label: 'Water Filter',
    category: 'Water',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [
      { id: 'WLOT', side: 'LEFT', medium: 'WATER' },
      { id: 'WYLOT', side: 'RIGHT', medium: 'WATER' }
    ]
  },
  'site.hydrofor': {
    type: 'site.hydrofor',
    label: 'Pressure Booster',
    category: 'Water',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [{ id: 'WYLOT', side: 'LEFT', medium: 'WATER' }]
  },
  'site.flow_meter': {
    type: 'site.flow_meter',
    label: 'Flow Meter',
    category: 'Water',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [
      { id: 'WLOT', side: 'LEFT', medium: 'WATER' },
      { id: 'WYLOT', side: 'RIGHT', medium: 'WATER' }
    ]
  },
  'site.water_meter': {
    type: 'site.water_meter',
    label: 'Water Meter',
    category: 'Water',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [
      { id: 'WLOT', side: 'LEFT', medium: 'WATER' },
      { id: 'WYLOT', side: 'RIGHT', medium: 'WATER' }
    ]
  },
  'site.pressure_switch': {
    type: 'site.pressure_switch',
    label: 'Pressure Switch',
    category: 'Water',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [
      { id: 'WLOT', side: 'LEFT', medium: 'WATER' },
      { id: 'WYLOT', side: 'RIGHT', medium: 'WATER' }
    ]
  },
  'site.sprinkler_head': {
    type: 'site.sprinkler_head',
    label: 'Sprinkler Head',
    category: 'Water',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [{ id: 'WODA', side: 'BOTTOM', medium: 'WATER' }]
  },
  'site.drip_line': {
    type: 'site.drip_line',
    label: 'Drip Line',
    category: 'Water',
    defaultWidth: 192,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [{ id: 'WLOT', side: 'LEFT', medium: 'WATER' }]
  },
};
