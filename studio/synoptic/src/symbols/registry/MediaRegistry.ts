export type MediaDomain = 'electrical' | 'water' | 'hvac' | 'data' | 'control' | 'unknown';

export interface MediaDefinition {
  id: string;
  domain: MediaDomain;
  label: string;
  visualStyle: {
    strokeColor: string;
    strokeWidth: number;
    dash?: number[];
    flowColor?: string;
  };
}

export const MEDIA_REGISTRY: Record<string, MediaDefinition> = {
  'electrical_ac': {
    id: 'electrical_ac',
    domain: 'electrical',
    label: 'Electrical AC',
    visualStyle: { strokeColor: '#e74c3c', strokeWidth: 2, flowColor: '#f1c40f' }
  },
  'electrical_dc': {
    id: 'electrical_dc',
    domain: 'electrical',
    label: 'Electrical DC',
    visualStyle: { strokeColor: '#34495e', strokeWidth: 2, flowColor: '#f1c40f' }
  },
  'water': {
    id: 'water',
    domain: 'water',
    label: 'Water Process',
    visualStyle: { strokeColor: '#3498db', strokeWidth: 2, flowColor: '#2980b9' }
  },
  'hvac_air': {
    id: 'hvac_air',
    domain: 'hvac',
    label: 'HVAC Air',
    visualStyle: { strokeColor: '#bdc3c7', strokeWidth: 2, flowColor: '#ecf0f1' }
  },
  'rs485': {
    id: 'rs485',
    domain: 'data',
    label: 'RS485 Serial',
    visualStyle: { strokeColor: '#8e44ad', strokeWidth: 1, dash: [4, 4] }
  },
  'ethernet': {
    id: 'ethernet',
    domain: 'data',
    label: 'Ethernet',
    visualStyle: { strokeColor: '#9b59b6', strokeWidth: 1 }
  },
  'control_24vdc': {
    id: 'control_24vdc',
    domain: 'control',
    label: 'Control 24V DC',
    visualStyle: { strokeColor: '#f39c12', strokeWidth: 1 }
  }
};

export const getMediaDefinition = (id: string): MediaDefinition | undefined => MEDIA_REGISTRY[id];
