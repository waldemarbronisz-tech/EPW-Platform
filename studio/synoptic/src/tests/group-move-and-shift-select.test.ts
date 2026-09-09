// feat/appearance-selection-frames commit 2: rubber-band selection and
// group move. Tests 4/5/6/7/9 from this task's own mandatory list were
// already covered before this commit by selection-and-keyboard.test.ts
// (feat/editing-and-signal-panel commit 3, which first built the
// rubber-band/moveSelectionBy machinery this commit reuses for a mouse
// drag) - see that file's "Rubber-band containment" and "Arrow-key
// movement" describe blocks. This file adds the two that were not yet
// covered by a dedicated, explicit assertion: test 8 (moving a group
// of three preserves their PAIRWISE relative distances, not just "the
// same delta from a shared origin" - the two are equivalent, but a
// distance check is the more direct proof) and test 10 (Shift+drag
// adds to the existing selection instead of replacing it).
//
// The live group-drag interaction itself (grab any selected element,
// the whole group visually follows) has no Konva rendering harness to
// test against (same as every other rendering-only piece of this
// codebase - see raport.md) and was verified empirically in a running
// browser instead; what IS tested here is the two pure/store pieces
// that interaction is actually built on: moveSelectionBy (already
// existed, reused as-is) and mergeSelectionAdditive (new, extracted
// out of Canvas.tsx's own handleMouseUp for exactly this purpose).

import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import { mergeSelectionAdditive } from '../utils/SelectionBox';
import { GRID_SIZE } from '../theme/ScadaTheme';
import type { SynopticObject } from '../store';

function makeObj(id: string, x: number, y: number): SynopticObject {
  return {
    id, type: 'electrical.circuit_breaker', category: 'Electrical',
    x, y, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 1,
    tag: id, description: '', color: '#000', fill: '#000', border: '#000',
    text: '', font: 'Arial', fontSize: 12, tooltip: '',
    width: 64, height: 64, customProperties: {}
  };
}

function resetStore() {
  useStore.setState({
    objects: [], connections: [], meters: [], signalPanels: [],
    selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [],
    history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [] }],
    historyIndex: 0
  });
}

// 8. moving a group of three preserves their relative distances
describe('Group move preserves relative distances (moveSelectionBy)', () => {
  beforeEach(resetStore);

  it('three objects at distinct, unaligned positions keep every pairwise distance unchanged after a group move', () => {
    useStore.setState({
      objects: [makeObj('A', 0, 0), makeObj('B', 300, 50), makeObj('C', 120, 400)]
    });
    useStore.getState().selectObjects(['A', 'B', 'C'], false);

    const before = useStore.getState().objects;
    const distance = (p: SynopticObject, q: SynopticObject) => Math.hypot(p.x - q.x, p.y - q.y);
    const distAB = distance(before.find(o => o.id === 'A')!, before.find(o => o.id === 'B')!);
    const distBC = distance(before.find(o => o.id === 'B')!, before.find(o => o.id === 'C')!);
    const distAC = distance(before.find(o => o.id === 'A')!, before.find(o => o.id === 'C')!);

    useStore.getState().moveSelectionBy(160, 96); // an arbitrary, non-trivial drag delta

    const after = useStore.getState().objects;
    const a = after.find(o => o.id === 'A')!, b = after.find(o => o.id === 'B')!, c = after.find(o => o.id === 'C')!;
    expect(distance(a, b)).toBeCloseTo(distAB, 9);
    expect(distance(b, c)).toBeCloseTo(distBC, 9);
    expect(distance(a, c)).toBeCloseTo(distAC, 9);
    // and every one of them actually moved by the same delta
    expect(a.x).toBe(0 + 160); expect(a.y).toBe(0 + 96);
    expect(b.x).toBe(300 + 160); expect(b.y).toBe(50 + 96);
    expect(c.x).toBe(120 + 160); expect(c.y).toBe(400 + 96);
  });

  it('the group move of three is exactly one history entry, same as a single-element move', () => {
    useStore.setState({ objects: [makeObj('A', 0, 0), makeObj('B', 300, 50), makeObj('C', 120, 400)] });
    useStore.getState().selectObjects(['A', 'B', 'C'], false);

    const before = useStore.getState().history.length;
    useStore.getState().moveSelectionBy(GRID_SIZE, GRID_SIZE);
    expect(useStore.getState().history.length).toBe(before + 1);
  });
});

// 10. Shift+drag adds to the existing selection instead of replacing it
describe('mergeSelectionAdditive (Shift+drag rubber-band)', () => {
  it('adds newly-found ids to an existing selection, per kind, without dropping what was already selected', () => {
    const existing = { objectIds: ['A'], connectionIds: ['W1'], meterIds: [], signalPanelIds: ['P1'], frameIds: [], groupCommandIds: [], setpointPanelIds: [] };
    const found = { objectIds: ['B', 'C'], connectionIds: [], meterIds: ['M1'], signalPanelIds: [] };

    const merged = mergeSelectionAdditive(existing, found);

    expect(merged.objectIds.sort()).toEqual(['A', 'B', 'C']);
    expect(merged.connectionIds).toEqual(['W1']);
    expect(merged.meterIds).toEqual(['M1']);
    expect(merged.signalPanelIds).toEqual(['P1']);
  });

  it('never duplicates an id already in both the existing selection and the newly-found set', () => {
    const existing = { objectIds: ['A', 'B'], connectionIds: [], meterIds: [], signalPanelIds: [], frameIds: [], groupCommandIds: [], setpointPanelIds: [] };
    const found = { objectIds: ['B', 'C'], connectionIds: [], meterIds: [], signalPanelIds: [] };

    const merged = mergeSelectionAdditive(existing, found);

    expect(merged.objectIds.sort()).toEqual(['A', 'B', 'C']);
  });

  it('an empty found set (the box enclosed nothing new) leaves the existing selection exactly as it was', () => {
    const existing = { objectIds: ['A'], connectionIds: ['W1'], meterIds: ['M1'], signalPanelIds: ['P1'], frameIds: ['F1'], groupCommandIds: [], setpointPanelIds: [] };

    const merged = mergeSelectionAdditive(existing, {});

    expect(merged).toEqual(existing);
  });

  it('drives selectMixed the same way Canvas.tsx\'s own Shift+drag handler does, end to end through the store', () => {
    useStore.setState({
      objects: [], connections: [], meters: [], signalPanels: [],
      selectedIds: ['A'], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [],
      history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [] }],
      historyIndex: 0
    });

    const merged = mergeSelectionAdditive(
      { objectIds: useStore.getState().selectedIds, connectionIds: useStore.getState().selectedConnectionIds, meterIds: useStore.getState().selectedMeterIds, signalPanelIds: useStore.getState().selectedSignalPanelIds, frameIds: [], groupCommandIds: [], setpointPanelIds: [] },
      { objectIds: ['B'] }
    );
    useStore.getState().selectMixed(merged);

    expect(useStore.getState().selectedIds.sort()).toEqual(['A', 'B']);
  });
});
