import type { SymbolDefinition } from '../SymbolRegistry';

export const measurementsSymbols: Record<string, SymbolDefinition> = {
  'measurements.generic_display': {
    type: 'measurements.generic_display',
    label: 'Value Display',
    category: 'Measurements',
    defaultWidth: 100,
    defaultHeight: 50,
    allowedStates: ['NORMAL', 'FAULT'],
    defaultState: 'NORMAL'
  },
  'measurements.voltage_display': {
    type: 'measurements.voltage_display',
    label: 'Voltage',
    category: 'Measurements',
    defaultWidth: 100,
    defaultHeight: 50,
    allowedStates: ['NORMAL', 'FAULT'],
    defaultState: 'NORMAL'
  },
  'measurements.current_display': {
    type: 'measurements.current_display',
    label: 'Current',
    category: 'Measurements',
    defaultWidth: 100,
    defaultHeight: 50,
    allowedStates: ['NORMAL', 'FAULT'],
    defaultState: 'NORMAL'
  },
  'measurements.temperature_display': {
    type: 'measurements.temperature_display',
    label: 'Temperature',
    category: 'Measurements',
    defaultWidth: 100,
    defaultHeight: 50,
    allowedStates: ['NORMAL', 'FAULT'],
    defaultState: 'NORMAL'
  },

  // Generic primitives
};

// Object Library trim (part E): none of this category's symbols are in
// the kept 22 (the EKRAN group's "Miernik" is scada.meter, a different
// symbol) - hidden as a whole rather than repeating the flag per entry.
Object.values(measurementsSymbols).forEach(def => { def.hiddenFromLibrary = true; });
