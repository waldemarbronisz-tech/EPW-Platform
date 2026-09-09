// feat/wire-routing-around-obstacles commit 3 - the 7 mandatory tests
// for wiring the router into wire drawing (Canvas.tsx). Points 17/18
// exercise the exact same pipeline Canvas.tsx's own OMIJAJ-mode
// handleMouseDown/commitWire composes (attachAnchorsToNewPoints +
// getObstacles + routeAround + findCollisions) rather than simulating
// a Konva mouse event - the underlying pure functions are what this
// task's own GRANICE lets a test reach directly, same convention every
// other commit in this codebase's history already uses. Points 19-23
// exercise the store directly (isManualRoute, recalculateConnectionRoutes,
// history, and the project-file round-trip) - the same level
// anchor-terminal-consistency.test.ts's own store-driven tests already
// operate at.

import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import type { SynopticObject } from '../store';
import { GRID_SIZE } from '../theme/ScadaTheme';
import { getObstacles } from '../project/WireCollision';
import { routeAround } from '../project/WireRouter';
import { findCollisions } from '../project/WireCollision';
import { attachAnchorsToNewPoints } from '../utils/WireAnchoring';
import { getObjectTerminals, getTerminalWorldPosition } from '../utils/Terminals';
import { ProjectManager } from '../project/ProjectManager';

function valve(id: string, x: number): SynopticObject {
  return {
    id, type: 'site.check_valve', category: 'Water',
    x, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 0,
    tag: '', description: '', color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
    customProperties: {}, width: 128, height: 96
  } as SynopticObject;
}

function inTheWay(id: string): SynopticObject {
  return {
    id, type: 'electrical.circuit_breaker', category: 'Electrical',
    x: 200, y: 16, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 0,
    tag: '', description: '', color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
    customProperties: {}, width: 64, height: 64
  } as SynopticObject;
}

function worldTerminal(obj: SynopticObject, terminalId: string) {
  const t = getObjectTerminals(obj).find(t => t.id === terminalId)!;
  return getTerminalWorldPosition(obj, t);
}

describe('17. in OMIJAJ mode, a wire drawn between two valves with an obstacle between them does not collide', () => {
  it('routeAround finds a path around the breaker sitting between them', () => {
    const vA = valve('vA', 0);
    const vB = valve('vB', 400);
    const obstacleObj = inTheWay('mid');
    const objects = [vA, vB, obstacleObj];

    const start = worldTerminal(vA, 'WYLOT'); // (128, 48)
    const end = worldTerminal(vB, 'WLOT');    // (400, 48)

    // Exactly what Canvas.tsx's own OMIJAJ handleMouseDown computes:
    // exclude the two valves this wire is itself anchored to, route
    // around everything else.
    const obstacles = getObstacles({ objects }, [vA.id, vB.id]);
    const routed = routeAround(start, end, obstacles, GRID_SIZE);
    const points = attachAnchorsToNewPoints(routed, objects);
    const wire = { id: 'w', medium: 'WATER' as const, style: 'NORMAL' as const, points };

    expect(findCollisions(wire, obstacles)).toEqual([]);
    expect(points[0].anchor).toEqual({ symbolId: 'vA', terminalId: 'WYLOT' });
    expect(points[points.length - 1].anchor).toEqual({ symbolId: 'vB', terminalId: 'WLOT' });
  });
});

describe('18. the same wire, drawn PROSTO (straight, no routing), does collide', () => {
  it('a plain two-point wire between the same two terminals crosses the breaker', () => {
    const vA = valve('vA', 0);
    const vB = valve('vB', 400);
    const obstacleObj = inTheWay('mid');
    const objects = [vA, vB, obstacleObj];

    const start = worldTerminal(vA, 'WYLOT');
    const end = worldTerminal(vB, 'WLOT');
    const obstacles = getObstacles({ objects }, [vA.id, vB.id]);

    const straightWire = { id: 'w', medium: 'WATER' as const, style: 'NORMAL' as const, points: [start, end] };
    expect(findCollisions(straightWire, obstacles).length).toBeGreaterThan(0);
  });
});

function resetStoreForRouting(objects: SynopticObject[], connections: any[]) {
  useStore.setState({
    objects, connections, messages: [],
    selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [],
    selectedFrameIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: [],
    meters: [], signalPanels: [], frames: [], groupCommands: [], setpointPanels: []
  });
}

describe('19. placing your own bend marks a wire as manual', () => {
  beforeEach(() => resetStoreForRouting([], []));

  it('updateConnection with isManualRoute:true (exactly what Canvas.tsx\'s Alt+click handler does) sets the flag', () => {
    const conn = { id: 'c1', medium: 'ELECTRICAL' as const, style: 'NORMAL' as const, points: [{ x: 0, y: 0 }, { x: 160, y: 0 }] };
    useStore.setState({ connections: [conn] });
    useStore.getState().updateConnection('c1', { points: [{ x: 0, y: 0 }, { x: 80, y: 0 }, { x: 80, y: 32 }, { x: 160, y: 32 }], isManualRoute: true });
    expect(useStore.getState().connections[0].isManualRoute).toBe(true);
  });
});

describe('20. a manual wire is never recalculated by the router', () => {
  beforeEach(() => resetStoreForRouting([], []));

  it('recalculateConnectionRoutes leaves a manual connection\'s points untouched', () => {
    const originalPoints = [{ x: 0, y: 0 }, { x: 160, y: 0 }];
    const conn = { id: 'c1', medium: 'ELECTRICAL' as const, style: 'NORMAL' as const, points: originalPoints, isManualRoute: true };
    useStore.setState({ connections: [conn] });
    useStore.getState().recalculateConnectionRoutes(['c1']);
    expect(useStore.getState().connections[0].points).toEqual(originalPoints);
  });
});

describe('21. moving an apparatus never recalculates a route on its own', () => {
  beforeEach(() => resetStoreForRouting([], []));

  it('saveHistory (the one hook point every move goes through) never touches a wire\'s own points just because an object moved into its path', () => {
    const mover = inTheWay('m1');
    const conn = { id: 'c1', medium: 'ELECTRICAL' as const, style: 'NORMAL' as const, points: [{ x: 0, y: 48 }, { x: 400, y: 48 }] };
    resetStoreForRouting([mover], [conn]);
    const before = JSON.stringify(useStore.getState().connections[0].points);

    // Move the object so the existing wire now collides with it - this
    // is a deliberate consequence (point (e)): the wire keeps its own
    // shape, it is only flagged, never reshaped, by a move.
    useStore.getState().updateObject('m1', { x: 100 });
    useStore.getState().saveHistory();

    const after = JSON.stringify(useStore.getState().connections[0].points);
    expect(after).toBe(before);
  });
});

describe('22. PRZELICZ TRASE changes a selected wire\'s shape and creates exactly one history entry', () => {
  beforeEach(() => resetStoreForRouting([], []));

  it('a straight, colliding wire is reshaped around the obstacle, in one saveHistory call', () => {
    const obstacleObj = inTheWay('mid'); // x:200-264, y:16-80
    const conn = { id: 'c1', medium: 'ELECTRICAL' as const, style: 'NORMAL' as const, points: [{ x: 0, y: 48 }, { x: 400, y: 48 }] };
    resetStoreForRouting([obstacleObj], [conn]);
    useStore.getState().saveHistory(); // establish a clean baseline entry first
    const historyLengthBefore = useStore.getState().history.length;

    useStore.getState().recalculateConnectionRoutes(['c1']);

    const newPoints = useStore.getState().connections[0].points;
    expect(newPoints.length).toBeGreaterThan(2); // no longer the plain 2-point straight line
    const obstacles = getObstacles({ objects: [obstacleObj] });
    expect(findCollisions({ id: 'c1', medium: 'ELECTRICAL', style: 'NORMAL', points: newPoints }, obstacles)).toEqual([]);
    expect(useStore.getState().history.length).toBe(historyLengthBefore + 1);
  });
});

describe('23. the routing mode never reaches the saved project file', () => {
  it('ProjectManager.getProjectData\'s own JSON never mentions wireRoutingMode, whichever mode is currently armed', () => {
    useStore.getState().setWireRoutingMode('STRAIGHT');
    const json = ProjectManager.getProjectData();
    expect(json).not.toBeNull();
    expect(json).not.toContain('wireRoutingMode');
    useStore.getState().setWireRoutingMode('AVOID');
  });
});
