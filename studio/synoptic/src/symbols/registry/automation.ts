import type { SymbolDefinition } from '../SymbolRegistry';

export const automationSymbols: Record<string, SymbolDefinition> = {
  'automation.plc': {
    type: 'automation.plc',
    label: 'PLC',
    category: 'Automation',
    defaultWidth: 120,
    defaultHeight: 80,
    allowedStates: ['OFF', 'RUNNING', 'FAULT'],
    defaultState: 'OFF'
  },
  'automation.remote_io': {
    type: 'automation.remote_io',
    label: 'Remote IO',
    category: 'Automation',
    defaultWidth: 80,
    defaultHeight: 80,
    allowedStates: ['OFF', 'RUNNING', 'FAULT'],
    defaultState: 'OFF'
  },
  'automation.ela_inputs': {
    type: 'automation.ela_inputs',
    label: 'ELA Inputs',
    category: 'Automation',
    defaultWidth: 60,
    defaultHeight: 80,
    allowedStates: ['NORMAL', 'FAULT'],
    defaultState: 'NORMAL',
    connectionPoints: [{id: 'ELEC', x: 0.5, y: 0, domain: 'electrical', direction: 'in'}, {id: 'DATA', x: 0.5, y: 1, domain: 'data', direction: 'out'}]
  },
  'automation.ada_outputs': {
    type: 'automation.ada_outputs',
    label: 'ADA Outputs',
    category: 'Automation',
    defaultWidth: 60,
    defaultHeight: 80,
    allowedStates: ['NORMAL', 'FAULT'],
    defaultState: 'NORMAL',
    connectionPoints: [{id: 'POWER', x: 0.2, y: 0, domain: 'electrical', direction: 'in'}, {id: 'RS485', x: 0.8, y: 0, domain: 'data', direction: 'bidirectional'}]
  },
  'automation.epw_core': {
    type: 'automation.epw_core',
    label: 'EPW CORE',
    category: 'Automation',
    defaultWidth: 100,
    defaultHeight: 80,
    allowedStates: ['OFF', 'RUNNING', 'FAULT'],
    defaultState: 'RUNNING',
    connectionPoints: [{id: 'POWER', x: 0.2, y: 0, domain: 'electrical', direction: 'in'}, {id: 'ETH', x: 0.8, y: 0, domain: 'data', direction: 'bidirectional'}]
  },
  'automation.epm': {
    type: 'automation.epm',
    label: 'EPM',
    category: 'Automation',
    defaultWidth: 60,
    defaultHeight: 80,
    allowedStates: ['OFF', 'RUNNING', 'FAULT'],
    defaultState: 'RUNNING'
  },
  'automation.psu_24v': {
    type: 'automation.psu_24v',
    label: '24V PSU',
    category: 'Automation',
    defaultWidth: 60,
    defaultHeight: 80,
    allowedStates: ['OFF', 'ON', 'FAULT'],
    defaultState: 'ON',
    connectionPoints: [{id: 'AC_IN', x: 0.5, y: 0, domain: 'electrical', direction: 'in'}, {id: 'DC_OUT', x: 0.5, y: 1, domain: 'electrical', direction: 'out'}]
  },

  // Measurements
};

// Object Library trim (node-based wiring task, part E): none of this
// category's symbols are in the kept 22 - hidden as a whole rather than
// repeating the flag on every entry above.
Object.values(automationSymbols).forEach(def => { def.hiddenFromLibrary = true; });
