// Adapters between the editor's generic { obj, state } symbol contract
// (SymbolProps, from SymbolRenderer.tsx) and the nine SCADA-style symbols'
// own, purpose-built props (LoadSwitchSymbol({state}), BusbarSymbol({width,
// state}), MeterSymbol({width, title, rows}), ...). Kept separate from the
// symbol components themselves, which stay standalone and independently
// testable (scada-symbols.test.ts imports their pure logic directly, not
// through this file).

import React from 'react';
import type { SymbolProps } from '../SymbolRenderer';
import { LoadSwitchSymbol, LOAD_SWITCH_STATES } from './LoadSwitchSymbol';
import type { LoadSwitchState } from './LoadSwitchSymbol';
import { BusbarSymbol, BUSBAR_STATES } from './BusbarSymbol';
import type { BusbarState } from './BusbarSymbol';
import { WireNodeSymbol } from './WireNodeSymbol';
import { LabelFrameSymbol } from './LabelFrameSymbol';
import { MotorSymbol, MOTOR_STATES } from './MotorSymbol';
import type { MotorState } from './MotorSymbol';
import { PilotLampSymbol, PILOT_LAMP_STATES } from './PilotLampSymbol';
import type { PilotLampState } from './PilotLampSymbol';
import { SocketSymbol, SOCKET_STATES } from './SocketSymbol';
import type { SocketState } from './SocketSymbol';
import { IndicatorDiodeSymbol, INDICATOR_DIODE_STATES } from './IndicatorDiodeSymbol';
import type { IndicatorDiodeSize, IndicatorDiodeState } from './IndicatorDiodeSymbol';
import { MeterSymbol } from './MeterSymbol';
import type { MeterRow } from './MeterSymbol';
import { BoundaryPointSymbol } from './BoundaryPointSymbol';
import type { BoundaryDirection, BoundaryMedium, BoundaryPortSide } from './BoundaryPointSymbol';

/** Falls back to the definition's own default rather than an arbitrary state when a saved/loaded preview_state is stale or absent. */
function resolveState<T extends string>(state: string, allowed: readonly T[], fallback: T): T {
  return (allowed as readonly string[]).includes(state) ? (state as T) : fallback;
}

export const ScadaLoadSwitchAdapter: React.FC<SymbolProps> = ({ state }) => (
  <LoadSwitchSymbol state={resolveState<LoadSwitchState>(state, LOAD_SWITCH_STATES, 'OPEN')} />
);

export const ScadaBusbarAdapter: React.FC<SymbolProps> = ({ obj, state }) => (
  <BusbarSymbol width={obj.width} state={resolveState<BusbarState>(state, BUSBAR_STATES, 'DEAD')} />
);

export const ScadaWireNodeAdapter: React.FC<SymbolProps> = () => <WireNodeSymbol />;

export const ScadaLabelFrameAdapter: React.FC<SymbolProps> = ({ obj }) => (
  <LabelFrameSymbol title={obj.designation || obj.name || 'LABEL'} description={obj.description || obj.text || ''} />
);

export const ScadaMotorAdapter: React.FC<SymbolProps> = ({ state }) => (
  <MotorSymbol state={resolveState<MotorState>(state, MOTOR_STATES, 'STOP')} />
);

export const ScadaPilotLampAdapter: React.FC<SymbolProps> = ({ state }) => (
  <PilotLampSymbol state={resolveState<PilotLampState>(state, PILOT_LAMP_STATES, 'OFF')} />
);

export const ScadaSocketAdapter: React.FC<SymbolProps> = ({ state }) => (
  <SocketSymbol state={resolveState<SocketState>(state, SOCKET_STATES, 'DEAD')} />
);

export const ScadaIndicatorDiodeAdapter: React.FC<SymbolProps> = ({ obj, state }) => {
  const size: IndicatorDiodeSize = obj.customProperties?.size === 'large' ? 'large' : 'small';
  return <IndicatorDiodeSymbol state={resolveState<IndicatorDiodeState>(state, INDICATOR_DIODE_STATES, 'OFF')} size={size} />;
};

export const ScadaMeterAdapter: React.FC<SymbolProps> = ({ obj }) => {
  const rows: MeterRow[] = obj.meterRows || [];
  return <MeterSymbol width={obj.width} title={obj.designation || obj.name || undefined} rows={rows} />;
};

export const ScadaBoundaryPointAdapter: React.FC<SymbolProps> = ({ obj }) => {
  const direction: BoundaryDirection = obj.boundaryDirection === 'SINK' ? 'SINK' : 'SOURCE';
  const medium: BoundaryMedium =
    obj.boundaryMedium === 'WATER' ? 'WATER' :
    obj.boundaryMedium === 'VENTILATION' ? 'VENTILATION' : 'ELECTRICAL';
  const portSide: BoundaryPortSide =
    obj.boundaryPortSide === 'BOTTOM' || obj.boundaryPortSide === 'LEFT' || obj.boundaryPortSide === 'RIGHT'
      ? obj.boundaryPortSide
      : 'TOP';
  return (
    <BoundaryPointSymbol
      label={obj.designation || obj.name || 'LABEL'}
      sublabel={obj.description || obj.text || ''}
      direction={direction}
      medium={medium}
      portSide={portSide}
    />
  );
};
