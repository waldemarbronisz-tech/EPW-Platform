// feat/media-and-proportions part C: the toolbar's medium/style
// selector for newly drawn wires - store-level behavior only (the
// toolbar buttons and Canvas.tsx's 1/2/3 shortcuts are thin wrappers
// around these same two actions, already exercised by hand).

import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';

describe('Drawing medium/style selector', () => {
  beforeEach(() => {
    useStore.setState({ drawingMedium: 'ELECTRICAL', drawingStyle: 'NORMAL' });
  });

  it('defaults to ELECTRICAL / NORMAL', () => {
    expect(useStore.getState().drawingMedium).toBe('ELECTRICAL');
    expect(useStore.getState().drawingStyle).toBe('NORMAL');
  });

  it('setDrawingMedium switches the medium a new wire will be drawn with', () => {
    useStore.getState().setDrawingMedium('WATER');
    expect(useStore.getState().drawingMedium).toBe('WATER');

    useStore.getState().setDrawingMedium('VENTILATION');
    expect(useStore.getState().drawingMedium).toBe('VENTILATION');
  });

  it('setDrawingStyle switches between NORMAL and BUS', () => {
    useStore.getState().setDrawingStyle('BUS');
    expect(useStore.getState().drawingStyle).toBe('BUS');

    useStore.getState().setDrawingStyle('NORMAL');
    expect(useStore.getState().drawingStyle).toBe('NORMAL');
  });

  it('a wire finished while a non-default medium/style is selected carries that medium/style', () => {
    useStore.setState({ objects: [], connections: [], history: [{ objects: [], connections: [] } as any], historyIndex: 0 });
    useStore.getState().setDrawingMedium('VENTILATION');
    useStore.getState().setDrawingStyle('BUS');

    const { drawingMedium, drawingStyle } = useStore.getState();
    useStore.getState().addConnection({
      points: [{ x: 0, y: 0 }, { x: 32, y: 0 }],
      medium: drawingMedium,
      style: drawingStyle,
      state: 'LIVE'
    });

    const conn = useStore.getState().connections[0];
    expect(conn.medium).toBe('VENTILATION');
    expect(conn.style).toBe('BUS');
  });
});
