import React from 'react';
import { Group, Rect, Circle, Text } from 'react-konva';
import { useStore } from '../store';
import type { SynopticObject } from '../store';
import { FONT_UI, FONT_SIZE_BASE } from '../theme/ScadaTheme';
import { getSymbolDefinition } from './SymbolRegistry';
import { getTerminalNetStates } from '../project/NetResolver';
import { CircuitBreakerSymbol } from './electrical/CircuitBreakerSymbol';
import { DisconnectSwitchSymbol } from './electrical/DisconnectSwitchSymbol';
import { ContactorSymbol } from './electrical/ContactorSymbol';
import { TransformerSymbol } from './electrical/TransformerSymbol';
import { BusbarSymbol } from './electrical/BusbarSymbol';
import { IndicatorLampSymbol } from './electrical/IndicatorLampSymbol';
import { GeneratorSymbol } from './electrical/GeneratorSymbol';
import { FuseSymbol } from './electrical/FuseSymbol';
import { RelaySymbol } from './electrical/RelaySymbol';
import { MotorSymbol } from './electrical/MotorSymbol';
import { TerminalSymbol } from './electrical/TerminalSymbol';
import { CableSymbol } from './electrical/CableSymbol';
import { CableTraySymbol } from './electrical/CableTraySymbol';
import { EarthSymbol } from './electrical/EarthSymbol';
import { ACWireSymbol } from './electrical/ACWireSymbol';
import { ThreePhaseLineSymbol } from './electrical/ThreePhaseLineSymbol';
import { GridSourceSymbol } from './electrical/GridSourceSymbol';
import { RCDSymbol } from './electrical/RCDSymbol';
import { SPDSymbol } from './electrical/SPDSymbol';
import { GenericLoadSymbol } from './electrical/GenericLoadSymbol';
import { SelectorSwitchSymbol } from './electrical/SelectorSwitchSymbol';
import { PipeSymbol } from './water/PipeSymbol';
import { PipeElbowSymbol } from './water/PipeElbowSymbol';
import { TeeSymbol } from './water/TeeSymbol';
import { ValveSymbol } from './water/ValveSymbol';
import { GateValveSymbol } from './water/GateValveSymbol';
import { BallValveSymbol } from './water/BallValveSymbol';
import { DrainSymbol } from './water/DrainSymbol';
import { SolenoidValveSymbol } from './water/SolenoidValveSymbol';
import { DrainValveSymbol } from './water/DrainValveSymbol';
import { PumpSymbol } from './water/PumpSymbol';
import { TankSymbol } from './water/TankSymbol';
import { MeasurementDisplaySymbol } from './measurements/MeasurementDisplaySymbol';
import { VoltageDisplaySymbol, CurrentDisplaySymbol, TemperatureDisplaySymbol } from './measurements/SpecificDisplaySymbols';
import { FanSymbol } from './hvac/FanSymbol';
import { HeaterSymbol } from './hvac/HeaterSymbol';
import { TemperatureSensorSymbol } from './instrumentation/TemperatureSensorSymbol';
import { PressureSensorSymbol } from './instrumentation/PressureSensorSymbol';
import { LevelSensorSymbol } from './instrumentation/LevelSensorSymbol';
import { HumiditySensorSymbol } from './instrumentation/HumiditySensorSymbol';
import { LeakSensorSymbol } from './instrumentation/LeakSensorSymbol';
import { PLCSymbol } from './automation/PLCSymbol';
import { RemoteIOSymbol } from './automation/RemoteIOSymbol';
import { ELAInputsSymbol } from './automation/ELAInputsSymbol';
import { ADAOutputsSymbol } from './automation/ADAOutputsSymbol';
import { EPWCoreSymbol } from './automation/EPWCoreSymbol';
import { EPMSymbol } from './automation/EPMSymbol';
import { PSU24VSymbol } from './automation/PSU24VSymbol';
import {
  ScadaLoadSwitchAdapter,
  ScadaBusbarAdapter,
  ScadaWireNodeAdapter,
  ScadaLabelFrameAdapter,
  ScadaMotorAdapter,
  ScadaPilotLampAdapter,
  ScadaSocketAdapter,
  ScadaIndicatorDiodeAdapter,
  ScadaMeterAdapter,
  ScadaBoundaryPointAdapter
} from './scada/ScadaSymbolAdapters';
import { HouseSymbol } from './site/HouseSymbol';
import { WarehouseSymbol } from './site/WarehouseSymbol';
import { SlidingGateSymbol } from './site/SlidingGateSymbol';
import { RainTankSymbol } from './site/RainTankSymbol';
import { SewagePlantSymbol } from './site/SewagePlantSymbol';
import { WaterManholeSymbol } from './site/WaterManholeSymbol';
import { LampPostDoubleSymbol, LampPostSingleSymbol } from './site/LampPostSymbol';
import { HalogenSymbol } from './site/HalogenSymbol';
import { GardenLightSymbol } from './site/GardenLightSymbol';
import { CableJunctionSymbol } from './site/CableJunctionSymbol';
import { AlarmBeaconSymbol } from './site/AlarmBeaconSymbol';
import { AlarmHornSymbol } from './site/AlarmHornSymbol';
import { GardenSprinklerSymbol } from './site/GardenSprinklerSymbol';
import { GrassSymbol } from './site/GrassSymbol';
import { ConcreteRoadSymbol } from './site/ConcreteRoadSymbol';
import { RainwaterTank2Symbol } from './site/RainwaterTank2Symbol';
import { WaterValveSymbol } from './site/WaterValveSymbol';
import { WaterSelectorValveSymbol } from './site/WaterSelectorValveSymbol';
import { CheckValveSymbol } from './site/CheckValveSymbol';
import { WaterFilterSymbol } from './site/WaterFilterSymbol';
import { HydroforSymbol } from './site/HydroforSymbol';
import { FlowMeterSymbol } from './site/FlowMeterSymbol';
import { WaterMeterSymbol } from './site/WaterMeterSymbol';
import { PressureSwitchSymbol } from './site/PressureSwitchSymbol';
import { RainSensorSymbol } from './site/RainSensorSymbol';
import { SprinklerHeadSymbol } from './site/SprinklerHeadSymbol';
import { DripLineSymbol } from './site/DripLineSymbol';

export interface SymbolProps {
  obj: SynopticObject;
  state: string; // the resolved state (either preview_state or fallback default)
  // feat/wire-routing-around-obstacles commit 5: a water-medium
  // aparat's own krociec no longer carries a color of its own - this
  // resolves ONE of its own terminal ids to the state of the NET that
  // terminal currently belongs to (ACTIVE/INACTIVE), or 'INACTIVE' for
  // a terminal that is not on any net at all (unconnected - point c).
  // Only ever passed to a component whose registered symbol actually
  // has a WATER terminal (SymbolRenderer.tsx's own dispatch below) -
  // every other component simply never receives it, same as any other
  // optional prop.
  terminalNetState?: (terminalId: string) => 'ACTIVE' | 'INACTIVE';
}

// feat/appearance-selection-frames commit 4c: PropertyInspector.tsx's
// own "Text" field only makes sense to show for a type whose renderer
// actually reads obj.text somewhere - every other type's own dedicated
// component (the switch below) never looks at it at all, so editing it
// there did nothing but leave a stale, misleading value ("Meter
// (SCADA)", "Indicator Lamp" - literally def.label from the moment it
// was dropped, per Canvas.tsx's own handleDrop) sitting in the field.
// Kept in sync with the switch by construction: graphics.* is exactly
// the one prefix with no dedicated case at all (falls to GenericSymbol,
// which reads obj.text || obj.type directly) - confirmed against every
// registry file, not assumed. The other three are dedicated components
// that still read obj.text as their own fallback when a more specific
// field (description/tag) is empty.
// oxlint-disable-next-line react/only-export-components -- kept beside the component/switch it describes, for the same reason GenericSymbol itself lives here.
export function symbolUsesTextField(type: string): boolean {
  if (type.startsWith('graphics.')) return true;
  if (type.startsWith('measurements.')) return true;
  return type === 'scada.label_frame' || type === 'scada.boundary_point';
}

export const GenericSymbol: React.FC<SymbolProps> = ({ obj }) => {
  const isCircle = obj.type === 'graphics.circle' || (!obj.type.startsWith('graphics.') && (obj.type.includes('pump') || obj.type.includes('valve') || obj.type.includes('meter')));

  return (
    <Group>
      {isCircle ? (
        <Circle
          x={obj.width / 2}
          y={obj.height / 2}
          radius={obj.width / 2}
          fill={obj.fill || '#c0c0c0'}
          stroke={obj.border || '#000000'}
          strokeWidth={1}
        />
      ) : (
        <Rect
          width={obj.width}
          height={obj.height}
          fill={obj.fill || '#c0c0c0'}
          stroke={obj.border || '#000000'}
          strokeWidth={1}
        />
      )}
      <Text
        text={obj.text || obj.type}
        width={obj.width}
        height={obj.height}
        align="center"
        verticalAlign="middle"
        fontSize={obj.fontSize || FONT_SIZE_BASE}
        fontFamily={obj.font || FONT_UI}
        fill="#000"
      />
    </Group>
  );
};

export const SymbolRenderer: React.FC<{ obj: SynopticObject }> = ({ obj }) => {
  const state = obj.editor?.preview_state || 'NORMAL';

  // feat/wire-routing-around-obstacles commit 5, point (a): "uzyj TEJ
  // SAMEJ funkcji, ktora wyznacza stan sieci dla przewodow" -
  // getTerminalNetStates is a thin wrapper around NetResolver.ts's own
  // resolveNets, never a second mechanism. Computed only for an object
  // whose registered symbol actually has a WATER terminal (most
  // objects on a screen do not) - a plain useStore.getState() snapshot
  // read, not a subscribing hook: this component already re-renders on
  // every store change anyway (Canvas.tsx's own top-level subscription
  // re-renders its whole objects/connections list), so a second
  // subscription here would add reactivity this already has, not gain any.
  const def = getSymbolDefinition(obj.type);
  const hasWaterTerminal = (def?.terminals || []).some(t => t.medium === 'WATER');
  let terminalNetState: ((terminalId: string) => 'ACTIVE' | 'INACTIVE') | undefined;
  if (hasWaterTerminal) {
    const { connections, objects, devices } = useStore.getState();
    const netStates = getTerminalNetStates(connections, objects, devices);
    terminalNetState = (terminalId: string) => netStates.get(`${obj.id}:${terminalId}`) ?? 'INACTIVE';
  }

  switch (obj.type) {
    case 'electrical.circuit_breaker':
      return <CircuitBreakerSymbol obj={obj} state={state} />;
    case 'electrical.disconnect_switch':
      return <DisconnectSwitchSymbol obj={obj} state={state} />;
    case 'electrical.contactor':
      return <ContactorSymbol obj={obj} state={state} />;
    case 'electrical.transformer':
      return <TransformerSymbol obj={obj} state={state} />;
    case 'electrical.busbar':
      return <BusbarSymbol obj={obj} state={state} />;
    case 'electrical.indicator_lamp':
      return <IndicatorLampSymbol obj={obj} state={state} />;
    case 'electrical.generator':
      return <GeneratorSymbol obj={obj} state={state} />;
    case 'electrical.grid_source':
      return <GridSourceSymbol obj={obj} state={state} />;
    case 'electrical.fuse':
      return <FuseSymbol obj={obj} state={state} />;
    case 'electrical.rcd':
      return <RCDSymbol obj={obj} state={state} />;
    case 'electrical.spd':
      return <SPDSymbol obj={obj} state={state} />;
    case 'electrical.generic_load':
      return <GenericLoadSymbol obj={obj} state={state} />;
    case 'electrical.relay':
      return <RelaySymbol obj={obj} state={state} />;
    case 'electrical.motor':
      return <MotorSymbol obj={obj} state={state} />;
    case 'electrical.terminal':
      return <TerminalSymbol obj={obj} state={state} />;
    case 'electrical.cable':
      return <CableSymbol obj={obj} state={state} />;
    case 'electrical.ac_wire':
      return <ACWireSymbol obj={obj} state={state} />;
    case 'electrical.three_phase_line':
      return <ThreePhaseLineSymbol obj={obj} state={state} />;
    case 'electrical.cable_tray':
      return <CableTraySymbol obj={obj} state={state} />;
    case 'electrical.earth':
      return <EarthSymbol obj={obj} state={state} />;
    case 'electrical.selector_switch':
      return <SelectorSwitchSymbol obj={obj} state={state} />;
    case 'water.pipe':
      return <PipeSymbol obj={obj} state={state} />;
    case 'water.pipe_elbow':
      return <PipeElbowSymbol obj={obj} state={state} />;
    case 'water.tee':
      return <TeeSymbol obj={obj} state={state} />;
    case 'water.valve':
      return <ValveSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'water.gate_valve':
      return <GateValveSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'water.ball_valve':
      return <BallValveSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'water.drain':
      return <DrainSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'water.solenoid_valve':
      return <SolenoidValveSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'water.drain_valve':
      return <DrainValveSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'water.pump':
      return <PumpSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'water.tank':
      return <TankSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'measurements.generic_display':
      return <MeasurementDisplaySymbol obj={obj} state={state} />;
    case 'measurements.voltage_display':
      return <VoltageDisplaySymbol obj={obj} state={state} />;
    case 'measurements.current_display':
      return <CurrentDisplaySymbol obj={obj} state={state} />;
    case 'measurements.temperature_display':
      return <TemperatureDisplaySymbol obj={obj} state={state} />;
    case 'hvac.fan':
      return <FanSymbol obj={obj} state={state} />;
    case 'hvac.heater':
      return <HeaterSymbol obj={obj} state={state} />;
    case 'instrumentation.temperature_sensor':
      return <TemperatureSensorSymbol obj={obj} state={state} />;
    case 'instrumentation.pressure_sensor':
      return <PressureSensorSymbol obj={obj} state={state} />;
    case 'instrumentation.level_sensor':
      return <LevelSensorSymbol obj={obj} state={state} />;
    case 'instrumentation.humidity_sensor':
      return <HumiditySensorSymbol obj={obj} state={state} />;
    case 'instrumentation.leak_sensor':
      return <LeakSensorSymbol obj={obj} state={state} />;
    case 'automation.plc':
      return <PLCSymbol obj={obj} state={state} />;
    case 'automation.remote_io':
      return <RemoteIOSymbol obj={obj} state={state} />;
    case 'automation.ela_inputs':
      return <ELAInputsSymbol obj={obj} state={state} />;
    case 'automation.ada_outputs':
      return <ADAOutputsSymbol obj={obj} state={state} />;
    case 'automation.epw_core':
      return <EPWCoreSymbol obj={obj} state={state} />;
    case 'automation.epm':
      return <EPMSymbol obj={obj} state={state} />;
    case 'automation.psu_24v':
      return <PSU24VSymbol obj={obj} state={state} />;
    case 'scada.load_switch':
      return <ScadaLoadSwitchAdapter obj={obj} state={state} />;
    case 'scada.busbar':
      return <ScadaBusbarAdapter obj={obj} state={state} />;
    case 'scada.wire_node':
      return <ScadaWireNodeAdapter obj={obj} state={state} />;
    case 'scada.label_frame':
      return <ScadaLabelFrameAdapter obj={obj} state={state} />;
    case 'scada.motor':
      return <ScadaMotorAdapter obj={obj} state={state} />;
    case 'scada.pilot_lamp':
      return <ScadaPilotLampAdapter obj={obj} state={state} />;
    case 'scada.socket':
      return <ScadaSocketAdapter obj={obj} state={state} />;
    case 'scada.indicator_diode':
      return <ScadaIndicatorDiodeAdapter obj={obj} state={state} />;
    case 'scada.meter':
      return <ScadaMeterAdapter obj={obj} state={state} />;
    case 'scada.boundary_point':
      return <ScadaBoundaryPointAdapter obj={obj} state={state} />;
    case 'site.house':
      return <HouseSymbol obj={obj} state={state} />;
    case 'site.warehouse':
      return <WarehouseSymbol obj={obj} state={state} />;
    case 'site.sliding_gate':
      return <SlidingGateSymbol obj={obj} state={state} />;
    case 'site.rain_tank':
      return <RainTankSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'site.sewage_plant':
      return <SewagePlantSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'site.water_manhole':
      return <WaterManholeSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'site.lamp_post_double':
      return <LampPostDoubleSymbol obj={obj} state={state} />;
    case 'site.lamp_post_single':
      return <LampPostSingleSymbol obj={obj} state={state} />;
    case 'site.halogen':
      return <HalogenSymbol obj={obj} state={state} />;
    case 'site.garden_light':
      return <GardenLightSymbol obj={obj} state={state} />;
    case 'site.cable_junction':
      return <CableJunctionSymbol obj={obj} state={state} />;
    case 'site.alarm_beacon':
      return <AlarmBeaconSymbol obj={obj} state={state} />;
    case 'site.alarm_horn':
      return <AlarmHornSymbol obj={obj} state={state} />;
    case 'site.garden_sprinkler':
      return <GardenSprinklerSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'site.grass':
      return <GrassSymbol obj={obj} state={state} />;
    case 'site.concrete_road':
      return <ConcreteRoadSymbol obj={obj} state={state} />;
    case 'site.rainwater_tank2':
      return <RainwaterTank2Symbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'site.water_selector_valve_switched':
      return <WaterValveSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'site.water_selector_valve_3pos':
      return <WaterSelectorValveSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'site.check_valve':
      return <CheckValveSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'site.water_filter':
      return <WaterFilterSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'site.hydrofor':
      return <HydroforSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'site.flow_meter':
      return <FlowMeterSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'site.water_meter':
      return <WaterMeterSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'site.pressure_switch':
      return <PressureSwitchSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'site.rain_sensor':
      return <RainSensorSymbol obj={obj} state={state} />;
    case 'site.sprinkler_head':
      return <SprinklerHeadSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    case 'site.drip_line':
      return <DripLineSymbol obj={obj} state={state} terminalNetState={terminalNetState} />;
    default:
      return <GenericSymbol obj={obj} state={state} />;
  }
};
