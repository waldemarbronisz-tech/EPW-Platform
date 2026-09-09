import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';

describe('Store History and Core Operations', () => {
  beforeEach(() => {
    useStore.setState({
      objects: [],
      connections: [],
      history: [{ objects: [], connections: [] } as any],
      historyIndex: 0
    });
  });

  it('undoes and redoes object creation cleanly', () => {
    const store = useStore.getState();
    store.addObject({ type: 'electrical.busbar', x: 0, y: 0 } as any);

    expect(useStore.getState().objects.length).toBe(1);

    useStore.getState().undo();
    expect(useStore.getState().objects.length).toBe(0);

    useStore.getState().redo();
    expect(useStore.getState().objects.length).toBe(1);
  });

  it('addObject still creates a history entry (regression check for the updateObject/saveHistory split)', () => {
    const store = useStore.getState();
    expect(useStore.getState().history.length).toBe(1);

    store.addObject({ type: 'electrical.busbar', x: 0, y: 0 } as any);

    expect(useStore.getState().history.length).toBe(2);
    expect(useStore.getState().historyIndex).toBe(1);
  });

  it('multiple updateObject calls on the same object do not grow history', () => {
    const store = useStore.getState();
    store.addObject({ type: 'electrical.busbar', x: 0, y: 0, designation: '' } as any);
    const objId = useStore.getState().objects[0].id;
    const historyLenAfterAdd = useStore.getState().history.length;

    store.updateObject(objId, { designation: 'K' });
    store.updateObject(objId, { designation: 'KM' });
    store.updateObject(objId, { designation: 'KMG' });
    store.updateObject(objId, { designation: 'KMG-1' });

    expect(useStore.getState().objects[0].designation).toBe('KMG-1');
    expect(useStore.getState().history.length).toBe(historyLenAfterAdd);
  });

  it('an explicit saveHistory after a series of updateObject calls adds exactly one entry', () => {
    const store = useStore.getState();
    store.addObject({ type: 'electrical.busbar', x: 0, y: 0, designation: '' } as any);
    const objId = useStore.getState().objects[0].id;
    const historyLenBefore = useStore.getState().history.length;

    store.updateObject(objId, { designation: 'K' });
    store.updateObject(objId, { designation: 'KM' });
    store.updateObject(objId, { designation: 'KMG-1' });
    store.saveHistory();

    expect(useStore.getState().history.length).toBe(historyLenBefore + 1);
  });

  it('calling saveHistory twice without a state change in between adds only one entry', () => {
    const store = useStore.getState();
    store.addObject({ type: 'electrical.busbar', x: 0, y: 0, designation: '' } as any);
    const objId = useStore.getState().objects[0].id;

    store.updateObject(objId, { designation: 'KMG-1' });
    store.saveHistory();
    const lenAfterFirstSave = useStore.getState().history.length;

    store.saveHistory();
    const lenAfterSecondSave = useStore.getState().history.length;

    expect(lenAfterSecondSave).toBe(lenAfterFirstSave);
  });

  it('history caps at MAX_HISTORY (100) and undo still lands on the correct state', () => {
    const store = useStore.getState();
    store.addObject({ type: 'electrical.busbar', x: 0, y: 0, designation: '' } as any);
    const objId = useStore.getState().objects[0].id;

    // Push well past the cap with 150 distinct, individually-committed states.
    for (let i = 0; i < 150; i++) {
      store.updateObject(objId, { designation: `D${i}` });
      store.saveHistory();
    }

    const state = useStore.getState();
    expect(state.history.length).toBe(100);
    expect(state.historyIndex).toBe(99);
    expect(state.objects[0].designation).toBe('D149');

    useStore.getState().undo();
    expect(useStore.getState().objects[0].designation).toBe('D148');
  });
});
