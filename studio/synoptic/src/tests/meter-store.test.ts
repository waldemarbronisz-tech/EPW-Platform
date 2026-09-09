// feat/meter-element part A: the meter behaves like any other element -
// place, select, move, copy, delete. Store-level regression coverage,
// same pattern as store.test.ts already uses for objects.

import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import { GRID_SIZE } from '../theme/ScadaTheme';

describe('Meter element - place/select/move/copy/delete', () => {
  beforeEach(() => {
    useStore.setState({
      objects: [], connections: [], meters: [],
      selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [],
      clipboard: [], clipboardMeters: [],
      history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [] }],
      historyIndex: 0
    });
  });

  it('addMeter places a meter and gives it an id', () => {
    useStore.getState().addMeter({ x: 100, y: 100, width: 200, fontSize: 12, rows: [] });
    const meters = useStore.getState().meters;
    expect(meters.length).toBe(1);
    expect(typeof meters[0].id).toBe('string');
    expect(meters[0].id.length).toBeGreaterThan(0);
  });

  it('selectMeters selects a meter and clears object/connection selection', () => {
    useStore.getState().addMeter({ x: 0, y: 0, width: 200, fontSize: 12, rows: [] });
    const id = useStore.getState().meters[0].id;
    useStore.setState({ selectedIds: ['fake-obj'], selectedConnectionIds: ['fake-conn'] });

    useStore.getState().selectMeters([id], false);

    expect(useStore.getState().selectedMeterIds).toEqual([id]);
    expect(useStore.getState().selectedIds).toEqual([]);
    expect(useStore.getState().selectedConnectionIds).toEqual([]);
  });

  it('updateMeter moves a meter (drag) by changing x/y', () => {
    useStore.getState().addMeter({ x: 0, y: 0, width: 200, fontSize: 12, rows: [] });
    const id = useStore.getState().meters[0].id;

    useStore.getState().updateMeter(id, { x: 160, y: 240 });

    const moved = useStore.getState().meters[0];
    expect(moved.x).toBe(160);
    expect(moved.y).toBe(240);
  });

  it('copySelected + paste duplicates a selected meter at an offset, with a new id', () => {
    useStore.getState().addMeter({ x: 50, y: 60, width: 200, title: 'M1', fontSize: 12, rows: [] });
    const id = useStore.getState().meters[0].id;
    useStore.getState().selectMeters([id], false);

    useStore.getState().copySelected();
    useStore.getState().paste();

    const meters = useStore.getState().meters;
    expect(meters.length).toBe(2);
    const pasted = meters.find(m => m.id !== id)!;
    expect(pasted).toBeTruthy();
    // feat/editing-and-signal-panel commit 2: paste now offsets by
    // exactly one grid cell (GRID_SIZE) for every pasteable element,
    // meters included - this replaces the earlier, meter-element-task
    // era hardcoded +20px offset (a generic store.ts clipboard detail,
    // not part of the meter element's own behavior, so updating this
    // expectation does not run afoul of "do not change meter behavior").
    expect(pasted.x).toBe(50 + GRID_SIZE);
    expect(pasted.y).toBe(60 + GRID_SIZE);
    expect(pasted.title).toBe('M1');
    expect(useStore.getState().selectedMeterIds).toEqual([pasted.id]);
  });

  it('deleteObjects with a meter id removes that meter and its selection', () => {
    useStore.getState().addMeter({ x: 0, y: 0, width: 200, fontSize: 12, rows: [] });
    const id = useStore.getState().meters[0].id;
    useStore.getState().selectMeters([id], false);

    useStore.getState().deleteObjects([], [], [id]);

    expect(useStore.getState().meters.length).toBe(0);
    expect(useStore.getState().selectedMeterIds).toEqual([]);
  });

  it('undo restores a deleted meter', () => {
    useStore.getState().addMeter({ x: 0, y: 0, width: 200, fontSize: 12, rows: [] });
    const id = useStore.getState().meters[0].id;
    useStore.getState().deleteObjects([], [], [id]);
    expect(useStore.getState().meters.length).toBe(0);

    useStore.getState().undo();
    expect(useStore.getState().meters.length).toBe(1);
    expect(useStore.getState().meters[0].id).toBe(id);
  });
});
