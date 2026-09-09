import type { SymbolDefinition } from '../SymbolRegistry';

// Both of this file's symbols stay visible in the Object Library (part
// E). feat/media-and-proportions part A2 brought their defaultWidth/
// defaultHeight to GRID_SIZE multiples (50, 40 were not). Part B: their
// single terminal's medium is VENTILATION now, not ELECTRICAL - a fan
// or heater's feed is a duct connecting into the ventilation network,
// not a wire (they had been wrongly typed as ELECTRICAL before this
// medium existed to describe them correctly).
export const hvacSymbols: Record<string, SymbolDefinition> = {
  'hvac.fan': {
    type: 'hvac.fan',
    label: 'Fan',
    category: 'HVAC',
    defaultWidth: 64,
    defaultHeight: 64,
    allowedStates: ['OFF', 'RUNNING', 'FAULT'],
    defaultState: 'OFF',
    terminals: [{ id: 'IN', side: 'TOP', medium: 'VENTILATION' }]
  },
  'hvac.heater': {
    type: 'hvac.heater',
    label: 'Heater',
    category: 'HVAC',
    defaultWidth: 96,
    defaultHeight: 64,
    allowedStates: ['OFF', 'HEATING', 'FAULT'],
    defaultState: 'OFF',
    terminals: [{ id: 'IN', side: 'TOP', medium: 'VENTILATION' }]
  },

  // Instrumentation (Sensors & Displays)
};
