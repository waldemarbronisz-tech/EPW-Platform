import { describe, it, expect } from 'vitest';

import loadSwitchSource from '../symbols/scada/LoadSwitchSymbol.tsx?raw';
import busbarSource from '../symbols/scada/BusbarSymbol.tsx?raw';
import wireNodeSource from '../symbols/scada/WireNodeSymbol.tsx?raw';
import labelFrameSource from '../symbols/scada/LabelFrameSymbol.tsx?raw';
import motorSource from '../symbols/scada/MotorSymbol.tsx?raw';
import pilotLampSource from '../symbols/scada/PilotLampSymbol.tsx?raw';
import socketSource from '../symbols/scada/SocketSymbol.tsx?raw';
import indicatorDiodeSource from '../symbols/scada/IndicatorDiodeSymbol.tsx?raw';
import meterSource from '../symbols/scada/MeterSymbol.tsx?raw';

import { LOAD_SWITCH_STATES, getLoadSwitchBottomConductorColor } from '../symbols/scada/LoadSwitchSymbol';
import { BUSBAR_STATES, getBusbarPorts } from '../symbols/scada/BusbarSymbol';
import { WIRE_NODE_STATES } from '../symbols/scada/WireNodeSymbol';
import { LABEL_FRAME_STATES } from '../symbols/scada/LabelFrameSymbol';
import { MOTOR_STATES } from '../symbols/scada/MotorSymbol';
import { PILOT_LAMP_STATES } from '../symbols/scada/PilotLampSymbol';
import { SOCKET_STATES } from '../symbols/scada/SocketSymbol';
import { INDICATOR_DIODE_STATES, getIndicatorDiodeRadius } from '../symbols/scada/IndicatorDiodeSymbol';
import { METER_STATES, getMeterHeight } from '../symbols/scada/MeterSymbol';
import { COLOR_ENERGIZED, COLOR_DE_ENERGIZED, GRID_SIZE } from '../theme/ScadaTheme';

describe('SCADA symbol state lists', () => {
  it('1. each of the nine symbols exports a list of its states', () => {
    expect(Array.isArray(LOAD_SWITCH_STATES)).toBe(true);
    expect(Array.isArray(BUSBAR_STATES)).toBe(true);
    expect(Array.isArray(WIRE_NODE_STATES)).toBe(true);
    expect(Array.isArray(LABEL_FRAME_STATES)).toBe(true);
    expect(Array.isArray(MOTOR_STATES)).toBe(true);
    expect(Array.isArray(PILOT_LAMP_STATES)).toBe(true);
    expect(Array.isArray(SOCKET_STATES)).toBe(true);
    expect(Array.isArray(INDICATOR_DIODE_STATES)).toBe(true);
    expect(Array.isArray(METER_STATES)).toBe(true);
  });
});

describe('Load switch (LoadSwitchSymbol)', () => {
  it('2. has states CLOSED, OPEN, FAULT', () => {
    expect(LOAD_SWITCH_STATES).toEqual(['CLOSED', 'OPEN', 'FAULT']);
  });

  it('3. CLOSED returns the bottom conductor color as energized', () => {
    expect(getLoadSwitchBottomConductorColor('CLOSED')).toBe(COLOR_ENERGIZED);
  });

  it('4. OPEN returns the bottom conductor color as de-energized', () => {
    expect(getLoadSwitchBottomConductorColor('OPEN')).toBe(COLOR_DE_ENERGIZED);
  });
});

describe('Motor (MotorSymbol)', () => {
  it('5. has states RUN, STOP, FAULT', () => {
    expect(MOTOR_STATES).toEqual(['RUN', 'STOP', 'FAULT']);
  });
});

describe('Pilot lamp (PilotLampSymbol)', () => {
  it('6. has states ON, OFF', () => {
    expect(PILOT_LAMP_STATES).toEqual(['ON', 'OFF']);
  });
});

describe('Indicator diode (IndicatorDiodeSymbol)', () => {
  it('7. has states ON, OFF, QUALITY, ALARM', () => {
    expect(INDICATOR_DIODE_STATES).toEqual(['ON', 'OFF', 'QUALITY', 'ALARM']);
  });

  it('8. accepts two sizes and returns different radii', () => {
    const small = getIndicatorDiodeRadius('small');
    const large = getIndicatorDiodeRadius('large');
    // feat/appearance-selection-frames commit 1: 8/12 -> 5/7 (diodes
    // were disproportionately large next to a signal panel's row text -
    // see ScadaTheme.ts's DIODE_RADIUS_SMALL/DIODE_RADIUS_LARGE). This
    // is not a meter/panel test (GRANICE's "no test modification"
    // clause is scoped to those), so updating the literal expectation
    // here is the deliberate point of mandatory test 1, not a
    // workaround of it.
    expect(small).toBe(5);
    expect(large).toBe(7);
    expect(small).not.toBe(large);
  });
});

describe('Busbar (BusbarSymbol)', () => {
  it('9. a busbar of width 320 generates 20 ports at GRID_SIZE 16', () => {
    expect(GRID_SIZE).toBe(16);
    const ports = getBusbarPorts(320);
    expect(ports.length).toBe(20);
  });

  it('10. a busbar of width 0 is handled without throwing', () => {
    expect(() => getBusbarPorts(0)).not.toThrow();
    expect(getBusbarPorts(0)).toEqual([]);
  });
});

describe('Meter (MeterSymbol)', () => {
  it('11. a 3-row meter is taller than a 1-row meter', () => {
    const heightThreeRows = getMeterHeight(3, false);
    const heightOneRow = getMeterHeight(1, false);
    expect(heightThreeRows).toBeGreaterThan(heightOneRow);
  });

  it('12. a 0-row meter is handled without throwing', () => {
    expect(() => getMeterHeight(0, false)).not.toThrow();
    expect(getMeterHeight(0, false)).toBeGreaterThan(0); // padding alone
  });
});

describe('No hard-coded colors in scada symbols', () => {
  const symbolSources: Record<string, string> = {
    'LoadSwitchSymbol.tsx': loadSwitchSource,
    'BusbarSymbol.tsx': busbarSource,
    'WireNodeSymbol.tsx': wireNodeSource,
    'LabelFrameSymbol.tsx': labelFrameSource,
    'MotorSymbol.tsx': motorSource,
    'PilotLampSymbol.tsx': pilotLampSource,
    'SocketSymbol.tsx': socketSource,
    'IndicatorDiodeSymbol.tsx': indicatorDiodeSource,
    'MeterSymbol.tsx': meterSource
  };

  it('13. every color used by the nine symbols comes from ScadaTheme (no symbol hard-codes a hex color)', () => {
    const hexColorPattern = /#[0-9A-Fa-f]{3,8}\b/g;

    for (const [file, source] of Object.entries(symbolSources)) {
      const matches = source.match(hexColorPattern);
      expect(matches, `${file} must not contain a literal hex color - found: ${matches?.join(', ')}`).toBeNull();
    }
  });
});
