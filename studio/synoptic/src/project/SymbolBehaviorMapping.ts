// fix/inline-device-creation commit 3: the ONE place a schematic
// symbol's own type (SynopticObject.type, e.g.
// 'electrical.disconnect_switch' - src/symbols/registry/*.ts) is mapped
// to the DeviceBehavior a brand-new device for it should suggest.
// DeviceFormDialog.tsx's own "create or assign" mode is the only
// caller; GRANICE requires this to live in exactly one place rather
// than scattered per-component guesses, so nothing else in src/ may
// keep a second copy of this list.
//
// The suggestion is always changeable, never a lock - DeviceFormDialog's
// own Zachowanie <select> stays exactly as editable as it always was;
// this only decides its INITIAL value. A symbol type outside this
// mapping suggests nothing at all (suggestBehaviorForSymbolType returns
// undefined) - DeviceFormDialog then leaves behavior unchosen until the
// user picks one by hand (see that file's own comment on the ''
// sentinel it uses for "not chosen yet").
//
// Source (task's own literal three groups):
//  SWITCHED - lacznik, rozlacznik, wylacznik, stycznik, silnik, pompa,
//    wentylator, grzalka, zawor elektromagnetyczny
//  SIGNAL   - czujka, kontaktron, krancowka, lampka
//  MEASURED - czujnik temperatury, cisnienia, poziomu, wilgotnosci,
//    przeplywu
//
// Mapped onto the ACTUAL registered symbol types (src/symbols/registry/
// *.ts's own `type` fields) that correspond to each Polish word:
//  lacznik -> scada.load_switch (Load Switch)
//  rozlacznik -> electrical.disconnect_switch (Disconnect Switch)
//  wylacznik -> electrical.circuit_breaker (Circuit Breaker)
//  stycznik -> electrical.contactor (Contactor)
//  silnik -> electrical.motor AND scada.motor (both are "Motor")
//  pompa -> water.pump (Pump)
//  wentylator -> hvac.fan (Fan)
//  grzalka -> hvac.heater (Heater)
//  zawor elektromagnetyczny -> water.solenoid_valve (Solenoid Valve) -
//    the plain water.valve (a manual valve, no actuator) is deliberately
//    left OUT of the mapping: it is not a remotely-controlled device.
//  czujka -> instrumentation.leak_sensor (Leak Sensor) - the only
//    binary/presence-style detector this registry has today; "kontaktron"
//    (reed contact) and "krancowka" (limit switch) have no matching
//    symbol type in the registry yet, so they map to nothing - adding
//    a mapping entry for a symbol type that does not exist would be
//    dead code, not a real suggestion.
//  lampka -> electrical.indicator_lamp AND scada.pilot_lamp (both are
//    indicator/pilot lamps)
//  czujnik temperatury -> instrumentation.temperature_sensor
//  czujnik cisnienia -> instrumentation.pressure_sensor
//  czujnik poziomu -> instrumentation.level_sensor
//  czujnik wilgotnosci -> instrumentation.humidity_sensor
//  czujnik przeplywu -> no matching symbol type exists in the registry
//    today (no flow sensor symbol) - left unmapped for the same reason
//    as kontaktron/krancowka above.
import type { DeviceBehavior } from './DeviceSchema';

const SYMBOL_TYPE_TO_BEHAVIOR: Record<string, DeviceBehavior> = {
  'scada.load_switch': 'SWITCHED',
  'electrical.disconnect_switch': 'SWITCHED',
  'electrical.circuit_breaker': 'SWITCHED',
  'electrical.contactor': 'SWITCHED',
  'electrical.motor': 'SWITCHED',
  'scada.motor': 'SWITCHED',
  'water.pump': 'SWITCHED',
  'hvac.fan': 'SWITCHED',
  'hvac.heater': 'SWITCHED',
  'water.solenoid_valve': 'SWITCHED',

  'instrumentation.leak_sensor': 'SIGNAL',
  'electrical.indicator_lamp': 'SIGNAL',
  'scada.pilot_lamp': 'SIGNAL',

  'instrumentation.temperature_sensor': 'MEASURED',
  'instrumentation.pressure_sensor': 'MEASURED',
  'instrumentation.level_sensor': 'MEASURED',
  'instrumentation.humidity_sensor': 'MEASURED',
};

/** The suggested DeviceBehavior for a symbol of this type, or undefined when it is outside the mapping above (the caller then leaves behavior unchosen, per this file's own header comment). */
export function suggestBehaviorForSymbolType(symbolType: string): DeviceBehavior | undefined {
  return SYMBOL_TYPE_TO_BEHAVIOR[symbolType];
}
