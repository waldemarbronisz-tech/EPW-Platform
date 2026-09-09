import type { SymbolDefinition } from '../SymbolRegistry';

export const graphicsSymbols: Record<string, SymbolDefinition> = {
  'graphics.rectangle': {
    type: 'graphics.rectangle',
    label: 'Rectangle',
    category: 'Graphics',
    defaultWidth: 100,
    defaultHeight: 100,
    allowedStates: [],
    defaultState: ''
  },
  'graphics.circle': {
    type: 'graphics.circle',
    label: 'Circle',
    category: 'Graphics',
    defaultWidth: 100,
    defaultHeight: 100,
    allowedStates: [],
    defaultState: ''
  },
  'graphics.text': {
    type: 'graphics.text',
    label: 'Text',
    category: 'Graphics',
    defaultWidth: 100,
    defaultHeight: 30,
    allowedStates: [],
    defaultState: ''
  }
};

// Object Library trim (part E): none of this category's symbols are in
// the kept 22 (the EKRAN group's "Opis tekstowy" is scada.label_frame,
// a different symbol) - hidden as a whole rather than repeating the
// flag per entry.
Object.values(graphicsSymbols).forEach(def => { def.hiddenFromLibrary = true; });
