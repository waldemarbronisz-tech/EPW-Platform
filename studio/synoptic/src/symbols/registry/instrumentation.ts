import type { SymbolDefinition } from '../SymbolRegistry';

// All five of this file's symbols stay visible in the Object Library
// (part E, CZUJNIKI) - none had connectionPoints before (sensors were
// never wireable in the old port model at all); each gets one
// ELECTRICAL terminal (power/signal feed) now. feat/media-and-
// proportions part A2 brought defaultWidth/defaultHeight to GRID_SIZE
// multiples (30, 40, 20 were not); the terminal x recomputed at the
// same top-center fraction moved for pressure/level/leak sensor (24
// used to snap down to 16, the new width's 24 snaps up to 32) but
// landed back on its old coordinate for temperature/humidity sensor
// (16 is exact for the new 32-wide default).
export const instrumentationSymbols: Record<string, SymbolDefinition> = {
  'instrumentation.temperature_sensor': {
    type: 'instrumentation.temperature_sensor',
    label: 'Temp Sensor',
    category: 'Instrumentation',
    defaultWidth: 32,
    defaultHeight: 64,
    allowedStates: ['NORMAL', 'FAULT'],
    defaultState: 'NORMAL',
    terminals: [{ id: 'IN', side: 'TOP', medium: 'ELECTRICAL' }]
  },
  'instrumentation.pressure_sensor': {
    type: 'instrumentation.pressure_sensor',
    label: 'Pressure Sensor',
    category: 'Instrumentation',
    defaultWidth: 64,
    defaultHeight: 64,
    allowedStates: ['NORMAL', 'FAULT'],
    defaultState: 'NORMAL',
    terminals: [{ id: 'IN', side: 'TOP', medium: 'ELECTRICAL' }]
  },
  'instrumentation.level_sensor': {
    type: 'instrumentation.level_sensor',
    label: 'Level Sensor',
    category: 'Instrumentation',
    defaultWidth: 64,
    defaultHeight: 64,
    allowedStates: ['NORMAL', 'FAULT'],
    defaultState: 'NORMAL',
    terminals: [{ id: 'IN', side: 'TOP', medium: 'ELECTRICAL' }]
  },
  'instrumentation.humidity_sensor': {
    type: 'instrumentation.humidity_sensor',
    label: 'Humidity Sensor',
    category: 'Instrumentation',
    defaultWidth: 32,
    defaultHeight: 64,
    allowedStates: ['NORMAL', 'FAULT'],
    defaultState: 'NORMAL',
    terminals: [{ id: 'IN', side: 'TOP', medium: 'ELECTRICAL' }]
  },
  'instrumentation.leak_sensor': {
    type: 'instrumentation.leak_sensor',
    label: 'Leak Sensor',
    category: 'Instrumentation',
    defaultWidth: 64,
    defaultHeight: 32,
    allowedStates: ['NORMAL', 'ACTIVE', 'FAULT'],
    defaultState: 'NORMAL',
    terminals: [{ id: 'IN', side: 'TOP', medium: 'ELECTRICAL' }]
  },

  // fix/hydraulic-connections commit 7: relocated here from
  // registry/site.ts (TEREN) - a rain sensor is a domain-Instrumentation
  // object (it is a SIGNAL-behavior sensor, per feat/water-management's
  // own aparat table), not site infrastructure. Registry-entry move
  // only (see electrical.ts's own header comment on this same commit
  // for the full reasoning) - `type` unchanged, only `category`.
  'site.rain_sensor': {
    type: 'site.rain_sensor',
    label: 'Rain Sensor',
    category: 'Instrumentation',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [{ id: 'ZASILANIE', side: 'BOTTOM', medium: 'ELECTRICAL' }]
  },

  // Automation
};
