// feat/editing-and-signal-panel commit 6: the signal panel behaves like
// any other element - place, select, move, copy, delete. Mirrors
// meter-store.test.ts's own coverage for the meter element.

import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import { GRID_SIZE } from '../theme/ScadaTheme';

function resetStore() {
  useStore.setState({
    objects: [], connections: [], meters: [], signalPanels: [],
    selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [],
    clipboard: [], clipboardMeters: [], clipboardSignalPanels: [], clipboardConnections: [],
    history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [] }],
    historyIndex: 0
  });
}

describe('Signal panel element - place/select/move/copy/delete', () => {
  beforeEach(resetStore);

  it('addSignalPanel places a panel and gives it an id', () => {
    useStore.getState().addSignalPanel({ x: 100, y: 100, width: 160, fontSize: 12, rows: [] });
    const panels = useStore.getState().signalPanels;
    expect(panels.length).toBe(1);
    expect(typeof panels[0].id).toBe('string');
    expect(panels[0].id.length).toBeGreaterThan(0);
  });

  it('selectSignalPanels selects a panel and clears every other kind\'s selection', () => {
    useStore.getState().addSignalPanel({ x: 0, y: 0, width: 160, fontSize: 12, rows: [] });
    const id = useStore.getState().signalPanels[0].id;
    useStore.setState({ selectedIds: ['fake-obj'], selectedConnectionIds: ['fake-conn'], selectedMeterIds: ['fake-meter'] });

    useStore.getState().selectSignalPanels([id], false);

    expect(useStore.getState().selectedSignalPanelIds).toEqual([id]);
    expect(useStore.getState().selectedIds).toEqual([]);
    expect(useStore.getState().selectedConnectionIds).toEqual([]);
    expect(useStore.getState().selectedMeterIds).toEqual([]);
  });

  it('updateSignalPanel moves a panel (drag) by changing x/y', () => {
    useStore.getState().addSignalPanel({ x: 0, y: 0, width: 160, fontSize: 12, rows: [] });
    const id = useStore.getState().signalPanels[0].id;

    useStore.getState().updateSignalPanel(id, { x: 160, y: 240 });

    const moved = useStore.getState().signalPanels[0];
    expect(moved.x).toBe(160);
    expect(moved.y).toBe(240);
  });

  it('copySelected + paste duplicates a selected panel at an offset of exactly GRID_SIZE, with a new id', () => {
    useStore.getState().addSignalPanel({ x: 50, y: 60, width: 160, title: 'P1', fontSize: 12, rows: [] });
    const id = useStore.getState().signalPanels[0].id;
    useStore.getState().selectSignalPanels([id], false);

    useStore.getState().copySelected();
    useStore.getState().paste();

    const panels = useStore.getState().signalPanels;
    expect(panels.length).toBe(2);
    const pasted = panels.find(p => p.id !== id)!;
    expect(pasted).toBeTruthy();
    expect(pasted.x).toBe(50 + GRID_SIZE);
    expect(pasted.y).toBe(60 + GRID_SIZE);
    expect(pasted.title).toBe('P1');
    expect(useStore.getState().selectedSignalPanelIds).toEqual([pasted.id]);
  });

  it('duplicateSelected (Ctrl+D) duplicates in place with the same offset, without touching the clipboard', () => {
    useStore.getState().addSignalPanel({ x: 0, y: 0, width: 160, fontSize: 12, rows: [] });
    const id = useStore.getState().signalPanels[0].id;
    useStore.getState().selectSignalPanels([id], false);

    useStore.getState().duplicateSelected();

    const panels = useStore.getState().signalPanels;
    expect(panels.length).toBe(2);
    const dup = panels.find(p => p.id !== id)!;
    expect(dup.x).toBe(GRID_SIZE);
    expect(dup.y).toBe(GRID_SIZE);
    expect(useStore.getState().clipboardSignalPanels).toEqual([]);
  });

  it('duplicateSignalPanelInPlace (Alt+drag) leaves a copy at the exact same position, selection untouched', () => {
    useStore.getState().addSignalPanel({ x: 40, y: 60, width: 160, fontSize: 12, rows: [] });
    const id = useStore.getState().signalPanels[0].id;
    useStore.getState().selectSignalPanels([id], false);

    useStore.getState().duplicateSignalPanelInPlace(id);

    const panels = useStore.getState().signalPanels;
    expect(panels.length).toBe(2);
    const clone = panels.find(p => p.id !== id)!;
    expect(clone.x).toBe(40);
    expect(clone.y).toBe(60);
    expect(useStore.getState().selectedSignalPanelIds).toEqual([id]);
  });

  it('deleteObjects with a signal panel id removes that panel and its selection', () => {
    useStore.getState().addSignalPanel({ x: 0, y: 0, width: 160, fontSize: 12, rows: [] });
    const id = useStore.getState().signalPanels[0].id;
    useStore.getState().selectSignalPanels([id], false);

    useStore.getState().deleteObjects([], [], [], [id]);

    expect(useStore.getState().signalPanels.length).toBe(0);
    expect(useStore.getState().selectedSignalPanelIds).toEqual([]);
  });

  it('undo restores a deleted signal panel', () => {
    useStore.getState().addSignalPanel({ x: 0, y: 0, width: 160, fontSize: 12, rows: [] });
    const id = useStore.getState().signalPanels[0].id;
    useStore.getState().deleteObjects([], [], [], [id]);
    expect(useStore.getState().signalPanels.length).toBe(0);

    useStore.getState().undo();
    expect(useStore.getState().signalPanels.length).toBe(1);
    expect(useStore.getState().signalPanels[0].id).toBe(id);
  });

  // 22. a panel copied via Ctrl+C/Ctrl+V keeps every row
  it('copying a panel with several rows keeps all of them in the pasted copy', () => {
    useStore.getState().addSignalPanel({
      x: 0, y: 0, width: 160, fontSize: 12,
      rows: [
        { device: '', label: 'Krancowka otwarta', manualState: 'ON' },
        { device: '', label: 'Krancowka zamknieta', manualState: 'OFF' },
        { device: '', label: 'Fotokomorka', manualState: 'QUALITY' }
      ]
    });
    const id = useStore.getState().signalPanels[0].id;
    useStore.getState().selectSignalPanels([id], false);

    useStore.getState().copySelected();
    useStore.getState().paste();

    const pasted = useStore.getState().signalPanels.find(p => p.id !== id)!;
    expect(pasted.rows.length).toBe(3);
    expect(pasted.rows.map(r => r.label)).toEqual(['Krancowka otwarta', 'Krancowka zamknieta', 'Fotokomorka']);
    expect(pasted.rows.map(r => r.manualState)).toEqual(['ON', 'OFF', 'QUALITY']);
  });
});
