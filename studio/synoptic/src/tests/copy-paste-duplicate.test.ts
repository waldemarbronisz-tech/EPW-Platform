// feat/editing-and-signal-panel commit 2: Ctrl+C/Ctrl+V/Ctrl+D and
// Alt-drag-in-place, all through the store directly (the same
// convention every other feature in this codebase is tested with -
// no simulated mouse/keyboard events, just the store actions
// themselves).

import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import { resolveNets } from '../project/NetResolver';
import { GRID_SIZE } from '../theme/ScadaTheme';
import type { SynopticObject } from '../store';

function makeCircuitBreaker(id: string, x: number, y: number): SynopticObject {
  return {
    id, type: 'electrical.circuit_breaker', category: 'Electrical',
    x, y, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 1,
    tag: id, description: '', color: '#000', fill: '#000', border: '#000',
    text: '', font: 'Arial', fontSize: 12, tooltip: '',
    width: 64, height: 64, customProperties: {}
  };
  // electrical.circuit_breaker (64x64, per commit 1): IN terminal at
  // (32,0) TOP, OUT at (32,64) BOTTOM.
}

function resetStore() {
  useStore.setState({
    objects: [], connections: [], meters: [],
    selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [],
    clipboard: [], clipboardMeters: [], clipboardConnections: [],
    history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [] }],
    historyIndex: 0
  });
}

describe('Copy and paste', () => {
  beforeEach(resetStore);

  // 4. pasting a copy offsets it by one grid cell
  it('pasting offsets the copy by exactly one grid cell right and down', () => {
    useStore.setState({ objects: [makeCircuitBreaker('A', 100, 200)] });
    useStore.getState().selectObjects(['A'], false);

    useStore.getState().copySelected();
    useStore.getState().paste();

    const objects = useStore.getState().objects;
    expect(objects.length).toBe(2);
    const pasted = objects.find(o => o.id !== 'A')!;
    expect(pasted.x).toBe(100 + GRID_SIZE);
    expect(pasted.y).toBe(200 + GRID_SIZE);
  });

  it('paste does not touch the original at all', () => {
    useStore.setState({ objects: [makeCircuitBreaker('A', 100, 200)] });
    useStore.getState().selectObjects(['A'], false);
    useStore.getState().copySelected();
    useStore.getState().paste();

    const original = useStore.getState().objects.find(o => o.id === 'A')!;
    expect(original.x).toBe(100);
    expect(original.y).toBe(200);
  });

  it('the pasted copy becomes the new selection', () => {
    useStore.setState({ objects: [makeCircuitBreaker('A', 0, 0)] });
    useStore.getState().selectObjects(['A'], false);
    useStore.getState().copySelected();
    useStore.getState().paste();

    const pastedId = useStore.getState().objects.find(o => o.id !== 'A')!.id;
    expect(useStore.getState().selectedIds).toEqual([pastedId]);
  });

  // 5. a copied fragment with two symbols and a connection between them
  // keeps that connection - and does not connect to the original.
  it('copying two connected symbols and their wire preserves the connection in the copy, separately from the original', () => {
    const a = makeCircuitBreaker('A', 0, 0);       // OUT at world (32, 64)
    const b = makeCircuitBreaker('B', 0, 128);      // IN at world (32, 128)
    const wire = {
      id: 'W', points: [{ x: 32, y: 64 }, { x: 32, y: 128 }],
      medium: 'ELECTRICAL' as const, style: 'NORMAL' as const, state: 'LIVE' as const
    };
    useStore.setState({ objects: [a, b], connections: [wire] });
    useStore.getState().selectObjects(['A', 'B'], false);
    useStore.setState({ selectedConnectionIds: ['W'] }); // a mixed selection - see store.ts's copySelected comment

    useStore.getState().copySelected();
    useStore.getState().paste();

    const state = useStore.getState();
    expect(state.objects.length).toBe(4); // A, B and their two pasted copies
    expect(state.connections.length).toBe(2); // the original wire W, plus its pasted copy

    // Two SEPARATE nets now - the untouched original (A-W-B, exactly
    // where it always was) and the pasted copy (its own wire touching
    // only its own two pasted objects) - not one net merging all four
    // objects together, which is exactly what "does not connect to the
    // original" means geometrically in this node-based model.
    const nets = resolveNets(state.connections, state.objects);
    expect(nets.length).toBe(2);
    nets.forEach(net => expect(net.terminals.length).toBe(2));

    const pastedA = state.objects.find(o => o.type === 'electrical.circuit_breaker' && o.id !== 'A' && o.y === GRID_SIZE)!;
    const pastedB = state.objects.find(o => o.type === 'electrical.circuit_breaker' && o.id !== 'B' && o.y === 128 + GRID_SIZE)!;
    const pastedNet = nets.find(n => n.terminals.some(t => t.objId === pastedA.id))!;
    expect(pastedNet.terminals.map(t => t.objId).sort()).toEqual([pastedA.id, pastedB.id].sort());

    const originalNet = nets.find(n => n.terminals.some(t => t.objId === 'A'))!;
    expect(originalNet.terminals.map(t => t.objId).sort()).toEqual(['A', 'B']);
  });
});

describe('Duplicate (Ctrl+D)', () => {
  beforeEach(resetStore);

  it('duplicates the current selection with the same grid offset as paste, without touching the clipboard', () => {
    useStore.setState({ objects: [makeCircuitBreaker('A', 50, 50)] });
    useStore.getState().selectObjects(['A'], false);

    useStore.getState().duplicateSelected();

    const objects = useStore.getState().objects;
    expect(objects.length).toBe(2);
    const dup = objects.find(o => o.id !== 'A')!;
    expect(dup.x).toBe(50 + GRID_SIZE);
    expect(dup.y).toBe(50 + GRID_SIZE);
    expect(useStore.getState().clipboard).toEqual([]); // never copied - clipboard stays empty
  });

  it('duplicate selects the new copy, not the original', () => {
    useStore.setState({ objects: [makeCircuitBreaker('A', 0, 0)] });
    useStore.getState().selectObjects(['A'], false);
    useStore.getState().duplicateSelected();

    const dupId = useStore.getState().objects.find(o => o.id !== 'A')!.id;
    expect(useStore.getState().selectedIds).toEqual([dupId]);
  });
});

describe('Alt-drag duplicate-in-place', () => {
  beforeEach(resetStore);

  it('duplicateObjectInPlace leaves a copy at the exact same position, selection untouched', () => {
    useStore.setState({ objects: [makeCircuitBreaker('A', 40, 60)] });
    useStore.getState().selectObjects(['A'], false);

    useStore.getState().duplicateObjectInPlace('A');

    const objects = useStore.getState().objects;
    expect(objects.length).toBe(2);
    const clone = objects.find(o => o.id !== 'A')!;
    expect(clone.x).toBe(40);
    expect(clone.y).toBe(60);
    // Selection is untouched by the clone itself - it still points at
    // the original, which is what the ongoing drag keeps moving.
    expect(useStore.getState().selectedIds).toEqual(['A']);
  });

  it('duplicateMeterInPlace does the same for a meter', () => {
    useStore.getState().addMeter({ x: 10, y: 20, width: 200, fontSize: 12, rows: [] });
    const id = useStore.getState().meters[0].id;

    useStore.getState().duplicateMeterInPlace(id);

    const meters = useStore.getState().meters;
    expect(meters.length).toBe(2);
    const clone = meters.find(m => m.id !== id)!;
    expect(clone.x).toBe(10);
    expect(clone.y).toBe(20);
  });
});

describe('Each copy/paste/duplicate operation is one history entry', () => {
  beforeEach(resetStore);

  it('paste adds exactly one history entry', () => {
    useStore.setState({ objects: [makeCircuitBreaker('A', 0, 0)] });
    useStore.getState().selectObjects(['A'], false);
    useStore.getState().copySelected();

    const before = useStore.getState().history.length;
    useStore.getState().paste();
    expect(useStore.getState().history.length).toBe(before + 1);
  });

  it('duplicateSelected adds exactly one history entry', () => {
    useStore.setState({ objects: [makeCircuitBreaker('A', 0, 0)] });
    useStore.getState().selectObjects(['A'], false);

    const before = useStore.getState().history.length;
    useStore.getState().duplicateSelected();
    expect(useStore.getState().history.length).toBe(before + 1);
  });
});
