// The runtime frame (View -> Runtime frame): what the panel shows of a
// screen. "Set from what I see now" turns the current zoom/pan into a
// canvas rectangle; it is kept per screen, written as canvas.viewport for
// the active screen and screenContents[id].viewport for the others, and
// read back the same way. Without it the panel fits everything drawn.

import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import { ProjectManager } from '../project/ProjectManager';
import { normalizeViewport } from '../project/RuntimeViewport';
import { visibleCanvasRect } from '../utils/CanvasView';

describe('visibleCanvasRect - the canvas rectangle a window shows', () => {
  it('undoes zoom and pan and rounds to whole canvas pixels', () => {
    expect(visibleCanvasRect({ zoom: 1, panX: 0, panY: 0 }, 800, 600)).toEqual({ x: 0, y: 0, width: 800, height: 600 });
    // Zoomed 2x and panned so canvas (100, 50) sits at the window's top-left.
    expect(visibleCanvasRect({ zoom: 2, panX: -200, panY: -100 }, 800, 600)).toEqual({ x: 100, y: 50, width: 400, height: 300 });
    expect(visibleCanvasRect({ zoom: 0.5, panX: 40, panY: 0 }, 800, 600)).toEqual({ x: -80, y: 0, width: 1600, height: 1200 });
  });

  it('a zoom of zero cannot divide the window away', () => {
    expect(visibleCanvasRect({ zoom: 0, panX: 0, panY: 0 }, 10, 10).width).toBe(10);
  });
});

describe('normalizeViewport - what a file may carry', () => {
  it('keeps four finite numbers with a positive size and drops the rest', () => {
    expect(normalizeViewport({ x: 1, y: 2, width: 3, height: 4 })).toEqual({ x: 1, y: 2, width: 3, height: 4 });
    expect(normalizeViewport({ x: 1, y: 2, width: 0, height: 4 })).toBeUndefined();
    expect(normalizeViewport({ x: '1', y: 2, width: 3, height: 4 })).toBeUndefined();
    expect(normalizeViewport({ x: 1, y: 2, width: 3, height: Infinity })).toBeUndefined();
    expect(normalizeViewport(null)).toBeUndefined();
    expect(normalizeViewport('x')).toBeUndefined();
  });
});

describe('The runtime frame in the store and the file', () => {
  beforeEach(() => {
    ProjectManager.newProject('Frames');
  });

  it('is set from the current view, dirties the project and is per screen', () => {
    const s = useStore.getState();
    expect(s.canvasConfig.viewport).toBeUndefined();
    s.setCanvasViewportSize({ width: 800, height: 600 });
    s.setCanvasState({ zoom: 2, panX: -200, panY: -100 });
    useStore.getState().setRuntimeViewport(visibleCanvasRect(useStore.getState().canvasState, 800, 600));
    expect(useStore.getState().canvasConfig.viewport).toEqual({ x: 100, y: 50, width: 400, height: 300 });
    expect(useStore.getState().isDirty).toBe(true);

    // A second screen starts without a frame; switching back restores the first one's.
    const first = useStore.getState().activeScreenId;
    useStore.getState().addScreen('Second');
    const second = useStore.getState().activeScreenId;
    expect(second).not.toBe(first);
    expect(useStore.getState().canvasConfig.viewport).toBeUndefined();
    useStore.getState().setRuntimeViewport({ x: 0, y: 0, width: 640, height: 480 });
    useStore.getState().switchScreen(first);
    expect(useStore.getState().canvasConfig.viewport).toEqual({ x: 100, y: 50, width: 400, height: 300 });
    expect(useStore.getState().screenContents[second]?.viewport).toEqual({ x: 0, y: 0, width: 640, height: 480 });

    // Clearing goes back to "fit everything drawn".
    useStore.getState().setRuntimeViewport(undefined);
    expect(useStore.getState().canvasConfig.viewport).toBeUndefined();
  });

  it('round-trips through the file: canvas.viewport for the active screen, screenContents for the rest', () => {
    useStore.getState().setRuntimeViewport({ x: 100, y: 50, width: 400, height: 300 });
    const first = useStore.getState().activeScreenId;
    useStore.getState().addScreen('Second');
    const second = useStore.getState().activeScreenId;
    useStore.getState().setRuntimeViewport({ x: 0, y: 0, width: 640, height: 480 });
    useStore.getState().switchScreen(first);

    const json = ProjectManager.getProjectData()!;
    const data = JSON.parse(json);
    expect(data.canvas.viewport).toEqual({ x: 100, y: 50, width: 400, height: 300 });
    expect(data.screenContents[second].viewport).toEqual({ x: 0, y: 0, width: 640, height: 480 });

    ProjectManager.newProject('Empty');
    expect(useStore.getState().canvasConfig.viewport).toBeUndefined();
    ProjectManager.loadProject(json, 'frames.epwsyn');
    expect(useStore.getState().canvasConfig.viewport).toEqual({ x: 100, y: 50, width: 400, height: 300 });
    useStore.getState().switchScreen(second);
    expect(useStore.getState().canvasConfig.viewport).toEqual({ x: 0, y: 0, width: 640, height: 480 });

    // A malformed frame in a file is simply no frame.
    data.canvas.viewport = { x: 1, y: 1, width: -5, height: 3 };
    ProjectManager.loadProject(JSON.stringify(data), 'bad.epwsyn');
    expect(useStore.getState().canvasConfig.viewport).toBeUndefined();
  });
});
