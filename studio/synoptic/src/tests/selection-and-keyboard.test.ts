// feat/editing-and-signal-panel commit 3: rubber-band containment
// (pure functions, no Konva/mouse simulation needed) and the store
// actions the keyboard shortcuts call directly - the same "test the
// store action, not the DOM event" convention every other keyboard
// shortcut in this codebase already follows.

import { describe, it, expect, beforeEach } from 'vitest';
import { isObjectFullyInBox, isMeterFullyInBox, isConnectionFullyInBox } from '../utils/SelectionBox';
import { useStore } from '../store';
import { GRID_SIZE } from '../theme/ScadaTheme';
import type { SynopticObject } from '../store';

function makeObj(id: string, x: number, y: number, width = 64, height = 64): SynopticObject {
  return {
    id, type: 'electrical.circuit_breaker', category: 'Electrical',
    x, y, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 1,
    tag: id, description: '', color: '#000', fill: '#000', border: '#000',
    text: '', font: 'Arial', fontSize: 12, tooltip: '',
    width, height, customProperties: {}
  };
}

function resetStore() {
  useStore.setState({
    objects: [], connections: [], meters: [],
    selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [],
    history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [] }],
    historyIndex: 0
  });
}

describe('Rubber-band containment (isObjectFullyInBox etc.)', () => {
  const box = { x: 0, y: 0, width: 200, height: 200 };

  // 6. an element lying ENTIRELY inside the box is selected; one
  // poking out past the box's edge is NOT.
  it('selects an object lying entirely within the box', () => {
    expect(isObjectFullyInBox(makeObj('A', 10, 10, 64, 64), box)).toBe(true);
  });

  it('does not select an object poking out past the box edge', () => {
    // right edge at 10+64+150=224, past the box's own right edge (200)
    expect(isObjectFullyInBox(makeObj('A', 150, 10, 64, 64), box)).toBe(false);
  });

  it('does not select an object straddling the box entirely (starts before, ends after)', () => {
    expect(isObjectFullyInBox(makeObj('A', -50, 10, 300, 64), box)).toBe(false);
  });

  it('applies the same entirely-inside rule to meters, using their computed height', () => {
    expect(isMeterFullyInBox({ x: 10, y: 10, width: 150 }, 50, box)).toBe(true);
    expect(isMeterFullyInBox({ x: 10, y: 10, width: 150 }, 300, box)).toBe(false); // pokes out the bottom
  });

  it('applies the same entirely-inside rule to a connection - every point must be inside', () => {
    expect(isConnectionFullyInBox({ points: [{ x: 10, y: 10 }, { x: 190, y: 190 }] }, box)).toBe(true);
    expect(isConnectionFullyInBox({ points: [{ x: 10, y: 10 }, { x: 250, y: 10 }] }, box)).toBe(false);
  });
});

describe('Selection across kinds (Shift+click, Ctrl+A, Escape)', () => {
  beforeEach(resetStore);

  it('a plain (non-Shift) selectObjects call replaces the whole selection, clearing other kinds', () => {
    useStore.setState({ selectedConnectionIds: ['W1'], selectedMeterIds: ['M1'] });
    useStore.getState().selectObjects(['A'], false);
    expect(useStore.getState().selectedIds).toEqual(['A']);
    expect(useStore.getState().selectedConnectionIds).toEqual([]);
    expect(useStore.getState().selectedMeterIds).toEqual([]);
  });

  it('a Shift (multi) selectObjects call leaves other kinds untouched - a mixed selection is possible', () => {
    useStore.setState({ selectedConnectionIds: ['W1'], selectedMeterIds: ['M1'] });
    useStore.getState().selectObjects(['A'], true);
    expect(useStore.getState().selectedIds).toEqual(['A']);
    expect(useStore.getState().selectedConnectionIds).toEqual(['W1']);
    expect(useStore.getState().selectedMeterIds).toEqual(['M1']);
  });

  it('Shift+click toggles: clicking an already-selected object again removes it', () => {
    useStore.getState().selectObjects(['A'], false);
    useStore.getState().selectObjects(['A'], true);
    expect(useStore.getState().selectedIds).toEqual([]);
  });

  it('selectMixed replaces the whole selection across all three kinds at once', () => {
    useStore.getState().selectMixed({ objectIds: ['A', 'B'], connectionIds: ['W1'], meterIds: ['M1'] });
    expect(useStore.getState().selectedIds).toEqual(['A', 'B']);
    expect(useStore.getState().selectedConnectionIds).toEqual(['W1']);
    expect(useStore.getState().selectedMeterIds).toEqual(['M1']);
  });

  it('selectAll selects every object, connection and meter currently in the project', () => {
    useStore.setState({
      objects: [makeObj('A', 0, 0), makeObj('B', 100, 100)],
      connections: [{ id: 'W1', points: [{ x: 0, y: 0 }, { x: 16, y: 0 }], medium: 'ELECTRICAL', style: 'NORMAL', state: 'LIVE' }],
      meters: []
    });
    useStore.getState().addMeter({ x: 0, y: 0, width: 200, fontSize: 12, rows: [] });

    useStore.getState().selectAll();

    expect(useStore.getState().selectedIds.sort()).toEqual(['A', 'B']);
    expect(useStore.getState().selectedConnectionIds).toEqual(['W1']);
    expect(useStore.getState().selectedMeterIds.length).toBe(1);
  });

  it('clearSelection empties all three kinds at once', () => {
    useStore.getState().selectMixed({ objectIds: ['A'], connectionIds: ['W1'], meterIds: ['M1'] });
    useStore.getState().clearSelection();
    expect(useStore.getState().selectedIds).toEqual([]);
    expect(useStore.getState().selectedConnectionIds).toEqual([]);
    expect(useStore.getState().selectedMeterIds).toEqual([]);
  });
});

describe('Delete/Backspace removes the selection', () => {
  beforeEach(resetStore);

  it('deleteObjects with the current mixed selection removes everything selected', () => {
    useStore.setState({
      objects: [makeObj('A', 0, 0)],
      connections: [{ id: 'W1', points: [{ x: 0, y: 0 }, { x: 16, y: 0 }], medium: 'ELECTRICAL', style: 'NORMAL', state: 'LIVE' }]
    });
    useStore.getState().addMeter({ x: 0, y: 0, width: 200, fontSize: 12, rows: [] });
    const meterId = useStore.getState().meters[0].id;
    useStore.getState().selectMixed({ objectIds: ['A'], connectionIds: ['W1'], meterIds: [meterId] });

    const s = useStore.getState();
    s.deleteObjects(s.selectedIds, s.selectedConnectionIds, s.selectedMeterIds);

    expect(useStore.getState().objects).toEqual([]);
    expect(useStore.getState().connections).toEqual([]);
    expect(useStore.getState().meters).toEqual([]);
  });
});

describe('Arrow-key movement (moveSelectionBy)', () => {
  beforeEach(resetStore);

  // 7. an arrow press moves the selection by GRID_SIZE, by 10x with Shift
  it('moves the selected object by exactly GRID_SIZE', () => {
    useStore.setState({ objects: [makeObj('A', 100, 100)] });
    useStore.getState().selectObjects(['A'], false);

    useStore.getState().moveSelectionBy(GRID_SIZE, 0);

    expect(useStore.getState().objects[0].x).toBe(100 + GRID_SIZE);
    expect(useStore.getState().objects[0].y).toBe(100);
  });

  it('moves the selected object by 10x GRID_SIZE when the Shift step is used', () => {
    useStore.setState({ objects: [makeObj('A', 100, 100)] });
    useStore.getState().selectObjects(['A'], false);

    useStore.getState().moveSelectionBy(0, GRID_SIZE * 10);

    expect(useStore.getState().objects[0].y).toBe(100 + GRID_SIZE * 10);
  });

  it('skips a locked object', () => {
    useStore.setState({ objects: [{ ...makeObj('A', 100, 100), locked: true }] });
    useStore.getState().selectObjects(['A'], false);

    useStore.getState().moveSelectionBy(GRID_SIZE, 0);

    expect(useStore.getState().objects[0].x).toBe(100);
  });

  it('moves a selected meter and a selected connection together with a selected object', () => {
    useStore.setState({
      objects: [makeObj('A', 0, 0)],
      connections: [{ id: 'W1', points: [{ x: 0, y: 0 }, { x: 16, y: 0 }], medium: 'ELECTRICAL', style: 'NORMAL', state: 'LIVE' }]
    });
    useStore.getState().addMeter({ x: 0, y: 0, width: 200, fontSize: 12, rows: [] });
    const meterId = useStore.getState().meters[0].id;
    useStore.getState().selectMixed({ objectIds: ['A'], connectionIds: ['W1'], meterIds: [meterId] });

    useStore.getState().moveSelectionBy(GRID_SIZE, GRID_SIZE);

    expect(useStore.getState().objects[0].x).toBe(GRID_SIZE);
    expect(useStore.getState().meters[0].x).toBe(GRID_SIZE);
    expect(useStore.getState().connections[0].points).toEqual([{ x: GRID_SIZE, y: GRID_SIZE }, { x: 16 + GRID_SIZE, y: GRID_SIZE }]);
  });

  it('moveSelectionBy is exactly one history entry per call', () => {
    useStore.setState({ objects: [makeObj('A', 0, 0)] });
    useStore.getState().selectObjects(['A'], false);

    const before = useStore.getState().history.length;
    useStore.getState().moveSelectionBy(GRID_SIZE, 0);
    expect(useStore.getState().history.length).toBe(before + 1);

    useStore.getState().moveSelectionBy(GRID_SIZE, 0);
    expect(useStore.getState().history.length).toBe(before + 2);
  });

  it('does nothing (no history entry) when nothing is selected', () => {
    const before = useStore.getState().history.length;
    useStore.getState().moveSelectionBy(GRID_SIZE, 0);
    expect(useStore.getState().history.length).toBe(before);
  });
});
