// feat/editing-and-signal-panel commit 4: pan/zoom math (pure,
// Konva-free) and confirmation that canvasState (zoom/pan) never
// reaches a saved project file - a session setting, not content.

import { describe, it, expect } from 'vitest';
import { clampZoom, computeContentBounds, computeFitView, MIN_ZOOM, MAX_ZOOM } from '../utils/CanvasView';
import { useStore } from '../store';
import { ProjectManager } from '../project/ProjectManager';
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

describe('clampZoom', () => {
  it('clamps below MIN_ZOOM (25%) up to the minimum', () => {
    expect(clampZoom(0.05)).toBe(MIN_ZOOM);
  });

  it('clamps above MAX_ZOOM (400%) down to the maximum', () => {
    expect(clampZoom(10)).toBe(MAX_ZOOM);
  });

  it('leaves an in-range zoom untouched', () => {
    expect(clampZoom(1.5)).toBe(1.5);
  });

  it('the declared range is exactly 25% to 400%', () => {
    expect(MIN_ZOOM).toBe(0.25);
    expect(MAX_ZOOM).toBe(4);
  });
});

describe('computeContentBounds', () => {
  it('returns null when there is nothing at all', () => {
    expect(computeContentBounds([], [], [])).toBeNull();
  });

  it('bounds a single object exactly to its own box', () => {
    const bounds = computeContentBounds([makeObj('A', 100, 200, 64, 64)], [], []);
    expect(bounds).toEqual({ minX: 100, minY: 200, maxX: 164, maxY: 264 });
  });

  it('bounds span multiple objects, meters and connection points together', () => {
    const bounds = computeContentBounds(
      [makeObj('A', 0, 0, 64, 64)],
      [],
      [{ id: 'W', points: [{ x: -50, y: 0 }, { x: 500, y: 500 }], medium: 'ELECTRICAL', style: 'NORMAL', state: 'LIVE' }]
    );
    expect(bounds!.minX).toBe(-50);
    expect(bounds!.maxX).toBe(500);
    expect(bounds!.maxY).toBe(500);
  });
});

describe('computeFitView', () => {
  it('falls back to 100% zoom, no pan, when there is nothing to fit', () => {
    expect(computeFitView(null, 800, 600)).toEqual({ zoom: 1, panX: 0, panY: 0 });
  });

  it('fits and centers a content box inside the viewport, clamped to the zoom range', () => {
    const bounds = { minX: 0, minY: 0, maxX: 400, maxY: 200 };
    const view = computeFitView(bounds, 800, 600);
    expect(view.zoom).toBeGreaterThan(0);
    expect(view.zoom).toBeLessThanOrEqual(MAX_ZOOM);
    // The content's own center (200,100) should land at the viewport's
    // own center (400,300) once panned and scaled.
    expect(200 * view.zoom + view.panX).toBeCloseTo(400, 5);
    expect(100 * view.zoom + view.panY).toBeCloseTo(300, 5);
  });

  it('never exceeds MAX_ZOOM even for tiny content in a huge viewport', () => {
    const bounds = { minX: 0, minY: 0, maxX: 1, maxY: 1 };
    const view = computeFitView(bounds, 4000, 4000);
    expect(view.zoom).toBe(MAX_ZOOM);
  });

  it('never goes below MIN_ZOOM even for huge content in a tiny viewport', () => {
    const bounds = { minX: 0, minY: 0, maxX: 100000, maxY: 100000 };
    const view = computeFitView(bounds, 200, 200);
    expect(view.zoom).toBe(MIN_ZOOM);
  });
});

describe('canvasState (zoom/pan) is never saved to the project file', () => {
  it('getProjectData does not include zoom, panX or panY anywhere in the saved JSON', () => {
    useStore.setState({
      objects: [], connections: [], meters: [],
      canvasState: { zoom: 2.5, panX: 123, panY: 456 }
    });

    const json = ProjectManager.getProjectData();
    expect(json).not.toBeNull();
    expect(json).not.toContain('"zoom"');
    expect(json).not.toContain('"panX"');
    expect(json).not.toContain('"panY"');
  });

  it('loadProject does not touch canvasState at all - it stays whatever the session already had', () => {
    useStore.setState({ canvasState: { zoom: 3, panX: 10, panY: 20 } });
    const projectJson = ProjectManager.getProjectData();

    // Loading a (freshly saved, zoom-free) project file must not reset
    // or otherwise touch the current session's zoom/pan.
    ProjectManager.loadProject(projectJson!, 'test.epwsyn');

    expect(useStore.getState().canvasState).toEqual({ zoom: 3, panX: 10, panY: 20 });
  });
});
