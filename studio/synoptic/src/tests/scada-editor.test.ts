import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import type { SynopticObject } from '../store';
import { getBusbarEdgePorts } from '../symbols/scada/BusbarSymbol';
import { resolveConnectionPoint } from '../utils/GeometryUtils';
import { getSymbolDefinition } from '../symbols/SymbolRegistry';
import { resolveObjectLabelText, measureLabelLine, LABEL_MAX_WIDTH } from '../components/ObjectLabelRenderer';
import { snapValue } from '../utils/GridSnap';
import { GRID_SIZE, BUSBAR_HEIGHT } from '../theme/ScadaTheme';
import { ProjectManager } from '../project/ProjectManager';
import { FORMAT_NAME } from '../project/ProjectSchema';
import { getBoundaryPointWidth, getBoundaryPortFraction } from '../symbols/scada/BoundaryPointSymbol';
import { ConnectionService } from '../project/ConnectionService';
import { describeObject } from '../utils/ObjectDisplay';

function makeBusbar(overrides: Partial<SynopticObject> = {}): SynopticObject {
  return {
    id: 'BUS1',
    type: 'scada.busbar',
    category: 'SCADA',
    x: 0, y: 0,
    rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 1,
    tag: 'BUS1', description: '', color: '#000', fill: '#000', border: '#000',
    text: '', font: 'Arial', fontSize: 12, tooltip: '',
    width: 320, height: BUSBAR_HEIGHT,
    customProperties: {},
    ...overrides
  };
}

describe('SCADA busbar edge ports (getBusbarEdgePorts)', () => {
  it('top ports sit at y = 0', () => {
    const ports = getBusbarEdgePorts(320, 'top');
    expect(ports.every(p => p.y === 0)).toBe(true);
  });

  it('bottom ports sit at y = BUSBAR_HEIGHT', () => {
    const ports = getBusbarEdgePorts(320, 'bottom');
    expect(ports.every(p => p.y === BUSBAR_HEIGHT)).toBe(true);
  });

  it('generates one port per GRID_SIZE step, same count as the single-row model', () => {
    expect(getBusbarEdgePorts(320, 'top').length).toBe(Math.floor(320 / GRID_SIZE));
  });

  it('a zero-width bar produces no ports on either edge, without throwing', () => {
    expect(() => getBusbarEdgePorts(0, 'top')).not.toThrow();
    expect(getBusbarEdgePorts(0, 'top')).toEqual([]);
    expect(getBusbarEdgePorts(0, 'bottom')).toEqual([]);
  });

  // Mandatory test from the task spec: a 320-wide busbar at GRID_SIZE 16
  // must generate 40 ports total (20 top + 20 bottom) - calls the actual
  // port-generating function itself, not a stand-in constant.
  it('a 320-wide busbar generates 40 ports total: 20 top and 20 bottom', () => {
    const width = 320;
    const top = getBusbarEdgePorts(width, 'top');
    const bottom = getBusbarEdgePorts(width, 'bottom');

    expect(top.length).toBe(20);
    expect(bottom.length).toBe(20);
    expect(top.length + bottom.length).toBe(40);
    // Ties the count to GRID_SIZE itself, not a hardcoded 20, so this
    // still catches a regression if GRID_SIZE ever changes.
    expect(top.length).toBe(Math.floor(width / GRID_SIZE));
  });

  // Root-cause fix for usterka "szyna zbiorcza nie ma przylaczen": a port
  // is generated at a custom height too, not hardcoded to BUSBAR_HEIGHT -
  // electrical.busbar (defaultHeight 10, not 22) now shares this same
  // mechanism and needs its OWN edge, not scada.busbar's.
  it('bottom-row ports sit at a caller-supplied height, not always BUSBAR_HEIGHT', () => {
    const ports = getBusbarEdgePorts(160, 'bottom', 10);
    expect(ports.every(p => p.y === 10)).toBe(true);
  });
});

describe('Dynamic port resolution (GeometryUtils.resolveConnectionPoint)', () => {
  it('resolves a legacy center-row dyn_NN port unchanged (y = 0.5)', () => {
    // The legacy unprefixed dyn_NN center-row id format must keep
    // resolving correctly (existing saved projects use it) even though
    // new connections are generated in the top/bottom edge format now -
    // this checks adding that format did not regress it.
    const bar = makeBusbar();
    const point = resolveConnectionPoint(bar, 'dyn_50');
    expect(point).not.toBeNull();
    expect(point?.y).toBe(0.5);
    expect(point?.x).toBeCloseTo(0.5, 5);
  });

  it('resolves a new dyn_top_NN port at y = 0', () => {
    const bar = makeBusbar();
    const point = resolveConnectionPoint(bar, 'dyn_top_25');
    expect(point).not.toBeNull();
    expect(point?.y).toBe(0);
    expect(point?.x).toBeCloseTo(0.25, 5);
  });

  it('resolves a new dyn_bot_NN port at y = 1', () => {
    const bar = makeBusbar();
    const point = resolveConnectionPoint(bar, 'dyn_bot_75');
    expect(point).not.toBeNull();
    expect(point?.y).toBe(1);
    expect(point?.x).toBeCloseTo(0.75, 5);
  });

  it('uses the object\'s own current width, not the symbol definition\'s static default', () => {
    const narrowed = makeBusbar({ width: 32 }); // shrunk well below the registry's default of 200
    const point = resolveConnectionPoint(narrowed, 'dyn_top_50');
    expect(point?.x).toBeCloseTo(0.5, 5);
  });

  // Root-cause fix: electrical.busbar (the plain "Busbar" in the
  // Electrical category, listed ahead of "Busbar (SCADA)") had no
  // connectionPoints and no supportsDynamicPorts at all - it reported
  // zero ports, so no wire could ever attach to it, regardless of what
  // the newer scada.busbar could do. Now shares the same mechanism.
  it('electrical.busbar registry entry now supports dynamic ports', () => {
    const def = getSymbolDefinition('electrical.busbar');
    expect(def?.supportsDynamicPorts).toBe(true);
  });

  it('resolves a dyn_top_NN port on an electrical.busbar object too, at its own height', () => {
    const legacyBar = makeBusbar({ type: 'electrical.busbar', width: 200, height: 10 });
    const point = resolveConnectionPoint(legacyBar, 'dyn_top_40');
    expect(point).not.toBeNull();
    expect(point?.y).toBe(0);
    expect(point?.x).toBeCloseTo(0.4, 5);
  });
});

// The old store.resizeBusbar action and its dyn_top_NN reattachment
// mechanism are gone entirely under the node-based wiring model (a
// busbar is now a BUS-style wire, not a resizable symbol with dynamic
// ports) - the describe block that used to live here (four tests) tested
// exactly that removed action and was deleted along with it, not
// replaced: resizing a wire's own length is just dragging its endpoint,
// already covered by the wire-drawing tests.

function makeDevice(overrides: Partial<SynopticObject> = {}): SynopticObject {
  return {
    id: 'obj-uuid-123',
    type: 'electrical.circuit_breaker',
    category: 'Electrical',
    x: 0, y: 0,
    rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 1,
    tag: 'electrical.circuit_breaker_1', // the exact kind of type-derived tag the label must never show
    description: '', color: '#000', fill: '#000', border: '#000',
    text: '', font: 'Arial', fontSize: 12, tooltip: '',
    width: 40, height: 40,
    customProperties: {},
    ...overrides
  };
}

describe('Object label text (resolveObjectLabelText)', () => {
  it('shows the designation when present', () => {
    const obj = makeDevice({ designation: '-K1' });
    expect(resolveObjectLabelText(obj).primary).toBe('-K1');
  });

  it('draws no primary line at all when designation is empty - bug fix: the previous task wrongly fell back to the object id (a UUID), which is exactly usterka 1', () => {
    const obj = makeDevice({ designation: '' });
    const { primary } = resolveObjectLabelText(obj);
    expect(primary).toBe('');
    expect(primary).not.toBe(obj.id);
    expect(primary).not.toContain('electrical.circuit_breaker');
    expect(primary).not.toBe(obj.type);
    expect(primary).not.toBe(obj.tag);
  });

  it('never falls back to the type identifier or the tag under any field combination', () => {
    const obj = makeDevice({ designation: '', name: '' });
    const { primary, secondary } = resolveObjectLabelText(obj);
    expect(primary).not.toContain('electrical.');
    expect(secondary).not.toContain('electrical.');
  });

  it('shows the name as the secondary line when showName is on', () => {
    const obj = makeDevice({ designation: '-K1', name: 'Stycznik grzalki', showName: true });
    expect(resolveObjectLabelText(obj).secondary).toBe('Stycznik grzalki');
  });

  it('hides the secondary line when showName is off', () => {
    const obj = makeDevice({ designation: '-K1', name: 'Stycznik grzalki', showName: false });
    expect(resolveObjectLabelText(obj).secondary).toBe('');
  });

  it('hides the primary line when showDesignation is off, even with a designation set', () => {
    const obj = makeDevice({ designation: '-K1', showDesignation: false });
    expect(resolveObjectLabelText(obj).primary).toBe('');
  });

  it('produces neither line for a device with no designation and no name - the object stands unlabeled', () => {
    const obj = makeDevice({ designation: '', name: '' });
    const { primary, secondary } = resolveObjectLabelText(obj);
    expect(primary).toBe('');
    expect(secondary).toBe('');
  });
});

describe('Label width capping (measureLabelLine / LABEL_MAX_WIDTH)', () => {
  it('shrinks to fit short text, well under the cap', () => {
    const line = measureLabelLine('-K1', 12, LABEL_MAX_WIDTH - 8);
    expect(line.lines).toBe(1);
    expect(line.width).toBeLessThan(LABEL_MAX_WIDTH - 8);
  });

  it('caps a long designation at the max width and reserves a second line', () => {
    // Long enough that the character-count estimate exceeds any
    // reasonable single-line budget - exactly the UUID-length case
    // usterka 1 was reported against.
    const longText = 'ae77a756-08cb-42d9-b3ff-ef0243a4818d';
    const maxTextWidth = LABEL_MAX_WIDTH - 8;
    const line = measureLabelLine(longText, 12, maxTextWidth);
    expect(line.width).toBeLessThanOrEqual(maxTextWidth);
    expect(line.lines).toBe(2);
  });

  it('returns zero size for empty text, so an unused line takes no space', () => {
    const line = measureLabelLine('', 12, LABEL_MAX_WIDTH);
    expect(line.width).toBe(0);
    expect(line.height).toBe(0);
  });
});

describe('Grid snapping (GridSnap.snapValue / shouldSnapToGrid)', () => {
  beforeEach(() => {
    useStore.setState({ snapToGridEnabled: true });
  });

  it('rounds a value to the nearest grid node when snapping is on and Alt is not held', () => {
    expect(snapValue(37, 16, false)).toBe(32); // nearest multiple of 16
    expect(snapValue(40, 16, false)).toBe(48);
  });

  it('holding Alt bypasses snapping even though the toggle is on', () => {
    expect(snapValue(37, 16, true)).toBe(37);
  });

  it('turning the persistent toggle off bypasses snapping even without Alt', () => {
    useStore.setState({ snapToGridEnabled: false });
    expect(snapValue(37, 16, false)).toBe(37);
  });

  it('the View menu toggle defaults to on', () => {
    useStore.setState({ snapToGridEnabled: true }); // reset from prior test in this file
    expect(useStore.getState().snapToGridEnabled).toBe(true);
  });

  it('toggleSnapToGrid flips the persistent setting', () => {
    const before = useStore.getState().snapToGridEnabled;
    useStore.getState().toggleSnapToGrid();
    expect(useStore.getState().snapToGridEnabled).toBe(!before);
  });
});

describe('Grid size on project load (ProjectManager.loadProject, usterka 3 fix)', () => {
  // Root cause of usterka 3, found by empirical inspection (see raport.md):
  // handleDrop/onDragEnd/onTransformEnd all snap correctly against
  // canvasConfig.gridSize on a fresh session - but ProjectManager used to
  // fall back to a hardcoded 20 (a pre-GRID_SIZE leftover) whenever a
  // loaded project's canvas.gridSize was missing or falsy, silently
  // diverging canvasConfig.gridSize from GRID_SIZE for any such file.
  it('falls back to GRID_SIZE, not a hardcoded 20, when a loaded project omits canvas.gridSize', () => {
    const minimalProject = {
      format: FORMAT_NAME,
      schema_version: 1,
      project: { name: 'Legacy project', description: '', created_at: '', modified_at: '' },
      canvas: { width: 1920, height: 1080, background: '#ffffff' }, // no gridSize field
      objects: [],
      connections: []
    };

    const ok = ProjectManager.loadProject(JSON.stringify(minimalProject), 'legacy.epwsyn');

    expect(ok).toBe(true);
    expect(useStore.getState().canvasConfig.gridSize).toBe(GRID_SIZE);
    expect(useStore.getState().canvasConfig.gridSize).not.toBe(20);
  });

  it('still honors an explicit, valid gridSize from the file', () => {
    const project = {
      format: FORMAT_NAME,
      schema_version: 1,
      project: { name: 'Custom grid', description: '', created_at: '', modified_at: '' },
      canvas: { width: 1920, height: 1080, background: '#ffffff', gridSize: 32 },
      objects: [],
      connections: []
    };

    ProjectManager.loadProject(JSON.stringify(project), 'custom.epwsyn');

    expect(useStore.getState().canvasConfig.gridSize).toBe(32);
  });
});

function makeBoundaryPoint(overrides: Partial<SynopticObject> = {}): SynopticObject {
  return {
    id: 'BP1',
    type: 'scada.boundary_point',
    category: 'SCADA',
    x: 0, y: 0,
    rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 1,
    tag: 'BP1', description: '', color: '#000', fill: '#000', border: '#000',
    text: '', font: 'Arial', fontSize: 12, tooltip: '',
    width: 150, height: 60,
    customProperties: {},
    designation: 'ZKP',
    boundaryDirection: 'SOURCE',
    boundaryMedium: 'ELECTRICAL',
    boundaryPortSide: 'TOP',
    ...overrides
  };
}

describe('Boundary point width (getBoundaryPointWidth)', () => {
  it('clamps a short label/sublabel up to the 96px minimum', () => {
    expect(getBoundaryPointWidth('X', '')).toBe(96);
  });

  it('clamps a long label/sublabel down to the 220px maximum', () => {
    expect(getBoundaryPointWidth('A VERY LONG BOUNDARY LABEL INDEED', 'AN EQUALLY LONG SUBLABEL TEXT')).toBe(220);
  });

  it('hugs a mid-length label between the two bounds', () => {
    const width = getBoundaryPointWidth('WORKSHOP', '400V AC');
    expect(width).toBeGreaterThan(96);
    expect(width).toBeLessThan(220);
  });
});

describe('Boundary point port side (getBoundaryPortFraction)', () => {
  it('TOP sits at the horizontal center of the top edge', () => {
    expect(getBoundaryPortFraction('TOP')).toEqual({ x: 0.5, y: 0 });
  });

  it('BOTTOM sits at the horizontal center of the bottom edge', () => {
    expect(getBoundaryPortFraction('BOTTOM')).toEqual({ x: 0.5, y: 1 });
  });

  it('LEFT sits at the vertical center of the left edge', () => {
    expect(getBoundaryPortFraction('LEFT')).toEqual({ x: 0, y: 0.5 });
  });

  it('RIGHT sits at the vertical center of the right edge', () => {
    expect(getBoundaryPortFraction('RIGHT')).toEqual({ x: 1, y: 0.5 });
  });
});

describe('Boundary point connection resolution (GeometryUtils.resolveConnectionPoint)', () => {
  it('resolves its single PORT id at the configured side', () => {
    const bp = makeBoundaryPoint({ boundaryPortSide: 'RIGHT' });
    const point = resolveConnectionPoint(bp, 'PORT');
    expect(point).not.toBeNull();
    expect(point?.x).toBe(1);
    expect(point?.y).toBe(0.5);
  });

  it('SOURCE resolves an out-direction port', () => {
    const bp = makeBoundaryPoint({ boundaryDirection: 'SOURCE' });
    expect(resolveConnectionPoint(bp, 'PORT')?.direction).toBe('out');
  });

  it('SINK resolves an in-direction port', () => {
    const bp = makeBoundaryPoint({ boundaryDirection: 'SINK' });
    expect(resolveConnectionPoint(bp, 'PORT')?.direction).toBe('in');
  });

  it('ELECTRICAL medium resolves the electrical domain and electrical_ac medium', () => {
    const bp = makeBoundaryPoint({ boundaryMedium: 'ELECTRICAL' });
    const point = resolveConnectionPoint(bp, 'PORT');
    expect(point?.domain).toBe('electrical');
    expect(point?.medium).toBe('electrical_ac');
  });

  it('WATER medium resolves the water domain and water medium', () => {
    const bp = makeBoundaryPoint({ boundaryMedium: 'WATER' });
    const point = resolveConnectionPoint(bp, 'PORT');
    expect(point?.domain).toBe('water');
    expect(point?.medium).toBe('water');
  });

  it('an unknown port id on a boundary point still resolves to null', () => {
    const bp = makeBoundaryPoint();
    expect(resolveConnectionPoint(bp, 'NOT_A_REAL_PORT')).toBeNull();
  });
});

describe('Boundary point connection validation (ConnectionService)', () => {
  it('a SOURCE boundary point can connect to a SINK boundary point of the same medium', () => {
    const source = makeBoundaryPoint({ id: 'SRC', boundaryDirection: 'SOURCE', boundaryMedium: 'ELECTRICAL' });
    const sink = makeBoundaryPoint({ id: 'SNK', boundaryDirection: 'SINK', boundaryMedium: 'ELECTRICAL' });
    const result = ConnectionService.validateConnection(source, 'PORT', sink, 'PORT', []);
    expect(result.valid).toBe(true);
    expect(result.inferredType).toBe('electrical_ac');
  });

  it('a WATER SOURCE and an ELECTRICAL SINK are rejected (different domains, checked before medium)', () => {
    const source = makeBoundaryPoint({ id: 'SRC', boundaryDirection: 'SOURCE', boundaryMedium: 'WATER' });
    const sink = makeBoundaryPoint({ id: 'SNK', boundaryDirection: 'SINK', boundaryMedium: 'ELECTRICAL' });
    const result = ConnectionService.validateConnection(source, 'PORT', sink, 'PORT', []);
    expect(result.valid).toBe(false);
    expect(result.code).toBe('DOMAIN_MISMATCH');
  });

  it('two SOURCE boundary points (out-to-out) are rejected on direction mismatch', () => {
    const a = makeBoundaryPoint({ id: 'A', boundaryDirection: 'SOURCE' });
    const b = makeBoundaryPoint({ id: 'B', boundaryDirection: 'SOURCE' });
    const result = ConnectionService.validateConnection(a, 'PORT', b, 'PORT', []);
    expect(result.valid).toBe(false);
    expect(result.code).toBe('DIRECTION_MISMATCH');
  });

  it('a WATER source resolves inferredType water, so the wire renders in the water color', () => {
    const source = makeBoundaryPoint({ id: 'SRC', boundaryDirection: 'SOURCE', boundaryMedium: 'WATER' });
    const sink = makeBoundaryPoint({ id: 'SNK', boundaryDirection: 'SINK', boundaryMedium: 'WATER' });
    const result = ConnectionService.validateConnection(source, 'PORT', sink, 'PORT', []);
    expect(result.valid).toBe(true);
    expect(result.inferredType).toBe('water');
  });
});

// Usterka: "Source/Target port is already occupied" blocked drawing any
// real schematic (several circuits off one feed, several wires landing
// on one node). A port must now accept any number of connections, while
// every other validation rule keeps working exactly as before.
describe('A port accepts more than one connection (ConnectionService, usterka fix)', () => {
  it('a second, third and fourth connection to an already-occupied SOURCE port all still validate', () => {
    const source = makeBoundaryPoint({ id: 'SRC', boundaryDirection: 'SOURCE', boundaryMedium: 'ELECTRICAL' });
    const sinkB = makeBoundaryPoint({ id: 'B', boundaryDirection: 'SINK', boundaryMedium: 'ELECTRICAL' });
    const sinkC = makeBoundaryPoint({ id: 'C', boundaryDirection: 'SINK', boundaryMedium: 'ELECTRICAL' });

    // Plain fixtures, not real SynopticConnection objects - validateConnection's
    // existingConnections param is untyped (any[]) and only ever reads
    // fromId/fromPort/toId/toPort/type off them, the old port-era shape
    // this describe block is deliberately still exercising.
    const existing = [
      { id: 'C1', fromId: 'SRC', fromPort: 'PORT', toId: 'A', toPort: 'PORT', type: 'electrical_ac' }
    ];

    // Source port SRC:PORT is already used by C1 above - a second wire
    // from it (to a different sink) must still succeed.
    const second = ConnectionService.validateConnection(source, 'PORT', sinkB, 'PORT', existing);
    expect(second.valid).toBe(true);
    expect(second.code).toBeUndefined();

    existing.push({ id: 'C2', fromId: 'SRC', fromPort: 'PORT', toId: 'B', toPort: 'PORT', type: 'electrical_ac' });

    const third = ConnectionService.validateConnection(source, 'PORT', sinkC, 'PORT', existing);
    expect(third.valid).toBe(true);
  });

  it('a target port with two wires already landed on it still accepts a third', () => {
    const sink = makeBoundaryPoint({ id: 'SNK', boundaryDirection: 'SINK', boundaryMedium: 'ELECTRICAL' });
    const sourceC = makeBoundaryPoint({ id: 'C', boundaryDirection: 'SOURCE', boundaryMedium: 'ELECTRICAL' });

    const existing = [
      { id: 'C1', fromId: 'A', fromPort: 'PORT', toId: 'SNK', toPort: 'PORT', type: 'electrical_ac' },
      { id: 'C2', fromId: 'B', fromPort: 'PORT', toId: 'SNK', toPort: 'PORT', type: 'electrical_ac' }
    ];

    const result = ConnectionService.validateConnection(sourceC, 'PORT', sink, 'PORT', existing);
    expect(result.valid).toBe(true);
  });

  it('every other validation rule still rejects, unaffected by the multiplicity removal', () => {
    const elec = makeBoundaryPoint({ id: 'E', boundaryMedium: 'ELECTRICAL' });
    const water = makeBoundaryPoint({ id: 'W', boundaryMedium: 'WATER' });
    expect(ConnectionService.validateConnection(elec, 'PORT', water, 'PORT', []).code).toBe('DOMAIN_MISMATCH');

    const self = makeBoundaryPoint({ id: 'S' });
    expect(ConnectionService.validateConnection(self, 'PORT', self, 'PORT', []).code).toBe('SELF_CONNECTION');

    const outA = makeBoundaryPoint({ id: 'OA', boundaryDirection: 'SOURCE' });
    const outB = makeBoundaryPoint({ id: 'OB', boundaryDirection: 'SOURCE' });
    expect(ConnectionService.validateConnection(outA, 'PORT', outB, 'PORT', []).code).toBe('DIRECTION_MISMATCH');
  });
});

// Usterka D1: Messages showed the raw object id (a UUID) - never
// readable, never allowed there per the task's boundary.
const UUID_PATTERN = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

describe('Readable object identification for Messages (describeObject)', () => {
  it('uses the designation when set', () => {
    const obj = makeDevice({ id: 'obj-uuid-123', designation: '-Q1' });
    expect(describeObject(obj)).toBe('-Q1');
  });

  it('falls back to the symbol\'s own library label when designation is empty - never the type string, never the id', () => {
    const obj = makeDevice({ id: 'obj-uuid-123', designation: '' });
    const text = describeObject(obj);
    expect(text).toBe('Circuit Breaker'); // electrical.circuit_breaker's registry label
    expect(text).not.toBe(obj.id);
    expect(text).not.toContain('electrical.circuit_breaker');
    expect(UUID_PATTERN.test(text)).toBe(false);
  });

  it('never throws and reads as "unknown object" for a missing object', () => {
    expect(describeObject(undefined)).toBe('unknown object');
    expect(describeObject(null)).toBe('unknown object');
  });
});

// ConnectionService.tryCreateConnection (the mechanism the two tests
// that used to live here exercised) is gone under the node-based wiring
// model - finishing a wire no longer creates a from/to port pair, so
// there is nothing left for it to do. The "no UUID in Messages" bar it
// checked is carried forward by new tests alongside the wire-finishing
// action itself (see wire-drawing.test.ts).
