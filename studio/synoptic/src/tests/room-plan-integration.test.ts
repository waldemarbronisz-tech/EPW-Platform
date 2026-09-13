// feat/room-plan + feat/multi-screen: the parts that connect the plan to
// the rest of the platform - circuit bindings (which controller output
// switches a circuit), the schedule derived from the drawing, and the
// several screens one project holds.
//
// Pure functions with exact expected values throughout, which is why
// CircuitBindings.ts, RoomTakeoff.ts and ScreenContent.ts contain no
// store and no Konva; the store slice is exercised through the real
// store, since a screen switch is precisely a store operation.

import { describe, it, expect, beforeEach } from 'vitest';
import type { WallElement } from '../elements/WallElement';
import { WALL_DEFAULT_THICKNESS } from '../elements/WallElement';
import {
  circuitDevice, circuitFeedbackMode, circuitOutputAddress,
  circuitStateIsAssumed, describeCircuitBinding, describeCircuitFeedback,
  findBinding, setBinding, switchableDevices,
} from '../project/CircuitBindings';
import type { CircuitBinding } from '../project/CircuitBindings';
import { buildRoomTakeoff, takeoffToText } from '../project/RoomTakeoff';
import { blankScreenContent, uniqueScreenName } from '../project/ScreenContent';
import { computeIlluminanceGrid, PHOTOMETRY } from '../project/Illuminance';
import type { Device } from '../project/DeviceSchema';
import type { SynopticObject } from '../store';
import { useStore } from '../store';
import { cm, m } from '../theme/Scale';

const wall = (from: [number, number], to: [number, number], extra: Partial<WallElement> = {}): WallElement => ({
  id: `${from.join(',')}->${to.join(',')}`,
  from: { x: from[0], y: from[1] },
  to: { x: to[0], y: to[1] },
  thickness: WALL_DEFAULT_THICKNESS,
  ...extra,
});

const fixture = (id: string, type: string, circuit?: string): SynopticObject => ({
  id, type, category: 'BUILDING', x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
  visible: true, locked: false, layer: 0, circuit, tag: '', description: '',
  color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
  tooltip: '', width: cm(30), height: cm(30), customProperties: {},
});

const switchedDevice = (id: string, designation: string, doClose: string): Device => ({
  id, designation, name: '', behavior: 'SWITCHED', kind: 'contactor', publishToHa: false,
  feedback: { mode: 'NONE' },
  command: { outputCount: 1, style: 'MAINTAINED', doClose },
  supervision: { confirmTimeoutMs: 5000, discrepancyAlarm: false },
  safeState: { onFault: 'OPEN' },
} as unknown as Device);

const measuredDevice = (id: string): Device => ({
  id, designation: id, name: '', behavior: 'MEASURED', kind: 'sensor', publishToHa: false,
} as unknown as Device);

describe('circuit bindings - what actually switches a circuit', () => {
  const devices = [switchedDevice('K1', '-K1', 'ELA1.DO.3'), measuredDevice('T1')];

  it('offers only SWITCHED devices - a circuit is switched on and off', () => {
    expect(switchableDevices(devices).map(d => d.id)).toEqual(['K1']);
  });

  it('binds and unbinds, matching circuit names case-insensitively', () => {
    let bindings: CircuitBinding[] = [];
    bindings = setBinding(bindings, 'OBW_1', 'K1');
    expect(findBinding(bindings, 'obw_1')?.deviceId).toBe('K1');
    // An empty device REMOVES the binding rather than storing a blank
    // one, so "not wired" has exactly one representation.
    bindings = setBinding(bindings, 'OBW_1', undefined);
    expect(findBinding(bindings, 'OBW_1')).toBeUndefined();
  });

  it('replaces a previous binding instead of stacking a second one', () => {
    let bindings = setBinding([], 'OBW_1', 'K1');
    bindings = setBinding(bindings, 'obw_1', 'K2');
    expect(bindings).toHaveLength(1);
    expect(bindings[0].deviceId).toBe('K2');
  });

  it('resolves the controller OUTPUT the circuit will energise', () => {
    const bindings = setBinding([], 'OBW_1', 'K1');
    expect(circuitOutputAddress(bindings, devices, 'OBW_1')).toBe('ELA1.DO.3');
    expect(circuitDevice(bindings, devices, 'OBW_1')?.id).toBe('K1');
    expect(describeCircuitBinding(bindings, devices, 'OBW_1')).toBe('-K1 -> ELA1.DO.3');
  });

  it('reads as NOT wired when the chain cannot be followed to the end', () => {
    // No binding at all...
    expect(circuitOutputAddress([], devices, 'OBW_1')).toBeNull();
    // ...a device that has since been deleted from the registry...
    const dangling = setBinding([], 'OBW_1', 'GONE');
    expect(circuitOutputAddress(dangling, devices, 'OBW_1')).toBeNull();
    expect(describeCircuitBinding(dangling, devices, 'OBW_1')).toBe('not bound');
    // ...and a device that is not SWITCHED and so cannot drive one.
    const wrongKind = setBinding([], 'OBW_1', 'T1');
    expect(circuitOutputAddress(wrongKind, devices, 'OBW_1')).toBeNull();
  });
});

describe('feedback - and why a lighting circuit has none', () => {
  // A lamp on a plain DO has no auxiliary contact to read back, so its
  // state is ASSUMED from the command. That is correct, not a shortcut,
  // and the editor has to be able to say which case it is looking at -
  // a circuit with no feedback must never grow a confirmation timeout
  // or a discrepancy alarm, because no input could ever satisfy them.
  const noFeedback = switchedDevice('K_LIGHT', '-K1', 'ELA1.DO.3');
  const withFeedback = {
    ...switchedDevice('K_VALVE', '-K2', 'ELA1.DO.4'),
    feedback: { mode: 'SINGLE', diClosed: 'ELA2.DI.7' },
  } as unknown as Device;
  const devices = [noFeedback, withFeedback];

  it('reports NONE for a lamp switched straight from a DO', () => {
    const bindings = setBinding([], 'OBW_SWIATLO', 'K_LIGHT');
    expect(circuitFeedbackMode(bindings, devices, 'OBW_SWIATLO')).toBe('NONE');
    expect(circuitStateIsAssumed(bindings, devices, 'OBW_SWIATLO')).toBe(true);
    expect(describeCircuitFeedback(bindings, devices, 'OBW_SWIATLO'))
      .toBe('none - state assumed from DO');
  });

  it('reports the DI when an auxiliary contact IS wired', () => {
    const bindings = setBinding([], 'OBW_ZAWOR', 'K_VALVE');
    expect(circuitFeedbackMode(bindings, devices, 'OBW_ZAWOR')).toBe('SINGLE');
    expect(circuitStateIsAssumed(bindings, devices, 'OBW_ZAWOR')).toBe(false);
    expect(describeCircuitFeedback(bindings, devices, 'OBW_ZAWOR')).toContain('ELA2.DI.7');
  });

  it('an unbound circuit is assumed too - nothing is confirming it either', () => {
    expect(circuitFeedbackMode([], devices, 'OBW_X')).toBeNull();
    expect(circuitStateIsAssumed([], devices, 'OBW_X')).toBe(true);
  });

  it('the schedule carries it, and does NOT flag its absence as a fault', () => {
    const objects = [fixture('a', 'building.luminaire', 'OBW_SWIATLO')];
    const bindings = setBinding([], 'OBW_SWIATLO', 'K_LIGHT');
    const takeoff = buildRoomTakeoff([], objects, bindings, devices, undefined);
    const row = takeoff.circuits.find(c => c.name === 'OBW_SWIATLO')!;
    expect(row.assumed).toBe(true);
    expect(row.feedback).toBe('none - state assumed from DO');
    // Wired is about having a DEVICE behind the circuit, which it has -
    // having no feedback is not a wiring gap.
    expect(row.wired).toBe(true);
    expect(takeoff.totals.unwiredCircuits).toBe(0);
  });
});

describe('the schedule is derived from the drawing', () => {
  // A 4 m x 3 m room of 2.5 m walls: 14 m of wall, 12 m2 of floor.
  const room = [
    wall([0, 0], [m(4), 0], { height: cm(250) }),
    wall([m(4), 0], [m(4), m(3)], { height: cm(250) }),
    wall([m(4), m(3)], [0, m(3)], { height: cm(250) }),
    wall([0, m(3)], [0, 0], { height: cm(250) }),
  ];

  it('measures wall runs in real metres', () => {
    const takeoff = buildRoomTakeoff(room, [], [], [], undefined);
    expect(takeoff.totals.wallLength).toBeCloseTo(14, 5);
    // Face area is the run times the height: 14 m x 2.5 m.
    expect(takeoff.totals.wallArea).toBeCloseTo(35, 4);
  });

  it('measures floor area in real square metres', () => {
    const takeoff = buildRoomTakeoff(room, [], [], [], undefined);
    expect(takeoff.totals.floorArea).toBeCloseTo(12, 4);
    expect(takeoff.floors[0].rooms).toBe(1);
  });

  it('reports "rozne" rather than averaging two different wall heights', () => {
    const mixed = [...room.slice(1), wall([0, 0], [m(4), 0], { height: cm(300) })];
    const takeoff = buildRoomTakeoff(mixed, [], [], [], undefined);
    expect(takeoff.walls[0].height).toBeNull();
  });

  it('counts fixtures by type, and only building ones', () => {
    const objects = [
      fixture('a', 'building.luminaire'),
      fixture('b', 'building.luminaire'),
      fixture('c', 'building.socket_outlet'),
      fixture('d', 'electrical.circuit_breaker'),
    ];
    const takeoff = buildRoomTakeoff(room, objects, [], [], undefined);
    expect(takeoff.totals.fixtures).toBe(3);
    const luminaires = takeoff.fixtures.find(f => f.type === 'building.luminaire');
    expect(luminaires?.count).toBe(2);
  });

  it('flags circuits with nothing behind them - the one actionable number here', () => {
    const objects = [
      fixture('a', 'building.luminaire', 'OBW_1'),
      fixture('b', 'building.luminaire', 'OBW_2'),
    ];
    const devices = [switchedDevice('K1', '-K1', 'ELA1.DO.3')];
    const bindings = setBinding([], 'OBW_1', 'K1');
    const takeoff = buildRoomTakeoff(room, objects, bindings, devices, undefined);
    expect(takeoff.totals.unwiredCircuits).toBe(1);
    expect(takeoff.circuits.find(c => c.name === 'OBW_1')?.wired).toBe(true);
    expect(takeoff.circuits.find(c => c.name === 'OBW_2')?.wired).toBe(false);
  });

  it('exports as tab-separated text with a decimal comma', () => {
    const text = takeoffToText(buildRoomTakeoff(room, [], [], [], undefined));
    expect(text).toContain('WALLS');
    expect(text).toContain('14,00');
    expect(text.split('\n')[1]).toContain('\t');
  });
});

describe('the schedule reports the lighting result', () => {
  const room = [
    { x: 0, y: 0 }, { x: m(4), y: 0 }, { x: m(4), y: m(3) }, { x: 0, y: m(3) },
  ];
  const walls = [
    wall([0, 0], [m(4), 0], { height: cm(250) }),
    wall([m(4), 0], [m(4), m(3)], { height: cm(250) }),
    wall([m(4), m(3)], [0, m(3)], { height: cm(250) }),
    wall([0, m(3)], [0, 0], { height: cm(250) }),
  ];
  const lit = (id: string, xm: number, ym: number, on = true): SynopticObject => ({
    ...fixture(id, 'building.luminaire'),
    x: m(xm) - cm(30) / 2,
    y: m(ym) - cm(30) / 2,
    editor: { preview_state: on ? 'ON' : 'OFF' },
  });

  it('says nothing at all about a room with the lights off', () => {
    const takeoff = buildRoomTakeoff(walls, [lit('a', 2, 1.5, false)], [], [], undefined);
    expect(takeoff.lighting).toEqual([]);
  });

  it('reports the same figures the map is drawn from', () => {
    const objects = [lit('a', 1, 1), lit('b', 3, 1), lit('c', 1, 2), lit('d', 3, 2)];
    const takeoff = buildRoomTakeoff(walls, objects, [], [], undefined);
    expect(takeoff.lighting).toHaveLength(1);
    const row = takeoff.lighting[0];
    // The same grid the false-colour view uses, so the two can never
    // disagree about a number.
    const grid = computeIlluminanceGrid(room, objects);
    expect(row.average).toBeCloseTo(grid.stats.average, 6);
    expect(row.min).toBeCloseTo(grid.stats.min, 6);
    expect(row.uniformity).toBeCloseTo(grid.stats.uniformity, 6);
  });

  it('counts installed flux only for fittings inside THAT room', () => {
    const objects = [
      lit('inside', 2, 1.5),
      // Well outside the 4x3 m room - its light may reach in, but its
      // flux is not this room's installed load.
      lit('outside', 9, 9),
    ];
    const takeoff = buildRoomTakeoff(walls, objects, [], [], undefined);
    expect(takeoff.lighting[0].installedFlux).toBe(PHOTOMETRY['building.luminaire'].flux);
    // 1200 lm over 12 m2.
    expect(takeoff.lighting[0].fluxDensity).toBeCloseTo(100, 5);
  });

  it('exports the lighting block as text too', () => {
    const text = takeoffToText(buildRoomTakeoff(walls, [lit('a', 2, 1.5)], [], [], undefined));
    expect(text).toContain('LIGHTING');
    expect(text).toContain('Uniformity');
  });
});

describe('screens', () => {
  it('never repeats a name', () => {
    const screens = [{ id: '1', name: 'Screen 1' }, { id: '2', name: 'Screen 2' }];
    expect(uniqueScreenName(screens, 'Screen 1')).toBe('Screen 1 2');
    expect(uniqueScreenName(screens, 'Kotlownia')).toBe('Kotlownia');
  });

  it('starts blank', () => {
    const blank = blankScreenContent();
    expect(blank.objects).toEqual([]);
    expect(blank.walls).toEqual([]);
  });
});

describe('screens, through the real store', () => {
  beforeEach(() => {
    useStore.setState({
      screens: [{ id: 'screen-1', name: 'Screen 1' }],
      activeScreenId: 'screen-1',
      screenContents: {},
      screenViews: {},
      screenHistories: {},
      hiddenScreens: [],
      canvasState: { zoom: 1, panX: 0, panY: 0 },
      objects: [], connections: [], meters: [], signalPanels: [],
      frames: [], walls: [], groupCommands: [], setpointPanels: [],
    });
  });

  it('parks the current screen and opens an empty one', () => {
    useStore.setState({ walls: [wall([0, 0], [100, 0])] });
    useStore.getState().addScreen();

    const state = useStore.getState();
    expect(state.screens).toHaveLength(2);
    expect(state.screens[1].name).toBe('Screen 2');
    // The new screen is empty...
    expect(state.walls).toEqual([]);
    // ...and the old one's content was kept, not lost.
    expect(state.screenContents['screen-1'].walls).toHaveLength(1);
  });

  it('brings each screen own content back on switching', () => {
    useStore.setState({ walls: [wall([0, 0], [100, 0])] });
    useStore.getState().addScreen();
    const secondId = useStore.getState().screens[1].id;
    useStore.setState({ walls: [wall([0, 0], [50, 0]), wall([50, 0], [50, 50])] });

    useStore.getState().switchScreen('screen-1');
    expect(useStore.getState().walls).toHaveLength(1);

    useStore.getState().switchScreen(secondId);
    expect(useStore.getState().walls).toHaveLength(2);
  });

  it('clears the selection on switching - it would point at objects no longer on screen', () => {
    useStore.setState({ walls: [wall([0, 0], [100, 0])], selectedWallIds: ['0,0->100,0'] });
    useStore.getState().addScreen();
    expect(useStore.getState().selectedWallIds).toEqual([]);
  });

  it('does not let undo cross a screen switch', () => {
    useStore.setState({ walls: [wall([0, 0], [100, 0])] });
    useStore.getState().addScreen();
    // History is reset to the screen being opened - one entry, at index 0.
    expect(useStore.getState().history).toHaveLength(1);
    expect(useStore.getState().historyIndex).toBe(0);
  });

  it('gives each screen its OWN undo stack back when you return to it', () => {
    // Clicking between tiles is constant now; an undo stack that emptied
    // on every click would be unusable. Undo still never crosses screens.
    useStore.setState({ history: [{ objects: [] } as any, { objects: [] } as any, { objects: [] } as any], historyIndex: 2 });
    useStore.getState().addScreen();
    const secondId = useStore.getState().screens[1].id;
    expect(useStore.getState().history).toHaveLength(1);

    useStore.getState().switchScreen('screen-1');
    expect(useStore.getState().history).toHaveLength(3);
    expect(useStore.getState().historyIndex).toBe(2);

    useStore.getState().switchScreen(secondId);
    expect(useStore.getState().history).toHaveLength(1);
  });

  it('remembers each screen zoom and pan, so activating a tile never jumps', () => {
    useStore.setState({ canvasState: { zoom: 2, panX: -40, panY: 15 } });
    useStore.getState().addScreen();
    const secondId = useStore.getState().screens[1].id;
    // A never-viewed screen starts neutral (Canvas fits it on first show).
    expect(useStore.getState().canvasState).toEqual({ zoom: 1, panX: 0, panY: 0 });

    useStore.setState({ canvasState: { zoom: 0.5, panX: 10, panY: 10 } });
    useStore.getState().switchScreen('screen-1');
    expect(useStore.getState().canvasState).toEqual({ zoom: 2, panX: -40, panY: 15 });

    useStore.getState().switchScreen(secondId);
    expect(useStore.getState().canvasState).toEqual({ zoom: 0.5, panX: 10, panY: 10 });
  });

  it('hides a tile without deleting the screen, and hands "active" on when the active one is hidden', () => {
    useStore.getState().addScreen();
    const secondId = useStore.getState().screens[1].id;
    useStore.getState().hideScreen(secondId);
    expect(useStore.getState().screens).toHaveLength(2);
    expect(useStore.getState().activeScreenId).toBe('screen-1');
    expect(useStore.getState().hiddenScreens).toEqual([secondId]);

    useStore.getState().showScreen(secondId);
    expect(useStore.getState().hiddenScreens).toEqual([]);
  });

  it('refuses to delete the last screen', () => {
    useStore.getState().deleteScreen('screen-1');
    expect(useStore.getState().screens).toHaveLength(1);
  });

  it('deleting the active screen opens another one', () => {
    useStore.getState().addScreen();
    const secondId = useStore.getState().screens[1].id;
    useStore.getState().deleteScreen(secondId);
    const state = useStore.getState();
    expect(state.screens).toHaveLength(1);
    expect(state.activeScreenId).toBe('screen-1');
  });

  it('captureActiveScreen flushes the live arrays - what saving depends on', () => {
    useStore.setState({ walls: [wall([0, 0], [100, 0])] });
    useStore.getState().captureActiveScreen();
    expect(useStore.getState().screenContents['screen-1'].walls).toHaveLength(1);
  });
});
